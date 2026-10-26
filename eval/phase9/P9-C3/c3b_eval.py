#!/usr/bin/env python3
"""P9-C2 step 5c evaluation. For every (variant, sequence, seed) run: flag-on, B0, B1-causal, B1-RTS with the SAME rows, associations and
error definitions (p9c_ped_error.py: camera-frame association for the primary camera-frame metric, P2-D association for the world frame,
world-frame velocity error), with the office evaluation filter (maps with |log s| < 0.2) and unfiltered.
Usage: c3b_eval.py OUT.pkl ROOT_Z1   (P9_C3 variants: env P9C_VARIANTS=name:label,...; roots by label)"""
import os, pickle, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3b_ped_error as E
import c3b_b1 as B1
from c3b_iter import cam, GTP, PED, TUNE
CL = 0.855387     # c_L, depth-z model (constants_z.json)
VARIANTS = {'v0': 'z1'}
if os.environ.get('P9C_VARIANTS'):
    VARIANTS = dict(x.split(':') for x in os.environ['P9C_VARIANTS'].split(','))
CFGDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'variants')
roots = {lab: sys.argv[2] for lab in VARIANTS.values()}   # one root for all labels (the none arm: pass z1; the variants: pass c3b via separate calls)


from c3b_eval_io import foot_row, read_floor_log


def b1_estimates(log, pdir, cfg, segsim, which, flog=None):
    groups = {}
    for (kf, t, tr, pw, Twc, vw) in log:
        row = E.percep_row(pdir, t, tr)
        S = E.sim_of(segsim, t)
        if row is None or row[2] <= 0 or S is None:
            continue
        d = dict(kf=kf, t=t, tr=tr, Twc=Twc, u=row[0], v=row[1], lpx=row[2], maskh=row[3])
        if flog and (kf, tr) in flog:
            ft = foot_row(pdir, t, tr)
            if ft is not None:
                d.update(fu=ft[0], fv=ft[1], zp=flog[(kf, tr)])
        groups.setdefault((tr, id(S)), []).append(d)
    out = []
    for g in groups.values():
        g.sort(key=lambda r: r['t'])
        res = B1.run_segment(g, cfg, smooth=(which == 'rts'))
        for r, (p, v, H) in zip(g, res[which]):
            out.append((r['kf'], r['t'], r['tr'], p, r['Twc'], v))
    return out


def pack(rows_cam, rows_world, rows_vel):
    return dict(cam=[(r['kf'], r['track'], r['cam'], r['range_gt']) for r in rows_cam],
                world=[(r['kf'], r['track'], r['world']) for r in rows_world],
                vel=[(r['kf'], r['track'], r['vel']) for r in rows_vel])


def evaluate_run(rd, seq, cfg, metric_only):
    flog = read_floor_log(rd) if str(cfg.get('FloorContact', 'none')) != 'none' else None
    body, objs, Tbc = E.load_gt(GTP[seq]); gtcam = E.GtCam(body, Tbc)
    segsim = [(t0, t1, E.umeyama(c, gtcam.Twc(ts)[:, :3, 3])) for (t0, t1, c, ts) in E.map_segments(rd)]
    log = E.read_log(rd)
    pdir = f'{PED}/{seq}'
    ests = {'on': log, 'B0': E.b0_estimates(log, pdir, CL),
            'B1c': b1_estimates(log, pdir, cfg, segsim, 'causal', flog), 'B1r': b1_estimates(log, pdir, cfg, segsim, 'rts', flog)}
    out = {}
    for name, est in ests.items():
        per, _ = E.group(est, segsim, metric_only)
        nn = E.group.n_nonmetric
        mc, _ = E.associate(per, objs, gtcam, 'cam'); mw, _ = E.associate(per, objs, gtcam, 'world')
        out[name] = dict(pack(E.samples(per, mc, objs, gtcam), E.samples(per, mw, objs, gtcam), E.velocity_rows(per, mc, objs, b0=(name == 'B0'))),
                         n_states=len(est), n_nonmetric=nn, n_tracks=len(per))
    return out


res = {}
for v, lab in VARIANTS.items():
    cfg = B1.read_cfg(f'{CFGDIR}/{v}.yaml')
    for seq in TUNE:
        for k in range(1, 6):
            rd = f'{roots[lab]}/{v}@{k}/on_{seq}'
            if not os.path.exists(f'{rd}/ped_log.txt'):
                print('MISSING', rd); continue
            c = cam(rd, seq)
            counters = None
            if os.path.exists(f'{rd}/ped_counters.csv'):
                last = open(f'{rd}/ped_counters.csv').read().strip().split('\n'); hdr = last[0].split(','); tot = last[-1].split(',')
                counters = {hdr[i]: int(tot[i]) for i in range(3, len(hdr))}
            res[(v, seq, k)] = dict(cam=c, counters=counters, filtered=evaluate_run(rd, seq, cfg, True), unfiltered=evaluate_run(rd, seq, cfg, False))
            print(v, seq, k, 'done', flush=True)
pickle.dump(res, open(sys.argv[1], 'wb'))
