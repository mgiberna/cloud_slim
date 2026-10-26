#!/usr/bin/env python3
"""P9-C2 step 5 evaluation of one tuning iteration (TUNING sequences only). Run dirs: <root>/{on,off}_<seq> fetched from workstation-1
(tools/fetch_iter.sh). Per sequence: camera ATE / coverage / map events of both arms (P9-B code, p9b_ate.run_metrics with the GT body->camera
transform), pedestrian error flag-on and B0 (p9c_ped_error.py), per-factor-type counters. Output <root>/summary.json and a markdown block.
Usage: p9c2_iter.py ROOT C_L VARIANT..."""
import glob, json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'P9-B'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p9b_ate as B                       # noqa: E402
import c3b_ped_error as E                  # noqa: E402

GT = '/media/marco/muffin1/datasets/p9b_gt'
PED = '/media/marco/muffin1/datasets/p9c2_perception'
GTP = {'office_s1_12h': '/media/marco/muffin1/datasets/phase1/P1-A/office_s1_12h_gt.npz',
       'apartment_s1_01h': '/media/marco/muffin1/datasets/p9c_gt/apartment_s1_01h_gt.npz',
       'apartment_s1_02h': '/media/marco/muffin1/datasets/p9c_gt/apartment_s1_02h_gt.npz'}
TUNE = ['apartment_s1_01h', 'apartment_s1_02h', 'office_s1_12h']


def cam(rd, seq):
    gt = B.A.load_tum(f'{GT}/{seq}_gt_body.tum')
    tbc = json.load(open(f'{GT}/{seq}_gt_summary.json'))['T_b_c']
    m = B.run_metrics(rd, gt, tbc)
    return {k: m.get(k) for k in ('ok', 'ate_sim3', 'ate_se3', 'abs_log_scale', 'coverage', 'maps_at_shutdown', 'map_reset_count',
                                   'maps_retired_by_reset', 'tracking_lost_events', 'losses_resets', 'losses_new_maps', 'main_map_keyframes', 'rtf', 'wall_seconds')}


def counters(rd):
    p = f'{rd}/ped_counters.csv'
    if not os.path.exists(p):
        return None
    last = open(p).read().strip().split('\n')
    hdr = last[0].split(','); tot = last[-1].split(',')
    return {hdr[i]: int(tot[i]) for i in range(3, len(hdr))}


def main(root, cL, variants):
    """root/off_<seq> (flag-off, shared) and root/<variant>/on_<seq> per variant."""
    out = {}
    offs = {}
    for seq in TUNE:
        rd = f'{root}/off_{seq}'
        if os.path.isdir(rd) and os.path.exists(f'{rd}/run_summary.json'):
            offs[seq] = cam(rd, seq)
    out['off'] = offs
    f = lambda v, n=2: 'n/a' if v is None else f'{v:.{n}f}'
    print('| variant | seq | ATE sim3 / se3 | |log s| | coverage | resets/new maps | ped cam med (p90) | B0 cam med (p90) | ped world med | B0 world med | samples / matched tracks of states/tracks |')
    for seq in TUNE:
        a = offs.get(seq)
        if a:
            print(f"| off | {seq} | {f(a['ate_sim3'],3)} / {f(a['ate_se3'],3)} | {f(a['abs_log_scale'],4)} | {f(a['coverage'])} | {a['losses_resets']}/{a['losses_new_maps']} | | | | | |")
    for v in variants:
        out[v] = {}
        for seq in TUNE:
            rd = f'{root}/{v}/on_{seq}'
            if not os.path.exists(f'{rd}/run_summary.json'):
                continue
            a = cam(rd, seq)
            r = {'cam': a}
            if os.path.exists(f'{rd}/ped_log.txt'):
                summ, _, _ = E.evaluate(rd, GTP[seq], f'{PED}/{seq}', cL)
                r['ped'] = summ; r['counters'] = counters(rd)
                p, b = summ['flag_on'], summ['B0']
                print(f"| {v} | {seq} | {f(a['ate_sim3'],3)} / {f(a['ate_se3'],3)} | {f(a['abs_log_scale'],4)} | {f(a['coverage'])} | {a['losses_resets']}/{a['losses_new_maps']} | "
                      f"{f(p['cam']['median'])} ({f(p['cam']['p90'])}) | {f(b['cam']['median'])} ({f(b['cam']['p90'])}) | {f(p['world']['median'])} | {f(b['world']['median'])} | "
                      f"{p['n_samples']} / {p['n_tracks_matched']} of {p['n_states']}/{p['n_tracks']} |")
            out[v][seq] = r
    json.dump(out, open(f'{root}/summary.json', 'w'), indent=1, default=lambda o: None if isinstance(o, float) and math.isnan(o) else o)
    for v in variants:
        for seq in TUNE:
            c = out[v].get(seq, {}).get('counters')
            if c:
                print(v, seq, ' '.join(f"{k.replace('_created','')}={c[k]}/{c[k.replace('created','active')]}" for k in c if k.endswith('_created')))


if __name__ == '__main__':
    main(sys.argv[1], float(sys.argv[2]), sys.argv[3:])
