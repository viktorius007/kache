STATUS: DONE
COMMIT: none
CHANGED: 518
OPEN: 5
BLOCKERS: none
CONFIRMED: 5
LIMITS: macOS arm64, rustc1.99/rustdoc1.98.1+1.99; partial semantic graph; dedicated suites sampled; Linux/Windows and real C/C++/CUDA execution omitted
---

Pinned source baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Five confirmed defects have real compiler controls, full red-test source, exact assertion failures, isolated stores and executable replay manifests. Production and committed test source remain unchanged. `OPEN: 5` counts the admitted findings awaiting owner disposition; there are no blocked requirements or additional findings inferred from unexecuted branches.

The CLI used is the coordinator's untouched baseline `target/debug/kache`, read-only throughout. Its SHA256 and compiler versions are saved in `evidence/baseline-binary.sha256`, `evidence/rustc-version.txt` and `evidence/rustdoc-version.txt`. All fixture homes, configuration, output, cache stores and logs are below this worktree's `investigation/`. No installed Kache, user configuration, real cache, launchd state or repository production file was changed. No build of Kache or dependencies was needed.

**Confirmed findings**

1. **rust-wrapper-002 — requested metadata file absent after a successful hit.** At `src/args.rs:324-331`, parsing retains `metadata` but drops its `--emit=metadata=PATH` destination. At `src/wrapper.rs:5433-5441`, hit placement uses the cached producer filename. Cold `out/first.rmeta` → remove outputs → request `out/second.rmeta` yields a local hit with exit 0 and only `first.rmeta`; direct rustc creates `second.rmeta`. Both keys were `7c910d2f64da578c81001f458c018fa87740754d84c2da3faf1cbbe6af5078b1`. This affects direct rustc/custom build systems using per-emit output destinations. The probe proves metadata; other explicit emit kinds are not claimed. Evidence: `evidence/emit-destination-red.log`, `evidence/emit-destination-observations.json`, `emit-destination-jexm3fcz/`, and `replay-cases/emit-destination.json`.

2. **rust-wrapper-003 — nested module edits return stale documentation.** For `lib.rs → foo.rs → foo/child.rs`, `collect_source` resolves the child against the parent of `foo.rs`, losing Rust's implicit `foo/` module directory (`src/compiler/rustdoc.rs:343-372`). Missing root `child.rs`/`child/mod.rs` is skipped. The key hashes this incomplete list (`198-208`). Changing the child's docs from OLD_MARKER to NEW_MARKER, deleting output/parts and rerunning yields a same-key hit with OLD_MARKER; direct rustdoc produces NEW_MARKER. Evidence: `evidence/rustdoc-nested-1.98-red.log`, `evidence/rustdoc-nested-observations.json`, `rustdoc-nested-f8vldfxl/`, and `replay-cases/rustdoc-nested.json`.

3. **rust-wrapper-004 — outer documentation includes return stale text.** `scan_rust` skips an outer attribute after optional `path` handling (`src/compiler/rustdoc.rs:478-491`). A public function with `#[doc = include_str!("README.md")]` therefore omits README from the key. Change OLD_MARKER → NEW_MARKER in README and delete output/parts: the hit restores OLD_MARKER while direct rustdoc produces NEW_MARKER. This has a separate root cause from module directory resolution. Evidence: `evidence/rustdoc-outer-include-1.98-red.log`, `evidence/rustdoc-outer-include-observations.json`, `rustdoc-outer_doc_include-fhdrvd59/`, and `replay-cases/rustdoc-outer-include.json`.

4. **rust-wrapper-005 — env! documentation returns stale environment text.** The source list explicitly does not read compiler dep-info (`src/compiler/rustdoc.rs:273-280`), and environmental key folding uses only configured `key_env_vars` (`253-262`). Source `#![doc = env!("DOC_TEXT")]`, unchanged flags/files and DOC_TEXT OLD_MARKER → NEW_MARKER yield a same-key hit containing OLD_MARKER, while direct rustdoc produces NEW_MARKER. This affects environment-derived docs without manual declarations. Configured key_env_vars is a possible narrow workaround, not an executed fix. Evidence: `evidence/rustdoc-env-1.98-red.log`, `evidence/rustdoc-env-observations.json`, `rustdoc-env-elv8ztz4/`, and `replay-cases/rustdoc-env.json`.

5. **rust-wrapper-001 — JSON diagnostics request replays human text.** `src/args.rs:16-33,653-660` drops diagnostic format flags from key inputs, while `src/wrapper.rs:7063-7082` replays stored text verbatim. Cold successful rlib with an unused-variable warning in human format → remove outputs → JSON request yields successful same-key hit and human stderr. Direct rustc emits JSON. Both keys were `61e920f22008784e0c495a19d600828c812294008d4c814278b02c3066b2bf89`; compiler_runs was 1 cold and 0 warm. Artifact bytes can be correct while a JSON diagnostic consumer receives the wrong protocol. Color/width/notification variants were source-read but not independently proved. Evidence: `evidence/diagnostic-format-red.log`, `evidence/diagnostic-format-observations.json`, `diagnostic-j73zrskb/`, and `replay-cases/diagnostic-format.json`.

Rustdoc findings affect the explicitly eligible per-crate mode `--merge=none --parts-out-dir ...`; real rustdoc1.98.1 and direct rustdoc1.99 both reproduced all three. `RUSTC_BOOTSTRAP=1` enables the required unstable rustdoc options. The assigned contract document `docs/getting-started/rustdoc.mdx:6-17,52-60` states plain cargo doc passes through and Cargo1.99's newer meta flags are unsupported/pass through. These results do not claim ordinary Cargo1.99 documentation builds are cached. No Cargo invocation is substituted for the real rustdoc controls.

The ordering prioritizes a missing promised build output, then wrong rendered documentation, then developer diagnostic protocol. The three documentation findings tie on audience severity; their order is arbitrary. Each assertion varies real source/environment/options and compares to independent direct compiler output, rather than reusing the cache key algorithm as its oracle.

**Replay and controls**

Run `python3 investigation/replay.py` from this worktree. It loads the five `replay-cases/*.json` manifests, runs their argv arrays with a 100-second bound, saves complete output, and requires exit 1 plus both named regex matches. `evidence/replay-results.json` records five matching failures. A replay failure here is the expected red proof; the dispatcher exits 0 only when every named defect reproduces. Each underlying probe performs cold/warm/direct calls, checks all compiler calls succeeded, and then fails on the wrong externally observable output.

The full source is in `probes/diagnostic_format.py`, `probes/emit_destination.py` and `probes/rustdoc_inputs.py`, also embedded under each finding's `proof.red_test` in `findings.json`. Replay assumes the pinned baseline CLI and installed toolchains remain at their recorded paths; no production hooks or edits are needed. Later fixing any finding should make its precise baseline assertion pass, at which point this audit's expected-red dispatcher should be revised for a fix verifier.

A meaningful dismissed lead is the **inner** crate attribute `#![doc = include_str!("README.md")]`. Its changed file caused a different key and wrapped/direct NEW_MARKER output, on rustdoc1.99 and 1.98.1. The original evidence is `rustdoc-doc_include-gvpj0yqu/` and `evidence/rustdoc-inner-include-control-observations.json`; the supported-toolchain control is `evidence/rustdoc-inner-include-1.98-green.log` and `rustdoc-doc_include-0wb1q8c4/`. This dismissal covers that syntax only and does not excuse the outer attribute finding.

**Source coverage and execution limits**

Every assigned production path and all inline test modules were read fully. The dedicated `src/wrapper/tests.rs` and `tests/cached_units_regression_test.rs` suites were deliberately sampled. `coverage.json` contains one record for every primary path, exact reviewed/omitted ranges and reopen conditions. Runtime coverage is not implied by source read. No full cargo test suite or mutation run was executed.

| Primary path | Source depth |
| --- | --- |
| docs/getting-started/rustdoc.mdx | Full 1–60 |
| src/args.rs | Full 1–2802, production and inline tests |
| src/compile.rs | Full 1–1847, production and inline tests |
| src/compiler/rustc.rs | Full 1–1779, production and inline tests |
| src/compiler/rustdoc.rs | Full 1–3371, production and inline tests |
| src/verify_compare.rs | Full 1–933, production and inline tests |
| src/wrapper.rs | Full 1–9255, including C/C++/CUDA dispatch |
| src/wrapper/hit.rs | Full 1–44 |
| src/wrapper/remote.rs | Full 1–81 |
| src/wrapper/rustc_hit.rs | Full 1–68 |
| src/wrapper/tests.rs | Sampled ranges below |
| src/wrapper/tests/hit.rs | Full 1–213 |
| src/wrapper/tests/rustc_hit.rs | Full 1–452 |
| tests/cached_units_regression_test.rs | Sampled ranges below |
| tests/macos_adaptive_debug_info_test.rs | Full 1–282 |
| tests/metadata_streaming_test.rs | Full 1–106 |
| tests/stale_artifact_test.rs | Full 1–796 |

`src/wrapper/tests.rs` reviewed ranges: 1–220 (prediction/fixture state), 1820–1884 (deferred compile exit), 2689–2752 (diagnostic replay), 6826–7051 (CUDA hits/input changes/depinfo), 7329–7670 (CUDA failure/key/env/qualification), 8313–8368 (emit completeness), 9094–9157 (partial-entry rejection), 9270–9512 (unsafe artifacts/staging/verification), 10244–10448 (CC qualifications/durability/publication), 10620–11006 (discovery/input/declared-input guards). Exact omitted ranges: 221–1819, 1885–2688, 2753–6825, 7052–7328, 7671–8312, 8369–9093, 9158–9269, 9513–10243, 10449–10619, 11007–11617. Function names elsewhere were navigation, not review credit.

`tests/cached_units_regression_test.rs` reviewed 1–489 (helpers, concurrent jobs, emitted-depinfo/module edit, re-exported proc-macro input) and 969–1053 (Clippy diagnostics/lint options). Omitted 490–968 and 1054–1796 (build-script/native archive/hermetic OUT_DIR sub-suites). Neighboring cargo/build-input and key/native agents own those seams; the omission still limits this slice's independent test review.

Structural exploration used the required codebase-memory skill and pinned coordinator graph `Users-viktor-Developer-github-kache-investigations-coordinator`. `evidence/graph-status.json` records ready index status with Rust `semantic_partial`: unavailable binding oracle, expanded calls and impl relationships; numerous unresolved calls/references. Graph search identified entry/test locations; full source read supplied the consequential wiring evidence. No negative/dead-code finding depends on an incomplete graph. `.cargo` is not indexed; YAML parse coverage is partial. Collateral reads of `src/cache_key.rs` included diagnostic/key groups around 2950–3035 and searches for diagnostic flags; this is consultation, not primary ownership or a full-file review.

Real runtime scope is macOS arm64 with rustc1.99 and rustdoc1.98.1/1.99, local synchronous publication and isolated stores. The Rust miss/hit/restore diagnostics and metadata output paths, and rustdoc crate miss/hit/archive reuse are executed. Remote daemon/publish cancellation, readonly stores, CUDA toolkit behavior, C/C++ compilers and linking, Linux/Windows filesystems/linking, native/proc-macro build closure races, scheduler flight contention, Rust adaptive backtraces and metadata streaming were source-read where assigned but not executed here. CUDA unit tests sampled above use their existing fake driver; reading them is not execution on a real toolkit. There is no broad correctness/performance conclusion from the tiny fixtures.

Consultations: cargo-build independently executed its declared-env/proc-macro adaptive lead green on rustc1.99 and retained narrow reopening conditions; no finding is duplicated here. CC/CUDA adapters received the unproved wrapper publication-without-lock lead and recorded real-toolkit/concurrency execution as unresolved in their coverage; it is not admitted here. The contract-conformance agent owns a distinct, mechanically replayed default-bin/cache_executables policy defect (`CONTRACT-BIN-001`) at `../audit-contract-conformance/investigation/report.md`; this report does not duplicate it. No finding is inferred merely because an error/branch remains unexecuted.
