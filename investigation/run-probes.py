#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import sys

artifact = Path(__file__).resolve().parent
cases = [
    ('entry-budget-red', 'investigation_packed_prefetch_obeys_the_configured_entry_budget', {}, 101),
    ('entry-budget-green', 'investigation_packed_prefetch_obeys_the_configured_entry_budget', {'KACHE_INV_ALLOW_TWO': '1'}, 0),
    ('plan-deadline-red', 'investigation_packed_prefetch_stops_starting_objects_after_plan_deadline', {}, 101),
    ('plan-deadline-green', 'investigation_packed_prefetch_stops_starting_objects_after_plan_deadline', {'KACHE_INV_FAST_CATALOG': '1'}, 0),
]
for label, test, overrides, expected in cases:
    if len(sys.argv) > 1 and not label.startswith(sys.argv[1]):
        continue
    env = os.environ.copy()
    env.pop('KACHE_INV_ALLOW_TWO', None)
    env.pop('KACHE_INV_FAST_CATALOG', None)
    env.update(overrides)
    args = [str(artifact / 'pack-probe'), f'daemon::tests::{test}', '--exact', '--nocapture', '--test-threads=1']
    result = subprocess.run(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (artifact / f'{label}.log').write_text(f'COMMAND: {args!r}\nFIXTURE_OVERRIDES: {overrides!r}\nEXIT: {result.returncode}\n' + result.stdout)
    print(f'{label}: observed {result.returncode}, expected {expected}')
    if result.returncode != expected:
        print(result.stdout)
        sys.exit(1)
