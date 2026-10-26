#!/usr/bin/env python3
"""P9-C3b step 5: apply adoption_rule_C3.md mechanically.
Usage: c3b_rule.py NONE.pkl VAR.pkl NONE_METRICS.json VAR_METRICS.json
  pickles: c3b_eval.py results, key (variant, seq, seed); none = variant `v0`, A + b = `floor_A`, B + b = `floor_B`
  metrics: c3b_runs_metrics.py output, key `<variant>|<seq>|<seed>` with n, speed, dist, contact_n, contact (shares)
Rule (adoption_rule_C3.md, committed c02fa04):
  score r = median flag-on / median B0 camera-frame position error on the same samples (office filter |log s| < 0.2); median over seeds per sequence; mean over sequences.
  (1) median r < none's per-seed minimum r in >= 2 of 3 sequences; (2) violation share (speed > 3 m/s, dist > 30 m, contact height > 0.3 m) <= none's maximum per-seed share,
  every sequence and measure (the candidate's share is pooled over its seeds' states; the max-per-seed reading is printed as a sensitivity check);
  (3) velocity error (median world-frame velocity error, pooled over seeds) <= 110 % of none's in every sequence. Both qualify: lower score; within 0.02: A + b."""
import json, pickle, sys
import numpy as np
SEQS = ['apartment_s1_01h', 'apartment_s1_02h', 'office_s1_12h']
CANDS = {'floor_A': 'A + b', 'floor_B': 'B + b'}
res = pickle.load(open(sys.argv[1], 'rb')); res.update(pickle.load(open(sys.argv[2], 'rb')))
met = json.load(open(sys.argv[3])); met.update(json.load(open(sys.argv[4])))
med = lambda a: float(np.median(a)) if len(a) else float('nan')


def r_of(rr):
    on = {(k, t): c for k, t, c, _ in rr['filtered']['on']['cam']}; b0 = {(k, t): c for k, t, c, _ in rr['filtered']['B0']['cam']}
    ks = sorted(set(on) & set(b0))
    return med([on[k] for k in ks]) / med([b0[k] for k in ks]) if ks else float('nan')


def seeds(v, s):
    return [k for k in range(1, 6) if (v, s, k) in res]


R = {(v, s): [r_of(res[(v, s, k)]) for k in seeds(v, s)] for v in ['v0'] + list(CANDS) for s in SEQS}
vel = lambda v, s: med([x[2] for k in seeds(v, s) for x in res[(v, s, k)]['filtered']['on']['vel']])
MEAS = ('speed', 'dist', 'contact')


def share(v, s, m, how):
    xs = [(met[f'{v}|{s}|{k}'], k) for k in seeds(v, s) if f'{v}|{s}|{k}' in met]
    per = []
    for d, k in xs:
        n = d['contact_n'] if m == 'contact' else d['n']
        if d[m] is not None and n:
            per.append((d[m], n))
    if not per:
        return float('nan')
    if how == 'max':
        return max(p for p, _ in per)
    return sum(p * n for p, n in per) / sum(n for _, n in per)


print('### r per seed (nan = no metric-map samples) and median\n')
print('| candidate | ' + ' | '.join(SEQS) + ' | score (mean of medians) |')
print('|---|---|---|---|---|')
score = {}
for v, lab in [('v0', 'none')] + [(k, CANDS[k]) for k in CANDS]:
    meds = [float(np.nanmedian(R[(v, s)])) for s in SEQS]
    score[v] = float(np.mean(meds))
    print(f'| {lab} | ' + ' | '.join(f'{", ".join("%.3f" % x for x in R[(v, s)])} → **{m:.3f}**' for s, m in zip(SEQS, meds)) + f' | **{score[v]:.3f}** |')
nonemin = {s: float(np.nanmin(R[('v0', s)])) for s in SEQS}
print('\nnone per-seed minimum r:', {s: round(x, 3) for s, x in nonemin.items()})
qual = {}
for v in CANDS:
    c1 = [float(np.nanmedian(R[(v, s)])) < nonemin[s] for s in SEQS]
    print(f'\n### {CANDS[v]}\n(1) median r < none per-seed min: ' + ', '.join(f'{s} {float(np.nanmedian(R[(v, s)])):.3f} vs {nonemin[s]:.3f} -> {"yes" if c else "no"}' for s, c in zip(SEQS, c1)) + f'  => {sum(c1)}/3 {"PASS" if sum(c1) >= 2 else "FAIL"}')
    ok2, ok2b = True, True
    print('(2) violation share vs none max per-seed share (pooled / max-per-seed reading):')
    for s in SEQS:
        for m in MEAS:
            lim = share('v0', s, m, 'max'); a = share(v, s, m, 'pooled'); b = share(v, s, m, 'max')
            f = lambda x: 'nan' if x != x else '%.2f %%' % (100 * x)
            p = (a <= lim + 1e-12) or (a != a and lim == lim and False)
            p2 = (b <= lim + 1e-12)
            if a != a: p = True      # no states: no violation
            if b != b: p2 = True
            ok2 &= p; ok2b &= p2
            print(f'   {s:17s} {m:8s} none max {f(lim):>8s} | {CANDS[v]} pooled {f(a):>8s} {"ok" if p else "ABOVE"} | max/seed {f(b):>8s} {"ok" if p2 else "ABOVE"}')
    print(f'   => (2) {"PASS" if ok2 else "FAIL"} (pooled reading); max-per-seed reading {"PASS" if ok2b else "FAIL"}')
    c3 = [vel(v, s) <= 1.10 * vel('v0', s) for s in SEQS]
    print('(3) velocity error: ' + ', '.join(f'{s} {vel(v, s):.3f} vs none {vel("v0", s):.3f} ({100 * vel(v, s) / vel("v0", s):.0f} %)' for s in SEQS) + f'  => {"PASS" if all(c3) else "FAIL"}')
    qual[v] = (sum(c1) >= 2) and ok2 and all(c3)
    print(f'QUALIFIES: {qual[v]}')
q = [v for v in CANDS if qual[v]]
if not q:
    adopted = 'none'
elif len(q) == 1:
    adopted = q[0]
else:
    adopted = 'floor_A' if abs(score['floor_A'] - score['floor_B']) <= 0.02 else min(q, key=lambda v: score[v])
print('\n## ADOPTED:', 'none' if adopted == 'none' else CANDS[adopted], '| scores', {CANDS.get(k, 'none'): round(x, 3) for k, x in score.items()})
json.dump(dict(adopted=adopted, score=score, qualifies=qual), open('raw/c3b_rule_result.json', 'w'), indent=1)
