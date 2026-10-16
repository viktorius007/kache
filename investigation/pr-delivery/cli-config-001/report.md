STATUS: DONE
COMMIT: a9f22bd37e70793bc977be3c2d96486f7a87421b
CHANGED: 3 files
OPEN: 0
BLOCKERS: none
---

The PR is based directly on 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9 and contains exactly two commits: test-only 8a404f7f75372c13b52f2623d32378bc0abc5d54, then production fix a9f22bd37e70793bc977be3c2d96486f7a87421b. The original investigation and evidence remain unchanged.

`apply_rustdoc_edit` now recognizes a commented build header. `closes_toml_table` recognizes valid commented headers for later tables, so an unrelated `[env]` rustdoc value remains untouched. Both header comments, the compiler wrapper and the native compiler settings survive the edit. The diff adds no production function, type, indirection or suppression; it changes two existing predicates and retains their callers.

The test oracle parses the input as valid TOML before invoking the editor or real `init`, then parses its output and checks the requested build rustdoc setting and retained settings. The discriminator is a trailing header comment: both newly added regressions failed on the baseline with a duplicate build table at their intended parsing assertion (red-unit.log and red.log). The unit fixture also contains a commented later `[env]` table with a literal `rustdoc = "keep"`, pinning the table boundary and repeat-edit stability. After repair, the editor/rustdoc group passed 15 tests and the init group passed 20 tests (green-unit.log and green.log).

The exact-tip `just check` exited 0 through gate.sh and the coordinated build-slot wrapper using this agent's exclusive cargo-build-001 target. Formatting, clippy with warnings denied, resource-guard checks and workspace tests passed. The full CLI suite passed 117 tests, and fallback recovery passed six tests. The first gate used a temporary global HOME/TMPDIR and failed an unchanged sandbox preflight test; focused comparisons and the final toolchain environment are documented in harness-notes.md. No unrelated source or assertion was changed.

The original real Cargo proof was replayed at the final binary with only candidate binary and disposable fixture paths adapted. Both plain and commented table cases retained valid TOML, `init` exited 0, and Cargo metadata succeeded before and after (rustdoc-config-evidence.json). Fixture HOME/config/cache are isolated under short lexical /tmp roots and host configuration is explicitly disabled. Original proof files were preserved. Independent review, cross-platform and mutation validation remain with the coordinator and CI; no local mutation or installation command was run.
