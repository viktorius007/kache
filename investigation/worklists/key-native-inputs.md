# Cache-key identity, normalization, external and native inputs

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 22; bytes: 1941052.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- compiler-adapters-probes-and-eligibility: 11 paths, 5640 text lines; subdivide into the listed contiguous file sections when needed.
- key-and-prediction: 8 paths, 36238 text lines; subdivide into the listed contiguous file sections when needed.
- native-and-toolchains: 3 paths, 7980 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace Rust, rustdoc, C/C++ and CUDA entry paths from compiler detection through eligibility, dependency discovery, key derivation, compile/passthrough and restore; preserve compiler exit status and diagnostic/artifact behavior.
- Account for every compiler-observable input, mutation between discovery/compile/publication, prediction validity, native linking, target specs, proc macros, diagnostic flags and path normalization; compare same-input reuse across worktrees and changed-input invalidation.
- Review inline tests and regression fixtures fully; vary real observable compiler output or exit status for candidate proofs. Public degree-zero methods are not evidence of dead code.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- rust-key-inputs: consult rust-wrapper; Rust wrapper discovery/eligibility/compilation ↔ cache key and native dependency closure; predicted and actual inputs, stable reuse, mutation guard

## Sampling declarations

- macOS host: Linux/Windows linking, filesystem and compiler-specific behavior require source review plus declared execution limits.
- Rust focus does not permit silently skipping C/C++/CUDA/rustdoc; name every unexecuted toolchain branch.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `docs/how-it-works/cache-key.mdx` (contract-doc-or-ci; 16143 bytes; 230 text lines)
- `src/cache_key.rs` (source-or-script; 403235 bytes; 9651 text lines)
- `src/cache_key/apple_install_name.rs` (source-or-script; 10086 bytes; 286 text lines)
- `src/cache_key/tests.rs` (test-or-fixture; 595225 bytes; 16106 text lines)
- `src/checked_regions.rs` (source-or-script; 2680 bytes; 77 text lines)
- `src/extra_inputs.rs` (source-or-script; 184618 bytes; 4718 text lines)
- `src/identity.rs` (source-or-script; 24734 bytes; 681 text lines)
- `src/key_env.rs` (source-or-script; 7720 bytes; 222 text lines)
- `src/native_archive.rs` (source-or-script; 149224 bytes; 3685 text lines)
- `src/native_link_key.rs` (source-or-script; 157504 bytes; 4146 text lines)
- `src/path_normalizer.rs` (source-or-script; 166253 bytes; 3858 text lines)
- `src/policy.rs` (source-or-script; 9866 bytes; 288 text lines)
- `src/toolchain_dylib.rs` (source-or-script; 5880 bytes; 149 text lines)
- `src/tree_stamp.rs` (source-or-script; 28729 bytes; 716 text lines)
- `tests/cache_key_underkeying_test.rs` (test-or-fixture; 32913 bytes; 958 text lines)
- `tests/codegen_backend_test.rs` (test-or-fixture; 3271 bytes; 94 text lines)
- `tests/extra_inputs_warm_target_test.rs` (test-or-fixture; 31823 bytes; 957 text lines)
- `tests/input_prediction_test.rs` (test-or-fixture; 77760 bytes; 2029 text lines)
- `tests/macos_native_install_name_test.rs` (test-or-fixture; 5614 bytes; 171 text lines)
- `tests/proc_macro_env_key_test.rs` (test-or-fixture; 9262 bytes; 243 text lines)
- `tests/workspace_extra_inputs_test.rs` (test-or-fixture; 12249 bytes; 395 text lines)
- `tests/worktree_depinfo_test.rs` (test-or-fixture; 6263 bytes; 198 text lines)
