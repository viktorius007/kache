STATUS: DONE
COMMIT: none
CHANGED: 31 files
OPEN: 0 unresolved investigations
BLOCKERS: none
CONFIRMED: 2
LIMITS: four test areas sampled; 16 benchmark source paths transferred; fixture payloads collateral; no full cross-platform suite, live publication, fuzz or mutation campaign
---

The production-readiness audit is complete at baseline `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`, with two confirmed guardrail defects. The audited baseline fails the two independent assertions below. Production source is unchanged; the 31 changed files are investigation artifacts, including a supported-interpreter symlink. Findings stay open for owner disposition. No production repair, publication or user-cache modification was performed.

| Finding | Reachable failure | Executed proof and scope |
| --- | --- | --- |
| `guardrails-apt-publication-order` | The release publisher replaces the live APT index before uploading the package files it advertises. An interrupted pool upload leaves installs/upgrades requesting an absent package. | The untouched publisher syncs new metadata, then a local object-store boundary injects upload failure. Publisher exits 9 and the live index points to an absent `new.deb`; the independent availability assertion fails. A healthy upload control exits 0 and finds the payload. |
| `guardrails-verify-timeout-unused` | The fixture harness ignores `verify.timeout_s`, accepting a verification program that exceeds its deadline. A hanging program can stall the sequential gate until outer CI cancellation. | The real baseline harness runs a bounded 1.25-second command with `timeout_s=1` in four phases, passes every phase and exits 0 after 5.141 seconds. The deadline assertion fails. A 0.05-second command passes in 0.325 seconds. |

APT publication order is in [publish.sh](../scripts/apt/publish.sh#L41), lines 41–60. Release wiring in [package-publish.yml](../.github/workflows/package-publish.yml#L161), lines 161–181, validates the local repository, publishes it, and runs live smoke checks only after successful publication. The [smoke check](../scripts/apt/smoke-test.sh#L44), lines 44–59, checks signed metadata and package names, without downloading payload objects named in `Filename` fields. The public suite can remain unavailable for the new version until retry or repair; successful slow uploads also expose an index-before-payload window. Separate invocations have no cross-call transaction; rclone documents [sync as updating destination contents](https://rclone.org/commands/rclone_sync/). The proof models this local file boundary and does not contact R2, sign metadata, run an APT client, or establish package corruption.

The timeout contract is documented and deserialized in [fixture.rs](../crates/kache-e2e/src/fixture.rs#L234), lines 234–260. [runner.rs](../crates/kache-e2e/src/runner.rs#L1055), lines 1055–1070, waits on `Command.output()` without consulting `timeout_s`. CI uses the sequential harness in [ci.yml](../.github/workflows/ci.yml#L1215), lines 1215–1245. The executed fixture deliberately uses trivial successful build/clean commands and one verification command, isolating the verification deadline. It clears inherited Kache and compiler-wrapper variables and supplies isolated HOME, config, runtime and local-only cache behavior. The bounded late command proves absent deadline enforcement; it does not prove that a current project hangs or that cache-integrity failures generally escape.

Full red-test source, baseline SHA, raw output, trace, authority and severity drivers are in [findings.json](findings.json). Replays are specified as argv arrays with workdir, timeout, failure regex and assertion regex in [replay-apt-publication.json](replay-apt-publication.json) and [replay-verify-timeout.json](replay-verify-timeout.json). The failing experimental tests are expected evidence, rather than unfinished work. From this worktree:

```sh
python3 investigation/probe-apt-publication.py
python3 investigation/probe-apt-publication.py --healthy
python3 investigation/probe-verify-timeout.py
python3 investigation/probe-verify-timeout.py --healthy
```

Both red commands exit 1 on their named independent assertion; both healthy commands exit 0. Raw outputs are [APT red](evidence/apt-publication-red.log), [APT healthy](evidence/apt-publication-control.log), [timeout red](evidence/verify-timeout-red.log) and [timeout healthy](evidence/verify-timeout-control.log). The timeout proof requires the untouched coordinator CLI at `/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache` and the baseline harness preserved at `investigation/target/debug/kache-scenario`. The harness was built successfully with the bounded command below, using an independent target directory. [Build output](evidence/harness-build.log) is preserved; the target occupies 167 MiB. Its finished binary was shared read-only with the benchmark helper.

```sh
RUSTC_WRAPPER= RUSTC_WORKSPACE_WRAPPER= HOST_CC=clang HOST_CXX=clang++ CC=clang CXX=clang++ CARGO_TARGET_DIR="$PWD/investigation/target" cargo build --locked -p kache-e2e --bin kache-scenario -j2
```

Supported-environment controls passed: CI path selection 10 tests, mutation-diff 12 tests including 40 randomized refactors, release-version consistency 5 tests, crate-publication helpers 10 tests, prefetch qualification 96 tests, resource-limit wrapper checks, AUR version 8 cases, and workflow policy 724 checks across 36 selectors plus 22 Node tests. All raw logs are in [evidence](evidence/). Initial host Python 3.9 and missing npm-dependency failures are preserved as setup evidence; final Python-dependent controls use Python 3.14 through a fixture PATH and locked npm test dependencies. These passing controls support their bounded predicates, without establishing whole-suite integrity.

[coverage.json](coverage.json) accounts for all 543 assigned primary paths: 218 reviewed, 4 sampled, 16 transferred/unreviewed and 305 collateral. Every retained production framework/script and delivery/CI configuration was read in full, including all 81 scenario definitions previously pending. Reading the scenario definitions does not claim executing their workloads. The 16 transferred benchmark source/script paths have owner `benchmark-guardrails` and remain unreviewed here; `/Users/viktor/Developer/github/kache-investigations/audit-benchmark-guardrails/investigation/coverage.json` supplies authoritative helper coverage.

The four sampled test areas are explicit: `scripts/prefetch-qualification-test.py` lines 1–190 and 1000–1252, `tests/integration_test.rs` lines 1–230 and 3390–3534, `crates/kache-e2e/src/bench_runner/tests.rs` lines 1–140, and `scripts/bench/tests/test_short.py` lines 1–100. The complete prefetch suite was executed. Repeated fixture source, helper manifests, patch payloads, generated lockfiles, licenses, media/demo assets and the symlink fixture are individually classified as collateral. Their content was inventoried rather than individually read or executed. Each ledger entry includes evidence and reopening conditions.

Structural exploration used the coordinator's codebase-memory index. [graph-coverage.json](evidence/graph-coverage.json) records Rust semantic partial coverage, two partial shell parses and five partial Helm templates. The missing Rust bindings/expanded calls/impl relationships constrain graph conclusions; all flagged retained sources/templates were read directly. Secondary configuration routing consultation was bounded to `src/config.rs` lines 1530–1595; primary ownership remains with cli-operations.

No concrete mutation-diff suppression defect or prefetch-admission bypass was established. Their checked conditions, executed controls and reopening triggers are recorded as two dismissals in `findings.json`. Live provider/auth variation, cross-platform compiler workloads, full archive fuzzing/mutation campaigns, individual scenario execution, container/Nix/Helm runtime deployment and inherited fixture config/runtime behavior remain qualification limits. The inherited-config concern was communicated without admitting an unexecuted defect. Repository instructions place mutation testing in CI; no local cargo-mutants run was attempted. Final tracked-source diff is empty.
