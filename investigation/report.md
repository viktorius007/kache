STATUS: DONE
COMMIT: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9
CHANGED: 20 files
OPEN: 1 unresolved item
BLOCKERS: none
CONFIRMED: 1
LIMITS: macOS Cargo/rustc 1.99.0; large test modules sampled; force-list seam only; cancellation/concurrent cleanup and other platforms not executed
---

The cargo-build audit confirms one silent cache correctness defect at the untouched baseline. No production source was repaired or changed. All 51 assigned primary paths are accounted for in coverage.json; production portions were read in full, with exact bounds for deliberately sampled large test modules. findings.json carries the complete admitted record and three meaningful dismissals.

`cargo-build-001`: Surrounding whitespace on a valid Cargo rerun environment declaration drops that variable from the build-script run key. A real dependency-free build.rs prints `  cargo:rerun-if-env-changed=APP_MODE  ` plus a stable declared file and writes APP_MODE to OUT_DIR/value. Cargo successfully builds with APP_MODE=first, then APP_MODE=second. With baseline Kache as RUSTC_WRAPPER, both resulting executables print first. Ordinary Cargo prints first, then second. The second wrapped build logs a build_script_run local_hit with exactly the first run key.

The prediction parser in src/build_script/declarations.rs:61-97 calls rerun_directive without trimming. Its Cargo-facing parser at :39-56 does trim; the run action key at src/build_script.rs:1290-1310 folds only the retained prediction.env names. Recording calls the untrimmed parser at :1531-1548. Ordinary Cargo reaches the cache through wrapper launcher installation, main shim dispatch and run_cached. The promised rule at docs/how-it-works/build-scripts.mdx:36-53 covers every declared variable. Cargo's [custom-build implementation](https://doc.rust-lang.org/stable/nightly-rustc/src/cargo/compiler/custom_build.rs.html) trims instruction lines, and the independent direct-Cargo control demonstrates that behavior on the tested toolchain.

The consequence is silently wrong generated contents after an explicitly declared input changes, including generated configuration or bindings. Reachability uses the default build-script cache; the tested cache mode was non-hermetic. The trigger is narrower than ordinary canonical declarations: it requires surrounding whitespace. No claim is made about prevalence, hermetic mode or every toolchain. Disabling the build-script cache is an existing documented escape hatch; no fix was implemented in this audit.

The reproducible red cases are:

- proofs/cargo-declarations.py, replay contract proofs/cargo-declarations.replay.json, raw proofs/cargo-declarations.log. Exit 1 is expected at STALE_CARGO_DECLARATION_OUTPUT. Invoke with `--direct` for the ordinary-Cargo green control in cargo-declarations-control.log.
- proofs/padded-declarations.py, replay contract proofs/padded-declarations.replay.json, raw proofs/padded-declarations.log. This smaller executable launcher proof independently returns first twice after deleting the old generated value. Invoke with `--control` to remove only fixture declaration padding; padded-declarations-control.log returns first, second.

Both scripts isolate writable homes, configs, runtime directories, targets and stores. The Cargo script uses the installed rustup toolchain's actual cargo/rustc binaries and the coordinator's read-only baseline Kache at /Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache. No real home/config/cache, installed executable, launchd service or other agent's worktree was changed. Cargo probes are dependency-free, offline and single-job; they ran after the coordinator released the quiet measurement window.

The owned proc-macro/declared-input seam did not reproduce stale output in the tested case. `cargo-declarations.py --incremental` uses a canonical declared APP_MODE input and an unchanged proc-macro dependency which reads that variable. Both force-list managed compiles produced the current value. Event reasons and an explicit assertion for private incremental.kache-auto query-cache files confirm that this was a managed-path probe. Its log is proofs/incremental-declarations.log and its green replay contract is proofs/incremental-declarations.replay.json. This closes that narrow hypothesis on Rust 1.99; learned adaptive activation, other mutation shapes and other toolchains remain outside executed coverage.

Two further source leads were dismissed against concrete authority. Undeclared PATH/system probes, external side effects and transformed root values are explicitly outside the documented build-script key/replay contract (docs/how-it-works/build-scripts.mdx:268-281). Test-runner lease argument omission does not lose target identity: src/target_use.rs:31-74 uses one cache-global lock, and argv changes only quiet notice output. These are scoped dismissals, not general safety claims.

A minor CLI compatibility observation is preserved without admission to the high-value findings: `init` rejects a valid `[env] # host settings` table because src/cargo_env.rs:127 only recognizes the bare header and adds a duplicate table. Caller validation at src/cli.rs:9411-9414 rejects the edit before writing, and the fixture confirms the original config remains unchanged. See proofs/commented-env.py, its red/control logs and replay metadata. It does not demonstrate corruption or a build failure and is excluded from CONFIRMED/OPEN above.

Graph evidence is retained in graph-coverage.json for the pinned coordinator index. All 54 requested indexed paths were returned; its Rust semantics are partial because binding, expanded-call and impl relationship oracles are unavailable. Native source confirmed the important wiring. graph-coverage.log is an earlier truncated path-limit view and is not the complete scope artifact. coverage.json records six additional collateral paths and exact sampling bounds; validation.json verifies all primary paths, unchanged production diff, baseline HEAD, JSON consistency and recorded assertion matches.

No committed test suite or mutation suite was run. Existing large test files were sampled, and no coverage percentage is used as proof of integrity. Cancellation, arbitrary external side effects, concurrent cleanup, the learned adaptive lane, Linux/Windows behavior and general toolchain compatibility were not exercised. The audit does not claim those areas are green. Build/test timings in the logs are incidental fixture timings and are not performance measurements.
