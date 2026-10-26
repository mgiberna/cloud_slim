#!/usr/bin/env python3
"""P9-D analysis (criterion.md sections 4-6 with addenda A1, A2). FROZEN once its md5 is recorded in prerun.md; no change after the first P9-D run.

Run layout (written by campaign_p9d.py):  ROOT/<seq>/<arm>@<k>/   arm in off | on | lev, k = 1..N, one run_p9c_one.sh output directory each.
Failed runs (no outputs after the one retry) are listed, one "<seq> <arm> <k>" per line, in ROOT/crashed_final.txt.

  collect SEQ ROOT OUT [--allow-incomplete]   per-run records of one cell -> OUT/records_<SEQ>.json (written once; refuses to overwrite).
                                              Aborts unless every run of the cell is complete (A2.1: N = 60 per arm on the subway cells, 20 on office_s1_06h).
  report  OUT                                 reads every OUT/records_<SEQ>.json present -> OUT/results.json and OUT/results.md (hypotheses, descriptives).
  selftest                                    synthetic records with known effects.
  stage0test RUNS_JSONL                       Stage 0 flag-off records as OFF and as fake ON/LEV (P9-C2/raw/stage0/runs.jsonl).

Camera (section 4, P9-B definitions via p9b_collect.run_record): M1 = SE(3) ATE of the main map (no main-map metric = +inf); M2 = >= 1 reset or new map
(losses_resets + losses_new_maps >= 1; a crashed run counts as a map event).
Pedestrians (frozen c3b_ped_error.py, c3b_b1.py / c5_b1.py, c5_eval.py helpers; P2-D association for the world frame, camera-frame association for the primary metric):
  per run and estimator (graph, B0, B1-causal, B1-RTS): the median camera-frame position error and the median world-frame velocity error over the (keyframe, track) samples
  that every one of the four estimators has (position and velocity sets intersected separately), on maps that pass the inclusion rule
  (|log s| < 0.2, Sim(3) camera-centre residual RMSE <= 0.5 m, extent >= 2 m [bounding-box diagonal of the aligned centres], >= 50 keyframes).
Statistics: bootstrap = percentile bootstrap over runs, 10000 resamples, numpy default_rng(9101) re-created per quantity; arm and OFF resampled independently.
"""
import glob
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P9 = os.path.join(HERE, '..')
for d in ('P9-B', 'P9-C3', 'P9-C5'):
    sys.path.insert(0, os.path.join(P9, d))

SUBWAY = ['subway_s1_36h', 'subway_s1_24h']
OFFICE = 'office_s1_06h'
NRUN = {'subway_s1_36h': 60, 'subway_s1_24h': 60, 'office_s1_06h': 20}      # A2.1
ARMS = ['off', 'on', 'lev']
EST = ['on', 'B0', 'B1c', 'B1r']
M1_MARGIN, M2_MARGIN, POS_MARGIN, VEL_MARGIN = 1.10, 0.20, 1.05, 1.10        # A2.2, criterion H2(b), H4
NBOOT, SEED = 10000, 9101
Z1, Z2 = 1.6448536269514722, 1.959963984540054                               # one-sided 95 %, two-sided 95 %
INCL = dict(logs=0.2, rmse=0.5, extent=2.0, poses=50)
GT_DIR_DEFAULT = os.environ.get('P9D_GT_DIR', '/media/marco/muffin1/datasets/p9d_gt')                      # <seq>_gt.npz in the P1-A layout (p9c_gt_objects.py); env P9D_GT_DIR / P9D_PERCEPTION / P9B_GT_DIR (body GT, p9b_collect) override the laptop defaults
PERC_DEFAULT = os.environ.get('P9D_PERCEPTION', '/media/marco/muffin1/datasets/p9d_perception')
CFG = {'on': os.path.join(P9, 'P9-C5', 'config', 'variants', 'none.yaml'), 'lev': os.path.join(P9, 'P9-C5', 'config', 'variants', 'levels.yaml')}


# --------------------------------------------------------------------------------------------- statistics
def _finite(x):
    return float(x) if x is not None and np.isfinite(x) else math.inf


def pct(x, q):
    """order-statistic percentile (no interpolation: +inf values must not produce nan)."""
    x = np.sort(np.asarray(x, float))
    return float(x[min(len(x) - 1, max(0, int(math.ceil(q / 100.0 * len(x))) - 1))])


def boot_median_ratio(a, b):
    """median(a) / median(b); a, b may contain +inf. Returns point, one-sided 95 % upper bound, two-sided 95 % interval."""
    a, b = np.array([_finite(x) for x in a]), np.array([_finite(x) for x in b])
    with np.errstate(all='ignore'):
        def ratio(ma, mb):
            r = ma / mb
            return np.where(np.isnan(r), np.inf, r)
        point = float(ratio(np.median(a), np.median(b)))
        rng = np.random.default_rng(SEED)
        ma = np.median(a[rng.integers(0, len(a), (NBOOT, len(a)))], axis=1)
        mb = np.median(b[rng.integers(0, len(b), (NBOOT, len(b)))], axis=1)
        r = ratio(ma, mb)
    return dict(point=point, ub95=float(pct(r, 95)), lo95=float(pct(r, 2.5)), hi95=float(pct(r, 97.5)), n_a=len(a), n_b=len(b))


def boot_median(x):
    """one-sample bootstrap of the median: point, one-sided 95 % upper bound, two-sided 95 % interval."""
    x = np.asarray(x, float)
    rng = np.random.default_rng(SEED)
    m = np.median(x[rng.integers(0, len(x), (NBOOT, len(x)))], axis=1)
    return dict(point=float(np.median(x)), ub95=float(pct(m, 95)), lo95=float(pct(m, 2.5)), hi95=float(pct(m, 97.5)), n=len(x))


def wilson(x, n, z):
    if n == 0:
        return 0.0, 1.0
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def newcombe_diff(x1, n1, x2, n2):
    """Newcombe hybrid score interval for p1 - p2 (method 10): one-sided 95 % upper (z = 1.645) and two-sided 95 % (z = 1.96)."""
    p1, p2 = x1 / n1, x2 / n2
    d = p1 - p2
    out = dict(point=d, p_a=p1, p_b=p2, n_a=n1, n_b=n2)
    for tag, z in (('one', Z1), ('two', Z2)):
        l1, u1 = wilson(x1, n1, z)
        l2, u2 = wilson(x2, n2, z)
        lo, hi = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
        if tag == 'one':
            out['ub95'] = hi
        else:
            out['lo95'], out['hi95'] = lo, hi
    return out


# --------------------------------------------------------------------------------------------- hypotheses
def camera_test(arm, off):
    """arm, off: lists of per-run camera dicts (m1, event). H1 / H3."""
    m1 = boot_median_ratio([r['m1'] for r in arm], [r['m1'] for r in off])
    m2 = newcombe_diff(sum(r['event'] for r in arm), len(arm), sum(r['event'] for r in off), len(off))
    m1['pass'] = bool(m1['ub95'] < M1_MARGIN)
    m2['pass'] = bool(m2['ub95'] < M2_MARGIN)
    m1['status'] = 'pass' if m1['pass'] else ('degradation' if m1['lo95'] > 1.0 else 'inconclusive at margin')       # A2.4
    m2['status'] = 'pass' if m2['pass'] else ('degradation' if m2['lo95'] > 0.0 else 'inconclusive at margin')
    return dict(M1=m1, M2=m2, passed=bool(m1['pass'] and m2['pass']))


def _wilcoxon_less(x):
    from scipy.stats import wilcoxon
    x = np.asarray(x, float)
    if len(x) < 2 or np.all(x == 0):
        return dict(p_one=None, p_two=None)
    return dict(p_one=float(wilcoxon(x, alternative='less').pvalue), p_two=float(wilcoxon(x, alternative='two-sided').pvalue))


def ped_h2(on_runs):
    """on_runs: per-run ped dicts of the ON arm (only runs with samples). H2(a) velocity vs B1-causal (log ratio, one-sided Wilcoxon), H2(b) position vs B0 (median ratio upper bound)."""
    runs = [r for r in on_runs if r is not None]
    if len(runs) < 3:
        return dict(n=len(runs), passed=False, note='too few runs with pedestrian samples')
    lr = np.log([r['vel']['on'] / r['vel']['B1c'] for r in runs])
    a = dict(n=len(lr), **_wilcoxon_less(lr), median_log_ratio=float(np.median(lr)), ci=boot_median(lr))
    a['median_ratio'] = float(np.exp(a['median_log_ratio']))
    a['pass'] = bool(a['p_one'] is not None and a['p_one'] < 0.05)
    pr = [r['pos']['on'] / r['pos']['B0'] for r in runs]
    b = boot_median(pr)
    b['pass'] = bool(b['ub95'] < POS_MARGIN)
    return dict(n=len(runs), a=a, b=b, passed=bool(a['pass'] and b['pass']))


def ped_h4(lev_runs, on_runs):
    from scipy.stats import mannwhitneyu
    lev, on = [r for r in lev_runs if r is not None], [r for r in on_runs if r is not None]
    if len(lev) < 3 or len(on) < 3:
        return dict(n_lev=len(lev), n_on=len(on), passed=False, note='too few runs with pedestrian samples')
    pl, po = np.array([r['pos']['on'] for r in lev]), np.array([r['pos']['on'] for r in on])
    vl, vo = np.array([r['vel']['on'] for r in lev]), np.array([r['vel']['on'] for r in on])
    mw = mannwhitneyu(pl, po, alternative='less')
    mw2 = mannwhitneyu(pl, po, alternative='two-sided')
    pos = dict(p_one=float(mw.pvalue), p_two=float(mw2.pvalue), ratio=boot_median_ratio(pl, po), pass_test=bool(mw.pvalue < 0.05))
    vr = float(np.median(vl) / np.median(vo))
    vel = dict(median_ratio=vr, ratio=boot_median_ratio(vl, vo), pass_cond=bool(vr <= VEL_MARGIN))
    return dict(n_lev=len(lev), n_on=len(on), pos=pos, vel=vel, passed=bool(pos['pass_test'] and vel['pass_cond']))


def evaluate(data):
    """data[cell][arm] = list of run records {k, cam:{m1,event,...}, ped: None | {pos:{est}, vel:{est}, ...}}. Confirmatory cells = SUBWAY (those present).
    Two independent families (A2.3), each a fixed sequence that stops at its first failure; each hypothesis must hold in every confirmatory cell."""
    cells = [c for c in SUBWAY if c in data]
    res = dict(cells=cells, per_cell={})
    for c in cells:
        d = data[c]
        cam = lambda arm: [r['cam'] for r in d[arm]]
        ped = lambda arm: [r['ped'] for r in d[arm]]
        res['per_cell'][c] = dict(H1=camera_test(cam('on'), cam('off')), H3=camera_test(cam('lev'), cam('off')), H2=ped_h2(ped('on')), H4=ped_h4(ped('lev'), ped('on')))
    fam = dict(camera=['H1', 'H3'], pedestrian=['H2', 'H4'])
    res['families'] = {}
    for f, seq in fam.items():
        stopped, out = False, {}
        for h in seq:
            holds = all(res['per_cell'][c][h]['passed'] for c in cells) if cells else False
            out[h] = dict(holds_in_every_cell=holds, tested=not stopped, per_cell={c: res['per_cell'][c][h]['passed'] for c in cells})
            if not stopped and not holds:
                stopped = True
        res['families'][f] = out
    return res


# --------------------------------------------------------------------------------------------- per-run extraction (disk)
def camera_record(r):
    """r: p9b_collect.run_record dict (+ exit_code) or a crash marker {crashed: True}."""
    if r.get('crashed'):
        return dict(m1=math.inf, event=True, crashed=True, ok=False)
    ev = (r.get('losses_resets') or 0) + (r.get('losses_new_maps') or 0)
    m1 = _finite(r.get('ate_se3')) if r.get('ok') else math.inf
    return dict(m1=m1, event=bool(ev >= 1), crashed=False, ok=bool(r.get('ok')), ate_sim3=r.get('ate_sim3'), abs_log_scale=r.get('abs_log_scale'), coverage=r.get('coverage'),
                scale_fail=bool((r.get('abs_log_scale') or 0) >= 1) if r.get('ok') else None, exit1=(r.get('exit_code') == 1), wall=r.get('wall_seconds'), rtf=r.get('rtf'),
                n_events=ev)


def _incl_maps(segs, gtcam, E):
    out = []
    for (t0, t1, c, ts) in segs:
        S = E.umeyama(c, gtcam.Twc(ts)[:, :3, 3])
        gc = gtcam.Twc(ts)[:, :3, 3]
        al = S[0] * (c @ S[1].T) + S[2]
        rmse = float(np.sqrt(np.mean(np.sum((al - gc) ** 2, axis=1))))
        extent = float(np.linalg.norm(al.max(0) - al.min(0)))
        ok = bool(abs(np.log(S[0])) < INCL['logs'] and rmse <= INCL['rmse'] and extent >= INCL['extent'] and len(ts) >= INCL['poses'])
        out.append(((t0, t1, S), ok, dict(s=float(S[0]), rmse=rmse, extent=extent, n=len(ts))))
    return out


def ped_record(rd, seq, arm, gtp, perc):
    """per-run pedestrian record of one flag-on run, or None if no included map / no matched sample."""
    sys.argv = ['c5_eval', '', '']          # c5_eval reads argv[2] at import (its main is guarded)
    import c3b_ped_error as E
    import c5_eval as C5
    import c5_b1 as B1
    C5.PERC = perc
    body, objs, Tbc = E.load_gt(gtp)
    gtcam = E.GtCam(body, Tbc)
    maps = _incl_maps(E.map_segments(rd), gtcam, E)
    segsim = [m[0] for m in maps]
    incl_ids = {id(m[0][2]) for m in maps if m[1]}
    if not incl_ids:
        return dict(none_included=True, n_maps=len(maps))
    log = E.read_log(rd)
    cfg = B1.read_cfg(CFG[arm])
    contacts, bias = C5.read_levels_log(rd) if arm == 'lev' else ({}, {})
    pdir = f'{perc}/{seq}'
    ests = {'on': log, 'B0': E.b0_estimates(log, pdir, C5.CL), 'B1c': C5.b1_estimates(log, pdir, cfg, segsim, 'causal', contacts),
            'B1r': C5.b1_estimates(log, pdir, cfg, segsim, 'rts', contacts)}
    pos, vel, velxy, world, keys_pos, keys_vel = {}, {}, {}, {}, [], []
    for name, est in ests.items():
        per, _ = E.group(est, segsim, True)
        per = {k: v for k, v in per.items() if k[1] in incl_ids}
        mc, _ = E.associate(per, objs, gtcam, 'cam')
        mw, _ = E.associate(per, objs, gtcam, 'world')
        rc, rv, rw = E.samples(per, mc, objs, gtcam), E.velocity_rows(per, mc, objs, b0=(name == 'B0')), E.samples(per, mw, objs, gtcam)
        pos[name] = {(r['kf'], r['track']): r['cam'] for r in rc}
        vel[name] = {(r['kf'], r['track']): r['vel'] for r in rv}
        velxy[name] = {(r['kf'], r['track']): r['vel_xy'] for r in rv}
        world[name] = {(r['kf'], r['track']): r['world'] for r in rw}
    kp = set.intersection(*[set(pos[n]) for n in EST])
    kv = set.intersection(*[set(vel[n]) for n in EST])
    if not kp or not kv:
        return dict(no_samples=True, n_maps=len(maps), n_pos=len(kp), n_vel=len(kv))
    med = lambda d, ks: {n: float(np.median([d[n][k] for k in ks])) for n in EST}
    rec = dict(pos=med(pos, kp), vel=med(vel, kv), vel_xy=med(velxy, kv), n_pos=len(kp), n_vel=len(kv), n_maps=len(maps), n_incl=len(incl_ids),
               world=med(world, set.intersection(*[set(world[n]) for n in EST])) if set.intersection(*[set(world[n]) for n in EST]) else None)
    # plausibility on the graph states of included maps (speed |v| s > 3 m/s, farther than 30 m from the camera)
    n = sp = ds = 0
    for (kf, t, tr, pw, Twc, vw) in log:
        S = E.sim_of(segsim, t)
        if S is None or id(S) not in incl_ids:
            continue
        Tcw = np.linalg.inv(Twc)
        n += 1
        sp += float(np.linalg.norm(vw) * S[0] > 3.0)
        ds += float(np.linalg.norm(Tcw[:3, :3] @ pw + Tcw[:3, 3]) > 30.0)
    rec['plaus'] = dict(n=n, speed=sp / n if n else None, dist=ds / n if n else None)
    if arm == 'lev':
        rec['lev'] = _levels_descr(rd, E, segsim, incl_ids, log)
        bv = np.array(list(bias.values())) if bias else np.zeros(0)
        rec['b'] = dict(n=len(bv), median=float(np.median(bv)) if len(bv) else None, p5=float(np.percentile(bv, 5)) if len(bv) else None, p95=float(np.percentile(bv, 95)) if len(bv) else None)
    return rec


def _levels_descr(rd, E, segsim, incl_ids, log):
    """levels descriptives: coverage (share of included-map graph states with an assigned, non-transitional contact), transitional share of assigned rows, alignment-free camera-height
    check (s (z_cam - z_level) vs 1.4895 m, as c5_levelcheck_camfree.py), contact-pixel residual share > 5 sigma (as c5_metrics.py)."""
    HCAM = 1.4895
    state = {(e[0], e[2]): e for e in log}
    assigned = trans = 0
    errs, used = [], 0
    p = f'{rd}/ped_levels.log'
    if os.path.exists(p):
        for l in open(p):
            x = l.split()
            if not x or x[0] in ('#', 'L', 'P', 'B') or int(x[5]) < 0:
                continue
            S = E.sim_of(segsim, float(x[2]))
            if S is None or id(S) not in incl_ids:
                continue
            assigned += 1
            if int(x[7]) != 0:
                trans += 1
                continue
            st = state.get((int(x[1]), int(x[3])))
            if st is not None:
                used += 1
                errs.append(S[0] * (st[4][2, 3] - float.fromhex(x[6])) - HCAM)
    e = np.array(errs)
    nstates = sum(1 for (kf, t, tr, pw, Twc, vw) in log if (E.sim_of(segsim, t) is not None and id(E.sim_of(segsim, t)) in incl_ids))
    out = dict(assigned=assigned, transitional=trans, used=used, n_states=nstates, coverage=used / nstates if nstates else None, transitional_share=trans / assigned if assigned else None,
               camh_median_err=float(np.median(e)) if len(e) else None, camh_share_within_0p10=float(np.mean(np.abs(e) <= 0.10)) if len(e) else None)
    q = f'{rd}/ped_floor_px.log'
    if os.path.exists(q):
        n = k = 0
        for l in open(q):
            if l[0] == '#' or not l.strip():
                continue
            x = l.split()
            S = E.sim_of(segsim, float(x[1]))
            if S is None or id(S) not in incl_ids:
                continue
            n += 1
            k += max(abs(float.fromhex(x[12])) / 6.0, abs(float.fromhex(x[13])) / 3.0) > 5.0
        out['contact_resid_share'] = k / n if n else None
        out['contact_resid_n'] = n
    return out


def collect(seq, root, out, allow_incomplete=False, gt_dir=GT_DIR_DEFAULT, perc=PERC_DEFAULT):
    import p9b_collect as K
    import p9b_ate as B
    os.makedirs(out, exist_ok=True)
    path = f'{out}/records_{seq}.json'
    if os.path.exists(path):
        raise SystemExit(f'refusing to overwrite {path}')
    crashed = set()
    if os.path.exists(f'{root}/crashed_final.txt'):
        crashed = {tuple(l.split()[:3]) for l in open(f'{root}/crashed_final.txt') if l.strip()}
    n = NRUN[seq]
    missing = [(arm, k) for arm in ARMS for k in range(1, n + 1)
               if not os.path.exists(f'{root}/{seq}/{arm}@{k}/md5.txt') and (seq, arm, str(k)) not in crashed]
    if missing and not allow_incomplete:
        raise SystemExit(f'{seq}: {len(missing)} runs incomplete (first: {missing[:3]}); no analysis before every run of a cell is complete (criterion section 8)')
    flat = f'{out}/flat'
    gt = B.A.load_tum(f'{K.GT_DIR}/{seq}_gt_body.tum')
    tbc = json.load(open(f'{K.GT_DIR}/{seq}_gt_summary.json'))['T_b_c']
    data = {a: [] for a in ARMS}
    for arm in ARMS:
        os.makedirs(f'{flat}/{arm}', exist_ok=True)
        for k in range(1, n + 1):
            rd = f'{root}/{seq}/{arm}@{k}'
            if not os.path.exists(rd + '/md5.txt'):
                data[arm].append(dict(k=k, cam=camera_record(dict(crashed=True)), ped=None, missing=(arm, k) in missing))
                continue
            dst = f'{flat}/{arm}/{seq}_inertial_s{k}'
            if not os.path.lexists(dst):
                os.symlink(rd, dst)
            r = K.run_record(dst, gt, tbc)
            prov = open(rd + '/provenance.txt').read()
            r['exit_code'] = int([l for l in prov.splitlines() if l.startswith('runner_exit=')][-1].split('=')[1])
            cam = camera_record(r)
            ped = None
            if arm != 'off' and cam['ok'] and os.path.exists(rd + '/ped_log.txt'):
                ped = ped_record(rd, seq, arm, f'{gt_dir}/{seq}_gt.npz', perc)
            data[arm].append(dict(k=k, cam=cam, ped=ped))
    json.dump(dict(seq=seq, n=n, data=data), open(path, 'w'), indent=1, default=lambda o: None if isinstance(o, float) and math.isnan(o) else o)
    print('wrote', path)


# --------------------------------------------------------------------------------------------- report
def _usable(p):
    return p if (p is not None and 'pos' in p) else None


def load_records(out):
    data = {}
    for f in sorted(glob.glob(f'{out}/records_*.json')):
        d = json.load(open(f))
        data[d['seq']] = {a: [dict(r, cam=_revive(r['cam']), ped=_usable(r['ped'])) for r in d['data'][a]] for a in ARMS}
    return data


def _revive(c):
    c = dict(c)
    c['m1'] = math.inf if c['m1'] is None else c['m1']
    return c


def _f(x, p=3):
    return '—' if x is None else (f'{x:.{p}f}' if np.isfinite(x) else 'inf')


def descriptives(data):
    desc = {}
    for seq, d in data.items():
        desc[seq] = {}
        for arm in ARMS:
            rs, cs = d[arm], [r['cam'] for r in d[arm]]
            ok = [c for c in cs if c['ok']]
            med = lambda key: float(np.median([c[key] for c in ok if c.get(key) is not None])) if any(c.get(key) is not None for c in ok) else None
            ps = [r['ped'] for r in rs if r['ped'] is not None]
            allped = [r['ped'] for r in rs]
            pd = dict(n_runs=len(rs), n_crashed=sum(c['crashed'] for c in cs), n_ok=len(ok), median_se3=float(np.median([c['m1'] for c in cs])),
                      median_sim3=med('ate_sim3'), median_abs_log_s=med('abs_log_scale'), median_coverage=med('coverage'),
                      scale_failure=float(np.mean([bool(c['scale_fail']) for c in ok])) if ok else None, exit1=float(np.mean([c['exit1'] for c in ok])) if ok else None,
                      map_event_rate=float(np.mean([c['event'] for c in cs])), wall_median=med('wall'), rtf_median=med('rtf'),
                      n_with_ped=len(ps), n_no_included_map=sum(1 for p in allped if p is not None and p.get('none_included')))
            if ps:
                for key in ('pos', 'vel', 'vel_xy'):
                    pd[key] = {e: float(np.median([p[key][e] for p in ps])) for e in EST}
                pd['plaus_speed_median'] = float(np.median([p['plaus']['speed'] for p in ps if p['plaus']['speed'] is not None])) if any(p['plaus']['speed'] is not None for p in ps) else None
                pd['plaus_dist_median'] = float(np.median([p['plaus']['dist'] for p in ps if p['plaus']['dist'] is not None])) if any(p['plaus']['dist'] is not None for p in ps) else None
                if arm == 'lev':
                    for key in ('coverage', 'transitional_share', 'camh_median_err', 'camh_share_within_0p10', 'contact_resid_share'):
                        v = [p['lev'][key] for p in ps if p.get('lev') and p['lev'].get(key) is not None]
                        pd['lev_' + key] = float(np.median(v)) if v else None
                    pd['b_median_of_medians'] = float(np.median([p['b']['median'] for p in ps if p.get('b') and p['b']['median'] is not None] or [np.nan]))
            desc[seq][arm] = pd
    return desc


def markdown(res, desc, data):
    L = ['# P9-D results (frozen p9d_analyze.py)', '']
    if res['cells']:
        L += ['## Hypotheses (A2.3: two independent families, fixed sequence within each; each must hold in every confirmatory cell)', '']
        for f, hs in res['families'].items():
            L.append(f'**{f} family**: ' + '; '.join(f"{h}: {'HOLDS' if v['holds_in_every_cell'] else 'FAILS'}{'' if v['tested'] else ' (not tested: earlier hypothesis failed; quantities are descriptive)'}" for h, v in hs.items()))
        L.append('')
        L += ['| cell | hyp | quantity | point | two-sided 95 % interval | one-sided 95 % upper / p | criterion | status |', '|---|---|---|---|---|---|---|---|']
        for c in res['cells']:
            pc = res['per_cell'][c]
            for h in ('H1', 'H3'):
                m1, m2 = pc[h]['M1'], pc[h]['M2']
                L.append(f"| {c} | {h} | M1 median ratio | {_f(m1['point'])} | {_f(m1['lo95'])} – {_f(m1['hi95'])} | {_f(m1['ub95'])} | < {M1_MARGIN} | {m1['status']} |")
                L.append(f"| {c} | {h} | M2 map-event rate diff | {_f(m2['point'])} ({_f(m2['p_a'])} vs {_f(m2['p_b'])}) | {_f(m2['lo95'])} – {_f(m2['hi95'])} | {_f(m2['ub95'])} | < +{M2_MARGIN} | {m2['status']} |")
            h2 = pc['H2']
            if 'a' in h2:
                a, b = h2['a'], h2['b']
                L.append(f"| {c} | H2(a) | median graph/B1-causal velocity ratio (n={a['n']}) | {_f(a['median_ratio'])} | {_f(math.exp(a['ci']['lo95']))} – {_f(math.exp(a['ci']['hi95']))} | p={_f(a['p_one'], 4)} | p < 0.05 | {'pass' if a['pass'] else 'fail'} |")
                L.append(f"| {c} | H2(b) | median per-run graph/B0 position ratio | {_f(b['point'])} | {_f(b['lo95'])} – {_f(b['hi95'])} | {_f(b['ub95'])} | < {POS_MARGIN} | {'pass' if b['pass'] else 'fail'} |")
            else:
                L.append(f"| {c} | H2 | — | — | — | — | — | {h2.get('note')} |")
            h4 = pc['H4']
            if 'pos' in h4:
                L.append(f"| {c} | H4 position | median LEV/ON position ratio (n={h4['n_lev']}/{h4['n_on']}) | {_f(h4['pos']['ratio']['point'])} | {_f(h4['pos']['ratio']['lo95'])} – {_f(h4['pos']['ratio']['hi95'])} | p={_f(h4['pos']['p_one'], 4)} | p < 0.05 | {'pass' if h4['pos']['pass_test'] else 'fail'} |")
                L.append(f"| {c} | H4 velocity | median LEV/ON velocity ratio | {_f(h4['vel']['median_ratio'])} | {_f(h4['vel']['ratio']['lo95'])} – {_f(h4['vel']['ratio']['hi95'])} | — | <= {VEL_MARGIN} | {'pass' if h4['vel']['pass_cond'] else 'fail'} |")
            else:
                L.append(f"| {c} | H4 | — | — | — | — | — | {h4.get('note')} |")
        L.append('')
    L += ['## Descriptive (section 6; no inference)', '']
    for seq, d in desc.items():
        L += [f'### {seq}', '', '| arm | runs | crashed | median SE(3) | median Sim(3) | median abs log s | coverage | scale fail | exit 1 | map-event rate | wall s | rtf | runs with ped / none included |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for arm, p in d.items():
            L.append(f"| {arm} | {p['n_runs']} | {p['n_crashed']} | {_f(p['median_se3'])} | {_f(p['median_sim3'])} | {_f(p['median_abs_log_s'], 4)} | {_f(p['median_coverage'])} | {_f(p['scale_failure'], 2)} | {_f(p['exit1'], 2)} | {_f(p['map_event_rate'], 2)} | {_f(p['wall_median'], 0)} | {_f(p['rtf_median'], 2)} | {p['n_with_ped']} / {p['n_no_included_map']} |")
        L += ['', '| arm | estimator | median pos (cam) | median vel (world) | median vel_xy |', '|---|---|---|---|---|']
        for arm, p in d.items():
            for e in EST if 'pos' in p else []:
                L.append(f"| {arm} | {e} | {_f(p['pos'][e])} | {_f(p['vel'][e])} | {_f(p['vel_xy'][e])} |")
        L += ['', '| arm | plausibility speed>3 m/s | dist>30 m | levels: coverage | transitional | camera-height median err | share <=0.10 m | contact resid >5 sigma | per-track b median |', '|---|---|---|---|---|---|---|---|---|']
        for arm, p in d.items():
            if 'pos' in p:
                L.append(f"| {arm} | {_f(p.get('plaus_speed_median'), 4)} | {_f(p.get('plaus_dist_median'), 4)} | {_f(p.get('lev_coverage'))} | {_f(p.get('lev_transitional_share'))} | {_f(p.get('lev_camh_median_err'))} | {_f(p.get('lev_camh_share_within_0p10'), 2)} | {_f(p.get('lev_contact_resid_share'))} | {_f(p.get('b_median_of_medians'))} |")
        L.append('')
    return '\n'.join(L) + '\n'


def report(out):
    data = load_records(out)
    res = evaluate(data) if any(c in data for c in SUBWAY) else dict(cells=[], per_cell={}, families={})
    desc = descriptives(data)
    json.dump(dict(results=res, descriptive=desc), open(f'{out}/results.json', 'w'), indent=1, default=lambda o: None if isinstance(o, float) and not np.isfinite(o) else o)
    open(f'{out}/results.md', 'w').write(markdown(res, desc, data))
    print(f'wrote {out}/results.json and results.md')


# --------------------------------------------------------------------------------------------- self test
def _synth_cell(rng, n, off_med, on_ratio, ev_off, ev_arm, vel_ratio=1.0, pos_ratio=1.0, ped=True):
    def cam(med, ev):
        return [dict(k=i + 1, cam=dict(m1=float(med * np.exp(rng.normal(0, 0.2))), event=bool(rng.random() < ev), crashed=False, ok=True, ate_sim3=1.0, abs_log_scale=0.05, coverage=0.99,
                                         scale_fail=False, exit1=False, wall=1400.0, rtf=1.0), ped=None) for i in range(n)]
    d = dict(off=cam(off_med, ev_off), on=cam(off_med * on_ratio, ev_arm), lev=cam(off_med * on_ratio, ev_arm))
    if ped:
        for arm, vr, pr in (('on', 0.8, 1.0), ('lev', 0.8 * vel_ratio, pos_ratio)):
            for r in d[arm]:
                b0 = 1.0 * np.exp(rng.normal(0, 0.1))
                r['ped'] = dict(pos=dict(on=b0 * pr, B0=b0, B1c=b0 * 0.97, B1r=b0 * 0.9), vel=dict(on=vr * np.exp(rng.normal(0, 0.1)), B0=1.5, B1c=1.0, B1r=0.7),
                                vel_xy=dict(on=0.5, B0=0.5, B1c=0.5, B1r=0.5), n_pos=10, n_vel=10, n_maps=1, n_incl=1, plaus=dict(n=10, speed=0.0, dist=0.0), world=None)
    return d


def selftest():
    rng = np.random.default_rng(1)
    # 1. no true effect on the camera, ON better than B1-causal on velocity, LEV better than ON on position -> everything passes
    data = {c: _synth_cell(rng, 60, 3.0, 1.0, 0.1, 0.1, vel_ratio=1.0, pos_ratio=0.8) for c in SUBWAY}
    res = evaluate(data)
    assert all(v['holds_in_every_cell'] for f in res['families'].values() for v in f.values()), json.dumps(res['families'])
    # 2. ON degrades M1 by +40 % -> H1 fails, H3 not tested; the pedestrian family is unaffected (A2.3)
    data = {c: _synth_cell(rng, 60, 3.0, 1.4, 0.1, 0.1, pos_ratio=0.8) for c in SUBWAY}
    res = evaluate(data)
    assert not res['families']['camera']['H1']['holds_in_every_cell'] and not res['families']['camera']['H3']['tested']
    assert res['families']['pedestrian']['H2']['holds_in_every_cell'] and res['families']['pedestrian']['H4']['holds_in_every_cell']
    m1 = res['per_cell'][SUBWAY[0]]['H1']['M1']
    assert m1['status'] == 'degradation' and m1['lo95'] > 1.0
    # 3. a failing cell blocks the hypothesis ("both cells")
    data = {SUBWAY[0]: _synth_cell(rng, 60, 3.0, 1.0, 0.1, 0.1, pos_ratio=0.8), SUBWAY[1]: _synth_cell(rng, 60, 3.0, 1.4, 0.1, 0.1, pos_ratio=0.8)}
    assert not evaluate(data)['families']['camera']['H1']['holds_in_every_cell']
    # 4. map-event rate +0.35 -> M2 fails; velocity worse than B1c -> H2(a) fails; LEV velocity 130 % -> H4 fails
    data = {c: _synth_cell(rng, 60, 3.0, 1.0, 0.1, 0.45, vel_ratio=1.3, pos_ratio=0.8) for c in SUBWAY}
    res = evaluate(data)
    assert not res['per_cell'][SUBWAY[0]]['H1']['M2']['pass'] and not res['per_cell'][SUBWAY[0]]['H4']['passed']
    # 5. failures count as +inf: 40 % of ON runs with no metric -> the median is inf -> fails, status degradation (lower bound > 1)
    data = {c: _synth_cell(rng, 60, 3.0, 1.0, 0.1, 0.1, pos_ratio=0.8) for c in SUBWAY}
    for c in SUBWAY:
        for r in data[c]['on'][:36]:
            r['cam'] = camera_record(dict(crashed=True))
    res = evaluate(data)
    assert not res['per_cell'][SUBWAY[0]]['H1']['M1']['pass']
    # 6. exact arithmetic of the interval helpers
    d = newcombe_diff(5, 60, 5, 60)
    assert abs(d['point']) < 1e-12 and d['lo95'] < 0 < d['hi95']
    r = boot_median_ratio([2.0] * 20, [1.0] * 20)
    assert r['point'] == 2.0 and r['lo95'] == 2.0
    print('selftest OK')


def stage0_test(runs_jsonl):
    """Stage 0 flag-off records used as OFF and as a fake ON / LEV (identical records): every camera ratio must be 1, every difference 0, no hypothesis may report a degradation."""
    recs = [json.loads(l) for l in open(runs_jsonl)]
    for seq in SUBWAY + [OFFICE]:
        cs = [camera_record(r) for r in recs if r['seq'] == seq]
        if not cs:
            continue
        t = camera_test(cs, cs)
        assert t['M1']['point'] == 1.0 and abs(t['M2']['point']) < 1e-12 and t['M1']['status'] != 'degradation' and t['M2']['status'] != 'degradation', (seq, t)
        print(seq, 'n=%d' % len(cs), 'M1 ratio %.3f [%.3f, %.3f] ub %.3f' % (t['M1']['point'], t['M1']['lo95'], t['M1']['hi95'], t['M1']['ub95']),
              'M2 diff %.3f ub %.3f' % (t['M2']['point'], t['M2']['ub95']), 'events %.2f' % t['M2']['p_a'], 'inf runs %d' % sum(not np.isfinite(c['m1']) for c in cs))
    print('stage0 test OK')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'collect':
        collect(a[1], a[2], a[3], allow_incomplete='--allow-incomplete' in a)
    elif a and a[0] == 'report':
        report(a[1])
    elif a and a[0] == 'stage0test':
        stage0_test(a[1])
    elif a and a[0] == 'selftest':
        selftest()
    else:
        raise SystemExit(__doc__)
