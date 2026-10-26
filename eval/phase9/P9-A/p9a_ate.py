#!/usr/bin/env python3
"""P9-A per-run metrics (criterion.md Metrics, Addendum 1 D2-D6).

ATE = evo APE translation-part RMSE after evo `align`; time association
`sync.associate_trajectories(gt, est, max_diff=0.02)` (p5a_analyze.py:70-71, analyze_y2.py:63).
VIO (mono-inertial): SE(3) (`correct_scale=False`); mono VO: Sim(3) (`correct_scale=True`).
Both are always computed and stored; `ate_primary` is the criterion one.

Usage: p9a_ate.py INVENTORY_JSONL OUT_JSONL [--procs N]
"""
import copy
import json
import math
import os
import re
import sys
from multiprocessing import Pool

import numpy as np
from evo.core import metrics, sync
from evo.core.trajectory import PoseTrajectory3D

import p9a_groups as G

MAX_DIFF_S = 0.02            # p5a_analyze.py:71
MIN_MATCHED = 20             # p5a_analyze.py:9, analyze_y2.py:64
COV_TOL_S, COV_GRID_S = 1.0, 0.05   # p5a_analyze.py:35-36,49
RESET_LINE = re.compile(r"\[Tracking\] (\d+) frames were set to lost!")       # Tracking.cc:4243
NEWMAP_LINE = re.compile(r"Creating a new map \(MapId: ([1-9]\d*)")           # Atlas.cc:66
P6A_LOST = re.compile(r"tracking_lost_events: (\d+)")                         # orbslam3_bag_runner (InCrowd-VI)


def load_tum(path):
    """8-column TUM file -> evo trajectory; malformed lines dropped in memory (ate_compare.load_tum does the same on disk)."""
    rows = []
    with open(path) as f:
        for ln in f:
            p = ln.split()
            if len(p) == 8 and not ln.startswith("#"):
                try:
                    rows.append([float(x) for x in p])
                except ValueError:
                    pass
    a = np.array(rows)
    if a.size == 0:
        return None
    o = np.argsort(a[:, 0], kind="stable")
    a = a[o]
    return PoseTrajectory3D(positions_xyz=a[:, 1:4], orientations_quat_wxyz=a[:, [7, 4, 5, 6]], timestamps=a[:, 0])


def ape_rmse(ref, est, sim3):
    e = copy.deepcopy(est)
    r = e.align(ref, correct_scale=sim3)
    ape = metrics.APE(metrics.PoseRelation.translation_part)
    ape.process_data((ref, e))
    return float(ape.get_statistic(metrics.StatisticsType.rmse)), float(r[2])


def ate(gt, est, sim3):
    """-> (rmse, scale, n_matched) on the sync-associated poses."""
    tr, te = sync.associate_trajectories(gt, est, max_diff=MAX_DIFF_S)
    if te.num_poses < MIN_MATCHED:
        return None, None, te.num_poses
    rmse, s = ape_rmse(tr, te, sim3)
    return rmse, s, te.num_poses


def coverage(gt_t, est_t, tol=COV_TOL_S, grid=COV_GRID_S):
    """p5a_analyze.coverage: share of the GT span (0.05 s grid) within `tol` of an estimated stamp."""
    gt_t, est_t = np.sort(gt_t), np.sort(est_t)
    if len(gt_t) < 2 or len(est_t) == 0:
        return 0.0
    g = np.arange(gt_t[0], gt_t[-1], grid)
    i = np.clip(np.searchsorted(est_t, g), 1, len(est_t) - 1) if len(est_t) > 1 else np.zeros(len(g), int)
    d = np.minimum(np.abs(est_t[i] - g), np.abs(est_t[np.maximum(i - 1, 0)] - g))
    return float(np.mean(d <= tol))


def covered_gt_count(gt_t, est_t, tol=COV_TOL_S):
    """Number of GT timestamps with an estimated pose within `tol` seconds."""
    est_t = np.sort(est_t)
    if len(est_t) == 0:
        return 0
    i = np.searchsorted(est_t, gt_t)
    lo = np.abs(gt_t - est_t[np.clip(i - 1, 0, len(est_t) - 1)])
    hi = np.abs(gt_t - est_t[np.clip(i, 0, len(est_t) - 1)])
    return int(np.sum(np.minimum(lo, hi) <= tol))


def main_map(maps, gt_t, tol=COV_TOL_S):
    """criterion.md Metrics: of the per-map trajectories (list of evo trajectories) the one covering the most GT
    timestamps; ties -> lowest index. Returns (index, covered_count, coverage_share)."""
    counts = [covered_gt_count(gt_t, m.timestamps, tol) for m in maps]
    k = int(np.argmax(counts))          # argmax returns the first maximum
    return k, counts[k], counts[k] / max(len(gt_t), 1)


def losses(r):
    """Addendum 1 D6."""
    log = os.path.join(r["dir"], "run.log" if r["dataset"] == "InCrowd-VI" else "launch.log")
    if not os.path.exists(log):
        return dict(losses_resets=None, losses_new_maps=None, losses=None)
    txt = open(log, errors="replace").read()
    new = len(NEWMAP_LINE.findall(txt))
    if r["dataset"] == "InCrowd-VI":
        m = P6A_LOST.search(txt)
        res = int(m.group(1)) if m else None
    else:
        res = len(RESET_LINE.findall(txt))
    return dict(losses_resets=res, losses_new_maps=new, losses=None if res is None else res + new)


def run_metrics(r):
    try:
        return _run_metrics(r)
    except sync.SyncException as e:       # task abort condition: trajectory cannot be matched to GT time
        raise RuntimeError(f"ABORT: {r['rel']} cannot be matched to GT time: {e}") from None


def _run_metrics(r):
    ok, why = G.eligible(r)
    out = dict(run=r["rel"], group=r["group"], dataset=r["dataset"], seq=r["seq"], mode=r["mode"], eligible=ok, reason=why,
               campaign=r["campaign"], maps_x2=(r["x2"] or {}).get("maps", r.get("p6a_maps_at_shutdown")))
    out.update(losses(r))
    if not ok:
        return out
    gt = load_tum(r["gt_path"])
    est = load_tum(G.traj_path(r))
    if gt is None or est is None:
        out.update(eligible=False, reason="empty trajectory after parsing")
        return out
    # criterion: mono VO evaluated on the main map; keyframe files hold one map (D5)
    k, ncov, share = main_map([est], gt.timestamps)
    se3, _, n_matched = ate(gt, est, False)
    sim3, scale, _ = ate(gt, est, True)
    sim3_mode = r["mode"] == "mono"
    out.update(n_keyframes=est.num_poses, n_matched=n_matched, ate_se3=se3, ate_sim3=sim3, sim3_scale=scale,
               ate_primary=(sim3 if sim3_mode else se3), primary_alignment=("sim3" if sim3_mode else "se3"),
               coverage=coverage(gt.timestamps, est.timestamps), covered_gt_share=share,
               main_map_unverified=bool((out["maps_x2"] or 1) > 1), gt_span_s=float(gt.timestamps[-1] - gt.timestamps[0]))
    if out["ate_primary"] is None:
        out.update(eligible=False, reason=f"only {n_matched} matched poses (<{MIN_MATCHED})")
    return out


def main(inv, out, procs=6):
    runs = [x for x in G.load_runs(inv) if x["group"]]
    with Pool(procs) as p:
        res = p.map(run_metrics, runs, chunksize=4)
    with open(out, "w") as f:
        for x in res:
            f.write(json.dumps(x, default=lambda o: None if (isinstance(o, float) and math.isnan(o)) else o) + "\n")
    print(f"{len(res)} runs written to {out}")


if __name__ == "__main__":
    a = sys.argv[1:]
    procs = int(a[a.index("--procs") + 1]) if "--procs" in a else 6
    main(a[0], a[1], procs)
