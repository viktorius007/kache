# Cargo, build scripts, incremental, fallback and test reuse

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 51; bytes: 1153434.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- build-script-execution-and-declarations: 8 paths, 10914 text lines; subdivide into the listed contiguous file sections when needed.
- cargo-incremental-fallback-test-and-shims: 43 paths, 20071 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace Cargo shim and wrapper chains, argument/environment overrides, manifest/target/Cargo-home identities, build directory isolation, inherited jobserver behavior and compile/test child lifetimes.
- Trace build-script installation, launch fallback, declared file/environment inputs, package walks, hermetic out directories, replayed outputs outside OUT_DIR, symlinks, permissions and paths across relocation.
- Trace adaptive incremental state, seed-to-incremental transitions, explicit user controls, fallback wrappers and test-result reuse; inspect cancellation, stdout drains and side effects under isolated fixtures.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- compiler-build-inputs: consult rust-wrapper; build_script_inputs/extra_inputs/incremental_policy → Rust key/prediction decisions; declarations and mutation validation

## Sampling declarations

- Build-script arbitrary external probes/side effects need declared scope; fixture subprocesses and cancellation paths can be exercised without real homes.
- Cargo and Rust version combinations need explicit tested versions; no general compatibility claim from one installed toolchain.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `crates/kache-shims/Cargo.toml` (config-or-delivery-collateral; 787 bytes; 26 text lines)
- `crates/kache-shims/README.md` (contract-doc-or-ci; 1606 bytes; 25 text lines)
- `crates/kache-shims/proptest-regressions/select/tests.txt` (config-or-delivery-collateral; 1352 bytes; 11 text lines)
- `crates/kache-shims/src/farm.rs` (source-or-script; 17603 bytes; 550 text lines)
- `crates/kache-shims/src/farm/tests.rs` (test-or-fixture; 31290 bytes; 990 text lines)
- `crates/kache-shims/src/fs.rs` (source-or-script; 7303 bytes; 229 text lines)
- `crates/kache-shims/src/lib.rs` (source-or-script; 449 bytes; 15 text lines)
- `crates/kache-shims/src/select.rs` (source-or-script; 19368 bytes; 578 text lines)
- `crates/kache-shims/src/select/tests.rs` (test-or-fixture; 35890 bytes; 1030 text lines)
- `docs/how-it-works/build-scripts.mdx` (contract-doc-or-ci; 16448 bytes; 284 text lines)
- `launcher/build_script.rs` (source-or-script; 9993 bytes; 261 text lines)
- `src/build_script.rs` (source-or-script; 206835 bytes; 5063 text lines)
- `src/build_script/declarations.rs` (source-or-script; 5873 bytes; 163 text lines)
- `src/build_script/hermetic.rs` (source-or-script; 54411 bytes; 1412 text lines)
- `src/build_script/inputs.rs` (source-or-script; 36394 bytes; 981 text lines)
- `src/build_script/outside.rs` (source-or-script; 45212 bytes; 1243 text lines)
- `src/build_script_inputs.rs` (source-or-script; 22294 bytes; 598 text lines)
- `src/build_script_inputs/tests.rs` (test-or-fixture; 42294 bytes; 1193 text lines)
- `src/cargo_env.rs` (source-or-script; 8697 bytes; 259 text lines)
- `src/cargo_layout.rs` (source-or-script; 16424 bytes; 441 text lines)
- `src/cargo_proxy.rs` (source-or-script; 64414 bytes; 1780 text lines)
- `src/fallback.rs` (source-or-script; 7229 bytes; 231 text lines)
- `src/fallback/macos.rs` (source-or-script; 7187 bytes; 207 text lines)
- `src/fallback/sandbox.rs` (source-or-script; 6191 bytes; 194 text lines)
- `src/incremental_policy.rs` (source-or-script; 96179 bytes; 2531 text lines)
- `src/out_dir_alias.rs` (source-or-script; 82018 bytes; 2174 text lines)
- `src/test_runner.rs` (source-or-script; 25405 bytes; 715 text lines)
- `src/test_runner/delegate.rs` (source-or-script; 43090 bytes; 1163 text lines)
- `test-projects/custom-harness/Cargo.lock` (license-or-lock-collateral; 158 bytes; 7 text lines)
- `test-projects/custom-harness/Cargo.toml` (test-or-fixture; 468 bytes; 15 text lines)
- `test-projects/custom-harness/src/lib.rs` (test-or-fixture; 34 bytes; 3 text lines)
- `test-projects/custom-harness/tests/harness.rs` (test-or-fixture; 223 bytes; 7 text lines)
- `test-projects/hello-world/Cargo.lock` (license-or-lock-collateral; 155 bytes; 7 text lines)
- `test-projects/hello-world/Cargo.toml` (test-or-fixture; 153 bytes; 7 text lines)
- `test-projects/hello-world/src/main.rs` (test-or-fixture; 62 bytes; 3 text lines)
- `test-projects/stale-check/Cargo.lock` (license-or-lock-collateral; 155 bytes; 7 text lines)
- `test-projects/stale-check/Cargo.toml` (test-or-fixture; 176 bytes; 10 text lines)
- `test-projects/stale-check/src/helper.rs` (test-or-fixture; 58 bytes; 3 text lines)
- `test-projects/stale-check/src/lib.rs` (test-or-fixture; 440 bytes; 27 text lines)
- `test-projects/stale-check/src/main.rs` (test-or-fixture; 236 bytes; 10 text lines)
- `tests/adaptive_incremental_test.rs` (test-or-fixture; 38229 bytes; 1065 text lines)
- `tests/adaptive_incremental_workspace_test.rs` (test-or-fixture; 27655 bytes; 710 text lines)
- `tests/build_script_declared_inputs_test.rs` (test-or-fixture; 20761 bytes; 552 text lines)
- `tests/build_script_inputs_test.rs` (test-or-fixture; 6218 bytes; 188 text lines)
- `tests/build_script_launcher_test.rs` (test-or-fixture; 4218 bytes; 127 text lines)
- `tests/cargo_proxy_test.rs` (test-or-fixture; 52374 bytes; 1365 text lines)
- `tests/custom_harness_test.rs` (test-or-fixture; 8560 bytes; 224 text lines)
- `tests/fallback_recovery_test.rs` (test-or-fixture; 13025 bytes; 377 text lines)
- `tests/incremental_passthrough_test.rs` (test-or-fixture; 18005 bytes; 522 text lines)
- `tests/out_dir_alias_test.rs` (test-or-fixture; 24217 bytes; 683 text lines)
- `tests/test_runner_test.rs` (test-or-fixture; 25618 bytes; 719 text lines)
