#!/usr/bin/env python3
"""P9-C2 pedestrian root error, P2-D definitions applied to SLAM keyframe states (docs/phase2/criterion_D.md, p2-skeleton-replay worktree).
  Estimate     p_w,est: the track's last-written world root at a keyframe (ped_log.txt) -- criterion_D.md sec. 2 "Estimate".
  Camera       T_cw,est = the keyframe's own pose at that write (the run's camera; sec. 2 "Window camera"); T_cw,GT = (T_w,base_link_gt * T_b_c)^-1,
               slerp + linear (sec. 2 "GT"); p_root,GT = the object_N tf origin, NEAREST GT sample within 0.05 s (sec. 2 "GT", last bullet).
  Error        e = T_cw,est p_w,est - T_cw,GT p_root,GT; depth d = e.r_hat, perpendicular q = |e - d r_hat| (sec. 2 "Error").  PRIMARY metric.
  Association  (WORLD frame, P2-D) per TRACK, exactly analyze_o2c.object_metrics (eval/o2c_height_prior/analyze_o2c.py:161-214, cited by criterion_D.md sec. 2
               "Association"): track positions -> GT world by the ego->GT Sim(3); for every GT object the nearest GT sample within 0.05 s of
               every estimate (>= 5 samples), median xy distance over them; the object with the smallest median is the match, accepted if < 5 m.
               The ego->GT Sim(3) is the Umeyama fit of the run's main-map keyframe camera centres to the GT camera centres.
  World error  |S(p_w,est) - p_root,GT| (secondary).
  B0           the per-frame measurement alone: the root pixel back-projected along its ray, depth z = f c_L 1.70 / l_px (P9-C3b z model; was the ray length) (stature prior mean, same c_L),
               posed with the SAME keyframe pose; no temporal model, no BA. Same keys (kf, track), same error definition, same association.
P9-C2 5b.3: the PRIMARY camera-frame metric associates in the camera frame: per track, for every GT object the median over the track's samples (GT
             sample nearest in time within 0.05 s, >= 5 samples) of |p_c,est - p_c,GT|; the nearest object is the match, accepted if < 5 m (same gate).
             The world-frame (secondary) metric keeps the P2-D association above. Both are computed per map (own Sim(3)).
P9-C2 5b.4: velocity: world-frame root velocity of the state (rotated by the map's Sim(3): s R v) against the GT root velocity = least-squares slope
             of the GT root over +-0.6 s (P7-A A8 window); B0 velocity = central finite difference of the B0 positions of consecutive states of the same
             track (neighbours <= 0.3 s away). Samples = camera-association matches.
Usage: p9c_ped_error.py RUN_DIR GT_NPZ PERCEPTION_SEQ_DIR C_L OUT_PREFIX    -> OUT_PREFIX.json, OUT_PREFIX_samples.csv"""
import csv, json, sys
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

F = 415.69219381653056
CX, CY = 360.0, 240.0
GATE_DT, MIN_SAMPLES, GATE_XY = 0.05, 5, 5.0


def load_gt(path):
    d = np.load(path, allow_pickle=True)
    body = d['tf|world|base_link_gt']
    objs = {k.split('|')[-1]: d[k][np.argsort(d[k][:, 0], kind='stable')] for k in d.files if k.startswith('tf|world|object_')}
    for s in d['tf_static']:
        t = eval(str(s))
        if t[0] == 'base_link_gt' and t[1] == 'left_cam':
            Tbc = np.eye(4); Tbc[:3, :3] = R.from_quat(t[5:9]).as_matrix(); Tbc[:3, 3] = t[2:5]
    o = np.argsort(body[:, 0], kind='stable'); body = body[o]
    _, first = np.unique(body[:, 0], return_index=True); body = body[np.sort(first)]
    return body, objs, Tbc


class GtCam:
    def __init__(self, body, Tbc):
        self.t, self.p, self.Tbc = body[:, 0], body[:, 1:4], Tbc
        self.sl = Slerp(self.t, R.from_quat(body[:, 4:8]))

    def Twc(self, ts):
        ts = np.clip(ts, self.t[0], self.t[-1])
        p = np.stack([np.interp(ts, self.t, self.p[:, c]) for c in range(3)], 1)
        Rm = self.sl(ts).as_matrix()
        T = np.tile(np.eye(4), (len(ts), 1, 1)); T[:, :3, :3] = Rm; T[:, :3, 3] = p
        return T @ self.Tbc


def nearest(a, te):
    """index of the nearest GT sample and the keep mask (|dt| < 0.05), criterion_D.md sec. 2 / analyze_o2c.py:195-198."""
    idx = np.clip(np.searchsorted(a[:, 0], te), 1, len(a) - 1)
    pick = np.where(np.abs(a[idx - 1, 0] - te) < np.abs(a[idx, 0] - te), idx - 1, idx)
    return pick, np.abs(a[pick, 0] - te) < GATE_DT


def umeyama(src, dst):
    mu_s, mu_d = src.mean(0), dst.mean(0)
    S, D = src - mu_s, dst - mu_d
    U, sig, Vt = np.linalg.svd(D.T @ S / len(src))
    d = np.ones(3); d[2] = np.sign(np.linalg.det(U) * np.linalg.det(Vt))
    Rm = U @ np.diag(d) @ Vt
    return (sig * d).sum() / (S ** 2).sum() * len(src), Rm, mu_d - (sig * d).sum() / (S ** 2).sum() * len(src) * Rm @ mu_s


def read_log(run):
    recs = []
    for l in open(f'{run}/ped_log.txt'):
        if l[0] == '#' or not l.strip():
            continue
        x = l.split(); v = [float.fromhex(u) for u in x[3:]]
        Twc = np.eye(4); Twc[:3, :3] = R.from_quat(v[9:13]).as_matrix(); Twc[:3, 3] = v[6:9]
        recs.append((int(x[0]), float(x[1]), int(x[2]), np.array(v[:3]), Twc, np.array(v[3:6])))
    return recs


def map_segments(run):
    """[(t_first, t_last, centres Nx3, stamps N)] for every map of the run: the live maps (keyframes_exact.txt) and the maps a reset retired
    (keyframe_trajectory_retired*_map*.tum, written by the runner just before the reset). Each map has its own world frame, so each gets its
    own ego->GT Sim(3)."""
    import glob
    segs = []
    by = {}
    for l in open(f'{run}/keyframes_exact.txt'):
        if l[0] == '#': continue
        x = l.split(); v = [float.fromhex(u) for u in x[3:]]
        by.setdefault(int(x[0]), []).append((float(x[2]), v[:3]))
    for m, lst in by.items():
        if len(lst) >= 20:
            ts = np.array([a for a, _ in lst]); segs.append((ts.min(), ts.max(), np.array([b for _, b in lst]), ts))
    for f in sorted(glob.glob(f'{run}/keyframe_trajectory_retired*_map*.tum')):
        a = np.loadtxt(f, ndmin=2)
        if len(a) >= 20:
            segs.append((a[:, 0].min(), a[:, 0].max(), a[:, 1:4], a[:, 0]))
    return segs


_cache = {}


def percep_row(pdir, stamp, track):
    key = (pdir, stamp)
    if key not in _cache:
        rows = {}
        try:
            for l in open(f'{pdir}/{int(round(stamp * 1e6)):019d}.ped.txt'):
                if l.startswith('P '):
                    x = l.split(); rows[int(x[1])] = [float(u) for u in x[2:6]]
        except FileNotFoundError:
            pass
        _cache[key] = rows
    return _cache[key].get(track)


def gt_velocity(a, t, half=0.6, min_n=8):
    m = (a[:, 0] >= t - half) & (a[:, 0] <= t + half)
    if m.sum() < min_n:
        return None
    tt = a[m, 0] - a[m, 0].mean()
    return np.array([(tt @ (a[m, c] - a[m, c].mean())) / (tt @ tt) for c in (1, 2, 3)])


def sim_of(segsim, t):
    c = [(abs(t - 0.5 * (a + b)), S) for a, b, S in segsim if a - 1.0 <= t <= b + 1.0]
    return min(c, key=lambda z: z[0])[1] if c else None


METRIC_LOGS = 0.2      # a map is "metric" when its ego->GT Sim(3) has |log s| < 0.2 (tuning evaluation only: uses GT)


def group(est, segsim, metric_only=False):
    """per[(track, map)] = [(estimate, Sim3)]. metric_only drops the states of maps whose Sim(3) scale is not ~1: before the IMU initialisation
    (and in maps where it failed) the map scale is arbitrary, the pedestrian factor set is only the scale-free root reprojection and the
    state is the per-frame initialisation, i.e. identical to B0 by construction (P9-C2 5b finding, office_s1_12h)."""
    per = {}
    n_nomap = 0
    group.n_nonmetric = 0
    for e in est:
        S = sim_of(segsim, e[1])
        if S is None:
            n_nomap += 1
            continue
        if metric_only and abs(np.log(S[0])) >= METRIC_LOGS:
            group.n_nonmetric += 1
            continue
        per.setdefault((e[2], id(S)), []).append((e, S))
    return per, n_nomap


def associate(per, objs, gtcam, mode):
    """mode 'world' (P2-D) or 'cam' (P9-C2 5b.3). Returns {track_key: gt_name} and outcome counts."""
    matched, outc = {}, {}
    for tkey, ess in per.items():
        es = [z[0] for z in ess]
        te = np.array([e[1] for e in es])
        if mode == 'world':
            pe = np.array([ess[i][1][0] * ess[i][1][1] @ e[3] + ess[i][1][2] for i, e in enumerate(es)])
        else:
            Tcws = np.linalg.inv(np.array([e[4] for e in es]))
            pe = np.einsum('nij,nj->ni', Tcws[:, :3, :3], np.array([e[3] for e in es])) + Tcws[:, :3, 3]
            Tgc = np.linalg.inv(gtcam.Twc(te))
        best = None
        for name, a in objs.items():
            pick, keep = nearest(a, te)
            if keep.sum() < MIN_SAMPLES:
                continue
            if mode == 'world':
                d = np.linalg.norm(pe[keep, :2] - a[pick[keep], 1:3], axis=1)
            else:
                g = a[pick, 1:4]
                pg = np.einsum('nij,nj->ni', Tgc[:, :3, :3], g) + Tgc[:, :3, 3]
                d = np.linalg.norm(pe[keep] - pg[keep], axis=1)
            md = float(np.median(d))
            if best is None or md < best[1]:
                best = (name, md)
        o = 'matched' if (best and best[1] < GATE_XY) else ('no_gt_sample_overlap' if best is None else 'nearest_gt_median_>=5m')
        outc.setdefault(o, [0, 0]); outc[o][0] += 1; outc[o][1] += len(es)
        if o == 'matched':
            matched[tkey] = best[0]
    return matched, {k: dict(tracks=v[0], states=v[1]) for k, v in outc.items()}


def samples(per, matched, objs, gtcam):
    rows = []
    for tkey, name in matched.items():
        a = objs[name]
        for (e_, S_) in per[tkey]:
            (kf, t, tr, pw, Twc, vw) = e_
            s, Rm, tt = S_
            pick, keep = nearest(a, np.array([t]))
            if not keep[0]:
                continue
            g = a[pick[0], 1:4]
            Tcw = np.linalg.inv(Twc); pc = Tcw[:3, :3] @ pw + Tcw[:3, 3]
            Tg = np.linalg.inv(gtcam.Twc(np.array([t]))[0]); pg = Tg[:3, :3] @ g + Tg[:3, 3]
            e = pc - pg; r = pg / np.linalg.norm(pg); d = float(e @ r)
            pws = s * Rm @ pw + tt
            rows.append(dict(kf=kf, stamp=t, track=tkey[0], gt=name, range_gt=float(np.linalg.norm(pg)), cam=float(np.linalg.norm(e)),
                             depth=abs(d), perp=float(np.linalg.norm(e - d * r)), depth_signed=d, world=float(np.linalg.norm(pws - g)),
                             world_xy=float(np.linalg.norm((pws - g)[:2]))))
    return rows


def velocity_rows(per, matched, objs, b0=False):
    """world-frame velocity error. flag-on: s R v_state; B0: central difference of consecutive states' world positions (Sim(3)-mapped)."""
    rows = []
    for tkey, name in matched.items():
        seq = sorted(per[tkey], key=lambda z: z[0][1])
        a = objs[name]
        P = [S[0] * S[1] @ e[3] + S[2] for e, S in seq]
        T = [e[1] for e, _ in seq]
        for k, (e, S) in enumerate(seq):
            gv = gt_velocity(a, e[1])
            if gv is None:
                continue
            if b0:
                if k == 0 or k == len(seq) - 1 or T[k + 1] - T[k] > 0.3 or T[k] - T[k - 1] > 0.3 or T[k + 1] - T[k - 1] <= 0:
                    continue
                v = (P[k + 1] - P[k - 1]) / (T[k + 1] - T[k - 1])
            else:
                v = S[0] * S[1] @ e[5]
            rows.append(dict(kf=e[0], track=tkey[0], vel=float(np.linalg.norm(v - gv)), vel_xy=float(np.linalg.norm((v - gv)[:2])), speed_gt=float(np.linalg.norm(gv[:2]))))
    return rows


def stats(rows, keys):
    out = {}
    for k in keys:
        a = np.array([r[k] for r in rows])
        out[k] = dict(median=float(np.median(a)) if len(a) else None, p90=float(np.percentile(a, 90)) if len(a) else None)
    return out


def b0_estimates(log, pdir, cL):
    out = []
    for (kf, t, tr, pw, Twc, vw) in log:
        row = percep_row(pdir, t, tr)
        if row is None or row[2] <= 0:
            continue
        u, v, lpx = row[0], row[1], row[2]
        b = np.array([(u - CX) / F, (v - CY) / F, 1.0])      # P9-C3b erratum: l_px = f L / z, so the OPTICAL-AXIS depth is z = f cL H0 / l_px (b has z = 1)
        Xc = (F * cL * 1.70 / lpx) * b
        out.append((kf, t, tr, Twc[:3, :3] @ Xc + Twc[:3, 3], Twc, np.zeros(3)))
    return out


def assess(est, segsim, objs, gtcam, label, metric_only=False):
    per, n_nomap = group(est, segsim, metric_only)
    n_nonmetric = group.n_nonmetric
    m_cam, a_cam = associate(per, objs, gtcam, 'cam')
    m_world, a_world = associate(per, objs, gtcam, 'world')
    rc = samples(per, m_cam, objs, gtcam)
    rw = samples(per, m_world, objs, gtcam)
    rv = velocity_rows(per, m_cam, objs, b0=(label == 'B0'))
    out = dict(label=label, n_states=len(est), n_states_no_map=n_nomap, n_states_nonmetric_map=n_nonmetric, n_tracks=len(per),
               primary_cam=dict(association=a_cam, n_tracks_matched=len(m_cam), n_samples=len(rc), **stats(rc, ('cam', 'depth', 'perp'))),
               secondary_world=dict(association=a_world, n_tracks_matched=len(m_world), n_samples=len(rw), **stats(rw, ('world', 'world_xy'))),
               velocity=dict(n_samples=len(rv), **stats(rv, ('vel', 'vel_xy'))))
    return out, rc, rv


def evaluate(run, gtp, pdir, cL, metric_only=False):
    body, objs, Tbc = load_gt(gtp)
    gtcam = GtCam(body, Tbc)
    segsim = []
    for (t0, t1, c, ts) in map_segments(run):
        gc = gtcam.Twc(ts)[:, :3, 3]
        segsim.append((t0, t1, umeyama(c, gc)))
    log = read_log(run)
    on, rows_on, vel_on = assess(log, segsim, objs, gtcam, 'flag_on', metric_only)
    b0, rows_b0, vel_b0 = assess(b0_estimates(log, pdir, cL), segsim, objs, gtcam, 'B0', metric_only)
    return {'sim3_scales': [float(S[0]) for _, _, S in segsim], 'flag_on': on, 'B0': b0}, rows_on, rows_b0


if __name__ == '__main__':
    run, gtp, pdir, cL, outp = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5]
    summ, ron, rb0 = evaluate(run, gtp, pdir, cL)
    json.dump(summ, open(outp + '.json', 'w'), indent=1)
    for tag, rows in (('flag_on', ron), ('B0', rb0)):
        if rows:
            with open(f'{outp}_samples_{tag}.csv', 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(json.dumps(summ))
