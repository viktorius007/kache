#!/usr/bin/env python3
"""Exercise the pure parsers and aggregators of the admission surge harness."""

import json
import unittest
from pathlib import Path

from bench import admission

CPU_STAT = """usage_usec 1234567
user_usec 1000000
system_usec 234567
nr_periods 0
nr_throttled 0
throttled_usec 0
"""

JUNIT = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="nextest-run" tests="3" failures="0" errors="0">
  <testsuite name="admission-probe" tests="3">
    <testcase name="tests::t_0" classname="admission-probe" time="0.004"/>
    <testcase name="tests::t_1" classname="admission-probe" time="0.250">
      <failure message="boom"/>
    </testcase>
    <testcase name="tests::t_2" classname="admission-probe" time="1.5"/>
  </testsuite>
</testsuites>
"""


def admission_line(**fields):
    record = {key: 0 for key in admission.ADMISSION_KEYS}
    record.update({"pid": 1, "key": "k", "want": 1, "leased": True, "held": 1})
    record.update(fields)
    return json.dumps(record)


class CpuStatTest(unittest.TestCase):
    def test_parses_user_and_system_usec(self):
        stat = admission.parse_cpu_stat(CPU_STAT)
        self.assertEqual(stat["user_usec"], 1000000)
        self.assertEqual(stat["system_usec"], 234567)
        self.assertEqual(stat["nr_periods"], 0)

    def test_skips_malformed_lines(self):
        stat = admission.parse_cpu_stat("user_usec 5\nbroken\nx y z\nsystem_usec nope\n")
        self.assertEqual(stat, {"user_usec": 5})

    def test_cgroup_dump_sections_and_summary(self):
        dump = (
            "== cpu.stat\n" + CPU_STAT + "== pids.peak\n57\n== memory.peak\n4096\n"
            "== cpu.pressure\nsome avg10=1.00 avg60=0.50 avg300=0.10 total=7\n"
        )
        summary = admission.cgroup_summary(dump)
        self.assertEqual(summary["user_usec"], 1000000)
        self.assertEqual(summary["system_usec"], 234567)
        self.assertEqual(summary["pids_peak"], 57)
        self.assertEqual(summary["memory_peak"], 4096)
        self.assertTrue(summary["cpu_pressure"].startswith("some avg10=1.00"))

    def test_missing_dump_yields_zero_cpu_and_no_peak(self):
        summary = admission.cgroup_summary("")
        self.assertEqual((summary["user_usec"], summary["system_usec"]), (0, 0))
        self.assertIsNone(summary["pids_peak"])


class JunitTest(unittest.TestCase):
    def test_collects_every_testcase_time_in_seconds(self):
        self.assertEqual(admission.parse_junit(JUNIT), [0.004, 0.25, 1.5])

    def test_summary_is_in_milliseconds(self):
        summary = admission.junit_summary(admission.parse_junit(JUNIT))
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["max_ms"], 1500.0)
        self.assertEqual(summary["p50_ms"], 250.0)
        self.assertEqual(summary["p99_ms"], 1500.0)
        self.assertAlmostEqual(summary["mean_ms"], (4 + 250 + 1500) / 3)

    def test_empty_summary(self):
        summary = admission.junit_summary([])
        self.assertEqual(summary["count"], 0)
        self.assertIsNone(summary["mean_ms"])


class AdmissionAggregateTest(unittest.TestCase):
    def test_empty_input_is_none(self):
        self.assertIsNone(admission.aggregate_admission([]))
        self.assertIsNone(admission.aggregate_admission(["", "\n"]))

    def test_aggregates_counters_and_fractions(self):
        lines = [
            admission_line(lock_attempts=1, wait_us=10, lock_wait_us=5, lock_holds=1, lock_hold_us=20),
            admission_line(lock_attempts=3, wait_us=30, lock_wait_us=15, lock_holds=2, lock_hold_us=40, lock_gave_up=1),
            admission_line(lock_attempts=2, wait_us=20, lock_wait_us=10, lock_holds=1, lock_hold_us=30, unordered=2),
            admission_line(lock_attempts=10, wait_us=100, lock_wait_us=50, lock_holds=0, lock_hold_us=0, leased=False),
        ]
        summary = admission.aggregate_admission(lines)
        self.assertEqual(summary["lines"], 4)
        self.assertEqual(summary["lock_attempts"], {"mean": 4.0, "p50": 2, "p99": 10})
        self.assertEqual(summary["wait_us"], {"mean": 40.0, "p50": 20, "p99": 100})
        self.assertEqual(summary["lock_wait_us"], {"mean": 20.0, "p50": 10, "p99": 50})
        self.assertEqual(summary["mean_hold_us"], 90 / 4)
        self.assertEqual(summary["gave_up_fraction"], 0.25)
        self.assertEqual(summary["unordered_fraction"], 0.25)
        self.assertEqual(summary["not_leased_fraction"], 0.25)

    def test_no_holds_gives_no_mean_hold(self):
        summary = admission.aggregate_admission([admission_line(lock_holds=0)])
        self.assertIsNone(summary["mean_hold_us"])

    def test_markdown_carries_notice_when_absent(self):
        self.assertEqual(
            admission.admission_rows(None), [("admission", admission.NO_ADMISSION_STATS)]
        )


class ProcStatTest(unittest.TestCase):
    def test_deltas_to_rate_and_percentages(self):
        # user nice system idle iowait irq softirq steal
        previous = admission.parse_proc_stat("cpu 100 0 50 800 0 0 0 0\nctxt 1000\nprocs_running 3\n")
        current = admission.parse_proc_stat("cpu 160 10 70 900 10 5 5 0\nctxt 3500\nprocs_running 9\n")
        delta = admission.proc_stat_delta(previous, current, 2.0)
        # deltas: 60 10 20 100 10 5 5 0 -> total 210
        self.assertEqual(delta["ctxt_per_s"], 1250.0)
        self.assertAlmostEqual(delta["user_pct"], 100 * 70 / 210)
        self.assertAlmostEqual(delta["sys_pct"], 100 * 30 / 210)
        self.assertAlmostEqual(delta["idle_pct"], 100 * 110 / 210)

    def test_zero_total_is_all_zero(self):
        snap = admission.parse_proc_stat("cpu 1 1 1 1 1 1 1 1\nctxt 5\n")
        delta = admission.proc_stat_delta(snap, snap, 1.0)
        self.assertEqual(delta, {"ctxt_per_s": 0.0, "user_pct": 0.0, "sys_pct": 0.0, "idle_pct": 0.0})

    def test_pressure_some_avg10(self):
        text = "some avg10=5.16 avg60=5.83 avg300=4.11 total=1\nfull avg10=0.00 avg60=0.00 avg300=0.00 total=0\n"
        self.assertEqual(admission.parse_pressure_some10(text), 5.16)
        self.assertEqual(admission.parse_pressure_some10(""), 0.0)


class PercentileTest(unittest.TestCase):
    def test_nearest_rank_on_known_list(self):
        values = list(range(100, 0, -1))
        self.assertEqual(admission.percentile(values, 50), 50)
        self.assertEqual(admission.percentile(values, 99), 99)
        self.assertEqual(admission.percentile(values, 100), 100)
        self.assertEqual(admission.percentile(values, 0), 1)

    def test_small_lists(self):
        self.assertEqual(admission.percentile([7], 99), 7)
        self.assertEqual(admission.percentile([3, 1, 2], 50), 2)
        self.assertEqual(admission.percentile([3, 1, 2], 99), 3)

    def test_timeseries_summary(self):
        rows = [
            {"load1": 1.0, "queue_depth": 2, "engine_procs": 1, "ctxt_per_s": 100.0, "cpu_sys_pct": 10.0},
            {"load1": 9.5, "queue_depth": 7, "engine_procs": 3, "ctxt_per_s": 300.0, "cpu_sys_pct": 30.0},
        ]
        summary = admission.timeseries_summary(rows)
        self.assertEqual(summary["samples"], 2)
        self.assertEqual(summary["peak_load1"], 9.5)
        self.assertEqual(summary["peak_queue_depth"], 7)
        self.assertEqual(summary["peak_engine_procs"], 3)
        self.assertEqual(summary["mean_ctxt_per_s"], 200.0)
        self.assertEqual(summary["mean_cpu_sys_pct"], 20.0)
        self.assertEqual(admission.timeseries_summary([])["samples"], 0)


class ArgumentTest(unittest.TestCase):
    def test_accepts_valid_arguments(self):
        self.assertEqual(admission.argument_errors("/usr/bin/kache", 1, 1, 1), [])

    def test_rejects_relative_kache(self):
        errors = admission.argument_errors("bin/kache", 8, 8, 2000)
        self.assertEqual(errors, ["--kache: got 'bin/kache', expected an absolute path"])

    def test_rejects_each_count_below_one(self):
        errors = admission.argument_errors("/k", 0, -1, 0)
        self.assertEqual(
            errors,
            [
                "--runs: got 0, expected an integer >= 1",
                "--threads: got -1, expected an integer >= 1",
                "--tests: got 0, expected an integer >= 1",
            ],
        )

    def test_parse_args_exits_on_rejection(self):
        with self.assertRaises(SystemExit) as caught:
            admission.parse_args(["--kache", "relative", "--runs", "0"])
        self.assertNotEqual(caught.exception.code, 0)

    def test_scrub_env_removes_runner_and_nextest_variables(self):
        env = {
            "PATH": "/bin",
            "NEXTEST_TEST_THREADS": "4",
            "NEXTEST": "1",
            "KACHE_CARGO_PROXY_X": "1",
            "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER": "r",
            "CARGO_TARGET_DIR": "/t",
            "KACHE_CACHE_DIR": "/c",
        }
        self.assertEqual(
            admission.scrub_env(env), {"PATH": "/bin", "CARGO_TARGET_DIR": "/t", "KACHE_CACHE_DIR": "/c"}
        )

    def test_crate_sources(self):
        sources = admission.crate_sources(3)
        self.assertIn('name = "admission-probe"', sources["Cargo.toml"])
        self.assertIn('edition = "2024"', sources["Cargo.toml"])
        self.assertIn("[workspace]", sources["Cargo.toml"])
        self.assertEqual(sources["src/lib.rs"].count("#[test]"), 3)
        self.assertIn("fn t_2() {}", sources["src/lib.rs"])
        self.assertNotIn("fn t_3()", sources["src/lib.rs"])
        self.assertIn('path = "junit.xml"', sources[".config/nextest.toml"])

    def test_run_config_points_store_dir_into_the_extract_dir(self):
        config = admission.run_config(Path("/o"), 3)
        self.assertIn('[store]\ndir = "/o/run-3/target/nextest"\n', config)
        self.assertIn("[profile.ci.junit]", config)

    def test_run_script_shape(self):
        script = admission.run_script("0-3", Path("/o"), 1)
        self.assertTrue(script.startswith("taskset -c 0-3 cargo nextest run "))
        self.assertIn("--config-file /o/run-1/nextest.toml", script)
        self.assertIn(">/o/run-1.log 2>&1", script)
        self.assertIn("cut -d: -f3 /proc/self/cgroup", script)
        self.assertIn(">>/o/run-1.cgroup", script)
        self.assertTrue(script.endswith("exit $rc"))
        self.assertTrue(admission.run_script("", Path("/o"), 1).startswith("cargo nextest run "))


if __name__ == "__main__":
    unittest.main()
