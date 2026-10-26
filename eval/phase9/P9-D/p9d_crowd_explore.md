# Claude Code task: P9-D crowd-stratified analysis (EXPLORATORY, existing runs only)

You have no memory of earlier sessions. Context: `eval/phase9/P9-D/` (criterion, A1, A2, results of the frozen `p9d_analyze.py`).

**Question.** Does the pedestrian layer (ON) or the floor levels (LEV) help the camera **in the most crowded or occluded moments**, where static features are scarce? The whole-trajectory ATE of P9-D averages these moments away.

## Status and rules

- **EXPLORATORY and post hoc.** Every output is labelled "exploratory, post hoc, P9-D runs". No P9-D verdict changes. Nothing here becomes a paper claim without a confirmatory test on fresh data (section 6).
- **Existing runs only:** the P9-D campaign, OFF/ON/LEV, subway_s1_36h and subway_s1_24h (60 seeds each), and office_s1_06h (20 seeds, reported separately as descriptive). No new run, and no change to the system or to `p9d_analyze.py`.
- **No tuning.** Nothing learned here changes a constant, a config or the binary.
- **Commit order.** Commit this file, then write and freeze `p9d_crowd.py` (md5 in the report header), test it on synthetic trajectories, and only then run it on the P9-D runs. Run it once.

## 1. Occupancy, from inputs only (identical across arms)

**Per frame:**

- **mask fraction:** pedestrian pixels / image pixels, from the pedestrian instance masks the runs used (`/camera/color/image_instance_masks` in the bag);
- **people in view:** the number of P rows in the perception file used by the runs.

**Windows:** 2.0 s windows, step 1.0 s, on the camera timeline. A window's occupancy is the mean mask fraction, and the maximum people-in-view, over its frames.

**Bins, fixed now:**

| | Bins |
|---|---|
| Mask fraction | < 0.10, 0.10–0.25, 0.25–0.50, ≥ 0.50 |
| People in view | 0, 1–2, 3–5, ≥ 6 |

Report how many windows fall in each bin, per sequence.

## 2. Camera error per window (per run)

**RPE over the window:** the relative pose between the estimated poses at the window's start and end frames, against the GT relative pose (GT body frame composed with the body→camera transform, as P9-B).

- translation error in m;
- rotation error in degrees.

There is no global alignment; this is metric VIO.

**Valid window:** both endpoint frames have an estimated pose **in the same map**, and no map event occurs inside the window.

**Failed window:** otherwise, i.e. an endpoint has no pose, the endpoints lie in different maps, or a map event falls inside. Failed windows don't enter the RPE statistics; they enter the window-failure rate.

## 3. Statistics per sequence and bin (both occupancy measures, separately)

**Per run:** the median translation RPE and the median rotation RPE over the run's valid windows in that bin, plus the run's window-failure rate in the bin. Runs with fewer than 5 valid windows in a bin don't contribute an RPE value there.

**Arm comparison:**

- RPE ratio = median over runs (ON) / median over runs (OFF), and likewise LEV/OFF;
- failure-rate difference = mean over runs (ON) − mean over runs (OFF), and likewise LEV/OFF.

**Intervals:** two-sided 95%, percentile bootstrap over runs, arms resampled independently, 10,000 resamples, seed 9301.

**Pooled subway:** the geometric mean of the two cells' ratios, and the mean of their differences, with a stratified bootstrap (resample within cell and arm).

## 4. Map events and occupancy (descriptive)

For every map event in every run, record the occupancy (mask fraction, people in view) of the 2 s before it. Report per arm and sequence:

- the distribution of pre-event occupancy;
- map events per hour of windows in each occupancy bin.

## 5. Outputs → `eval/phase9/P9-D/crowd_explore_report.md`

1. **First line:** "EXPLORATORY, post hoc". Then the one-line answer to the question, per sequence and pooled, stating whether any benefit appears in the high-occupancy bins.
2. **Tables:** per sequence and pooled, per bin, the number of windows; the translation and rotation RPE ratios [95% interval] for ON/OFF and LEV/OFF; and the window-failure differences [95% interval].
3. **Figures** (PNG and PDF): the RPE ratio against occupancy bin, with intervals and a line at 1.0, for both arms and both occupancy measures; the window-failure rate against bin, per arm; and the pre-event occupancy histograms.
4. office_s1_06h in a separate, descriptive section.

## 6. Decision rule for the next step (fixed now; decides only what to pre-register)

Look at the **highest occupancy bin with ≥ 200 valid windows per arm**, in the pooled subway result, separately for each occupancy measure and for ON and LEV.

A **signal** is either of:

- the upper 95% bound of the translation RPE ratio vs OFF is < 1.0;
- the upper 95% bound of the window-failure-rate difference vs OFF is < 0.

**If there is a signal:** report it. Marco may then add, by dated addendum to P9-E **before any Part B run**, a pre-registered crowd-stratified camera hypothesis on InCrowd-VI, with the same windows, bins and measure.

**If there is no signal:** report "no camera benefit detectable even in the most occluded windows (exploratory)". No further step follows.

**Stop** after the report.
