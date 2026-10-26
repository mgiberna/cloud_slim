"""P9-C3b: readers shared by c3b_eval.py and the viz tools (foot keypoint rows of p9c3_perception, ped_floor.log)."""
import os


_foot_cache = {}


def foot_row(pdir, stamp, track):
    """(u, v) of the lowest foot keypoint of the track in that image (the `F track u v score` rows of p9c3_perception)."""
    key = (pdir, stamp)
    if key not in _foot_cache:
        rows = {}
        try:
            for l in open(f'{pdir}/{int(round(stamp * 1e6)):019d}.ped.txt'):
                if l.startswith('F '):
                    x = l.split(); rows[int(x[1])] = (float(x[2]), float(x[3]))
        except FileNotFoundError:
            pass
        _foot_cache[key] = rows
    return _foot_cache[key].get(track)


def read_floor_log(rd):
    """(kf_id, track) -> plane height zp the graph used (ped_floor.log, map frame)."""
    d = {}
    if not os.path.exists(f'{rd}/ped_floor.log'):
        return d
    for l in open(f'{rd}/ped_floor.log'):
        if l[0] == '#' or not l.strip():
            continue
        x = l.split(); d[(int(x[0]), int(x[2]))] = float.fromhex(x[3])
    return d
