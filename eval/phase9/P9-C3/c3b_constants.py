#!/usr/bin/env python3
"""P9-C3b step 1: refit c_L under the depth-z model (P1-B method of constants.md: L_skel = median over (image, GT pedestrian) rows with a nose->heel length of
z_GT * l_px / f -- z_GT, the camera-frame z of the GT root, replaces the Euclidean range r_GT; c_L = L_skel / 1.70) and measure the across-track spread sigma_b of
the per-track median log-range residual rho = log(f c_L H0 / l_px) - log z_GT (tracks with >= 10 rows, 1.4826 MAD), its dependence on the image column.
Rows: c3_common.sequence_rows pickles (the 5b population: 410 / 124 / 8206 rows with l_px). Tuning sequences only.
Usage: c3b_constants.py ROWS_DIR OUT.json"""
import json, pickle, sys
import numpy as np
from scipy import stats
import c3_common as c

rows = []
for s in c.TUNE:
    for r in pickle.load(open(f'{sys.argv[1]}/rows_{s}.pkl', 'rb')):
        if r['lpx'] > 0:
            r['seq'] = s
            rows.append(r)
z = np.array([r['z_gt'] for r in rows]); rg = np.array([r['r_gt'] for r in rows]); lp = np.array([r['lpx'] for r in rows])
Lz, Lr = float(np.median(z * lp / c.F)), float(np.median(rg * lp / c.F))
cLz = Lz / c.H0
out = dict(n_rows=len(rows), L_skel_z=Lz, c_L_z=cLz, L_skel_r_check=Lr, c_L_r_check=Lr / c.H0, c_L_old=c.CL,
           per_sequence_L_z={s: float(np.median([r['z_gt'] * r['lpx'] / c.F for r in rows if r['seq'] == s])) for s in c.TUNE})
for name, cl, dist in (('z_refit', cLz, z), ('z_old_cL', c.CL, z), ('r_old_cL', c.CL, rg)):
    tr = {}
    for r, d in zip(rows, dist):
        tr.setdefault((r['seq'], r['track']), []).append((np.log(c.F * cl * c.H0 / r['lpx']) - np.log(d), abs(r['root'][0] - c.CX)))
    good = {k: v for k, v in tr.items() if len(v) >= 10}
    med = np.array([np.median([a for a, _ in v]) for v in good.values()])
    u = np.array([np.median([b for _, b in v]) for v in good.values()])
    within = np.concatenate([np.array([a for a, _ in v]) - np.median([a for a, _ in v]) for v in good.values()])
    out[name] = dict(n_tracks=len(good), spread_track_medians=float(c.mad(med)), mean_track_medians=float(med.mean()), within_track_sigma=float(c.mad(within)),
                     spearman_vs_abs_u=float(stats.spearmanr(med, u)[0]), p=float(stats.spearmanr(med, u)[1]))
out['sigma_b'] = out['z_refit']['spread_track_medians']
# range-consistency gate constants under the z model (the gate is OFF in v0, GateK 0; kept consistent): H_mask,z = median(z_GT mask_h / f); d = log z_lpx - log z_mask
mh = np.array([r['maskH'] for r in rows])
Hm = float(np.median(z * mh / c.F))
d = np.log(c.F * cLz * c.H0 / lp) - np.log(c.F * Hm / mh)
out['gate_z'] = dict(H_mask_z=Hm, d0=float(np.median(d)), sigma_d=float(c.mad(d)))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print(json.dumps(out, indent=1))
