#!/usr/bin/env python3
"""Reproduce a `kache test-runner` admission surge and measure its cost.

M concurrent `cargo nextest` runs, each with T test threads, start one
`kache test-runner` wrapper per test and compete for the test slots of one
shared scheduler. Every run lives in its own transient systemd scope so its
cgroup counters can be read, and a sampler thread records host load once per
second. The per-admission counters (`KACHE_ADMISSION_STATS`) are written by
the kache binary under test; this module only drives and parses.

The pure parsing and aggregation functions take text or lists and are
covered by `tests/test_admission.py`; the functions that launch processes
sit after them and are exercised by a smoke run.
"""

import argparse
import json
import math
import os
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timezone
from pathlib import Path

CGROUP_FILES = ("cpu.stat", "pids.peak", "memory.peak", "cpu.pressure")
ADMISSION_KEYS = (
    "pid",
    "key",
    "want",
    "held",
    "wait_us",
    "admit_calls",
    "lock_attempts",
    "lock_wait_us",
    "lock_holds",
    "lock_hold_us",
    "lock_gave_up",
    "parks",
    "park_us",
    "unordered",
    "claims",
    "unlocked",
)
NO_ADMISSION_STATS = (
    "no admission stats: the kache binary did not write KACHE_ADMISSION_STATS"
)
TIMESERIES_HEADER = (
    "ts load1 procs_running ctxt_per_s cpu_user_pct cpu_sys_pct cpu_idle_pct "
    "psi_cpu_some10 queue_depth engine_procs mem_avail_gb"
)
# Seconds systemd gives a scope beyond the harness's own run timeout before
# it kills the scope itself: the backstop for a harness process that is
# starved or gone.
SCOPE_GRACE_S = 30
# cgroup cpu.weight for the runs (default 100): the host's shells and the
# sampler outrank the load generator when every CPU is busy.
RUN_CPU_WEIGHT = 50
# Consecutive samples over the runnable-task cap before the guard trips;
# `procs_running` is an instantaneous count and spikes on its own.
RUNNING_STREAK = 3
SCRUBBED_ENV = re.compile(r"^(NEXTEST.*|KACHE_CARGO_PROXY_.*|CARGO_TARGET_.*_RUNNER)$")
NEXTEST_CONFIG = """[profile.ci]
fail-fast = false
[profile.ci.junit]
path = "junit.xml"
"""


# --- pure functions ---------------------------------------------------------


def utc_stamp(when=None):
    when = when or datetime.now(timezone.utc)
    return when.strftime("%Y%m%dT%H%M%SZ")


def utc_iso(when=None):
    when = when or datetime.now(timezone.utc)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def argument_errors(kache, runs, threads, tests):
    """Return one message per rejected flag; empty when all are acceptable."""
    errors = []
    if not os.path.isabs(kache):
        errors.append(f"--kache: got {kache!r}, expected an absolute path")
    for flag, value in (("--runs", runs), ("--threads", threads), ("--tests", tests)):
        if value < 1:
            errors.append(f"{flag}: got {value!r}, expected an integer >= 1")
    return errors


def percentile(values, pct):
    """Nearest-rank percentile of a non-empty list."""
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def describe(values):
    if not values:
        return {"count": 0, "mean": None, "p50": None, "p99": None, "max": None}
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "p50": percentile(values, 50),
        "p99": percentile(values, 99),
        "max": max(values),
    }


def parse_cpu_stat(text):
    """`cpu.stat` (`key value` lines) as a dict of ints; malformed lines are skipped."""
    stat = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("-").isdigit():
            stat[parts[0]] = int(parts[1])
    return stat


def parse_cgroup_dump(text):
    """Split a `run-<i>.cgroup` dump (`== <name>` sections) into name -> content."""
    sections = {}
    name = None
    for line in text.splitlines():
        if line.startswith("== "):
            name = line[3:].strip()
            sections[name] = ""
        elif name is not None:
            sections[name] += line + "\n"
    return sections


def cgroup_summary(text):
    sections = parse_cgroup_dump(text)
    cpu = parse_cpu_stat(sections.get("cpu.stat", ""))
    return {
        "user_usec": cpu.get("user_usec", 0),
        "system_usec": cpu.get("system_usec", 0),
        "pids_peak": parse_int(sections.get("pids.peak", "")),
        "memory_peak": parse_int(sections.get("memory.peak", "")),
        "cpu_pressure": sections.get("cpu.pressure", "").strip(),
    }


def parse_int(text):
    text = text.strip()
    return int(text) if text.lstrip("-").isdigit() else None


def parse_junit(text):
    """Every `<testcase time="...">` in seconds, in document order."""
    root = ElementTree.fromstring(text)
    times = []
    for case in root.iter("testcase"):
        value = case.get("time")
        if value is not None:
            times.append(float(value))
    return times


def junit_summary(times):
    stats = describe([t * 1000 for t in times])
    return {f"{k}_ms" if k != "count" else k: v for k, v in stats.items()}


def aggregate_admission(lines):
    """Summarise `admission.jsonl` records; `None` when there are none."""
    records = [json.loads(line) for line in lines if line.strip()]
    if not records:
        return None
    holds = sum(r.get("lock_holds", 0) for r in records)
    hold_us = sum(r.get("lock_hold_us", 0) for r in records)
    count = len(records)
    summary = {"lines": count}
    for key in ("lock_attempts", "wait_us", "lock_wait_us"):
        values = [r.get(key, 0) for r in records]
        summary[key] = {
            "mean": statistics.fmean(values),
            "p50": percentile(values, 50),
            "p99": percentile(values, 99),
        }
    summary["mean_hold_us"] = hold_us / holds if holds else None
    summary["gave_up_fraction"] = (
        sum(1 for r in records if r.get("lock_gave_up", 0) > 0) / count
    )
    summary["unordered_fraction"] = (
        sum(1 for r in records if r.get("unordered", 0) > 0) / count
    )
    summary["not_leased_fraction"] = (
        sum(1 for r in records if r.get("held", 0) == 0) / count
    )
    summary["claimed_fraction"] = (
        sum(1 for r in records if r.get("claims", 0) > 0) / count
    )
    summary["unlocked_fraction"] = (
        sum(1 for r in records if r.get("unlocked", 0) > 0) / count
    )
    return summary


def parse_proc_stat(text):
    """`ctxt` and the aggregate `cpu` line of `/proc/stat`."""
    snapshot = {"ctxt": 0, "cpu": []}
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "ctxt":
            snapshot["ctxt"] = int(parts[1])
        elif parts[0] == "cpu":
            snapshot["cpu"] = [int(v) for v in parts[1:]]
    return snapshot


def proc_stat_delta(previous, current, seconds):
    """Context switches per second and user/sys/idle percentages between snapshots.

    user = user + nice, sys = system + irq + softirq, idle = idle + iowait,
    each as a share of the total tick delta.
    """
    ctxt = (current["ctxt"] - previous["ctxt"]) / seconds if seconds > 0 else 0.0
    prev = previous["cpu"] + [0] * (8 - len(previous["cpu"]))
    cur = current["cpu"] + [0] * (8 - len(current["cpu"]))
    delta = [c - p for c, p in zip(cur, prev)]
    total = sum(delta)
    if total <= 0:
        return {"ctxt_per_s": ctxt, "user_pct": 0.0, "sys_pct": 0.0, "idle_pct": 0.0}
    user = delta[0] + delta[1]
    system = delta[2] + delta[5] + delta[6]
    idle = delta[3] + delta[4]
    return {
        "ctxt_per_s": ctxt,
        "user_pct": 100 * user / total,
        "sys_pct": 100 * system / total,
        "idle_pct": 100 * idle / total,
    }


def parse_pressure_some10(text):
    for line in text.splitlines():
        if line.startswith("some "):
            for field in line.split()[1:]:
                if field.startswith("avg10="):
                    return float(field[6:])
    return 0.0


def timeseries_summary(rows):
    """Peaks and means over sampler rows (dicts keyed by the TSV header)."""
    if not rows:
        return {
            "samples": 0,
            "peak_load1": None,
            "peak_queue_depth": None,
            "peak_engine_procs": None,
            "mean_ctxt_per_s": None,
            "mean_cpu_sys_pct": None,
            "peak_procs_running": None,
            "min_mem_avail_gb": None,
        }
    return {
        "samples": len(rows),
        "peak_load1": max(r["load1"] for r in rows),
        "peak_procs_running": max(r.get("procs_running", 0) for r in rows),
        "min_mem_avail_gb": min(r.get("mem_avail_gb", math.inf) for r in rows),
        "peak_queue_depth": max(r["queue_depth"] for r in rows),
        "peak_engine_procs": max(r["engine_procs"] for r in rows),
        "mean_ctxt_per_s": statistics.fmean(r["ctxt_per_s"] for r in rows),
        "mean_cpu_sys_pct": statistics.fmean(r["cpu_sys_pct"] for r in rows),
    }


def guard_verdict(row, caps, streak):
    """Why the run must stop now, or None, plus the new over-cap streak.

    `caps` has `load`, `running` and `mem_gb`; zero or None disables a cap.
    Load and memory trip on one sample; runnable tasks trip after
    RUNNING_STREAK consecutive samples over the cap.
    """
    if caps.get("load") and row["load1"] > caps["load"]:
        return f"load1 {row['load1']:.1f} over cap {caps['load']:.1f}", streak
    if caps.get("mem_gb") and row["mem_avail_gb"] < caps["mem_gb"]:
        return (
            f"MemAvailable {row['mem_avail_gb']:.1f} GiB under floor {caps['mem_gb']:.1f}",
            streak,
        )
    if caps.get("running") and row["procs_running"] > caps["running"]:
        streak += 1
        if streak >= RUNNING_STREAK:
            return (
                f"procs_running {row['procs_running']} over cap {caps['running']} "
                f"for {streak} samples",
                streak,
            )
        return None, streak
    return None, 0


def parse_mem_available_gb(text):
    """`MemAvailable` from /proc/meminfo text, in GiB; 0 when absent."""
    for line in text.splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / (1024 * 1024)
    return 0.0


def scrub_env(env):
    return {k: v for k, v in env.items() if not SCRUBBED_ENV.match(k)}


def crate_sources(tests):
    """Relative path -> content for the synthetic crate with `tests` empty tests."""
    body = "".join(f"    #[test]\n    fn t_{i}() {{}}\n" for i in range(tests))
    return {
        "Cargo.toml": (
            '[package]\nname = "admission-probe"\nversion = "0.0.0"\n'
            'edition = "2024"\n\n[workspace]\n'
        ),
        "src/lib.rs": f"#[cfg(test)]\nmod tests {{\n{body}}}\n",
        ".config/nextest.toml": NEXTEST_CONFIG,
    }


def run_config(out, index):
    """Per-run nextest config: the ci profile plus a store dir inside the extract dir.

    nextest resolves `store.dir` against the (remapped) workspace root, so without
    this every concurrent run would write the same `crate/target/nextest/ci/junit.xml`.
    """
    store = out / f"run-{index}" / "target" / "nextest"
    return f'[store]\ndir = "{store}"\n\n' + NEXTEST_CONFIG


def run_script(cpus, out, index):
    """The `sh -c` body of one run: nextest, then the scope's cgroup counters."""
    log = out / f"run-{index}.log"
    dump = out / f"run-{index}.cgroup"
    nextest = [
        "cargo",
        "nextest",
        "run",
        "--archive-file",
        str(out / "tests.tar.zst"),
        "--extract-to",
        str(out / f"run-{index}"),
        "--workspace-remap",
        str(out / "crate"),
        "--profile",
        "ci",
        "--no-fail-fast",
        "--config-file",
        str(out / f"run-{index}" / "nextest.toml"),
    ]
    if cpus:
        nextest = ["taskset", "-c", cpus] + nextest
    files = " ".join(CGROUP_FILES)
    return (
        f"{shlex.join(nextest)} >{shlex.quote(str(log))} 2>&1; rc=$?; "
        "cg=$(cut -d: -f3 /proc/self/cgroup); "
        f'for f in {files}; do echo "== $f"; cat "/sys/fs/cgroup$cg/$f"; done '
        f">>{shlex.quote(str(dump))} 2>&1; exit $rc"
    )


def runner_command(args):
    """The target runner the run measures: none, the one given, or kache's."""
    if args.no_runner:
        return None
    return args.runner if args.runner is not None else f"{args.kache} test-runner"


def run_env(base, runner, out, threads):
    """`runner` is Cargo's target runner command, or None to run the tests
    bare: no wrapper, so no admission and no admission stats, the floor
    the wrapper is measured against."""
    env = scrub_env(base)
    env.update(
        {
            "KACHE_CACHE_DIR": str(out / "cache"),
            "KACHE_RUNTIME_DIR": str(out / "cache"),
            "KACHE_NATIVE_RUNTIME_WARMUP": "0",
            "NEXTEST_TEST_THREADS": str(threads),
            "KACHE_ADMISSION_STATS": str(out / "admission.jsonl"),
        }
    )
    if runner is not None:
        env["CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER"] = runner
    return env


def fmt(value, digits=1):
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def summary_markdown(summary):
    """A metric/value table of the summary, with the admission notice when absent."""
    p = summary["parameters"]
    rows = [
        ("kache", summary["kache_version"]),
        ("commit", summary["git_head"]),
        ("runs x threads x tests", f'{p["runs"]} x {p["threads"]} x {p["tests"]}'),
        ("cpus", p["cpus"] or "(no taskset)"),
        ("start / end (UTC)", f'{summary["start_utc"]} / {summary["end_utc"]}'),
    ]
    rows += run_rows(summary["runs"])
    rows += junit_rows(summary["junit"])
    rows += cgroup_rows(summary["cgroup"], summary["cpu_seconds_per_test"])
    rows += timeseries_rows(summary["timeseries"])
    rows += admission_rows(summary["admission"])
    lines = ["| metric | value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in rows]
    return "\n".join(lines) + "\n"


def run_rows(runs):
    walls = [r["wall_s"] for r in runs]
    status = ", ".join(
        "timeout" if r["timed_out"] else str(r["exit_status"]) for r in runs
    )
    return [
        ("run wall s (mean / max)", f"{fmt(statistics.fmean(walls))} / {fmt(max(walls))}"),
        ("run exit statuses", status),
    ]


def junit_rows(junit):
    return [
        ("junit testcases", junit["count"]),
        (
            "testcase ms (mean / p50 / p99 / max)",
            " / ".join(fmt(junit[k], 2) for k in ("mean_ms", "p50_ms", "p99_ms", "max_ms")),
        ),
    ]


def cgroup_rows(cgroup, per_test):
    return [
        ("cgroup user s (per run)", ", ".join(fmt(u / 1e6) for u in cgroup["user_usec"])),
        ("cgroup system s (per run)", ", ".join(fmt(s / 1e6) for s in cgroup["system_usec"])),
        ("cgroup user s (sum)", fmt(cgroup["user_usec_total"] / 1e6)),
        ("cgroup system s (sum)", fmt(cgroup["system_usec_total"] / 1e6)),
        ("pids.peak (max)", fmt(cgroup["pids_peak_max"])),
        ("CPU s per test", fmt(per_test, 4)),
    ]


def timeseries_rows(ts):
    return [
        ("samples", ts["samples"]),
        ("peak load1", fmt(ts["peak_load1"], 2)),
        ("peak procs_running", fmt(ts["peak_procs_running"])),
        ("min MemAvailable GiB", fmt(ts["min_mem_avail_gb"])),
        ("peak queue_depth", fmt(ts["peak_queue_depth"])),
        ("peak engine_procs", fmt(ts["peak_engine_procs"])),
        ("mean ctxt/s", fmt(ts["mean_ctxt_per_s"], 0)),
        ("mean cpu_sys_pct", fmt(ts["mean_cpu_sys_pct"])),
    ]


def admission_rows(adm):
    if adm is None:
        return [("admission", NO_ADMISSION_STATS)]
    rows = [("admission lines", adm["lines"])]
    for key in ("lock_attempts", "wait_us", "lock_wait_us"):
        d = adm[key]
        rows.append((f"{key} (mean / p50 / p99)", f'{fmt(d["mean"])} / {d["p50"]} / {d["p99"]}'))
    rows += [
        ("mean hold us per acquisition", fmt(adm["mean_hold_us"])),
        ("lock_gave_up > 0", fmt(adm["gave_up_fraction"], 3)),
        ("unordered > 0", fmt(adm["unordered_fraction"], 3)),
        ("held == 0", fmt(adm["not_leased_fraction"], 3)),
        ("claims > 0", fmt(adm["claimed_fraction"], 3)),
        ("unlocked > 0", fmt(adm["unlocked_fraction"], 3)),
    ]
    return rows


def build_summary(args, results, junit_times, admission, cgroups, rows, meta):
    user = [c["user_usec"] for c in cgroups]
    system = [c["system_usec"] for c in cgroups]
    peaks = [c["pids_peak"] for c in cgroups if c["pids_peak"] is not None]
    total_cpu_s = (sum(user) + sum(system)) / 1e6
    return {
        "parameters": {
            "kache": args.kache,
            "runs": args.runs,
            "threads": args.threads,
            "tests": args.tests,
            "cpus": args.cpus,
            "out": str(args.out),
            "run_timeout": args.run_timeout,
            "load_cap": args.load_cap,
            "running_cap": args.running_cap,
            "mem_floor_gb": args.mem_floor_gb,
        },
        "aborted": read_or_empty(args.out / "aborted").strip() or None,
        **meta,
        "runs": results,
        "junit": junit_summary(junit_times),
        "admission": admission,
        "admission_notice": None if admission else NO_ADMISSION_STATS,
        "cgroup": {
            "user_usec": user,
            "system_usec": system,
            "user_usec_total": sum(user),
            "system_usec_total": sum(system),
            "pids_peak_max": max(peaks) if peaks else None,
            "per_run": cgroups,
        },
        "timeseries": timeseries_summary(rows),
        "cpu_seconds_per_test": total_cpu_s / len(junit_times) if junit_times else None,
    }


# --- process launchers ------------------------------------------------------


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kache", required=True, help="absolute path of the kache binary")
    parser.add_argument("--runs", type=int, default=8, help="concurrent nextest runs")
    parser.add_argument("--threads", type=int, default=8, help="NEXTEST_TEST_THREADS per run")
    parser.add_argument("--tests", type=int, default=2000, help="tests in the synthetic crate")
    parser.add_argument("--cpus", default="0-7", help="taskset -c mask; empty disables taskset")
    parser.add_argument("--out", type=Path, default=None, help="output directory")
    parser.add_argument("--keep-extracts", action="store_true")
    parser.add_argument(
        "--no-runner",
        action="store_true",
        help="run the tests without the kache test-runner wrapper",
    )
    parser.add_argument(
        "--runner",
        default=None,
        help="Cargo target runner command to measure instead of `<kache> test-runner`",
    )
    parser.add_argument("--run-timeout", type=float, default=600.0)
    parser.add_argument(
        "--load-cap", type=float, default=0.0, help="kill every run when load1 exceeds this"
    )
    parser.add_argument(
        "--running-cap",
        type=int,
        default=0,
        help=f"kill every run when procs_running exceeds this for {RUNNING_STREAK} samples",
    )
    parser.add_argument(
        "--mem-floor-gb",
        type=float,
        default=0.0,
        help="kill every run when MemAvailable falls under this many GiB",
    )
    args = parser.parse_args(argv)
    errors = argument_errors(args.kache, args.runs, args.threads, args.tests)
    if errors:
        parser.error("; ".join(errors))
    args.stamp = utc_stamp()
    if args.out is None:
        args.out = Path("tmp/bench/admission") / args.stamp
    args.out = args.out.resolve()
    return args


def write_crate(out, tests):
    for rel, content in crate_sources(tests).items():
        path = out / "crate" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


def archive(out):
    env = scrub_env(os.environ)
    env["CARGO_TARGET_DIR"] = str(out / "crate" / "target")
    command = [
        "cargo",
        "nextest",
        "archive",
        "--manifest-path",
        str(out / "crate" / "Cargo.toml"),
        "--archive-file",
        str(out / "tests.tar.zst"),
    ]
    done = subprocess.run(command, env=env, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"cargo nextest archive failed ({done.returncode}):\n{done.stderr}")


def launch_run(args, index, env, results):
    unit = f"admission-{args.stamp}-{index}"
    command = [
        "systemd-run",
        "--user",
        "--scope",
        "--quiet",
        "--collect",
        "--unit",
        unit,
        "-p",
        f"RuntimeMaxSec={int(args.run_timeout) + SCOPE_GRACE_S}",
        "-p",
        f"CPUWeight={RUN_CPU_WEIGHT}",
        "--",
        "sh",
        "-c",
        run_script(args.cpus, args.out, index),
    ]
    extract = args.out / f"run-{index}"
    extract.mkdir(parents=True, exist_ok=True)
    (extract / "nextest.toml").write_text(run_config(args.out, index))
    started = time.monotonic()
    proc = subprocess.Popen(command, env=env)
    timed_out = False
    try:
        status = proc.wait(timeout=args.run_timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        subprocess.run(
            ["systemctl", "--user", "kill", "--signal=KILL", f"{unit}.scope"],
            check=False,
        )
        status = proc.wait()
    results[index] = {
        "index": index,
        "unit": unit,
        "wall_s": time.monotonic() - started,
        "exit_status": status,
        "timed_out": timed_out,
    }


def read_sample_sources(out):
    queue = out / "cache" / "scheduler" / "queue"
    try:
        depth = sum(1 for _ in queue.iterdir())
    except OSError:
        depth = 0
    engines = 0
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            engines += comm.read_text().strip() == "kache-engine"
        except OSError:
            continue
    return {
        "load1": float(Path("/proc/loadavg").read_text().split()[0]),
        "procs_running": int(parse_proc_field("procs_running")),
        "psi": parse_pressure_some10(read_or_empty(Path("/proc/pressure/cpu"))),
        "queue_depth": depth,
        "engine_procs": engines,
        "mem_avail_gb": parse_mem_available_gb(read_or_empty(Path("/proc/meminfo"))),
    }


def parse_proc_field(name):
    for line in Path("/proc/stat").read_text().splitlines():
        if line.startswith(name + " "):
            return line.split()[1]
    return "0"


def read_or_empty(path):
    try:
        return path.read_text()
    except OSError:
        return ""


def sample_row(out, delta):
    src = read_sample_sources(out)
    return {
        "ts": utc_iso(),
        "load1": src["load1"],
        "procs_running": src["procs_running"],
        "ctxt_per_s": delta["ctxt_per_s"],
        "cpu_user_pct": delta["user_pct"],
        "cpu_sys_pct": delta["sys_pct"],
        "cpu_idle_pct": delta["idle_pct"],
        "psi_cpu_some10": src["psi"],
        "queue_depth": src["queue_depth"],
        "engine_procs": src["engine_procs"],
        "mem_avail_gb": src["mem_avail_gb"],
    }


def abort_runs(args, reason):
    """Kill every scope of this harness run at once and record why."""
    (args.out / "aborted").write_text(f"{utc_iso()} {reason}\n")
    subprocess.run(
        ["systemctl", "--user", "kill", "--signal=KILL", f"admission-{args.stamp}-*.scope"],
        check=False,
    )


def sampler(args, stop, rows):
    """One row per second into `timeseries.tsv` until `stop` is set, then a
    last row. Trips the guard, once, when a sample crosses a cap."""
    out = args.out
    caps = {"load": args.load_cap, "running": args.running_cap, "mem_gb": args.mem_floor_gb}
    streak = 0
    tripped = False
    previous = parse_proc_stat(Path("/proc/stat").read_text())
    last = time.monotonic()
    with open(out / "timeseries.tsv", "w") as sink:
        sink.write(TIMESERIES_HEADER.replace(" ", "\t") + "\n")
        stopped = False
        while not stopped:
            stopped = stop.wait(1.0)
            now = time.monotonic()
            if stopped and now - last < 0.05:
                break
            current = parse_proc_stat(Path("/proc/stat").read_text())
            delta = proc_stat_delta(previous, current, now - last)
            previous, last = current, now
            row = sample_row(out, delta)
            rows.append(row)
            sink.write("\t".join(fmt(v, 2) for v in row.values()) + "\n")
            sink.flush()
            reason, streak = guard_verdict(row, caps, streak)
            if reason and not tripped:
                tripped = True
                sys.stderr.write(f"guard: {reason}; killing every run\n")
                abort_runs(args, reason)


def run_all(args, env):
    results = {}
    rows = []
    stop = threading.Event()
    sampling = threading.Thread(target=sampler, args=(args, stop, rows), daemon=True)
    sampling.start()
    threads = [
        threading.Thread(target=launch_run, args=(args, i, env, results))
        for i in range(args.runs)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    stop.set()
    sampling.join()
    return [results[i] for i in range(args.runs)], rows


def stop_daemon(args, env):
    subprocess.run(
        [args.kache, "daemon", "stop"],
        env=env,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def collect_junit(args):
    times = []
    for i in range(args.runs):
        for path in (args.out / f"run-{i}").rglob("junit.xml"):
            times += parse_junit(path.read_text())
    return times


def collect_cgroups(args):
    return [
        cgroup_summary(read_or_empty(args.out / f"run-{i}.cgroup"))
        for i in range(args.runs)
    ]


def collect_meta(args, start):
    version = subprocess.run(
        [args.kache, "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()
    worktree = Path(__file__).resolve().parents[2]
    head = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return {
        "kache_version": version,
        "git_head": head,
        "start_utc": start,
        "end_utc": utc_iso(),
    }


def main(argv=None):
    args = parse_args(argv)
    start = utc_iso()
    args.out.mkdir(parents=True, exist_ok=True)
    write_crate(args.out, args.tests)
    archive(args.out)
    env = run_env(os.environ, runner_command(args), args.out, args.threads)
    results, rows = run_all(args, env)
    stop_daemon(args, env)
    junit_times = collect_junit(args)
    if not args.keep_extracts:
        for i in range(args.runs):
            shutil.rmtree(args.out / f"run-{i}", ignore_errors=True)
    admission_lines = read_or_empty(args.out / "admission.jsonl").splitlines()
    summary = build_summary(
        args,
        results,
        junit_times,
        aggregate_admission(admission_lines),
        collect_cgroups(args),
        rows,
        collect_meta(args, start),
    )
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    markdown = summary_markdown(summary)
    (args.out / "summary.md").write_text(markdown)
    sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
