# Flaky-test investigation: kache workspace (arm: opus)

- **Worktree:** `/Users/viktor/Developer/github/kache-investigations/flaky-opus`, detached at `991c836`.
- **Target dir:** `/private/tmp/kache-flaky/opus/target`.
- **Time:** 11:36 to 13:10 AEST.
- **Budget used:** 8 of 10 full-workspace runs, and about 274 of 300 runs of the known test.
- **Instrumentation:** the diff is at `/private/tmp/kache-flaky/opus/instrumentation.diff` (311 lines, summarised in Appendix A). I reverted it with `git apply -R`, so `git status` is clean.

All line numbers are at HEAD. Some failure output below was captured while the instrumentation was applied; there the cc test lines are 4 higher (`tests.rs:299` there is HEAD `:295`, and `:303` is HEAD `:299`).

## Verdict

The owner's idea that flaky tests assert the clock does not explain the known case. That failure is a race on **environment variables** shared by every test in the process. Tests that **leak env changes** into the rest of the run make it worse. One of the two flakes I saw in full-workspace runs does fit the clock idea: an integration test that, through its outcome, depends on a 200 ms production `lsof` deadline.

| # | Test | Class | Proven? | Seen without forcing | Severity |
|---|---|---|---|---|---|
| 1 | `compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes` (known case) | Env vars: a test reading without the lock races tests writing under it, plus an order-dependent env leak | **Proven**: exact hashes reproduced, interleaving forced | 3/40 `cargo test --bin kache`; 10/100 cc-module runs; 0/8 full runs | high |
| 2 | `cli::tests::test_is_macos_protected` (`src/cli/tests.rs:2823`, macOS only) | `HOME` cached in a process-wide `OnceLock` | **Proven**: deterministic cache poisoning | 2/40 `cargo test --bin kache` | high (macOS) |
| 3 | `sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server` (`tests/fallback_recovery_test.rs:220`) | Clock: the outcome depends on a 200 ms subprocess deadline in production | **Proven** that a missed deadline gives the identical failure; that load is what pushes `lsof` past 200 ms is strongly supported, not forced | 2/8 full runs (one at ambient load, one under load I added) | high |
| 4 | `compiler::cc::tests::a_key_from_before_the_input_race_fixes_is_never_todays` (`cc/tests.rs:310`) | Env vars, same as #1 | **Proven** (forced, 10/20) | 0 | low |
| 5 | `path_normalizer::tests::from_env_construction_is_deterministic` (`path_normalizer.rs:2793`) | Current directory and env | **Proven** (forced: 11/15 via cwd, 4/15 via `KACHE_BASE_DIR`) | 0 | low |
| 6 | `compiler::nvcc::tests::execute_drops_artifacts_when_object_embeds_mapped_root` (`nvcc.rs:2299`) | Env var `KACHE_NVCC_PATH_NORMALIZE` | **Proven** (forced, 1/15) | 0 | low |
| 7 | `daemon::tests::detached_daemon_survives_sigint_to_the_callers_group` (`daemon/tests.rs:151`) | Inherited signal disposition (SIGINT ignored by whatever launched the tests) | **Proven** (deterministic) | 1 run, caused by how I launched it | medium |

## 1. Known case: `terminal_formatting_shares_cc_keys_with_cold_and_warm_probes`

**Location.** `src/compiler/cc/tests.rs:250`. The failing asserts are `:295` (cold probe) and `:299` (warm probe).

### Reproduction

- **As in `just check`:**
  - Command: `./scripts/with-test-resources.sh cargo test -q --bin kache`, 16 threads.
  - Load: 18 to 123.
  - Result: **3/40 runs failed** (runs 19, 25 and 39, at loads 21.6, 25.3 and 31.0).
- **cc module only:**
  - Command: `env -u OUT_DIR <bin> compiler::cc::tests --skip zz_flaky`, 16 threads.
  - Load: 58 to 21.
  - Result: **10/100 failed**.
- **Full workspace:** the `just test` command failed this test **0/8** times. Among 4,460 tests its window is narrow.
- **Forced, test unchanged:**
  - Command: `env -u OUT_DIR FLAKY_TOGGLE_MS=1500 <bin> --test-threads=4 <known test> zz_flaky_sdkroot_toggler`. The toggler holds the lock and switches `SDKROOT` on and off.
  - Load: 53.
  - Result: **20/20 failed**.
- **Forced, deterministic (a hook inside the test):**
  - Command: `env -u OUT_DIR FLAKY_FORCE_SDKROOT=/tmp/flaky-sdk <bin> --exact <known test>`.
  - Load: 64.
  - Result: 2/2 failed, byte-identical to the reported failure:

```
thread 'compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes' (147842183) panicked at src/compiler/cc/tests.rs:299:9:
assertion `left == right` failed
  left: "6a5dd9ebc2a33d878f7a0ea2cb8942db35b71cc3b4bbf8aca8d1ea4a8d5ae4d7"
 right: "ec170f0d4c633cc97b1a38b9c75e0ee2cbe2781647e22b1dca0817e436d3899a"
```

An unforced failure (`cargo test --bin kache`, run 25) produced the same pair at instrumented line `:303`, which is HEAD `:299`. Run 19 failed with left `23e919aa…` and right `ec170f0d…`.

### Mechanism

1. **The cc cache key reads the environment at call time.**
   - `cc_prefix_maps` (`src/compiler/cc.rs:4389`) reads `KACHE_CC_PATH_NORMALIZE`, `KACHE_BASE_DIR`, `SDKROOT` and `OUT_DIR` for its memo (`cc.rs:4402-4411`).
   - It reads them again when rebuilding the maps: `cc.rs:4445`, `:4449`, `:4458` and `:4650`.
   - The resulting maps go into the key at `cc.rs:6933` (the `prefix_maps:` line) and `cc.rs:7108` (source paths).
   - The test never takes `process_state_test_lock`. It computes `baseline` once, then recomputes the key 8 more times, each run launching a shell-script compiler. That gives a window of tens of milliseconds.
2. **Tests that hold the lock change exactly those variables.**
   - `include_dir_digest_exempts_an_existing_sdkroot_directory` (`tests.rs:6976`) sets `SDKROOT=<tmp>/sdk`.
   - `out_dir_and_sdk_maps_follow_the_environment_and_the_normalize_switch` (`tests.rs:7962`) moves through `OUT_DIR=<tmp>/…/out`, then `SDKROOT=<tmp>/sdk`, then `OUT_DIR=""`, then `KACHE_CC_PATH_NORMALIZE=0`.
   - The lock keeps the writers from colliding with each other, not with this test, which only reads.
3. **Two earlier tests delete cargo's `OUT_DIR` for the rest of the run.**
   - `build_script::tests::a_symlinked_root_maps_both_spellings_and_a_plain_root_maps_once` (`src/build_script.rs:2685`, with `remove_var` at `:2701`).
   - `a_base_dir_keys_the_same_across_checkouts_only_in_remapping_flags` (`build_script.rs:2790`, with `remove_var` at `:2810`).
   - The test harness starts tests in name order, so these run before the cc tests.
   - I confirmed it under cargo with `--test-threads=1`: an instrumented copy of the key computation gives `23e919aa…` when run alone and `ec170f0d…` when run after either leaking test.
4. **The reported hashes map exactly to environment states.** The key does not depend on checkout location: running from the main checkout gave the same hashes.

| Environment state | Key |
|---|---|
| `OUT_DIR` unset, `SDKROOT` unset | `ec170f0d…`, the reported **right** (baseline) |
| `OUT_DIR` unset or `""`, `SDKROOT` set to any path | `6a5dd9eb…`, the reported **left** |
| `OUT_DIR` set the way cargo sets it (`…/target/debug/build/X/out`) | `23e919aa…` |
| `OUT_DIR` and `SDKROOT` both set | `5503f180…` |

So the failure the owner saw happened like this:
- `baseline` was computed after the leaking test had removed `OUT_DIR`, giving `ec17…`.
- During the loop, a lock-holding test had `SDKROOT` set, giving `6a5d…`.
- The cold assert at `:295` fired first.

I checked these and they leave the key unchanged:
- the current directory, `SOURCE_DATE_EPOCH`, `CPATH`, `LANG`, `PATH` and `CARGO_MANIFEST_DIR`;
- `KACHE_CACHE_DIR`, `KACHE_KEY_*`, `KACHE_CC_KEY_PROBE` and `DEP_*`.

**Class.** Env vars: a test reading without the lock races tests writing under it. Run order matters because of the env leaks. Not clock-related.

**Fix shape.**
- Minimal: hold the lock and pin the four variables with `set_env_for_test` before computing `baseline`.
- Better, per AGENTS.md:
  - pass an environment snapshot (`OUT_DIR`, `SDKROOT`, `KACHE_BASE_DIR`, `KACHE_CC_PATH_NORMALIZE`, current directory) into `cc_prefix_maps` through `KeyCtx`;
  - have the test pin that snapshot.
- Separately, the two `build_script` tests should use `set_env_for_test` instead of a bare `remove_var`.

**Severity: high.** About 7.5% of `cargo test --bin kache` runs fail, and it failed the owner's `just check`.

## 2. `cli::tests::test_is_macos_protected` (`src/cli/tests.rs:2823`, assert at `:2848`)

**Reproduction.**
- **Without forcing:** `cargo test -q --bin kache`, 16 threads, failed **2/40** (runs 13 and 25, at loads 39.4 and 25.3).
- **Forced:**
  - Command: `FLAKY_HOME_POISON=1 <bin> --test-threads=1 build_script::tests::zz_flaky_first_protected_call_under_home_override cli::tests::test_is_macos_protected`.
  - Result: failed 1/1. Without the env var it passed 1/1.
  - Load: 32.
- **Toggler running alongside the test:** 0/20. The test body takes microseconds and finishes before the toggler first overrides `HOME`.

```
thread 'cli::tests::test_is_macos_protected' (149397471) panicked at src/cli/tests.rs:2848:9:
assertion failed: is_macos_protected(&home.join("Desktop"))
```

**Mechanism.**
- `is_macos_protected` (`src/cli.rs:6209`) reads `$HOME` once, on its first call, and caches the list of protected directories in a process-wide `OnceLock` (`cli.rs:6212`, read at `:6223`).
- `KunobiConfigGuard` (`test_support.rs:107`) sets `HOME` to a temp directory under the lock. It is used by `cli::login::tests` and `planner_auth` tests; `wrapper_config.rs:345` also overrides `HOME`. `cli::login::tests` sorts directly before `cli::tests`, so they overlap.
- If the first call (from a `find_target_dirs` test, which holds no lock, or from this test) happens during such an override, the rest of the run holds `<tmp>/Desktop`, and every assert against the real home fails.
- Not forced: the test's own read of the home directory at `:2847` could also land during an override.

**Class.** An env var captured into a process-wide static. Whichever test calls it first decides the cached value for every later test.

**Fix shape.** Split out a pure `is_protected_under(path, home)` and test that directly. Alternatively, hold the lock and assert against the cached prefixes.

**Severity: high on macOS.** Linux compiles a stub that always returns false.

## 3. `sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server` (`tests/fallback_recovery_test.rs:220`, assert at `:320`)

**Reproduction.**
- **Full workspace** (`cargo test --workspace --no-fail-fast`):
  - full6 failed with no added load (load 83 to 16).
  - full5 failed with 32 `yes` processes running (load 199 to 255).
  - That is 2/8 full runs.
- **Alone with `--exact`:** 0/20 at load 175, and 0/20 with 32 `yes` processes.
- **Forced:**
  - Command: `FLAKY_LSOF_DEADLINE_MS=1 cargo test --test fallback_recovery_test -- sandbox_preflight…`. A temporary hook in `src/fallback/macos.rs` makes the deadline adjustable.
  - Result: 1/1 failed with identical output. The control run passed.
  - Load: 227.

```
thread 'sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server' (152410921) panicked at tests/fallback_recovery_test.rs:320:5:
assertion `left == right` failed: fallback compiler error
kache: warning: fallback `/var/folders/wq/48xldn_s09x1lqc7t7m16q7w0000gp/T/.tmpEfsZdx/sccache`: exit status: 42; compiling directly without fallback

  left: "fallback\ndirect\n"
 right: "direct\n"
```

**Mechanism.**
- To find the sccache server's PID, the preflight runs `/usr/sbin/lsof` with a hard **200 ms** deadline (`src/fallback/macos.rs:57`).
- On timeout it returns nothing, so the preflight declines and the fallback compiler runs. The test therefore effectively asserts that `lsof` finishes within 200 ms.
- I timed `lsof` while the kache unit-test binary ran: 341 samples, median 70 ms, p90 89 ms, max 241 ms, 1 over 200 ms. That was at load 27 to 56.
- I shortened the deadline on demand; I did not slow `lsof` itself.

**Second suspected cause.** The test reserves a port by binding and dropping it (`tests/fallback_recovery_test.rs:259-261`) before the sandboxed server binds it. Another process could grab the port in between, which would produce the same output. Next probe: log what each probe step returns during a full run.

**Class.** Clock/timing: the test's outcome depends on a production deadline. Possibly also a shared-port race.

**Fix shape.**
- Test the policy with a fake probe; `sandbox::check` already takes a trait.
- Or have the test pass a generous deadline, and assert on the `sandbox_denied` event rather than on the fallback never running.
- Hand the listening socket to the server instead of rebinding the port.

**Severity: high.** It failed 2 of 8 full runs, one at ambient load.

## 4. `a_key_from_before_the_input_race_fixes_is_never_todays` (`cc/tests.rs:310`, assert at `:340`)

**Reproduction.**
- Command: `env -u OUT_DIR FLAKY_TOGGLE_MS=1000 <bin> --test-threads=4 <test> zz_flaky_sdkroot_toggler`.
- Result: **10/20 failed**. Load: 59 to 84.
- It never failed unforced.
- Output: `panicked at …:344:5` (HEAD `:340`), left `6a5dd9eb…`, right `ec170f0d…`.

**Mechanism.** Same as #1: no lock, and it compares two key computations. Its window is only two computations, so it fails less often.

**Fix.** Same as #1.

**Severity: low.**

## 5. `path_normalizer::tests::from_env_construction_is_deterministic` (`path_normalizer.rs:2793`, assert at `:2811`)

**Reproduction.** Command: `FLAKY_GEN_MS=600 <bin> --test-threads=4 <test> zz_flaky_generic_toggler`. Load: 105 to 74.
- With `FLAKY_GEN_CWD=1` (current directory switched the way `lock.enter()` does): **11/15 failed**.
- With `FLAKY_GEN_VAR=KACHE_BASE_DIR`: **4/15 failed**.

**Output.** `assertion left == right failed`. One rule list starts with the worktree as `<WORKSPACE>`, the other with a temp directory as `<WORKSPACE>`. Under the `KACHE_BASE_DIR` toggle, an extra `("/tmp/flaky-base", "<BASE_DIR>")` rule appears.

**Mechanism.**
- `PathNormalizer::from_env` reads `KACHE_BASE_DIR` (`:232`) and the current directory (`:239`).
- The test holds no lock while building two normalizers and comparing them.
- The writers are every `lock.enter()` test and `build_script.rs:2805`.

**Sibling.** `with_rust_src_rule_is_noop_without_sysroot_hash_or_installed_src` (`:2411`) failed 0/15 with the same toggler, so it remains suspected only.

**Fix.** Build from an explicit env/cwd snapshot, or hold the lock.

**Severity: low.**

## 6. `execute_drops_artifacts_when_object_embeds_mapped_root` (`nvcc.rs:2299`, assert at `:2327`)

**Reproduction.**
- Command: the generic toggler with `KACHE_NVCC_PATH_NORMALIZE=0`.
- Result: **1/15 failed**. Load: about 90.

```
an object that embeds a mapped root must not be cached, got [".../k.o"]
```

**Mechanism.** The test reads `KACHE_NVCC_PATH_NORMALIZE` (`nvcc.rs:874`) without the lock. The locked test `normalize_disabled_by_knob` (`nvcc.rs:2211`) sets it to `0`.

**Fix.** Hold the lock, or pass the switch in explicitly.

**Severity: low.**

## 7. `detached_daemon_survives_sigint_to_the_callers_group` (`daemon/tests.rs:151`, assert at `:208`)

**Reproduction.**
- It failed once when I launched the test binary with `( <bin> -q ) &` (load 27 to 56).
- **Deterministic:**
  - Command: launch the test through a Python wrapper that sets SIGINT to ignored, then runs `<bin> --exact <test>`.
  - Result: 1/1 failed after 60.35 s. With normal SIGINT handling it passed in 0.38 s.
  - Load: 76.
  - Output: `SIGINT never reached the caller's group`.

**Mechanism.**
- A non-interactive shell starts background jobs with SIGINT ignored, and child processes inherit that.
- The test's helper process (`:124`) therefore ignores the `kill(-group, SIGINT)` at `:195`. It sleeps its full 60 s, exits 0, and the assert fails.

**Class.** A new one: inherited signal disposition, not timing.

**Fix.** Reset SIGINT to default in the helper process before it runs.

**Severity: medium.** It never happens from an interactive `just check`. It would happen in any script or CI step that runs the tests as a background job.

## Not a finding: my own instrumentation

In my first 100-run cc-module loop, `out_dir_and_sdk_maps_follow_the_environment_and_the_normalize_switch` failed once. My own `zz_flaky_probe_states` caused it: it released the lock before its env guards restored their values. I fixed that and reran the loop with `--skip zz_flaky`, which is where the 10/100 figure comes from. I excluded the first loop's 16/100.

## Static sweep summary

This comes from two read-only sweep agents plus my own greps. "Seen failing" means it failed in one of my runs.

### Env, current directory and other process-wide state

All the test locks are the same mutex as `process_state_test_lock`: `config_path_lock`, `key_test_lock`, `KunobiConfigGuard`, `PlannerEnv` and `TestCacheDirGuard`. No committed test restores env outside its lock.

**Changes made with no lock** (none seen failing):
- `timeline.rs:1893` (`KACHE_RUNNER_POOL`)
- `crates/kache-e2e/src/scenario_runner.rs:276`
- `compiler/mod.rs:2763` and `:2810`: ignored fixtures that set `PATH` and never restore it
- `platform.rs:388`: lowers the open-file limit (`RLIMIT_NOFILE`) and never restores the original
- `wrapper/tests.rs:673`: the `MAPPED_TARGET` static
- `worktree_discovery.rs:829`: the `LAST_RUN` static

**Leaks** (old value thrown away; only the `OUT_DIR` leak was seen contributing to a failure):
- `src/build_script.rs`:
  - `:2685` and `:2790`: `OUT_DIR`, `CARGO_MANIFEST_DIR`, `CARGO_HOME`, `KACHE_BASE_DIR`. These **feed #1**.
  - `:2102`: `TARGET`.
  - `:2160`: `DEP_Z_INCLUDE` and `CARGO_CFG_UNIX`.
  - `:2503` and `:3267`: `KACHE_BUILD_SCRIPT_CACHE`.
  - `:3345`, `:3531`, `:3603`, `:4327`, `:4366`: `DEP_*`.
  - `:4584` to `:4700`: `KACHE_CACHE_DIR` and `KACHE_RUNTIME_DIR`.
- `src/cache_key/tests.rs`:
  - `:5433`: `CARGO_MANIFEST_DIR` and `OUT_DIR`.
  - `:16041`: `OUT_DIR`.
  - `:16155`: `KACHE_CACHE_DIR`.
- `src/compiler/cc/tests.rs`:
  - `:4480`: about 18 vars, including `SDKROOT` and `CPATH`.
  - `:6968` and `:6989`: `SDKROOT`.
  - `:7708`: `TARGET`.
  - `:7938`: `CPATH`.
- `src/config/tests.rs`:
  - `:2240` to `:2405`: `KACHE_DEFERRED_*`, `KACHE_DAEMON_PUBLISH`, `KACHE_SHARED_HARDLINK_RESTORES`.
  - `:2413`: `KACHE_CACHE_DIR`.
  - `:4466`: `KACHE_S3_*`, which CI exports.
- `src/native_link_key.rs:2163` and `:2194`: `LIBRARY_PATH`, `GCC_EXEC_PREFIX` and `COMPILER_PATH`.

**Restored only if the test passes:** 31 locked sites. Examples are `RUSTC_LINKER` in `build_script.rs`, `KACHE_RUSTC_PATH_NORMALIZE` and `OUT_DIR` in `cache_key/tests.rs:14794` to `:16040`, `cc/tests.rs:5808`, `:7985` and `:8070`, and the config precedence tests. A failure in any of them leaks into later tests. None seen.

**Tests without the lock that compare two env-dependent values:**
- #1, #4, #5 and #6 above.
- `path_normalizer.rs:2411` (forced 0/15).
- `cc/tests.rs:6336` (only bites if `SOURCE_DATE_EPOCH` is set in the environment).
- None in `cache_key/tests.rs`, `build_script.rs` or `wrapper/tests.rs`.

**Other process-wide statics** (none seen except #2):
- the `is_macos_protected` `OnceLock` (#2, seen failing);
- kache-store's `SHARED_TEST_LOCK` (`link.rs:4683`) is a different mutex from that crate's process-state lock;
- the set-once `set_cow_warn_marker` `OnceLock`;
- the `heartbeat.rs:402` `CTX` `OnceLock`.

### Clock and timing in test code

No test pauses tokio time, so every tokio sleep and timeout uses the real clock. Apart from #3, none of these failed in my runs.

**High risk** (under-a-second wall-clock bounds, or a sleep used to order threads or processes):
- `daemon/tests.rs`: `:1292` (<750 ms), `:10520` and `:10538` (<500 ms), `:10559`, `:10573`, and the 100 ms timeouts at `:11780` and `:13001`.
- `daemon_publish.rs`: `:1440` to `:1447` (150 ms stall window), `:1804` (<100 ms).
- `test_support.rs`: `:409` (<250 ms), `:380` (Linux only).
- `scheduler.rs`: `:2315` (sleep 200 ms then "go"), `:2477` (30 ms), `:2349`, `:2911` (<300 ms).
- `wrapper/tests.rs`: `:10627` and `:10663` (sleep 200 ms then "go"), `:6539`.
- `tests/test_runner_test.rs:255` (macOS: 500 ms before SIGINT).
- `events.rs:3017` to `:3132`.
- `fallback/macos.rs:57` (**seen failing, #3**).

**Medium risk** (1 to 10 s deadlines or polling):
- About 45 sites, mostly 1 to 2 s timeouts in `daemon/tests.rs`.
- Polling helpers: `daemon/tests.rs:6069` and `:6810`; `wrapper/tests.rs:6044` and `:10589`; kache-store `store/tests.rs:5231`, `:7449`, `:3522`, `:8405`; `build_intent.rs:699` and `:811`.
- Retry loops for "text file busy" errors, 10×10 ms: `probe/mod.rs:1380`, `:1451`, `:1583` and `cc/tests.rs:5703`.

**Low risk:**
- About 60 sites with generous bounds, checks that something does not happen, lower bounds only, or file-time ageing with margin.
- `wrapper/tests.rs:10739` and `cache_key/tests.rs:13037` and `:13270` assume file timestamps tick within 20 to 50 ms. They would fail on filesystems with 1 s granularity, not under load.

## Run table

"known" counts runs of the known test. `<bin>` is `/private/tmp/kache-flaky/opus/target/debug/deps/kache-881bf021f508393b`. Load is the 1-minute `vm.loadavg` at start → end.

| # | Command | Threads | Load | Result |
|---|---|---|---|---|
| 1 | `cargo test --workspace --no-run` | – | 29 | build ok |
| 2 | `cargo test --bin kache -- zz_flaky_probe` (env/cwd perturbation) | 16 | 23 | `OUT_DIR`, `SDKROOT`, `KACHE_BASE_DIR`, `KACHE_CC_PATH_NORMALIZE` change the key; cwd and 13 other vars do not |
| 3 | `<bin> zz_flaky_probe…` run directly, several times with `OUT_DIR` variants and from the main checkout | 16 | ~60 | `ec17` without `OUT_DIR`, `23e9` with a cargo-style `OUT_DIR` |
| 4 | `<bin> zz_flaky_probe_states` | 16 | ~60 | `6a5d` = `OUT_DIR` unset + `SDKROOT` set |
| 5 | known test `--exact`: forced ×4, unforced ×1 | 16 | 64 | 4/4 forced fail with the reported hashes; unforced ok (known: 5) |
| 6 | key computation alone / after each leaking test, `--test-threads=1` | 1 | 57 | `23e9` / `ec17` |
| 7 | known test + SDKROOT toggler ×20 | 4 | 53 → 36 | **20/20 fail** (known: 20) |
| 8 | `compiler::cc::tests` ×100, instrumentation included | 16 | 31 → 46 | 16/100 fail, plus 1 instrumentation artifact (known: 100) |
| 9 | `compiler::cc::tests --skip zz_flaky` ×100 | 16 | 58 → 21 | **10/100 known fail**, nothing else (known: 100) |
| 10 | `a_key_from_before…` + toggler ×20 | 4 | 59 → 84 | **10/20 fail** |
| 11 | full1, `./scripts/with-test-resources.sh cargo test --workspace` | 16 | 18 → 98 | ok, 5m17s (known: 1) |
| 12 | `./scripts/with-test-resources.sh cargo test -q --bin kache` ×40 | 16 | 18–123 | known **3/40**, `test_is_macos_protected` **2/40** (known: 40) |
| 13 | `test_is_macos_protected` + HOME toggler ×20 | 4 | 20 → 34 | 0/20 |
| 14 | HOME-poisoning test, then `test_is_macos_protected`, poison on / off | 1 | 32 | **fail** / ok |
| 15 | full2, full3 | 16 | 32 → 43, 43 → 40 | ok, ok (known: 2) |
| 16 | full4 with 32 `yes` processes | 16 | 55 → 199 | ok (known: 1) |
| 17 | full5 with 32 `yes` processes, `--no-fail-fast` | 16 | 199 → 255 | **FAIL** `sandbox_preflight…` (known: 1) |
| 18 | `sandbox_preflight…` control / `FLAKY_LSOF_DEADLINE_MS=1` | 16 | 227 | ok / **fail** |
| 19 | `sandbox_preflight… --exact` ×20, then ×20 with 32 `yes` processes | 16 | 175, 168 | 0/20, 0/20 |
| 20 | generic toggler ×15 each: #5 via cwd / via `KACHE_BASE_DIR`; `:2411` via cwd; #6 | 4 | 105 → 74 | **11/15**, **4/15**, 0/15, **1/15** |
| 21 | full6, `--no-fail-fast` | 16 | 83 → 16 | **FAIL** `sandbox_preflight…` (known: 1) |
| 22 | full7, full8 | 16 | 16 → 31, 31 → 33 | ok, ok (known: 2) |
| 23 | `<bin> -q &` plus a 25 s `lsof` timing sampler | 16 | 27 → 56 | `lsof` median 70 ms, max 241 ms; `detached_daemon…` **FAIL** (inherited SIGINT ignore) (known: 1) |
| 24 | `detached_daemon…`: normal SIGINT / SIGINT ignored | 16 | 76 | ok 0.38 s / **FAIL** 60.35 s |

## Checked and found stable

- **cc key inputs that don't matter:**
  - The current directory, including the temp directory `lock.enter()` moves into, when `OUT_DIR` is unset. The key does not depend on where the checkout lives.
  - 13 other env vars (`SOURCE_DATE_EPOCH`, `CPATH`, `LANG`, `PATH`, `KACHE_CACHE_DIR` and others).
  - The probe-record cache and the include-directory listing cache.
- **cc module:** apart from #1 and #4, nothing failed in 200 module runs, other than the instrumentation artifact.
- **Integration tests:** apart from `fallback_recovery_test`, every integration-test binary passed in all 8 full runs, including 2 runs with 32 CPU-hogging processes (load up to 255).
- **Kache unit tests:** apart from #1, #2 and the self-inflicted #7, no failures in 40 runs plus 8 full runs.
- **Harmless noise:** the message "error: incremental compilation: could not create session directory lock file" appears in every full run, from some test's rustc subprocess around `wrapper::tests`. The surrounding test passes.
- **Not run:** I did not force the high-risk timing sites individually. The next probe for each would be `--exact` ×50 under 32 CPU hogs, or shrinking its bound the way I did with `lsof`.

## Appendix A: instrumentation

Everything has been reverted. The full diff is at `/private/tmp/kache-flaky/opus/instrumentation.diff` and applies to `991c836` with `git apply`. Every hook is off unless its `FLAKY_*` env var is set.

- **`src/compiler/cc/tests.rs:286`, inside the known test, right after `baseline`:**
  ```rust
  let _forced = std::env::var_os("FLAKY_FORCE_SDKROOT").map(|sdk| {
      crate::config::tests::set_env_for_test("SDKROOT", Some(sdk.as_os_str()))
  });
  ```
- **`src/fallback/macos.rs:57`:** the 200 ms `lsof` deadline becomes `FLAKY_LSOF_DEADLINE_MS`, defaulting to 200.
- **Tests appended to `src/compiler/cc/tests.rs`:**
  - `zz_flaky_probe_terminal_key_perturbations` and `zz_flaky_probe_states` (gated on `FLAKY_PROBE`): print the known test's key under each env and cwd state.
  - `zz_flaky_sdkroot_toggler` (`FLAKY_TOGGLE_MS`): holds the lock and switches `SDKROOT` every 5 ms.
  - `zz_flaky_home_toggler` (`FLAKY_HOME_TOGGLE_MS`): applies `KunobiConfigGuard` every 5 ms.
  - `zz_flaky_generic_toggler` (`FLAKY_GEN_MS`, `FLAKY_GEN_VAR`, `FLAKY_GEN_VAL`, `FLAKY_GEN_CWD`): holds the lock and switches one env var, or the current directory, every 3 ms.
- **Test appended to `src/build_script.rs`:** `zz_flaky_first_protected_call_under_home_override` (`FLAKY_HOME_POISON`) makes the first `find_target_dirs` call while `KunobiConfigGuard` has `HOME` overridden.

Raw logs are in `/private/tmp/kache-flaky/opus/`: `full1.log` to `full8.log`, `binloop.log`, `expC_fails.txt`, `expC2_fails.txt` and `lsof_bg_bin.log`.