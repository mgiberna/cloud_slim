#!/bin/sh
# Runs every T3 synthetic test (needs numpy, scipy, evo). Read-only use of eval/phase9.
cd "$(dirname "$0")" && for t in test_bootstrap_inf test_one_sided test_newcombe test_main_map test_population test_power; do echo "== $t"; python3 $t.py || exit 1; done
