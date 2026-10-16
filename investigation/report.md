STATUS: DONE
COMMIT: none
CHANGED: 16 files
OPEN: 2 unresolved items
BLOCKERS: none
CONFIRMED: 0
LIMITS: Full link.rs source review; one macOS green restore control; sentinel/path and readonly-state leads unexecuted by coordinator direction.
---

The delegated review admits no confirmed defect. This means no executed baseline assertion established wrong behavior; it does not establish that the restore and publication paths are defect-free. The full primary file was reviewed, and inspected production consumers are recorded in coverage.json. The coordinator directed completion without executing or extending the sentinel/path or readonly-state leads. Those remain unresolved, with no red proof or severity assigned.

The baseline is Kache 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. COMMIT is none because this investigation created no commit. CHANGED counts investigation artifacts, including the assigned brief/worklist and disposable fixture files; production files changed: zero. git diff --name-only was empty. The assigned and coordinator link.rs sources have identical SHA-256 hashes, recorded in evidence/provenance.json. The earlier #1034 report remains untouched in cache-poisoning-audit/investigation/report.md.

Source review covered all 5,015 lines of crates/kache-store/src/link.rs, including existing test bodies. The review followed native clone selection and copy/hardlink fallbacks, exclusive Unix link-count checks, executable restore permissions, private writable staging, create-only and replacing publication, cleanup guards, rewritten-content materialization, mtime handling, and dep-info root transformations. Existing tests were inspected for their oracles and failure routes; they were not executed during this delegated review.

Production reachability was checked against wrapper.rs C/C++ artifact preparation, Rust store preparation, cached artifact materialization and restore validation; prestage.rs Copy materialization; build_script.rs and outside.rs writable publication; and compiler/mod.rs in-memory dep-info transforms. The coverage record names exact inspected ranges. Other store-core paths remain the store-core agent's responsibility, and no exhaustive review of their implementation is claimed here.

Several relevant protections were identified in source. Writable C/C++ restore creates a stage beside the target, checks that a new clone is a separate inode, and falls back to copying into a rewound stage if cloning fails or produces an unsafe alias (link.rs:1033-1345). Create-only publication uses no-clobber persistence or a hardlink from the private temporary clone; replacing publication uses rename/persist replacement under an explicit caller-owned target contract (1044-1144). Unix fallback checks source link count before and after creating a target link; a losing exclusive restore removes its temporary consumer and copies instead (453-676). These are reviewed mechanisms, not new runtime proof of all races.

The one executed control examined source ACL propagation through the public writable restore API. investigation/acl-probe.rs creates a source with an explicit macOS user:nobody allow read ACL, creates an ordinary compiler-output comparison under umask 077, and calls prepare_writable_target_from_file(...).publish() using the read-only baseline kache_store rlib. The restored output did not contain the source-specific ACL; only source.o showed the ACL in the captured listing, and restored.o/compiler.o were mode 0600. The assertion passed and the process exited zero. Exact source, output, binary provenance and replay instructions are retained in acl-probe.rs, evidence/acl-probe.log, evidence/provenance.json and evidence/acl-case.json. This dismisses the tested source-ACL propagation concern only; it does not prove default-directory ACL behavior, every clone/copy route, or other platforms. The fixture did not record which data-transfer mechanism ran.

The unresolved leads are:

- Literal dep-info sentinel/path collisions. Source inspection identified sentinel rewriting at link.rs:1635-2170 and wrapper store/restore consumers. A prepared end-to-end script is retained as sentinel-replay.py, but it was never executed. No stale Cargo build, wrong output or other observable failure was demonstrated. The script is not admitted reproduction evidence.
- Shared-inode readonly-state interactions. The coordinator identified a possible store staging/discard interaction with an existing blob. Actual eligible filesystem behavior, the presence of a shared inode and a production consequence were not executed in this subreview. Store-core owns that separate implementation. APFS clone behavior cannot substitute for a demonstrated non-CoW hardlink route. No readonly-state experiment was executed after the stop instruction.

behavior-probe.rs was also prepared but never executed. README.md states that status explicitly. These prepared scripts do not contribute to CONFIRMED or to a claim of passing restore controls.

Structural exploration used the coordinator baseline codebase-memory graph. Relevant indexed files had matching metadata with no recorded parse/stale file issue. Rust semantic coverage remained partial: expanded calls, binding oracle and implementation relationships were unavailable, and link.rs had unresolved call/reference entries. Graph traces therefore identified candidate consumers; direct source reads and searches corroborated the inspected callsites. coverage.json records those limits rather than treating graph absence as evidence of no callers.

No full cargo suite, mutation run, broad stress test, crash/durability replay, Linux filesystem run or Windows filesystem run was performed. There are no executed baseline red proofs to return because no finding was admitted. findings.json contains one narrowly scoped dismissal and two explicitly unproved ambiguity records. This review's completion is the delivery of its source coverage and bounded evidence, with those limits preserved.
