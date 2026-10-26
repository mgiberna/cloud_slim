# T1 report: related work and novelty check

Date of research: 2026-10-26. Web research only, no experiment data used.

## How this was researched (read first)

- The session's network policy **blocked arxiv.org, ar5iv, semanticscholar.org, openaccess.thecvf.com, ecva.net, roboticsproceedings.org, orbilu.uni.lu and all `*.github.io` project pages**. Only github.com repository pages could be fetched directly.
- Every claim below therefore comes from either (a) a GitHub README fetched directly, or (b) the text excerpts a web search engine returned for the cited page. Excerpt-based claims are cited to the page they quote. I did **not** read the full PDFs. Before any of this goes into a paper, each number should be re-checked in the PDF.
- **"unverified"** means I could not confirm the item from any reachable source. A number marked *(secondary)* came from a third-party summary, not the paper itself, and is unverified until checked.
- Bracketed numbers such as [3] point to the reference list at the end.

## 1. Comparison matrix

Abbreviations: VI = visual-inertial; BA = bundle adjustment; FG = factor graph; ATE = absolute trajectory error; W-/WA-MPJPE = world-frame / world-aligned mean per-joint position error; RTE = root translation error.

| # | Method (venue) | Online / offline | Sensors | Humans inside SLAM back-end? | Human representation | Camera-odometry improvement claimed from humans? How big | Pedestrian metrics reported | Datasets | Code |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **3D Dynamic Scene Graphs / SPIN** (Rosinol et al., RSS 2020) [1][2] | unverified | VI [1] | **No.** Humans are tracked separately. The VIO's robustness to humans comes from rejecting them as outliers (DVIO) [3] | SMPL mesh; pose graph over time [1] | No gain *from* humans. The robust VIO that rejects dynamic features improves on uHumans: on uH_03, DVIO 88 cm vs 160 cm (5-point baseline) [3] | Human localisation error (numbers unverified) | uHumans, EuRoC [3] | Kimera-VIO is public [4]; code for the human module is unverified |
| 2 | **Kimera** (Rosinol et al., IJRR 2021) [5] | Real-time VIO and mesh [5]; the human module's runtime is unverified | VI (stereo + IMU); depth image used for the pelvis position [6] | **No.** Each human has their own pose graph (pelvis nodes, motion priors). Per-frame mesh locations enter that graph as prior factors, transformed by the Kimera-VIO pose [6]. Humans are masked from the mesh [3] | SMPL mesh via GraphCMR; pelvis pose-graph nodes [5][6] | No | Human localisation error, reduced "from meters to sub-meter" *(secondary; table unverified)* [6] | uHumans, uHumans2 (Unity simulation, SMPL humans, ground-truth human poses) [5] | Kimera-VIO public [4]; human-module code unverified |
| 3 | **Hydra** (Hughes et al., RSS 2022; IJRR 2024) [7][8] | Online, real-time [7] | VI [8] | No humans found. The README never mentions people [9]; the IJRR version has an odometric "agent layer" [8], but whether it holds humans is unverified | None found | No | None found | Simulated and real data [7] | Yes, BSD-2 [9] |
| 4 | **BodySLAM** (Henning et al., ECCV 2022) [10][11] | unverified (sequential SLAM; runtime not found) | Monocular RGB [10] | **Yes.** One FG/BA jointly optimises camera poses, landmarks, body-centre poses, and SMPL shape and posture [11] | SMPL (shape, posture, root pose) with a learned motion model [11] | **Yes**, "improves … camera poses compared to estimating these separately" [10]; size unverified | Body-parameter errors vs mocap (numbers unverified) | Own monocular sequences with mocap ground truth [11] | None found [12] |
| 5 | **BodySLAM++** (Henning et al., IROS 2023) [13] | **Online**, 15+ fps on an i7 CPU [13] | **Stereo + IMU** (OKVIS 2) [13] | **Yes, tightly coupled.** Frame-to-frame human–camera factors and anthropometric priors in the VI FG [14] | SMPL [13] | **Yes, 12%** better camera estimation; multi-person ATE 0.0317 m vs 0.0362 m (OKVIS 2) vs 0.0476 m (ORB-SLAM3); better in all but 2 sequences [13] | Human state error, 26% better than baseline [13] | Own multi-person sequences MP_01–MP_15 with mocap ground truth [13] | None found [12] |
| 6 | **SLAHMR** (Ye et al., CVPR 2023) [15][16] | **Offline**: three-stage optimisation [15] | Monocular RGB [15] | **Partly.** DROID-SLAM gives the relative camera; the joint stage then solves camera scale and human trajectories with HuMoR and SMPL priors [15] | SMPL + HuMoR prior [15] | Recovers camera **scale** from humans; the better scale helps downstream PoseTrack tracking [15]; no ATE gain claim found | WA-MPJPE, W-MPJPE, PA-MPJPE (EgoBody: 79.1 / 141.1 / 101.2 mm on val, as reported by [18]) | EgoBody, PoseTrack, 3DPW [15][16] | Yes, MIT [16] |
| 7 | **PACE** (Kocabas et al., 3DV 2024) [17] | **Offline** batch optimisation [17] | Monocular RGB [17] | **Yes.** SLAM features and human priors tied in a BA-style optimisation [17] | SMPL with a motion prior built for batch optimisation [17] | **Yes**, vs DROID-SLAM: **12% lower ATE with scale alignment, 74% lower without** [17] | Global human pose error [17] | HCM (new synthetic), RICH [17] | None found [17] |
| 8 | **WHAM** (Shin et al., CVPR 2024) [19][20] | Presented as online / efficient, unlike optimisation methods [19]; fps unverified | Monocular RGB + camera angular velocity from SLAM (DPVO / DROID-SLAM) **or a gyroscope** [20] | **No.** The SLAM output feeds forward into WHAM [20] | SMPL; contact-aware trajectory refinement [19] | No | WA-MPJPE, W-MPJPE, RTE, foot sliding [20] | EMDB (verified) [20]; others unverified | Yes, MIT [21] |
| 9 | **TRAM** (Wang et al., ECCV 2024) [22] | **Offline** pipeline [22][23] | Monocular RGB [22] | **No.** Masked DROID-SLAM removes humans; metric scale comes from ZoeDepth on the background [22][23] | SMPL via VIMO [22] | No (scale from the scene, not from humans) [22] | Global motion error, 60% lower than prior work [22]; EMDB evaluation [23] | EMDB (others unverified) [22][23] | Yes, MIT [23] |
| 10 | **GLAMR** (Yuan et al., CVPR 2022) [24][25] | **Offline** global optimisation [24] | Monocular RGB [24] | n/a: no SLAM. **Camera poses are optimised from human evidence** (predicted global trajectories plus 2D keypoints) [24] | SMPL + generative motion infiller [24] | n/a (the camera comes *only* from humans) | Global mesh recovery errors [24] | 3DPW, Dynamic Human3.6M, AMASS [25] | Yes [25] |
| 11 | **JOSH** (Liu et al., ICLR 2026) [26][27] | **Offline**, single-stage joint optimisation [26] | Monocular RGB [26] | **Yes.** Scene, camera poses and human motion are refined jointly with human–scene contact constraints (MASt3R init) [26][27] | SMPL with contact labels [26] | Better camera pose claimed only in a secondary review, so **unverified** [27] | Global human motion metrics (state of the art on EMDB) [26] | SLOPER4D, EMDB-2, RICH [27] | Authors point to vail-ucla.github.io/JOSH [27]; repository not verified |
| 12 | **AirDOS** (Qiu et al., ICRA 2022) [28][29] | unverified (feature-based visual SLAM) | **Stereo only** in the released code [29] | **Yes.** Dynamic articulated objects enter BA; camera pose, object motion and object structure are refined jointly [28] | Articulated rigid parts (keypoints + rigidity/motion constraints) [28][30] | **Yes, in crowds**: TartanAir Shibuya overall ATE 0.1449 m (AirDOS, masked) vs 0.3044 m (ORB-SLAM) vs 0.3717 m (VDO-SLAM). The search excerpt said the table was garbled, so **verify** [31]. On KITTI it is roughly on par [31] | unverified | TartanAir Shibuya, KITTI [29][31] | Yes [29] |
| 13 | **VDO-SLAM** (Zhang et al., 2020) [32][33] | unverified | **RGB-D** (depth-registered) [33] | **Yes.** Rigid object motions are in the graph [32] | Rigid-object points; non-rigid pedestrians are *excluded* from the KITTI evaluation [34] | Camera vs MVO on OMD: 0.0112 m vs 0.0314 m translation [34]; ClusterVO is better at 0.0066 m [34]. A "15–20%" joint-estimation gain on KITTI comes from a secondary summary, so **unverified** [37] | Object pose error, **object speed error** [32][34] | KITTI tracking, Oxford Multimotion [33] | Yes, GPLv3 [33] |
| 14 | **ClusterVO** (Huang et al., CVPR 2020) [35] | **Online**, sliding window [35] | **Stereo** [35] | **Yes.** Camera and cluster poses are solved in a sliding-window optimisation [35] | Clusters of points (rigid) [35] | "Comparable to state of the art" on odometry [35]; no gain claim | Dynamic trajectory recovery [35] | KITTI, Oxford Multimotion [35] | None found |
| 15 | **DynaSLAM** (Bescos et al., RA-L 2018) [36] | unverified | Mono / stereo / RGB-D [36] | **No.** Dynamic content is masked (Mask R-CNN + multi-view geometry) [36][38] | None (masks only) | Better than standard SLAM in dynamic scenes, by *removing* them [36] | None | TUM, KITTI [38] | Yes [38] |
| 16 | **DynaSLAM II** (Bescos et al., RA-L 2021) [39] | unverified | Stereo / RGB-D [39] | **Yes.** A single BA over static structure, object structure, and camera and object trajectories [39] | Object points + 3D bounding boxes [39] | Abstract claims tracking dynamic objects also helps camera tracking [39]; size unverified | Object trajectory errors (unverified) | KITTI (unverified) | Promised on acceptance; unverified [39] |
| 17 | **DynoSAM** (Morris et al., 2025; T-RO per repo) [40][41] | Batch, sliding-window and incremental [41]; online incremental follow-up [42] | Stereo / RGB-D; IMU via GTSAM, tested only on VIODE [41] | **Yes.** Unified FG over camera, static map, and object motion and structure [40] | Generic rigid objects; humans not mentioned [41] | Camera ATE/RPE better than VDO-SLAM on all tested sequences [37] | Object motion error (ME) [37] | KITTI tracking, VKITTI2, ClusterSLAM-CARLA, OMD, TartanAir Shibuya, VIODE [41] | Yes, BSD-3 [41] |
| 18 | **SynCHMR** (Zhao et al., CVPR 2024) [43] | Offline (unverified) | Monocular RGB [43] | **Partly.** "Human-aware metric SLAM" uses camera-frame human meshes as a scale/depth prior [43] | SMPL + scene-aware denoiser [43] | Metric-scale camera recovered from humans; size unverified [43] | PA-, FA-, WA-MPJPE [18] | EgoBody and others (unverified) | unverified |
| 19 | **WHAC** (Yin et al., ECCV 2024) [44] | Optimisation-free [44] | Monocular RGB [44] | **No** back-end. A "MotionVelocimeter" module turns human motion into world-frame metric cues [45] | SMPL-X [44] | Metric camera **scale** from humans [44]; size unverified | unverified | WHAC-A-Mole (new synthetic) [46] | Project page [44] |
| 20 | **Humans as Checkerboards, HAC** (Yang et al., ICCV 2025) [47][48] | Post-SLAM calibration, about 100× faster than optimisation [47] | Monocular RGB [47] | **No.** SLAM scale is rescaled from the absolute depth of human–scene contact joints [47] | SMPL (HMR output) [47] | Scale only: about 50% lower human motion error [47]; camera ATE/ATE-S are reported (values unverified) [48] | WA-MPJPE, W-MPJPE, PA-MPJPE, ATE, ATE-S [48] | unverified | unverified |
| 21 | **Human3R** (Chen et al., ICLR 2026) [49][50] | Feed-forward, about 15 FPS (authors' claim) [49] | Monocular RGB [49] | **No** explicit back-end (CUT3R-based) [49] | SMPL-X, multi-person [49] | Camera pose "SOTA or competitive"; no human-ablation claim found [49] | Global motion, local mesh [49] | 3DPW, EMDB; trained on BEDLAM [49] | Yes [50] |
| 22 | **Monocular Person Localization under Camera Ego-motion** (Zhan et al., 2025) [51] | Online on a quadruped robot (claimed) [51] | Monocular RGB [51] | **Partly.** Jointly optimises the camera's 2D attitude and the person's 3D position per frame; no full SLAM [51] | Four-point human model [51] | No (attitude only) | Person localisation accuracy [51] | Public datasets + robot experiments [51] | unverified |
| 23 | **DYNEMO-SLAM** (Giberna et al., 2025) [52][53] | Real-time [52] | **LiDAR** scene graph + images to detect dynamic entities [52] | **Yes.** Robot trajectory, dynamic entity poses and structure in one graph; entities constrained to robot keyframes and to the **floor level** [52] | Entity nodes (humans specifically: unverified) [52] | **Yes, 49.97% lower ATE** vs baseline (simulation + real) [52] | unverified | Simulation + real [52] | unverified |
| 24 | **DynoSLAM** (Tokhchukov et al., 2026 preprint) [54] | Online tracker alongside static SLAM [54] | unverified | **Yes.** Pedestrian states in a GraphSLAM FG with generative GNN motion priors and Mahalanobis-weighted factors [54] | Agent states (point-like; unverified) [54] | Robot RMSE 0.39 m in simulated crowds; static-SLAM and **constant-velocity baselines** fail on non-linear avoidance [54] | Pedestrian tracking vs constant-velocity baseline [54] | Simulated crowds [54] | unverified |

Our system, for reference: online; mono + IMU (ORB-SLAM3 / visual_sgraphs [55][56]); pedestrians **inside local BA**; persistent world-frame root point with a white-noise-acceleration prior; range from nose→heel size at a fixed stature; stance-foot footprints; optional floor landmarks; no measurable camera gain; uHumans2 [5], with InCrowd-VI [57] planned.

## 2. How each method differs from ours

1. **3D DSG / SPIN (RSS 2020)**: humans are rejected from the VIO and tracked downstream, while we put them into the local BA as states that share factors with the camera [1][3].
2. **Kimera (IJRR 2021)**: per-human pose graphs take the VIO pose as fixed input (one-way coupling) and use SMPL meshes with depth. We couple both ways inside BA with a point root state and range from mono size [6].
3. **Hydra**: has no human estimation that we could find; it is a scene-graph back-end with loop closure, not a pedestrian tracker [7][9].
4. **BodySLAM**: the closest conceptual match (humans in mono BA). It uses full SMPL, a learned motion model and mocap single-person sequences, has no IMU, and reports camera gains. We use a point root, an analytic WNA prior and a fixed stature, have an IMU, and see no camera gain [10][11].
5. **BodySLAM++**: closest in sensing (VI, tightly coupled, real-time). It is stereo, not mono, has full SMPL with anthropometric priors, and evaluates on its own mocap multi-person data, where it reports 12% camera gain. Our null result directly contrasts with it [13][14].
6. **SLAHMR**: offline, monocular, no IMU; humans fix scale on top of DROID-SLAM, not inside an online BA [15].
7. **PACE**: offline batch BA with SLAM features and SMPL priors on monocular video, with no IMU. Its camera gain is largest without scale alignment (74%), i.e. it mostly comes from scale [17].
8. **WHAM**: a learned regressor that consumes camera angular velocity (SLAM or gyro) feed-forward. It never feeds humans back into the odometry [19][20].
9. **TRAM**: masks humans out of SLAM and takes metric scale from scene depth. Humans are deliberately *not* used for the camera [22].
10. **GLAMR**: no visual SLAM at all. The camera is inferred from human motion alone, offline [24].
11. **JOSH**: offline dense 4D joint optimisation with contact constraints on monocular video. Its contact constraints are close in spirit to our footprints, but it is not an online sparse SLAM [26].
12. **AirDOS**: stereo, humans as articulated rigid parts in BA. Its camera gain shows in crowded synthetic Shibuya and is on par on KITTI. We use a single root point with mono + IMU [28][31].
13. **VDO-SLAM**: RGB-D, rigid objects only. Pedestrians (non-rigid) were excluded from its KITTI evaluation [33][34].
14. **ClusterVO**: stereo, rigid point clusters, no human model or human metrics [35].
15. **DynaSLAM**: removes dynamic content and estimates no human state [36].
16. **DynaSLAM II**: stereo/RGB-D BA over rigid objects with boxes, no humans or human motion prior [39].
17. **DynoSAM**: a stereo/RGB-D rigid-object FG framework; humans are not handled explicitly. It is a natural host for a comparison but not a pedestrian method [40][41].
18. **SynCHMR**: an offline monocular "human-aware metric SLAM" that uses human meshes for scale. We use the IMU for scale and humans only as tracked targets [43].
19. **WHAC**: optimisation-free, scale from human motion, no back-end coupling [44][45].
20. **HAC**: a post-hoc scale calibration from contact joints, not joint estimation [47].
21. **Human3R**: a feed-forward network with no explicit factor graph and no motion prior [49].
22. **Mono person localisation (2025)**: per-frame camera attitude + person position, with no persistent SLAM map or IMU [51].
23. **DYNEMO-SLAM**: LiDAR-based scene-graph SLAM with dynamic entities and floor-level constraints, reporting about 50% ATE gain. Ours is visual mono-inertial and finds no camera gain. The floor-level idea overlaps with our optional floor module [52].
24. **DynoSLAM (2026)**: pedestrian states in a GraphSLAM FG with learned social priors, evaluated in simulation against constant-velocity baselines. It is not a mono-inertial BA and has no size-based ranging [54].

## 3. Positioning (≈280 words)

Putting humans into the SLAM back-end is **already shown**. BodySLAM put SMPL bodies inside monocular BA [11]. BodySLAM++ tightly coupled them with a stereo-VI factor graph in real time [13]. AirDOS put articulated humans into stereo BA [28]. PACE and JOSH do it offline [17][26]. DYNEMO-SLAM and DynoSLAM put dynamic agents into graph SLAM [52][54]. Our architecture is therefore **incremental**. As far as we could find, a minimal *point-root* pedestrian inside the *local BA of a mono-inertial ORB-SLAM3* has not been published (absence of evidence, so **unverified**). The WNA prior is a standard choice: Kimera, BodySLAM and DynoSLAM all use motion priors [6][11][54]. Ranging from body size with a class height prior is also established in monocular SLAM [58][59]. Footprints overlap with the contact constraints in WHAM, JOSH and HAC [19][26][47]. To our knowledge they have not been used as BA factors in online VI-SLAM (**unverified**). Floor-level constraints appear in DYNEMO-SLAM [52].

Our **velocity-over-per-track-KF result** is weakly covered. DynoSLAM compares against constant-velocity baselines in simulation [54], but we found no paper that compares in-BA pedestrian estimates against a Kalman filter on *identical* measurements. That makes it a useful, if modest, contribution.

The **null camera result is the most distinctive claim**, and it runs against most of the literature: BodySLAM, BodySLAM++, PACE, AirDOS and DYNEMO-SLAM all report camera gains [10][13][17][31][52]. It is defensible if framed by conditions. Most gains appear where scale is unobservable (monocular without an IMU [10][17]), where static support is scarce (crowded Shibuya [31]), or where rich human models and multi-person stereo-VI data are used (BodySLAM++ [13]). Our explanation, that camera-relative factors are absorbed unless static support is near zero, predicts exactly that pattern. Still, BodySLAM++'s 12% VI gain must be addressed head-on. Evaluation on uHumans2 follows Kimera [5]. InCrowd-VI has so far been used for VO/SLAM benchmarking only [57] (pedestrian ground truth: **unverified**).

## 4. Papers that report the opposite camera finding (camera benefit from humans or dynamic objects)

| Paper | Reported benefit | Conditions under which it was observed |
|---|---|---|
| BodySLAM [10][11] | Joint estimation improves camera poses vs separate estimation (size unverified) | **Monocular, no IMU**; full SMPL with a learned motion model; the human makes **scale observable** [11]; own mocap sequences |
| BodySLAM++ [13] | **12%** camera improvement; ATE 0.0317 vs 0.0362 m (OKVIS 2) | **Stereo + IMU**, tightly coupled frame-to-frame human–camera factors, anthropometric priors, multi-person indoor mocap sequences; better in 13 of 15 sequences |
| PACE [17] | ATE **−12%** with scale alignment, **−74%** without, vs DROID-SLAM | **Offline**, monocular, batch BA; most of the gain is scale (no IMU); synthetic HCM + RICH |
| AirDOS [28][31] | Shibuya ATE 0.1449 m vs 0.3044 m (ORB-SLAM) (verify) | **Stereo**, **crowded synthetic** scenes (TartanAir Shibuya), articulated rigidity constraints; **no clear gain on KITTI** |
| DYNEMO-SLAM [52] | **49.97%** ATE reduction vs baseline | LiDAR scene-graph SLAM with image-detected dynamic entities, semantic motion priors, floor-level constraints; dynamic keyframe policy also contributes, so attribution to entities alone is unverified |
| DynaSLAM II [39] | Abstract states that tracking dynamic objects benefits camera tracking (size unverified) | Stereo / RGB-D, rigid objects (cars) with 3D boxes in BA |
| CubeSLAM [60] | Objects give long-range geometric and scale constraints that improve camera pose and reduce drift; KITTI error ~5% → 1.62% *(secondary, unverified)* | **Monocular**, mostly static objects with a motion model for dynamic ones; the gain is largely scale/drift |
| VDO-SLAM [32][34] | Camera better than MVO on OMD (0.0112 vs 0.0314 m); "15–20%" on KITTI *(secondary, unverified)* | RGB-D, rigid objects; comparison is against a different system, not an ablation of the same front-end |
| DynoSAM [37][40] | Camera ATE/RPE better than VDO-SLAM on all tested sequences | Stereo/RGB-D, rigid objects; mostly reflects front-end/formulation differences rather than a with/without-objects ablation (our reading) |
| SynCHMR / WHAC / HAC / SLAHMR [43][44][47][15] | Metric **scale** of the camera recovered from humans | **Monocular, no IMU**: humans supply the scale that is otherwise unobservable; not relevant when an IMU fixes scale |

What these have in common: the reported camera benefit appears when (i) scale is unobservable (monocular, no IMU), (ii) static features are scarce or corrupted (crowds), (iii) a much richer human or object model is used, or (iv) the comparison is against a different system rather than an ablation of the same front-end. Only BodySLAM++ reports a gain in a VI setting with an ablation-like baseline (OKVIS 2 is its own base system) [13]. It is the strongest counterexample to our finding.

## References

1. Rosinol et al., "3D Dynamic Scene Graphs: Actionable Spatial Perception with Places, Objects, and Humans", RSS 2020. https://roboticsconference.org/2020/program/papers/79.html ; arXiv https://arxiv.org/abs/2002.06289
2. RSS 2020 proceedings PDF. https://www.roboticsproceedings.org/rss16/p079.pdf
3. arXiv PDF of [1] (Table I, VIO on uHumans). https://arxiv.org/pdf/2002.06289
4. Kimera-VIO repository. https://github.com/MIT-SPARK/Kimera-VIO
5. Rosinol et al., "Kimera: from SLAM to Spatial Perception with 3D Dynamic Scene Graphs", IJRR 40(12-14), 2021. https://arxiv.org/abs/2101.06894 ; https://dspace.mit.edu/handle/1721.1/145298
6. Kimera full text (human pose graph, GraphCMR, depth, VIO transform). https://arxiv.org/pdf/2101.06894 ; https://ar5iv.labs.arxiv.org/html/2101.06894
7. Hughes, Chang, Carlone, "Hydra", RSS 2022. https://roboticsproceedings.org/rss18/p050.html ; https://arxiv.org/abs/2201.13360
8. Hughes et al., "Foundations of Spatial Perception for Robotics", IJRR 2024. https://arxiv.org/abs/2305.07154
9. Hydra repository. https://github.com/MIT-SPARK/Hydra
10. Henning, Laidlow, Leutenegger, "BodySLAM", ECCV 2022. https://www.ecva.net/papers/eccv_2022/papers_ECCV/html/7926_ECCV_2022_paper.php ; https://mlanthology.org/eccv/2022/henning2022eccv-bodyslam/
11. BodySLAM arXiv. https://arxiv.org/abs/2205.02301 ; https://arxiv.org/html/2205.02301v3
12. Search for BodySLAM / BodySLAM++ code (none found). https://mlanthology.org/authors/l/leutenegger-stefan/
13. Henning et al., "BodySLAM++", IROS 2023. https://arxiv.org/abs/2309.01236 ; https://arxiv.org/html/2309.01236
14. BodySLAM++ PDF. https://arxiv.org/pdf/2309.01236
15. Ye, Pavlakos, Malik, Kanazawa, "Decoupling Human and Camera Motion from Videos in the Wild" (SLAHMR), CVPR 2023. https://arxiv.org/abs/2302.12827
16. SLAHMR repository. https://github.com/vye16/slahmr
17. Kocabas et al., "PACE", 3DV 2024. https://arxiv.org/abs/2310.13768 ; https://ps.is.mpg.de/publications/pace2024kocabas ; poster https://ps.is.mpg.de/uploads_file/attachment/attachment/769/PACE_3DV_poster.pdf
18. SynCHMR paper (reports SLAHMR EgoBody numbers). https://arxiv.org/pdf/2405.14855
19. Shin et al., "WHAM", CVPR 2024. https://openaccess.thecvf.com/content/CVPR2024/html/Shin_WHAM_Reconstructing_World-grounded_Humans_with_Accurate_3D_Motion_CVPR_2024_paper.html
20. WHAM arXiv. https://arxiv.org/pdf/2312.07531
21. WHAM repository. https://github.com/yohanshin/WHAM
22. Wang et al., "TRAM", ECCV 2024. https://arxiv.org/abs/2403.17346 ; https://eccv.ecva.net/virtual/2024/poster/255
23. TRAM repository. https://github.com/yufu-wang/tram
24. Yuan et al., "GLAMR", CVPR 2022. https://openaccess.thecvf.com/content/CVPR2022/html/Yuan_GLAMR_Global_Occlusion-Aware_Human_Mesh_Recovery_With_Dynamic_Cameras_CVPR_2022_paper.html ; https://arxiv.org/abs/2112.01524
25. GLAMR repository. https://github.com/NVlabs/GLAMR
26. Liu et al., "Joint Optimization for 4D Human-Scene Reconstruction in the Wild" (JOSH), ICLR 2026. https://arxiv.org/abs/2501.02158 ; https://arxiv.org/html/2501.02158v2
27. JOSH ICLR page and review. https://iclr.cc/virtual/2026/poster/10011275 ; https://themoonlight.io/review/joint-optimization-for-4d-human-scene-reconstruction-in-the-wild
28. Qiu et al., "AirDOS: Dynamic SLAM benefits from Articulated Objects", ICRA 2022. https://arxiv.org/abs/2109.09903 ; https://ri.cmu.edu/publications/airdos-dynamic-slam-benefits-from-articulated-objects
29. AirDOS repository. https://github.com/haleqiu/AirDOS
30. Survey describing AirDOS human keypoints/rods (2026). https://wujns.edpsciences.org/10.1051/wujns/2026311045
31. AirDOS full text, ATE tables (via search excerpt). https://ar5iv.labs.arxiv.org/html/2109.09903
32. Zhang et al., "VDO-SLAM". https://arxiv.org/abs/2005.11052
33. VDO-SLAM repository. https://github.com/halajun/VDO_SLAM
34. VDO-SLAM full text (Table I, KITTI exclusions). https://ar5iv.labs.arxiv.org/html/2005.11052
35. Huang et al., "ClusterVO", CVPR 2020. https://openaccess.thecvf.com/content_CVPR_2020/html/Huang_ClusterVO_Clustering_Moving_Instances_and_Estimating_Visual_Odometry_for_Self_CVPR_2020_paper.html ; https://arxiv.org/abs/2003.12980
36. Bescos et al., "DynaSLAM", RA-L 2018. https://arxiv.org/abs/1806.05620
37. DynoSAM full text (camera vs VDO-SLAM, ME metric). https://arxiv.org/html/2501.11893v1
38. DynaSLAM repository. https://github.com/BertaBescos/DynaSLAM
39. Bescos et al., "DynaSLAM II". https://arxiv.org/abs/2010.07820
40. Morris et al., "DynoSAM". https://arxiv.org/abs/2501.11893
41. DynoSAM repository. https://github.com/ACFR-RPG/DynOSAM
42. Morris, Wang, Ila, "Online Dynamic SLAM with Incremental Smoothing and Mapping", 2025. https://arxiv.org/abs/2509.08197
43. Zhao et al., "Synergistic Global-space Camera and Human Reconstruction from Videos", CVPR 2024. https://openaccess.thecvf.com/content/CVPR2024/html/Zhao_Synergistic_Global-space_Camera_and_Human_Reconstruction_from_Videos_CVPR_2024_paper.html
44. Yin et al., "WHAC", ECCV 2024. https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/4945_ECCV_2024_paper.php ; https://mlanthology.org/eccv/2024/yin2024eccv-whac/
45. WHAC arXiv HTML. https://arxiv.org/html/2403.12959v1
46. WHAC ECCV PDF. https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/04945.pdf
47. Yang et al., "Humans as Checkerboards", ICCV 2025. https://mlanthology.org/iccv/2025/yang2025iccv-humans/ ; https://arxiv.org/abs/2407.00574
48. HAC PDF (metric definitions incl. ATE, ATE-S). https://arxiv.org/pdf/2407.00574
49. Chen et al., "Human3R: Everyone Everywhere All at Once", ICLR 2026. https://arxiv.org/abs/2510.06219 ; https://www.iclr.cc/virtual/2026/poster/10006590
50. Human3R repository. https://github.com/fanegg/Human3R
51. Zhan, Ye, Zhang, "Monocular Person Localization under Camera Ego-motion", 2025. https://arxiv.org/abs/2503.02916
52. Giberna et al., "DYNEMO-SLAM: Dynamic Entity and Motion-Aware 3D Scene Graph SLAM". https://arxiv.org/abs/2503.02050 ; https://arxiv.org/html/2503.02050v2
53. ORBilu record for [52]. https://orbilu.uni.lu/handle/10993/66638
54. Tokhchukov, Morozova, Ferrer, "DynoSLAM: Dynamic SLAM with Generative Graph Neural Networks for Real-World Social Navigation", 2026. https://arxiv.org/abs/2605.02759
55. vS-Graphs paper. https://arxiv.org/html/2503.01783v2
56. visual_sgraphs repository (RGB-D / RGB-D-inertial, GPL-3.0). https://github.com/snt-arg/visual_sgraphs
57. Bamdad, Hutter, Darvishy, "InCrowd-VI", Sensors 2024. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11679079/ ; https://arxiv.org/abs/2411.14358
58. Sucar, Hayet, "Bayesian Scale Estimation for Monocular SLAM Based on Generic Object Detection for Correcting Scale Drift". https://arxiv.org/abs/1711.02768
59. "Object-Aware Bundle Adjustment For Correcting Monocular Scale Drift" (Oxford). https://ora.ox.ac.uk/objects/uuid:580d2b5d-f8a0-44bb-bb8b-cd7518b97b16
60. Yang, Scherer, "CubeSLAM: Monocular 3D Object SLAM", T-RO 2019. https://arxiv.org/abs/1806.00557

uHumans2 dataset page (not reachable from this session): https://www.mit.edu/~arosinol/datasets/uHumans2
