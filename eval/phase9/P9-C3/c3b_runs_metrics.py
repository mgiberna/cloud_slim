#!/usr/bin/env python3
"""P9-C3b: per-run plausibility shares for a set of runs, the same three measures for every candidate (so that the relative rule can be applied):
  speed   share of metric-map states with |v| * s_Sim3 > 3 m/s           (p9c2_plausibility.py)
  dist    share of metric-map states farther than 30 m from the camera   (p9c2_plausibility.py)
  contact share of metric-map states whose lowest-foot-ray point horizontally nearest to the optimised root is > 0.3 m from the GT floor (c3_contact_height_gt.py;
          states without a foot observation or without a GT floor are not counted)
Usage: c3b_runs_metrics.py ROOT OUT.json   ROOT/<cand>@<seed>/on_<seq>/ ; candidates and seeds are discovered"""
import glob, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
P9C2 = os.path.join(HERE, '..', 'P9-C2')
root, outp = sys.argv[1], sys.argv[2]
PERC = '/media/marco/muffin1/datasets/p9c3_perception'
FLOOR = os.environ.get('C3_FLOOR_DIR', '/tmp/claude-1000/-home-marco-workspaces-dv-sgraphs-src/0c965e1f-61aa-4098-be4d-e5235fada0ed/scratchpad')
res = {}
for rd in sorted(glob.glob(f'{root}/*@*/on_*')):
    cand, seed = os.path.basename(os.path.dirname(rd)).split('@'); seq = os.path.basename(rd)[3:]
    if not os.path.exists(f'{rd}/ped_log.txt'):
        continue
    p = subprocess.run([sys.executable, 'p9c2_plausibility.py', rd, seq], capture_output=True, text=True, cwd=P9C2)
    if not p.stdout.strip():
        raise SystemExit(f'plausibility failed for {rd}:\n{p.stderr[-800:]}')
    pl = json.loads(p.stdout.strip().splitlines()[-1])
    m = pl['metric_maps']
    c = subprocess.run([sys.executable, 'c3_contact_height_gt.py', rd, seq, f'{PERC}/{seq}', FLOOR, '/tmp/c3b_ch.json'], capture_output=True, text=True, cwd=HERE)
    if c.returncode != 0:
        raise SystemExit(f'contact height failed for {rd}:\n{c.stderr[-800:]}')
    ch = json.load(open('/tmp/c3b_ch.json'))
    res[f'{cand}|{seq}|{seed}'] = dict(n=m['n'], speed=m['speed'] / m['n'] if m['n'] else None, dist=m['dist'] / m['n'] if m['n'] else None,
                                     wrong_scale_states=pl['wrong_scale_maps']['n'], contact_n=ch.get('n'), contact=ch.get('share_abs_gt_0p3'))
    print(cand, seq, seed, res[f'{cand}|{seq}|{seed}'], flush=True)
json.dump(res, open(outp, 'w'), indent=1)
