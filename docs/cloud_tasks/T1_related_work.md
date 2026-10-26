# Cloud task T1: related work and novelty check (web research only)

You have no memory of earlier sessions, and no access to any experiment data. Work from the web and from published papers only. Cite every claim with a source link. If something can't be verified, write "unverified", never a guess.

## Our system (for positioning)

**The system:**

- online pedestrian estimation **inside the local bundle adjustment** of a mono-inertial ORB-SLAM3 (visual_sgraphs fork);
- persistent per-person world-frame root states with a white-noise-acceleration motion prior;
- range from apparent body size (nose→heel) at a fixed stature, on depth z;
- stance-foot footprints;
- an optional floor-level landmark module.

**Results so far:**

- pedestrian velocity beats a per-track Kalman filter on the same measurements;
- pedestrian position is at per-frame level;
- there is no measurable camera improvement (with a theoretical explanation: camera-relative pedestrian factors are absorbed; pedestrians carry camera information only under near-zero static support);
- evaluated on uHumans2 (simulation) and planned on InCrowd-VI (camera).

## Task

1. Build a matrix, one row per method, covering at least:
   - Kimera / 3D Dynamic Scene Graphs (Rosinol et al., RSS 2020 and IJRR 2021; the uHumans datasets), Hydra;
   - BodySLAM, SLAHMR, PACE, WHAM, TRAM, GLAMR, JOSH;
   - AirDOS, DynoSAM, VDO-SLAM, ClusterVO, DynaSLAM;
   - any 2023–2026 work that estimates humans jointly with a SLAM or VIO back-end. Search for it.

   **Columns:**
   - online or offline;
   - sensors (mono / stereo / RGB-D / IMU);
   - whether humans live inside the SLAM back-end optimisation (yes / no / partly);
   - the human representation (point, box, skeleton, SMPL);
   - whether it claims camera-odometry improvement from humans, and how big;
   - pedestrian metrics reported;
   - datasets;
   - code available.
2. For each method, one sentence on how it differs from our system. Be precise and fair.
3. Write a 200–300-word positioning paragraph: which of our claims are new, which are incremental, and which are already shown by others.
4. List papers that report the **opposite** of our camera finding, i.e. a camera benefit from humans or dynamic objects, with their conditions.

## Output

Write `docs/cloud_tasks/T1_related_work_report.md`, with the matrix as a markdown table and a reference list with URLs.
