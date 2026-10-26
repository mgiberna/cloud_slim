# P9-D addendum A2 (Marco, 23 Oct 2026; committed before any P9-D run)

Applies to `eval/phase9/P9-D/criterion.md` (b7aa79f), together with A1. It supersedes the corresponding parts of criterion sections 3, 5 and 10.

**Why.** Compute is cut from about 8–9 days to about 2 days on one workstation, a deliberate decision by Marco. Margins and the test structure are adjusted to what the reduced N can resolve, so that a weak camera test cannot block the other claims.

## A2.1 N (replaces section 3, confirmatory part)

**N = 60 seeds per arm**, for both subway_s1_36h and subway_s1_24h. The seeds are k = 1…60, the same for all arms. office_s1_06h is unchanged: 20 per arm, descriptive only.

## A2.2 Margins (replace the margins in section 5)

The margins correspond to N = 60 at about 80% power under no true difference, from Stage 0's σ_r/median:

- **M1, SE(3) ATE:** the one-sided 95% upper bound of median(arm) / median(OFF) must be < **1.10**.
- **M2, map-event rate:** the one-sided 95% upper bound of the difference, arm − OFF, must be < **+0.20**.
- **H2(b), pedestrian position non-inferiority, graph vs B0:** the upper bound must be < **1.05**. This is unchanged, because the comparison is paired within runs.

## A2.3 Structure (replaces "fixed sequence … stop at the first that fails" in section 5)

There are two independent families, each tested as a fixed sequence at one-sided α = 0.05, stopping within the family at its first failure:

- **Camera family:** H1 (ON vs OFF), then H3 (LEV vs OFF).
- **Pedestrian family:** H2 (ON: velocity vs B1-causal, and position vs B0), then H4 (LEV vs ON).

A failure in one family does not stop the other. Each hypothesis must still hold in both subway cells.

## A2.4 Reporting (added to section 6)

Every hypothesis quantity is reported per cell with its point estimate and its two-sided 95% interval (the same bootstrap and test machinery), whether or not the hypothesis passes. A camera hypothesis whose bound misses the margin is reported as **inconclusive at that margin**, with its interval. It is not reported as "degradation" unless its lower bound exceeds 1.0 (for M1), or 0 (for M2).

## A2.5 Compute (replaces section 10)

About 420 runs:

- subway: 60 × 3 arms × 2 cells = 360;
- office: 20 × 3 arms = 60.

That is roughly 2 days of wall time on workstation-1 at 3 concurrent subway jobs.

## A2.6 Disclosure

The paper states that N and the margins were reduced from the Stage 0 plan (a 5% margin, N of 260 and 200) for compute reasons, before any P9-D data.
