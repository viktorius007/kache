# Fork branch audit — 2026-10-30

Audited `origin` (`viktorius007/kache`) against `patched` at `5fd995cfd4ed81ac0c82d40e8747904994a91333` and freshly fetched `upstream` (`kunobi-ninja/kache`). All 93 fork heads were inspected. This report recommends cleanup; no branches were deleted and no PRs were closed.

## Decision

- Keep `main` and `patched` (2 branches). Only `patched` and `upstream/main` participate in the maintained sync workflow.
- Retire 59 branches: 33 exact upstream copies, 24 superseded fix branches, `stable`, and `github-saved/patched`. Of these, 12 fix branches should have their stale fork CI PRs closed before deletion; the other 47 have no open PR found in either checked repository.
- Preserve the unique contents of 32 `investigation/*` branches in one archive ref before deleting their individual branch names. These are research history, not sync dependencies. Their work is not incorporated wholesale into `patched`.

## Evidence and limits

- Fetched both remotes with pruning; checked commit ancestry, patch equivalence with `git cherry`, branch containment, and PR state on the fork and authored upstream PRs.
- The 33 upstream copies have exactly the same full commit ID as the same-named upstream branch. Some contain work absent from upstream main; deleting the fork copy does not merge or discard the upstream branch.
- For all 24 fix branches, read the upstream closure/adoption discussion, checked the replacement PR is merged, and verified its merge commit is an ancestor of both upstream main and patched. Two are separately implemented resolutions (#1524 → #1565, #1525 → #1567); the other 22 are adopted contributions. Exact original patch IDs often differ because replacements were squashed or revised.
- All 12 open fork PRs are labeled `[fork CI]` in their titles and concern already resolved upstream changes. No remaining open authored upstream PR depends on these fix branches.
- `stable` is already contained in patched, upstream main and fork main. The old saved patched snapshot has 64 non-merge commits outside current ancestry: 9 have equivalent patches, 45 are referenced by source commit in current history, and the remaining 10 scanner commits have revised counterparts in current patched history. Range comparison confirms the shadowed include/glob/macro_use work was ported with newer scanner versions and concat-binding handling. The old assembly is superseded, not a required sync input.
- Investigation snapshots contain unique reports, reproductions, logs and review material. Most change only investigation files. `investigation/contract-bin-001` additionally contains earlier executable-policy changes; `investigation/post-upload-gc` contains GC test/measurement probes; `investigation/release-performance` contains optional hotpath profiling instrumentation and its Cargo dependency. These are not all production fixes that should be merged into patched.
- No tests/build were necessary for this read-only source and PR audit. GitHub PR state and branch tips can change; recheck them immediately before deletion. Keeping upstream copies or PR merge refs elsewhere is not a substitute for archiving unique investigation work before deleting its last maintained ref.

## Every branch

| Fork branch | Decision | Evidence / prerequisite |
| --- | --- | --- |
| `bench/windows-runner-speed` | DELETE | Exact upstream/bench/windows-runner-speed copy at `729c1681da07` |
| `c/amazing-driscoll-a4d3e8` | DELETE | Exact upstream/c/amazing-driscoll-a4d3e8 copy at `3a1d7667a5bf` |
| `chore/release-workflow-v11-immutable` | DELETE | Exact upstream/chore/release-workflow-v11-immutable copy at `b4a1805e40c5` |
| `ci/bench-aube-timeout` | DELETE | Exact upstream/ci/bench-aube-timeout copy at `ea3df3e93dbc` |
| `docs/extra-inputs-and-wrapper-chaining` | DELETE | Exact upstream/docs/extra-inputs-and-wrapper-chaining copy at `719dff9d8ef2` |
| `docs/extra-inputs-central-table-design` | DELETE | Exact upstream/docs/extra-inputs-central-table-design copy at `3a9dcc07d90a` |
| `docs/readme-orientation` | DELETE | Exact upstream/docs/readme-orientation copy at `3f9e2eb36f11` |
| `docs/simpler-quickstart` | DELETE | Exact upstream/docs/simpler-quickstart copy at `59f316e06bec` |
| `docs/terminal-recordings` | DELETE | Exact upstream/docs/terminal-recordings copy at `b5b158ed0dd1` |
| `docs/unify-readme-badges` | DELETE | Exact upstream/docs/unify-readme-badges copy at `1486363ff3e0` |
| `exp/substrate-bench-convergence` | DELETE | Exact upstream/exp/substrate-bench-convergence copy at `86493cb4ce26` |
| `feat/build-timeline` | DELETE | Exact upstream/feat/build-timeline copy at `cb0c95d4ddd3` |
| `feat/cargo-mutants-acceleration` | DELETE | Exact upstream/feat/cargo-mutants-acceleration copy at `fcd56297c456` |
| `feat/daemon-cc-resume` | DELETE | Exact upstream/feat/daemon-cc-resume copy at `d092c5caf283` |
| `feat/doctor-extra-inputs` | DELETE | Exact upstream/feat/doctor-extra-inputs copy at `ee35c666d963` |
| `feat/filesystem-remote-eviction` | DELETE | Exact upstream/feat/filesystem-remote-eviction copy at `e4cc68851135` |
| `feat/oci-backend` | DELETE | Exact upstream/feat/oci-backend copy at `c8f98dfaf3a5` |
| `feat/remote-input-predictions` | DELETE | Exact upstream/feat/remote-input-predictions copy at `686a2330d0eb` |
| `feat/salt-observability` | DELETE | Exact upstream/feat/salt-observability copy at `4c53568ffbe3` |
| `fix-windows-prefetch-marker` | DELETE | Exact upstream/fix-windows-prefetch-marker copy at `15253d8605b7` |
| `fix/1454-gc-reports-pinned` | DELETE | Resolved by [upstream #1472](https://github.com/kunobi-ninja/kache/pull/1472), `aa332f972c2d` in patched and upstream |
| `fix/1456-dry-run-keeps-registry` | DELETE | Resolved by [upstream #1471](https://github.com/kunobi-ninja/kache/pull/1471), `49d3e7c3fa28` in patched and upstream |
| `fix/benchmark-guardrails-001` | CLOSE CI PR, DELETE | Resolved by [upstream #1582](https://github.com/kunobi-ninja/kache/pull/1582), `5ae996b4f3b8` in patched and upstream; close [fork #66](https://github.com/viktorius007/kache/pull/66) |
| `fix/benchmark-guardrails-002` | CLOSE CI PR, DELETE | Resolved by [upstream #1600](https://github.com/kunobi-ninja/kache/pull/1600), `51ad202c4c99` in patched and upstream; close [fork #70](https://github.com/viktorius007/kache/pull/70) |
| `fix/cache-key-and-robustness` | DELETE | Exact upstream/fix/cache-key-and-robustness copy at `14fea195de21` |
| `fix/cargo-build-001` | DELETE | Resolved by [upstream #1564](https://github.com/kunobi-ninja/kache/pull/1564), `61aa3702ffb8` in patched and upstream |
| `fix/cc-header-permutation` | CLOSE CI PR, DELETE | Resolved by [upstream #1599](https://github.com/kunobi-ninja/kache/pull/1599), `83ea1231b0d1` in patched and upstream; close [fork #61](https://github.com/viktorius007/kache/pull/61) |
| `fix/cc-link-library` | CLOSE CI PR, DELETE | Resolved by [upstream #1627](https://github.com/kunobi-ninja/kache/pull/1627), `4df16c07951a` in patched and upstream; close [fork #69](https://github.com/viktorius007/kache/pull/69) |
| `fix/cli-config-001` | CLOSE CI PR, DELETE | Resolved by [upstream #1583](https://github.com/kunobi-ninja/kache/pull/1583), `ad93ff7f2be2` in patched and upstream; close [fork #75](https://github.com/viktorius007/kache/pull/75) |
| `fix/cli-config-002` | DELETE | Resolved by [upstream #1567](https://github.com/kunobi-ninja/kache/pull/1567), `5c4752732256` in patched and upstream |
| `fix/contract-bin-001` | DELETE | Resolved by [upstream #1597](https://github.com/kunobi-ninja/kache/pull/1597), `2ca2722c8e36` in patched and upstream |
| `fix/d5` | CLOSE CI PR, DELETE | Resolved by [upstream #1623](https://github.com/kunobi-ninja/kache/pull/1623), `e03480c50740` in patched and upstream; close [fork #71](https://github.com/viktorius007/kache/pull/71) |
| `fix/env-concat-prefix` | DELETE | Resolved by [upstream #1613](https://github.com/kunobi-ninja/kache/pull/1613), `29df1e9557a3` in patched and upstream |
| `fix/ephemeral-ci-001` | CLOSE CI PR, DELETE | Resolved by [upstream #1601](https://github.com/kunobi-ninja/kache/pull/1601), `e8c36544803c` in patched and upstream; close [fork #74](https://github.com/viktorius007/kache/pull/74) |
| `fix/ev594-001` | CLOSE CI PR, DELETE | Resolved by [upstream #1612](https://github.com/kunobi-ninja/kache/pull/1612), `f74e5acff303` in patched and upstream; close [fork #85](https://github.com/viktorius007/kache/pull/85) |
| `fix/extra-inputs-unset-var` | DELETE | Exact upstream/fix/extra-inputs-unset-var copy at `0d41b16a607a` |
| `fix/filesystem-ci-hosted` | DELETE | Exact upstream/fix/filesystem-ci-hosted copy at `7cc82e77fccb` |
| `fix/guardrails-apt-publication-order` | DELETE | Resolved by [upstream #1536](https://github.com/kunobi-ninja/kache/pull/1536), `7dadafe0746f` in patched and upstream |
| `fix/key-env-001` | DELETE | Resolved by [upstream #1605](https://github.com/kunobi-ninja/kache/pull/1605), `3eb6446f0e20` in patched and upstream |
| `fix/loud-size-validation` | DELETE | Exact upstream/fix/loud-size-validation copy at `32c59fb1cb57` |
| `fix/observability-001` | DELETE | Resolved by [upstream #1565](https://github.com/kunobi-ninja/kache/pull/1565), `d6dd7a2946c6` in patched and upstream |
| `fix/observability-002` | DELETE | Resolved by [upstream #1578](https://github.com/kunobi-ninja/kache/pull/1578), `7a5b2a25a340` in patched and upstream |
| `fix/observability-003` | CLOSE CI PR, DELETE | Resolved by [upstream #1579](https://github.com/kunobi-ninja/kache/pull/1579), `b2d95e3862bf` in patched and upstream; close [fork #73](https://github.com/viktorius007/kache/pull/73) |
| `fix/package-publish-gate` | DELETE | Exact upstream/fix/package-publish-gate copy at `731c692cb29e` |
| `fix/passthrough-cleanup` | DELETE | Exact upstream/fix/passthrough-cleanup copy at `c7f251107651` |
| `fix/qa-remote-binding` | CLOSE CI PR, DELETE | Resolved by [upstream #1598](https://github.com/kunobi-ninja/kache/pull/1598), `8a7e6a51abe4` in patched and upstream; close [fork #58](https://github.com/viktorius007/kache/pull/58) |
| `fix/rd-credential-child-001` | CLOSE CI PR, DELETE | Resolved by [upstream #1590](https://github.com/kunobi-ninja/kache/pull/1590), `e998c7b1abf0` in patched and upstream; close [fork #62](https://github.com/viktorius007/kache/pull/62) |
| `fix/remote-permits-cost-002` | CLOSE CI PR, DELETE | Resolved by [upstream #1591](https://github.com/kunobi-ninja/kache/pull/1591), `483e5e97420b` in patched and upstream; close [fork #67](https://github.com/viktorius007/kache/pull/67) |
| `fix/rustdoc-test-current-dir` | DELETE | Resolved by [upstream #1609](https://github.com/kunobi-ninja/kache/pull/1609), `5bb1c478e415` in patched and upstream |
| `fix/seed-stored-artifacts` | DELETE | Resolved by [upstream #1610](https://github.com/kunobi-ninja/kache/pull/1610), `2a9bdf0967e3` in patched and upstream |
| `github-saved/patched` | DELETE | Obsolete assembled snapshot; fixes carried into maintained history (see evidence above) |
| `investigation/audit-benchmark-guardrails` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-cargo-build` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-cc-cuda-adapters` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-cli-config` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-contract-conformance` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-filesystem-targets` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-guardrails` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-key-native-inputs` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-observability` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-planner-service` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-remote-daemon` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-rust-wrapper` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-store-core` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/audit-store-link` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/cache-poisoning-audit` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/contract-bin-001` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch; includes earlier executable-policy prototype |
| `investigation/coordinator` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/ephemeral-ci` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/eviction-value` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/flaky-reports` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/guardrails-verify-timeout-unused` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/pack-publisher` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/post-upload-gc` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch; includes GC measurement/test probes |
| `investigation/qa-ci-hydration` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/qa-file-restoration` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/qa-native-inputs` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/qa-remote-validation` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/qa-store-transactions` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/qa-target-coordination` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/release-performance` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch; includes profiling prototype |
| `investigation/remote-permits` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `investigation/sweep-map` | ARCHIVE CONTENTS | Unique investigation snapshot; consolidate into one archive ref, then delete branch |
| `main` | KEEP | Fork baseline |
| `patched` | KEEP | Maintained source, fixes and repeatable sync workflow |
| `perf/build-script-restore` | DELETE | Exact upstream/perf/build-script-restore copy at `3ab3c66b0d7a` |
| `perf/cc-shadowing` | DELETE | Exact upstream/perf/cc-shadowing copy at `4e1c7795e8d4` |
| `perf/daemon-cc-handoff` | DELETE | Exact upstream/perf/daemon-cc-handoff copy at `e86bc7121207` |
| `perf/env-dep-paths-once` | DELETE | Exact upstream/perf/env-dep-paths-once copy at `5892cbfcaf7d` |
| `perf/faster-cargo-install` | DELETE | Exact upstream/perf/faster-cargo-install copy at `0831f160dec8` |
| `perf/restore-kernel-copy` | DELETE | Exact upstream/perf/restore-kernel-copy copy at `a705e467a885` |
| `perf/wrapper-startup` | DELETE | Exact upstream/perf/wrapper-startup copy at `eee65e033d8b` |
| `stable` | DELETE | Already in patched, upstream/main and origin/main |

## Minimal retained layout

`main` and `patched` remain as working branches. If historical investigation evidence is to be preserved, one archive ref can retain all 32 investigation tips through a commit with those tips as parents; use a separate archive tree rather than merging their reports or prototypes into the production tree. The installed binary and sync script do not consume that archive.

No archive ref has been created by this audit. The individual investigation branches remain the current preserved copies.
