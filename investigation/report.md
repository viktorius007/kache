STATUS: DONE
COMMIT: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9
CHANGED: 3 files
OPEN: 2 unresolved native-input checks
BLOCKERS: agent-runtime content filter stopped the investigation; subsequent instruction restricted work to an evidence checkpoint
CONFIRMED: 0
LIMITS: read-only source and graph inspection only; no native-input behavioral experiment executed
---

This is an evidence checkpoint, not a completed native-input correctness verdict. The resumed instruction explicitly required read-only inspection and prohibited new experiments. There were no native experiment artifacts in this assigned worktree: `rg --files investigation` returned only `investigation/brief.md` before this report was written. No compiler build, wrapper fixture, archive mutation, dylib mutation, cache replay, or executable observation ran in this worktree. No gate-ready red test exists for a native finding, and `findings.json` is an explicitly empty array.

The runtime block reported by the coordinator was:

> Agent errored: This content was flagged for possible cybersecurity risk. If this seems wrong, try rephrasing your request.

The coordinator stated that the failed agent turn was resumed with the checkpoint-only request. This was an agent-runtime content-filter rejection, not a tool approval rejection. No tool approval rejection was reported. The resumed work did not attempt to bypass the filter or run the blocked experiments. Two initial read attempts returned `CreateProcess ... No such file or directory`; those were resolved by supplying the assigned worktree and `/bin/bash` explicitly and are separate from the runtime block.

**Checks completed and actual results.**

1. Read the assigned brief, common brief, prior native/environment report, local AGENTS.md, required standards, and shared evidence/findings contracts. Prior evidence was treated as leads rather than an imposed verdict.
2. Queried the shared read-only codebase-memory graph with `list_projects`, `index_status --project Users-viktor-Developer-github-kache-investigations-coordinator --diagnostics summary`, and bounded `search_graph` searches for native library hashing and dylib paths. The graph was ready with 26,827 nodes and 149,258 edges. Rust coverage was `semantic_partial` with `binding_oracle_unavailable`, `expanded_calls_unavailable`, and `impl_relationships_unavailable`; 127,041 call sites and 193,239 reference sites were unresolved. Consequently graph orientation cannot establish exhaustive reachability or absence.
3. Corroborated the identified bodies using source reads in this byte-identical worktree. Read `fold_native_link_inputs` and `fold_apple_install_name` at `src/cache_key.rs:4803-5098`, `FileHasher::hash_static_lib_for` at `8140-8212`, the ordinary-input restat guard around `7980-8040`, guard tracking/revalidation around `7190-7265`, the complete `src/cache_key/apple_install_name.rs`, wrapper input-race decisions around `src/wrapper.rs:4570-4615` and `6628-6660`, and the native bundle audit around `5818-5885`. Also read the dynamic-content key test at `src/cache_key/tests.rs:7420-7465` and modified-input configuration around `src/config.rs:2595-2618`.
4. Verified `git rev-parse HEAD` returned the baseline SHA above. `git diff --exit-code 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9 -- src crates Cargo.toml Cargo.lock` exited 0. No production source or committed test changed. Before checkpoint output, `git status --short` showed only the untracked `investigation/` directory.

**Unexecuted archive interleaving check.**

Source orientation: `fold_native_link_inputs` calls `FileHasher::hash_static_lib_for` for resolved native archives. That method records the too-new flag, computes structural archive digests, and may memoize them; its inspected body does not call the ordinary `guard_input`/`restat_after_read` helpers. The wrapper evaluates input changes before storing successful compilations, and the modified-input guard is opt-in with a default of false. The rlib bundle audit credits members of keyed archives by member names, so its presence alone does not demonstrate protection against changed archive bytes. These are leads, not an admitted defect.

Remaining behavioral requirement: deterministically change generated archive bytes after Kache calculates a key and before rustc consumes the archive; establish actual store/reuse behavior and compare a restored artifact's observable result with direct rustc using the restored original archive. Test the opt-in modified-input guard explicitly, and account for the rlib bundle audit if the fixture bundles native members. No such experiment executed, so production-reachable incorrect reuse remains unproven and undismissed.

**Unexecuted macOS dylib identity/content check.**

Source orientation: for Apple linked outputs, `fold_native_link_inputs` folds the install names of dylibs/stubs in selected search directories. `fold_apple_install_name` uses the parser result, directory-relative file identity, and index. The inspected Mach-O parser returns the `LC_ID_DYLIB` name and does not return export-table or current/compatibility-version values. A sampled key test deliberately preserves the key after changing dylib code bytes, because a dynamically referenced implementation can change at runtime. This test is not a behavioral oracle for changed exports or linker-copied version metadata.

Remaining behavioral requirement: hold the install name fixed while changing exports and/or dylib version identity; compare Kache's actual reuse with direct rustc and an external artifact/runtime oracle. Also run a same-export implementation-only control, since dynamic content changes can legitimately remain outside the consumer key. No such experiment executed, so no native dylib defect or dismissal is claimed.

**Prior confirmed environment evidence preserved.**

The earlier investigation at `/Users/viktor/Developer/github/kache-investigations/audit-key-native-inputs/investigation/report.md` records two executed environment findings: absent-versus-empty compile-time environment values (`KEY-ENV-001`) and a shadowed include macro causing an OUT_DIR runtime value to normalize away (`KEY-ENV-002`). Its replay sources, red logs, direct controls, gate JSON and isolated fixture stores remain in that separate worktree. This checkpoint did not rerun, copy, modify, or re-adjudicate those experiments. They are not included in this report's native confirmation count. The prior PGO dismissal and opaque-toolchain limit also remain in that report and are outside this checkpoint's narrowed scope.

All checkpoint outputs are in the assigned investigation directory. No user configuration, installed Kache, launchd service, real cache, external service, or other agent's files were changed. No additional dependency/baseline builds or benchmarks ran.
