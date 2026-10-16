# C/C++/CUDA compiler adapters, flags, probes and eligibility

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 32; bytes: 1172695.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- compiler-adapters-probes-and-eligibility: 32 paths, 29084 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace Rust, rustdoc, C/C++ and CUDA entry paths from compiler detection through eligibility, dependency discovery, key derivation, compile/passthrough and restore; preserve compiler exit status and diagnostic/artifact behavior.
- Account for every compiler-observable input, mutation between discovery/compile/publication, prediction validity, native linking, target specs, proc macros, diagnostic flags and path normalization; compare same-input reuse across worktrees and changed-input invalidation.
- Review inline tests and regression fixtures fully; vary real observable compiler output or exit status for candidate proofs. Public degree-zero methods are not evidence of dead code.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- cc-key-inputs: consult key-native-inputs; C/C++/CUDA classification/probes/depfiles ↔ cache key/path/native inputs; compiler-observable flags and identity

## Sampling declarations

- macOS host: Linux/Windows linking, filesystem and compiler-specific behavior require source review plus declared execution limits.
- Rust focus does not permit silently skipping C/C++/CUDA/rustdoc; name every unexecuted toolchain branch.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `docs/getting-started/c-cpp.mdx` (contract-doc-or-ci; 14366 bytes; 185 text lines)
- `docs/getting-started/cuda.mdx` (contract-doc-or-ci; 5724 bytes; 77 text lines)
- `src/compiler/cc.rs` (source-or-script; 333196 bytes; 7856 text lines)
- `src/compiler/cc/tests.rs` (test-or-fixture; 308765 bytes; 8602 text lines)
- `src/compiler/flags.rs` (source-or-script; 23160 bytes; 647 text lines)
- `src/compiler/mod.rs` (source-or-script; 107328 bytes; 2631 text lines)
- `src/compiler/nvcc.rs` (source-or-script; 104088 bytes; 2726 text lines)
- `src/compiler/platform.rs` (source-or-script; 45095 bytes; 1121 text lines)
- `src/probe/cache.rs` (source-or-script; 21804 bytes; 554 text lines)
- `src/probe/mod.rs` (source-or-script; 68293 bytes; 1739 text lines)
- `src/probe/resolve.rs` (source-or-script; 49359 bytes; 1141 text lines)
- `src/probe/testdata/clang_cl_windows.txt` (config-or-delivery-collateral; 2266 bytes; 6 text lines)
- `src/probe/testdata/clang_o2.txt` (config-or-delivery-collateral; 4096 bytes; 5 text lines)
- `src/probe/testdata/clang_o2_gdwarf2.txt` (config-or-delivery-collateral; 4138 bytes; 5 text lines)
- `src/probe/testdata/clang_o2_gdwarf4.txt` (config-or-delivery-collateral; 4138 bytes; 5 text lines)
- `src/probe/testdata/clang_o2_march_native.txt` (config-or-delivery-collateral; 3971 bytes; 5 text lines)
- `src/probe/testdata/clang_ubsan_strip_path.txt` (config-or-delivery-collateral; 4065 bytes; 5 text lines)
- `src/probe/testdata/gcc_o2.txt` (config-or-delivery-collateral; 2358 bytes; 14 text lines)
- `src/probe/testdata/gcc_o2_march_native.txt` (config-or-delivery-collateral; 2751 bytes; 14 text lines)
- `src/probe/testdata/gcc_wrapv_param.txt` (config-or-delivery-collateral; 5272 bytes; 14 text lines)
- `src/probe_memo.rs` (source-or-script; 6935 bytes; 181 text lines)
- `tests/cc_family_probe_test.rs` (test-or-fixture; 4774 bytes; 115 text lines)
- `tests/cc_passthrough_args_test.rs` (test-or-fixture; 22343 bytes; 643 text lines)
- `tests/cc_release_regression_test.rs` (test-or-fixture; 1782 bytes; 64 text lines)
- `tests/fixtures/cc_release_regressions.sh` (test-or-fixture; 4156 bytes; 113 text lines)
- `tests/fixtures/mock_cc_constant_output.sh` (test-or-fixture; 202 bytes; 7 text lines)
- `tests/fixtures/mock_cc_diagnostics.sh` (test-or-fixture; 419 bytes; 18 text lines)
- `tests/fixtures/mock_cc_lc_all.sh` (test-or-fixture; 363 bytes; 18 text lines)
- `tests/fixtures/mock_cc_static.sh` (test-or-fixture; 192 bytes; 13 text lines)
- `tests/fixtures/native_archive_fuzz/truncated-member` (test-or-fixture; 10 bytes; 2 text lines)
- `tests/nvcc_cuda_toolchain_test.rs` (test-or-fixture; 14144 bytes; 446 text lines)
- `tests/unknown_compiler_probe_test.rs` (test-or-fixture; 3142 bytes; 112 text lines)
