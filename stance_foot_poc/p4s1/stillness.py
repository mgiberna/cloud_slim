"""P4-S1 floor-ray stillness of an anchor pixel over a claim run.

For each frame of the run the anchor pixel is cast through the GT camera onto the horizontal floor plane z = z_floor (GT root z -
h_root of the associated pedestrian); the run's displacement is measured on the resulting world points (horizontal plane).
  max = largest pairwise distance between the run's points (diameter, a rotation- and origin-free "how far did it move")
  rms = RMS distance to the run's mean point
Frames whose ray misses the floor are dropped; a run needs >= MIN_POINTS valid points to be scored.
"""
import numpy as np

from p4s1 import data

MIN_POINTS = 3


def displacement(T_w_c, uv, z_floor):
    """T_w_c (m,4,4), uv (m,2), z_floor (m,) -> dict(max, rms, n, pts)"""
    p = data.floor_points(T_w_c, uv, z_floor)[:, :2]
    ok = np.isfinite(p).all(1)
    p = p[ok]
    if len(p) < MIN_POINTS:
        return dict(max=np.nan, rms=np.nan, n=int(len(p)), pts=p)
    dm = np.linalg.norm(p[:, None] - p[None], axis=2)
    return dict(max=float(dm.max()), rms=float(np.sqrt(((p - p.mean(0)) ** 2).sum(1).mean())), n=int(len(p)), pts=p)
