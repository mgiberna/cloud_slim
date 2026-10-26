# P9-D pre-run record (criterion §7, addenda A1, A2) — 23 Oct 2026

Status: all pre-run requirements done. **No P9-D run has been made.** Next: campaign (`campaign_p9d.py`), on Marco's go.

## 1. Foot (F) rows for the evaluation sequences (A1.2)

Perception directory of the levels runs on the tuning sequences: `p9c3c_perception` (default of `P9-C5/tools/run_p9c_one.sh`). Its F rows were made by `P9-C4/c3c_add_mid.py` (midpoint of the left and right foot's lowest valid keypoint) from `p9c2_perception` and the RTMW detections.
Scripts and inputs (md5, recorded **before** generation):

| item | md5 |
|---|---|
| `P9-C4/c3c_add_mid.py` | 7f2feebc1eed6562958a9996254c57c3 |
| `P9-C3/c3_common.py` | 422710e3ee1009feb76bd0503868e8db |
| `P9-C2/perception/p9c_assemble.py` | a84b0eb792283e689e590ccc3b885fba |
| `P9-C2/constants.json` | fe5412d9623486840e6c61733ec85ffd |
| stance_foot_poc `p4s1/data.py` (commit 455f9b59774c2859957d49ab10767e112d9047cd) | e6d62119c85368681bf18ce6ec6a7553 |
| RTMW detections subway_s1_36h / subway_s1_24h / office_s1_06h | 7f7d85c2… / d5531926… / 4f26829b… (equal to the `rtmw` md5 in the p9c2 manifests) |
| P1-A tracks subway_36h / subway_24h / office_06h | a31eab18… / 953af244… / 618b81ce… (24h equals the p9c2 manifest) |

No model weights are involved: the keypoints are read from the stored RTMW detection files (no inference).
**Reproduction check (tuning sequence, allowed):** the same script, same arguments, on apartment_s1_01h reproduced `p9c3c_perception/apartment_s1_01h` byte for byte (`diff -r` empty, 132 F rows).

Generation: `c3c_add_mid.py SEQ p9c_perception_work/p1a RTMW_NPZ p9c2_perception p9d_perception`, run from `stance_foot_poc` with its `.venv`. Output `p9d_perception/<seq>/`.

**P and C rows unchanged:** the `p9c2_perception` directory md5 (sorted per-file md5 list) is identical before and after for all three sequences (36h `e9bc04f7…`, 24h `0d027bf9…`, office `007aa555…`), and for every output file, the file minus its F rows equals the input byte for byte (0 mismatches in 12597 / 13230 / 8522 files; the script also asserts this).

**Coverage (counts only; nothing else of the F rows was read):**

| sequence | person (P) rows | F rows | share with F |
|---|---|---|---|
| subway_s1_36h | 14063 | 6583 | 46.8 % |
| subway_s1_24h | 10836 | 5858 | 54.1 % |
| office_s1_06h | 6837 | 4868 | 71.2 % |

## 2. Pedestrian GT objects (input, no run data)

`p9c_gt_objects.py` (from `/tf` of the bag only) on workstation-1 for office_s1_06h and subway_s1_36h → `p9d_gt/*_gt.npz` (md5 7401e2e3…, 19e12e6d…); subway_s1_24h uses the P1-A npz (918a013d…), copied into `p9d_gt`.

## 3. D1-P with LEV (§7.1, A1.3)

subway_s1_24h, `levels.yaml`, `p9d_perception`, default staging path, no jitter, 5 identical invocations (3 concurrent, then 2), `run_d1p_lev.sh`, workstation-1, binary as `final_binaries.md`.

- **5/5 byte-identical:** the md5.txt of all five runs is identical (md5 of md5.txt `9bfa91c6e3b5eafc135eab27c1a42eb6`; `frame_poses.txt` `2c0b7df5…`, `ped_log.txt` `06beed96…`, `ped_counters.csv` `fd24afcb…`). Also identical across the five: `ped_levels.log` (`ded0c86a…`) and `ped_floor_px.log` (`b77f3ee4…`).
- **Level code executed (md5 and line counts only):** `ped_counters.csv` has 11220 lines and the header contains the `floor`, `bias`, `lvpt` and `plat` factor columns; `ped_levels.log` has 9322 lines and `ped_floor_px.log` 3922 lines. No counter value was read.
- Runner exit code 1 (quality gate) in all five, from `provenance.txt`; not a crash (§8).

## 4. Analysis script (§7.2)

`eval/phase9/P9-D/p9d_analyze.py`, md5 **52e386a2cea57a57b99427e2119dc15a**. Frozen from this commit; no change after the first P9-D run.
Tests run (all pass):
1. `selftest` — synthetic records with known effects: no-effect cell passes everything; +40 % M1 makes H1 fail, H3 untested and leaves the pedestrian family unaffected (A2.3); one failing cell blocks a hypothesis; M2 +0.35 and worse velocity fail; failures enter as +∞; interval helpers exact.
2. `stage0test P9-C2/raw/stage0/runs.jsonl` — Stage 0 flag-off records as OFF and as fake ON/LEV: ratio 1.000, difference 0.000, no degradation call. subway_36h M1 [0.828, 1.203] ub 1.160 (n = 20); subway_24h [0.816, 1.210] ub 1.159; office [0.267, 3.650]; M2 ub 0.244 / 0.236 / 0.240. (At n = 20 the bounds exceed the A2 margins, as expected; n = 60 is the design.)
3. Pedestrian extraction on a real tuning run (office_s1_12h, `none@3`, frozen path): camera-frame position medians (graph 0.3474, B0 0.3601, B1c 0.3851, B1r 0.3493) equal the frozen `c5_eval.evaluate_run` values exactly; velocity medians differ only because the script intersects the (keyframe, track) samples of the four estimators (criterion §4). A levels run (`levels@1`) exercised the contacts, b and level descriptives; `none@1` (scale 4.3) correctly gives "no included map".

Decisions the script fixes (not stated in the criterion):
- bootstrap: arm and OFF resampled independently; quantiles are order statistics (no interpolation) so +∞ values stay defined.
- inclusion "extent" = bounding-box diagonal of the Sim(3)-aligned camera centres; "≥ 50 poses" = keyframes of the map.
- primary pedestrian velocity metric = 3-D world-frame velocity error (`vel`); `vel_xy` is reported.
- plausibility shares are computed on included maps from `ped_log.txt`.
- "levels vs GT floors on subway" = the alignment-free camera-height check (as `c5_levelcheck_camfree.py`), coverage, transitional share and contact-residual share, per LEV run.
- **Not in the script:** the one threaded-mode run per arm on subway_s1_24h (wall-clock only), and B1-RTS beyond the table of medians.

## 5. Campaign script (§7.3)

`campaign_p9d.py` md5 907de6832ce79988ab7c9e42240cb451: interleaved by seed (k = 1: OFF, ON, LEV per cell; …), N = 60 subway / 20 office (A2.1), seeds k = jitter seed and staging path of 40 + k characters, same for every arm; ≤ 3 concurrent subway jobs; checks the binaries before the campaign and before every start; one retry of a crashed run, then `crashed_final.txt`. **Not run, not tested end to end** (a dry smoke test is the first step of the campaign).

## 6. Host verification (A1.4)

Synced with `P9-C5/tools/sync_ws.sh` (the visual_sgraphs rsync dry run showed 0 changes first). `p9d_manifest.py` md5 `eabcbdec56369e8bba11be3b8ddc0bf8`; its output on both hosts is identical except for the lines below:
- The binaries (lib, DBoW2, g2o, runner) exist only on workstation-1 (built there). They equal the values recorded in `P9-C2/final_binaries.md`: lib `1a6b1b3b…`, DBoW2 `64778571…`, g2o `7875c100…`, runner `007ed74e…`.
- `P9-C5/tools/run_stage0.py`: `final_binaries.md` records `0257c152…`, the version before the D1-P scheduler fix (`P9-C2/d1p_subway_fix.md`, `run_stage0.py:28`); both hosts have `181eb1b5…`. P9-D does not use this script; the manifest check expects the fixed md5.
- The source commit of the workstation worktree cannot be read there (the sync excludes `.git`; its worktree HEAD is another commit); the source is identical to the laptop's `p9c5-floor-levels` 9862a18 (rsync dry run empty), and the built md5s are the frozen ones.

Configs: `none.yaml` `fb715917…`, `levels.yaml` `4baf3307…`, `run_p9c_one.sh` `d0dbad51…`, `common_p9c.sh` `e4e41d2f…`. Perception directory manifests (tree md5) and the full list: see `prerun_manifest.txt` (workstation-1 output).

## 7. Disclosures added before the campaign (Marco, 23 Oct 2026)

- **Exit code read from the D1-P LEV runs.** For the five D1-P LEV runs on subway_s1_24h (the evaluation sequence), `runner_exit=` was read from each `provenance.txt` (value 1 in all five), together with `md5.txt`, the counter file's md5 / line count / header, and the line counts and md5 of `ped_levels.log` and `ped_floor_px.log`. The exit code is a quality-gate flag from the runner, not a metric, and A1.3 lists only md5 and counter-file md5 / line count; reading the exit code goes slightly beyond that list. No ATE, coverage, pose, pedestrian quantity or counter value was read.
- **`run_stage0.py` md5.** `P9-C2/final_binaries.md` records `0257c152…` for `P9-C5/tools/run_stage0.py`; both hosts have `181eb1b5…`. The recorded value predates the D1-P scheduler fix (`P9-C2/d1p_subway_fix.md`, `run_stage0.py:28`, evaluation script only, binary unchanged). P9-D does not use this script. `p9d_manifest.py` therefore expects `181eb1b5…` for that one entry; every other entry of `final_binaries.md` is checked against its recorded value, and the campaign stops on any mismatch.

## 8. Campaign script smoke test (23 Oct 2026)

`campaign_p9d.py` gained `--dry-run` and `--perc`, and an apartment_s1_01h entry (smoke only); new md5 **d2216c837fd6f008984a5b66bcd73086** (supersedes §5). Dry run: 420 runs in the interleaved order, staging path of 40 + k characters. Real smoke on the tuning sequence apartment_s1_01h, k = 1, three arms (`--perc p9c3c_perception`): all three completed, scheduler log clean, runner_exit 0, md5.txt written (8 lines OFF, 11 ON and LEV). No metric was read. Then the campaign was started: `campaign_p9d.py ~/datasets/p9d_campaign` on workstation-1.
