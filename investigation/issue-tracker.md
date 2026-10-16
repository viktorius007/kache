# Kache issue tracker

Updated 2026-10-11. Audited baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`.

This is the current decision tracker. **Confirmed bugs need fixes.** Trigger conditions affect priority and exposure; they do not change the confirmed-bug status. Fix PR preparation is now underway using the saved proofs and original agents. [Delivery queue](pr-delivery/queue.json) tracks separate test/fix commits, independent review and upstream PR links. Bugs remain open until the upstream fix merges.

| Classification | Decision |
|---|---|
| Confirmed bug — fix | Executed evidence establishes incorrect behavior. Schedule a repair. |
| Measured cost — evaluate | Cost is measured; a correctness defect or unnecessary cost has not been established. Test an optimization or policy change. |
| External tool gap — address externally | Detection/integration gap belongs to the external tool. |
| Unproven lead — investigate | No executed proof establishes a bug. Do not schedule a repair on this evidence alone. |

## High impact — confirmed bugs

Every item in this section is **Confirmed bug — fix**.

| ID | Bug | Required action | Evidence |
|---|---|---|---|
| cargo-build-001 | Build-script caching drops Cargo-recognized rerun environment declarations surrounded by whitespace and silently restores stale generated output. | [Draft PR #1498](https://github.com/kunobi-ninja/kache/pull/1498); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-cargo-build/investigation/report.md) |
| cc-header-permutation | C compile keys lose the association between header paths and header contents, restoring obsolete objects after contents are exchanged. | [Draft PR #1505](https://github.com/kunobi-ninja/kache/pull/1505); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-cc-cuda-adapters/investigation/report.md) |
| cc-optional-header | C read-set reuse misses a newly created header tested through __has_include and restores an obsolete object. | [Draft PR #1501](https://github.com/kunobi-ninja/kache/pull/1501); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-cc-cuda-adapters/investigation/report.md) |
| cc-link-library | Opt-in C/C++ link keys do not hash libraries selected with -l, restoring obsolete executables after a library changes. | [Draft PR #1513](https://github.com/kunobi-ninja/kache/pull/1513); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-cc-cuda-adapters/investigation/report.md) |
| KEY-ENV-001 | Unset and set-to-empty compile-time environment variables share a cache key and can restore the wrong option_env! result. | [Draft PR #1499](https://github.com/kunobi-ninja/kache/pull/1499); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-key-native-inputs/investigation/report.md) |
| KEY-ENV-002 | A user-defined include! macro is treated as a builtin path locator, allowing restored artifacts to embed another checkout's OUT_DIR. | [Draft PR #1503](https://github.com/kunobi-ninja/kache/pull/1503); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-key-native-inputs/investigation/report.md) |
| restoration-literal-marker | Literal dependency directories that match Kache dep-info sentinels are expanded into different paths, allowing Cargo and Make to miss real input changes. | [Draft PR #1502](https://github.com/kunobi-ninja/kache/pull/1502); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/qa-file-restoration/investigation/report.md) |
| restoration-shared-publication-permission | Duplicate publication of a source already hardlinked to its published blob clears the existing blob read-only protection and allows mutation through the source alias. | [Draft PR #1509](https://github.com/kunobi-ninja/kache/pull/1509); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/qa-file-restoration/investigation/report.md) |
| qa-remote-binding | Exact remote restore accepts a valid pack for another cache key and silently restores an incorrect compiler output. | [Draft PR #1500](https://github.com/kunobi-ninja/kache/pull/1500); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/qa-remote-validation/investigation/report.md) |
| store-publication-rollback-001 | An aborted republication of a stranded committed key leaves filesystem metadata ahead of SQL; removing the key can reclaim a different committed entry’s only blob. | [Draft PR #1508](https://github.com/kunobi-ninja/kache/pull/1508); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/qa-store-transactions/investigation/report.md) |

## Medium impact — confirmed bugs

Every item in this section is **Confirmed bug — fix**.

| ID | Bug | Required action | Evidence |
|---|---|---|---|
| benchmark-guardrails-001 | A nonzero measurement exit leaves surviving members of its process group running. | [Draft PR #1510](https://github.com/kunobi-ninja/kache/pull/1510); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-benchmark-guardrails/investigation/report.md) |
| benchmark-guardrails-002 | The timed Cargo dependency-fetch guard scans stdout and accepts recognized fetch messages sent to stderr. | [Draft PR #1514](https://github.com/kunobi-ninja/kache/pull/1514); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-benchmark-guardrails/investigation/report.md) |
| cli-config-001 | Unix init corrupts a valid Cargo config when its build table has a trailing comment. | [Draft PR #1521](https://github.com/kunobi-ninja/kache/pull/1521); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-cli-config/investigation/report.md) |
| cli-config-002 | Doctor migration turns a working absolute sccache wrapper path into a nonexistent kache path. | [Draft PR #1525](https://github.com/kunobi-ninja/kache/pull/1525); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-cli-config/investigation/report.md) |
| CONTRACT-BIN-001 | Implicit default-bin rustc invocations ignore cache_executables=false and skip the configured fallback. | [Draft PR #1516](https://github.com/kunobi-ninja/kache/pull/1516); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-contract-conformance/investigation/report.md) |
| guardrails-apt-publication-order | APT publication exposes new indexes before uploading the package files they name. | [Draft PR #1530](https://github.com/kunobi-ninja/kache/pull/1530); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-guardrails/investigation/report.md) |
| guardrails-verify-timeout-unused | The fixture harness ignores verify.timeout_s and passes an executable that exceeds its deadline. | [Draft PR #1526](https://github.com/kunobi-ninja/kache/pull/1526); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-guardrails/investigation/report.md) |
| observability-001 | Redacted JSON reports expose workspace roots in bypass.slowest rows. | [Draft PR #1524](https://github.com/kunobi-ninja/kache/pull/1524); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/report.md) |
| observability-003 | An interrupted event record inside a UTF-8 character poisons reporting even after the next valid event is appended. | [Draft PR #1518](https://github.com/kunobi-ninja/kache/pull/1518); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/report.md) |
| planner-service-stale-lease | A stale inherited test lease marker suppresses scheduler admission after the owner has exited and released its slots. | [Draft PR #1528](https://github.com/kunobi-ninja/kache/pull/1528); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-planner-service/investigation/report.md) |
| rd-credential-child-001 | A timed-out S3 credential_process keeps running after the remote operation is cancelled. | [Draft PR #1506](https://github.com/kunobi-ninja/kache/pull/1506); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-remote-daemon/investigation/report.md) |
| rust-wrapper-001 | Changing --error-format to JSON replays cached human diagnostics. | [Draft PR #1507](https://github.com/kunobi-ninja/kache/pull/1507); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-rust-wrapper/investigation/report.md) |
| rust-wrapper-002 | A rustc hit for an explicit emit destination restores the producer filename and omits the requested output. | [Draft PR #1517](https://github.com/kunobi-ninja/kache/pull/1517); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-rust-wrapper/investigation/report.md) |
| rust-wrapper-003 | Rustdoc cache keys omit nested module files below a non-mod.rs module. | [Draft PR #1527](https://github.com/kunobi-ninja/kache/pull/1527); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-rust-wrapper/investigation/report.md) |
| rust-wrapper-004 | Rustdoc cache keys omit files included by an outer documentation attribute. | [Draft PR #1522](https://github.com/kunobi-ninja/kache/pull/1522); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-rust-wrapper/investigation/report.md) |
| rust-wrapper-005 | Rustdoc cache keys omit environment dependencies read by env! in documentation. | [Draft PR #1531](https://github.com/kunobi-ninja/kache/pull/1531); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-rust-wrapper/investigation/report.md) |
| ephemeral-ci-001 | Bulk sync skips an extracted but uncommitted remote entry and exits successfully with incomplete hydration. | [Draft PR #1519](https://github.com/kunobi-ninja/kache/pull/1519); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/ephemeral-ci/investigation/report.md) |
| ephemeral-ci-002 | Concurrent bulk sync clients sharing a local store race destructive extraction against import and fail otherwise valid CI jobs. | [Draft PR #1529](https://github.com/kunobi-ninja/kache/pull/1529); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/ephemeral-ci/investigation/report.md) |
| pack-prefetch-entry-budget | Packed prefetch imports sibling entries excluded by the configured per-plan entry budget. | [Draft PR #1523](https://github.com/kunobi-ninja/kache/pull/1523); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/pack-publisher/investigation/report.md) |
| pack-prefetch-plan-deadline | Packed prefetch starts new pack downloads after the configured plan dispatch deadline. | [Draft PR #1532](https://github.com/kunobi-ninja/kache/pull/1532); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/pack-publisher/investigation/report.md) |
| qa-cross-shard-singleflight | Concurrent same-key remote checks for distinct configured stores reuse the leader hit even though the follower store receives no entry. | [Draft PR #1512](https://github.com/kunobi-ninja/kache/pull/1512); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/qa-remote-validation/investigation/report.md) |
| remote-permits-cost-002 | Three queue-only demand timeouts open the shared read breaker and suppress new valid reads after every occupied request permit has been released. | [Draft PR #1511](https://github.com/kunobi-ninja/kache/pull/1511); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/remote-permits/investigation/report.md) |
| D5 | Successful remote PUTs execute pressure GC synchronously on async workers, delaying unrelated health work when available async capacity is exhausted. | [Draft PR #1515](https://github.com/kunobi-ninja/kache/pull/1515); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-d5-investigation/investigation/report.md) |

## Lower impact — confirmed bugs

Every item in this section is **Confirmed bug — fix**.

| ID | Bug | Required action | Evidence |
|---|---|---|---|
| observability-002 | Report bypass reasons discard the dedicated skip_reason recorded by successful Rust skip gates. | [Draft PR #1533](https://github.com/kunobi-ninja/kache/pull/1533); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/report.md) |
| planner-service-timeline-auth | Timeline uploads omit automatic workload and session authentication, so documented OIDC/Actions-only services reject them. | [Draft PR #1535](https://github.com/kunobi-ninja/kache/pull/1535); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/audit-planner-service/investigation/report.md) |
| EV594-001 | Compile-cost backfill repeatedly reselects a full batch of zero-cost legacy entries and starves recoverable expensive entries behind it. | [Draft PR #1534](https://github.com/kunobi-ninja/kache/pull/1534); awaiting CI/merge | [Executed proof](/Users/viktor/Developer/github/kache-investigations/eviction-value/investigation/report.md) |

## Trigger conditions for the two store-integrity bugs

- **store-publication-rollback-001: Confirmed bug — fix.** Executed with a generated stranded entry and injected SQLite failure; natural recurrence is not measured.
- **restoration-shared-publication-permission: Confirmed bug — fix.** Executed through the production store API on HFS+ with an already shared inode; ordinary Cargo recurrence is not demonstrated.

These exposure questions remain open; the executed rollback and immutability failures are confirmed.

## Measured costs — evaluate

| ID | Observed cost | Next action | Evidence |
|---|---|---|---|
| remote-permits-cost-001 | A full request pool delays valid small demand restores and can exhaust a stricter client deadline without issuing their GET. | Evaluate latency policy and scheduling | [Measurements](/Users/viktor/Developer/github/kache-investigations/remote-permits/investigation/report.md) |
| PERFORMANCE-RELEASE-1494 | Workspace tree guard adds measured overhead; repeated work offers optimization candidates. No validated fix or proof of the exact Biome regression yet. | Implement a safe optimization experiment; measure retained cost and rerun the exact upstream gate | [Measurements](/Users/viktor/Developer/github/kache-investigations/release-performance/investigation/report.md) |

The release slowdown is not listed as a confirmed logic bug. The queue-saturation timeout is not listed as a bug. By contrast, local queue timeouts incorrectly suppressing healthy reads is a confirmed bug (`remote-permits-cost-002`).

## External tool gap

| ID | Gap | Action | Evidence |
|---|---|---|---|
| cache-poisoning-1034-001 | Current released zizmor does not recognize kache-action cache reads in publishing workflows. | Add external scanner coverage | [Executed fixture](/Users/viktor/Developer/github/kache-investigations/cache-poisoning-audit/investigation/report.md) |

## Unproven leads — investigate

No confirmed bug and no repair decision exists for these items.

| ID | Investigation | Action | Checkpoint |
|---|---|---|---|
| LEAD-NATIVE-ARCHIVE | Native archive changes between key calculation and compiler consumption | Execute a behavioral test before proposing a fix | [Checkpoint](/Users/viktor/Developer/github/kache-investigations/qa-native-inputs/investigation/report.md) |
| LEAD-NATIVE-DYLIB | macOS dylib export/version changes with unchanged install name | Execute a behavioral test before proposing a fix | [Checkpoint](/Users/viktor/Developer/github/kache-investigations/qa-native-inputs/investigation/report.md) |
| LEAD-CARGO-SPLIT-LOCK | Cargo split-build-directory lock exclusion | Execute a behavioral test before proposing a fix | [Checkpoint](/Users/viktor/Developer/github/kache-investigations/qa-target-coordination/investigation/report.md) |
| LEAD-TARGET-BLOB | Target artifact validation after same-length middle-blob corruption | Execute a behavioral test before proposing a fix | [Checkpoint](/Users/viktor/Developer/github/kache-investigations/qa-target-coordination/investigation/report.md) |

## Tracking totals

- 36 confirmed bugs; all require fixes, with severity recorded above.
- 2 measured-cost items, including the release-performance investigation.
- 1 external tool gap.
- 4 unproven leads.

Evidence and historical agent reports are preserved. The structured decisions are in [findings-register.json](findings-register.json) and [investigation-items.json](investigation-items.json). Full audit context is in [report.md](report.md).
