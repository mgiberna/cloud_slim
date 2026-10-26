# Cloud task T4: paper skeleton (IEEE RA-L format, LaTeX)

You have no memory of earlier sessions. Inputs in the repository:

- `docs/cloud_tasks/handover.md`: the project handover, exported by Marco;
- `eval/phase9/P9-D/` results and `postcheck_report.md`;
- `docs/cloud_tasks/T1_related_work_report.md`, if present.

No experiment data. **Do not invent numbers.** Every number must come from those files and cite its file; anything missing is a `\TODO{}` placeholder.

## Paper framing (Marco, provisional)

A system-plus-analysis paper: pedestrians inside visual-inertial SLAM, with online pedestrian estimation and no measurable camera cost, plus why pedestrians cannot improve odometry in normal conditions.

## Claims, with their status

Use exactly these, and don't upgrade any.

**Supported (P9-D, pre-registered):**

- H2a: pedestrian velocity beats a per-track Kalman filter;
- H2b: pedestrian position is no worse than per-frame back-projection.

**Caveat:** H2 rests on the best-aligned runs. A post-hoc sensitivity analysis is pending.

**Camera:**

- ratio 1.00 [0.94, 1.06] and 1.07 [0.95, 1.18];
- non-inferior at 10% on one sequence, inconclusive on the other; H1 formally failed;
- worded as "no evidence of degradation".

**Analysis:**

- absorption of camera-relative factors (exact);
- the information-analysis regime (≥ 2 static points per node, so no camera benefit);
- stature unidentifiability (MAP shrinkage);
- the depth-z vs ray-length range erratum;
- the chaotic ORB-SLAM3 spread and its effect on detectable effect sizes.

**Online:** threaded throughput of about 6–7× real time. Latency was not measured.

**Not claimed:**

- camera improvement;
- floor levels (H4 failed; levels go to a follow-up paper);
- real-data pedestrian accuracy.

## Task

Write `docs/paper/main.tex` (IEEEtran journal, RA-L style) and `docs/paper/refs.bib`, containing:

- the section structure: Introduction, Related Work, Method, Analysis (why pedestrians don't help the camera), Experiments, Discussion and Limitations, Conclusion;
- a full Method draft (factors, states, stature, depth-z range, motion prior, footprints, local-BA integration, determinism), from the handover;
- the claims list as a contributions paragraph;
- table and figure placeholders matching P9-E's T1, T2 and F1–F4;
- a Limitations section, with every disclosure from the handover;
- related work from T1, if present.

**Tables:** keep them portrait. Use `adjustbox`, smaller fonts or reduced spacing, never landscape.
