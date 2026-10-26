#!/usr/bin/env python3
"""P9-C2 5c baseline B1: per-track Kalman filter (offline, from the outputs of a run).
State x = [p (3), v (3)] : world-frame root position and velocity; the stature is the constant H0 = StatureFixedM (P9-C2 5d: a free per-track stature is not
identifiable from monocular measurements; see step5d_report.md). Motion: white-noise acceleration with the graph's q_v.
Measurements = the graph's measurement rows: the (keyframe, track) rows of the run's ped_log.txt, with the perception row (u, v, l_px, mask_h) of that image
and the keyframe pose of the run at that write; per row, sequentially:
  root pixel   z = (u, v), h = pi(R_cw p + t_cw)                              sigma = RootPxSigma                       (Huber sqrt(5.991), as the graph)
  log depth    z = log f + log cL + log H0 - log l_px, h = log (R_cw p + t_cw)_z  (P9-C3b erratum)  sigma = LogDepthSigma, only if the range gate passes (same rule as
               PedestrianBA.cc:93-95)                                                                                   (Huber sqrt(3.841))
Initialisation = the graph's rule (PedestrianBA.cc:149-154): back-project the root pixel of the first row to the range f cL H / l_px (mask range
f H_mask / mask_h if the gate rejects the row), p0 = T_wc (that point), v0 = 0; the covariance is diffuse (p 50 m, v 5 m/s)
because the graph has no prior on p and v either. A segment = one track in one map (a map has its own world frame); a Huber step inflates the measurement
covariance by w/delta when the whitened residual w exceeds delta (robust EKF; no BA, no stance, no footprints).
causal = the forward filter (primary comparison); rts = Rauch-Tung-Striebel smoother over the segment (offline reference).
"""
import numpy as np

F = 415.69219381653056
CX, CY = 360.0, 240.0
HUBER_2D, HUBER_1D = np.sqrt(5.991), np.sqrt(3.841)      # Optimizer.cc:1994-1995


def read_cfg(path):
    d = {}
    for l in open(path):
        if l.startswith('Pedestrians.'):
            k, v = l.split(':')
            v = v.split('#')[0].strip()
            try:
                d[k.split('.')[1]] = float(v)
            except ValueError:
                d[k.split('.')[1]] = v      # FloorContact: none | regional | joint, Dir: path
    return d


def gate_ok(cfg, lpx, maskh):
    if cfg['GateK'] <= 0 or maskh <= 0:
        return True
    d = np.log(cfg['SkeletonOverStature'] * cfg['StatureFixedM'] / lpx) - np.log(cfg['MaskHeightM'] / maskh)
    return abs(d - cfg['GateCenter']) <= cfg['GateK'] * cfg['GateSigma']


def _huber_update(x, P, z, h, J, sig, delta):
    """one measurement update with measurement covariance sig^2 I (inflated by the Huber weight)."""
    r = z - h
    m = len(r)
    w = np.linalg.norm(r) / sig
    infl = 1.0 if w <= delta else w / delta
    R = (sig * sig * infl) * np.eye(m)
    S = J @ P @ J.T + R
    K = P @ J.T @ np.linalg.inv(S)
    x = x + K @ r
    I_KJ = np.eye(len(x)) - K @ J
    P = I_KJ @ P @ I_KJ.T + K @ R @ K.T          # Joseph form
    return x, 0.5 * (P + P.T)


def _huber_update_cov(x, P, z, h, J, R0, delta):
    """measurement update with a full measurement covariance R0, inflated by w/delta when the whitened residual norm w exceeds delta."""
    r = z - h
    w = float(np.sqrt(r @ np.linalg.solve(R0, r)))
    infl = 1.0 if w <= delta else w / delta
    R = R0 * infl
    S = J @ P @ J.T + R
    K = P @ J.T @ np.linalg.inv(S)
    x = x + K @ r
    I_KJ = np.eye(len(x)) - K @ J
    P = I_KJ @ P @ I_KJ.T + K @ R @ K.T
    return x, 0.5 * (P + P.T)


def floor_ground_point(Twc, fu, fv, zp):
    """foot ray (pixel fu, fv) meets the plane z = zp (map frame, gravity along -z): the graph's ground point G (PedestrianFactors.h Geometry()); None for a grazing ray
    (less than ~1.1 deg below the horizon, PedestrianBA.cc guard)."""
    d = Twc[:3, :3] @ np.array([(fu - CX) / F, (fv - CY) / F, 1.0])
    if d[2] / np.linalg.norm(d) > -0.02:
        return None
    return Twc[:3, 3] + ((zp - Twc[2, 3]) / d[2]) * d


def run_segment(rows, cfg, smooth):
    """rows: time-ordered list of dict(t, Twc (4x4), u, v, lpx, maskh [, fu, fv, zp]). Returns per row (p, v, H) causal and (if smooth) rts, plus covariances.
    P9-C3b: with cfg FloorContact != none the state is [p, v, b] (b = the per-track log-scale bias, prior N(0, BiasSigma^2), constant in time), the range
    measurement is log z_c - b = log f + log cL + log H0 - log l_px, and a row with a foot pixel and a plane height zp (the plane height the graph used for that
    (keyframe, track), from ped_floor.log) adds the floor measurement G_xy = p_xy with the radial / tangential covariance of the graph's factor."""
    q = cfg['Qv']; H0 = cfg['StatureFixedM']; cL = cfg['SkeletonOverStature']
    withb = str(cfg.get('FloorContact', 'none')) != 'none'
    n = 7 if withb else 6
    xs, Ps, xp, Pp, Fs = [], [], [], [], []
    x = None; P = None; tprev = None
    for k, r in enumerate(rows):
        Twc = r['Twc']; Rcw = Twc[:3, :3].T; tcw = -Rcw @ Twc[:3, 3]
        ok = gate_ok(cfg, r['lpx'], r['maskh'])
        if x is None:
            b = np.array([(r['u'] - CX) / F, (r['v'] - CY) / F, 1.0])
            rng = (F * cL * H0 / r['lpx']) if ok else (F * cfg['MaskHeightM'] / max(r['maskh'], 1.0))
            z = rng * b                      # P9-C3b: rng is the optical-axis depth
            x = np.zeros(n); x[:6] = np.concatenate([Twc[:3, :3] @ z + Twc[:3, 3], np.zeros(3)])
            P = np.diag([50.0 ** 2] * 3 + [5.0 ** 2] * 3 + ([cfg['BiasSigma'] ** 2] if withb else []))
            Fk = np.eye(n); xpred, Ppred = x.copy(), P.copy()
        else:
            dt = r['t'] - tprev
            Fk = np.eye(n); Fk[:3, 3:6] = dt * np.eye(3)
            Q = np.zeros((n, n))
            Q[:3, :3] = q * dt ** 3 / 3 * np.eye(3); Q[:3, 3:6] = Q[3:6, :3] = q * dt ** 2 / 2 * np.eye(3); Q[3:6, 3:6] = q * dt * np.eye(3)
            xpred = Fk @ x; Ppred = Fk @ P @ Fk.T + Q
            x, P = xpred, Ppred
        xp.append(xpred.copy()); Pp.append(Ppred.copy()); Fs.append(Fk)
        # root pixel
        Xc = Rcw @ x[:3] + tcw
        if Xc[2] > 0.5:
            h = np.array([F * Xc[0] / Xc[2] + CX, F * Xc[1] / Xc[2] + CY])
            dpi = np.array([[F / Xc[2], 0, -F * Xc[0] / Xc[2] ** 2], [0, F / Xc[2], -F * Xc[1] / Xc[2] ** 2]])
            J = np.zeros((2, n)); J[:, :3] = dpi @ Rcw
            x, P = _huber_update(x, P, np.array([r['u'], r['v']]), h, J, cfg['RootPxSigma'], HUBER_2D)
        # log range
        if ok:
            Xc = Rcw @ x[:3] + tcw
            zc = Xc[2]                       # P9-C3b erratum: log of the optical-axis depth z_c, not of |X_c|
            if zc > 0.5:
                h = np.array([np.log(zc) - (x[6] if withb else 0.0)])
                J = np.zeros((1, n)); J[0, :3] = np.array([0.0, 0.0, 1.0 / zc]) @ Rcw
                if withb:
                    J[0, 6] = -1.0
                zlog = np.array([np.log(F) + np.log(cL) + np.log(H0) - np.log(r['lpx'])])
                x, P = _huber_update(x, P, zlog, h, J, cfg['LogDepthSigma'], HUBER_1D)
        # floor contact
        if withb and r.get('zp') is not None:
            G = floor_ground_point(Twc, r['fu'], r['fv'], r['zp'])
            if G is not None:
                dxy = x[:2] - Twc[:2, 3]
                if np.linalg.norm(dxy) > 1e-6:
                    ur = dxy / np.linalg.norm(dxy); ut = np.array([-ur[1], ur[0]])
                    R0 = cfg['FloorSigmaRadialM'] ** 2 * np.outer(ur, ur) + cfg['FloorSigmaTangentialM'] ** 2 * np.outer(ut, ut)
                    J = np.zeros((2, n)); J[:, :2] = np.eye(2)
                    x, P = _huber_update_cov(x, P, G[:2], x[:2], J, R0, HUBER_2D * cfg.get('HuberScale', 1.0))
        xs.append(x.copy()); Ps.append(P.copy()); tprev = r['t']
    out = dict(causal=[(s[:3], s[3:6], H0) for s in xs], P_causal=Ps, b_causal=[s[6] if withb else 0.0 for s in xs])
    if smooth:
        m = len(xs); xsm = [None] * m; Psm = [None] * m
        xsm[-1], Psm[-1] = xs[-1], Ps[-1]
        for k in range(m - 2, -1, -1):
            C = Ps[k] @ Fs[k + 1].T @ np.linalg.inv(Pp[k + 1])
            xsm[k] = xs[k] + C @ (xsm[k + 1] - xp[k + 1])
            Psm[k] = Ps[k] + C @ (Psm[k + 1] - Pp[k + 1]) @ C.T
            Psm[k] = 0.5 * (Psm[k] + Psm[k].T)
        out.update(rts=[(s[:3], s[3:6], H0) for s in xsm], P_rts=Psm, b_rts=[s[6] if withb else 0.0 for s in xsm])
    return out
