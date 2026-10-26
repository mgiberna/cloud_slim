# Cloud task T3: independent audit of the evaluation/analysis code (read-only)

You have no memory of earlier sessions. Repository: `object_motion_estimator`, branch `p9e-eval`, or the newest branch containing `eval/phase9/P9-D/`. **Read-only:** do not change any existing script. Write only your report and, if useful, small standalone test scripts under `docs/cloud_tasks/T3_tests/`. No experiment data is available. Reason from the code, the specifications and synthetic inputs you construct.

## Specifications (what the code is supposed to compute)

- `eval/phase9/P9-D/criterion.md`, `addendum_A1.md`, `addendum_A2.md`;
- `eval/phase9/P9-D/postcheck_report.md`, which lists the two defects already found.

## Code to audit

- `eval/phase9/P9-D/p9d_analyze.py`, and `p9d_analyze_posthoc.py` if present;
- the scripts they import, in particular `eval/phase9/P9-C3/c3b_ped_error.py`, `c3b_b1.py`, `c3b_runs_metrics.py`, `c3b_eval.py`, and the P9-B metric code (`p9b_collect.run_record`).

## Task

1. **Check every quantity against its definition in the criterion and its addenda.** Covering:
   - inclusion;
   - SE(3) and Sim(3) ATE and main-map selection;
   - map events;
   - the bootstrap: independence, seeds, order-statistic quantiles, +∞ handling;
   - the Newcombe interval;
   - Wilcoxon and Mann–Whitney: direction, one-sided;
   - the pedestrian association (P2-D), per-map Sim(3), and the intersection of the four estimators' samples;
   - velocity definition;
   - plausibility shares;
   - levels descriptives.
2. **List every discrepancy** with `file:line`, what the spec says, what the code does, which reported quantities it affects (hypothesis or descriptive), and severity.
3. **Build synthetic test cases** for the riskiest computations (bootstrap upper bounds with +∞, one-sided test direction, main-map choice with retired maps) and report their results.
4. **Note anything** that could silently change a pedestrian sample population, as the RMSE clause and the transitional count did.

## Output

`docs/cloud_tasks/T3_audit_report.md`. The first line states the number of discrepancies affecting hypotheses and the number affecting descriptives.
