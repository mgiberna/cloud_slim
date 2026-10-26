"""T3 test 2: direction of the one-sided tests (H2(a) Wilcoxon, H4 Mann-Whitney, H2(b) bound)."""
import numpy as np
import _paths  # noqa: F401
import p9d_analyze as A
from scipy.stats import wilcoxon, mannwhitneyu


def rec(pos_on, pos_b0, vel_on, vel_b1c):
    return dict(pos=dict(on=pos_on, B0=pos_b0, B1c=1.0, B1r=1.0), vel=dict(on=vel_on, B0=1.0, B1c=vel_b1c, B1r=1.0))


g = np.random.default_rng(3)
for n in (6, 9, 12):
    for vr, pr in ((0.8, 0.9), (1.25, 1.2)):
        runs = [rec(pr * np.exp(g.normal(0, .05)), 1.0, vr * np.exp(g.normal(0, .05)), 1.0) for _ in range(n)]
        h = A.ped_h2(runs)
        print(f"H2 n={n:2d} graph/B1c vel ratio {vr}: p_one={h['a']['p_one']:.4g} pass_a={h['a']['pass']} | graph/B0 pos ratio {pr}: ub95={h['b']['ub95']:.3f} pass_b={h['b']['pass']}")
        assert h['a']['pass'] == (vr < 1) and h['b']['pass'] == (pr < 1)
    # smallest attainable exact one-sided Wilcoxon p (all n log ratios negative) = 2^-n
    print(f'   min exact one-sided Wilcoxon p at n={n}: {wilcoxon(-np.arange(1, n + 1, dtype=float), alternative="less").pvalue:.5f} (2^-n = {2.0 ** -n:.5f})')

for nl, no in ((6, 9), (10, 12)):
    for pr in (0.8, 1.25):
        lev = [rec(pr * np.exp(g.normal(0, .05)), 1, 1, 1) for _ in range(nl)]
        on = [rec(np.exp(g.normal(0, .05)), 1, 1, 1) for _ in range(no)]
        h = A.ped_h4(lev, on)
        print(f"H4 n={nl}/{no} LEV/ON pos ratio {pr}: MW p_one={h['pos']['p_one']:.4g} pass={h['pos']['pass_test']}")
        assert h['pos']['pass_test'] == (pr < 1)
    print(f'   min one-sided MW p at {nl}/{no} (complete separation): {mannwhitneyu(np.arange(nl), np.arange(nl, nl + no), alternative="less").pvalue:.2e}')

# H4 velocity condition: <= 110 % of ON's median
lev = [rec(1, 1, 1.10, 1) for _ in range(5)]; on = [rec(1, 1, 1.0, 1) for _ in range(5)]
print('H4 vel ratio exactly 1.10 ->', A.ped_h4(lev, on)['vel']['pass_cond'])
# fewer than 3 runs -> H2 fails with no quantities (A2.4 asks for point + interval regardless)
print('H2 with 2 runs ->', A.ped_h2([rec(1, 1, .5, 1)] * 2))
print('test_one_sided OK')
