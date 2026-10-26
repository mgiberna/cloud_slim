"""T3 test 5: things that silently change a pedestrian sample population or a reported count (synthetic inputs, frozen code)."""
import math, os, tempfile
import numpy as np
import _paths  # noqa: F401
import p9d_analyze as A
import c3b_ped_error as E

I3 = np.eye(3)


def S(s=1.0):
    return (s, I3.copy(), np.zeros(3))


# --- 1. state -> map assignment by time window (sim_of): a reset at t = 500 s, new map starts 500.5 s
S_old, S_new = S(1.0), S(1.0)
segsim = [(0.0, 500.0, S_old), (500.5, 520.0, S_new)]
for t in (498.0, 499.0, 499.5, 499.9, 500.0):
    got = E.sim_of(segsim, t)
    print(f'state at t={t:6.1f} s (written in the OLD map) -> assigned to', 'old map' if got is S_old else 'NEW map')
assert E.sim_of(segsim, 499.9) is S_new
# a dropped short map (< 20 keyframes, map_segments) -> its states borrow a neighbour's Sim(3) within 1 s, else they are lost
segsim2 = [(0.0, 100.0, S_old)]
print('state of a dropped 15-keyframe map at t=100.8 ->', 'old map Sim(3)' if E.sim_of(segsim2, 100.8) is S_old else E.sim_of(segsim2, 100.8))

# --- 2. inclusion thresholds of _incl_maps (strict / non-strict) with a fake GT camera
class FakeGt:
    def __init__(self, f): self.f = f
    def Twc(self, ts):
        T = np.tile(np.eye(4), (len(ts), 1, 1)); T[:, :3, 3] = self.f(ts); return T


ts = np.linspace(0, 60, 200)
line = lambda t: np.stack([t * 0.1, 0.05 * np.sin(t), np.zeros_like(t)], 1)        # 6 m, not collinear (Umeyama needs a non-degenerate set)
gt = FakeGt(line)
for s_true, n in ((math.exp(-0.1999), 200), (math.exp(0.2001), 200), (1.0, 60), (1.0, 72)):
    c = line(ts[:n]) / s_true
    (_, ok, d), = A._incl_maps([(ts[0], ts[n - 1], c, ts[:n])], gt, E)
    print(f'map s={d["s"]:.5f} |log s|={abs(math.log(d["s"])):.4f} rmse={d["rmse"]:.3f} extent={d["extent"]:.2f} n={d["n"]} -> included={ok}')
# rmse exactly at the gate
rng = np.random.default_rng(0)
noise = rng.normal(size=(200, 3)); noise -= noise.mean(0)
for k in (0.27, 0.30, 0.33):
    c = line(ts) + k * noise
    (_, ok, d), = A._incl_maps([(0, 60, c, ts)], gt, E)
    print(f'noisy map rmse={d["rmse"]:.3f} -> included={ok} (gate 0.5 m)')
# 50-pose rule
ts50 = np.linspace(0, 30, 50); ts49 = ts50[:49]
for t_ in (ts50, ts49):
    (_, ok, d), = A._incl_maps([(t_[0], t_[-1], line(t_), t_)], gt, E)
    print(f'map with n={d["n"]} keyframes, extent {d["extent"]:.2f} m -> included={ok}')

# --- 3. per-estimator association: B0 matched to ANOTHER person, or unmatched -> dropped for every estimator
body = np.array([[t, 0, 0, 0, 0, 0, 0, 1] for t in np.arange(0, 20, 0.01)])
gtcam = E.GtCam(body, np.eye(4))
tt = np.arange(0, 20, 0.01)
objs = {'object_A': np.c_[tt, np.zeros_like(tt), np.zeros_like(tt), 5 + 0 * tt], 'object_B': np.c_[tt, 2 + 0 * tt, np.zeros_like(tt), 5 + 0 * tt]}


def states(offset):
    return [(kf, kf * 0.5, 7, np.array([0.0, 0, 5]) + offset, np.eye(4), np.zeros(3)) for kf in range(1, 20)]


Sm = S(1.0)
for label, off in (('B0 1.6 m towards person B', np.array([1.6, 0, 0])), ('B0 6 m away', np.array([0, 6.0, 0]))):
    res = {}
    for name, o in (('graph', np.zeros(3)), ('B0', off)):
        per = {(7, id(Sm)): [(e, Sm) for e in states(o)]}
        m, _ = E.associate(per, objs, gtcam, 'cam')
        rows = E.samples(per, m, objs, gtcam)
        res[name] = (m.get((7, id(Sm))), float(np.median([r['cam'] for r in rows])) if rows else None, len(rows))
    print(f'{label}: graph -> {res["graph"]}, B0 -> {res["B0"]}  (GT person, median cam error, n samples)')
# with B0 matched to B its error is 0.4 m instead of 1.6 m against the graph's person A; with B0 unmatched the track leaves the four-estimator intersection

# --- 4. B0 velocity needs neighbours <= 0.3 s; an empty velocity intersection removes the run from the POSITION hypotheses too (ped_record:239-240)
for dt in (0.2, 0.4):
    st = [(kf, kf * dt, 7, np.array([0.0, 0, 5]), np.eye(4), np.zeros(3)) for kf in range(1, 30)]
    per = {(7, id(Sm)): [(e, Sm) for e in st]}
    m = {(7, id(Sm)): 'object_A'}
    print(f'keyframe spacing {dt} s: graph velocity rows {len(E.velocity_rows(per, m, objs))}, B0 velocity rows {len(E.velocity_rows(per, m, objs, b0=True))}, position rows {len(E.samples(per, m, objs, gtcam))}')

# --- 5. crash semantics: crash marker vs a run dir with md5.txt but no run_summary.json (p9b_collect.run_record -> ok False, no loss counts)
print('crash marker           ->', {k: A.camera_record(dict(crashed=True))[k] for k in ('m1', 'event')})
print('runner abort (no summary, md5 present) ->', {k: A.camera_record(dict(ok=False, reason='runner crash: runner_exit=134'))[k] for k in ('m1', 'event')})
print('ok run, run.log missing (loss counts None) ->', {k: A.camera_record(dict(ok=True, ate_se3=1.0, losses_resets=None, losses_new_maps=None))[k] for k in ('m1', 'event')})

# --- 6. descriptives: 'none included' column (known defect) and exit-1 denominator
cam_ok = dict(m1=1.0, event=False, crashed=False, ok=True, ate_sim3=1, abs_log_scale=.01, coverage=1, scale_fail=False, exit1=False, wall=1, rtf=1)
cam_bad = dict(cam_ok, ok=False, m1=math.inf, exit1=True, scale_fail=None)
recs = [dict(k=1, cam=cam_ok, ped=dict(none_included=True, n_maps=2)), dict(k=2, cam=cam_ok, ped=dict(no_samples=True, n_pos=0, n_vel=0)),
        dict(k=3, cam=cam_bad, ped=None), dict(k=4, cam=dict(cam_ok, exit1=True), ped=None)]
with tempfile.TemporaryDirectory() as d:
    import json
    json.dump(dict(seq='subway_s1_24h', n=4, data={a: recs for a in A.ARMS}), open(f'{d}/records_subway_s1_24h.json', 'w'))
    data = A.load_records(d)
desc = A.descriptives(data)['subway_s1_24h']['on']
print(f"descriptives: n_with_ped={desc['n_with_ped']} n_no_included_map={desc['n_no_included_map']} (truth: 1 none_included, 1 no_samples, 2 without a record) "
      f"exit1 rate={desc['exit1']:.2f} (truth 2/4 runs = 0.50; ok-only denominator)")
assert desc['n_no_included_map'] == 0

# --- 7. transitional share (known defect) and duplicate (kf, track) contact rows in _levels_descr
with tempfile.TemporaryDirectory() as rd:
    Sx = S(1.0)
    seg = [(0.0, 100.0, Sx)]
    lz = float(0.0).hex()
    rows = ['# map kf t track . level z trans',
            f'0 1 1.0 7 x 0 {lz} 0', f'0 2 2.0 7 x 0 {lz} 0',
            f'0 3 3.0 7 x -1 {lz} 1', f'0 4 4.0 7 x -1 {lz} 1',      # transitional contacts are unassigned (level -1)
            f'0 2 2.0 7 x 0 {lz} 0']                                    # the same (kf, track) contact written again by a later BA
    open(f'{rd}/ped_levels.log', 'w').write('\n'.join(rows) + '\n')
    Twc = np.eye(4); Twc[2, 3] = 1.4895
    log = [(kf, float(kf), 7, np.zeros(3), Twc, np.zeros(3)) for kf in (1, 2, 3, 4)]
    out = A._levels_descr(rd, E, seg, {id(Sx)}, log)
print(f"levels: assigned={out['assigned']} transitional={out['transitional']} share={out['transitional_share']} (truth 2 of 4 contacts = 0.5); "
      f"used={out['used']} n_states={out['n_states']} coverage={out['coverage']} (2 distinct states with a contact -> 0.5; duplicate row counted)")
print('test_population OK')
