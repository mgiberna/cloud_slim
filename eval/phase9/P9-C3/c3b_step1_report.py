#!/usr/bin/env python3
"""P9-C3b step 1: tables of the frozen configuration + depth-z erratum (flag none), seeds 1-5, from c3b_eval.py's pickle. Usage: c3b_step1_report.py results.pkl [metrics.json]"""
import json, pickle, sys
import numpy as np
res = pickle.load(open(sys.argv[1], 'rb'))
SEQS = ['apartment_s1_01h', 'apartment_s1_02h', 'office_s1_12h']
med = lambda a: float(np.median(a)) if len(a) else float('nan')
def r_of(rr):
    on = {(k, t): c for k, t, c, _ in rr['filtered']['on']['cam']}; b0 = {(k, t): c for k, t, c, _ in rr['filtered']['B0']['cam']}
    ks = sorted(set(on) & set(b0))
    return (med([on[k] for k in ks]) / med([b0[k] for k in ks]), len(ks)) if ks else (float('nan'), 0)
def pooled(seq, m, f, i):
    return [x[i] for k in range(1, 6) if ('v0', seq, k) in res for x in res[('v0', seq, k)]['filtered'][m][f]]
OLD = {'apartment_s1_01h': (0.818, '0.318 / 0.364 / 0.312 / 0.304', '0.304 / 0.376 / 0.312 / 0.299', '0.561 / 1.006 / 0.578 / 0.539'),
       'apartment_s1_02h': (0.969, '0.374 / 0.389 / 0.354 / 0.369', '0.373 / 0.381 / 0.345 / 0.365', '0.328 / 0.624 / 0.338 / 0.340'),
       'office_s1_12h': (0.954, '0.589 / 0.616 / 0.612 / 0.592', '3.241 / 3.240 / 3.343 / 3.426', '0.599 / 1.322 / 0.640 / 0.583')}
print('| sequence | r per seed (nan: no metric map) | median r | 5d median r | camera-frame pos [m] on / B0 / B1c / B1r | 5d | world-frame pos | 5d | velocity [m/s] on / B0 / B1c / B1r | 5d |')
print('|---|---|---|---|---|---|---|---|---|---|')
for s in SEQS:
    rs = [r_of(res[('v0', s, k)])[0] for k in range(1, 6)]
    row = lambda f, i: ' / '.join('%.3f' % med(pooled(s, m, f, i)) for m in ('on', 'B0', 'B1c', 'B1r'))
    n = sum(r_of(res[('v0', s, k)])[1] for k in range(1, 6))
    print(f'| {s} | {", ".join("%.3f" % x for x in rs)} | **{np.nanmedian(rs):.3f}** | {OLD[s][0]} | {row("cam", 2)} | {OLD[s][1]} | {row("world", 2)} | {OLD[s][2]} | {row("vel", 2)} | {OLD[s][3]} |')
print()
print('camera regression check (descriptive): |log s| / ATE Sim(3) [m] / map resets per seed')
for s in SEQS:
    print(s, [(round(res[('v0', s, k)]['cam']['abs_log_scale'], 3), round(res[('v0', s, k)]['cam']['ate_sim3'], 3), res[('v0', s, k)]['cam']['map_reset_count']) for k in range(1, 6)])
