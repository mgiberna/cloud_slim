# Cloud task T2: real datasets with a moving visual-inertial camera and 3D ground truth of other people (web research only)

You have no memory of earlier sessions. Cite every claim with a source link. Mark anything you cannot verify as "unverified".

## What we need

A **real** dataset where:

1. a moving camera records video **with a synchronised IMU stream**, released raw: mono-inertial or stereo-inertial, head-mounted, handheld or robot;
2. the camera's **6-DoF trajectory GT** is available;
3. **3D ground truth of people other than the camera wearer** is available: root position over time at minimum, ideally a skeleton or SMPL, in the same world frame as the camera, or registrable to it;
4. several people are in view at once, ideally a crowd;
5. images allow 2D person detection: RGB or grey, resolution and intrinsics known.

## Candidates to check first (not verified)

Nymeria (Meta, Aria glasses; an observer wearer filming a participant in an XSens suit), EgoHumans, Ego-Exo4D, EgoBody, HPS, 3DPW, EMDB (no raw IMU released, as far as known; verify), RICH, and InCrowd-VI (known: no pedestrian GT; verify). Search for others from 2022–2026.

## Output

Write `docs/cloud_tasks/T2_dataset_report.md` with:

1. **A table, one row per dataset,** with columns:
   - raw IMU released (yes / no / unverified);
   - camera GT, and how it was obtained;
   - other-person 3D GT, and its form;
   - the same frame as the camera (yes / no / registrable);
   - number of people in view;
   - scenes (indoor or outdoor, crowd level);
   - size;
   - licence and access;
   - format;
   - link.
2. **A ranked shortlist,** at most 3, of datasets meeting criteria 1–3, with any conversion work needed: camera model, rectification, time synchronisation, and frame alignment of the people GT.
3. **For the top candidate,** the exact files or streams to download, and a rough conversion plan to a ROS2 bag with camera images, IMU and GT transforms.
