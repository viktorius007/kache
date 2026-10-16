# Rust/rustdoc wrapper, discovery, compilation, hits and diagnostics

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 17; bytes: 1310362.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- compiler-adapters-probes-and-eligibility: 8 paths, 10992 text lines; subdivide into the listed contiguous file sections when needed.
- wrapper-execution: 9 paths, 24510 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace Rust, rustdoc, C/C++ and CUDA entry paths from compiler detection through eligibility, dependency discovery, key derivation, compile/passthrough and restore; preserve compiler exit status and diagnostic/artifact behavior.
- Account for every compiler-observable input, mutation between discovery/compile/publication, prediction validity, native linking, target specs, proc macros, diagnostic flags and path normalization; compare same-input reuse across worktrees and changed-input invalidation.
- Review inline tests and regression fixtures fully; vary real observable compiler output or exit status for candidate proofs. Public degree-zero methods are not evidence of dead code.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- compiler-store-hit: consult store-core; wrapper/hit/compile → kache-store/compile preclean; output completeness, diagnostics, mtimes, carrier isolation
- rust-cc-dispatch: consult cc-cuda-adapters; wrapper.run_cc/run_nvcc dispatch and generic adapter interface ↔ concrete compiler execution and restore

## Sampling declarations

- macOS host: Linux/Windows linking, filesystem and compiler-specific behavior require source review plus declared execution limits.
- Rust focus does not permit silently skipping C/C++/CUDA/rustdoc; name every unexecuted toolchain branch.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `docs/getting-started/rustdoc.mdx` (contract-doc-or-ci; 2513 bytes; 60 text lines)
- `src/args.rs` (source-or-script; 110060 bytes; 2802 text lines)
- `src/compile.rs` (source-or-script; 69397 bytes; 1847 text lines)
- `src/compiler/rustc.rs` (source-or-script; 67524 bytes; 1779 text lines)
- `src/compiler/rustdoc.rs` (source-or-script; 115915 bytes; 3371 text lines)
- `src/verify_compare.rs` (source-or-script; 33984 bytes; 933 text lines)
- `src/wrapper.rs` (source-or-script; 363755 bytes; 9255 text lines)
- `src/wrapper/hit.rs` (source-or-script; 1757 bytes; 44 text lines)
- `src/wrapper/remote.rs` (source-or-script; 2628 bytes; 81 text lines)
- `src/wrapper/rustc_hit.rs` (source-or-script; 2253 bytes; 68 text lines)
- `src/wrapper/tests.rs` (test-or-fixture; 415598 bytes; 11617 text lines)
- `src/wrapper/tests/hit.rs` (test-or-fixture; 7497 bytes; 213 text lines)
- `src/wrapper/tests/rustc_hit.rs` (test-or-fixture; 14777 bytes; 452 text lines)
- `tests/cached_units_regression_test.rs` (test-or-fixture; 63586 bytes; 1796 text lines)
- `tests/macos_adaptive_debug_info_test.rs` (test-or-fixture; 10935 bytes; 282 text lines)
- `tests/metadata_streaming_test.rs` (test-or-fixture; 3697 bytes; 106 text lines)
- `tests/stale_artifact_test.rs` (test-or-fixture; 24486 bytes; 796 text lines)
