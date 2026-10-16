STATUS: READY
COMMIT: 19b0c7418b5f92b5bc364a7a8510b7d6bb49f163
CHANGED: 2 files
OPEN: Independent review and CI mutation verdict pending
BLOCKERS: None
---

The collector now distinguishes an out-of-line module file from a crate root or included file. Implicit children of foo.rs resolve under foo/; mod.rs, explicit paths and includes retain their existing directories.

The oracle varies foo/child.rs documentation from OLD_MARKER to NEW_MARKER after an ordinary warm hit. Baseline production fails with `cached rustdoc omitted the nested module edit` (red.log, exit 101); the repair materializes NEW_MARKER, rejects OLD_MARKER, and agrees with direct rustdoc. Cold/warm event keys are equal before the edit, differ across the edit, and agree for repeated NEW_MARKER requests. This cannot pass by merely succeeding or bypassing the cache.

Independent review found the first repair wrongly assigned an implicit stem directory to explicit #[path] modules. The revised fixture includes a parent child.rs under #[path="renamed.rs"] pub mod foo, checks OLD_MARKER to NEW_MARKER, direct rustdoc and both warm hits. That new control fails against the exact original 71dc3d5 source (review-red.log, exit 101), while baseline production passes it. The revised collector marks only implicit modules as owners of a stem directory. Explicit-path inventory additionally excludes a decoy renamed/child.rs. The original tip and logs remain in v1 artifacts; coordinator review report is investigation/pr-delivery/reviews/rust-wrapper-003.md.

Per-path evidence:
- src/compiler/rustdoc.rs: custom crate-root, two-level non-mod.rs modules, unused sibling, include, explicit-path child and mod.rs inventory controls; all 41 rustdoc unit tests pass (rustdoc-suite.log).
- tests/rustdoc_nested_module_test.rs: real rustdoc edit correctness and direct output, with ordinary warm reuse before and after the edit; 2 tests pass (green.log).

Shape: extends the existing collector with module context; no new helper or abstraction. The changed collector remains below the repository function-size threshold. Filesystem fixtures and child-process environments are isolated. Only test additions occupy the red commit; the fix commit holds production traversal and mechanical call updates.

Reuse query: `codebase-memory-mcp cli search_graph --project Users-viktor-Developer-github-kache-investigations-coordinator --name-pattern 'source_records|collect_source|scan_rust|rustdoc.*nested' --file-pattern rustdoc --limit 8` returned three untruncated source hits. Existing source_records and hermetic CLI helpers are reused. Rust graph semantic relationships are partial; actual indexed baseline source and the bounded diff establish the changed scope.

`just check` exited 0 at the listed commit (gate.log and gate-exit.txt). Mutation coverage is delegated to CI as AGENTS.md requires; this is a writer handoff, with independent review handled by the coordinator.
