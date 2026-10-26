"""P4-S1 data layer: uHumans2 images, exact camera GT, pedestrian GT, tracker tracks, floor model.

Ported read-only from the main project, worktree p1b-skeleton-vs-mask @ c7cd432
(/home/marco/workspaces/dv_sgraphs/src/object_motion_estimator/.claude/worktrees/p1b-skeleton-vs-mask/eval/phase1):
  dedup, load_gt, Poses, obj_at, project, join_tracks_masks, frames_table, root_pixel  <- P1-A/p1a_common.py:41-190
  greedy_nearest                                                                     <- P1-B/p1b_common.py:49-64
Nothing in the main repository is modified or imported.
"""
import ast
import os
import re

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

P1A = '/media/marco/muffin/datasets/phase1/P1-A'
P4 = os.environ.get('P4S1_OUT', '/media/marco/muffin/datasets/phase4/P4-S1')
SEQS = ('office_s1_12h', 'subway_s1_24h')
SHORT = {'office_s1_12h': 'office', 'subway_s1_24h': 'subway'}

# config/uHumans2_TESSE_imufix.yaml:14-27 (main repo); P1-A/p1a_common.py:17-19
FX = FY = 415.69219381653056
CX, CY = 360.0, 240.0
W, H = 720, 480

C_ROOT = 0.55          # P1-A/p1a_common.py:38 (mask root = (cu, vb - C_ROOT * h))
ASSOC_FRAC = 0.5       # P1-B/p1b_common.py:27 (accept if distance < 0.5 x pixel height)
H_ROOT_NOMINAL = 0.95  # brief, precondition 3
H_ROOT_SWEEP = (0.85, 0.95, 1.05)
MAX_IMAGE_DT = 0.075   # s; images are 20 Hz (dt 0.05), larger steps are dropped frames -> series break
P2_GATE_H, P2_RANGE_RATIO, H0 = 1.0, (0.5, 2.0), 1.70   # P1-A/p1a_common.py:35-37 (track <-> GT object)


def dedup(arr):
    arr = arr[np.argsort(arr[:, 0], kind='stable')]
    _, first = np.unique(arr[:, 0], return_index=True)
    return arr[np.sort(first)]


def load_gt(seq):
    d = np.load(os.path.join(P1A, f'{seq}_gt.npz'))
    objs = {}
    for k in d.files:
        m = re.fullmatch(r'tf\|world\|(object_\d+)', k)
        if m:
            objs[m.group(1)] = dedup(d[k])
    body = dedup(d['tf|world|base_link_gt'])
    statics = {(s[0], s[1]): s for s in (ast.literal_eval(x) for x in d['tf_static'])}
    s = statics[('base_link_gt', 'left_cam')]
    T_b_c = np.eye(4)
    T_b_c[:3, :3] = Rotation.from_quat(s[5:9]).as_matrix()   # tf_static quaternion order x,y,z,w
    T_b_c[:3, 3] = s[2:5]
    return objs, body, T_b_c


class Poses:
    """GT camera pose from /tf world -> base_link_gt and tf_static base_link_gt -> left_cam."""

    def __init__(self, body, T_b_c):
        self.t = body[:, 0]
        self.p = body[:, 1:4]
        self.slerp = Slerp(self.t, Rotation.from_quat(body[:, 4:8]))
        self.T_b_c = T_b_c

    def T_w_c(self, ts):
        ts = np.clip(ts, self.t[0], self.t[-1])
        R_w_b = self.slerp(ts).as_matrix()
        p_w_b = np.stack([np.interp(ts, self.t, self.p[:, i]) for i in range(3)], 1)
        T_w_b = np.tile(np.eye(4), (len(ts), 1, 1))
        T_w_b[:, :3, :3], T_w_b[:, :3, 3] = R_w_b, p_w_b
        return T_w_b @ self.T_b_c

    def T_c_w(self, ts):
        return np.linalg.inv(self.T_w_c(ts))


def obj_at(arr, ts, max_gap=0.2):
    """Linear interpolation of a deduplicated GT object track; NaN if the nearest sample is > max_gap away."""
    t = arr[:, 0]
    p = np.stack([np.interp(ts, t, arr[:, 1 + i]) for i in range(3)], 1)
    i = np.clip(np.searchsorted(t, ts), 1, len(t) - 1)
    gap = np.minimum(np.abs(t[i] - ts), np.abs(t[i - 1] - ts))
    p[(gap > max_gap) | (ts < t[0]) | (ts > t[-1])] = np.nan
    return p


def project(T_c_w, p_w):
    pc = np.einsum('nij,nj->ni', T_c_w[:, :3, :3], p_w) + T_c_w[:, :3, 3]
    z = pc[:, 2]
    with np.errstate(divide='ignore', invalid='ignore'):
        return FX * pc[:, 0] / z + CX, FY * pc[:, 1] / z + CY, z


def join_tracks_masks(tracks, masks):
    """Attach the exact mask bbox to each track row with pixel_height > 0 (P1-A/p1a_common.py:131-163).
    Rows: stamp, track_id, h, flags, cu, vb, x0, y0, x1, y1 (NaN bbox if unmatched) + counts."""
    out = np.full((len(tracks), 10), np.nan)
    out[:, :6] = tracks[:, :6]
    mt = masks[:, 0]
    order = np.argsort(mt, kind='stable')
    mt, masks = mt[order], masks[order]
    n_h = n_m = n_dup = n_amb = 0
    for r, row in enumerate(tracks):
        if row[2] <= 0:
            continue
        n_h += 1
        lo, hi = np.searchsorted(mt, row[0] - 1e-4), np.searchsorted(mt, row[0] + 1e-4)
        c = masks[lo:hi]
        ok = (np.abs(c[:, 10] - row[2]) < 0.5) & (np.abs(c[:, 9] - row[5]) < 0.5) & (np.abs(c[:, 8] - row[4]) < 0.05)
        if ok.sum() == 1:
            n_m += 1
            out[r, 6:10] = c[ok][0, 4:8]
        elif ok.sum() > 1:
            b = c[ok][:, 4:8]
            if (b == b[0]).all():
                n_dup += 1
                out[r, 6:10] = b[0]
            else:
                n_amb += 1
    return out, {'with_h': n_h, 'matched_unique': n_m, 'matched_duplicate_same_bbox': n_dup, 'ambiguous_unmatched': n_amb}


def root_pixel(row):
    return row[4], row[5] - C_ROOT * row[2]


def greedy_one_to_one(pairs):
    """pairs: iterable of (cost, a, b). Greedy by ascending cost, one-to-one. Returns {a: b} and the cost."""
    used_a, used_b, out = set(), set(), {}
    for cost, a, b in sorted(pairs):
        if a in used_a or b in used_b:
            continue
        used_a.add(a), used_b.add(b)
        out[a] = (b, cost)
    return out


def assoc_detections_to_tracks(det_pts, track_rows):
    """Hip midpoint -> mask root, gate ASSOC_FRAC x mask pixel height, greedy one-to-one, rejected nearest pairs are
    not replaced (P1-B/p1b_common.py:49-64, with the gate on the mask height as in the P4-S1 brief).
    det_pts: [(u, v)] (None allowed); track_rows: joined rows. Returns {det_index: row_index}."""
    pairs = []
    for i, p in enumerate(det_pts):
        if p is None:
            continue
        for k, r in enumerate(track_rows):
            ru, rv = root_pixel(r)
            pairs.append((float(np.hypot(p[0] - ru, p[1] - rv)), i, k))
    out = {}
    for i, (k, d) in greedy_one_to_one(pairs).items():
        if track_rows[k][2] > 0 and d < ASSOC_FRAC * track_rows[k][2]:
            out[i] = k
    return out


class Seq:
    def __init__(self, seq):
        self.seq = seq
        self.short = SHORT[seq]
        self.objs, body, T_b_c = load_gt(seq)
        self.names = sorted(self.objs, key=lambda o: int(o.split('_')[1]))
        self.stamps = np.load(os.path.join(P1A, f'{seq}_rgb_stamps.npy'))
        self.n = len(self.stamps)
        self.poses = Poses(body, T_b_c)
        self.T_w_c = self.poses.T_w_c(self.stamps)      # (n,4,4)
        self.T_c_w = np.linalg.inv(self.T_w_c)
        tracks = np.load(os.path.join(P1A, f'{seq}_tracks.npy'))
        masks = np.load(os.path.join(P1A, f'{seq}_masks.npy'))
        self.joined, self.join_counts = join_tracks_masks(tracks, masks)
        ok = ~np.isnan(self.joined[:, 6])
        self._ftab = {}
        for r in self.joined[ok]:
            self._ftab.setdefault(round(r[0], 4), []).append(r)
        self.root_xyz = {o: obj_at(self.objs[o], self.stamps) for o in self.names}
        self.uvz = {o: np.stack(project(self.T_c_w, self.root_xyz[o]), 1) for o in self.names}
        # time gap before each image (dropped frames): series must break where it exceeds MAX_IMAGE_DT
        self.dt = np.r_[np.inf, np.diff(self.stamps)]

    def rgb(self):
        return np.memmap(os.path.join(P1A, f'{self.seq}_rgb.u8'), np.uint8, 'r', shape=(self.n, H, W, 3))

    def tracks_at(self, i):
        return np.array(self._ftab.get(round(self.stamps[i], 4), np.zeros((0, 10))))

    def assoc_track_to_gt(self, i):
        """{track_id: object} at frame i, P1-A criterion §1.2 (p1a_analyze.py:79-93): independent of bbox containment,
        gate 1.0 x h_px, range ratio in (0.5, 2), greedy one-to-one."""
        rows = self.tracks_at(i)
        cands = []
        for o in self.names:
            u, v, z = self.uvz[o][i]
            if not (np.isfinite(z) and z > 0):
                continue
            for k, r in enumerate(rows):
                ru, rv = root_pixel(r)
                d = np.hypot(u - ru, v - rv) / r[2]
                ratio = z / (FX * H0 / r[2])
                if d <= P2_GATE_H and P2_RANGE_RATIO[0] <= ratio <= P2_RANGE_RATIO[1]:
                    cands.append((d, k, o))
        return {int(rows[k][1]): o for k, (o, _) in greedy_one_to_one(cands).items()}

    def root_speed(self, o, i, half=0.25):
        """Horizontal GT root speed (m/s) around image i over +-half s; NaN if GT is missing."""
        t = self.stamps[i]
        p = obj_at(self.objs[o], np.array([t - half, t + half]))
        return float(np.linalg.norm(p[1, :2] - p[0, :2]) / (2 * half)) if np.isfinite(p).all() else np.nan


def pixel_rays_world(T_w_c, uv):
    """T_w_c (N,4,4), uv (N,2) -> camera centres (N,3), unit world directions (N,3)."""
    d_c = np.stack([(uv[:, 0] - CX) / FX, (uv[:, 1] - CY) / FY, np.ones(len(uv))], 1)
    d_w = np.einsum('nij,nj->ni', T_w_c[:, :3, :3], d_c)
    return T_w_c[:, :3, 3], d_w / np.linalg.norm(d_w, axis=1, keepdims=True)


def floor_points(T_w_c, uv, z_floor):
    """Intersect pixel rays with the horizontal plane z = z_floor (per-row). NaN where the ray does not hit it ahead."""
    c, d = pixel_rays_world(T_w_c, uv)
    with np.errstate(divide='ignore', invalid='ignore'):
        s = (z_floor - c[:, 2]) / d[:, 2]
    p = c + s[:, None] * d
    p[~(np.isfinite(s) & (s > 0))] = np.nan
    return p
