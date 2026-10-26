#!/usr/bin/env python3
"""P9-B per-run metrics (criterion.md "Stage 2" / "Metrics").

Reuses the P9-A code unchanged (eval/phase9/P9-A/p9a_ate.py): evo APE translation-part RMSE after evo `align`,
time association `sync.associate_trajectories(gt, est, max_diff=0.02)`, coverage on a 0.05 s grid with 1 s tolerance,
main map = the map covering the most GT timestamps (ties -> lowest map id). New here: the keyframe trajectories of
ALL maps (runner `keyframe_trajectory_map<id>.tum`), the optional body->camera composition of the GT, and the
scale error |log s| of the Sim(3) alignment.
"""
import glob
import json
import math
import os
import re
import sys

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "P9-A"))
import p9a_ate as A          # noqa: E402  (P9-A code, unchanged)
import p9a_mde as M          # noqa: E402

RESET_LINE, NEWMAP_LINE = A.RESET_LINE, A.NEWMAP_LINE     # Tracking.cc:4243, Atlas.cc:66 (P9-A D6)


def compose_gt_cam(gt, T_bc):
    """GT body trajectory (T_w_b) -> GT camera trajectory (T_w_c = T_w_b * T_b_c). T_bc: 4x4, camera pose in the body frame."""
    T_bc = np.asarray(T_bc, float)
    R_bc, t_bc = T_bc[:3, :3], T_bc[:3, 3]
    q = gt.orientations_quat_wxyz                                   # (w, x, y, z)
    R_wb = Rot.from_quat(q[:, [1, 2, 3, 0]])
    p = gt.positions_xyz + R_wb.apply(t_bc)
    R_wc = R_wb * Rot.from_matrix(R_bc)
    qc = R_wc.as_quat()                                             # xyzw
    return PoseTrajectory3D(positions_xyz=p, orientations_quat_wxyz=qc[:, [3, 0, 1, 2]], timestamps=gt.timestamps)


def load_maps(run_dir):
    """-> list of (map_id, trajectory) sorted by map id; maps without keyframes are dropped."""
    out = []
    for f in sorted(glob.glob(os.path.join(run_dir, "keyframe_trajectory_map*.tum")),
                    key=lambda p: int(re.search(r"map(\d+)\.tum$", p).group(1))):
        tr = A.load_tum(f)
        if tr is not None:
            out.append((int(re.search(r"map(\d+)\.tum$", f).group(1)), tr))
    return out


def load_retired(run_dir):
    """Trajectories of maps the tracker discarded (Tracking::ResetActiveMap / Reset), exported just before they were cleared.
    -> list of (label, trajectory) in discard order; label 'rK_mapID'."""
    out = []
    for f in sorted(glob.glob(os.path.join(run_dir, "keyframe_trajectory_retired*_map*.tum")),
                    key=lambda p: int(re.search(r"retired(\d+)_map", p).group(1))):
        tr = A.load_tum(f)
        if tr is not None:
            m = re.search(r"retired(\d+)_map(\d+)\.tum$", f)
            out.append((f"r{m.group(1)}_map{m.group(2)}", tr))
    return out


def read_json(path):
    with open(path) as f:
        return json.load(f)


def log_counts(run_dir):
    p = os.path.join(run_dir, "run.log")
    if not os.path.exists(p):
        return dict(losses_resets=None, losses_new_maps=None)
    txt = open(p, errors="replace").read()
    return dict(losses_resets=len(RESET_LINE.findall(txt)), losses_new_maps=len(NEWMAP_LINE.findall(txt)),
                # LocalMapping.cc:154-161 (resets mTinit) and :236, :250 (IMU init stages 1 and 2)
                lm_not_enough_motion=txt.count("Not enough motion for map initializing"),
                imu_stage1_starts=txt.count("IMU bias/scale initialization (stage#1)") // 2,
                imu_stage2_starts=txt.count("IMU bias/scale initialization (stage#2)") // 2)


def evaluate_trajectories(gt, maps, T_bc=None, retired=None):
    """gt: body-frame GT trajectory; maps: list of (id, est trajectory) of the maps alive at shutdown. -> dict of metrics for the
    main map (criterion). T_bc None = GT used as is (P9-A convention). `retired` (optional list of (label, trajectory), see
    load_retired) only adds the descriptive *_incl_retired fields: the same metrics for the best-covering map among the surviving
    and the discarded ones."""
    gt_used = compose_gt_cam(gt, T_bc) if T_bc is not None else gt
    out = dict(gt_transform=T_bc is not None, n_maps_exported=len(maps))
    if retired is not None:
        out["n_maps_retired"] = len(retired)
        allm = [(f"s{mid}", tr) for mid, tr in maps] + list(retired)
        if allm:
            k, ncov, share = A.main_map([m for _, m in allm], gt_used.timestamps)
            lab, est = allm[k]
            sim3, scale, n_matched = A.ate(gt_used, est, True)
            out.update(incl_retired_map=lab, incl_retired_covered_gt_share=share, ate_sim3_incl_retired=sim3,
                       abs_log_scale_incl_retired=(abs(math.log(scale)) if scale and scale > 0 else None))
    if not maps:
        return dict(out, ok=False, reason="no map with keyframes")
    k, ncov, share = A.main_map([m for _, m in maps], gt_used.timestamps)
    mid, est = maps[k]
    sim3, scale, n_matched = A.ate(gt_used, est, True)
    se3, _, _ = A.ate(gt_used, est, False)
    out.update(main_map_id=mid, main_map_keyframes=est.num_poses, n_matched=n_matched, covered_gt_share=share,
               coverage=A.coverage(gt_used.timestamps, est.timestamps), ate_sim3=sim3, ate_se3=se3, sim3_scale=scale,
               abs_log_scale=(abs(math.log(scale)) if scale and scale > 0 else None))
    if sim3 is None:
        return dict(out, ok=False, reason=f"only {n_matched} matched poses (<{A.MIN_MATCHED})")
    return dict(out, ok=True, reason="")


def run_metrics(run_dir, gt_path, T_bc=None):
    """gt_path: TUM path or an already loaded evo trajectory."""
    gt = A.load_tum(gt_path) if isinstance(gt_path, str) else gt_path
    maps = load_maps(run_dir)
    out = evaluate_trajectories(gt, maps, T_bc, load_retired(run_dir))
    s = read_json(os.path.join(run_dir, "run_summary.json"))
    out.update(log_counts(run_dir))
    out.update(frames_processed=s["frames_processed"], maps_at_shutdown=s["maps_at_shutdown"],
               map_reset_count=s["map_reset_count"], maps_retired_by_reset=s.get("maps_retired_by_reset"), tracking_lost_events=s["tracking_lost_events"],
               wall_seconds=s["wall_seconds"], sensor_seconds=s["sensor_seconds"],
               rtf=(s["sensor_seconds"] / s["wall_seconds"]) if s["wall_seconds"] else None,
               images_skipped_insufficient_imu=s["images_skipped_insufficient_imu"],
               images_skipped_duplicate=s["images_skipped_duplicate"])
    out["run"] = os.path.basename(os.path.normpath(run_dir))
    return out


def cell_stats(values):
    """Per (sequence, mode) statistics of one metric over the seeds (criterion: median, sigma_r, MDE_rel(10/20), n(5%))."""
    v = np.array([x for x in values if x is not None], float)
    if len(v) < 2:
        return dict(n=len(v))
    med, sig = float(np.median(v)), M.sigma_r(v)
    if med <= 0:
        return dict(n=len(v), median=med, sigma_r=sig)
    return dict(n=len(v), median=med, sigma_r=sig, sigma_r_over_median=sig / med,
                mde_rel_10=M.mde_formula(sig, med, 10), mde_rel_20=M.mde_formula(sig, med, 20),
                n_5pct=M.n_required(0.05, sig, med))
