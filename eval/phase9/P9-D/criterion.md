# P9-D — Evaluation: pedestrians inside ORB-SLAM3's local BA (criterion)

Status: PRE-REGISTERED. Commit on branch `p9d-eval` before any P9-D run. Changes only as dated addenda committed before the data they govern.

## 1. Claims under test

1. Adding the pedestrian layer does not degrade the camera (VIO), within a 5% margin.
2. The pedestrian layer estimates pedestrian **velocity** better than a per-track Kalman filter (B1-causal) on the same measurements. Its **position** is no worse than a per-frame back-projection (B0).
3. Adding floor levels does not degrade the camera, and it improves pedestrian position over the base. (Levels are disclosed as failing earlier gates: the synthetic gate, the shadow check and re-admission rule C. They are included by Marco's explicit decision of 23 Oct 2026.)

## 2. System and arms

**Binary**, frozen:

- `libvs_graphs_lib.so` `1a6b1b3bc3dc4a0b56157c1956b0307b`;
- runner `007ed74e6831364a3e8e6fa1b8fb7bdd`;
- `visual_sgraphs` `p9c5-floor-levels` 9862a18.

Every md5 in `P9-C2/final_binaries.md` is checked before each campaign. A mismatch stops the campaign.

**Arms:** all deterministic mode, mono-inertial, with pedestrian masks applied in every arm.

| Arm | Config |
|---|---|
| OFF | `Pedestrians.Enabled: 0` |
| ON | `P9-C5/config/variants/none.yaml` (C4 base: `FloorContact: none`) |
| LEV | `P9-C5/config/variants/levels.yaml` (`FloorContact: levels`, no platform prior) |

**Seeds:** the P9-B null (jitter seed k, staging path of 40 + k characters), k = 1…N. The **same k values for every arm**.

## 3. Cells

**Confirmatory**, both mono-inertial:

| Cell | N |
|---|---|
| subway_s1_36h | 260 |
| subway_s1_24h | 200 |

N per arm is set from Stage 0's SE(3) σ_r/median (0.227 and 0.198), for a one-sided α of 0.05, power 0.8 and a 5% margin: N = 2 (1.645 + 0.84)² (σ_r / median / 0.05)², rounded up.

**Descriptive only:** office_s1_06h, 20 seeds per arm. Stage 0 gives a median coverage of 0.156, 60% of runs below 50% coverage, and n(5%) of about 12,000. No hypothesis is tested on it.

## 4. Metrics

**Camera** (P9-B definitions, `p9b_collect.run_record`, frozen):

- **M1 (primary):** SE(3) ATE of the main map. A run with no main-map metric counts as +∞, the worst rank.
- **M2 (co-primary):** map-event indicator, meaning ≥ 1 reset or new map in the run.
- **Secondary:** Sim(3) ATE, |log ŝ|, coverage, scale failure (|log ŝ| ≥ 1), exit code 1.

**Pedestrians** (frozen `c3b_ped_error.py`, `c3b_b1.py`, `c3b_eval.py`, P2-D association):

- per run: the median camera-frame position error and the median world-frame velocity error;
- for the graph, B0, B1-causal and B1-RTS, all on the same (keyframe, track) samples.

**Inclusion:** a map counts only if:

- |log ŝ| < 0.2;
- the Sim(3) camera-centre residual RMSE is ≤ 0.5 m;
- the trajectory extent is ≥ 2 m;
- it has ≥ 50 poses.

A run with no included map contributes no pedestrian sample. The number of such runs is reported per arm.

## 5. Hypotheses: fixed sequence, each at one-sided α = 0.05, stop at the first that fails

Each hypothesis must hold in **both** confirmatory cells.

**H1. Camera, ON vs OFF.**

- **M1:** the one-sided 95% upper bound of median(ON) / median(OFF) is < 1.05. Use a percentile bootstrap over runs, 10,000 resamples, seed 9101; failures enter as +∞.
- **M2:** the one-sided 95% upper bound of the difference in map-event rate, ON − OFF, is < +0.10 (Newcombe hybrid score interval).

**H2. Pedestrians, ON.**

- **(a) Velocity:** the per-run log-ratio of graph to B1-causal velocity error is < 0, by a one-sided Wilcoxon signed-rank test over runs with pedestrian samples.
- **(b) Position non-inferiority:** the one-sided 95% upper bound of the median per-run ratio of graph to B0 camera-frame position error is < 1.05 (bootstrap as in H1).

**H3. Camera, LEV vs OFF.** As H1, with LEV in place of ON.

**H4. Levels improve pedestrian position.** The per-run median camera-frame position error is lower for LEV than for ON, by a one-sided Mann–Whitney test over runs with pedestrian samples. In addition, the LEV velocity error must be ≤ 110% of ON's, compared by medians over runs.

## 6. Descriptive outputs (no inference)

Report:

- all secondary metrics per arm and cell;
- office_s1_06h in full;
- the levels found on subway against GT floors (alignment-free camera-height check, coverage, transitional share);
- plausibility shares (speed > 3 m/s, distance > 30 m, contact residual);
- B1-RTS;
- per-track b;
- runtime and real-time factor;
- one threaded-mode run per arm on subway_s1_24h, for wall-clock timing only (the online claim).

## 7. Pre-run requirements (before the first P9-D run)

1. **D1-P with LEV:** subway_s1_24h, `FloorContact: levels`, 5 identical invocations, md5 only. They must be byte-identical.
2. **Analysis script:** `eval/phase9/P9-D/p9d_analyze.py` implements sections 4–6 exactly. It is tested on synthetic run records and on the Stage 0 flag-off records (as OFF and as fake ON). It is committed, and its md5 recorded in `eval/phase9/P9-D/prerun.md`. **No change after the first P9-D run.**
3. **Campaign script:** run order is interleaved across arms by seed (k = 1: OFF, ON, LEV; k = 2: …), so that host drift affects all arms equally.

## 8. Run handling

- A run that crashes (no outputs) is retried once, with the same seed and path. If it fails again, it counts as a failure (+∞ for M1, a map event for M2, no pedestrian sample).
- Exit code 1 is not a crash.
- No result is computed or looked at until every run of a cell is complete. The analysis runs once per cell, with the frozen script.

## 9. Disclosures, carried into the paper

- **Tuning:** on apartment_s1_01h, apartment_s1_02h and office_s1_12h only. The one evaluation-sequence pair seen in P9-C is disclosed.
- **Levels' history:** the failed synthetic gate (S6 spread), the failed shadow check, failed re-admission rule C, and two overrides by Marco.
- **office_s1_06h:** descriptive only, because of Stage 0. Its mono-inertial initialisation fails with stock ORB-SLAM3 parameters.
- **Deterministic mode is not stock ORB-SLAM3.** Three vanilla uninitialised-read contexts remain.
- **The terrain:** the subway sequences are multi-level (the camera changes height by about 6 m, and about 16–18% of pedestrian samples are on non-level ground).

## 10. Compute (estimate)

About 1,440 runs:

- subway: (260 + 200) × 3 arms;
- office: 20 × 3 arms.

Subway runs take about 1,300–1,600 s each, and at most 3 run concurrently (about 12.5 GB of RAM each). That's about 8–9 days of wall time on one workstation, or proportionally less with additional identical hosts. Identical binaries and container images are required on every host.
</document_content></document>


</documents>

<document index="31" media_type="text/plain"><document_content>(see above)</document_content></document>
</documents>
</document_content>
</document>
</documents>
