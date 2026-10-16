#!/usr/bin/env python3
"""Recreate all generated data and execute one hydration contract assertion."""
import argparse
from pathlib import Path
import shutil
import ci_probe

parser = argparse.ArgumentParser()
parser.add_argument('case', choices=['residue', 'concurrent'])
parser.add_argument('--binary', type=Path, required=True)
args = parser.parse_args()
binary = args.binary.resolve()
assert binary.is_file(), binary
ci_probe.FIXTURE = ci_probe.ROOT / ('gate-fixture-' + args.case)
ci_probe.RAW = ci_probe.ROOT / ('gate-raw-' + args.case)
assert ci_probe.FIXTURE.is_relative_to(ci_probe.ROOT)
if ci_probe.FIXTURE.exists():
    shutil.rmtree(ci_probe.FIXTURE)
ci_probe.RAW.mkdir(exist_ok=True)
ci_probe.prepare()
ci_probe.seed(binary)
getattr(ci_probe, args.case)(binary)
