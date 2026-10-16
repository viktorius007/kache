Seven tests have demonstrated dependencies on scheduling, the live process environment, or process-wide initialization. Two findings assert elapsed clock bounds, two use sleeps as synchronization, two depend on shared process state, and one assumes an optional external probe meets a deadline. The known cache-key failure is a shared-process-state race. The owner's clock hypothesis explains some findings, but does not explain all of them.

Investigation: detached `991c83694c056119d8eba8f9c1f376ac246efb52`, macOS arm64, one investigator, no subagents. No fixes, commits, pushes, PRs, issues, or mutation runs. Final `git diff --exit-code` and `git status --short` were clean. Temporary source instrumentation was restored; its complete diffs are included below. The report is saved at [report.md](/private/tmp/kache-flaky/sol/report.md); test logs and the run ledger are in the same directory. Test execution ran from 01:36:48 to 02:28:20 UTC on 2026-10-14, stopping at ten full-workspace commands.

All cargo invocations inherited `CARGO_TARGET_DIR=/private/tmp/kache-flaky/sol/target`. The normal libtest default was 16 threads on this machine; explicit thread counts are recorded per run. The shell's soft nofile limit was 1,048,576, above the wrapper's 4,096 requirement. Load entries are the verbatim output of `sysctl -n vm.loadavg` immediately before each invocation, giving the 1-, 5-, and 15-minute averages; they are not measurements throughout the run.

For compact reproduction commands and the run table, `W` expands to `./scripts/with-test-resources.sh cargo test --workspace`, and `K` expands to `./scripts/with-test-resources.sh cargo test -p kache --bin kache`. Execute these from the worktree with the target directory exported. Commands requiring instrumentation use the corresponding patch below.

**1. Proven: `compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes`, [src/compiler/cc/tests.rs:250](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/compiler/cc/tests.rs:250). Class: shared process state, environment and current directory. Severity: high.**

The test computes the baseline at line 285 and compares cold and warm keys at lines 295 and 299 without taking the process-state lock. Every key reads ambient state again: `src/compiler/cc.rs:4389` builds its prefix-map identity from cwd, `KACHE_CC_PATH_NORMALIZE`, `KACHE_BASE_DIR`, `SDKROOT`, and `OUT_DIR`; line 4432 recomputes maps. A nonempty SDK contributes `/kache/sdkroot` at line 4628. Key generation hashes the distinct prefix-map sentinels at line 6933 and mapped source paths at line 7108. Changing normalization changes both of those inputs. The fake compiler at `tests/fixtures/mock_cc_diagnostics.sh:3` returns constant version/preprocessor output and echoes the already filtered probe arguments; it contains no clock-dependent output.

Sibling writers are concrete: `src/compiler/cc/tests.rs:6985` sets SDKROOT and line 6990 removes it; the environment/normalization test at line 7962 changes cwd, OUT_DIR, SDKROOT, and the normalization switch at lines 7983, 7996, and 8009. The shared lock at `src/test_support.rs:83` coordinates participating tests only. `set_env_for_test`, `src/config/tests.rs:114`, changes the same process environment; OUT_DIR writers include `src/cache_key/tests.rs:5170`. The known test does not participate in that lock. Cwd changes also alter the root topology used at `src/compiler/cc.rs:5005` and 5077. That cwd participation is established by source inspection; an independent cwd-only failure was not forced.

The owner supplied one earlier full `just check` failure at line 295 and 3/3 isolated passes; those prior observations are not counted in this run ledger. The uninstrumented full suite reproduced a warm-key hash mismatch in R01 at 16 threads, load `{ 48.32 45.66 35.56 }`. A controlled SDKROOT removal between the baseline and first comparison failed in R05, and disabling normalization there failed in R07, both at one thread. No fake-compiler script, flag classifier, C fixture content, or production key algorithm was changed. The baseline and comparison therefore genuinely used different ambient inputs. Relocating SDKROOT between two nonempty paths passed in R03, consistent with the SDK sentinel; the OUT_DIR-only probe passed in R06 and is not counted as proof of an OUT_DIR cause.

Reproduce on demand: `env KACHE_FLAKY_PROBE=SDKROOT ./scripts/with-test-resources.sh cargo test -p kache --bin kache terminal_formatting_shares_cc_keys_with_cold_and_warm_probes -- --test-threads=1 --nocapture` with phase-2 instrumentation and a nonempty initial SDKROOT; or substitute `KACHE_FLAKY_PROBE=NORMALIZE`. R04 and R13 were passing isolated controls. Natural and forced failure counts, with all later suite observations, are tabulated below.

The owner's historical pair of hashes cannot uniquely identify the writer or variable that changed; that run did not capture its key inputs. The proven explanation is that the test compares computations across mutable process state. SDKROOT removal and the normalization toggle are demonstrated sufficient causes, and a natural suite failure was reproduced. Attributing that particular historical event to one named sibling would require a trace of its inputs and writers.

Fix shape: hold the existing process-state lock for the entire comparison and establish explicit environment/cwd fixtures, or pass one environment/cwd snapshot through every computation. The assertion should vary diagnostic flags while keeping every other key input fixed.

```text
thread 'compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes' (147591341) panicked at src/compiler/cc/tests.rs:299:9:
assertion `left == right` failed
  left: "ec170f0d4c633cc97b1a38b9c75e0ee2cbe2781647e22b1dca0817e436d3899a"
 right: "355fcb4eb4dd4d15b6685a4aa7ce399183bafee49d3f966b870d84418b96317f"
```

Controlled SDKROOT removal (instrumentation shifts the original assertion line):

```text
thread 'compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes' (147823926) panicked at src/compiler/cc/tests.rs:310:9:
assertion `left == right` failed
  left: "e7001bca5ac575b023348b437ad4bb940ff5f1453e45a142b1acf130499f57e2"
 right: "aef934ce006e80408cc673d337f2ce4c1770aab489a627f488375a0d68867490"
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

Controlled normalization toggle:

```text
thread 'compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes' (147862497) panicked at src/compiler/cc/tests.rs:310:9:
assertion `left == right` failed
  left: "5e168a078b4edc8759c2ceb8d93c8869dbfa3209d2e3d243443a5a9078eaff10"
 right: "051c05cae3d0db87e5af9d4906160ecc80d29b1dcac45475841171e8d1907c21"
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**2. Proven: `scheduler::tests::permit_pool_blocks_until_a_slot_is_free`, [src/scheduler.rs:2335](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/scheduler.rs:2335). Class: scheduling-dependent clock assertion. Severity: medium.**

The child writes `lock-ready` and sleeps for 300 ms before exiting, `src/scheduler.rs:2651`. The parent observes readiness, then starts its measurement at line 2341. It asserts at least 50 ms elapsed at line 2349 and at least 50 ms added to the global wait counter at line 2353. Readiness establishes that the child held the permit when it wrote the file; it does not establish that the child still holds it when the parent is scheduled to acquire.

R08 forced the parent to resume after the child exited by waiting for that same child after readiness and before the original measurement. The permit was successfully acquired, but the original lower-bound assertion failed. This inserts no work into the measured operation and changes no scheduler behavior. It is the legal schedule where the parent loses its CPU slice long enough for the 300 ms holder to finish. Reproduce: `env KACHE_FLAKY_SCHEDULER=permit ./scripts/with-test-resources.sh cargo test -p kache --bin kache permit_pool_blocks_until_a_slot_is_free -- --test-threads=1 --nocapture`. One forced failure in one invocation; R14 was a passing serial control within the scheduler suite. Load in the forced run: `{ 43.84 66.49 50.05 }`.

Fix shape: keep the child permit held until an explicit release handshake, establish a failed/nonblocking acquisition while it is held, then release it and assert acquisition succeeds. Verify wait attribution with an isolated counter or a deterministic clock rather than the remaining duration of the child's sleep.

```text
thread 'scheduler::tests::permit_pool_blocks_until_a_slot_is_free' (147862733) panicked at src/scheduler.rs:2359:9:
parent must have waited for the child-held slot
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**3. Proven: `scheduler::tests::waiter_rechecks_after_owner_completes`, [src/scheduler.rs:2300](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/scheduler.rs:2300). Class: nondeterministic thread scheduling and sleep used as synchronization. Severity: medium.**

The test spawns a waiter at line 2311, sleeps 200 ms at line 2315, and releases the child through `go` at line 2316. The fixture writes the artifact and drops its lock at lines 2568–2569. The test requires `BeginMiss::Recheck` at line 2317, assuming the waiter has already tried the held lock. `Scheduler::join_flight`, `src/scheduler.rs:413`, legitimately returns ownership immediately if its first acquisition finds the lock free; only a failed initial acquisition followed by a release produces `FlightJoin::Waited` and the recheck path.

R09 gated the waiter before its original `begin_miss`, released and joined the existing child, and only then let the waiter execute. The original assertion failed with `Compile`, while the owner's artifact had already been written. The 200 ms sleep supplies no happens-before relationship with the waiter's first lock attempt. Reproduce: `env KACHE_FLAKY_SCHEDULER=flight ./scripts/with-test-resources.sh cargo test -p kache --bin kache waiter_rechecks_after_owner_completes -- --test-threads=1 --nocapture`. One forced failure in one invocation; R14 passed without the gate. Forced-run load: `{ 43.84 66.49 50.05 }`.

Fix shape: acknowledge the waiter's failed acquisition before allowing the owner to publish/release, then assert the subsequent recheck and artifact visibility. An explicit handshake must replace the assumption that a spawned thread ran within 200 ms.

```text
thread 'scheduler::tests::waiter_rechecks_after_owner_completes' (147863150) panicked at src/scheduler.rs:2327:38:
second process must wait for the in-flight owner
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**4. Proven: `wrapper::tests::admit_scheduler_miss_recheck_returns_accepted_meta`, [src/wrapper/tests.rs:10603](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/wrapper/tests.rs:10603). Class: nondeterministic thread scheduling and sleep used as synchronization. Severity: medium.**

This has the same schedule dependency at a distinct wrapper boundary. It spawns its waiter at line 10614, sleeps 200 ms at line 10627, releases the fixture at line 10628, then requires an empty guard and a cache hit at lines 10630–10635. The child drops its scheduler guard at line 10694. `admit_scheduler_miss`, `src/wrapper.rs:1123`, consults the cached metadata only on `BeginMiss::Recheck` at line 1145; an immediately acquired flight returns `(guard, None)` at line 1150.

R12 held the waiter before the original wrapper call, released and joined the existing owner, then admitted the waiter. It returned the compile guard, failing the original assertion. Reproduce: `env KACHE_FLAKY_WRAPPER=1 ./scripts/with-test-resources.sh cargo test -p kache --bin kache admit_scheduler_miss_recheck_returns_accepted_meta -- --test-threads=1 --nocapture`. One forced failure in one invocation; R17 passed without the gate. Forced-run load: `{ 43.84 66.49 50.05 }`.

Fix shape: prove the waiter encountered the held flight before permitting release. Then assert the accepted metadata and released guard at the wrapper boundary, using the owner/waiter handshake rather than elapsed sleep.

```text
thread 'wrapper::tests::admit_scheduler_miss_recheck_returns_accepted_meta' (147863750) panicked at src/wrapper/tests.rs:10637:5:
a Recheck hit must not keep the flight or permit
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**5. Proven: `cli::tests::test_is_macos_protected`, [src/cli/tests.rs:2823](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/cli/tests.rs:2823). Class: shared process state and order-dependent global initialization. Severity: medium; macOS only.**

`is_macos_protected`, `src/cli.rs:6209`, caches its prefix list in a process-wide `OnceLock` at line 6212. Its first call uses `dirs::home_dir()` at line 6223. The test later obtains the current home at `src/cli/tests.rs:2847` and expects that home's Desktop to be protected at line 2848. Those home values need not agree. Existing sibling code temporarily replaces HOME and XDG_CONFIG_HOME in `KunobiConfigGuard::new`, `src/test_support.rs:109`, and restores them on drop at line 132. A lock cannot retroactively repair a OnceLock initialized under a temporary home by an uncoordinated reader.

R11 initialized the existing prefix cache with a temporary HOME, restored HOME through the existing guard, and ran the original assertions. The Desktop assertion failed. No cache implementation was modified. Reproduce in a fresh process: `env KACHE_FLAKY_HOME=1 ./scripts/with-test-resources.sh cargo test -p kache --bin kache test_is_macos_protected -- --test-threads=1 --nocapture`. One forced failure in one invocation; R16 passed in a fresh process without that initialization. Forced-run load: `{ 43.84 66.49 50.05 }`.

Fix shape: test the classification core with explicit home/prefix inputs; test process-wide initialization in isolated subprocesses with a deliberately fixed HOME. Comparing a cache initialized by an earlier caller against the current ambient HOME leaves run order in the oracle.

```text
thread 'cli::tests::test_is_macos_protected' (147863622) panicked at src/cli/tests.rs:2853:9:
assertion failed: is_macos_protected(&home.join("Desktop"))
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**6. Proven: `daemon::tests::test_wait_for_warming_blocks_then_signals`, [src/daemon/tests.rs:10544](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/daemon/tests.rs:10544). Class: wall-clock upper-bound assertion under descheduling. Severity: medium.**

The signal task sleeps 50 ms at line 10551. The waiter has a five-second grace at line 10556, but the test also requires elapsed time below one second at line 10560. `wait_for_warming`, `src/daemon.rs:3268`, returns the watch-channel completion state, or observes a change under the requested timeout. A CPU scheduling pause can consume the test's one-second allowance without breaking that mechanism or exhausting the five-second grace.

R20 emitted a PID marker immediately after the original timer started, then the external controller sent SIGSTOP only to that test process, waited 1.2 seconds, and sent SIGCONT. The existing warming-result assertion passed, and the existing `elapsed < 1s` assertion failed. Reproduce by applying phase-3 instrumentation and running `python3 /private/tmp/kache-flaky/sol/run.py R20-repro python3 /private/tmp/kache-flaky/sol/suspend.py`. The controller invokes `env KACHE_FLAKY_SUSPEND=1 ./scripts/with-test-resources.sh cargo test -p kache --bin kache test_wait_for_warming_blocks_then_signals -- --test-threads=1 --nocapture`. One valid forced failure in one invocation, load `{ 26.51 43.46 46.73 }`. R15 and the subsequent uninstrumented workspace runs provide controls.

R10's preliminary probe added an await before the timer and failed the lower bound. That is **not** counted as proof: the original default current-thread Tokio runtime has no yield between spawning the signal task and starting the timer. R20 preserves that original scheduling structure and proves the upper-bound problem by pausing the process externally.

Fix shape: establish a pending warming future, signal completion, and assert it resolves successfully. Exercise timeout behavior with virtual Tokio time or explicit clock input. The mechanism does not require a real-machine one-second speed assertion.

```text
thread 'daemon::tests::test_wait_for_warming_blocks_then_signals' (148857835) panicked at src/daemon/tests.rs:10563:5:
assertion failed: elapsed < Duration::from_secs(1)
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**7. Proven: `sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server`, [tests/fallback_recovery_test.rs:220](/Users/viktor/Developer/github/kache-investigations/flaky-sol/tests/fallback_recovery_test.rs:220). Class: external-tool deadline and a strict assertion on a best-effort probe. Severity: high; macOS only.**

The test proves its sandboxed listener accepts a TCP connection using a 30-second readiness budget at lines 276–284. It then requires the fallback to be bypassed, and `fixture.calls()` to be exactly `"direct\n"`, at line 320. The optional production preflight has an independent, much narrower budget: `src/fallback/macos.rs:38` starts `/usr/sbin/lsof`; line 57 starts a 200 ms deadline; lines 59–67 kill/reap an unfinished lsof and return `None`. `src/fallback/sandbox.rs:32` propagates that missing PID as an unknown policy. `src/fallback.rs:35` then takes its documented recovery path: try the fallback and, if it fails, compile directly. The test's listener-readiness condition does not ensure lsof completes within 200 ms.

R21 naturally failed the original call-sequence assertion in a 16-thread full run, load `{ 79.93 70.06 57.80 }`. R19 at one thread and R22 at 32 threads passed this target, so failure is not a monotonic function of thread count. R27 stopped only the lsof child that kache had just spawned, leaving the test's ready listener and all policy/timeout logic intact. The log records a successful SIGSTOP, expiry of the 200 ms deadline, and the same original assertion failure: `"fallback\ndirect\n"` instead of `"direct\n"`. This is one on-demand failure in one invocation at one thread, load `{ 19.34 54.36 58.75 }`. The natural R21 failure had no branch trace, so the precise reason its optional probe returned unknown cannot be retroactively identified; the deadline mechanism is independently proved sufficient.

Reproduce with phase-4 instrumentation: `env KACHE_FLAKY_LSOF=1 ./scripts/with-test-resources.sh cargo test -p kache --test fallback_recovery_test sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server -- --test-threads=1 --nocapture`. R28 was the control with that flag absent and also failed the call-sequence assertion (load `{ 23.00 47.22 55.58 }`). R29 added branch/elapsed logging with no process stop and failed again, load `{ 43.10 47.66 55.15 }`. It directly recorded the production deadline expiring at **202.175542 ms with lsof unfinished**, proving this cause in an ordinary, unpaused process. Its output appears below.

Fix shape: test policy-based bypass with the deterministic Probe already used in `src/fallback/sandbox.rs`; test native policy against a known ready child PID separately. The full integration test should accept the documented fail-open recovery outcome when optional PID discovery times out, while still checking successful direct compilation and the structured attempt outcome. Listener readiness should not stand in for guaranteed completion of lsof.

Natural failure:

```text
thread 'sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server' (149068254) panicked at tests/fallback_recovery_test.rs:320:5:
assertion `left == right` failed: fallback compiler error
kache: warning: fallback `/tmp/kache-flaky/sol/t/.tmp3GURz3/sccache`: exit status: 42; compiling directly without fallback

  left: "fallback\ndirect\n"
 right: "direct\n"
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

Controlled lsof deadline failure:

```text
thread 'sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server' (149523426) panicked at tests/fallback_recovery_test.rs:320:5:
assertion `left == right` failed: FLAKY_LSOF paused owned child 5634: 0
FLAKY_LSOF 200ms deadline expired with owned child unfinished
fallback compiler error
kache: warning: fallback `/tmp/kache-flaky/sol/t/.tmpuagyvW/sccache`: exit status: 42; compiling directly without fallback

  left: "fallback\ndirect\n"
 right: "direct\n"
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

Unpaused run with branch logging:

```text
thread 'sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server' (149734474) panicked at tests/fallback_recovery_test.rs:320:5:
assertion `left == right` failed: FLAKY_LSOF 200ms deadline expired with owned child unfinished, elapsed=202.175542ms
fallback compiler error
kache: warning: fallback `/tmp/kache-flaky/sol/t/.tmprze9fL/sccache`: exit status: 42; compiling directly without fallback

  left: "fallback\ndirect\n"
 right: "direct\n"
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**Static risks not promoted to proven findings.**

The additional mechanisms below remain suspected. Except for F7, which already has a distinct proven cause, these tests did not fail in the uninstrumented valid-path runs. Severity is low for these static risks; failure output is therefore absent. A successful run does not prove these sites cannot flake. Their observations used the full commands, thread counts, and loads in the run ledger; no special repetitions were performed. Counts below are failures over full commands that reached the named test, including the identified setup runs.

| Test and original site | Full-command failures/reached | Suspected mechanism/class | Fix shape and next discriminating probe |
|---|---|---|---|
| `daemon::tests::test_wait_for_warming_already_signaled`, `src/daemon/tests.rs:10511`; `test_prefetch_disabled_remote_releases_warming_barrier`, `:10524`; `test_wait_for_warming_timeout`, `:10564` | 0/10 each | 500 ms upper bounds at 10520, 10538, 10574 include OS descheduling. Clock/timing. | Assert watch state/timeout using controlled time. Pause only the owned test process inside each timed interval while preserving the original scheduling structure. |
| `daemon_publish::tests::handing_off_without_a_socket_declines_at_once`, `src/daemon_publish.rs:1784` | 0/10 | A correct declined-socket result can still take more than its 100 ms elapsed allowance at 1804. Clock/timing. | Assert the declined reason and absence of a retry; suspend its own process after the timer starts to settle the risk. |
| `events::tests::choosing_what_to_keep_stays_linear_in_the_log`, `src/events.rs:2672` | 0/10 | Two-second performance assertion at 2682 depends on scheduler/CPU speed, not just complexity. Clock/timing. | Pin work/operation growth; run controlled descheduling within the timed operation to distinguish algorithm correctness from wall time. |
| `tui::tests::background_work_is_due_only_when_unpaused_idle_and_on_schedule`, `src/tui/tests.rs:1777` | 0/10 | Fresh `Instant::now()` samples at 1794 and 1803 are followed by negative due assertions; deadlines are 2 and 10 seconds (`src/tui.rs:730`). Clock/timing. | Pass a fixed `now`; pause between the fresh sample and assertion beyond its interval. |
| `tree_stamp::tests::a_stamp_settles_one_window_after_its_newest_write`, `src/tree_stamp.rs:517` | 0/10 | The real-file branch expects the freshly walked stamp still unsettled at live `now`, 538. The window is two seconds at line 24. Clock/timing. | Assert against the observed newest timestamp and a supplied time; pause after the walk beyond the window. |
| `scheduler::pressure::tests::a_forced_answer_replaces_the_machine_until_cleared`, `src/scheduler/pressure.rs:175` | 0/10 | Reads live kernel pressure once at 178 and expects the same live result after clearing the pin at 184; pressure may change meanwhile. Shared host resource state. | Supply the pressure reader or assert pin behavior independently of two live readings. A controlled reader transition would settle it; kernel state was not altered. |
| `store::tests::eviction_pauses_between_write_slices`, `crates/kache-store/src/store/tests.rs:12167` | 0/2 | Requires 500 removals to consume at least a 5 ms slice at 12187; a sufficiently fast fixture may not do so. Timing/fixture throughput. | Drive slice expiry with controlled clock/work state and assert the pause boundary; no fast-host failure was observed. |
| F7's additional port handoff, `tests/fallback_recovery_test.rs:259–271` | No isolated port-collision failure | The ephemeral reservation is dropped before the C listener binds; a different process could take that port, and TCP connect alone would accept it as readiness. Shared port/TOCTOU; never observed. | Have the child bind port zero and report its owned port, or transfer the reserved listener. A competing listener deliberately bound in that gap would settle this separate risk. |

**Static sweep and stable checks.**

The source sweep checked explicit clock samples (`Instant`, `SystemTime`, `Utc`, `Local`, `stamp_clock_ns`), sleeps, elapsed/deadline/timeout calls, and direct process-global environment/cwd/signal mutations in test files, annotated test scopes, and test-support code under `src/`, `crates/`, and `tests/`. This is a source inventory, not a claim that every listed call is a bug. Clock sampling used only to stamp fixture events or pass an explicit time is common. Many sleeps are bounded retry/poll helpers, fixture lifetimes, or intentional test input. Many timeouts are watchdogs around a separately asserted mechanism.

Graph navigation used `search_graph`, `trace_path`, and `get_code_snippet`. Coverage checks were made for relied-on files. The index reported partial Rust semantics (binding oracle, expanded calls, and impl relationships unavailable); direct source reads and literal searches supplement those links. During instrumentation, changed-source files were read directly and their diffs preserved. No exhaustive absence claim rests on a graph edge being absent.

The table below gives every matched source site compactly as file plus original line numbers, split into clock/sleep/timeout sites and direct mutation sites. Together each column denotes `file:line` for every listed line. `set_env_for_test` and its matching restore implementation at `src/config/tests.rs:98–123` are excluded from the direct-mutation inventory as requested. Other environment guards and their restore writes remain included. 'No' means no valid-path, uninstrumented failure observed for those direct sites; the seven indirect/forced mechanisms are documented above. Ignored or platform-excluded code is not treated as executed proof. Tests may also return early when a toolchain is unavailable; native Linux, Windows, CUDA, and live cloud dependencies were not forced into availability.

| File | Clock, sleep, elapsed, timeout lines | Direct process-mutation lines | Observed direct-site timing/state failure |
|---|---|---|---|
| `crates/kache-e2e/src/bench_runner/tests.rs` | 227, 3151 | — | No |
| `crates/kache-e2e/src/daemon.rs` | 141, 142, 143, 158, 159, 160, 190, 191, 192, 197 | — | No |
| `crates/kache-e2e/src/scenario_runner.rs` | — | 276, 279, 284, 285 | No |
| `crates/kache-service/src/auth.rs` | 234 | — | No |
| `crates/kache-service/src/lib.rs` | 623, 673, 718, 731, 743, 762, 769, 778, 786, 799 | — | No |
| `crates/kache-service/tests/cli.rs` | 15, 21, 26 | — | No |
| `crates/kache-store/src/atomic.rs` | 605 | — | No |
| `crates/kache-store/src/file_hash.rs` | 1076, 1094, 1113, 1114, 1116, 1118, 1120, 1139 | — | No |
| `crates/kache-store/src/markers.rs` | 424, 451 | — | No |
| `crates/kache-store/src/store.rs` | 6307 | — | No |
| `crates/kache-store/src/store/tests.rs` | 3504, 3522, 3523, 3524, 5231, 5232, 5237, 5265, 6665, 6671, 6720, 6727, 7449, 7456, 7461, 7516, 8358, 8360, 8362, 8379, 8381, 8383, 9673, 9985, 10111, 10134, 10148, 10288, 12146, 12148, 12180, 12182, 12228, 12230 | 2166, 2172, 2180, 2181 | No |
| `crates/kache-store/src/test_support.rs` | — | 30, 65 | No |
| `src/blob_heal.rs` | 595, 828, 834 | — | No |
| `src/build_intent.rs` | 590, 673, 683, 696, 702, 704, 717, 852 | — | No |
| `src/build_script.rs` | 2314, 2350, 2385, 2452, 3033, 3059, 3294, 3330, 3410, 3455, 3505, 3600, 3633, 3647, 3652, 3727, 3735, 3777, 3817, 3895, 4015, 4039, 4066, 4102, 4134, 4157, 4194, 4319, 4353, 4391, 4595, 4596, 4604, 4726, 4728 | 2102, 2114, 2126, 2160, 2161, 2162, 2163, 2164, 2168, 2169, 2170, 2173, 2174, 2318, 2329, 2330, 2366, 2405, 2406, 2440, 2464, 2465, 2481, 2493, 2494, 2503, 2512, 2515, 2694, 2695, 2696, 2697, 2701, 2702, 2803, 2804, 2805, 2806, 2810, 2811, 2812, 3131, 3150, 3267, 3269, 3345, 3354, 3359, 3512, 3531, 3533, 3547, 3550, 3552, 3554, 3562, 3567, 3568, 3572, 3573, 3603, 3605, 4327, 4329, 4366, 4370, 4372, 4584, 4633, 4644, 4676, 4688, 4689, 4699, 4700, 4786, 4789, 4790 | No |
| `src/build_script/hermetic.rs` | 863, 1298, 1315, 1353, 1369 | — | No |
| `src/build_script/inputs.rs` | 738, 744, 746 | — | No |
| `src/build_script_inputs/tests.rs` | 873, 1155 | — | No |
| `src/cache_key/tests.rs` | 12167, 12225, 12365, 12543, 12683, 12714, 12769, 12814, 12876, 12941, 12988, 13025, 13037, 13065, 13113, 13159, 13237, 13249, 13270, 13275, 13308, 13323 | 1146, 1153, 1163, 1164, 1567, 1573, 1757, 1763, 1764, 3485, 3600, 3642, 4157, 5163, 5433, 5434, 5465, 5473, 5478, 6053, 6058, 6059, 14763, 14764, 14794, 14795, 14797, 14801, 14803, 14806, 14860, 14861, 14863, 14867, 14869, 14922, 14924, 14927, 15088, 15096, 15152, 15153, 15161, 15162, 15220, 15228, 16040, 16041, 16079, 16080, 16155, 16177 | No |
| `src/cargo_proxy.rs` | 1096 | — | No |
| `src/cli/login.rs` | — | 369, 370, 387, 388 | No |
| `src/cli/tests.rs` | 979, 1670, 1672, 2163, 3415, 3468, 4152, 4158, 5208, 5618, 7753 | — | No; indirect F5 described above |
| `src/compile.rs` | 841, 848, 850, 872, 880 | — | No |
| `src/compiler/cc/tests.rs` | 5709, 7172 | 656, 661, 662, 671, 678, 679, 4476, 4482, 4494, 4496, 5804, 5808, 5813, 5814, 6964, 6966, 6968, 6985, 6990, 7704, 7934, 7948, 7951, 7981, 7982, 7983, 7984, 7996, 7999, 8008, 8009, 8040, 8041, 8066, 8090, 8091 | No; indirect F1 described above |
| `src/compiler/mod.rs` | — | 2763, 2810 | No |
| `src/compiler/nvcc.rs` | — | 1692, 1693, 1713, 1717, 1718, 1724, 1727, 1732, 1735, 2215, 2220, 2223, 2235, 2236, 2239, 2243, 2246, 2251, 2254 | No |
| `src/compiler/platform.rs` | 1024 | — | No |
| `src/compiler/rustdoc.rs` | 3355 | — | No |
| `src/config/tests.rs` | — | 225, 231, 240, 241, 1097, 1098, 1104, 2240, 2253, 2265, 2312, 2325, 2337, 2347, 2360, 2368, 2380, 2393, 2405, 2413, 2415, 2579, 2580, 2597, 2605, 2618, 2619, 2633, 2636, 2808, 2809, 2835, 2846, 2859, 2860, 2883, 2890, 2903, 2904, 2918, 3358, 3360, 3377, 3406, 3420, 3498, 3872, 3903, 3904, 3913, 4213, 4215, 4219, 4220, 4288, 4290, 4294, 4295, 4466, 4879, 4889, 4892, 5001, 5043 | No |
| `src/daemon.rs` | 4428, 4974, 8639 | — | No |
| `src/daemon/tests.rs` | 141, 182, 189, 192, 203, 460, 1009, 1110, 1118, 1127, 1133, 1153, 1159, 1225, 1246, 1270, 1284, 1292, 1766, 1800, 1849, 1855, 1922, 1927, 2720, 2941, 3682, 3687, 3689, 3690, 3934, 4035, 4163, 4508, 4947, 4954, 4993, 5001, 5587, 5713, 5795, 5806, 5809, 5834, 6070, 6265, 6818, 7414, 7650, 7835, 7913, 7923, 7929, 8010, 8014, 8037, 8040, 8092, 8206, 8294, 8402, 8414, 8478, 8482, 8750, 8771, 8776, 8783, 8849, 8981, 9001, 9056, 9209, 9278, 9332, 9396, 9402, 9450, 9457, 9651, 9662, 9834, 9897, 10134, 10149, 10518, 10520, 10535, 10538, 10551, 10555, 10557, 10570, 10572, 10588, 10811, 10824, 11080, 11082, 11124, 11143, 11146, 11433, 11484, 11543, 11620, 11632, 11662, 11780, 12246, 12248, 12259, 12296, 12312, 12325, 12460, 12515, 12533, 12573, 12610, 12697, 12721, 12761, 12853, 12881, 13001, 13051, 13128, 13264, 13540, 13658, 13683, 13697, 13700, 13726, 13729, 13733, 13766, 13795, 13800, 13804, 13829, 13830, 13834, 13845, 13875, 13879, 13885, 13905, 13909, 13913, 13946, 13949, 14191, 14246, 14255, 14374, 14394, 14442, 14454, 14484, 14486, 14490, 14517, 14720, 14773, 14820, 14830, 14896, 14898 | 131, 278, 287, 298, 299 | F6 forced upper bound; otherwise no |
| `src/daemon_control.rs` | 256, 278, 328, 353, 380, 414, 444, 452, 477 | — | No |
| `src/daemon_lifecycle.rs` | 525, 560, 572, 604, 621, 656, 694, 695, 696, 718, 723 | — | No |
| `src/daemon_publish.rs` | 899, 1126, 1216, 1234, 1235, 1324, 1330, 1440, 1460, 1463, 1718, 1722, 1724, 1801, 1804 | — | No |
| `src/events.rs` | 1721, 1890, 2232, 2495, 2501, 2679, 2682, 2684, 3017, 3028, 3051 | — | No |
| `src/extra_inputs.rs` | — | 2722, 2723, 2732 | No |
| `src/fallback/macos.rs` | 174, 185, 192 | — | No direct test-site failure; F7 production deadline above |
| `src/fallback_planner.rs` | — | 479, 480, 490, 491 | No |
| `src/heartbeat.rs` | 412, 421, 424 | — | No |
| `src/identity.rs` | — | 501, 502, 512, 513 | No |
| `src/incremental_policy.rs` | 2496, 2501 | — | No |
| `src/index_compact.rs` | 826, 840 | — | No |
| `src/main.rs` | 1882 | — | No |
| `src/maintenance.rs` | 47 | — | No |
| `src/native_link_key.rs` | — | 526, 556, 1926, 1943, 2163, 2194, 2196 | No |
| `src/opcounts.rs` | 286 | — | No |
| `src/phase_trace.rs` | 172 | — | No |
| `src/planner_auth.rs` | 403, 411, 571, 689, 811, 816, 830, 884 | 913, 927, 928 | No |
| `src/prestage.rs` | 656, 752, 784, 831, 871, 875, 896 | — | No |
| `src/probe/mod.rs` | 1384, 1455, 1586 | 1191, 1193, 1195, 1200, 1201, 1220, 1221, 1231 | No |
| `src/remote.rs` | 955, 1228 | — | No |
| `src/remote_backend.rs` | 1462, 1522, 1593, 1607, 1621, 2306, 2309, 2320 | 3020, 3028, 3029 | No |
| `src/remote_backend/oci/tests.rs` | 667, 1475, 1490 | — | No |
| `src/remote_layout.rs` | 882, 1638 | — | No |
| `src/remote_resilience.rs` | 104, 324, 352, 1121, 1311, 1479, 1555, 1581, 1600, 1819, 1852, 1927, 1975 | — | No |
| `src/report/tests.rs` | 18, 46, 47, 57, 59, 67, 74, 391, 405, 516, 1180, 1324, 1471, 1490, 1583, 1603, 1626, 1650, 2422 | — | No |
| `src/savings/tests.rs` | 202, 322 | — | No |
| `src/scheduler.rs` | 1499, 1500, 1505, 2315, 2341, 2349, 2477, 2544, 2564, 2565, 2566, 2652, 2868, 2873, 2909, 2911, 3107 | — | F2/F3 forced; no unforced failure |
| `src/scheduler/pressure.rs` | 252 | — | No |
| `src/service.rs` | 1490, 1496, 1503 | — | No |
| `src/target_cleanup.rs` | 1702, 1723, 2065 | — | No |
| `src/target_liveness.rs` | 1547 | — | No |
| `src/target_seed.rs` | 1017, 1358, 1793, 1794, 1818, 1832, 1881, 1891, 1910, 1956, 2147 | — | No |
| `src/target_use.rs` | 155, 158 | — | No |
| `src/test_support.rs` | 254, 294, 297, 298, 380, 402, 409 | 28, 39, 115, 137, 138, 320 | No |
| `src/tree_stamp.rs` | 538, 654 | — | No |
| `src/tui/tests.rs` | 194, 196, 359, 365, 371, 481, 498, 504, 512, 521, 525, 544, 777, 795, 811, 860, 866, 920, 977, 1380, 1393, 1430, 1627, 1732, 1779, 1780, 1794, 1803, 1916, 2039, 2052, 2068, 2120, 2129, 2150, 2160, 2169, 2179, 2205, 2241, 2347, 2352, 2360, 2361, 2396, 2450, 2485, 2518, 2632, 2668, 2692, 2706, 2719, 2798 | — | No |
| `src/unit_prune.rs` | 681, 734, 996, 1016, 1038, 1083, 1112, 1167, 1206, 1261, 1330, 1344 | — | No |
| `src/verify_compare.rs` | — | 486, 488, 490, 493, 494 | No |
| `src/worktree_discovery.rs` | 883, 901, 956, 991, 1007, 1012, 1019, 1065 | — | No |
| `src/wrapper/tests.rs` | 916, 1005, 1440, 1650, 1864, 1885, 5316, 5426, 5568, 6015, 6045, 6048, 6052, 6071, 6395, 6425, 6481, 6517, 7069, 7246, 7313, 7379, 7981, 7987, 8188, 9865, 10016, 10057, 10591, 10592, 10597, 10627, 10663, 10690, 10691, 10692, 10733, 10739, 10967 | 22, 30, 40, 41, 296, 366, 2698, 5699, 5703, 5707, 5711, 5715, 9758, 9776, 9777, 10320 | F4 forced; no unforced failure |
| `src/wrapper/tests/hit.rs` | 19, 101 | — | No |
| `src/wrapper/tests/rustc_hit.rs` | 93 | — | No |
| `tests/adaptive_incremental_test.rs` | 54, 64, 314, 318, 1000, 1010, 1020 | — | No |
| `tests/adaptive_incremental_workspace_test.rs` | 231, 640 | — | No |
| `tests/build_script_declared_inputs_test.rs` | 248 | — | No |
| `tests/cargo_proxy_test.rs` | 81, 87, 88, 162, 164, 170, 171 | — | No |
| `tests/cc_passthrough_args_test.rs` | 490 | — | No |
| `tests/cli_commands_test.rs` | 1787, 1871, 2504, 2509, 2518, 2630, 2640, 4069 | — | No |
| `tests/common/mod.rs` | 252, 256, 257, 293, 295, 301, 333, 336, 337 | — | No |
| `tests/fallback_recovery_test.rs` | 276, 281, 284 | — | No; indirect F7 described above |
| `tests/filesystem_remote_test.rs` | 191, 195, 206, 409, 415, 418, 457, 463, 473, 1053, 1197, 1200, 1203 | — | No |
| `tests/host_config_test.rs` | — | 39, 48, 49 | No |
| `tests/input_prediction_test.rs` | 509, 522, 530 | — | No |
| `tests/integration_test.rs` | 3313, 3314, 3319 | — | No |
| `tests/macos_adaptive_debug_info_test.rs` | 70 | — | No |
| `tests/nvcc_cuda_toolchain_test.rs` | 210, 409 | — | No |
| `tests/s3_remote_test.rs` | 302, 307, 316 | — | No |
| `tests/test_runner_test.rs` | 148, 153, 162, 199, 206, 210, 223, 245, 249, 255, 353, 355, 361, 362, 529, 537, 624, 666 | — | No |
| `tests/unknown_compiler_probe_test.rs` | 21, 31, 48, 58, 80, 90, 101, 102, 103 | — | No |
| `tests/worktree_depinfo_test.rs` | 180 | — | No |

Additional global-state sites: `src/cli.rs:6212` (home-derived OnceLock, proven above), `src/heartbeat.rs:57` (one-shot heartbeat context; installation at 72, test caller at 402), `src/opcounts.rs:122–127` (process start and additive counters), `src/scheduler/pressure.rs:33` (global enabled switch; test writes at 177, 242, 244), `src/phase_trace.rs:12` (thread-local recorder, not shared across libtest threads). The counters are cumulative, so lower-bound delta assertions can be stable but cannot prove exclusive attribution under concurrency. No independent counter/context failure was observed. These supplementary statics are not captured by a search limited to `set_var` and clock literals.

The shell regression fixture also sleeps at `tests/fixtures/cc_release_regressions.sh:28,45,49,75,85`. It is invoked through `tests/cc_release_regression_test.rs:32`; all four caller tests reported passing in the seven full commands that reached that target. No failure at those shell sleep sites was observed.

What checked stable: the valid-path serial run completed all enabled workspace targets, including 4,446 kache unit tests and 571 kache-store tests; the other valid-path runs are recorded below. Nonempty SDKROOT relocation was stable; isolated controls of the gated scheduler/wrapper/home tests passed. The rejected-meta wrapper test uses the same 200 ms sleep, but its final expected compile outcome also holds when the waiter starts late, so that sleep alone is not evidence it flakes. Download-waiter tests at `src/daemon/tests.rs:13708,13744,13861` combine notifications with map rechecks; no lost-wakeup failure was observed. The file-hash wall-clock observation test at `crates/kache-store/src/file_hash.rs:1137` brackets the observation with before/after samples rather than an elapsed speed requirement; it passed, though wall-clock adjustments were not induced. Phase tracing uses a thread-local recorder. Socket fixtures reviewed use unique temporary paths or ephemeral loopback ports, including `tests/fallback_recovery_test.rs:259` and `tests/s3_remote_test.rs:462`; no port collision, EMFILE, thread-exhaustion, or disk-exhaustion failure was observed. The resource wrapper remained in use; low-nofile exhaustion was not constructed.

**Run ledger, limitations, and stop rule.**

R01–R03 used `TMPDIR=/private/tmp/kache-flaky/sol/tmp`; R04–R18 used the worktree's `.flaky-tmp`; R19 onward use `/tmp/kache-flaky/sol/t`, whose resolved path is inside `/private/tmp/kache-flaky/sol/`. The scratch-path changes were necessary to honor the write fence while avoiding macOS protection and long socket names. R01/R02's two CLI target-discovery failures are deterministic: `src/cli.rs:6218` excludes `/private` and line 6265 returns before scanning. R18's 19 failures include `SUN_LEN` socket rejection and fixture paths accidentally inheriting the repository's workspace/toolchain roots; all disappeared in the serial run with the short outside-worktree alias. They are recorded as setup/path failures rather than timing/concurrency findings. No failure from those runs was silently converted into a timing finding.

R03/R04 were queued before earlier work finished; their isolated test processes overlapped briefly after build/package locks cleared. All subsequent test invocations were sequential. Loads also reflect the other investigator and unrelated jobs. No process not started by this investigation was stopped or killed; R20 paused/resumed its own test process; R27 paused its own lsof child, which the existing timeout killed and reaped.

10 full-workspace test commands were run (maximum 10). No single test approached 300 invocations. The investigation stopped test work at the full-run budget, before the three-hour wall limit. Counts below count each top-level invocation that actually reached the test; aborted targets do not contribute an invented pass. Full-command counts include the explicitly identified scratch-path setup runs. F1's R03/R06 negative discriminators and F6's invalid R10 probe are excluded from these categories. F7's controls include the diagnostic, unpaused R29 run.

| Finding | Unforced full commands: failures/reached | Valid forced probes: failures/runs | Other isolated controls: failures/runs |
|---|---|---|---|
| F1 | 1/10 | 2/2 | 0/2 |
| F2 | 0/10 | 1/1 | 0/1 |
| F3 | 0/10 | 1/1 | 0/1 |
| F4 | 0/10 | 1/1 | 0/1 |
| F5 | 0/10 | 1/1 | 0/1 |
| F6 | 0/10 | 1/1 | 0/1 |
| F7 | 5/7 | 1/1 | 2/2 |

| Run / log | Command | Test threads | Load average | Result |
|---|---|---:|---|---|
| [R01](/private/tmp/kache-flaky/sol/logs/R01.log) | `W` | 16 (default) | `{ 48.32 45.66 35.56 }` | FAIL (exit 101): cli::tests::targets_inside_worktree_containers_are_found, cli::tests::test_find_target_dirs_with_cargo_project, compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes; two `/private` discovery setup failures |
| [R02](/private/tmp/kache-flaky/sol/logs/R02.log) | `W -- --test-threads=1` | 1 | `{ 32.42 38.21 33.80 }` | FAIL (exit 101): cli::tests::targets_inside_worktree_containers_are_found, cli::tests::test_find_target_dirs_with_cargo_project; two `/private` discovery setup failures |
| [R03](/private/tmp/kache-flaky/sol/logs/R03.log) | `env KACHE_FLAKY_PROBE=1 K terminal_formatting_shares_cc_keys_with_cold_and_warm_probes -- --test-threads=1 --nocapture` | 1 | `{ 18.60 33.76 32.39 }` | PASS |
| [R04](/private/tmp/kache-flaky/sol/logs/R04.log) | `K terminal_formatting_shares_cc_keys_with_cold_and_warm_probes -- --test-threads=1 --nocapture` | 1 | `{ 15.13 31.72 31.69 }` | PASS |
| [R05](/private/tmp/kache-flaky/sol/logs/R05.log) | `env KACHE_FLAKY_PROBE=SDKROOT K terminal_formatting_shares_cc_keys_with_cold_and_warm_probes -- --test-threads=1 --nocapture` | 1 | `{ 71.50 43.72 36.12 }` | FAIL (exit 101): compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes |
| [R06](/private/tmp/kache-flaky/sol/logs/R06.log) | `env KACHE_FLAKY_PROBE=OUT_DIR K terminal_formatting_shares_cc_keys_with_cold_and_warm_probes -- --test-threads=1 --nocapture` | 1 | `{ 56.54 70.28 50.96 }` | PASS |
| [R07](/private/tmp/kache-flaky/sol/logs/R07.log) | `env KACHE_FLAKY_PROBE=NORMALIZE K terminal_formatting_shares_cc_keys_with_cold_and_warm_probes -- --test-threads=1 --nocapture` | 1 | `{ 43.84 66.49 50.05 }` | FAIL (exit 101): compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes |
| [R08](/private/tmp/kache-flaky/sol/logs/R08.log) | `env KACHE_FLAKY_SCHEDULER=permit K permit_pool_blocks_until_a_slot_is_free -- --test-threads=1 --nocapture` | 1 | `{ 43.84 66.49 50.05 }` | FAIL (exit 101): scheduler::tests::permit_pool_blocks_until_a_slot_is_free |
| [R09](/private/tmp/kache-flaky/sol/logs/R09.log) | `env KACHE_FLAKY_SCHEDULER=flight K waiter_rechecks_after_owner_completes -- --test-threads=1 --nocapture` | 1 | `{ 43.84 66.49 50.05 }` | FAIL (exit 101): scheduler::tests::waiter_rechecks_after_owner_completes |
| [R10](/private/tmp/kache-flaky/sol/logs/R10.log) | `env KACHE_FLAKY_WARMING=1 K test_wait_for_warming_blocks_then_signals -- --test-threads=1 --nocapture` | 1 | `{ 43.84 66.49 50.05 }` | FAIL (exit 101): daemon::tests::test_wait_for_warming_blocks_then_signals; rejected probe |
| [R11](/private/tmp/kache-flaky/sol/logs/R11.log) | `env KACHE_FLAKY_HOME=1 K test_is_macos_protected -- --test-threads=1 --nocapture` | 1 | `{ 43.84 66.49 50.05 }` | FAIL (exit 101): cli::tests::test_is_macos_protected |
| [R12](/private/tmp/kache-flaky/sol/logs/R12.log) | `env KACHE_FLAKY_WRAPPER=1 K admit_scheduler_miss_recheck_returns_accepted_meta -- --test-threads=1 --nocapture` | 1 | `{ 43.84 66.49 50.05 }` | FAIL (exit 101): wrapper::tests::admit_scheduler_miss_recheck_returns_accepted_meta |
| [R13](/private/tmp/kache-flaky/sol/logs/R13.log) | `K terminal_formatting_shares_cc_keys_with_cold_and_warm_probes -- --test-threads=1 --nocapture` | 1 | `{ 43.84 66.49 50.05 }` | PASS |
| [R14](/private/tmp/kache-flaky/sol/logs/R14.log) | `K scheduler::tests:: -- --test-threads=1 --nocapture` | 1 | `{ 43.84 66.49 50.05 }` | PASS |
| [R15](/private/tmp/kache-flaky/sol/logs/R15.log) | `K test_wait_for_warming -- --test-threads=1 --nocapture` | 1 | `{ 40.89 65.50 49.79 }` | PASS |
| [R16](/private/tmp/kache-flaky/sol/logs/R16.log) | `K test_is_macos_protected -- --test-threads=1 --nocapture` | 1 | `{ 40.89 65.50 49.79 }` | PASS |
| [R17](/private/tmp/kache-flaky/sol/logs/R17.log) | `K admit_scheduler_miss_recheck_returns_accepted_meta -- --test-threads=1 --nocapture` | 1 | `{ 40.89 65.50 49.79 }` | PASS |
| [R18](/private/tmp/kache-flaky/sol/logs/R18.log) | `W -- --test-threads=1` | 1 | `{ 25.62 57.38 47.68 }` | FAIL (exit 101): 19 scratch-path/setup failures; see log |
| [R19](/private/tmp/kache-flaky/sol/logs/R19.log) | `W -- --test-threads=1` | 1 | `{ 95.13 66.27 52.12 }` | PASS |
| [R20](/private/tmp/kache-flaky/sol/logs/R20.log) | `python3 /private/tmp/kache-flaky/sol/suspend.py` | 1 (inner) | `{ 26.51 43.46 46.73 }` | FAIL (exit 101): daemon::tests::test_wait_for_warming_blocks_then_signals |
| [R21](/private/tmp/kache-flaky/sol/logs/R21.log) | `W -- --test-threads=16` | 16 | `{ 79.93 70.06 57.80 }` | FAIL (exit 101): sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server |
| [R22](/private/tmp/kache-flaky/sol/logs/R22.log) | `W -- --test-threads=32` | 32 | `{ 103.88 84.02 65.78 }` | PASS |
| [R27](/private/tmp/kache-flaky/sol/logs/R27.log) | `env KACHE_FLAKY_LSOF=1 ./scripts/with-test-resources.sh cargo test -p kache --test fallback_recovery_test sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server -- --test-threads=1 --nocapture` | 1 | `{ 19.34 54.36 58.75 }` | FAIL (exit 101): sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server |
| [R28](/private/tmp/kache-flaky/sol/logs/R28.log) | `./scripts/with-test-resources.sh cargo test -p kache --test fallback_recovery_test sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server -- --test-threads=1 --nocapture` | 1 | `{ 23.00 47.22 55.58 }` | FAIL (exit 101): sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server |
| [R29](/private/tmp/kache-flaky/sol/logs/R29.log) | `env KACHE_FLAKY_LSOF_TRACE=1 ./scripts/with-test-resources.sh cargo test -p kache --test fallback_recovery_test sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server -- --test-threads=1 --nocapture` | 1 | `{ 43.10 47.66 55.15 }` | FAIL (exit 101): sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server |
| [R23](/private/tmp/kache-flaky/sol/logs/R23.log) | `W -- --test-threads=8` | 8 | `{ 27.57 41.15 51.63 }` | FAIL (exit 101): sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server |
| [R24](/private/tmp/kache-flaky/sol/logs/R24.log) | `W -- --test-threads=64` | 64 | `{ 18.68 31.15 45.49 }` | FAIL (exit 101): sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server |
| [R25](/private/tmp/kache-flaky/sol/logs/R25.log) | `W -- --test-threads=16` | 16 | `{ 36.47 48.54 51.11 }` | FAIL (exit 101): sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server |
| [R26](/private/tmp/kache-flaky/sol/logs/R26.log) | `W -- --test-threads=16` | 16 | `{ 19.08 34.49 44.49 }` | FAIL (exit 101): sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server |

Full logs are linked in the run table. The exact command arguments, start/end times, load, and cargo exit status are also in [runs.jsonl](/private/tmp/kache-flaky/sol/runs.jsonl). The wrapper script itself returns zero after recording a child failure, so the recorded cargo/child exit status—not the orchestration process's exit—is the result used here. R20's controller command has one test thread internally even though its outer ledger field says default.

**Temporary instrumentation diffs.**

Phase 1, R03: controlled SDKROOT relocation. This passed and is a negative discriminator for claiming that any SDK path change must change a key.

```diff
--- a/src/compiler/cc/tests.rs
+++ b/src/compiler/cc/tests.rs
@@ -283,6 +283,14 @@
     };
     let warm = dir.path().join("warm");
     let baseline = key(&[], &warm);
+    let _probe_env = if std::env::var_os("KACHE_FLAKY_PROBE").is_some() {
+        let sdk = dir.path().join("forced-sdk");
+        fs::create_dir(&sdk).unwrap();
+        eprintln!("FLAKY_PROBE baseline SDKROOT={:?}", std::env::var_os("SDKROOT"));
+        Some(crate::config::tests::set_env_for_test("SDKROOT", Some(sdk.as_os_str())))
+    } else {
+        None
+    };
     for (index, flag) in [
         "-fcolor-diagnostics",
         "-fno-color-diagnostics",
```

Phase 2, R05–R17: environment switches, owner/waiter gates, home-cache initialization, and the rejected preliminary warming probe. R06's OUT_DIR probe passed. The three-line warming await in this patch is the invalid R10 experiment, explicitly superseded by phase 3.

```diff
diff --git a/src/cli/tests.rs b/src/cli/tests.rs
index f59b11a..d5f789b 100644
--- a/src/cli/tests.rs
+++ b/src/cli/tests.rs
@@ -2821,6 +2821,11 @@ fn test_parse_cargo_lock_crate_names_from_valid_missing_and_bad_files() {
 
 #[test]
 fn test_is_macos_protected() {
+    if cfg!(target_os = "macos") && std::env::var_os("KACHE_FLAKY_HOME").is_some() {
+        let home = tempfile::tempdir().unwrap();
+        let _env = crate::config::tests::set_env_for_test("HOME", Some(home.path().as_os_str()));
+        assert!(is_macos_protected(&home.path().join("Desktop")));
+    }
     // On non-macOS the stub always returns false — verify that invariant
     // and skip the positive-match assertions.
     if !cfg!(target_os = "macos") {
diff --git a/src/compiler/cc/tests.rs b/src/compiler/cc/tests.rs
index 69eb031..e732c29 100644
--- a/src/compiler/cc/tests.rs
+++ b/src/compiler/cc/tests.rs
@@ -283,6 +283,21 @@ fn terminal_formatting_shares_cc_keys_with_cold_and_warm_probes() {
     };
     let warm = dir.path().join("warm");
     let baseline = key(&[], &warm);
+    let _probe_env = match std::env::var("KACHE_FLAKY_PROBE").ok().as_deref() {
+        Some("SDKROOT") => {
+            eprintln!("FLAKY_PROBE removing SDKROOT={:?}", std::env::var_os("SDKROOT"));
+            Some(crate::config::tests::set_env_for_test("SDKROOT", None))
+        }
+        Some("OUT_DIR") => {
+            let out = dir.path().join("target/debug/build/probe-1/out");
+            fs::create_dir_all(&out).unwrap();
+            Some(crate::config::tests::set_env_for_test("OUT_DIR", Some(out.as_os_str())))
+        }
+        Some("NORMALIZE") => Some(crate::config::tests::set_env_for_test(
+            "KACHE_CC_PATH_NORMALIZE", Some(std::ffi::OsStr::new("0")),
+        )),
+        _ => None,
+    };
     for (index, flag) in [
         "-fcolor-diagnostics",
         "-fno-color-diagnostics",
diff --git a/src/daemon/tests.rs b/src/daemon/tests.rs
index 61e2e50..7813594 100644
--- a/src/daemon/tests.rs
+++ b/src/daemon/tests.rs
@@ -10552,6 +10552,9 @@ async fn test_wait_for_warming_blocks_then_signals() {
         d.signal_warming_complete();
     });
 
+    if std::env::var_os("KACHE_FLAKY_WARMING").is_some() {
+        tokio::time::sleep(Duration::from_millis(100)).await;
+    }
     let start = std::time::Instant::now();
     assert!(daemon.wait_for_warming(Duration::from_secs(5)).await);
     let elapsed = start.elapsed();
diff --git a/src/scheduler.rs b/src/scheduler.rs
index 651d231..f206e31 100644
--- a/src/scheduler.rs
+++ b/src/scheduler.rs
@@ -2308,12 +2308,20 @@ mod tests {
         let identity = FlightIdentity::rustc("shared", &["lib".into()], true);
         let cache = dir.path().to_path_buf();
         let flight_wait_before = crate::opcounts::flight_wait_ms();
-        let waiter =
-            std::thread::spawn(move || begin_miss(&cache, true, &identity, "shared", false, None));
+        let (probe_tx, probe_rx) = std::sync::mpsc::channel();
+        let force = std::env::var("KACHE_FLAKY_SCHEDULER").ok().as_deref() == Some("flight");
+        let waiter = std::thread::spawn(move || {
+            if force { probe_rx.recv().unwrap(); }
+            begin_miss(&cache, true, &identity, "shared", false, None)
+        });
         // The child holds the flight until `go` exists. Give the waiter time
         // to block on that lock so it cannot become the owner by racing.
         std::thread::sleep(Duration::from_millis(200));
         fs::write(dir.path().join("go"), b"go").unwrap();
+        if force {
+            child.wait().unwrap();
+            probe_tx.send(()).unwrap();
+        }
         match waiter.join().unwrap() {
             BeginMiss::Recheck => {}
             BeginMiss::Compile(_) => panic!("second process must wait for the in-flight owner"),
@@ -2337,6 +2345,9 @@ mod tests {
         let mut child = spawn_fixture(dir.path(), "scheduler::tests::permit_owner_child_fixture");
         wait_ready(dir.path(), &mut child);
 
+        if std::env::var("KACHE_FLAKY_SCHEDULER").ok().as_deref() == Some("permit") {
+            child.wait().unwrap();
+        }
         let scheduler = test_scheduler(dir.path(), 1);
         let started = std::time::Instant::now();
         let permit_wait_before = crate::opcounts::permit_wait_ms();
diff --git a/src/wrapper/tests.rs b/src/wrapper/tests.rs
index 429276d..f61c480 100644
--- a/src/wrapper/tests.rs
+++ b/src/wrapper/tests.rs
@@ -10611,7 +10611,10 @@ fn admit_scheduler_miss_recheck_returns_accepted_meta() {
     wait_flight_ready(dir.path(), &mut child);
 
     let cache = dir.path().to_path_buf();
+    let (probe_tx, probe_rx) = std::sync::mpsc::channel();
+    let force = std::env::var_os("KACHE_FLAKY_WRAPPER").is_some();
     let waiter = std::thread::spawn(move || {
+        if force { probe_rx.recv().unwrap(); }
         let config = test_config(cache);
         let store = Store::open(&config).unwrap();
         admit_scheduler_miss(
@@ -10626,6 +10629,10 @@ fn admit_scheduler_miss_recheck_returns_accepted_meta() {
     });
     std::thread::sleep(std::time::Duration::from_millis(200));
     std::fs::write(dir.path().join("go"), b"go").unwrap();
+    if force {
+        child.wait().unwrap();
+        probe_tx.send(()).unwrap();
+    }
     let (guard, hit) = waiter.join().unwrap();
     assert!(
         guard.is_empty(),
```

Phase 3, R20: PID marker only; the controller performs the process pause outside the test. Its controller source is [suspend.py](/private/tmp/kache-flaky/sol/suspend.py). The phase-3 patch was removed before R21. The suite was paused between R22 and R23 for the new fallback probe; both fallback instrumentation phases were removed before resuming it.

```diff
diff --git a/src/daemon/tests.rs b/src/daemon/tests.rs
index 61e2e50..5ca2e3a 100644
--- a/src/daemon/tests.rs
+++ b/src/daemon/tests.rs
@@ -10553,6 +10553,9 @@ async fn test_wait_for_warming_blocks_then_signals() {
     });
 
     let start = std::time::Instant::now();
+    if std::env::var_os("KACHE_FLAKY_SUSPEND").is_some() {
+        eprintln!("FLAKY_SUSPEND_PID={}", std::process::id());
+    }
     assert!(daemon.wait_for_warming(Duration::from_secs(5)).await);
     let elapsed = start.elapsed();
     // Should have waited ~50ms, not the full 5s timeout
```

Phase 4, R27–R28: stop only the lsof child just spawned by this kache process, so the existing 200 ms timeout executes. The flag is absent in the control and all subsequent workspace runs.

```diff
diff --git a/src/fallback/macos.rs b/src/fallback/macos.rs
index a5dbee0..1d45196 100644
--- a/src/fallback/macos.rs
+++ b/src/fallback/macos.rs
@@ -54,12 +54,19 @@ fn server_pid(port: u16) -> Option<i32> {
         .stderr(Stdio::null())
         .spawn()
         .ok()?;
+    if std::env::var_os("KACHE_FLAKY_LSOF").is_some() {
+        let stopped = unsafe { libc::kill(child.id() as i32, libc::SIGSTOP) };
+        eprintln!("FLAKY_LSOF paused owned child {}: {stopped}", child.id());
+    }
     let deadline = Instant::now() + Duration::from_millis(200);
     let success = loop {
         match child.try_wait() {
             Ok(Some(status)) => break status.success(),
             Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(5)),
             _ => {
+                if std::env::var_os("KACHE_FLAKY_LSOF").is_some() {
+                    eprintln!("FLAKY_LSOF 200ms deadline expired with owned child unfinished");
+                }
                 let _ = child.kill();
                 let _ = child.wait();
                 return None;
```

Phase 5, R29: retain the inactive phase-4 stop switch and add diagnostic timing/PID-result logging. R29 sets only the TRACE switch, so this probe does not pause any child.

```diff
diff --git a/src/fallback/macos.rs b/src/fallback/macos.rs
index a5dbee0..0337b1f 100644
--- a/src/fallback/macos.rs
+++ b/src/fallback/macos.rs
@@ -54,12 +54,22 @@ fn server_pid(port: u16) -> Option<i32> {
         .stderr(Stdio::null())
         .spawn()
         .ok()?;
+    if std::env::var_os("KACHE_FLAKY_LSOF").is_some() {
+        let stopped = unsafe { libc::kill(child.id() as i32, libc::SIGSTOP) };
+        eprintln!("FLAKY_LSOF paused owned child {}: {stopped}", child.id());
+    }
+    let probe_started = Instant::now();
     let deadline = Instant::now() + Duration::from_millis(200);
     let success = loop {
         match child.try_wait() {
             Ok(Some(status)) => break status.success(),
             Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(5)),
             _ => {
+                if std::env::var_os("KACHE_FLAKY_LSOF").is_some()
+                    || std::env::var_os("KACHE_FLAKY_LSOF_TRACE").is_some()
+                {
+                    eprintln!("FLAKY_LSOF 200ms deadline expired with owned child unfinished, elapsed={:?}", probe_started.elapsed());
+                }
                 let _ = child.kill();
                 let _ = child.wait();
                 return None;
@@ -74,7 +84,11 @@ fn server_pid(port: u16) -> Option<i32> {
     output.rewind().ok()?;
     let mut text = String::new();
     output.take(4096).read_to_string(&mut text).ok()?;
-    sandbox::parse_pid(&text)
+    let pid = sandbox::parse_pid(&text);
+    if std::env::var_os("KACHE_FLAKY_LSOF_TRACE").is_some() {
+        eprintln!("FLAKY_LSOF completed elapsed={:?}, pid={pid:?}", probe_started.elapsed());
+    }
+    pid
 }
 
 fn process_path(pid: i32) -> Option<PathBuf> {
```