STATUS: READY
COMMIT: eb8fb0045eea4f44adf62e61789a57f83d7d5d82
CHANGED: 2 files
OPEN: Independent review and CI mutation verdict pending
BLOCKERS: None
---

Source closures containing env! or option_env! invocations now run through real rustdoc. The adapter has no compiler-reported environment dependency closure, so this admission guard avoids pretending a partial source-name scanner can validate cached output. The guard examines lexical tokens before attribute skipping and preserves ordinary documentation caching. Existing configured environment folding remains intact for admitted source.

Oracle and executed discriminator: tests/rustdoc_environment_test.rs varies only the child process DOC_TEXT from OLD_MARKER to NEW_MARKER with unchanged source bytes. Each call removes generated output and parts directories. Baseline production fails at `cached rustdoc omitted the env macro change` (red.log, exit 101), while the separate ordinary-docs warm control passes. With the repair, NEW_MARKER HTML excludes OLD_MARKER and agrees with direct rustdoc. Three wrapped env requests report passthrough with the exact compiler-dependency refusal identity. A second fixture varies the same environment input without an env macro and requires miss/local_hit events with identical keys and STATIC_MARKER HTML. Thus a successful process, blanket bypass or whole-environment key cannot satisfy both cases.

Per-path evidence:
- src/compiler/rustdoc.rs: environment_macros_require_compiler_dependency_tracking pins env!/option_env!, both attribute contexts, all macro delimiter forms, computed names and the exact error. Comments, strings, ordinary env functions and env != expressions remain admitted. All 39 rustdoc unit tests pass (rustdoc-suite.log).
- tests/rustdoc_environment_test.rs: real compiler expansion, refreshed HTML, direct output agreement and ordinary warm reuse; both tests pass (green.log). CLI HOME/config/cache/runtime/output are isolated; child-process env values do not mutate global state.

Shape: the change adds a small concrete invocation predicate over the existing tokenizer, without types, traits, visibility or dependencies. scan_rust stays within the repository size threshold. Test-only additions are in 7fea52a8502ea0e8a4a594843afd98d5920cfab9; production guard and its contract comment are in the listed fix commit.

Reuse queries: rustdoc env/hash_file_bytes/rust_tokens graph search returned 3 untruncated hits; env-source/macro/name search returned 25 hits over 2 complete pages. Existing rust_tokens and punct_at are reused. source_env_dep_use classifies uses of a supplied variable, and parse_env_macro_name does not discover complete compiler dependencies. Their bounded baseline source explains why they cannot license safe automatic admission here. Graph Rust semantic relationships are partial; actual source and the small diff establish this scope.

Tradeoff: sources with environment macros lose cache reuse, including those with manually configured variable declarations, until compiler dependency tracking is available. This protects against existing stale entries without changing ordinary-source keys. The proof does not claim completeness for proc-macro hidden environment reads.

`just check` exited 0 at the listed commit (gate.log and gate-exit.txt). Mutation coverage belongs to CI per AGENTS.md; independent review belongs to the coordinator. Writer READY; independent review and CI mutation verdict remain pending.
