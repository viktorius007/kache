# Kache correctness and performance investigation

**Current item classifications and repair decisions: [issue-tracker.md](issue-tracker.md).** This tracker supersedes earlier mixed descriptions of bugs, costs and leads.

STATUS: REPORTS SAVED; UNEXECUTED CHECKS REMAIN
BASELINE: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9
MODEL: delegated agents used gpt-6.1-sol with high reasoning
PRODUCTION REPAIRS: none; optional hotpath instrumentation exists only in its investigation worktree

The audit produced real wrong-output and cache-integrity failures, alongside release performance, concurrency and guardrail findings. This evidence does not support treating all current cache results as trustworthy across the affected input mechanisms. It also does not establish that the user's ordinary workload has encountered any listed defect. Read the workload-specific limits before treating a finding as broadly applicable.

Every assigned agent now has a saved report or checkpoint. Fresh-context redeployment completed remote validation, file restoration and CI hydration work and preserved the store rollback evidence. Five fresh agents received agent-runtime content-filter errors; the remote agent's report was already saved when its final turn errored. These were not tool approval rejections. The unfinished native and Cargo target checks remain explicitly open.

## Findings to prioritize

| Mechanism | Executed consequence | Evidence and limits |
|---|---|---|
| Exact remote entry identity | A valid pack for another key is accepted under the requested key; the restored library returns 29 while the requested source returns 11. | [Remote validation](../../qa-remote-validation/investigation/report.md). Real wrapper/daemon and loopback remote. Requires a wrong-object response within the trusted remote domain; frequency not measured. |
| Compile-time Rust environment | Absent and empty option_env! values share a key and restore the wrong runtime result. A separate shadowed include macro can retain a donor OUT_DIR. | [Key inputs](../../audit-key-native-inputs/investigation/report.md). Real rustc and runtime consumers, direct green controls. Macro finding has a narrower trigger. |
| Build-script declarations | Padded declarations that Cargo recognizes are omitted by the run-cache parser; changing a declared variable leaves generated contents stale. | [Cargo integration](../../audit-cargo-build/investigation/report.md). Actual Cargo builds compared with plain Cargo. |
| Native compilation inputs | Optional-header creation and exchanged header contents can restore obsolete objects; opt-in -l link caching misses library changes. | [C/C++ audit](../../audit-cc-cuda-adapters/investigation/report.md). Actual Apple Clang; default compile versus opt-in link scope separated. |
| Restored dependency paths | Literal paths matching internal markers are rewritten to decoys; a later true source/header edit is considered fresh by Cargo/Make and old code runs. | [Restoration](../../qa-file-restoration/investigation/report.md). Real Rust/C++ workflows; narrow specially named directory trigger. |
| Publication rollback | Failed republication leaves metadata and SQL mappings from different generations; later removal deletes a peer blob, and failed publication can appear as a hit. | [Store transactions](../../qa-store-transactions/investigation/report.md). Conditional generated missing-meta state plus injected SQLite ABORT. Natural precondition provenance and wrong compiled bytes are not established. |
| Shared blob permissions | Duplicate public API publication of an already shared inode clears readonly and permits source writes to change the published blob. | [Restoration](../../qa-file-restoration/investigation/report.md). Actual HFS+ volume and baseline store library. Ordinary Cargo recurrence was not demonstrated. |
| CI prewarming | Sync skips uncommitted extraction residue; concurrent clients sharing a store can fail valid imports. | [Independent hydration validation](../../qa-ci-hydration/investigation/report.md). Final concurrent row counts reached completeness; persistent wrong bytes not established. Healthy repeated-run controls passed. |
| Cross-shard scheduling | Singleflight shares a successful response across distinct destinations, leaving one requested store without an entry. | [Remote validation](../../qa-remote-validation/investigation/report.md). Reverse-order and independent-socket controls executed. Wrapper recompilation is the source-supported outcome; same physical volume used. |

The register retains further Rustdoc input omissions, output destination/diagnostic failures, remote timeout/circuit-breaker behavior, scheduling and reporting contracts, publication/harness guardrails and migration evidence. Lower-priority reporting detail does not displace wrong-output repairs. The zizmor detection gap is an external tool integration finding, not a demonstrated Kache exploit. CI revalidation records are deduplicated against their original findings. The [machine-readable register](findings-register.json) has 38 distinct finding records; their severity and exposure differ substantially.

## Release performance

[The hotpath investigation](../../release-performance/investigation/report.md) instrumented optional scopes and compared unprofiled stable and main release builds. In a generated 24-library workspace with 4,000 small unrelated documents, fresh documentation edits measured main at 1.754 seconds versus stable at 0.239 seconds (paired median +550.10%). All 24 library actions remained hits. Perturbation and traces point to tree traversal/digest work: a recent edit invalidates a memo and causes repeated hashing of settled small files below the memo size floor. Unchanged main measured 0.347 seconds versus stable 0.237 seconds; that comparison was below the repository's absolute regression threshold and is inconclusive under its gate.

The measured repair direction is memoization of settled small inputs with existing stat/restat/fingerprint safeguards, preserving arbitrary proc-macro/build-script inputs. No repair was implemented. The exact upstream Biome fixture/revision was unavailable, so this synthetic result neither clears the release gate nor proves its precise regression path. Profiling overhead was measured separately and excluded from the stable/main comparison.

[Post-upload GC](../../../kache-d5-investigation/investigation/report.md) separately proves async-worker occupancy under pressure: one-worker and conditional two-worker main/shard cases block health responsiveness, while tested sixteen-worker cases stay responsive. Multiple worktrees alone do not imply repeated parallel sweeps. The proposed direction reuses the coalesced GC scheduler; ordinary sixteen-worker Cargo slowdown is not established.

## Independent verification and coverage

Root independently admitted 38 replay cases across the completed code investigations, checking nonzero exit and the specified behavioral assertion rather than accepting compilation/setup failures. Multiple cases can prove one root cause: store consequences and Rust/C++ marker examples are deliberately not counted as separate defects. [Combined verdicts](root-replay-combined-results.json) and full raw logs are retained. Two manifests initially used incorrect expected text (pack deadline assertion wording and external scanner exit code); original rejected evidence remains saved and corrected manifests were replayed. No production code was changed to obtain a red result.

The D5 golden red was separately admitted, and a passing eviction control was correctly rejected by the same gate. The offline zizmor fixture was separately replayed and reproduced the specified missing detection; its scanner returned 14 for other findings, not zero. These are in the golden/external logs and are not added to the 38-case code batch count. Final independent restoration replay detached its generated HFS+ image successfully.

[Primary coverage](primary-coverage.json) accounts for all 843 tracked paths: 433 reviewed, 104 sampled and 306 collateral. Collateral paths are fixtures/assets/metadata and do not claim exhaustive semantic review. Large test suites have omitted ranges, and whole-suite, local mutation, live-cloud and broad cross-platform campaigns were not run. Graph orientation was corroborated in source because Rust semantic relationships were incomplete.

Remaining work is explicit: native archive hash/consume interleaving, macOS dylib export/version behavior, Cargo split-build-directory lock exclusion, target blob middle-corruption validation, and the exact upstream release benchmark. The source-supported store fault precondition and public-API hardlink recurrence also need ordinary workload validation. These gaps cannot be treated as passed checks.

The main clone is clean at the pinned baseline. The investigation did not deploy a fix, publish a GitHub issue/PR, or alter the installed Kache/launchd configuration. Evidence, scripts, profiler changes and fixture artifacts are retained in permanent worktrees listed in [run-manifest.json](run-manifest.json). An early first-wave filesystem probe used an incorrect config field and may have opened the default store before failing; it did not reach artifact mutation. Later probes and all independent root replay envelopes use explicit fixture isolation. No assertion about zero metadata side effects from that earlier attempt is made.
