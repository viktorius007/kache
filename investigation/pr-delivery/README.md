# Focused fix PR delivery

Scope: the 36 confirmed bugs in the issue tracker. Measured costs, external tool gaps and unproven leads are excluded.

Original agents are resumed with their saved proofs. Each independent PR targets upstream main and has a regression-test commit followed by a fix commit. Authors run the required just check gate. Independent review precedes publication; PRs start as drafts and changed-line mutation testing runs in CI. No PR is merged by this task.

The first dispatched fixes are KEY-ENV-001, cargo-build-001, cc-optional-header, qa-remote-binding and restoration-literal-marker. Subsequent siblings reuse their author's build cache and context.

- Delivery state: queue.json
- Author contract: common-brief.md
- Review contract: review-brief.md
- Build/test concurrency: three slots, each with two Cargo/test threads and private targets

PR descriptions use at most75 words: Cause, Fix, Tests, with baseline file/line permalinks. Source proofs and logs remain outside PR diffs.
