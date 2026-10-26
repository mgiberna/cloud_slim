**Verdicts.** (1) Selection, not extraction: the pre-registered Sim(3) RMSE ≤ 0.5 m map filter removes most subway runs (median map RMSE 1.3–1.4 m); the report column "none included" is an analysis defect (always 0). (2) Analysis defect: transitional share is counted only among assigned contacts, where the flag is 0 by construction; the logger works (3.0–4.8% of contact rows flagged). (3) The levels check is not invalidated by non-level ground (96–98% of GT-associated subway contacts are same-level), but the subway_36h −0.53 m comes from contacts whose track has no GT association (39%, median −0.78 m); same-level-only median −0.10 m. (4) Binary, configs, command lines and staging paths are identical; the only difference is the settings file text (a comment line and the `Pedestrians.Dir` string): known layout sensitivity; exit-1 12/20 vs 5/20, Fisher p = 0.054. Office LEV coverage 0.055 is a single late reset at t ≈ 501–504 s, about 477 s after the first level (t ≈ 24.7–24.8 s). (5) Threaded runs finished; wall-clock 100–122 s for 738 s of sensor data (RTF 0.135–0.165), one run per arm.

Frozen verdicts (H1 fails/inconclusive, H3 untested, H2 holds, H4 fails) are unchanged and were not recomputed. `p9d_analyze.py` (md5 `52e386a2…`) is unchanged. No P9-D run was made; item 5 is the only new run set. All post-check numbers below are descriptive and post hoc. Scripts: `p9d_postcheck_item1.py`, `p9d_postcheck_item3.py`, `p9d_postcheck_item4.py`; data: `results/postcheck/`.

## 1. Why 6–12 of 60 runs contribute pedestrian samples

Inclusion rule (frozen): |log s| < 0.2, Sim(3) camera-centre RMSE ≤ 0.5 m, extent ≥ 2 m, ≥ 50 keyframes; a run contributes if at least one of its maps passes. Per-map detail: `results/postcheck/item1_per_map.csv` (one row per map; 420 rows).

| cell / arm | runs | runs with an included map | maps total | maps failing RMSE | maps failing log s | runs that would be included without the RMSE rule | without the log s rule |
|---|---|---|---|---|---|---|---|
| subway_36h ON | 60 | 9 | 104 | 71 | 50 | 52 | 22 |
| subway_36h LEV | 60 | 6 | 94 | 72 | 36 | 54 | 14 |
| subway_24h ON | 60 | 12 | 85 | 69 | 24 | 53 | 12 |
| subway_24h LEV | 60 | 10 | 79 | 63 | 20 | 54 | 13 |
| office_06h ON | 20 | 12 | 27 | 10 | 14 | 13 | 17 |
| office_06h LEV | 20 | 13 | 31 | 7 | 17 | 14 | 19 |

- Median 1 map per run (1–7 maps). Median per-map RMSE: 1.27–1.44 m on subway, 0.17–0.19 m on office. Subway maps sit at the camera Sim(3) ATE of about 1.35 m, so an RMSE ≤ 0.5 m gate is passed only by the best-aligned runs. **The RMSE filter removes most runs** (every map of 38–47 runs per arm fails it); the log s filter is second (6–8 runs fail it on every map).
- On included maps: 9,257 / 2,497 / 8,514 / 10,117 pedestrian states (36h ON / 36h LEV / 24h ON / 24h LEV); 7,752 / 1,626 / 7,618 / 9,287 of them in GT-associated tracks; 7,416 / 1,461 / 7,585 / 8,882 (n_pos summed over runs) reach the metric after the four-estimator intersection. Every run with an included map reaches the metric (n = 9, 6, 12, 10).
- **Column "runs with ped / none included" is wrong, not the selection.** `_usable()` (`p9d_analyze.py:349`) turns every record without `pos` (including `none_included`) into `None` when records are loaded (`:357`); `descriptives` then counts `none_included` on those `None` values (`:380`, `:385`), so it prints 0. Real counts of runs without an included map: subway_36h 51 ON / 54 LEV, subway_24h 48 / 50, office 8 / 7. The defect is in the descriptive table only; H2 and H4 use only usable records and are unaffected. No corrected H2/H4 sensitivity was computed (no defect reaches them), and `p9d_analyze_posthoc.py` was not created.

## 2. Transitional share 0.000

- Field read: correct (`ped_levels.log` column 8, as the header says). Logger: works. Raw LEV logs, all contact rows: subway_36h 14,029 / 291,969 flagged (4.8%), subway_24h 7,541 / 252,441 (3.0%), office 1,943 / 63,635 (3.1%).
- Defect (`p9d_analyze.py:273`, `:278–280`): rows with level < 0 are skipped before counting; a transitional contact is never assigned to a level, so **0 of the 260,313 / 221,490 / 60,812 assigned rows is flagged**, and the printed share is 0 by construction. The flagged rows are all unassigned (level −1).
- Real behaviour: 3.0–4.8% of contact rows are flagged, at or below the low end of the tuning rates (4–33%). Verdict: analysis (definition) defect in a descriptive column; logging fine.

## 3. Levels check on multi-level scenes (GT only)

Same level = |(z_root − z_cam)_GT − (0.935 − 1.4895)| ≤ 0.3 m, for assigned non-transitional LEV contacts on included maps whose track is GT-associated. The frozen numbers are reproduced (median of per-run medians).

| cell | contacts | GT-associated | same level | other level | not GT-associated |
|---|---|---|---|---|---|
| subway_36h | 1,813 | 1,100 | 1,056 (96%) | 44 | 713 (39%) |
| subway_24h | 7,929 | 7,082 | 6,912 (98%) | 170 | 847 (11%) |
| office | 23,621 | 22,711 | 22,711 (100%) | 0 | 910 |

| cell | frozen (all contacts), median of per-run medians; share ≤ 0.10 m pooled | same-level only (median of per-run medians) | pooled same-level median; share ≤ 0.10 m | other-level pooled median | not-associated pooled median |
|---|---|---|---|---|---|
| subway_36h | −0.532 | −0.098 | −0.098; 49% | −0.92 | −0.78 |
| subway_24h | +0.006 | +0.010 | −0.013; 69% | −1.07 | −0.73 |
| office | −0.030 | −0.030 | −0.008; 85% | n/a | −0.02 |

On subway_36h the six per-run medians go from (−0.11, −0.77, −0.77, −0.39, −0.08, −0.67) to (−0.09, −0.11, −0.12, −0.22, −0.09, −0.04) when restricted to verified same-level contacts. Other-level contacts are only 4% (36h) and 2% (24h) of the associated ones and are always wrong by about 1 m. The large −0.53 m therefore comes mainly from the 39% of contacts that cannot be verified against GT (tracks without a GT association, median −0.78 m): whether those are on other levels cannot be determined from GT here.

## 4. office_s1_06h OFF vs Stage 0

- Compared per seed (k = 1…20), `provenance.txt` of Stage 0 (`p9c2_stage0/stage0_flat`) vs P9-D OFF: binary md5s (runner, library, DBoW2, g2o, vocabulary, `system_params.yaml`), script md5s, command lines (including thread env, `setarch -R`), staging path lengths (41…60), host kernel and commit hashes are identical (0 differing lines in all 20 seeds). The process environment itself is not recorded beyond the command line; both runs were on the same host.
- The only difference is `orb_settings.yaml` (md5 `a30e70a8…` vs `b2b4a9bc…`): one comment line (the C4 base text vs "P9-C5 none = the C4 base…") and the `Pedestrians.Dir` string (`/p9c3c_perception/office_s1_06h` vs `/p9d_perception/office_s1_06h`), inert with `Pedestrians.Enabled: 0`. This is the known layout sensitivity (path/text length).
- Exit code 1: Stage 0 12/20, P9-D OFF 5/20; Fisher exact two-sided p = 0.054 (odds ratio 4.5), one-sided 0.027. Coverage: median 0.156 → 0.988. Per seed the outcomes do not line up (e.g. seeds 1, 3, 7, 9 bad in Stage 0 and fine in P9-D; seeds 2, 5 the reverse).
- Office LEV coverage 0.055: 11 of 20 LEV runs have a reset of the large first map (about 1,640–1,680 keyframes) at sensor time 501.0–502.6 s (a few also have a second tiny map retired at 502.9–504.4 s); the main map is then the post-reset map (coverage ≈ 0.05). Events per run: 9 runs 0, 6 runs 1, 5 runs 2. The first level is created at t = 24.72–24.82 s, so every reset comes about 477 s after the first level. ON has 7/20 and OFF 5/20 runs with a reset of the large map (ON 502.1–502.7 s; OFF 398.5–502.3 s). Times only; no causal attribution made.

## 5. Threaded timing (subway_s1_24h, k-independent, one run per arm, host otherwise idle)

Script: `P9-C5/tools/run_threaded_timing.sh` (a copy of `run_p9c_one.sh` with `System.Deterministic: 0`, default thread env, no `setarch -R`, no jitter). Runner as for the campaign. Wall-clock only; the order was OFF, ON, LEV, run alone in one container.

| arm | wall s | sensor s | wall / sensor | exit |
|---|---|---|---|---|
| off | 117.5 | 738.0 | 0.159 | 0 |
| on | 99.8 | 738.0 | 0.135 | 0 |
| lev | 121.6 | 738.0 | 0.165 | 0 |

For comparison the deterministic campaign medians were 1,317–1,700 s wall (0.43–0.56). The runner admits frames as fast as possible (pacing only when LocalMapping is behind), so these are offline throughput figures, not online latency; N = 1 per arm, so differences between arms (ON fastest) are not interpretable. No metric was computed from these runs.
