#!/usr/bin/env python3
"""P9-C5 evaluation (c4_eval.py with c5_b1: B1 given the same contacts, levels and b). For every (variant, sequence, seed) run: graph ('on'), B0, B1-causal, B1-RTS with the SAME rows,
associations and error definitions (c3b_ped_error.py, frozen), metric maps only (|log s| < 0.2). Variants none | levels | levels_platform (config/variants/<v>.yaml).
Also collects: camera descriptives (c3b_iter.cam), per-track b on metric maps (B rows of ped_levels.log: the last written b of each (map, track), with its map's |log s|).
Usage: c5_eval.py OUT.pkl RUNS_ROOT      (RUNS_ROOT/<variant>@<seed>/on_<seq>)"""
import os, pickle, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'P9-C3'))
sys.path.insert(0, HERE)
import c3b_ped_error as E
import c5_b1 as B1
from c3b_iter import cam, GTP, PED, TUNE
CL = 0.855387
PERC = '/media/marco/muffin1/datasets/p9c3c_perception'
VARIANTS = ['none', 'levels', 'levels_platform']
CFGDIR = os.path.join(HERE, 'config', 'variants')
root = sys.argv[2]


def read_levels_log(rd):
    """contacts the graph used: {(kf, track): (level z, map)} for rows assigned to a level and not transitional; b rows {(map, track): b at the last write}."""
    con, b = {}, {}
    p = f'{rd}/ped_levels.log'
    if not os.path.exists(p):
        return con, b
    last = {}
    for l in open(p):
        x = l.split()
        if not x or x[0] in ('#', 'L', 'P'):
            continue
        if x[0] == 'B':
            kf = int(x[2]); b[(int(x[1]), int(x[3]))] = (kf, float.fromhex(x[4])) if (int(x[1]), int(x[3])) not in b or kf >= b[(int(x[1]), int(x[3]))][0] else b[(int(x[1]), int(x[3]))]
            continue
        if int(x[5]) >= 0 and int(x[7]) == 0:
            con[(int(x[1]), int(x[3]))] = (float.fromhex(x[6]), int(x[0]))
    return con, {k: v[1] for k, v in b.items()}


_fc = {}
def foot_row(pdir, stamp, track):
    key = (pdir, stamp)
    if key not in _fc:
        rows = {}
        try:
            for l in open(f'{pdir}/{int(round(stamp * 1e6)):019d}.ped.txt'):
                if l.startswith('F '):
                    x = l.split(); rows[int(x[1])] = (float(x[2]), float(x[3]))
        except FileNotFoundError:
            pass
        _fc[key] = rows
    return _fc[key].get(track)


def b1_estimates(log, pdir, cfg, segsim, which, contacts):
    groups = {}
    for (kf, t, tr, pw, Twc, vw) in log:
        row = E.percep_row(pdir, t, tr)
        S = E.sim_of(segsim, t)
        if row is None or row[2] <= 0 or S is None:
            continue
        d = dict(kf=kf, t=t, tr=tr, Twc=Twc, u=row[0], v=row[1], lpx=row[2], maskh=row[3])
        c = contacts.get((kf, tr))
        f = foot_row(PERC + '/' + os.path.basename(pdir), t, tr) if c else None
        if c and f:
            d.update(fu=f[0], fv=f[1], zl=c[0])
        groups.setdefault((tr, id(S)), []).append(d)
    out = []
    for g in groups.values():
        g.sort(key=lambda r: r['t'])
        res = B1.run_segment(g, cfg, smooth=(which == 'rts'))
        subs = res['subs'] if 'subs' in res else [dict(idx=list(range(len(g))), causal=res['causal'], rts=res.get('rts'))]
        for sub in subs:
            for ix, (p, v, H) in zip(sub['idx'], sub[which]):
                r = g[ix]
                out.append((r['kf'], r['t'], r['tr'], p, r['Twc'], v))
    return out


def pack(rows_cam, rows_world, rows_vel):
    return dict(cam=[(r['kf'], r['track'], r['cam'], r['range_gt']) for r in rows_cam],
                world=[(r['kf'], r['track'], r['world']) for r in rows_world],
                vel=[(r['kf'], r['track'], r['vel']) for r in rows_vel])


def evaluate_run(rd, seq, cfg, metric_only):
    body, objs, Tbc = E.load_gt(GTP[seq]); gtcam = E.GtCam(body, Tbc)
    segsim = [(t0, t1, E.umeyama(c, gtcam.Twc(ts)[:, :3, 3])) for (t0, t1, c, ts) in E.map_segments(rd)]
    log = E.read_log(rd)
    pdir = f'{PED}/{seq}'
    contacts, bias = read_levels_log(rd)
    ests = {'on': log, 'B0': E.b0_estimates(log, pdir, CL),
            'B1c': b1_estimates(log, pdir, cfg, segsim, 'causal', contacts), 'B1r': b1_estimates(log, pdir, cfg, segsim, 'rts', contacts)}
    out = {}
    for name, est in ests.items():
        per, _ = E.group(est, segsim, metric_only)
        nn = E.group.n_nonmetric
        mc, _ = E.associate(per, objs, gtcam, 'cam'); mw, _ = E.associate(per, objs, gtcam, 'world')
        out[name] = dict(pack(E.samples(per, mc, objs, gtcam), E.samples(per, mw, objs, gtcam), E.velocity_rows(per, mc, objs, b0=(name == 'B0'))),
                         n_states=len(est), n_nonmetric=nn, n_tracks=len(per))
    # per-track b on metric maps: (map, track) -> (b, |log s| of the map segment holding the track's last state)
    bt = []
    stamp_of = {(e[0], e[2]): e[1] for e in log}
    mapof = {}
    for l in open(f'{rd}/ped_levels.log') if os.path.exists(f'{rd}/ped_levels.log') else []:
        x = l.split()
        if x and x[0] not in ('#', 'L', 'P', 'B'):
            mapof[(int(x[1]), int(x[3]))] = int(x[0])
    for (m, tr), bv in bias.items():
        ks = [k for k, mm in mapof.items() if mm == m and k[1] == tr and k in stamp_of]
        if not ks:
            continue
        S = E.sim_of(segsim, stamp_of[max(ks)])
        bt.append((m, tr, bv, None if S is None else float(abs(np.log(S[0])))))
    out['b_tracks'] = bt
    out['n_contacts'] = len(contacts)
    return out


if __name__ == '__main__':
    res = {}
    for v in VARIANTS:
        cfg = B1.read_cfg(f'{CFGDIR}/{v}.yaml')
        for seq in TUNE:
            for k in range(1, 6):
                rd = f'{root}/{v}@{k}/on_{seq}'
                if not os.path.exists(f'{rd}/ped_log.txt'):
                    print('MISSING', rd); continue
                c = cam(rd, seq)
                counters = None
                if os.path.exists(f'{rd}/ped_counters.csv'):
                    last = open(f'{rd}/ped_counters.csv').read().strip().split('\n'); hdr = last[0].split(','); tot = last[-1].split(',')
                    counters = {hdr[i]: int(tot[i]) for i in range(3, len(hdr))}
                res[(v, seq, k)] = dict(cam=c, counters=counters, filtered=evaluate_run(rd, seq, cfg, True))
                print(v, seq, k, 'done', flush=True)
    pickle.dump(res, open(sys.argv[1], 'wb'))
