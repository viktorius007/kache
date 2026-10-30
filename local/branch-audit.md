# Fork branch audit — 2026-10-30

Audited `origin` (`viktorius007/kache`) against `patched` at `5fd995cfd4ed81ac0c82d40e8747904994a91333` and freshly fetched `upstream` (`kunobi-ninja/kache`). All 93 fork heads were inspected. The approved cleanup is complete: 91 retired branches were deleted, 12 stale fork CI PRs were closed, and all 32 investigation tips were preserved in one archive tag. The fork now has only `main` and `patched` branches.

## Completed cleanup

- Kept `main` and `patched` (2 branches). Only `patched` and `upstream/main` participate in the maintained sync workflow.
- Retired 59 branches: 33 exact upstream copies, 24 superseded fix branches, `stable`, and `github-saved/patched`. Of these, 12 fix branches had their stale fork CI PRs closed before deletion; the other 47 had no open PR in either checked repository.
- Preserved the unique contents of 32 `investigation/*` branches in the annotated tag `archive/investigations-2026-10-30`, then deleted their individual branch names. These are research history, not sync dependencies. Their work is not incorporated wholesale into `patched`.

## Evidence and limits

- Fetched both remotes with pruning; checked commit ancestry, patch equivalence with `git cherry`, branch containment, and PR state on the fork and authored upstream PRs.
- The 33 upstream copies have exactly the same full commit ID as the same-named upstream branch. Some contain work absent from upstream main; deleting the fork copy does not merge or discard the upstream branch.
- For all 24 fix branches, read the upstream closure/adoption discussion, checked the replacement PR is merged, and verified its merge commit is an ancestor of both upstream main and patched. Two are separately implemented resolutions (#1524 → #1565, #1525 → #1567); the other 22 are adopted contributions. Exact original patch IDs often differ because replacements were squashed or revised.
- All 12 open fork PRs are labeled `[fork CI]` in their titles and concern already resolved upstream changes. No remaining open authored upstream PR depends on these fix branches.
- `stable` is already contained in patched, upstream main and fork main. The old saved patched snapshot has 64 non-merge commits outside current ancestry: 9 have equivalent patches, 45 are referenced by source commit in current history, and the remaining 10 scanner commits have revised counterparts in current patched history. Range comparison confirms the shadowed include/glob/macro_use work was ported with newer scanner versions and concat-binding handling. The old assembly is superseded, not a required sync input.
- Investigation snapshots contain unique reports, reproductions, logs and review material. Most change only investigation files. `investigation/contract-bin-001` additionally contains earlier executable-policy changes; `investigation/post-upload-gc` contains GC test/measurement probes; `investigation/release-performance` contains optional hotpath profiling instrumentation and its Cargo dependency. These are not all production fixes that should be merged into patched.
- No Rust tests/build were necessary: production code was unchanged. Immediately before deletion, revalidated all 93 fork tips, the 33 exact upstream copies and the 12 expected open CI PR heads. Pushed and verified the archive first, closed the CI PRs, then deleted all 91 branches atomically with expected-tip leases. Verified the final remote heads and pruned local origin tracking refs.

## Every branch — final disposition

| Fork branch | Decision | Evidence / prerequisite |
| --- | --- | --- |
| `bench/windows-runner-speed` | DELETED | Exact upstream/bench/windows-runner-speed copy at `729c1681da07` |
| `c/amazing-driscoll-a4d3e8` | DELETED | Exact upstream/c/amazing-driscoll-a4d3e8 copy at `3a1d7667a5bf` |
| `chore/release-workflow-v11-immutable` | DELETED | Exact upstream/chore/release-workflow-v11-immutable copy at `b4a1805e40c5` |
| `ci/bench-aube-timeout` | DELETED | Exact upstream/ci/bench-aube-timeout copy at `ea3df3e93dbc` |
| `docs/extra-inputs-and-wrapper-chaining` | DELETED | Exact upstream/docs/extra-inputs-and-wrapper-chaining copy at `719dff9d8ef2` |
| `docs/extra-inputs-central-table-design` | DELETED | Exact upstream/docs/extra-inputs-central-table-design copy at `3a9dcc07d90a` |
| `docs/readme-orientation` | DELETED | Exact upstream/docs/readme-orientation copy at `3f9e2eb36f11` |
| `docs/simpler-quickstart` | DELETED | Exact upstream/docs/simpler-quickstart copy at `59f316e06bec` |
| `docs/terminal-recordings` | DELETED | Exact upstream/docs/terminal-recordings copy at `b5b158ed0dd1` |
| `docs/unify-readme-badges` | DELETED | Exact upstream/docs/unify-readme-badges copy at `1486363ff3e0` |
| `exp/substrate-bench-convergence` | DELETED | Exact upstream/exp/substrate-bench-convergence copy at `86493cb4ce26` |
| `feat/build-timeline` | DELETED | Exact upstream/feat/build-timeline copy at `cb0c95d4ddd3` |
| `feat/cargo-mutants-acceleration` | DELETED | Exact upstream/feat/cargo-mutants-acceleration copy at `fcd56297c456` |
| `feat/daemon-cc-resume` | DELETED | Exact upstream/feat/daemon-cc-resume copy at `d092c5caf283` |
| `feat/doctor-extra-inputs` | DELETED | Exact upstream/feat/doctor-extra-inputs copy at `ee35c666d963` |
| `feat/filesystem-remote-eviction` | DELETED | Exact upstream/feat/filesystem-remote-eviction copy at `e4cc68851135` |
| `feat/oci-backend` | DELETED | Exact upstream/feat/oci-backend copy at `c8f98dfaf3a5` |
| `feat/remote-input-predictions` | DELETED | Exact upstream/feat/remote-input-predictions copy at `686a2330d0eb` |
| `feat/salt-observability` | DELETED | Exact upstream/feat/salt-observability copy at `4c53568ffbe3` |
| `fix-windows-prefetch-marker` | DELETED | Exact upstream/fix-windows-prefetch-marker copy at `15253d8605b7` |
| `fix/1454-gc-reports-pinned` | DELETED | Resolved by [upstream #1472](https://github.com/kunobi-ninja/kache/pull/1472), `aa332f972c2d` in patched and upstream |
| `fix/1456-dry-run-keeps-registry` | DELETED | Resolved by [upstream #1471](https://github.com/kunobi-ninja/kache/pull/1471), `49d3e7c3fa28` in patched and upstream |
| `fix/benchmark-guardrails-001` | PR CLOSED; DELETED | Resolved by [upstream #1582](https://github.com/kunobi-ninja/kache/pull/1582), `5ae996b4f3b8` in patched and upstream; closed [fork #66](https://github.com/viktorius007/kache/pull/66) |
| `fix/benchmark-guardrails-002` | PR CLOSED; DELETED | Resolved by [upstream #1600](https://github.com/kunobi-ninja/kache/pull/1600), `51ad202c4c99` in patched and upstream; closed [fork #70](https://github.com/viktorius007/kache/pull/70) |
| `fix/cache-key-and-robustness` | DELETED | Exact upstream/fix/cache-key-and-robustness copy at `14fea195de21` |
| `fix/cargo-build-001` | DELETED | Resolved by [upstream #1564](https://github.com/kunobi-ninja/kache/pull/1564), `61aa3702ffb8` in patched and upstream |
| `fix/cc-header-permutation` | PR CLOSED; DELETED | Resolved by [upstream #1599](https://github.com/kunobi-ninja/kache/pull/1599), `83ea1231b0d1` in patched and upstream; closed [fork #61](https://github.com/viktorius007/kache/pull/61) |
| `fix/cc-link-library` | PR CLOSED; DELETED | Resolved by [upstream #1627](https://github.com/kunobi-ninja/kache/pull/1627), `4df16c07951a` in patched and upstream; closed [fork #69](https://github.com/viktorius007/kache/pull/69) |
| `fix/cli-config-001` | PR CLOSED; DELETED | Resolved by [upstream #1583](https://github.com/kunobi-ninja/kache/pull/1583), `ad93ff7f2be2` in patched and upstream; closed [fork #75](https://github.com/viktorius007/kache/pull/75) |
| `fix/cli-config-002` | DELETED | Resolved by [upstream #1567](https://github.com/kunobi-ninja/kache/pull/1567), `5c4752732256` in patched and upstream |
| `fix/contract-bin-001` | DELETED | Resolved by [upstream #1597](https://github.com/kunobi-ninja/kache/pull/1597), `2ca2722c8e36` in patched and upstream |
| `fix/d5` | PR CLOSED; DELETED | Resolved by [upstream #1623](https://github.com/kunobi-ninja/kache/pull/1623), `e03480c50740` in patched and upstream; closed [fork #71](https://github.com/viktorius007/kache/pull/71) |
| `fix/env-concat-prefix` | DELETED | Resolved by [upstream #1613](https://github.com/kunobi-ninja/kache/pull/1613), `29df1e9557a3` in patched and upstream |
| `fix/ephemeral-ci-001` | PR CLOSED; DELETED | Resolved by [upstream #1601](https://github.com/kunobi-ninja/kache/pull/1601), `e8c36544803c` in patched and upstream; closed [fork #74](https://github.com/viktorius007/kache/pull/74) |
| `fix/ev594-001` | PR CLOSED; DELETED | Resolved by [upstream #1612](https://github.com/kunobi-ninja/kache/pull/1612), `f74e5acff303` in patched and upstream; closed [fork #85](https://github.com/viktorius007/kache/pull/85) |
| `fix/extra-inputs-unset-var` | DELETED | Exact upstream/fix/extra-inputs-unset-var copy at `0d41b16a607a` |
| `fix/filesystem-ci-hosted` | DELETED | Exact upstream/fix/filesystem-ci-hosted copy at `7cc82e77fccb` |
| `fix/guardrails-apt-publication-order` | DELETED | Resolved by [upstream #1536](https://github.com/kunobi-ninja/kache/pull/1536), `7dadafe0746f` in patched and upstream |
| `fix/key-env-001` | DELETED | Resolved by [upstream #1605](https://github.com/kunobi-ninja/kache/pull/1605), `3eb6446f0e20` in patched and upstream |
| `fix/loud-size-validation` | DELETED | Exact upstream/fix/loud-size-validation copy at `32c59fb1cb57` |
| `fix/observability-001` | DELETED | Resolved by [upstream #1565](https://github.com/kunobi-ninja/kache/pull/1565), `d6dd7a2946c6` in patched and upstream |
| `fix/observability-002` | DELETED | Resolved by [upstream #1578](https://github.com/kunobi-ninja/kache/pull/1578), `7a5b2a25a340` in patched and upstream |
| `fix/observability-003` | PR CLOSED; DELETED | Resolved by [upstream #1579](https://github.com/kunobi-ninja/kache/pull/1579), `b2d95e3862bf` in patched and upstream; closed [fork #73](https://github.com/viktorius007/kache/pull/73) |
| `fix/package-publish-gate` | DELETED | Exact upstream/fix/package-publish-gate copy at `731c692cb29e` |
| `fix/passthrough-cleanup` | DELETED | Exact upstream/fix/passthrough-cleanup copy at `c7f251107651` |
| `fix/qa-remote-binding` | PR CLOSED; DELETED | Resolved by [upstream #1598](https://github.com/kunobi-ninja/kache/pull/1598), `8a7e6a51abe4` in patched and upstream; closed [fork #58](https://github.com/viktorius007/kache/pull/58) |
| `fix/rd-credential-child-001` | PR CLOSED; DELETED | Resolved by [upstream #1590](https://github.com/kunobi-ninja/kache/pull/1590), `e998c7b1abf0` in patched and upstream; closed [fork #62](https://github.com/viktorius007/kache/pull/62) |
| `fix/remote-permits-cost-002` | PR CLOSED; DELETED | Resolved by [upstream #1591](https://github.com/kunobi-ninja/kache/pull/1591), `483e5e97420b` in patched and upstream; closed [fork #67](https://github.com/viktorius007/kache/pull/67) |
| `fix/rustdoc-test-current-dir` | DELETED | Resolved by [upstream #1609](https://github.com/kunobi-ninja/kache/pull/1609), `5bb1c478e415` in patched and upstream |
| `fix/seed-stored-artifacts` | DELETED | Resolved by [upstream #1610](https://github.com/kunobi-ninja/kache/pull/1610), `2a9bdf0967e3` in patched and upstream |
| `github-saved/patched` | DELETED | Obsolete assembled snapshot; fixes carried into maintained history (see evidence above) |
| `investigation/audit-benchmark-guardrails` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-cargo-build` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-cc-cuda-adapters` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-cli-config` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-contract-conformance` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-filesystem-targets` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-guardrails` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-key-native-inputs` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-observability` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-planner-service` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-remote-daemon` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-rust-wrapper` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-store-core` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/audit-store-link` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/cache-poisoning-audit` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/contract-bin-001` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted; includes earlier executable-policy prototype |
| `investigation/coordinator` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/ephemeral-ci` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/eviction-value` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/flaky-reports` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/guardrails-verify-timeout-unused` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/pack-publisher` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/post-upload-gc` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted; includes GC measurement/test probes |
| `investigation/qa-ci-hydration` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/qa-file-restoration` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/qa-native-inputs` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/qa-remote-validation` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/qa-store-transactions` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/qa-target-coordination` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/release-performance` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted; includes profiling prototype |
| `investigation/remote-permits` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `investigation/sweep-map` | ARCHIVED; DELETED | Unique investigation snapshot; preserved in archive tag, individual branch deleted |
| `main` | KEEP | Fork baseline |
| `patched` | KEEP | Maintained source, fixes and repeatable sync workflow |
| `perf/build-script-restore` | DELETED | Exact upstream/perf/build-script-restore copy at `3ab3c66b0d7a` |
| `perf/cc-shadowing` | DELETED | Exact upstream/perf/cc-shadowing copy at `4e1c7795e8d4` |
| `perf/daemon-cc-handoff` | DELETED | Exact upstream/perf/daemon-cc-handoff copy at `e86bc7121207` |
| `perf/env-dep-paths-once` | DELETED | Exact upstream/perf/env-dep-paths-once copy at `5892cbfcaf7d` |
| `perf/faster-cargo-install` | DELETED | Exact upstream/perf/faster-cargo-install copy at `0831f160dec8` |
| `perf/restore-kernel-copy` | DELETED | Exact upstream/perf/restore-kernel-copy copy at `a705e467a885` |
| `perf/wrapper-startup` | DELETED | Exact upstream/perf/wrapper-startup copy at `eee65e033d8b` |
| `stable` | DELETED | Already in patched, upstream/main and origin/main |

## Retained layout and archive recovery

`main` and `patched` are the only remaining fork branches. The annotated tag
[`archive/investigations-2026-10-30`](https://github.com/viktorius007/kache/tree/archive/investigations-2026-10-30)
points to archive commit `04fe1e687c5a1aa604bb218097e1d4c0e561dbe9`. Its 32 parents are the
original investigation tips, preserving their complete trees and histories.
The archive tree contains only `README.md` and `branches.json`, which maps each
original branch name to its full commit ID. Research and prototypes were not
merged into production. The sync workflow does not consume the archive.

To inspect the archive or recover a particular investigation later:

```sh
git fetch origin tag archive/investigations-2026-10-30
git show archive/investigations-2026-10-30:branches.json
git ls-tree -r --name-only <original-commit>
git show <original-commit>:investigation/report.md
# Only when a working branch is needed:
git switch -c recovered-investigation <original-commit>
```

Validation confirmed every manifest tip is an ancestor of the archive commit
and the remote tag resolves to that exact archive commit. All fork PRs were
closed after cleanup. Upstream branches were not changed.
