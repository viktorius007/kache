# Kache investigation checkpoint

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. This is a progress record, not a completed assessment or a repair.

The first wave saved reports for every assigned slice. Six fresh Sol 6.1/high agents were dispatched to complete selected checks. Four encountered agent-runtime content-filter errors: native inputs, store transactions, target coordination and file restoration. The first three saved checkpoints after resumption with report-only tasks; restoration checkpoint is pending. No tool approval rejection was reported. Native archive interleaving, dylib exports/version semantics, Cargo split-directory locks and target corrupted-blob handling remain unexecuted.

Root independently reproduced 24 initial behavioral failures. Targeted pack, migration and remote permit proofs were also replayed; the pack deadline manifest initially used the wrong assertion text, then its exact existing assertion was corrected and admitted. Both conditional store rollback consequences and both CI hydration findings have now reproduced under root replay. 33 behavioral proof cases were admitted across the independent replay batches. Runtime evidence does not establish defect prevalence, cross-platform behavior or source-data loss.

The synthetic release performance experiment measured main at 1.754 seconds versus stable at 0.239 seconds for an edit to a documentation file in a generated workspace with 4,000 small unrelated documents. All 24 library actions remained hits. This points to repeated tree scanning/digest work rather than lost hit rate. The exact upstream release-blocking Biome workload was unavailable, so the release gate remains unresolved.

Primary coverage accounts for all 843 tracked paths: 433 reviewed, 104 sampled and 306 collateral. Collateral paths are fixtures/assets/metadata, not evidence of exhaustive semantic review; sampled large suites have explicit omitted ranges. This does not establish that Kache is free of defects.

Evidence is saved in permanent per-agent worktrees. `findings-checkpoint.json` embeds the current findings and report paths, excluding duplicate CI validations. `primary-coverage.json` preserves per-path coverage and limitations. Raw independent replay commands and logs are under `root-replay/`.

Final report saved: [report.md](report.md). All fresh scopes now have reports/checkpoints, including remote validation and restoration. Five fresh agent turns received runtime flags in total; completed proof cases were preserved. The completed independent code replay batches admitted 38 cases; remaining unexecuted checks are listed in the report.
