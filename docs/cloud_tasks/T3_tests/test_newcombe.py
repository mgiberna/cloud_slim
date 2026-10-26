"""T3 test 3: Newcombe hybrid score interval (method 10) against Newcombe (1998), Stat Med 17:873, Table II, two-sided 95 %."""
import _paths  # noqa: F401
import p9d_analyze as A

cases = [((56, 70, 48, 80), (0.0524, 0.3339)), ((9, 10, 3, 10), (0.1705, 0.8090)), ((6, 7, 2, 7), (0.0582, 0.8062)),
         ((5, 56, 0, 29), (-0.0381, 0.1926)), ((0, 10, 0, 20), (-0.1611, 0.2775)), ((10, 10, 0, 20), (0.6791, 1.0000))]
for (x1, n1, x2, n2), (lo, hi) in cases:
    d = A.newcombe_diff(x1, n1, x2, n2)
    print(f'{x1}/{n1} - {x2}/{n2}: code [{d["lo95"]:.4f}, {d["hi95"]:.4f}]  published [{lo:.4f}, {hi:.4f}]  one-sided ub95 {d["ub95"]:.4f}')
    assert abs(d['lo95'] - lo) < 1e-4 and abs(d['hi95'] - hi) < 1e-4
# direction: arm - OFF (camera_test passes arm first)
t = A.camera_test([dict(m1=1, event=i < 30) for i in range(60)], [dict(m1=1, event=i < 6) for i in range(60)])
print('ON 30/60 events vs OFF 6/60: point', round(t['M2']['point'], 3), 'ub95', round(t['M2']['ub95'], 3), 'status', t['M2']['status'])
assert t['M2']['point'] > 0 and t['M2']['status'] == 'degradation'
print('test_newcombe OK')
