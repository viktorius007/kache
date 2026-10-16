# Cross-model assessment of flaky-test findings: kache workspace (assessor: sol)

- Worktree: `/Users/viktor/Developer/github/kache-investigations/flaky-assess-sol`, detached at `991c83694c056119d8eba8f9c1f376ac246efb52`.
- Platform: macOS, 16 logical CPUs; libtest therefore used 16 threads unless a command below supplied `--test-threads`.
- Full-workspace budget used: 1/4 runs.
- Instrumentation: `/private/tmp/kache-flaky/opus/instrumentation.diff` was applied only for the forced probes, then reversed. Final `git status --short` and `git diff --check` were empty.

## 1. `compiler::cc::tests::a_key_from_before_the_input_race_fixes_is_never_todays`

**Test path:** `src/compiler/cc/tests.rs:310`

**Verdict: REAL**

**Severity: low.** I obtained a failure without instrumentation when the test was paired with the real sibling writer, but neither my canonical full-workspace run nor the investigator's eight full runs failed this test. This is a real race with a small full-suite scheduling window, not a rate likely to fail an ordinary contributor run frequently.

**Claim tested:** The two cache-key computations can observe different process environment values because this test does not take `process_state_test_lock` while sibling tests change `SDKROOT` and related key inputs.

**Evidence:**

- The test computes `today`, immediately recomputes the key, and compares them without taking the process-state lock (`src/compiler/cc/tests.rs:339-343`).
- The key path reads the current directory and `KACHE_CC_PATH_NORMALIZE`, `KACHE_BASE_DIR`, `SDKROOT`, and `OUT_DIR` (`src/compiler/cc.rs:4389-4411`), then reads `KACHE_BASE_DIR`, `SDKROOT`, and `OUT_DIR` again while constructing maps (`src/compiler/cc.rs:4441-4460`). The maps and mapped source paths are hashed at `src/compiler/cc.rs:6933-6936` and `src/compiler/cc.rs:7108-7112`.
- The forced reproduction used the investigator's opt-in SDKROOT toggler: `env -u OUT_DIR FLAKY_TOGGLE_MS=1000 <instrumented-bin> --test-threads=4 compiler::cc::tests::a_key_from_before_the_input_race_fixes_is_never_todays compiler::cc::tests::zz_flaky_sdkroot_toggler`. It failed 6/10 runs at one-minute loads 14.68-15.81.
- More importantly, the uninstrumented binary, with the actual committed sibling writer and no hook or artificial sleep, failed 7/100: `env -u OUT_DIR <unmodified-bin> --test-threads=2 compiler::cc::tests::a_key_from_before_the_input_race_fixes_is_never_todays compiler::cc::tests::include_dir_digest_exempts_an_existing_sdkroot_directory`. One-minute loads were 16.79-18.89. The real writer sets `SDKROOT` at `src/compiler/cc/tests.rs:6985`, does filesystem/digest work while it remains set, and removes it at `src/compiler/cc/tests.rs:6990`.
- Representative uninstrumented failure output, verbatim:

```text
thread 'compiler::cc::tests::a_key_from_before_the_input_race_fixes_is_never_todays' (153734983) panicked at src/compiler/cc/tests.rs:340:5:
assertion `left == right` failed
  left: "6a5dd9ebc2a33d878f7a0ea2cb8942db35b71cc3b4bbf8aca8d1ea4a8d5ae4d7"
 right: "ec170f0d4c633cc97b1a38b9c75e0ee2cbe2781647e22b1dca0817e436d3899a"
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**Difference from the investigator:** I agree on the mechanism and the lock/snapshot fix shape. My evidence is stronger than the report's forced-only result because the committed writer reproduced the failure without instrumentation. I retain the investigator's low severity because the filtered pair deliberately maximizes overlap and the canonical full suite passed.

## 2. `path_normalizer::tests::from_env_construction_is_deterministic`

**Test path:** `src/path_normalizer.rs:2793`

**Verdict: REAL**

**Severity: low.** The committed current-directory writer caused frequent failures when paired directly, but this test passed my canonical full-workspace run and all eight investigator full runs. The full suite normally places the most obvious writers far from this test; a long OS scheduling gap is needed to preserve their overlap.

**Claim tested:** The two `PathNormalizer::from_env` calls can see different current directories or environment values while other tests mutate process-global state.

**Evidence:**

- `PathNormalizer::from_env` reads `KACHE_BASE_DIR` at `src/path_normalizer.rs:232` and the process current directory at `src/path_normalizer.rs:239-246`. The test calls it twice without taking the process-state lock (`src/path_normalizer.rs:2798-2800`) and compares the complete rule lists at `src/path_normalizer.rs:2811`.
- The investigator's current-directory forcing was reproduced with `FLAKY_GEN_MS=600 FLAKY_GEN_CWD=1 <instrumented-bin> --test-threads=4 path_normalizer::tests::from_env_construction_is_deterministic compiler::cc::tests::zz_flaky_generic_toggler`: 7/10 failed at one-minute loads 15.81-17.18.
- The investigator's environment forcing was reproduced with `FLAKY_GEN_MS=600 FLAKY_GEN_VAR=KACHE_BASE_DIR FLAKY_GEN_VAL=/tmp/flaky-base` and the same two tests: 2/10 failed at one-minute loads 17.18-18.05.
- The current-directory arm also failed without instrumentation. I paired the subject with `compiler::cc::tests::out_dir_and_sdk_maps_follow_the_environment_and_the_normalize_switch`; 65/100 runs failed with two threads at one-minute load 18.18. That real test calls `lock.enter()` at `src/compiler/cc/tests.rs:7963-7964`; `ProcessStateTestGuard::enter` changes the process current directory at `src/test_support.rs:26-29`, and its `Drop` restores it at `src/test_support.rs:33-40`.
- A real environment writer also exists without instrumentation: `build_script::tests::a_base_dir_keys_the_same_across_checkouts_only_in_remapping_flags` sets `KACHE_BASE_DIR` at `src/build_script.rs:2805` and removes it at `src/build_script.rs:2812`. A direct uninstrumented pair was 0/50 at two threads and one-minute loads 20.56-21.39, so that natural window is narrower than the current-directory arm; the forced result establishes causation when the transition lands between the two reads.
- Representative uninstrumented current-directory failure output, verbatim:

```text
thread 'path_normalizer::tests::from_env_construction_is_deterministic' (153742467) panicked at src/path_normalizer.rs:2811:9:
assertion `left == right` failed
  left: [("/Users/viktor/Developer/github/kache-investigations/flaky-assess-sol", "<WORKSPACE>"), ("/private/var/folders/wq/48xldn_s09x1lqc7t7m16q7w0000gp/T/.tmpcEVd4w", "<WORKSPACE>"), ("/var/folders/wq/48xldn_s09x1lqc7t7m16q7w0000gp/T/.tmpcEVd4w", "<WORKSPACE>"), ("/Users/viktor/.cargo", "<CARGO_HOME>"), ("/Users/viktor/.rustup", "<RUSTUP_HOME>"), ("/Users/viktor", "<HOME>"), ("/private/var/folders/wq/48xldn_s09x1lqc7t7m16q7w0000gp/T", "<TMPDIR>")]
 right: [("/private/var/folders/wq/48xldn_s09x1lqc7t7m16q7w0000gp/T/.tmpDaJ0Vi", "<WORKSPACE>"), ("/private/var/folders/wq/48xldn_s09x1lqc7t7m16q7w0000gp/T/.tmpcEVd4w", "<WORKSPACE>"), ("/var/folders/wq/48xldn_s09x1lqc7t7m16q7w0000gp/T/.tmpcEVd4w", "<WORKSPACE>"), ("/Users/viktor/.cargo", "<CARGO_HOME>"), ("/Users/viktor/.rustup", "<RUSTUP_HOME>"), ("/Users/viktor", "<HOME>"), ("/private/var/folders/wq/48xldn_s09x1lqc7t7m16q7w0000gp/T", "<TMPDIR>")]
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**Difference from the investigator:** I agree on the mechanism and on snapshotting or locking as the fix shape. I add an uninstrumented committed-writer reproduction for the current-directory arm. I keep severity low rather than extrapolating the 65% filtered-pair rate to the normal full suite.

## 3. `compiler::nvcc::tests::execute_drops_artifacts_when_object_embeds_mapped_root`

**Test path:** `src/compiler/nvcc.rs:2299`

**Verdict: REAL**

**Severity: low.** This meets the requested forced-plus-real-sibling-writer standard, but I observed 0/100 failures in the direct real-writer pair, 0/100 in the unmodified nvcc module at 16 threads, and 0/1 in the canonical full workspace. It is a static, extremely narrow scheduling risk.

**Claim tested:** A sibling test can set `KACHE_NVCC_PATH_NORMALIZE=0` while this test executes, causing `NvccCompiler::execute` to build no prefix maps and retain the object artifact that the assertion expects to be dropped.

**Evidence:**

- `nvcc_path_normalize_enabled` reads `KACHE_NVCC_PATH_NORMALIZE` at `src/compiler/nvcc.rs:873-875`; `nvcc_prefix_maps` immediately returns an empty vector when disabled at `src/compiler/nvcc.rs:899-906`.
- `NvccCompiler::execute` obtains those maps at `src/compiler/nvcc.rs:1250`, and only drops the object if it embeds one of those maps at `src/compiler/nvcc.rs:1306-1315`. Empty maps therefore leave the produced artifact present and make the assertion at `src/compiler/nvcc.rs:2327-2336` fail.
- The investigator's forced reproduction was rerun as `FLAKY_GEN_MS=600 FLAKY_GEN_VAR=KACHE_NVCC_PATH_NORMALIZE FLAKY_GEN_VAL=0 <instrumented-bin> --test-threads=4 compiler::nvcc::tests::execute_drops_artifacts_when_object_embeds_mapped_root compiler::cc::tests::zz_flaky_generic_toggler`: 11/15 failed at one-minute loads 16.29-17.16.
- The same forced condition exists in committed code: `compiler::nvcc::tests::normalize_disabled_by_knob` takes the writer-side lock and sets `KACHE_NVCC_PATH_NORMALIZE=0` at `src/compiler/nvcc.rs:2211-2216`, reads prefix maps, then restores/removes the variable at `src/compiler/nvcc.rs:2217-2224`. The subject does not take that lock. In libtest's unmodified list the subject and writer are 11 entries apart, inside the normal 16-thread scheduling width.
- Natural-rate probes were negative: the unmodified two-test pair was 0/100 at two threads and one-minute load 16.51; the whole unmodified `compiler::nvcc::tests` module was 0/100 at 16 threads and one-minute loads 14.48-14.60; the canonical full workspace also passed.
- Forced failure output, verbatim:

```text
thread 'compiler::nvcc::tests::execute_drops_artifacts_when_object_embeds_mapped_root' (153636781) panicked at src/compiler/nvcc.rs:2327:9:
an object that embeds a mapped root must not be cached, got ["/var/folders/wq/48xldn_s09x1lqc7t7m16q7w0000gp/T/.tmpmWHR38/k.o"]
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

**Difference from the investigator:** I agree on the mechanism and lock/snapshot fix shape. My observed forced rate was higher (11/15 rather than 1/15), but the real-writer and module probes were both 0/100, reinforcing the investigator's low severity rather than suggesting a contributor-visible rate.

## 4. `daemon::tests::detached_daemon_survives_sigint_to_the_callers_group`

**Test path:** `src/daemon/tests.rs:151`

**Verdict: NOT A FLAKE**

**Severity: low.** The failure requires the test launcher to install `SIG_IGN` for SIGINT. Under the supplied verdict definition, a failure caused by the launch environment rather than by an unmodified suite state is NOT A FLAKE.

**Claim tested:** The helper inherits SIGINT ignored from a parent that launched the test with that disposition, so the group-directed SIGINT does not terminate the caller fixture.

**Evidence:**

- The test spawns the caller fixture without resetting signal dispositions at `src/daemon/tests.rs:169-179`, sends SIGINT to its process group at `src/daemon/tests.rs:200`, waits for it, and asserts that the exit was unsuccessful at `src/daemon/tests.rs:208`.
- A normal direct run passed in 0.44 s at load `{ 14.78 29.15 46.69 }`.
- A Python parent that executed `signal.signal(signal.SIGINT, signal.SIG_IGN)` before `execv` reproduced the report exactly: 1/1 failed after 60.40 s at the same sampled load. This is a parent-launcher condition; it is neither instrumentation nor a state produced by another test.
- Failure output, verbatim:

```text
thread 'daemon::tests::detached_daemon_survives_sigint_to_the_callers_group' (153649148) panicked at src/daemon/tests.rs:208:5:
SIGINT never reached the caller's group
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

- The canonical resource wrapper foreground-`exec`s its command on every path (`scripts/with-test-resources.sh:47`, `:53`, and `:79`); it does not set signal dispositions. CI also invokes the suite in foreground steps at `.github/workflows/ci.yml:124` and `.github/workflows/ci.yml:1402-1405`. My canonical unmodified full-workspace run passed this test.
- A non-interactive shell may deliberately start a background job with SIGINT ignored, but that is precisely the external launch-environment case excluded by the NOT A FLAKE definition. Nothing in the canonical command or CI creates it.

**Difference from the investigator:** I agree that inherited `SIG_IGN` is the mechanism and that resetting SIGINT in the fixture would harden the test. I disagree with classifying it as a suite flake or medium severity: the report's only failure was caused by how the investigator launched the binary, and the requested rubric explicitly assigns launch-environment failures to NOT A FLAKE.

## Run table

`<instrumented-bin>` is `/private/tmp/kache-flaky/sol/target/debug/deps/kache-6e34f88e8d8cfb8d` while the opt-in diff was applied. `<unmodified-bin>` is `/private/tmp/kache-flaky/sol/target/debug/deps/kache-881bf021f508393b`. Every repetition was preceded by `sysctl -n vm.loadavg`; ranges below summarize the observed one-minute component unless braces show the complete sample.

| Command | Threads | Load | Result |
|---|---:|---|---|
| `CARGO_TARGET_DIR=/private/tmp/kache-flaky/sol/target cargo test --workspace --no-run` after applying instrumentation | n/a | `{ 24.07 36.91 51.73 }` | build passed |
| Finding 1 + SDKROOT toggler, 10 repetitions | 4 | 14.68-15.81 | 6/10 failed |
| Finding 2 + generic cwd toggler, 10 repetitions | 4 | 15.81-17.18 | 7/10 failed |
| Finding 2 + generic `KACHE_BASE_DIR` toggler, 10 repetitions | 4 | 17.18-18.05 | 2/10 failed |
| Finding 3 + generic `KACHE_NVCC_PATH_NORMALIZE=0` toggler, 15 repetitions | 4 | 16.29-17.16 | 11/15 failed |
| Finding 4, normal direct run | 16 (1 selected) | `{ 14.78 29.15 46.69 }` | passed in 0.44 s |
| Finding 4, Python parent with SIGINT ignored | 16 (1 selected) | `{ 14.78 29.15 46.69 }` | failed 1/1 in 60.40 s |
| Finding 1 + committed SDKROOT writer, unmodified, 100 repetitions | 2 | 16.79-18.89 | 7/100 failed |
| Finding 2 + committed cwd writer, unmodified, 100 repetitions | 2 | 18.18 | 65/100 failed |
| Finding 2 + committed `KACHE_BASE_DIR` writer, unmodified, 50 repetitions | 2 | 20.56-21.39 | 0/50 failed |
| Finding 3 + committed knob writer, unmodified, 100 repetitions | 2 | 16.51 | 0/100 failed |
| Unmodified `compiler::nvcc::tests`, 100 repetitions | 16 | 14.48-14.60 | 0/100 failed |
| `CARGO_TARGET_DIR=/private/tmp/kache-flaky/sol/target ./scripts/with-test-resources.sh cargo test --workspace` | 16 | start `{ 13.09 22.75 40.70 }`; end `{ 24.44 40.83 44.79 }` | passed; all 4,460 kache unit tests and all workspace/integration/doc tests passed |

## Investigator analysis checked and found correct

- The finding 4-6 forced hooks are opt-in: with their `FLAKY_*` variables absent, the added tests return or the production deadline retains its original default. The diff applied cleanly to `991c836` and reversed cleanly.
- Finding 4's two hashes map to the SDKROOT-present versus SDKROOT-absent cache-key states; the exact `6a5dd9eb...`/`ec170f0d...` mismatch reproduced both with the toggler and with the committed sibling writer.
- Finding 5 correctly identifies both inputs read by `PathNormalizer::from_env`: `KACHE_BASE_DIR` and the process current directory. Each forced perturbation produced the predicted rule-list difference.
- Finding 6 correctly traces `KACHE_NVCC_PATH_NORMALIZE=0` to an empty prefix-map set and therefore to retention of the object artifact.
- Finding 7 correctly identifies inherited SIGINT disposition rather than a timer deadline as the cause of its 60-second failure.
- The investigator's low severities for findings 4-6 are supported by the clean canonical full run and, for nvcc, the additional 0/100 real-writer and 0/100 module probes.
- The investigator's proposed fix shapes are technically appropriate: pin/snapshot or lock process state for findings 4-6, and reset SIGINT in the fixture if the project wants robustness to noncanonical launchers. No fixes were made in this assessment.