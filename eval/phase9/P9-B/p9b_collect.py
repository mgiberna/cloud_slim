#!/usr/bin/env python3
"""P9-B: per-run metrics of the stage-2 campaign and per-cell statistics (criterion.md "Stage 2").

usage: p9b_collect.py STAGE2_ROOT RAW_DIR
  reads   STAGE2_ROOT/<seq>_<mode>_s<seed>/{keyframe_trajectory_map*.tum, run_summary.json, run.log, md5.txt}
          /media/marco/muffin/datasets/p9b_gt/<seq>_gt_body.tum and <seq>_gt_summary.json (T_b_c)
  writes  RAW_DIR/runs.jsonl   one record per run (written once: refuses to overwrite)
          RAW_DIR/cells.json   per (sequence, mode) statistics
GT is the body frame; it is composed with T_b_c from the bag's /tf_static (criterion "GT frame"). The same metrics without the
composition are stored as *_notf for the descriptive comparison.
"""
import glob
import hashlib
import json
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p9b_ate as B           # noqa: E402

GT_DIR = os.environ.get("P9B_GT_DIR", "/media/marco/muffin/datasets/p9b_gt")
SEQS = ["office_s1_06h", "office_s1_12h", "subway_s1_24h", "subway_s1_36h", "apartment_s1_01h", "apartment_s1_02h"]
MODES = ["mono", "inertial"]
NSEEDS = 20


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def run_record(rd, gt, tbc):
    m = re.match(r"(.+)_(mono|inertial)_s(\d+)$", os.path.basename(rd))
    seq, mode, seed = m.group(1), m.group(2), int(m.group(3))
    if not os.path.exists(os.path.join(rd, "run_summary.json")):      # runner aborted before writing its summary (crash)
        crashed = open(os.path.join(rd, "provenance.txt")).read()
        return dict(run=os.path.basename(rd), seq=seq, mode=mode, seed=seed, ok=False, reason="runner crash: " + "".join(
            l for l in crashed.splitlines() if l.startswith("runner_exit")), run_dir=rd, main_map_md5=None)
    on = B.run_metrics(rd, gt, tbc)
    off = B.run_metrics(rd, gt, None)
    on.update(seq=seq, mode=mode, seed=seed, ate_sim3_notf=off["ate_sim3"], ate_se3_notf=off["ate_se3"],
              abs_log_scale_notf=off["abs_log_scale"], main_map_id_notf=off["main_map_id"] if "main_map_id" in off else None)
    f = os.path.join(rd, "keyframe_trajectory_map%d.tum" % on["main_map_id"]) if "main_map_id" in on else None
    on["main_map_md5"] = md5(f) if f else None
    on["frame_poses_md5"] = md5(os.path.join(rd, "frame_poses.txt"))
    on["run_dir"] = rd
    return on


def cell_summary(recs):
    ok = [r for r in recs if r.get("ok")]
    out = dict(n_runs=len(recs), n_ok=len(ok), complete=(len(recs) == NSEEDS), n_failed=len(recs) - len(ok),
               failed=[(r["seed"], r.get("reason")) for r in recs if not r.get("ok")])
    for k, key in [("sim3", "ate_sim3"), ("abs_log_scale", "abs_log_scale"), ("se3", "ate_se3"),
                   ("sim3_incl_retired", "ate_sim3_incl_retired")]:
        out[k] = B.cell_stats([r.get(key) for r in ok])
    for key in ["coverage", "maps_at_shutdown", "losses_resets", "losses_new_maps", "map_reset_count", "tracking_lost_events",
                "wall_seconds", "rtf", "main_map_keyframes", "images_skipped_insufficient_imu", "maps_retired_by_reset",
                "lm_not_enough_motion", "imu_stage1_starts", "imu_stage2_starts"]:
        v = [r[key] for r in recs if r.get(key) is not None]
        out[key] = dict(median=float(np.median(v)), min=float(np.min(v)), max=float(np.max(v))) if v else None
    out["distinct_main_map_md5"] = len({r["main_map_md5"] for r in recs})
    return out


def main(root, raw):
    os.makedirs(raw, exist_ok=True)
    runs_p, cells_p = os.path.join(raw, "runs.jsonl"), os.path.join(raw, "cells.json")
    for p in (runs_p, cells_p):
        if os.path.exists(p):
            raise SystemExit(f"refusing to overwrite {p} (raw data is written once)")
    recs = []
    for seq in SEQS:
        gt_p = os.path.join(GT_DIR, f"{seq}_gt_body.tum")
        if not os.path.exists(gt_p):
            continue
        gt = B.A.load_tum(gt_p)
        tbc = json.load(open(os.path.join(GT_DIR, f"{seq}_gt_summary.json")))["T_b_c"]
        for mode in MODES:
            for rd in sorted(glob.glob(os.path.join(root, f"{seq}_{mode}_s*")),
                             key=lambda p: int(p.rsplit("_s", 1)[1])):
                if os.path.exists(os.path.join(rd, "md5.txt")):
                    recs.append(run_record(rd, gt, tbc))
    with open(runs_p, "w") as f:
        for r in recs:
            f.write(json.dumps(r, default=lambda o: None if (isinstance(o, float) and math.isnan(o)) else o) + "\n")
    cells = {}
    for seq in SEQS:
        for mode in MODES:
            rs = [r for r in recs if r["seq"] == seq and r["mode"] == mode]
            if rs:
                cells[f"{seq}|{mode}"] = cell_summary(rs)
    json.dump(cells, open(cells_p, "w"), indent=1, default=lambda o: None if (isinstance(o, float) and math.isnan(o)) else o)
    print(f"{len(recs)} runs, {len(cells)} cells -> {raw}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
