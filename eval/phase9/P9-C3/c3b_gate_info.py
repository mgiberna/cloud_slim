#!/usr/bin/env python3
"""P9-C3b gate erratum (gate_erratum.md): criterion (2) restated against the information bound.
Cell: observed median |b_hat-b_true| <= 1.2 m* + |shrinkage|, m* = 0.674 sigma_post (I, the verdict); error not increasing with track length.
Usage: c3b_gate_info.py LOG"""
import sys
SB = 0.0422
rows = []
for l in open(sys.argv[1]):
    if '\t' not in l: continue
    f = l.rstrip('\n').split('\t'); d = {'cand': f[0]}
    for kv in f[1:]:
        k, v = kv.split('=', 1); d[k] = v
    rows.append(d)
cells = {}
for r in rows:
    cells[(r['cand'], float(r['b_true']), int(r['NKF']))] = r
ok_all = True
print('| cand | b_true | NKF | observed [%] | sigma_post I [%] | m*(I) [%] | shrinkage [%] | bound (I) [%] | verdict (I) | sigma II [%] | bound (II) | (II) | sigma III [%] | bound (III) | (III) |')
print('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
res = {}
for (c, b, n), r in sorted(cells.items()):
    obs = float(r['median_abs_bhat_err'])
    line = f'| {c} | {b:+.2f} | {n} | {obs*100:.2f} '
    for key in ('I', 'II', 'III'):
        s = float(r['sigb_post_' + key]); m = 0.674 * s; sh = abs(b) * s * s / SB ** 2; bound = 1.2 * m + sh
        ok = obs <= bound
        if key == 'I':
            ok_all &= ok
            line += f'| {s*100:.3f} | {m*100:.3f} | {sh*100:.3f} | {bound*100:.3f} | {"ok" if ok else "ABOVE"} '
        else:
            line += f'| {s*100:.3f} | {bound*100:.3f} | {"ok" if ok else "ABOVE"} '
        res[(c, b, n, key)] = ok
    print(line + '|')
print()
mono = True
for c in ('A+b', 'B+b'):
    for b in (-0.05, 0.0, 0.05):
        e = [float(cells[(c, b, n)]['median_abs_bhat_err']) for n in (30, 100, 300)]
        inc = e[1] > e[0] or e[2] > e[1]
        mono &= not inc
        print(f'{c} b={b:+.2f}: observed 30/100/300 = {e[0]*100:.2f} / {e[1]*100:.2f} / {e[2]*100:.2f} %  {"INCREASES" if inc else "non-increasing"}')
for key in ('I', 'II', 'III'):
    n_ok = sum(v for k, v in res.items() if k[3] == key)
    print(f'bound ({key}): {n_ok}/18 cells ok')
print('\nCRITERION (2) restated: (a) every cell within the bound (I):', 'PASS' if ok_all else 'FAIL', '| (b) not increasing with length:', 'PASS' if mono else 'FAIL')
