#!/usr/bin/env python3
"""Replay a proof command; admit only its specified behavioral failure."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    case = json.loads(args.case.read_text())
    run = subprocess.run(case["argv"], cwd=case["workdir"], capture_output=True, text=True, timeout=case.get("timeout_seconds", 300))
    output = run.stdout + run.stderr
    args.output.write_text(output)
    expected = re.search(case["expected_failure_regex"], output) is not None
    assertion = re.search(case["assertion_regex"], output) is not None
    admitted = run.returncode != 0 and expected and assertion
    print(json.dumps({"verdict": "ADMITTED" if admitted else "REJECTED", "exit_code": run.returncode, "expected_failure_found": expected, "assertion_found": assertion, "log": str(args.output)}))
    return 0 if admitted else 1


if __name__ == "__main__":
    sys.exit(main())
