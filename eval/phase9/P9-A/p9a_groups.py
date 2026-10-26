#!/usr/bin/env python3
"""Shared group/eligibility logic for P9-A (inventory and main computation). No ATE here.

Eligibility rule (fixed in inventory.md before any ATE statistic):
  eligible(run) := done marker AND NOT outcome_incomplete marker AND keyframe trajectory file non-empty
                   AND a GT file exists for the run.
  n_runs of a group := number of eligible runs (the Units table of criterion.md is applied to it).
"""
import collections
import json
import os
import re


def load_runs(path):
    return [json.loads(l) for l in open(path)]


def traj_path(r):
    if r["dataset"] == "InCrowd-VI":
        return os.path.join(r["dir"], "keyframe_trajectory_tum.txt")
    return os.path.join(r["dir"], "keyframe.tum")


def eligible(r):
    """-> (bool, reason)"""
    f = r["files"]
    tp = os.path.basename(traj_path(r))
    if r["dataset"] == "InCrowd-VI":
        if not r["markers"]["done"]:
            return False, "no done marker"
    else:
        if not r["markers"]["done"]:
            return False, "no done marker"
        if r["markers"]["outcome_incomplete"]:
            return False, "outcome_incomplete"
    if not f.get(tp):
        return False, "no/empty " + tp
    if not r.get("gt_path"):
        return False, "no GT file in run dir"
    return True, ""


def stem(r):
    n = os.path.basename(r["dir"])
    return re.sub(r"_?(rep|run)\d+$", "", n)


def groups(runs):
    g = collections.defaultdict(list)
    for r in runs:
        if r["group"]:
            g[r["group"]].append(r)
    return g


def label(rs):
    c = collections.Counter(stem(r) for r in rs)
    return "+".join(f"{k}x{v}" for k, v in c.most_common(4))
