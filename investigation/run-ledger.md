# Investigation run ledger

Baseline: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. All delegated agents: gpt-6.1-sol, high reasoning.

| Agent | Scope | Worktree | Report | Status |
|---|---|---|---|---|
| release-performance | release-performance | /Users/viktor/Developer/github/kache-investigations/release-performance | investigation/report.md | done (report saved; scope limits apply) |
| remote-permits | remote-permits | /Users/viktor/Developer/github/kache-investigations/remote-permits | investigation/report.md | done (report saved; scope limits apply) |
| eviction-value | eviction-value | /Users/viktor/Developer/github/kache-investigations/eviction-value | investigation/report.md | done |
| ephemeral-ci | ephemeral-ci | /Users/viktor/Developer/github/kache-investigations/ephemeral-ci | investigation/report.md | done (report saved; scope limits apply) |
| pack-publisher | pack-publisher | /Users/viktor/Developer/github/kache-investigations/pack-publisher | investigation/report.md | done (report saved; scope limits apply) |
| cache-poisoning-audit | cache-poisoning-audit | /Users/viktor/Developer/github/kache-investigations/cache-poisoning-audit | investigation/report.md | done |
| sweep-map | sweep-map | /Users/viktor/Developer/github/kache-investigations/sweep-map | investigation/report.md | done |
| post-upload-gc | D5 | /Users/viktor/Developer/github/kache-d5-investigation | investigation/report.md | done (report saved; scope limits apply) |
| audit-cargo-build | cargo-build (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-cargo-build | investigation/report.md | done (report saved; scope limits apply) |
| audit-remote-daemon | remote-daemon (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-remote-daemon | investigation/report.md | done (report saved; scope limits apply) |
| audit-planner-service | planner-service (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-planner-service | investigation/report.md | done (report saved; scope limits apply) |
| audit-guardrails | guardrails (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-guardrails | investigation/report.md | done (report saved; scope limits apply) |
| audit-rust-wrapper | rust-wrapper (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-rust-wrapper | investigation/report.md | done (report saved; scope limits apply) |
| audit-key-native-inputs | key-native-inputs (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-key-native-inputs | investigation/report.md | done (report saved; scope limits apply) |
| audit-cc-cuda-adapters | cc-cuda-adapters (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-cc-cuda-adapters | investigation/report.md | done (report saved; scope limits apply) |
| audit-store-core | store-core (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-store-core | investigation/report.md | done (report saved; scope limits apply) |
| audit-filesystem-targets | filesystem-targets (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-filesystem-targets | investigation/report.md | done (report saved; scope limits apply) |
| audit-cli-config | cli-config (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-cli-config | investigation/report.md | done (report saved; scope limits apply) |
| audit-observability | observability (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-observability | investigation/report.md | done (report saved; scope limits apply) |
| audit-contract-conformance | contract-conformance (spec-conformance) | /Users/viktor/Developer/github/kache-investigations/audit-contract-conformance | investigation/report.md | done (report saved; scope limits apply) |
| audit-benchmark-guardrails | benchmark-guardrails (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-benchmark-guardrails | investigation/report.md | done (report saved; scope limits apply) |
| audit-store-link | store-link (production-readiness) | /Users/viktor/Developer/github/kache-investigations/audit-store-link | investigation/report.md | done (report saved; scope limits apply) |

## Fresh-context completion wave

All six launched successfully as gpt-6.1-sol/high at baseline 4ee0f9e. Store transactions and native inputs then received agent-runtime content-filter errors; both resumed with artifact checkpoint-only tasks. Other scopes continue. These are runtime agent errors, not tool approval rejections.

- qa-store-transactions: /Users/viktor/Developer/github/kache-investigations/qa-store-transactions/investigation/report.md
- qa-file-restoration: /Users/viktor/Developer/github/kache-investigations/qa-file-restoration/investigation/report.md
- qa-target-coordination: /Users/viktor/Developer/github/kache-investigations/qa-target-coordination/investigation/report.md
- qa-remote-validation: /Users/viktor/Developer/github/kache-investigations/qa-remote-validation/investigation/report.md
- qa-native-inputs: /Users/viktor/Developer/github/kache-investigations/qa-native-inputs/investigation/report.md
- qa-ci-hydration: /Users/viktor/Developer/github/kache-investigations/qa-ci-hydration/investigation/report.md

Independent root replay: 24/24 expected behavioral failures admitted. Raw logs and case verdicts: investigation/root-replay/. Further targeted proofs remain to replay.

Final wave status: every report/checkpoint is saved. Five fresh agent turns received runtime content flags, including remote validation after report save. Root completed independent replay of the saved remote and restoration cases; all five were admitted. See report.md for remaining unexecuted work and scope limits.
