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

@@FAIL_R01@@

Controlled SDKROOT removal (instrumentation shifts the original assertion line):

@@FAIL_R05@@

Controlled normalization toggle:

@@FAIL_R07@@

**2. Proven: `scheduler::tests::permit_pool_blocks_until_a_slot_is_free`, [src/scheduler.rs:2335](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/scheduler.rs:2335). Class: scheduling-dependent clock assertion. Severity: medium.**

The child writes `lock-ready` and sleeps for 300 ms before exiting, `src/scheduler.rs:2651`. The parent observes readiness, then starts its measurement at line 2341. It asserts at least 50 ms elapsed at line 2349 and at least 50 ms added to the global wait counter at line 2353. Readiness establishes that the child held the permit when it wrote the file; it does not establish that the child still holds it when the parent is scheduled to acquire.

R08 forced the parent to resume after the child exited by waiting for that same child after readiness and before the original measurement. The permit was successfully acquired, but the original lower-bound assertion failed. This inserts no work into the measured operation and changes no scheduler behavior. It is the legal schedule where the parent loses its CPU slice long enough for the 300 ms holder to finish. Reproduce: `env KACHE_FLAKY_SCHEDULER=permit ./scripts/with-test-resources.sh cargo test -p kache --bin kache permit_pool_blocks_until_a_slot_is_free -- --test-threads=1 --nocapture`. One forced failure in one invocation; R14 was a passing serial control within the scheduler suite. Load in the forced run: `{ 43.84 66.49 50.05 }`.

Fix shape: keep the child permit held until an explicit release handshake, establish a failed/nonblocking acquisition while it is held, then release it and assert acquisition succeeds. Verify wait attribution with an isolated counter or a deterministic clock rather than the remaining duration of the child's sleep.

@@FAIL_R08@@

**3. Proven: `scheduler::tests::waiter_rechecks_after_owner_completes`, [src/scheduler.rs:2300](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/scheduler.rs:2300). Class: nondeterministic thread scheduling and sleep used as synchronization. Severity: medium.**

The test spawns a waiter at line 2311, sleeps 200 ms at line 2315, and releases the child through `go` at line 2316. The fixture writes the artifact and drops its lock at lines 2568–2569. The test requires `BeginMiss::Recheck` at line 2317, assuming the waiter has already tried the held lock. `Scheduler::join_flight`, `src/scheduler.rs:413`, legitimately returns ownership immediately if its first acquisition finds the lock free; only a failed initial acquisition followed by a release produces `FlightJoin::Waited` and the recheck path.

R09 gated the waiter before its original `begin_miss`, released and joined the existing child, and only then let the waiter execute. The original assertion failed with `Compile`, while the owner's artifact had already been written. The 200 ms sleep supplies no happens-before relationship with the waiter's first lock attempt. Reproduce: `env KACHE_FLAKY_SCHEDULER=flight ./scripts/with-test-resources.sh cargo test -p kache --bin kache waiter_rechecks_after_owner_completes -- --test-threads=1 --nocapture`. One forced failure in one invocation; R14 passed without the gate. Forced-run load: `{ 43.84 66.49 50.05 }`.

Fix shape: acknowledge the waiter's failed acquisition before allowing the owner to publish/release, then assert the subsequent recheck and artifact visibility. An explicit handshake must replace the assumption that a spawned thread ran within 200 ms.

@@FAIL_R09@@

**4. Proven: `wrapper::tests::admit_scheduler_miss_recheck_returns_accepted_meta`, [src/wrapper/tests.rs:10603](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/wrapper/tests.rs:10603). Class: nondeterministic thread scheduling and sleep used as synchronization. Severity: medium.**

This has the same schedule dependency at a distinct wrapper boundary. It spawns its waiter at line 10614, sleeps 200 ms at line 10627, releases the fixture at line 10628, then requires an empty guard and a cache hit at lines 10630–10635. The child drops its scheduler guard at line 10694. `admit_scheduler_miss`, `src/wrapper.rs:1123`, consults the cached metadata only on `BeginMiss::Recheck` at line 1145; an immediately acquired flight returns `(guard, None)` at line 1150.

R12 held the waiter before the original wrapper call, released and joined the existing owner, then admitted the waiter. It returned the compile guard, failing the original assertion. Reproduce: `env KACHE_FLAKY_WRAPPER=1 ./scripts/with-test-resources.sh cargo test -p kache --bin kache admit_scheduler_miss_recheck_returns_accepted_meta -- --test-threads=1 --nocapture`. One forced failure in one invocation; R17 passed without the gate. Forced-run load: `{ 43.84 66.49 50.05 }`.

Fix shape: prove the waiter encountered the held flight before permitting release. Then assert the accepted metadata and released guard at the wrapper boundary, using the owner/waiter handshake rather than elapsed sleep.

@@FAIL_R12@@

**5. Proven: `cli::tests::test_is_macos_protected`, [src/cli/tests.rs:2823](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/cli/tests.rs:2823). Class: shared process state and order-dependent global initialization. Severity: medium; macOS only.**

`is_macos_protected`, `src/cli.rs:6209`, caches its prefix list in a process-wide `OnceLock` at line 6212. Its first call uses `dirs::home_dir()` at line 6223. The test later obtains the current home at `src/cli/tests.rs:2847` and expects that home's Desktop to be protected at line 2848. Those home values need not agree. Existing sibling code temporarily replaces HOME and XDG_CONFIG_HOME in `KunobiConfigGuard::new`, `src/test_support.rs:109`, and restores them on drop at line 132. A lock cannot retroactively repair a OnceLock initialized under a temporary home by an uncoordinated reader.

R11 initialized the existing prefix cache with a temporary HOME, restored HOME through the existing guard, and ran the original assertions. The Desktop assertion failed. No cache implementation was modified. Reproduce in a fresh process: `env KACHE_FLAKY_HOME=1 ./scripts/with-test-resources.sh cargo test -p kache --bin kache test_is_macos_protected -- --test-threads=1 --nocapture`. One forced failure in one invocation; R16 passed in a fresh process without that initialization. Forced-run load: `{ 43.84 66.49 50.05 }`.

Fix shape: test the classification core with explicit home/prefix inputs; test process-wide initialization in isolated subprocesses with a deliberately fixed HOME. Comparing a cache initialized by an earlier caller against the current ambient HOME leaves run order in the oracle.

@@FAIL_R11@@

**6. Proven: `daemon::tests::test_wait_for_warming_blocks_then_signals`, [src/daemon/tests.rs:10544](/Users/viktor/Developer/github/kache-investigations/flaky-sol/src/daemon/tests.rs:10544). Class: wall-clock upper-bound assertion under descheduling. Severity: medium.**

The signal task sleeps 50 ms at line 10551. The waiter has a five-second grace at line 10556, but the test also requires elapsed time below one second at line 10560. `wait_for_warming`, `src/daemon.rs:3268`, returns the watch-channel completion state, or observes a change under the requested timeout. A CPU scheduling pause can consume the test's one-second allowance without breaking that mechanism or exhausting the five-second grace.

R20 emitted a PID marker immediately after the original timer started, then the external controller sent SIGSTOP only to that test process, waited 1.2 seconds, and sent SIGCONT. The existing warming-result assertion passed, and the existing `elapsed < 1s` assertion failed. Reproduce by applying phase-3 instrumentation and running `python3 /private/tmp/kache-flaky/sol/run.py R20-repro python3 /private/tmp/kache-flaky/sol/suspend.py`. The controller invokes `env KACHE_FLAKY_SUSPEND=1 ./scripts/with-test-resources.sh cargo test -p kache --bin kache test_wait_for_warming_blocks_then_signals -- --test-threads=1 --nocapture`. One valid forced failure in one invocation, load `{ 26.51 43.46 46.73 }`. R15 and the subsequent uninstrumented workspace runs provide controls.

R10's preliminary probe added an await before the timer and failed the lower bound. That is **not** counted as proof: the original default current-thread Tokio runtime has no yield between spawning the signal task and starting the timer. R20 preserves that original scheduling structure and proves the upper-bound problem by pausing the process externally.

Fix shape: establish a pending warming future, signal completion, and assert it resolves successfully. Exercise timeout behavior with virtual Tokio time or explicit clock input. The mechanism does not require a real-machine one-second speed assertion.

@@FAIL_R20@@

**7. Proven: `sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server`, [tests/fallback_recovery_test.rs:220](/Users/viktor/Developer/github/kache-investigations/flaky-sol/tests/fallback_recovery_test.rs:220). Class: external-tool deadline and a strict assertion on a best-effort probe. Severity: high; macOS only.**

The test proves its sandboxed listener accepts a TCP connection using a 30-second readiness budget at lines 276–284. It then requires the fallback to be bypassed, and `fixture.calls()` to be exactly `"direct\n"`, at line 320. The optional production preflight has an independent, much narrower budget: `src/fallback/macos.rs:38` starts `/usr/sbin/lsof`; line 57 starts a 200 ms deadline; lines 59–67 kill/reap an unfinished lsof and return `None`. `src/fallback/sandbox.rs:32` propagates that missing PID as an unknown policy. `src/fallback.rs:35` then takes its documented recovery path: try the fallback and, if it fails, compile directly. The test's listener-readiness condition does not ensure lsof completes within 200 ms.

R21 naturally failed the original call-sequence assertion in a 16-thread full run, load `{ 79.93 70.06 57.80 }`. R19 at one thread and R22 at 32 threads passed this target, so failure is not a monotonic function of thread count. R27 stopped only the lsof child that kache had just spawned, leaving the test's ready listener and all policy/timeout logic intact. The log records a successful SIGSTOP, expiry of the 200 ms deadline, and the same original assertion failure: `"fallback\ndirect\n"` instead of `"direct\n"`. This is one on-demand failure in one invocation at one thread, load `{ 19.34 54.36 58.75 }`. The natural R21 failure had no branch trace, so the precise reason its optional probe returned unknown cannot be retroactively identified; the deadline mechanism is independently proved sufficient.

Reproduce with phase-4 instrumentation: `env KACHE_FLAKY_LSOF=1 ./scripts/with-test-resources.sh cargo test -p kache --test fallback_recovery_test sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server -- --test-threads=1 --nocapture`. R28 was the control with that flag absent and also failed the call-sequence assertion (load `{ 23.00 47.22 55.58 }`). R29 added branch/elapsed logging with no process stop and failed again, load `{ 43.10 47.66 55.15 }`. It directly recorded the production deadline expiring at **202.175542 ms with lsof unfinished**, proving this cause in an ordinary, unpaused process. Its output appears below.

Fix shape: test policy-based bypass with the deterministic Probe already used in `src/fallback/sandbox.rs`; test native policy against a known ready child PID separately. The full integration test should accept the documented fail-open recovery outcome when optional PID discovery times out, while still checking successful direct compilation and the structured attempt outcome. Listener readiness should not stand in for guaranteed completion of lsof.

Natural failure:

@@FAIL_R21@@

Controlled lsof deadline failure:

@@FAIL_R27@@

Unpaused run with branch logging:

@@FAIL_R29@@

**Static risks not promoted to proven findings.**

The additional mechanisms below remain suspected. Except for F7, which already has a distinct proven cause, these tests did not fail in the uninstrumented valid-path runs. Severity is low for these static risks; failure output is therefore absent. A successful run does not prove these sites cannot flake. Their observations used the full commands, thread counts, and loads in the run ledger; no special repetitions were performed. Counts below are failures over full commands that reached the named test, including the identified setup runs.

| Test and original site | Full-command failures/reached | Suspected mechanism/class | Fix shape and next discriminating probe |
|---|---|---|---|
| `daemon::tests::test_wait_for_warming_already_signaled`, `src/daemon/tests.rs:10511`; `test_prefetch_disabled_remote_releases_warming_barrier`, `:10524`; `test_wait_for_warming_timeout`, `:10564` | @@RISK_WARM@@ each | 500 ms upper bounds at 10520, 10538, 10574 include OS descheduling. Clock/timing. | Assert watch state/timeout using controlled time. Pause only the owned test process inside each timed interval while preserving the original scheduling structure. |
| `daemon_publish::tests::handing_off_without_a_socket_declines_at_once`, `src/daemon_publish.rs:1784` | @@RISK_PUBLISH@@ | A correct declined-socket result can still take more than its 100 ms elapsed allowance at 1804. Clock/timing. | Assert the declined reason and absence of a retry; suspend its own process after the timer starts to settle the risk. |
| `events::tests::choosing_what_to_keep_stays_linear_in_the_log`, `src/events.rs:2672` | @@RISK_EVENTS@@ | Two-second performance assertion at 2682 depends on scheduler/CPU speed, not just complexity. Clock/timing. | Pin work/operation growth; run controlled descheduling within the timed operation to distinguish algorithm correctness from wall time. |
| `tui::tests::background_work_is_due_only_when_unpaused_idle_and_on_schedule`, `src/tui/tests.rs:1777` | @@RISK_TUI@@ | Fresh `Instant::now()` samples at 1794 and 1803 are followed by negative due assertions; deadlines are 2 and 10 seconds (`src/tui.rs:730`). Clock/timing. | Pass a fixed `now`; pause between the fresh sample and assertion beyond its interval. |
| `tree_stamp::tests::a_stamp_settles_one_window_after_its_newest_write`, `src/tree_stamp.rs:517` | @@RISK_STAMP@@ | The real-file branch expects the freshly walked stamp still unsettled at live `now`, 538. The window is two seconds at line 24. Clock/timing. | Assert against the observed newest timestamp and a supplied time; pause after the walk beyond the window. |
| `scheduler::pressure::tests::a_forced_answer_replaces_the_machine_until_cleared`, `src/scheduler/pressure.rs:175` | @@RISK_PRESSURE@@ | Reads live kernel pressure once at 178 and expects the same live result after clearing the pin at 184; pressure may change meanwhile. Shared host resource state. | Supply the pressure reader or assert pin behavior independently of two live readings. A controlled reader transition would settle it; kernel state was not altered. |
| `store::tests::eviction_pauses_between_write_slices`, `crates/kache-store/src/store/tests.rs:12167` | @@RISK_EVICT@@ | Requires 500 removals to consume at least a 5 ms slice at 12187; a sufficiently fast fixture may not do so. Timing/fixture throughput. | Drive slice expiry with controlled clock/work state and assert the pause boundary; no fast-host failure was observed. |
| F7's additional port handoff, `tests/fallback_recovery_test.rs:259–271` | No isolated port-collision failure | The ephemeral reservation is dropped before the C listener binds; a different process could take that port, and TCP connect alone would accept it as readiness. Shared port/TOCTOU; never observed. | Have the child bind port zero and report its owned port, or transfer the reserved listener. A competing listener deliberately bound in that gap would settle this separate risk. |

**Static sweep and stable checks.**

The source sweep checked explicit clock samples (`Instant`, `SystemTime`, `Utc`, `Local`, `stamp_clock_ns`), sleeps, elapsed/deadline/timeout calls, and direct process-global environment/cwd/signal mutations in test files, annotated test scopes, and test-support code under `src/`, `crates/`, and `tests/`. This is a source inventory, not a claim that every listed call is a bug. Clock sampling used only to stamp fixture events or pass an explicit time is common. Many sleeps are bounded retry/poll helpers, fixture lifetimes, or intentional test input. Many timeouts are watchdogs around a separately asserted mechanism.

Graph navigation used `search_graph`, `trace_path`, and `get_code_snippet`. Coverage checks were made for relied-on files. The index reported partial Rust semantics (binding oracle, expanded calls, and impl relationships unavailable); direct source reads and literal searches supplement those links. During instrumentation, changed-source files were read directly and their diffs preserved. No exhaustive absence claim rests on a graph edge being absent.

The table below gives every matched source site compactly as file plus original line numbers, split into clock/sleep/timeout sites and direct mutation sites. Together each column denotes `file:line` for every listed line. `set_env_for_test` and its matching restore implementation at `src/config/tests.rs:98–123` are excluded from the direct-mutation inventory as requested. Other environment guards and their restore writes remain included. 'No' means no valid-path, uninstrumented failure observed for those direct sites; the seven indirect/forced mechanisms are documented above. Ignored or platform-excluded code is not treated as executed proof. Tests may also return early when a toolchain is unavailable; native Linux, Windows, CUDA, and live cloud dependencies were not forced into availability.

@@SWEEP@@

Additional global-state sites: `src/cli.rs:6212` (home-derived OnceLock, proven above), `src/heartbeat.rs:57` (one-shot heartbeat context; installation at 72, test caller at 402), `src/opcounts.rs:122–127` (process start and additive counters), `src/scheduler/pressure.rs:33` (global enabled switch; test writes at 177, 242, 244), `src/phase_trace.rs:12` (thread-local recorder, not shared across libtest threads). The counters are cumulative, so lower-bound delta assertions can be stable but cannot prove exclusive attribution under concurrency. No independent counter/context failure was observed. These supplementary statics are not captured by a search limited to `set_var` and clock literals.

The shell regression fixture also sleeps at `tests/fixtures/cc_release_regressions.sh:28,45,49,75,85`. It is invoked through `tests/cc_release_regression_test.rs:32`; all four caller tests reported passing in the seven full commands that reached that target. No failure at those shell sleep sites was observed.

What checked stable: the valid-path serial run completed all enabled workspace targets, including 4,446 kache unit tests and 571 kache-store tests; the other valid-path runs are recorded below. Nonempty SDKROOT relocation was stable; isolated controls of the gated scheduler/wrapper/home tests passed. The rejected-meta wrapper test uses the same 200 ms sleep, but its final expected compile outcome also holds when the waiter starts late, so that sleep alone is not evidence it flakes. Download-waiter tests at `src/daemon/tests.rs:13708,13744,13861` combine notifications with map rechecks; no lost-wakeup failure was observed. The file-hash wall-clock observation test at `crates/kache-store/src/file_hash.rs:1137` brackets the observation with before/after samples rather than an elapsed speed requirement; it passed, though wall-clock adjustments were not induced. Phase tracing uses a thread-local recorder. Socket fixtures reviewed use unique temporary paths or ephemeral loopback ports, including `tests/fallback_recovery_test.rs:259` and `tests/s3_remote_test.rs:462`; no port collision, EMFILE, thread-exhaustion, or disk-exhaustion failure was observed. The resource wrapper remained in use; low-nofile exhaustion was not constructed.

**Run ledger, limitations, and stop rule.**

R01–R03 used `TMPDIR=/private/tmp/kache-flaky/sol/tmp`; R04–R18 used the worktree's `.flaky-tmp`; R19 onward use `/tmp/kache-flaky/sol/t`, whose resolved path is inside `/private/tmp/kache-flaky/sol/`. The scratch-path changes were necessary to honor the write fence while avoiding macOS protection and long socket names. R01/R02's two CLI target-discovery failures are deterministic: `src/cli.rs:6218` excludes `/private` and line 6265 returns before scanning. R18's 19 failures include `SUN_LEN` socket rejection and fixture paths accidentally inheriting the repository's workspace/toolchain roots; all disappeared in the serial run with the short outside-worktree alias. They are recorded as setup/path failures rather than timing/concurrency findings. No failure from those runs was silently converted into a timing finding.

R03/R04 were queued before earlier work finished; their isolated test processes overlapped briefly after build/package locks cleared. All subsequent test invocations were sequential. Loads also reflect the other investigator and unrelated jobs. No process not started by this investigation was stopped or killed; R20 paused/resumed its own test process; R27 paused its own lsof child, which the existing timeout killed and reaped.

@@COUNTS@@

@@RUNS@@

Full logs are linked in the run table. The exact command arguments, start/end times, load, and cargo exit status are also in [runs.jsonl](/private/tmp/kache-flaky/sol/runs.jsonl). The wrapper script itself returns zero after recording a child failure, so the recorded cargo/child exit status—not the orchestration process's exit—is the result used here. R20's controller command has one test thread internally even though its outer ledger field says default.

**Temporary instrumentation diffs.**

Phase 1, R03: controlled SDKROOT relocation. This passed and is a negative discriminator for claiming that any SDK path change must change a key.

```diff
@@PATCH1@@
```

Phase 2, R05–R17: environment switches, owner/waiter gates, home-cache initialization, and the rejected preliminary warming probe. R06's OUT_DIR probe passed. The three-line warming await in this patch is the invalid R10 experiment, explicitly superseded by phase 3.

```diff
@@PATCH2@@
```

Phase 3, R20: PID marker only; the controller performs the process pause outside the test. Its controller source is [suspend.py](/private/tmp/kache-flaky/sol/suspend.py). The phase-3 patch was removed before R21. The suite was paused between R22 and R23 for the new fallback probe; both fallback instrumentation phases were removed before resuming it.

```diff
@@PATCH3@@
```

Phase 4, R27–R28: stop only the lsof child just spawned by this kache process, so the existing 200 ms timeout executes. The flag is absent in the control and all subsequent workspace runs.

```diff
@@PATCH4@@
```

Phase 5, R29: retain the inactive phase-4 stop switch and add diagnostic timing/PID-result logging. R29 sets only the TRACE switch, so this probe does not pause any child.

```diff
@@PATCH5@@
```
