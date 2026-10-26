**7 discrepancies affect hypothesis quantities (H1–H4), and 7 affect descriptive quantities only. 2 of the descriptive ones are the defects already in `postcheck_report.md`; 12 are new.** None of them reverses a frozen verdict on the evidence available here, but H-1, H-2 and H-3 can change a hypothesis input without any visible sign.

# T3: independent audit of the P9-D analysis code

## Scope and method

- **Repository snapshot:** `mgiberna/cloud_slim` (a slim snapshot of `object_motion_estimator`: P9 analysis code, docs and import closure, commit 854a4bb). It contains `eval/phase9/P9-D/` but no `p9d_analyze_posthoc.py`; the post-check report confirms that file was never created.
- **No experiment data.** Everything below comes from reading the code against `criterion.md`, A1 and A2, and from synthetic inputs run through the frozen functions.
- **Packages:** numpy was present. scipy 1.18.1 and evo were installed with pip; the network allowed it.
- **Read-only:** no existing file was changed. The tests are in `docs/cloud_tasks/T3_tests/` (`run_all.sh`; the output is in `run_all_output.txt`).
- **Code actually exercised:** `p9d_analyze.py` imports `c3b_ped_error.py` (P9-C3), `c5_eval.py` and `c5_b1.py` (P9-C5, which wraps `c3b_b1.py`), and `p9b_collect.py` → `p9b_ate.py` → `p9a_ate.py`.
  - `c3b_eval.py` and `c3b_runs_metrics.py` are **not** imported by the P9-D path. `c5_eval.py` is its successor.
  - `c3b_runs_metrics.py` is relevant only because it defines the earlier plausibility shares (see D-7).
- **Not available, so not checked:** the configs `P9-C5/config/variants/{none,levels}.yaml`, `p9c2_plausibility.py`, `campaign_p9d.py`, and the C++ log writers (`ped_log.txt`, `ped_levels.log`, `keyframes_exact.txt`).

Line numbers refer to `eval/phase9/P9-D/p9d_analyze.py` unless another file is named.

## 1. Quantity-by-quantity check

| Quantity | Spec | Code | Verdict |
|---|---|---|---|
| **Inclusion** | per map: \|log ŝ\| < 0.2, Sim(3) camera-centre RMSE ≤ 0.5 m, extent ≥ 2 m, ≥ 50 poses | `_incl_maps` :193–203. Umeyama of the map's keyframe centres to the interpolated GT camera centres; extent = bounding-box diagonal; poses = keyframes | Thresholds and strictness are correct (test 5.2: \|log s\| 0.1999 in / 0.2001 out, RMSE 0.492 in / 0.536 out, 49 vs 50 keyframes, 1.78 vs 2.14 m). Umeyama is correct (exact recovery of s, R, t). Population issues: H-3, H-4, H-5, D-3 |
| **M1, SE(3) ATE of the main map** | P9-B `run_record`; no main-map metric = +∞ | :186–187 uses `ate_se3` if `ok` else +∞; NaN/None become +∞ (`_finite`) | Matches P9-B. Main map = surviving map covering the most GT stamps, ties to the lowest map id; retired maps are excluded (test 4). See note N-1 |
| **Sim(3) ATE, \|log ŝ\|, coverage, scale failure, exit 1** (secondary) | per arm and cell | :377–384, over `ok` runs only | D-5 |
| **M2, map event** | ≥ 1 reset or new map; a crash counts as an event | :186 `losses_resets + losses_new_maps ≥ 1`; only the `crashed_final.txt` / no-`md5.txt` marker sets `event=True` | H-1 |
| **Bootstrap** | percentile, over runs, 10,000 resamples, seed 9101, failures = +∞ | :59–79. Arm and OFF resampled independently from one `default_rng(9101)` re-created per quantity; order-statistic quantiles; nan (inf/inf) → +∞ | Correct (test 1). `pct` equals numpy `inverted_cdf` (nearest rank) on 200 random vectors containing +∞; the indices for q = 2.5, 95 and 97.5 are 249, 9499 and 9749. ON and LEV get identical index draws (same seed): harmless. Pairing by seed k is ignored (a declared choice in `prerun.md`). Edge cases: N-2 |
| **Newcombe interval** | hybrid score, one-sided 95 % upper bound of arm − OFF | :82–105, Wilson with z = 1.645 for the one-sided bound and 1.96 for the two-sided interval | Correct. All 6 published cases of Newcombe (1998), Table II, reproduced to 4 decimals (test 3). The direction is arm − OFF |
| **Wilcoxon, H2(a)** | log(graph / B1-causal) < 0, one-sided, over runs with samples | :120–136, `wilcoxon(x, alternative='less')` | Direction correct (test 2: ratio 0.8 → p = 2⁻ⁿ, pass; 1.25 → p = 1, fail). Exact for n ≤ 50, so the minimum p at n = 6 is 0.0156: enough |
| **Mann–Whitney, H4** | LEV < ON on the per-run median camera-frame position error, one-sided | :150, `mannwhitneyu(pl, po, alternative='less')` | Direction correct (test 2). The velocity condition, median ratio ≤ 1.10, is correct (exactly 1.10 passes) |
| **H2(b)** | one-sided 95 % upper bound of the median per-run graph / B0 ratio < 1.05 | :137–139, `boot_median` of the per-run ratios | Correct |
| **Fixed sequences, A2.3** | two families; stop within a family at the first failure; both cells | :168–177 | Correct when both cells are present (H-6 otherwise) |
| **A2.4 statuses** | "inconclusive at margin" unless lo95 > 1 (M1) or > 0 (M2) | :115–116 | Correct (test 3: M2 0.40 → degradation). Missing quantities when n < 3: H-7 |
| **Pedestrian association (P2-D)** and per-map Sim(3) | world frame by P2-D, per map; primary metric in the camera frame | `c3b_ped_error.associate` per estimator, per (track, map) group; Sim(3) chosen per state by `sim_of` | H-2, H-5 |
| **Intersection of the four estimators** | "graph, B0, B1-causal, B1-RTS, all on the same (keyframe, track) samples" | :237–243; position and velocity keys intersected separately | Correct as key sets, but see H-2 (the GT person can differ) and H-3 |
| **Velocity** | median world-frame velocity error | `velocity_rows`: 3-D \|s R v − v_GT\|; GT slope over ±0.6 s (≥ 8 samples); B0 central difference with neighbours ≤ 0.3 s | Matches the P9-C2 5b.4 definition. B0's availability gates the whole velocity intersection (H-3, N-4) |
| **Plausibility shares** | speed > 3 m/s, distance > 30 m, contact residual | :245–254, :290–303 | D-6, D-7 |
| **Levels descriptives** | camera-height check, coverage, transitional share, per-track b | :262–304, :255–258 | D-2 (known), D-4, N-5 |

## 2. Discrepancies

### Affecting hypothesis quantities

| # | Location | Spec says | Code does | Affects | Severity |
|---|---|---|---|---|---|
| **H-1** | `p9d_analyze.py:184–187`; `p9b_collect.py:39–42`; `p9b_ate.py:72–73` | §8: a run that fails after its retry counts as +∞ for M1 **and a map event** for M2 | Only the crash marker (in `crashed_final.txt`, or no `md5.txt`) sets `event=True`. A run directory that has `md5.txt` but no `run_summary.json` (the runner aborted; `p9b_collect` calls it a "runner crash") gets `ok=False` and no loss counts, so M1 = +∞ but **event = False**. Likewise, an `ok` run whose `run.log` is missing gets loss counts of `None`, read as 0, so no event (test 5.5) | H1/H3 M2 (understates the event rate of the arm that crashes more); the map-event rate descriptive | **Medium**: it depends on whether `campaign_p9d.py` writes `md5.txt` for aborted runs (not in the snapshot). Check `crashed_final.txt` against runs with `ok=False` and `reason` beginning "runner crash" |
| **H-2** | `:230–238` (`E.associate` called once per estimator) | §4: all four estimators "on the same (keyframe, track) samples", with P2-D association | Each estimator associates its own estimates to GT. The intersection guarantees the same **keys**, not the same **GT person**: a track can be matched to person A by the graph and to person B by B0, and then both errors enter the per-run medians against different references. A track any estimator fails to match (median > 5 m) leaves the sample for all four. Test 5.3: graph → A, error 0.00; B0 1.6 m off → matched to **B**, reported error 0.40 m instead of 1.60 m; B0 6 m off → unmatched, track dropped for all four | H2(a), H2(b), H4 (the sample population and the reference); B1-RTS and the medians in the descriptives | **Medium**: inherited from frozen `c5_eval` and plausibly rare, but it biases precisely the noisy baselines (B0) towards lower error in crowds, and silently removes the hardest tracks |
| **H-3** | `:239–240` | §4: per-run position and velocity medians; only the inclusion rule removes runs | `if not kp or not kv: return no_samples`. A run with position samples but an **empty velocity intersection** is dropped from H2(b) and H4 position as well. B0 velocity exists only where the track's neighbouring keyframes are ≤ 0.3 s apart (test 5.4: spacing 0.4 s → 0 B0 velocity rows, 29 position rows), so B0's keyframe density decides whether a run enters the position hypotheses. Such runs are then counted nowhere (D-3) | H2(b), H4 (run population) | **Low–medium**: the post-check found every run with an included map reaching the metric, so the frozen results are unaffected. It is a latent coupling |
| **H-4** | `:341` | §4: a run contributes pedestrian samples iff it has an included map | The pedestrian record is computed only if the camera record is `ok` (main map with ≥ 20 matched poses). A run whose main map fails the matched-pose minimum but which has another map passing inclusion is excluded | H2, H4 (run population) | **Low**: a map with ≥ 50 keyframes almost always has more covered GT stamps than a map with < 20 matches, so it would be the main map |
| **H-5** | `c3b_ped_error.py:129–131` (`sim_of`), used at `:228`, `:247`, `:275`, `:297`; `c5_eval.py:59` | §4 inclusion and per-map Sim(3): a state belongs to its own map | `ped_log.txt` rows carry no map id. Each state is given the map whose [t₀ − 1 s, t₁ + 1 s] window contains it, nearest by **midpoint**. After a reset at t = 500 s with a new map from 500.5 s, states written in the old map at 499.5–500 s are assigned to the new map (test 5.1). States of a map dropped for < 20 keyframes (`c3b_ped_error.py:95,99`) borrow a neighbour's Sim(3) within 1 s. Consequences: the wrong Sim(3) for world velocity, a wrong inclusion verdict, and B1 segments (`c5_eval.py:67`, keyed by `id(S)`) that mix rows from two world frames. `ped_levels.log` rows do carry the map id (x[0]), but `_levels_descr` ignores it | H2(a) and H4 velocity; B1 inputs; inclusion membership (all pedestrian quantities); levels camera-height check | **Low**: ≤ 1 s per map boundary. Subway runs have a median of 1 map but up to 7 |
| **H-6** | `:161`, `:173`, `:447` | §5 / A2.3: each hypothesis must hold in **both** subway cells | `cells` = the subway cells *present* in `OUT`. If one `records_<seq>.json` is missing, a hypothesis "holds in every cell" on a single cell | All hypotheses (procedure) | **Low**: procedural. It does not apply to the frozen report, which has both cells |
| **H-7** | `:131–132`, `:146–147`, `:419–420`, `:425–426` | A2.4: every hypothesis quantity is reported per cell with its point estimate and two-sided 95 % interval, *whether or not it passes* | With < 3 runs with samples, H2/H4 return only a note, and no point or interval is reported | Reporting of H2/H4 | **Low**: it did not trigger (n = 6–12). Notable because the RMSE clause brought n close to this floor (LEV 36h: n = 6) |

### Affecting descriptive quantities only

| # | Location | Spec says | Code does | Severity |
|---|---|---|---|---|
| **D-1** (known) | `:349–357`, `:380–385` | §4: report per arm the number of runs with no included map | `_usable` turns every record without `pos` into `None` at load time, so the `none_included` count is always 0 (reproduced, test 5.6) | Medium (already documented) |
| **D-2** (known) | `:273`, `:278–281` | §6: transitional share | Rows with level < 0 are skipped before counting. Transitional contacts are always unassigned (−1), so the share is 0 by construction (reproduced, test 5.7: 0.0 vs a true 0.5) | Medium (already documented) |
| **D-3** | `:239–240`, `:341`, `:385` | §4: "A run with no included map contributes no pedestrian sample. The number of such runs is reported per arm." | Even with D-1 fixed, the count covers only `none_included`. Runs with included maps but an empty intersection (`no_samples`, H-3), runs not `ok` (H-4), runs without `ped_log.txt`, and crashed runs all fall out silently. `n_with_ped` + `n_no_included_map` ≠ `n_runs`, and nothing reports the rest | Low–medium |
| **D-4** | `:222`, `:257–258` (with `c5_eval.py:21–37`) | §6 per-track b on the evaluated (included) maps; `c5_eval` stored each b with its map's \|log s\| for this filtering | `read_levels_log` returns b for **every** (map, track), including excluded and wrong-scale maps, and `rec['b']` summarises all of them | Low |
| **D-5** | `:377–384` | §6: secondary metrics per arm: exit code 1, scale failure, runtime / RTF | Exit-1 rate, scale-failure rate, wall time and RTF are computed over `ok` runs only. A run with exit 1 but no main-map metric leaves numerator and denominator (test 5.6: 0.33 reported vs 2/4 = 0.50) | Low |
| **D-6** | `:252–253` | §6: distance > 30 m (metres) | Speed is scaled by the map's s (`|v| s > 3`), but distance is not (`|T_cw p| > 30` in map units). On included maps (\|log s\| < 0.2) the threshold is effectively 24.6–36.6 m | Low |
| **D-7** | `:290–303` (vs `P9-C3/c3b_runs_metrics.py:176–179`) | §6 "contact residual" plausibility share; P9-C3 defined it as the share of states whose foot-ray point is > 0.3 m from the **GT floor** | P9-D computes a different quantity: the share of `ped_floor_px.log` rows with max(\|r_u\|/6, \|r_v\|/3) > 5. The σ (6, 3 px) and the 5σ threshold are hard-coded, not read from `levels.yaml` (not available, so a match cannot be checked). It is LEV only, and its definition is not listed among "decisions the script fixes" in `prerun.md` §4 | Low |

## 3. Synthetic tests (`docs/cloud_tasks/T3_tests/`, all pass)

**Test 1 (`test_bootstrap_inf.py`): bootstrap upper bound with +∞, N = 60, no true effect on the finite runs.**

| ON failures (+∞) | point | ub95 | two-sided 95 % |
|---|---|---|---|
| 0 | 1.003 | 1.068 | 0.948–1.082 |
| 6 | 1.036 | 1.095 | 0.962–1.108 |
| 10 | 1.048 | 1.118 | 0.976–1.139 |
| 20 | 1.092 | 1.212 | 1.014–1.234 (degradation) |
| 29 | 1.232 | +∞ | 1.099–+∞ |
| 30 | +∞ | +∞ | 1.099–+∞ |

- +∞ behaves as the worst rank: 30 failures out of 60 make the median +∞, because the even-n midpoint averages a finite value with +∞.
- `None`, NaN and +∞ inputs give identical results.
- When both medians are +∞ the result is +∞ (conservative).
- **Edge case:** OFF with ≥ 50 % failures and ON finite gives ratio 0, so M1 **passes** (N-2).

**Test 2 (`test_one_sided.py`): test directions.**

- H2(a), H2(b) and H4 pass when graph/LEV is better and fail when it is worse, for n = 6–12.
- The minimum exact Wilcoxon p is 2⁻ⁿ.
- H4's velocity condition passes at exactly 1.10.
- With 2 runs, H2 returns no quantities (H-7).

**Test 3 (`test_newcombe.py`):** 6/6 published intervals reproduced. The direction is arm − OFF.

**Test 4 (`test_main_map.py`): main-map choice with retired maps (frozen P9-B code via evo).**

| Case | main map | M1 | event |
|---|---|---|---|
| A: one drifting map, 0–100 s | 0 | 1.089 | no |
| B: drifting map 0–90 s **retired** by a reset; new map 91–100 s survives | 1 (covers 10 % of GT) | **0.012** | yes |
| C: as B, surviving map only 97–100 s (15 keyframes) | 1 | +∞ (ok = False) | yes |
| D: both maps survive (new map, no reset) | 0 | 0.952 | yes |
| E: tie in covered GT stamps (map ids 1 and 3) | 1 (lowest id) | — | — |

**Test 5 (`test_population.py`):** results are cited in H-1–H-5, D-1, D-2, D-5 and N-5.

**Test 6 (`test_power.py`, observation):** M1 pass rate under no true difference at N = 60 and margin 1.10, lognormal runs without failures:

| log-sd | M1 pass rate per cell | both cells |
|---|---|---|
| 0.15 | 0.86 | ≈ 0.73 |
| 0.198 | 0.67 | ≈ 0.44 |
| 0.227 | 0.56 | ≈ 0.31 |

## 4. Notes (code matches the spec, but the result is fragile)

**N-1: retired maps and M1** (test 4).

- M1 follows the frozen P9-B rule: the main map is chosen among maps alive at shutdown.
- A **late reset therefore lowers M1**: the long drifting map is retired, and ATE is computed on the short post-reset map. If that map has < 20 matched poses, M1 becomes +∞ instead.
- So M1 is not monotone in tracking quality. Arms with more late resets (the post-check reports this for office LEV: 11/20 resets at t ≈ 501 s, main-map coverage 0.05) can gain or lose M1 arbitrarily. Only M2 penalises the reset.
- `ate_sim3_incl_retired` (descriptive, P9-B) is the robust alternative, but the P9-D report does not print it.
- Severity for interpretation: **high on office, low on subway**, where the post-check reports a median of 1 map per run.

**N-2: +∞ edge cases.**

- If OFF's median is +∞ and the arm's is finite, the ratio is 0 and H1/H3 M1 pass, with interval [0, ·].
- If the bootstrap medians of OFF are +∞ in more than 2.5 % of resamples, lo95 = 0.
- Neither case is wrong under "worst rank", but both are uninterpretable as ratios. With the frozen data (OFF mostly finite) they did not occur.

**N-3: the power claim of A2.2 is optimistic for a median-ratio bootstrap** (test 6).

- The sample-size formula of §3 is the normal-mean formula. The sample median's variance is about π/2 larger, so the effective N is about 60/1.57 ≈ 38.
- Simulated pass rates under no effect are 0.56–0.67 per cell at log-sd 0.20–0.23, and about 0.3–0.45 for both cells together, not 0.8.
- This matches H1 being "inconclusive at margin" on subway_24h. It is a design property, not a code defect, but should be disclosed with the A2 reduction.

**N-4: populations that change without a visible count.** These are the candidates of the same kind as the RMSE clause and the transitional count:

- **the per-estimator association** (H-2): the hardest tracks leave the sample, and B0 can be scored against the wrong person;
- **B0 velocity availability** (neighbours ≤ 0.3 s) gating the velocity intersection, and through H-3 the position runs;
- **GT gating:** the nearest GT object sample within 0.05 s; a GT velocity needs ≥ 8 GT samples within ±0.6 s; association needs ≥ 5 overlapping samples and a median < 5 m;
- **perception rows:** a missing perception row or l_px ≤ 0 removes the state from B0 and B1, and so from the graph too (intersection);
- **maps with < 20 keyframes** are dropped from `map_segments`, and their states are lost or reassigned (H-5);
- **the camera-ok gate** (H-4) and the **run-count gaps** (D-3);
- **duplicate (keyframe, track) rows:** if `ped_log.txt` or `ped_levels.log` holds more than one write per (keyframe, track), which "last-written" in `c3b_ped_error.py:3` suggests:
  - the dict comprehensions at `:233–236` keep the last write, silently;
  - the association medians and the B1 filter (`c5_eval.py:57–67`) use every write, and the B1 filter applies the same measurement twice at dt = 0;
  - `_levels_descr` counts duplicate contact rows in `used` and `coverage` (test 5.7: coverage 0.75 vs 0.5 for 2 distinct states).

  This could not be checked without a log file. `sort | uniq -d` on columns 1 and 3 of one `ped_log.txt` would settle it;
- **keyframe-id reuse across a reset:** if keyframe ids restart after `ResetActiveMap`, keys (keyframe, track) from the retired and new maps collide in the same dicts. ORB-SLAM3's static `nNextId` normally prevents this, but it is not verified for this build.

**N-5: two GT pipelines.**

- The camera metric uses `<seq>_gt_body.tum` + `gt_summary.json` `T_b_c`, with evo association within 0.02 s.
- Map inclusion and the pedestrian Sim(3) use `<seq>_gt.npz`, with `T_b_c` from its `tf_static` and slerp interpolation.
- They agree only if the two `T_b_c` are the same. Worth one md5/value check.

**N-6: version pinning.** The scipy Wilcoxon and Mann–Whitney defaults (`method='auto'`, tie handling) have changed across versions. The frozen run's scipy version is not recorded in `prerun.md`.

**N-7: not verifiable here.**

- The B0 constant `CL = 0.855387` (`c5_eval.py:14`) should equal `SkeletonOverStature` in `none.yaml` / `levels.yaml`, which B1 and the graph use. The configs are not in the snapshot.
- The `keyframes_exact.txt` columns 3–5 are assumed to be camera centres (twc).
