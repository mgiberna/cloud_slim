"""P4-S1 per-track series. numpy only (also imported from the GVHMR environment).

A track's associated detections form a sorted set of image indices. Segments are maximal ranges of images in which
  - no run of >= 2 consecutive images is missing (a single missing image is a bridged hole), and
  - no image-time step exceeds MAX_DT (dropped frames in the bag break the series).
Each segment is dense over [f0, f1]; det[j] = detection row of image f0 + j, or -1 for a bridged hole.
"""
import numpy as np

MAX_DT = 0.075  # s, images are 20 Hz (data.MAX_IMAGE_DT)


def build_segments(track_id, frame, stamps):
    """track_id (D,), frame (D,) -> list of dict(track, f0, det (L,)) over the associated detections (track_id >= 0)."""
    dt = np.r_[np.inf, np.diff(stamps)]
    segs = []
    for tid in np.unique(track_id[track_id >= 0]):
        rows = np.flatnonzero(track_id == tid)
        rows = rows[np.argsort(frame[rows], kind='stable')]
        fr = frame[rows]
        assert len(np.unique(fr)) == len(fr), f'track {tid} has two detections in one image'
        start = 0
        for k in range(1, len(rows) + 1):
            cut = k == len(rows)
            if not cut:
                gap = fr[k] - fr[k - 1]
                cut = gap > 2 or (dt[fr[k - 1] + 1:fr[k] + 1] > MAX_DT).any()
            if cut:
                r, f = rows[start:k], fr[start:k]
                det = np.full(f[-1] - f[0] + 1, -1, int)
                det[f - f[0]] = r
                segs.append(dict(track=int(tid), f0=int(f[0]), det=det))
                start = k
    return segs


def flatten(segs):
    """Concatenate segments: seg_id (N,), frame (N,), det (N,), seg_start (S,), seg_len (S,), seg_track (S,)."""
    lens = np.array([len(s['det']) for s in segs])
    start = np.r_[0, np.cumsum(lens)[:-1]]
    return dict(seg_id=np.repeat(np.arange(len(segs)), lens),
                frame=np.concatenate([s['f0'] + np.arange(len(s['det'])) for s in segs]),
                det=np.concatenate([s['det'] for s in segs]), seg_start=start, seg_len=lens,
                seg_track=np.array([s['track'] for s in segs]))
