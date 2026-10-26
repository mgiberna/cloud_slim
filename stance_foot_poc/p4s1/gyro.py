"""P4-S1: camera rotation per image from the noisy gyro (P2 rep1 bias estimate) and from the GT camera.

R_w2c(t+1) = Exp(-w_c dt) R_w2c(t) with w_c = R_b_c^T (w_imu - bw), gyro in the IMU frame (base_link_gt, tesse imu header), bw =
latest /vs_graphs/imu_bias bwx..bwz at or before the sample (zero before the first estimate), R_b_c = tf_static base_link_gt ->
left_cam rotation. Piecewise-constant w over each IMU sample interval, split at image stamps. Only relative rotations enter GVHMR
(compute_cam_angvel), so the integration starts at the identity.
"""
import numpy as np
from scipy.spatial.transform import Rotation


def integrate(img_stamps, imu_t, imu_w, bias_t, bias_w, R_b_c):
    """Returns R_w2c (n,3,3) relative to image 0 (identity), plus w_c at the samples used (diagnostics)."""
    j = np.searchsorted(bias_t, imu_t, side='right') - 1
    bw = np.where((j >= 0)[:, None], bias_w[np.clip(j, 0, None)], 0.0)
    w_c = (imu_w - bw) @ R_b_c                       # rows: R_b_c^T w
    # breakpoints: all IMU stamps and image stamps in [img0, img_last]
    R = np.zeros((len(img_stamps), 3, 3))
    R[0] = np.eye(3)
    cur = np.eye(3)
    for n in range(1, len(img_stamps)):
        t0, t1 = img_stamps[n - 1], img_stamps[n]
        edges = np.r_[t0, imu_t[(imu_t > t0) & (imu_t < t1)], t1]
        mid = 0.5 * (edges[:-1] + edges[1:])
        k = np.clip(np.searchsorted(imu_t, mid, side='right') - 1, 0, len(imu_t) - 1)   # zero-order hold of the last sample
        rotvec = -(w_c[k] * np.diff(edges)[:, None]).sum(0)
        cur = Rotation.from_rotvec(rotvec).as_matrix() @ cur
        R[n] = cur
    return R


def relative_angle_deg(Ra, Rb):
    """Angle (deg) of Ra[i] Rb[i]^T."""
    M = np.einsum('nij,nkj->nik', Ra, Rb)
    return np.degrees(np.arccos(np.clip((np.trace(M, axis1=1, axis2=2) - 1) / 2, -1, 1)))
