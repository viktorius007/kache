#!/usr/bin/env python3
"""Temporarily register report-only tests, replay them, and restore the suite file."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

BASELINE = "4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9"
REGISTRATION = '\n#[path = "../../investigation/multi_upload_gc.rs"]\nmod multi_upload_gc;\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("test", choices=["red", "control", "measure"])
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if revision != BASELINE:
        raise SystemExit(f"Refusing baseline replay: expected {BASELINE}, got {revision}")
    production_diff = subprocess.check_output([
        "git", "diff", "HEAD", "--", "src/daemon.rs", "src/volume_gc.rs",
        "src/disk_recovery.rs", "src/config.rs", "src/wrapper.rs",
        "crates/kache-store/src/store.rs",
    ], cwd=root, text=True)
    if production_diff:
        raise SystemExit("Refusing baseline replay: investigation production scope differs from HEAD")
    tests = root / "src/daemon/tests.rs"
    prior = tests.read_text()
    registered = prior.endswith(REGISTRATION)
    if not registered:
        if "mod multi_upload_gc;" in prior:
            raise SystemExit("Refusing ambiguous test registration")
        tests.write_text(prior + REGISTRATION)
    names = {
        "red": "two_async_workers_allow_health_while_main_and_shard_sweeps_wait_for_writers",
        "control": "two_async_workers_allow_health_while_one_store_sweep_waits_for_a_writer",
        "measure": "measure_pipeline_gc_capacity",
    }
    command = ["cargo", "test", "--locked", "--bin", "kache", names[args.test],
               "--", "--nocapture", "--test-threads=1"]
    if args.test == "measure":
        command.append("--ignored")
    env = os.environ.copy()
    env.update(RUSTC_WRAPPER="", HOST_CC="clang", HOST_CXX="clang++", CC="clang", CXX="clang++")
    env.setdefault("CARGO_TARGET_DIR", "/private/tmp/kache-d5-target")
    env.setdefault("CARGO_BUILD_JOBS", "2")
    try:
        result = subprocess.run(command, cwd=root, env=env, check=False)
        print(f"REPLAY {args.test}: exit={result.returncode}")
        return result.returncode
    finally:
        if not registered:
            current = tests.read_text()
            if not current.endswith(REGISTRATION):
                raise RuntimeError("Cannot safely remove changed test registration")
            tests.write_text(current[:-len(REGISTRATION)])


if __name__ == "__main__":
    sys.exit(main())
