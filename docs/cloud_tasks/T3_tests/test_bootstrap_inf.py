"""T3 test 1: bootstrap upper bounds with +inf, order-statistic quantiles, seed handling (p9d_analyze.boot_median_ratio, pct, camera_test)."""
import math
import numpy as np
import _paths  # noqa: F401
import p9d_analyze as A

INF = math.inf


def show(tag, r):
    print(f"{tag:58s} point={r['point']:.4g} ub95={r['ub95']:.4g} lo95={r['lo95']:.4g} hi95={r['hi95']:.4g}")


# 1. order-statistic indices used by pct() for n = 10000
n = 10000
x = np.arange(n, dtype=float)              # value == 0-based index
for q in (2.5, 95, 97.5):
    print(f'pct q={q}: 0-based index {int(A.pct(x, q))}  (nearest-rank ceil(q n/100)-1 = {math.ceil(q * n / 100) - 1})')
# equals numpy's inverted_cdf (nearest rank) on data with +inf
rng = np.random.default_rng(0)
for _ in range(200):
    m = int(rng.integers(5, 300))
    v = rng.lognormal(0, 1, m)
    v[rng.random(m) < 0.3] = INF
    for q in (2.5, 5, 50, 95, 97.5):
        assert A.pct(v, q) == np.percentile(v, q, method='inverted_cdf'), (m, q)
print('pct == numpy inverted_cdf on 200 random vectors with +inf: OK')

# 2. growing share of ON failures (+inf), N = 60, no true effect on finite runs
base = np.random.default_rng(1)
off = list(np.exp(base.normal(0, 0.2, 60)))
fin = list(np.exp(base.normal(0, 0.2, 60)))
for k in (0, 3, 6, 10, 20, 29, 30):
    on = fin[:60 - k] + [INF] * k
    r = A.boot_median_ratio(on, off)
    show(f'ON with {k:2d}/60 failures (+inf)', r)
    assert np.isfinite(r['point']) == (k < 30)
# exactly half failures -> median of the even-sized sample averages a finite and an inf value -> +inf
assert A.boot_median_ratio(fin[:30] + [INF] * 30, off)['point'] == INF

# 3. OFF median +inf, ON finite -> ratio 0 -> H1 M1 'passes' (edge case, see report)
r = A.boot_median_ratio(fin, fin[:30] + [INF] * 30)
show('OFF with 30/60 failures, ON none', r)
t = A.camera_test([dict(m1=v, event=False) for v in fin], [dict(m1=v, event=False) for v in fin[:30] + [INF] * 30])
print('  camera_test M1 pass =', t['M1']['pass'], 'status =', t['M1']['status'])
assert r['point'] == 0.0 and t['M1']['pass']

# 4. both medians +inf -> inf/inf = nan -> mapped to +inf (conservative)
r = A.boot_median_ratio([INF] * 60, [INF] * 60)
show('both arms all failures', r)
assert r['point'] == INF and r['ub95'] == INF

# 5. None / nan entries become +inf via _finite
r1 = A.boot_median_ratio(fin[:50] + [None] * 10, off)
r2 = A.boot_median_ratio(fin[:50] + [float('nan')] * 10, off)
r3 = A.boot_median_ratio(fin[:50] + [INF] * 10, off)
assert r1 == r2 == r3
print('None, nan and +inf entries give identical results: OK')

# 6. the RNG is re-created per call: identical ON and LEV inputs give identical bounds; ON and OFF use different index draws
r_on = A.boot_median_ratio(fin, off)
r_lev = A.boot_median_ratio(list(fin), off)
assert r_on == r_lev
same = A.boot_median_ratio(off, off)
print(f'arm == OFF data (independent resampling): point {same["point"]:.3f}, 95% two-sided [{same["lo95"]:.3f}, {same["hi95"]:.3f}], ub {same["ub95"]:.3f}')
assert same['point'] == 1.0 and same['lo95'] < 1.0 < same['hi95']

# 7. power check of the design under no effect (A2.2 claims ~80 % at N = 60, margin 1.10), sigma_r/median ~ 0.2 as Stage 0
passes = 0
R = 200
g = np.random.default_rng(7)
for i in range(R):
    a = np.exp(g.normal(0, 0.25, 60)); b = np.exp(g.normal(0, 0.25, 60))
    passes += A.boot_median_ratio(a, b)['ub95'] < A.M1_MARGIN
print(f'no-effect lognormal(sd 0.25) N=60: M1 passes in {passes}/{R} simulated cells')
print('test_bootstrap_inf OK')
