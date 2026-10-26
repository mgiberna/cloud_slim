#!/usr/bin/env python3
"""P9-C3b step 3: apply the synthetic-gate criteria (fixed by the brief) to the synthetic_floor_contact logs.
 (1) with contacts, A+b and B+b: median absolute range error reduced by >= 70 % relative to `none` for the +-5 % walkers;
 (2) with contacts: median |b_hat - b_true| <= 1 % at every track length (30, 100, 300 keyframes), all walkers;
 (3) without contacts: median |b_hat| at 300 keyframes <= sigma_b (0.0422).
Usage: c3b_gate_eval.py LOG [LOG...]"""
import sys, json
rows = []
for p in sys.argv[1:]:
    for l in open(p):
        if '\t' not in l: continue
        f = l.rstrip('\n').split('\t'); d = {'cand': f[0]}
        for kv in f[1:]:
            k, v = kv.split('=', 1); d[k] = v
        rows.append(d)
def get(c, feet, b, n, seeds=None):
    r = [x for x in rows if x['cand'] == c and int(x['feet']) == feet and abs(float(x['b_true']) - b) < 1e-9 and int(x['NKF']) == n and (seeds is None or int(x['seeds']) == seeds)]
    return r[-1] if r else None
out = []
for seeds in sorted({int(x['seeds']) for x in rows}):
    print(f'--- {seeds} seeds')
    for n in (30, 100, 300):
        for b in (-0.05, 0.0, 0.05):
            no = get('none', 1, b, n, seeds)
            if not no: continue
            for c in ('A+b', 'B+b'):
                r = get(c, 1, b, n, seeds)
                if not r: continue
                red = 1 - float(r['median_abs_range_err_m']) / float(no['median_abs_range_err_m']) if abs(b) > 0 else float('nan')
                be = float(r['median_abs_bhat_err'])
                print(f'N={n:3d} b={b:+.2f} {c}: range-error reduction {red*100:6.1f} %  (abs {no["median_abs_range_err_m"]} -> {r["median_abs_range_err_m"]} m) | median |b_hat-b| {be*100:5.2f} % {"OK" if be <= 0.01 else "ABOVE 1 %"}')
for n in (30, 100, 300):
    for b in (-0.05, 0.0, 0.05):
        r = get('A+b', 0, b, n)
        if r: print(f'no contacts N={n} b={b:+.2f}: median |b_hat| {float(r["median_abs_bhat"]):.4f} (limit 0.0422) {"OK" if float(r["median_abs_bhat"]) <= 0.0422 else "COLLAPSE"}')
