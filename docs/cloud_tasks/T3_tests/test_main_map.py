"""T3 test 4: main-map choice with retired maps (p9b_ate.evaluate_trajectories, frozen P9-B definition) and its effect on M1 (p9d_analyze.camera_record)."""
import numpy as np
import _paths  # noqa: F401
from evo.core.trajectory import PoseTrajectory3D
import p9b_ate as B
import p9d_analyze as A

GT_T = np.round(np.arange(0.0, 100.0, 0.01), 2)


def gt_pos(t):
    return np.stack([2.0 * np.cos(0.05 * t), 2.0 * np.sin(0.05 * t), 0.02 * t], 1) * np.array([5, 5, 1])


def traj(t, p):
    q = np.tile([1.0, 0, 0, 0], (len(t), 1))
    return PoseTrajectory3D(positions_xyz=p, orientations_quat_wxyz=q, timestamps=t)


gt = traj(GT_T, gt_pos(GT_T))


def est(t0, t1, drift=0.0, hz=5.0):
    t = np.round(np.arange(t0, t1, 1.0 / hz), 2)
    p = gt_pos(t) + drift * np.stack([(t - t0) ** 2 / 100.0, np.zeros_like(t), np.zeros_like(t)], 1)
    return traj(t, p)


def cam(maps, retired, ev):
    r = B.evaluate_trajectories(gt, maps, None, retired)
    r.update(losses_resets=ev, losses_new_maps=0)
    c = A.camera_record(r)
    return r, c


cases = {
    'A: one map 0-100 s, drift': ([(0, est(0, 100, 0.05))], [], 0),
    'B: map0 0-90 s (drift) RETIRED by reset, map1 91-100 s survives': ([(1, est(91, 100, 0.05))], [('r0_map0', est(0, 90, 0.05))], 1),
    'C: as B but surviving map1 only 97-100 s (15 kf)': ([(1, est(97, 100, 0.05))], [('r0_map0', est(0, 97, 0.05))], 1),
    'D: map0 0-90 s and map1 91-100 s both SURVIVE (new map, no reset)': ([(0, est(0, 90, 0.05)), (1, est(91, 100, 0.05))], [], 1),
    'E: tie: map3 (10-40 s) and map1 (60-90 s) cover equally many GT stamps': ([(1, est(60, 90, 0.0)), (3, est(10, 40, 0.0))], [], 1),
}
for name, (maps, ret, ev) in cases.items():
    r, c = cam(maps, ret, ev)
    print(f"{name}\n   main_map_id={r.get('main_map_id')} covered_gt_share={r.get('covered_gt_share', 0):.3f} ok={r['ok']} M1(SE3)={c['m1']:.3f} event={c['event']} "
          f"| incl_retired map={r.get('incl_retired_map')} sim3_incl_retired={r.get('ate_sim3_incl_retired')}")
rA = cam(*cases['A: one map 0-100 s, drift'])[1]['m1']
rB = cam(*cases['B: map0 0-90 s (drift) RETIRED by reset, map1 91-100 s survives'])[1]['m1']
rC = cam(*cases['C: as B but surviving map1 only 97-100 s (15 kf)'])[1]['m1']
assert rB < rA, 'a late reset lowers M1 (the big drifting map is excluded from the main-map choice)'
assert rC == float('inf'), 'a surviving map with < 20 matched poses -> ok False -> +inf'
r, _ = cam(*cases['E: tie: map3 (10-40 s) and map1 (60-90 s) cover equally many GT stamps'])
assert r['main_map_id'] == 1
print('tie -> main map id', r['main_map_id'], '(frozen rule: first maximum in map-id order = lowest map id)')
print('test_main_map OK')
