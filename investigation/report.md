STATUS: DONE
COMMIT: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9
CHANGED: 274 files
OPEN: 2 unresolved items
BLOCKERS: none for this audit; no CUDA toolkit for remaining runtime investigations
CONFIRMED: 3
LIMITS: real Apple Clang 17 on arm64 macOS only; dedicated/large inline test bodies sampled; no real GCC, clang-cl, CUDA, Linux/Windows, remote, concurrency, or performance execution
---

Three silent stale-output defects are confirmed on untouched baseline production source. Default C/C++ compile caching is affected by lost header-path/content association and untracked absent optional headers. A third defect affects opt-in C/C++ link caching when libraries are selected through `-l`. No production repair is included.

`cc-header-permutation` is the strongest key-integrity result. The source includes a.h then b.h, each redefining VALUE. Moving the complete existing contents between those header names preserves the sorted/deduplicated content hashes used by `cc_direct_inputs_digest` (`src/compiler/cc.rs:6102`). The memo notices changed stamps and fresh preprocessing can run, but its actual expansion is replaced with the same content-set digest (`src/compiler/cc.rs:7333`). The changed build restores a cached object whose linked program exits 2; direct compilation of the current tree exits 1. This occurs with deferred discovery both enabled and disabled. A non-permutation edit adding VALUE=3 correctly misses and agrees with the oracle. A remediation should preserve the association between normalized input identity and content, or use the actual expansion semantics, while maintaining portable checkout reuse.

`cc-optional-header` arises when `__has_include("optional.h")` changes from false to true. The initial read set never contains that absent filename. `cc_shadowing_names` only extracts names from previously read files (`src/compiler/cc.rs:5490`), so creating optional.h leaves the warm key unchanged. Cached code exits 1 while a direct compile exits 2. Both deferred-discovery settings reproduce this. Editing an already included optional.h correctly misses. A remediation needs negative/existence dependencies or a conservative refusal/invalidation mechanism for preprocessor availability probes; turning deferred discovery off does not fix this warm-hit gap.

`cc-link-library` requires `KACHE_CACHE_CC_LINKS=1`, which defaults off. A real static archive update behind identical `clang main.o -L. -lvalue -o app` arguments restores an obsolete app returning 1; a current direct link returns 2. `cache_key_for_link` hashes explicit positional inputs, and `cc_link_file_inputs` skips dash-prefixed flags (`src/compiler/cc.rs:6414`, `:7727`). Passing libvalue.a positionally correctly misses on update. A remediation must resolve/hash the compiler's selected library inputs or refuse unresolved named-library links. The proof establishes local static -l behavior; it does not establish dynamic or platform-specific linker behavior.

Every failure includes a cold miss, an unchanged warm local hit, identical changed-build key, zero changed-build compiler executions, and an independent direct-Clang oracle. Output objects/apps are removed before wrapper invocation to force restore. Input changes settle for 2.1 seconds, excluding recent-write timestamp guards. Fixture HOME/config/cache/runtime are isolated under investigation. Real compilers and the untouched baseline CLI execute through their public interfaces; there are no test-only production hooks. Normalization in the direct compiler oracle matches the wrapper's file-prefix map; numeric cases do not depend on paths. Program exits encode intentional return values, distinct from compiler process exit success.

| Replay / control | Changed-build event | Cached program | Direct program | Verdict |
| --- | --- | --- | --- | --- |
| header-swap-1 | local_hit | 2 | 1 | expected RED |
| header-swap-0 | local_hit | 2 | 1 | expected RED |
| has-include-1 | local_hit | 1 | 2 | expected RED |
| has-include-0 | local_hit | 1 | 2 | expected RED |
| link-library-1 | local_hit | 1 | 2 | expected RED |
| epoch-1 | miss | Jan  1 2000 00:00:00 | Jan  1 2000 00:00:00 | PASS control |
| header-swap-1-control | miss | 3 | 3 | PASS control |
| has-include-1-control | miss | 2 | 2 | PASS control |
| link-library-1-control | miss | 2 | 2 | PASS control |

Replay each admitted finding using its `*.replay.json` argv/workdir. Expected assertion failure is success for this audit. Full reusable source is `cc-integrity-probes.py`; `findings.json` embeds that source and exact red output per finding. Each fixture directory preserves source/header/archive/object/app, `commands.json` (exact real process argv/status/stdout/stderr), `observations.json`, per-phase wrapper diagnostics and local cache events. Root `*-1.log`/`*-0.log` files contain complete executed stdout and assertion. The baseline CLI is `/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache`; its SHA-256 is recorded in `baseline-cli-sha256.txt`, and compiler identity in `clang-version.txt`. `git diff --exit-code -- src tests docs` passed and the worktree remains at 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. All changed files are investigation artifacts.

The initial Clang epoch-underkey candidate was refuted: SOURCE_DATE_EPOCH 0 -> 946684800 causes a different cache key, a miss, and direct-equivalent Jan 1 2000 output. Do not infer that CUDA behaves the same: its documentation explicitly describes an unkeyed epoch, and no actual nvcc is available here. Four bounded dismissals are in `findings.json`; passing controls do not establish whole-adapter correctness.

All assigned production implementation bodies were read in full, including CC argument classification and exclusions; unsafe assembly/PCH/module gates; diagnostic and exit handling; memo identities/revalidation; compiler identity/argument/environment probes; C/CUDA dependency extraction; prefix-map handling; linker artifact capture; and macOS signature/debug-bundle packing/extraction. Documents, small integration tests, probe snapshots and shell fixtures were fully read. `coverage.json` records every one of the 32 primary paths plus consulted wrapper ranges. Large test-body omissions are exact:

- `src/compiler/cc/tests.rs`: reviewed 1-640, 6588-7170, 7463-7600; omitted 641-6587, 7171-7462, 7601-8602.
- `src/compiler/mod.rs`: reviewed 1-1400; omitted 1401-2631 (tests; production ends 995).
- `src/compiler/nvcc.rs`: reviewed 1-1400; omitted 1401-2726 (tests; production ends 1333).
- `src/compiler/platform.rs`: reviewed 1-670; omitted 671-1121 (tests; production ends 500).
- `src/probe/mod.rs`: reviewed 1-950; omitted 951-1739 (tests; production ends 786).

Existing committed integration/unit suites were inspected rather than run; focused real compiler probes above are the executed verification. The host cannot exercise CUDA, native GNU GCC, Windows clang-cl, Linux/Windows filesystem/locking/signing or GPU toolchains. No mock NVCC proof is presented as toolkit behavior. Daemon/remote stores, concurrency races, publication failure injection and performance were not executed. No load-sensitive benchmark or broad performance inference was made. After the coordinator released its quiet window, only bounded compiler fixtures ran; no baseline or dependency build was needed.

Structural exploration used the installed codebase-memory skill and baseline project `Users-viktor-Developer-github-kache-investigations-coordinator`, ready index at 2026-10-11T05:36:35Z, with 26,827 nodes and 149,258 edges. Rust coverage is semantic_partial because binding oracle, expanded calls and impl relationships are unavailable. Project unresolved-site counts are 127,041 calls and 193,239 references. Graph architecture/symbol/inbound queries provided navigation; all relevant production was checked in source. Partial graph edges and zero-name search results are not exhaustive caller/absence evidence. `graph-status.txt` preserves current coverage metadata. No claim that the index is exhaustive or that source review proves runtime safety is made.

Two unresolved groups remain in `unresolved.json`: real-toolkit CUDA epoch/host executable identity behavior, and an NVCC lock/publication seam consulted from the wrapper owner. The source allows a contention/error path to compile and reach storage with no retained build lock, but no externally observable concurrency consequence was executed; redundant publication alone is not an admitted defect. These are follow-up leads with explicit proof conditions. They do not dilute the three executed CC results.
