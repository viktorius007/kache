PASS
Delivered tip: c8285860ce1c002b0e11fa1f3f8d91c4d9954387; checkout verified clean.
Baseline: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. Test-only commit: fe7fe9059d8793dbe60120765ea282573d8d891b; fix follows in delivered tip. Independent baseline branch does not inherit rust-wrapper-003 traversal changes.
Evidence root: /Users/viktor/Developer/github/kache-investigations/audit-rust-wrapper/investigation/pr-delivery/rust-wrapper-004.
Checked delivery.json, test/fix diffs and messages, red.log, green.log, rustdoc-suite.log, gate.log and pr-body.md.
Behavioral red: baseline real rustdoc fails “cached rustdoc omitted the outer doc include edit”; green regression 1/1 and rustdoc controls 39/39 pass.
Full just check: delivery gate_exit 0 at exact delivered tip; gate.log main 4382 passed/14 ignored, real outer-include regression passes, remaining workspace/doc suites complete successfully. No gate/audit rerun or source edits performed.

Findings: none blocking.

- [Attribute scan](/Users/viktor/Developer/github/kache-prs/rust-wrapper-004/src/compiler/rustdoc.rs:490) examines literal include tokens before skipping an outer attribute payload, preserving the existing path-attribute handling and avoiding interpreting arbitrary attribute module tokens as module declarations. Lexer string/comment handling prevents text from inventing includes.
- [Shared recognizer](/Users/viktor/Developer/github/kache-prs/rust-wrapper-004/src/compiler/rustdoc.rs:561) extracts the existing literal recognition/refusal logic for attribute and ordinary-body consumers. Both use the same include/include_str/include_bytes spelling check and fail closed on nonliteral arguments. Existing inner-attribute behavior remains covered; it does not depend on changing the outer-attribute branch.
- [Scanner oracle](/Users/viktor/Developer/github/kache-prs/rust-wrapper-004/src/compiler/rustdoc.rs:2203) checks outer/inner documentation, nested concat wrappers, all three include spellings, false macro/string spellings, fake module tokens, and the exact nonliteral refusal. It covers positive inclusion and false-positive boundaries.
- [Behavioral oracle](/Users/viktor/Developer/github/kache-prs/rust-wrapper-004/tests/rustdoc_outer_include_test.rs:10) warms OLD_MARKER from README.md, changes only README.md, clears generated outputs, then requires NEW_MARKER and absence of OLD_MARKER in the item HTML. Direct rustdoc agrees. Four events must be miss/local_hit/miss/local_hit, with equal keys for repeats and distinct keys across the edit. Merely succeeding, replaying old HTML or bypassing the cache cannot satisfy this test.
- Upgrade safety follows from newly collected include records entering the existing source-path/bytes artifact hash. Old stale entries computed without README.md cannot satisfy the repaired key; previously complete closures remain valid. No archive format change is introduced.
- Scope is one bug, two changed files and two commits, with test-only additions before the production fix. The helper is short and shared by two concrete consumers; no added dependency or abstraction. PathBuf/tempdir and hermetic child environments preserve existing platform handling; local real-compiler evidence is macOS and CI owns additional platforms/mutation coverage.
- Body is 46 words, states the skipped-attribute cause, shared-parser repair and successful regression/controls/gate, and links the actual defective baseline scanner branch.

Codebase-memory: coordinator baseline graph ready with partial Rust semantic coverage. scan_rust|is_include|path_attribute bounded query returned three untruncated owner hits; src/compiler/rustdoc.rs coverage was checked during adjacent review. Delivered source and independent-baseline diff verified the conclusions; no exhaustive graph claim made.
