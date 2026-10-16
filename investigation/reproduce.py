"""Replay proof against unchanged production, retaining logs under investigation."""
from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "investigation"
BASELINE = "4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9"
ENV = dict(os.environ, RUSTC_WRAPPER="", HOST_CC="clang", HOST_CXX="clang++", CC="clang", CXX="clang++", CARGO_BUILD_JOBS="3", CARGO_TARGET_DIR=str(ARTIFACTS / "target"))


def run(args, log):
    result = subprocess.run(args, cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (ARTIFACTS / log).write_text(result.stdout)
    return result


def main():
    clean = run(["git", "diff", "--exit-code", BASELINE, "--", "crates", "src", "Cargo.toml", "Cargo.lock"], "production-diff.txt")
    if clean.returncode:
        raise RuntimeError("Production source differs from the reviewed baseline:\n" + clean.stdout)
    tests = run(["cargo", "test", "--locked", "--manifest-path", "investigation/harness/Cargo.toml", "--lib", "--", "--nocapture"], "backfill-test.log")
    required = [
        "test tests::compile_cost_backfill_does_not_starve_legacy_expensive_entry ... FAILED",
        "test tests::backfill_control_recovers_expensive_entry_inside_the_batch ... ok",
        "blocking_rows=10000 passes=[0, 0, 0] recovered_cost_ms=0",
        "blocking_rows=9999 passes=[1, 0, 0] recovered_cost_ms=60000",
        "test result: FAILED. 1 passed; 1 failed;",
    ]
    if tests.returncode != 101 or any(line not in tests.stdout for line in required):
        raise RuntimeError("Red/control pair did not produce the expected exact failures; cargo output:\n" + tests.stdout)
    experiment = subprocess.run(["cargo", "run", "--locked", "--manifest-path", "investigation/harness/Cargo.toml"], cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    (ARTIFACTS / "generated-traces-build.log").write_text(experiment.stderr)
    if experiment.returncode:
        raise RuntimeError("Generated-trace process failed: " + experiment.stderr)
    data = json.loads(experiment.stdout)
    scores = [[result["net_miss_cost_ms"] for result in trace["results"]] for trace in data["traces"]]
    if scores != [[59970, 6], [0, 6]]:
        raise RuntimeError(f"Independent future-demand costs changed: {scores}")
    (ARTIFACTS / "generated-traces.json").write_text(experiment.stdout)
    print("DONE: baseline production unchanged; exact red/control pair and two future-demand trace objectives reproduced")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise
