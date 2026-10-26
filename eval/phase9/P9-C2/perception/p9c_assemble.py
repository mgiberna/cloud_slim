#!/usr/bin/env python3
"""P9-C step 2, stage D: assemble the per-frame pedestrian files read by the deterministic runner.

One file per image of the sequence: <OUT>/<seq>/<round(stamp*1e6):019d>.ped.txt (an image without pedestrians gets a header-only file).
Rows (one per tracker track with a matched mask at that image, ascending track id):
  P track_id root_u root_v lpx mask_h
  C claimed_stamp track_id claim_L claim_R toeL_u toeL_v toeR_u toeR_v box_h      (P9-C2: LATE stance claims, see below)
  root_u/v  mask root (cu, vb - 0.55 h)  (P1-A p1a_common.py:38, data.root_pixel)
  lpx       RTMW |nose - mean(heels)| in pixels (keypoints 0, 19, 22 >= 0.3 and in the image; P1-B p1b_common.py:44-45), 0 if absent;
            the RTMW detection is associated to the track exactly as P4-S1 does (hip midpoint -> mask root, gate 0.5 mask height, greedy)
  mask_h    mask pixel height
  C rows    P4-S1 agree+timing stance claims (at least one foot claimed) of the image TIMING_WINDOW_FRAMES = 6 images earlier
            (stance_foot_poc stance/fusion.py:72,92,110: a claim at image t is final only at image t+6); box_h = person box height of the
            Halpe26 detection, toe*_u/v = toe-midpoint pixel of that foot at the claimed image
Usage (stance_foot_poc .venv python): p9c_assemble.py SEQ P1A_DIR RTMW_NPZ STANCE_DIR OUT_DIR
"""
import hashlib, json, os, subprocess, sys
import numpy as np
POC = '/home/marco/workspaces/stance_foot_poc'
sys.path.insert(0, POC)
from p4s1 import data  # noqa: E402

CONF = 0.3
NOSE, L_HIP, R_HIP, L_HEEL, R_HEEL = 0, 11, 12, 19, 22
W, H = 720, 480


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


class Tracks:
    def __init__(self, p1a, seq):
        self.stamps = np.load(f'{p1a}/{seq}_rgb_stamps.npy')
        tr = np.load(f'{p1a}/{seq}_tracks.npy'); mk = np.load(f'{p1a}/{seq}_masks.npy')
        joined, self.counts = data.join_tracks_masks(tr, mk)
        ok = ~np.isnan(joined[:, 6])
        self.tab = {}
        for r in joined[ok]:
            self.tab.setdefault(round(r[0], 4), []).append(r)

    def at(self, i):
        return np.array(self.tab.get(round(self.stamps[i], 4), np.zeros((0, 10))))


def associate_dets(rows, kp, sc):
    """kp (n,K,2), sc (n,K) of the detections of one frame; returns {det_index: row_index} (P4-S1 rule, hips 11/12)."""
    pts = []
    for k in range(len(kp)):
        pts.append(tuple(0.5 * (kp[k, L_HIP] + kp[k, R_HIP])) if sc[k, L_HIP] >= CONF and sc[k, R_HIP] >= CONF else None)
    return data.assoc_detections_to_tracks(pts, rows)


def main(seq, p1a, rtmw_npz, stance_dir, out):
    T = Tracks(p1a, seq)
    n = len(T.stamps)
    rt = np.load(rtmw_npz)
    st = np.load(f'{stance_dir}/{seq}/dets.npz'); cl = np.load(f'{stance_dir}/{seq}/claims_agree_timing.npz')
    # RTMW detections per frame
    by_rt = {}
    for k, f in enumerate(rt['frame']):
        by_rt.setdefault(int(f), []).append(k)
    # stance: claims per (frame, track) and the Halpe26 detection behind them
    real = cl['det'] >= 0
    tid = cl['seg_track'][cl['seg_id']]
    claims = {}
    for det, fr, t, c in zip(cl['det'][real], cl['frame'][real], tid[real], cl['claim'][real]):
        kp = st['kp'][det]
        toe = np.stack([0.5 * (kp[20] + kp[22]), 0.5 * (kp[21] + kp[23])])   # Halpe26: 20/22 L big/small toe, 21/23 R (p4s1_export_claims.py)
        claims[(int(fr), int(t))] = (c, toe, float(st['bbox'][det, 3] - st['bbox'][det, 1]))
    LAG = 6   # stance_foot_poc stance/fusion.py:72 TIMING_WINDOW_FRAMES
    late = {}  # file image index -> list of C rows
    for (fr, tr), (c, toe, bh) in sorted(claims.items()):
        if c.any() and fr + LAG < n:
            late.setdefault(fr + LAG, []).append('C %.9f %d %d %d %.2f %.2f %.2f %.2f %.1f' % (T.stamps[fr], tr, int(c[0]), int(c[1]), toe[0, 0], toe[0, 1], toe[1, 0], toe[1, 1], bh))
    os.makedirs(f'{out}/{seq}', exist_ok=True)
    stats = dict(images=n, rows=0, with_lpx=0)
    for i in range(n):
        rows = T.at(i)
        order = np.argsort(rows[:, 1]) if len(rows) else []
        lpx = {}
        if len(rows) and i in by_rt:
            ks = by_rt[i]
            kp, sc = rt['kp'][ks], rt['sc'][ks]
            a = associate_dets(rows, kp, sc)
            for j, r in a.items():
                p = kp[j]; s = sc[j]
                if s[NOSE] >= CONF and s[L_HEEL] >= CONF and s[R_HEEL] >= CONF and all(0 <= p[q, 0] < W and 0 <= p[q, 1] < H for q in (NOSE, L_HEEL, R_HEEL)):
                    lpx[int(rows[r][1])] = float(np.linalg.norm(p[NOSE] - 0.5 * (p[L_HEEL] + p[R_HEEL])))
        lines = [f'# stamp {T.stamps[i]:.9f} image {i}']
        seen = set()
        for r in (rows[order] if len(rows) else []):
            t = int(r[1])
            if t in seen:
                continue
            seen.add(t)
            ru, rv = data.root_pixel(r)
            lines.append('P %d %.3f %.3f %.3f %.1f' % (t, ru, rv, lpx.get(t, 0.0), r[2]))
            stats['rows'] += 1; stats['with_lpx'] += t in lpx
        lines += late.get(i, [])
        stats['late_claim_rows'] = stats.get('late_claim_rows', 0) + len(late.get(i, []))
        with open(f'{out}/{seq}/{int(round(T.stamps[i] * 1e6)):019d}.ped.txt', 'w') as f:
            f.write('\n'.join(lines) + '\n')
    poc = subprocess.run(['git', '-C', POC, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    man = dict(seq=seq, stats=stats, poc_commit=poc, assemble_md5=md5(__file__),
               inputs={k: md5(v) for k, v in dict(tracks=f'{p1a}/{seq}_tracks.npy', masks=f'{p1a}/{seq}_masks.npy', stamps=f'{p1a}/{seq}_rgb_stamps.npy',
                                                    rtmw=rtmw_npz, dets=f'{stance_dir}/{seq}/dets.npz', claims=f'{stance_dir}/{seq}/claims_agree_timing.npz').items()},
               join_counts=T.counts)
    json.dump(man, open(f'{out}/{seq}/manifest.json', 'w'), indent=1)
    print(seq, stats)


if __name__ == '__main__':
    main(*sys.argv[1:6])
