# Claude Code task: P9-D post-check (descriptive, existing runs only)

You have no memory of earlier sessions. Context: `eval/phase9/P9-D/` (`criterion.md`, A1, A2, `prerun.md`, and the results report of the frozen `p9d_analyze.py`).

**The frozen verdicts stand and are not recomputed:**

| Family | Hypothesis | Verdict |
|---|---|---|
| Camera | H1 | fails: subway_s1_24h M1 inconclusive |
| Camera | H3 | untested |
| Pedestrian | H2 | holds |
| Pedestrian | H4 | fails |

This task explains four observations. **No new P9-D run. No change to `p9d_analyze.py`.** Any corrected analysis goes in a separate, clearly labelled post-hoc script and section.

## 1. Why only 9–12 of 60 runs per cell contribute pedestrian samples

For each run of the ON and LEV arms (both subway cells, office), report:

- each map's |log s|, Sim(3) residual RMSE, extent and pose count, with its inclusion verdict and the reason for exclusion;
- the number of pedestrian states on included maps;
- the number associated to GT (P2-D association), and the number that reach the metric.

Then state which filter removes most runs.

**Also check** the meaning of the report's column "runs with ped / none included". It reads 12 / 0 while 48 runs have no pedestrian samples. Is the column wrong, or the selection?

**If a defect in `p9d_analyze.py` is found:** describe it with `file:line`. Then compute H2 and H4 quantities with a corrected copy (`p9d_analyze_posthoc.py`), reported **only** as a post-hoc sensitivity, beside the frozen numbers.

## 2. Transitional share 0.000 everywhere

On the LEV runs, check whether contacts are flagged as transitional at all: the counts in `ped_levels.log`, or wherever the flag is logged. Then check whether the analysis reads the right field.

Compare with the tuning rates (4–33%). State whether this is an analysis defect, a logging defect, or real behaviour on the evaluation data.

## 3. Validity of the levels check on multi-level scenes

The alignment-free camera-height check assumes each person stands on the camera's floor level.

Using GT only, for each LEV contact, report whether the GT person is on the camera's GT level: GT root height relative to GT camera height, within ±0.3 m of the expected height difference. Then recompute the camera-height error **only for same-level contacts**, descriptively.

Report subway_s1_36h separately (median −0.53 m; 18% of contacts within 0.10 m).

## 4. office_s1_06h OFF vs Stage 0

Stage 0 (flag off, 20 seeds) gave median coverage 0.156 and 60% exit code 1. The P9-D OFF arm, with nominally the same binary, config and seeds, gave 0.988 and 25%.

Compare, by md5 and full command line:

- binaries and configs;
- staging paths;
- the perception directory path string;
- environment variables.

State the differences. If the only difference is a path string, say so: it is the known layout sensitivity. Report a Fisher test of the exit-code-1 proportions (12/20 vs 5/20) as descriptive.

Also report why office LEV coverage is 0.055: map events per run, and when they occur relative to the first level creation (times only).

## 5. Threaded-mode timing (criterion §6)

One threaded-mode run per arm on subway_s1_24h. Wall-clock and real-time factor only. No metric.

## Report → `eval/phase9/P9-D/postcheck_report.md`

1. **First line:** one verdict per item.
2. Any post-hoc numbers labelled as such.
3. **Stop.**
