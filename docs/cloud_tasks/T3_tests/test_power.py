"""T3 test 6 (observation, not a defect): M1 pass rate under NO true difference at N = 60, margin 1.10 (A2.2 claims ~80 %), lognormal runs, no failures."""
import numpy as np
import _paths  # noqa: F401
import p9d_analyze as A

for sd in (0.15, 0.198, 0.227):
    g = np.random.default_rng(11); R = 300
    p = sum(A.boot_median_ratio(np.exp(g.normal(0, sd, 60)), np.exp(g.normal(0, sd, 60)))['ub95'] < A.M1_MARGIN for _ in range(R))
    print(f'log-sd {sd}: M1 passes in {p}/{R} = {p / R:.2f} of simulated no-effect cells (both cells must pass: ~{(p / R) ** 2:.2f})')
