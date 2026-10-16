#!/usr/bin/env python3
"""Persist unedited stdout/stderr and exit status of baseline red probes."""
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
for case in sys.argv[1:]:
    argv = [sys.executable, str(ROOT / 'investigation/probes/real_compile_report.py'), case]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60)
    stem = ROOT / 'investigation/evidence' / ('red-' + case)
    stem.with_suffix('.stdout.txt').write_text(result.stdout)
    stem.with_suffix('.stderr.txt').write_text(result.stderr)
    stem.with_suffix('.result.json').write_text(json.dumps({'argv': argv, 'workdir': str(ROOT), 'exit_code': result.returncode}, indent=2))
    print(case + ': exit=' + str(result.returncode) + '\n' + result.stdout + result.stderr)
