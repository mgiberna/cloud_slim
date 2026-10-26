#!/usr/bin/env python3
"""P9-A minimum detectable effect (criterion.md "Minimum detectable effect")."""
import math

import numpy as np
from scipy.stats import mannwhitneyu

Z = 2.80                                   # (z_{0.975} + z_{0.8}) = 1.96 + 0.84
SHIFTS = (0, 1, 2, 3, 5, 7, 10, 15, 20, 30, 50)    # percent
NS = (5, 10, 20)
REPS = 1000
SEED = 9001
ALPHA = 0.05


def sigma_r(x):
    x = np.asarray(x, float)
    return 1.4826 * float(np.median(np.abs(x - np.median(x))))


def heavy_tail_fraction(x):
    x = np.asarray(x, float)
    return float(np.mean(x > np.median(x) + 3 * sigma_r(x)))


def mde_formula(sig, med, n):
    return Z * sig * math.sqrt(2.0 / n) / med


def n_required(delta, sig, med):
    return 2.0 * (Z * sig / (delta * med)) ** 2


def mwu_p(a, b):
    """Addendum 1 D7."""
    try:
        return float(mannwhitneyu(a, b, alternative="two-sided", method="asymptotic", use_continuity=True).pvalue)
    except ValueError:                    # all values identical -> scipy raises; no evidence of a difference
        return 1.0


def detection_rate(values, n, shift_pct, rng, reps=REPS):
    v = np.asarray(values, float)
    hits = 0
    f = 1.0 + shift_pct / 100.0
    for _ in range(reps):
        a = v[rng.integers(0, len(v), n)]
        b = v[rng.integers(0, len(v), n)] * f
        if mwu_p(a, b) < ALPHA:
            hits += 1
    return hits / reps


def empirical(values, n, group_index, n_index, reps=REPS):
    """-> (rates {shift: rate}, mde_pct or None). Each (group, n, shift) has its own stream: default_rng([SEED, g, n_index, s_index])."""
    rates = {}
    for si, s in enumerate(SHIFTS):
        rng = np.random.default_rng([SEED, group_index, n_index, si])
        rates[s] = detection_rate(values, n, s, rng, reps)
    mde = next((s for s in SHIFTS if rates[s] >= 0.8), None)
    return rates, mde


# ---- Addendum 3: additive shift model ----
SHIFTS_A3 = (0, 1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100)


def detection_rate_add(values, n, frac, rng, reps=REPS):
    """Arm B gets + frac * median(values) (Addendum 3 A3.1)."""
    v = np.asarray(values, float)
    d = frac * float(np.median(v))
    hits = 0
    for _ in range(reps):
        a = v[rng.integers(0, len(v), n)]
        b = v[rng.integers(0, len(v), n)] + d
        if mwu_p(a, b) < ALPHA:
            hits += 1
    return hits / reps


def empirical_add(values, n, group_index, n_index, reps=REPS):
    rates = {}
    for si, s in enumerate(SHIFTS_A3):
        rng = np.random.default_rng([SEED, group_index, n_index, si, 3])
        rates[s] = detection_rate_add(values, n, s / 100.0, rng, reps)
    return rates, next((s for s in SHIFTS_A3 if rates[s] >= 0.8), None)
