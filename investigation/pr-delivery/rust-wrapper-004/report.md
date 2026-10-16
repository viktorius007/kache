STATUS: READY
COMMIT: c8285860ce1c002b0e11fa1f3f8d91c4d9954387
CHANGED: 2 files
OPEN: Independent review and CI mutation verdict pending
BLOCKERS: None
---

The source scanner now collects literal include macros inside outer attribute payloads before skipping their other tokens. Attribute module/path handling stays intact. The existing body recognizer is extracted once and shared by both production consumers, preventing divergent path/refusal rules.

Oracle and executed discriminator: tests/rustdoc_outer_include_test.rs warms OLD_MARKER from README.md, changes only that file to NEW_MARKER and removes generated directories. Baseline production fails at `cached rustdoc omitted the outer doc include edit` (red.log, exit 101). With the repair, the requested item HTML contains NEW_MARKER and excludes OLD_MARKER; direct rustdoc agrees. Miss/hit event pairs and key equality before and after the edit prove real ordinary warm reuse while the edit changes the key. Passing the compiler status alone cannot satisfy these assertions.

Per-path evidence:
- src/compiler/rustdoc.rs: the new documentation_attributes_track_literal_includes_and_skip_fake_items control covers outer and inner documentation attributes, nested concat wrappers, all three include spellings, false macro/string spellings, fake module tokens and exact nonliteral refusal. All 39 rustdoc controls pass (rustdoc-suite.log).
- tests/rustdoc_outer_include_test.rs: real rustdoc observes external file bytes, refreshed item HTML, direct compiler agreement and ordinary warm reuse; 1 test passes (green.log).

Shape: scanner and extracted recognizer stay below the repository size threshold; the helper has two production call sites. No new types, visibility, errors or dependencies. Fixtures and child environment are isolated. Test-only additions occupy the deliberately red commit; production extraction and traversal occupy the fix commit.

Reuse query: `codebase-memory-mcp cli search_graph --project Users-viktor-Developer-github-kache-investigations-coordinator --name-pattern 'scan_rust|is_include|path_attribute|include.*literal' --file-pattern rustdoc --limit 10` returned three untruncated hits. is_include, scanner test helpers and hermetic CLI helpers are reused. The literal recognizer previously lived inside scan_rust and is moved to its shared helper for the two token contexts. Rust relationship coverage is partial; indexed baseline source and bounded diff establish these concrete call sites.

`just check` exited 0 at the listed commit (gate.log and gate-exit.txt). Mutation coverage is delegated to CI as AGENTS.md requires; this is a writer handoff, with independent review handled by the coordinator.
