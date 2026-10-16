# Post-upload GC investigation

This permanent worktree contains the complete D5 investigation against upstream `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`, on local branch `investigation/post-upload-gc`.

- Test and experiment source: `../src/daemon/tests/post_upload_gc.rs`.
- Findings: [outstanding-findings.md](outstanding-findings.md).
- Methods, results and reproduction commands: [verification.md](verification.md).
- Summary script: [summarize.py](summarize.py).
- Raw optimized measurements: [release-measurements.log](release-measurements.log).
- Structured results: [release-summary.json](release-summary.json).
- Preliminary debug measurements: [debug-measurements.log](debug-measurements.log).
- Regression failure logs: [regression.log](regression.log) and [release-regression.log](release-regression.log).
- Two-worker control: [discriminator.log](discriminator.log).
- Portable test patch: [regression.patch](regression.patch).

The regression deliberately fails on the unchanged upstream production code. No production fix has been applied. All investigation files are uncommitted in this worktree. Build caches under `/private/tmp/kache-d5-target` and `/private/tmp/kache-d5-release-target` are disposable and can be regenerated with Cargo.

To summarize the saved optimized measurements from the worktree root:

```sh
python3 investigation/summarize.py investigation/release-measurements.log
```
