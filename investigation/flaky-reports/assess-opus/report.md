# Assessment of Sol findings 2, 3, 4, 6 (assessor: opus)

Worktree `flaky-assess-opus` at `991c836`. Instrumentation was removed at the end: `git status --short` is empty and `git diff --exit-code` exits 0. Artifacts are under `/private/tmp/kache-flaky/assess-opus/`: `logs/`, `scripts/` (run wrapper, stress runner, latency probe), `measure.patch` (measurement-only instrumentation), and `bin/` (copies of the unmodified and measurement test binaries).

## Summary

All four mechanisms are correct as code readings. All four forced reproductions fail again when I re-run them. Each forcing only inserts a delay at a point where the OS can preempt the thread, so the kind of forcing is legitimate. What is not established is whether the delay gets that large without instrumentation. Every test passed in about 286 repetitions, including full-suite runs and runs at load average 117. The OS scheduling gaps I measured topped out at 97 ms. Findings 2–4 need a stall of 164–250 ms to fail, and finding 6 needs about 935 ms. The rules make the verdict UNSETTLED for all four, with low severity rather than Sol's medium.

## Finding 2: `scheduler::tests::permit_pool_blocks_until_a_slot_is_free` (`src/scheduler.rs:2335`)

- **Verdict:** UNSETTLED. The mechanism is confirmed, but no gap that large occurred without instrumentation.
- **Severity:** low (static risk).
- **Claim tested:** readiness (`lock-ready`, `src/scheduler.rs:2651`) does not guarantee the child still holds the permit when the parent starts its clock (`:2341`). If the parent is delayed past the child's 300 ms sleep (`:2652`), the lower bound `elapsed >= 50ms` (`:2349`) fails.
- **Evidence:**
  - Forced (Sol phase-2 patch, `KACHE_FLAKY_SCHEDULER=permit`, 1 thread, load `{ 29.41 43.16 45.70 }`): FAIL, matching R08: `panicked at src/scheduler.rs:2359:9: parent must have waited for the child-held slot`. The same patched binary passes with the flag absent (C234).
  - Measured headroom (`measure.patch` prints `started.elapsed()` after `acquire_permit`). Failing needs elapsed below 50 ms.

    | Run | Load | n | Elapsed min / median / max (ms) |
    |---|---|---|---|
    | M01, 8-way parallel | 32.7 | 85 | 296.1 / 311.2 / 326.0 |
    | M02, with 64 CPU burners | 117.5 | 24 | 297.1 / 312.4 / 323.5 |
    | A02, inside a full `cargo test --workspace` | 22.7 | 1 | 301.4 |

    So the parent would have to lose about 246 ms between the child writing `lock-ready` and line 2341.
  - Unforced: 0 failures in A01 (full suite), S01 (160 parallel runs of the unmodified binary), M01, M02 and A02.
  - Latency probe (1 ms sleep loop at default priority, running beside the tests): worst wakeup delay was 97.1 ms at load 117 with 64 burners, and under 50 ms during both full-suite runs (156,865 and 118,006 samples).
  - I cannot cite a `file:line` where a gap of 250 ms or more happens without instrumentation.
- **Where I differ:**
  - Severity: low, not medium. The machine could not produce the needed gap even at load 117 on 16 cores. macOS favours threads that wake from sleep over CPU-bound ones, which is why burners barely moved the margins.
  - Mechanism and fix shape: agreed.
  - Sol says the second assertion (`:2353`) is attributed separately. It is effectively implied by the first. `acquire_permit` starts its own clock a few microseconds after `started`, so it can only diverge at the 50 ms edge.

## Finding 3: `scheduler::tests::waiter_rechecks_after_owner_completes` (`src/scheduler.rs:2300`)

- **Verdict:** UNSETTLED. The mechanism is confirmed, but no gap that large occurred without instrumentation.
- **Severity:** low (static risk).
- **Claim tested:** the 200 ms sleep (`:2315`) gives no happens-before with the waiter's first `try_acquire` in `join_flight` (`:413-416`). A waiter that first tries after the fixture drops the lock (`:2568-2569`) becomes Owner, gets `Compile`, and fails `:2319`.
- **Evidence:**
  - Forced (Sol phase-2 patch, `KACHE_FLAKY_SCHEDULER=flight`, 1 thread, same load as finding 2): FAIL, matching R09: `panicked at src/scheduler.rs:2327:38: second process must wait for the in-flight owner`. The no-flag control passes.
  - Measured margin: the time by which the waiter thread entered `begin_miss` before `go` was written. Failing needs a margin below about −(0 to 10) ms. The extra 0–10 ms is the fixture's poll interval plus its artifact write.

    | Run | Load | n | Margin min / median / max (ms) |
    |---|---|---|---|
    | M01 | 32.7 | 91 | 200.3 / 209.1 / 222.5 |
    | M02 | 117.5 | 23 | 201.4 / 209.2 / 212.9 |
    | A02 | 22.7 | 1 | 220.3 |

    So the spawned waiter would have to be held off the CPU for about 200 ms longer than the main thread's sleep.
  - Unforced: 0 failures, same runs as finding 2.
- **Where I differ:**
  - Severity: low, not medium.
  - There is a second, narrower failure path with the same root cause. A waiter whose first attempt lands less than 1 ms before the release records less than 1 ms of wait. `flight_wait_ms` (`src/opcounts.rs:199`, whole milliseconds) might then not advance, and `:2328` fails, unless a concurrent test adds wait time.
  - Fix shape: agreed. The waiter should acknowledge its failed acquisition before `go` is written.

## Finding 4: `wrapper::tests::admit_scheduler_miss_recheck_returns_accepted_meta` (`src/wrapper/tests.rs:10603`)

- **Verdict:** UNSETTLED. The mechanism is confirmed, but no gap that large occurred without instrumentation.
- **Severity:** low (static risk).
- **Claim tested:** same race at the wrapper boundary. A waiter whose first `begin_miss` comes after the fixture drops its guard (`:10694`) gets `Compile` (`src/wrapper.rs:1150`) instead of `Recheck` (`:1145`). It then holds a non-empty guard and fails `:10630`.
- **Evidence:**
  - Forced (Sol phase-2 patch, `KACHE_FLAKY_WRAPPER=1`, 1 thread): FAIL, matching R12: `panicked at src/wrapper/tests.rs:10637:5: a Recheck hit must not keep the flight or permit`. The no-flag control passes.
  - Measured margin, taken after the waiter's `test_config` and `Store::open`:

    | Run | Load | n | Margin min / median / max (ms) | Waiter setup max (ms) |
    |---|---|---|---|---|
    | M01 | 32.7 | 93 | 163.7 / 205.7 / 226.0 | 21.4 |
    | M02 | 117.5 | 23 | 190.8 / 206.3 / 215.2 | 12.0 |
    | A02 | 22.7 | 1 | 188.2 | 18.2 |

    This is the smallest headroom of the four findings, because the waiter does store setup before it reaches the lock.
  - Unforced: 0 failures.
- **Where I differ:**
  - Severity: low, not medium.
  - Separate static risk, not Sol's mechanism and never observed: this file's `wait_flight_ready` gives the fixture only 5 s to become ready (`src/wrapper/tests.rs:10591`). The scheduler's equivalent was raised to 30 s, with the comment "on a loaded machine the spawn alone can take several seconds" (`src/scheduler.rs:1494-1499`). That is a different way this test, and `..._skips_rejected_meta`, could fail under load.

## Finding 6: `daemon::tests::test_wait_for_warming_blocks_then_signals` (`src/daemon/tests.rs:10544`)

- **Verdict:** UNSETTLED. The mechanism is confirmed, but no pause that long occurred without instrumentation.
- **Severity:** low (static risk).
- **Claim tested:** the test asserts `elapsed < 1s` (`:10560`). A pause of the test process of about 1 s inside the measured window fails it, even though `wait_for_warming` (`src/daemon.rs:3268`) works correctly.
- **Evidence:**
  - Forced (Sol phase-3 patch plus `suspend.py`, SIGSTOP for 1.2 s, 1 thread, load `{ 24.44 40.83 44.79 }`): FAIL, matching R20: `panicked at src/daemon/tests.rs:10563:5: assertion failed: elapsed < Duration::from_secs(1)`.
  - Measured `elapsed`:

    | Run | Load | n | Elapsed min / median / max (ms) |
    |---|---|---|---|
    | M01 | 32.7 | 96 | 51.2 / 53.4 / 66.2 |
    | M02 | 117.5 | 24 | 51.4 / 53.2 / 64.7 |
    | A02 | 22.7 | 1 | 51.2 |

    Failing needs about 935 ms more, roughly 10 times the worst scheduling gap I measured (97 ms).
  - A SIGSTOP does not happen in an unmodified run. It only stands in for a stall that I could not produce or observe.
  - The lower bound (`>= 30ms`) is robust. On the current-thread runtime the 50 ms sleep starts only after the waiter yields. Sol was right to reject R10 for this reason.
- **Where I differ:**
  - Severity: low, not medium.
  - Fix shape: agreed. One caution: with `start_paused` or virtual time, `std::time::Instant` no longer measures the wait. The lower-bound check would have to use `tokio::time::Instant`, or be dropped.

## Next probe that would settle findings 2, 3, 4 and 6

Apply `/private/tmp/kache-flaky/assess-opus/measure.patch`, which only prints margins after the measured operation, on the CI macOS runner and the Linux coverage job across many runs. Per `.github/workflows/ci.yml:811`, the self-hosted Mac "is one persistent host shared by several runners". Any margin below 0, or any warming `elapsed` of 1000 ms or more, is an unforced failure. Locally, the equivalent is the same patch under `memory_pressure -l critical` on an otherwise idle machine. I did not run that here, because it would degrade the other assessor's and other users' jobs.

## Run table

Reps counts repetitions of each target test. Per-test totals: findings 2–4 about 286, finding 6 about 285, all under 300.

| ID | Command | Threads | Load at start | Result |
|---|---|---|---|---|
| A01 | `./scripts/with-test-resources.sh cargo test --workspace` (unmodified), with latency probe | 16 (default) | `{ 15.27 31.65 48.58 }` | PASS, 5960 passed / 0 failed. Probe: 0 gaps of 50 ms or more in 156,865 samples |
| S01 | unmodified test binary, `--exact` the 4 tests, 8 workers × 20 iterations | 4 per process | `{ 16.49 27.01 44.79 }` | 0/160 failures per test |
| (smoke) | unmodified binary, 4 tests, once | 4 | ~16 | PASS |
| B01 | `cargo test --workspace --no-run` with `measure.patch` | – | `{ 13.78 22.30 40.12 }` | build ok. An earlier attempt overlapped A01, so I killed it, along with the rustc processes it had spawned. A01's binaries were not replaced |
| M01 | measurement binary, `--nocapture`, 8 × 12 | 4 | `{ 32.74 25.19 39.92 }` | 0/96 failures. Margins as above |
| L02 | latency probe, 75 s, under 64 `yes` burners I started and then killed | – | rose to `{ 117.49 55.12 49.66 }` | worst gap 97.1 ms; 1 gap of 50 ms or more; none of 100 ms or more (48,311 samples) |
| M02 | measurement binary, 8 × 3, with the same burners running | 4 | `{ 117.49 55.12 49.66 }` | 0/24 failures. Margins as above |
| B02 | build with Sol `instrumentation.patch` (phase 2) | – | `{ 54.94 49.25 47.88 }` | ok |
| F02 | `env KACHE_FLAKY_SCHEDULER=permit … cargo test -p kache --bin kache permit_pool_blocks_until_a_slot_is_free -- --test-threads=1 --nocapture` | 1 | `{ 29.41 43.16 45.70 }` | FAIL (forced) at `src/scheduler.rs:2359:9` |
| F03 | `env KACHE_FLAKY_SCHEDULER=flight … waiter_rechecks_after_owner_completes …` | 1 | same | FAIL (forced) at `src/scheduler.rs:2327:38` |
| F04 | `env KACHE_FLAKY_WRAPPER=1 … admit_scheduler_miss_recheck_returns_accepted_meta …` | 1 | same | FAIL (forced) at `src/wrapper/tests.rs:10637:5` |
| C234 | same patched binary, flags absent, the 3 tests `--exact` | 1 | same | PASS |
| B03 + F06 | build with phase-3 patch; `python3 -I /private/tmp/kache-flaky/sol/suspend.py` | 1 | `{ 24.44 40.83 44.79 }` | FAIL (forced) at `src/daemon/tests.rs:10563:5` |
| A02 | `./scripts/with-test-resources.sh cargo test --workspace -- --show-output` with `measure.patch`, with latency probe | 16 | `{ 22.73 39.65 44.30 }` | PASS, 5958 passed / 0 failed. Probe: 0 gaps of 50 ms or more in 118,006 samples |

Two of the four allowed full-workspace runs were used.

## What I checked and found correct in Sol's analysis

- **Line citations.** I checked these against HEAD, and they match:
  - `src/scheduler.rs`: 2315, 2341, 2349, 2353, 2568, 2569. 2651 is the `lock-ready` write; the 300 ms sleep is 2652.
  - `src/wrapper.rs`: 1123, 1145, 1150.
  - `src/wrapper/tests.rs`: 10614, 10627, 10628, 10694.
  - `src/daemon/tests.rs`: 10551, 10556, 10560.
  - `src/daemon.rs`: 3268.
- **`join_flight` behaviour.** It returns `Owner` immediately when its first `try_acquire` succeeds (`src/scheduler.rs:413-416`). Only a failed first attempt followed by a successful wait yields `Waited`, which becomes `Recheck`. This is the premise of findings 3 and 4.
- **Permit hold time.** The fixture holds the permit until its function returns, after the 300 ms sleep. The parent's 5 s timeout makes an upper-bound failure in finding 2 implausible.
- **Phase-2 forcings.** Each only delays a thread (`child.wait()` before the measurement, or a channel gate before the waiter's call). Neither changes any scheduler operation. All three reproduce exactly, and the patched binary passes without the flags.
- **Phase-3 forcing.** It only prints a PID; the stall is external. Sol was right to reject R10's added await, which changes the order of the current-thread runtime.
- **Global counters.** `opcounts` counters only grow, so concurrent tests cannot make the `>=` counter assertions fail.
- **Fixture isolation.** Each test uses its own temporary directory. No sibling test shares these flight or permit locks, and wrapper `test_config` (`src/test_support.rs:166`) reads no process environment, so environment races are not an alternative cause.
- **Unforced counts.** Sol reported 0 unforced failures in 10 full runs for each of these findings. That matches my 0 in about 286 repetitions.
