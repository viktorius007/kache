STATUS: DONE
COMMIT: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9
CHANGED: 236 files
OPEN: 5 unresolved items
BLOCKERS: none
CONFIRMED: 2
LIMITS: macOS aarch64/rustc 1.99.0 CLI proofs; test suites sampled; native interleaving, dylib export identity and opaque toolchain changes unexecuted
---

Two confirmed cache-key defects restore artifacts with observably wrong compiled behavior. Both tests run the untouched baseline Kache CLI, prove an unchanged warm hit, then compare the changed build's runtime output with direct rustc. Both baseline tests exit 1 at the intended cache-oracle assertion; both direct-only controls exit 0. No production change or repair was made.

**KEY-ENV-001 — absent and empty compile-time environment values collide.**

The rlib exports `option_env!("KACHE_AUDIT_SWITCH").is_some()`. A cold build with the variable absent and an unchanged warm hit both return `false`. Setting the variable to `""` produces another local hit that still returns `false`; direct rustc returns `true`.

`parse_env_dep_info` at `src/cache_key.rs:8607-8621` collapses the unset `# env-dep:VAR` record and present-empty `# env-dep:VAR=` record into the same `(VAR, String::new())`. The key fold at `3210-3247` records only name and string value. Prediction validation at `6739-6755` retains the same equivalence, so turning off predictions would not repair the key representation. The sampled prediction test at `src/cache_key/tests.rs:2655-2685` explicitly asserts that equivalence; it has no external presence oracle. The separate declared-env policy correctly distinguishes absent and empty values, but this fixture needs no declared-env configuration and exercises rustc-reported input handling.

Affected workloads use ordinary `option_env!` to select generated constants or branches, then encounter a shell/CI environment change between absent and empty. This can silently change intended semantics without changing the restored artifact. The proof establishes a wrong program value in a local cache; deployment or data loss is not claimed.

- Full replay source: [repro_env_cases.py](repro_env_cases.py).
- Exact replay case: [replay-empty.json](replay-empty.json), `python3 investigation/repro_env_cases.py empty`.
- Executed red: [empty-red.log](empty-red.log), `cached=false`, `direct=true`, `changed_cache_hit=true`.
- Green oracle control: [empty-control.log](empty-control.log), `python3 investigation/repro_env_cases.py empty --direct-only`.
- Per-stage trace, artifacts and runtime logs: `replay-empty-svqhtoyc/`; control: `replay-empty-zx6gbf_q/`.

**KEY-ENV-002 — a shadowed include macro erases a runtime OUT_DIR value.**

Equivalent producer and consumer checkouts contain:

```rust
macro_rules! include { ($path:expr) => { $path }; }
pub const BAKED: &str = include!(env!("OUT_DIR"));
pub const TEXT: &str = include_str!(concat!(env!("OUT_DIR"), "/data.txt"));
```

The custom `include!` returns the path expression, so `BAKED` is a runtime string. The genuine `include_str!` supplies the included-file evidence beneath `OUT_DIR`. The generated `data.txt` bytes and Rust source bytes are identical in both checkouts. No force/path-only allowlist is configured.

The producer cold compile and unchanged warm hit embed its own path. The consumer gets a local cache hit and embeds the producer's `checkout_a/.../out` path. Direct rustc embeds the consumer's `checkout_b/.../out` path. `env_dep_path_only_decision` at `src/cache_key.rs:5426-5484` uses the dep-info path shape plus a lexical include proof. `env_dep_source_decision` at `5639-5695` treats `IncludeLocator` as proof even when Rust resolves that name to another macro. Its comments already acknowledge this residual gap. The normalization at `5266-5350` then folds a shared OUT_DIR sentinel and permits donor restoration.

Affected workloads must combine a macro named `include`, `include_str` or `include_bytes` whose semantics bake the expression with genuine included-file proof. This is narrower than the first finding but crosses worktrees under default OUT_DIR normalization. The proved consequence is a producer path in consumer runtime output. Other residual gaps involving attribute macros, transitive macro expansion or Rust-looking text files were not executed and are not additional findings.

- Full replay source: [repro_env_cases.py](repro_env_cases.py).
- Exact replay case: [replay-locator.json](replay-locator.json), `python3 investigation/repro_env_cases.py locator`.
- Executed red: [locator-red.log](locator-red.log), producer path restored in consumer and `changed_cache_hit=true`.
- Green oracle control: [locator-control.log](locator-control.log), `python3 investigation/repro_env_cases.py locator --direct-only`.
- Per-stage trace, artifacts and runtime logs: `replay-locator-o5t9z8bt/`; control: `replay-locator-e6s9cdls/`.

**Meaningful dismissal: PGO input contents on this compiler.**

The raw `-Cprofile-use` flag initially looked path-keyed. The executed probe shows rustc 1.99.0 reports the profile file in dep-info, and ordinary source-content hashing covers it. An unchanged warm build hit; replacing bytes at the same path changed the folded profile digest and produced a miss. Invalid profile bytes also compile directly with a warning, so that warning is compiler behavior. This closes the tested missing-content-input candidate, not every PGO implementation or compiler version. Raw logs and fixture inputs are retained in `pgo-fixture/`, and the dismissal is `KEY-DISMISS-PGO-001` in [findings.json](findings.json).

**Coverage and limits.**

[coverage.json](coverage.json) accounts for every primary path in the supplied worklist and the collateral wrapper interaction. Assigned production bodies were read in full: key computation/predictions/file hashing, extra inputs, manifest identity, environment capture, native archives, native-link parsing/context, path normalization, policy, checked regions, toolchain dylibs and tree stamps. Large inline and dedicated test suites were deliberately sampled; exact read and omitted ranges are persisted. No repository test suite was executed. The behavioral probes are evidence for these two defects, not general integrity certification.

The coordinator graph `Users-viktor-Developer-github-kache-investigations-coordinator` was ready with 26,827 nodes and 149,258 edges. Rust coverage was `semantic_partial`, with binding-oracle, expanded-call and implementation-relationship gaps and many unresolved edges. Graph lookups supplied positive orientation only; production source was the review authority. No exhaustive caller claim rests on graph output.

Three source-only candidates remain explicit unresolved limits, and no additional linker/interleaving experiments were started after the coordinator narrowed completion scope:

1. Apple dynamic-library keying folds install names; export-table/current-version/compatibility-version changes preserving the install name were not exercised.
2. `hash_static_lib_for` records too-new metadata but does not visibly add the same guarded-input tracking as ordinary file hashes. Mutation between key hashing and linker consumption was not exercised; wrapper interactions may further constrain reachability.
3. Compiler binary or sysroot contents changing while reported `rustc -vV` identity remains unchanged were not exercised. The public contract documents `cache.key_salt` / `KACHE_KEY_SALT` as an opaque toolchain boundary, so source inspection alone does not establish a contract defect.

The header's five unresolved items are the two admitted findings plus these three unexecuted candidates. There is no confirmed native-linking finding from this slice. Linux, Windows, remote cache reuse, other rustc versions and load-sensitive performance were not tested here.

**Execution and preservation.**

The replay uses `/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache` read-only and `rustup which rustc` for the compiler. The tested compiler is rustc 1.99.0 (`b940084d7`, 2026-09-28), host `aarch64-apple-darwin`, LLVM 23.1.1. Each replay creates a fresh directory inside this investigation directory with its own local store/config/runtime directory, disables scheduler/deferred discovery, removes inherited Kache/Cargo controls, and directly compiles observation consumers. It never uses the user's cache, configuration or installed Kache service. Replay source includes stage timeouts and compile-success/control assertions; logs identify actual changed-build local hits.

[verification.json](verification.json) records compiler identity and baseline production diff status. `git diff --exit-code 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9 -- .` returned 0. All changed files are untracked investigation artifacts, including preserved isolated caches and executable outputs; no production repair or new commit was created. The current investigation directory occupies about 10 MiB. Scripts can be rerun with `--kache /absolute/path/to/another/baseline/kache`; they preserve each run's raw evidence in a newly named directory.
