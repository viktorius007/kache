# Kache trust and performance investigations

**Current item classifications and repair decisions: [issue-tracker.md](issue-tracker.md).** This tracker supersedes earlier mixed descriptions of bugs, costs and leads.

Baseline: upstream main `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`, checked 2026-10-11. The main clone and installed Kache remain outside the investigation write scope.

Each targeted investigation and audit owns a permanent worktree beside this coordinator worktree. Agents use `gpt-6.1-sol` with high reasoning. The run is investigation-only, with feature-gated hotpath-rs instrumentation authorized for release-performance. No GitHub submissions or production repairs are part of this wave.

The review emphasizes wrong outputs, unsafe reuse, data integrity, concurrency, substantial avoidable misses and measurable performance costs. Style and minor cleanup are excluded. Negative findings and unexamined regions are recorded rather than asserting bug freedom.

- Dispatch status and report locations: [run-ledger.md](run-ledger.md).
- Full tracked inventory: [tracked-inventory.json](tracked-inventory.json).
- Deterministic review frontier: [frontier.json](frontier.json).
- Common evidence and isolation contract: [common-brief.md](common-brief.md).
- Baseline index diagnostic: [code-index.log](code-index.log).
- Untouched CLI build: [baseline-build.log](baseline-build.log).

Targeted scopes: release performance (#1494), remote permit saturation (#327), value-aware eviction (#594), ephemeral CI hydration (#810), pack publication (#812), cache-poisoning audit integration (#1034), and D5 post-upload GC.

Audit scopes were mapped from all 843 tracked paths. Every path receives a primary owner; reviewed, sampled and unreviewed paths remain distinct. Final defect admission requires a runnable red proof at baseline and a mechanical replay that distinguishes behavioral assertion failures from build/environment failures. Benchmark timing claims require isolated runs and declared fixture/host limits.

Build caches can be recreated. All useful scripts, fixtures, patches, logs, profiling data and reports remain within the assigned worktree.

Consolidated evidence and explicit gaps: [report.md](report.md). Findings: [findings-register.json](findings-register.json). Independent replays: [root-replay-combined-results.json](root-replay-combined-results.json). Coverage: [primary-coverage.json](primary-coverage.json).
