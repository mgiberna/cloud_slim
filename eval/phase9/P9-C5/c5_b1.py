#!/usr/bin/env python3
"""P9-C5 baseline B1 (per-track Kalman filter + RTS, offline from a run's rows) GIVEN THE SAME CONTACTS, LEVELS AND b as the graph (c5_continue.md section 3):
c3b_b1.py (isotropic motion prior q = Qv, root pixel, log range with the range-consistency gate) plus, for the levels arms (cfg FloorContact levels | levels_platform):
  * a per-track log-scale bias state b (prior N(0, BiasSigma^2), constant in time), the range measurement being log z_c - b (as the graph's EdgePedLogRange with the bias vertex);
  * for each row with a contact the graph used (assigned to a level, not transitional: ped_levels.log; contact pixel = the perception F row; level height z_l = the level's height at the
    last write of that contact): the image-space measurement  (u, v)_contact = pi(R_cw (p_x, p_y, z_l + delta_v) + t_cw),  sigma = (FloorSigmaPxU, FloorSigmaPxV), Huber sqrt(5.991)
    (EdgePedLevelPx). The level heights and b are those the model uses; B1 estimates b itself (same model, prior and measurements as the graph, no BA).
FloorContact none: exactly c3b_b1.run_segment (no b, no contact). The platform prior F3 has no B1 counterpart (it constrains the camera and the level, not the person).
rows: time-ordered dicts (t, Twc, u, v, lpx, maskh [, fu, fv, zl])."""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'P9-C3'))
import c3b_b1 as B
from c3b_b1 import F, CX, CY, HUBER_2D, HUBER_1D, read_cfg, gate_ok, _huber_update  # noqa: F401


def _huber_update_diag(x, P, z, h, J, sigs, delta):
    r = z - h
    w = float(np.sqrt(np.sum((r / sigs) ** 2)))
    infl = 1.0 if w <= delta else w / delta
    R = np.diag(sigs ** 2) * infl
    S = J @ P @ J.T + R
    K = P @ J.T @ np.linalg.inv(S)
    x = x + K @ r
    I_KJ = np.eye(len(x)) - K @ J
    P = I_KJ @ P @ I_KJ.T + K @ R @ K.T
    return x, 0.5 * (P + P.T)


def run_segment(rows, cfg, smooth):
    withb = str(cfg.get('FloorContact', 'none')) in ('levels', 'levels_platform')
    if not withb:
        return B.run_segment(rows, cfg, smooth)
    q = cfg['Qv']; H0 = cfg['StatureFixedM']; cL = cfg['SkeletonOverStature']; n = 7
    dv = cfg['FloorMidDeltaM']; sig = np.array([cfg['FloorSigmaPxU'], cfg['FloorSigmaPxV']])
    xs, Ps, xp, Pp, Fs = [], [], [], [], []
    x = None; P = None; tprev = None
    for k, r in enumerate(rows):
        Twc = r['Twc']; Rcw = Twc[:3, :3].T; tcw = -Rcw @ Twc[:3, 3]
        ok = gate_ok(cfg, r['lpx'], r['maskh'])
        if x is None:
            b = np.array([(r['u'] - CX) / F, (r['v'] - CY) / F, 1.0])
            rng = (F * cL * H0 / r['lpx']) if ok else (F * cfg['MaskHeightM'] / max(r['maskh'], 1.0))
            x = np.zeros(n); x[:6] = np.concatenate([Twc[:3, :3] @ (rng * b) + Twc[:3, 3], np.zeros(3)])
            P = np.diag([50.0 ** 2] * 3 + [5.0 ** 2] * 3 + [cfg['BiasSigma'] ** 2])
            Fk = np.eye(n); xpred, Ppred = x.copy(), P.copy()
        else:
            dt = r['t'] - tprev
            Fk = np.eye(n); Fk[:3, 3:6] = dt * np.eye(3)
            Q = np.zeros((n, n))
            Q[:3, :3] = q * dt ** 3 / 3 * np.eye(3); Q[:3, 3:6] = Q[3:6, :3] = q * dt ** 2 / 2 * np.eye(3); Q[3:6, 3:6] = q * dt * np.eye(3)
            xpred = Fk @ x; Ppred = Fk @ P @ Fk.T + Q
            x, P = xpred, Ppred
        xp.append(xpred.copy()); Pp.append(Ppred.copy()); Fs.append(Fk)
        Xc = Rcw @ x[:3] + tcw
        if Xc[2] > 0.5:
            h = np.array([F * Xc[0] / Xc[2] + CX, F * Xc[1] / Xc[2] + CY])
            dpi = np.array([[F / Xc[2], 0, -F * Xc[0] / Xc[2] ** 2], [0, F / Xc[2], -F * Xc[1] / Xc[2] ** 2]])
            J = np.zeros((2, n)); J[:, :3] = dpi @ Rcw
            x, P = _huber_update(x, P, np.array([r['u'], r['v']]), h, J, cfg['RootPxSigma'], HUBER_2D)
        if ok:
            Xc = Rcw @ x[:3] + tcw
            zc = Xc[2]
            if zc > 0.5:
                h = np.array([np.log(zc) - x[6]])
                J = np.zeros((1, n)); J[0, :3] = np.array([0.0, 0.0, 1.0 / zc]) @ Rcw; J[0, 6] = -1.0
                zlog = np.array([np.log(F) + np.log(cL) + np.log(H0) - np.log(r['lpx'])])
                x, P = _huber_update(x, P, zlog, h, J, cfg['LogDepthSigma'], HUBER_1D)
        if r.get('zl') is not None:                       # contact of a level, image-space residual (EdgePedLevelPx)
            Fw = np.array([x[0], x[1], r['zl'] + dv])
            Xc = Rcw @ Fw + tcw
            if Xc[2] > 0.5:
                h = np.array([F * Xc[0] / Xc[2] + CX, F * Xc[1] / Xc[2] + CY])
                dpi = np.array([[F / Xc[2], 0, -F * Xc[0] / Xc[2] ** 2], [0, F / Xc[2], -F * Xc[1] / Xc[2] ** 2]])
                J = np.zeros((2, n)); J[:, :2] = (dpi @ Rcw)[:, :2]
                x, P = _huber_update_diag(x, P, np.array([r['fu'], r['fv']]), h, J, sig, HUBER_2D * cfg.get('HuberScale', 1.0))
        xs.append(x.copy()); Ps.append(P.copy()); tprev = r['t']
    out = dict(causal=[(s[:3], s[3:6], H0) for s in xs], P_causal=Ps, b_causal=[s[6] for s in xs])
    if smooth:
        m = len(xs); xsm = [None] * m; Psm = [None] * m
        xsm[-1], Psm[-1] = xs[-1], Ps[-1]
        for k in range(m - 2, -1, -1):
            C = Ps[k] @ Fs[k + 1].T @ np.linalg.inv(Pp[k + 1])
            xsm[k] = xs[k] + C @ (xsm[k + 1] - xp[k + 1])
            Psm[k] = Ps[k] + C @ (Psm[k + 1] - Pp[k + 1]) @ C.T
            Psm[k] = 0.5 * (Psm[k] + Psm[k].T)
        out.update(rts=[(s[:3], s[3:6], H0) for s in xsm], P_rts=Psm, b_rts=[s[6] for s in xsm])
    return out
