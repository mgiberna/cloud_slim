"""P9-C3 shared loaders (tuning sequences only). Reuses the P9-C2 5b tooling: stance_foot_poc p4s1.data.Seq (GT association, P1-A criterion 1.2),
p9c_assemble.associate_dets (RTMW detection -> track, P4-S1 rule) and constants.json (c_L). Runs with the stance_foot_poc python (laptop python3.8 is enough)."""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P9C2 = os.path.join(HERE, '..', 'P9-C2')
sys.path.insert(0, '/home/marco/workspaces/stance_foot_poc')
sys.path.insert(0, os.path.join(P9C2, 'perception'))
from p4s1 import data  # noqa: E402
import p9c_assemble as asm  # noqa: E402

D = '/media/marco/muffin1/datasets'
TUNE = ['apartment_s1_01h', 'apartment_s1_02h', 'office_s1_12h']
data.P1A = f'{D}/p9c_gtp1a'
data.SHORT.update({s: s for s in TUNE})
F, CX, CY = data.FX, data.CX, data.CY
W, H = 720, 480
CL = json.load(open(os.path.join(P9C2, 'constants.json')))['c_L']
H0 = 1.70
CONF = 0.3
FOOT_KP = (17, 18, 19, 20, 21, 22)       # COCO-WholeBody: L big toe, L small toe, L heel, R big toe, R small toe, R heel
RTMW = {'apartment_s1_01h': f'{D}/p9c_perception_work/rtmw/apartment_s1_01h_rtmw_all.npz',
        'apartment_s1_02h': f'{D}/p9c_perception_work/rtmw/apartment_s1_02h_rtmw_all.npz',
        'office_s1_12h': f'{D}/phase2/skeleton/office_s1_12h_rtmw_all.npz'}
PED2 = f'{D}/p9c2_perception'
mad = lambda x: 1.4826 * np.median(np.abs(np.asarray(x) - np.median(x)))


def lowest_foot(kp, sc):
    """Lowest (max image v) of the six foot keypoints with score >= CONF inside the image, or None. kp (K,2), sc (K,)."""
    best = None
    for k in FOOT_KP:
        if sc[k] >= CONF and 0 <= kp[k, 0] < W and 0 <= kp[k, 1] < H:
            if best is None or kp[k, 1] > best[1]:
                best = (float(kp[k, 0]), float(kp[k, 1]), float(sc[k]), k)
    return best


def sequence_rows(seq):
    """One dict per (image, track) with a P row in p9c2_perception, a non-truncated mask and a GT pedestrian (P1-A criterion 1.2):
    i, stamp, track, obj, root (u,v), lpx, maskH, r_gt, z_gt, g_w (GT root, world), T_w_c, foot (u,v,score,kp) or None."""
    S = data.Seq(seq)
    rt = np.load(RTMW[seq])
    by = {}
    for k, f in enumerate(rt['frame']):
        by.setdefault(int(f), []).append(k)
    out = []
    for i in range(S.n):
        rows = S.tracks_at(i)
        if not len(rows):
            continue
        foot = {}
        if i in by:
            ks = by[i]
            kp, sc = rt['kp'][ks], rt['sc'][ks]
            for j, r in asm.associate_dets(rows, kp, sc).items():
                lf = lowest_foot(kp[j], sc[j])
                if lf is not None:
                    foot[int(rows[r][1])] = (lf, kp[j], sc[j])
        t2g = S.assoc_track_to_gt(i)
        lpxs = {}
        if i in by:
            for j, r in asm.associate_dets(rows, kp, sc).items():
                p, s = kp[j], sc[j]
                if s[0] >= CONF and s[19] >= CONF and s[22] >= CONF and all(0 <= p[q, 0] < W and 0 <= p[q, 1] < H for q in (0, 19, 22)):
                    lpxs[int(rows[r][1])] = float(np.linalg.norm(p[0] - 0.5 * (p[19] + p[22])))
        for r in rows:
            t = int(r[1])
            if t not in t2g or r[9] >= 479 or r[7] <= 0:
                continue
            o = t2g[t]
            g = S.root_xyz[o][i]
            if not np.isfinite(g).all():
                continue
            pc = S.T_c_w[i][:3, :3] @ g + S.T_c_w[i][:3, 3]
            if pc[2] <= 0.5:
                continue
            ru, rv = data.root_pixel(r)
            out.append(dict(i=i, stamp=float(S.stamps[i]), track=t, obj=o, root=(float(ru), float(rv)), lpx=lpxs.get(t, 0.0), maskH=float(r[2]),
                            r_gt=float(np.linalg.norm(pc)), z_gt=float(pc[2]), g_w=g.copy(), T_w_c=S.T_w_c[i].copy(),
                            foot=foot[t][0] if t in foot else None))
    return S, out
