STATUS: DONE
COMMIT: none
CHANGED: 26 files
OPEN: 2 unresolved items
BLOCKERS: New probes stopped by coordinator checkpoint instruction after an agent-runtime cybersecurity flag elsewhere; this was not a tool approval rejection
CONFIRMED: 0
LIMITS: One valid-blob control executed; corruption, Cargo split-layout coordination, target seeding, held-lock controls and red proofs remain unexecuted
---

Checkpoint at untouched production baseline 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. No production source or repository test-suite edits, no Kache build, no generated Cargo build, no daemon/service changes, no external service access and no publication were performed. CHANGED counts investigation artifact files, including the generated fixture and supplied brief; all changes are inside this owned worktree's investigation directory. No commit was created.

Completed execution

The original prior probe was inspected, not executed. Its accepted `local_store` replacement still lacked full HOME/CARGO_HOME/temp isolation. The newly saved probe constructs every child environment explicitly, using fixture-only HOME, KACHE_CONFIG, KACHE_HOST_CONFIG, KACHE_CACHE_DIR, KACHE_RUNTIME_DIR, CARGO_HOME, TMPDIR/TMP/TEMP and preserving `/Users/viktor/.rustup` as RUSTUP_HOME. All child working directories are inside investigation. Before operations it asserts path containment and accepted config values match environment overrides; afterwards it asserts the fixture index exists and owns a blobs table. Runtime CLI introspection of resolved config was not added or executed, which remains an isolation-evidence limitation even though fixture files and actual observed DB initialization corroborate the chosen store.

`python3 investigation/probes/target-probes.py valid` completed successfully; full raw stdout/stderr and invocations are in logs/valid.log and commands.json. Initial baseline `targets share --json` created the fixture index and reported examined=1, size_rejected=1. The helper hashed the generated 131072-byte artifact as `24e9cbe9f25292cd57991ccab25ccbfcd965456b59098d3c3f7ff68db31ab941`. After adding that valid blob and its index row, baseline `targets share --apply --json` reported examined=1, hashed=1, matches=1, replaced=1, failed=0 and skipped_busy=0. The target inode changed from 1917394630 to 1917394664, while independent direct byte equality and SHA-256 confirmed bytes were preserved (`59f410ae5e17962412e2aed4f815918f634932f2abf084f00bb638c4db017850`). Final line: `ASSERTION_PASS valid`.

This is a positive mechanism control: the generated file really reaches the cloning path. The expectation is the generated pre-operation byte sequence, never a value read back from the blob under test. It is not a corruption proof or a coordination clearance. The corrupt fixture and endpoint-mismatch fixture were prepared in the same source but never run, so the discriminator required to establish corruption rejection has no executed evidence. control-cases.json retains the successfully executed control; replay-cases.json is intentionally empty because no confirmed finding has a red test.

Preserved artifacts

probes/target-probes.py is the complete script as executed for the valid case, also containing unexecuted proposed corrupt/endpoint/split-lock variants. The original hash helper source and executable were copied as snapshot-blake3-file.rs and snapshot-blake3-file; the executed script still names the original read-only helper, recorded in provenance.json and control-cases.json. The generated fixture `valid-6v_2tq0x` preserves config, explicit child environment, SQLite indexes, raw per-command logs, original blob and cloned target. observation.json stores the exact measured result.

Source/graph checkpoint

The shared coordinator graph was ready, indexed at 2026-10-11T05:36:35Z. Its Rust semantic coverage is partial: binding oracle, expanded calls and implementation relationships are unavailable. A bounded graph search returned nine symbols and was corroborated in source. One attempted trace used an inexact qualified name and failed `function not found`; no caller completeness follows from it. coverage.json records sampled source ranges and these limitations.

Sampled source establishes the relevant production seams: explicit `targets share` → target_dedup::run → one_pass → consider → account_match → replace_with; good-target hashing is at target_dedup.rs:685-715, while replacement validation at 1169-1227 uses lengths and endpoint reads. Cargo cleanup uses cli.rs:5212 target_in_use, which scans .cargo-lock at 5252-5290; dedup's another_build_holds and lock_profile also use that filename (808-835, 1139-1163). Seed placement resolves build-dir (target_seed/placement.rs:71-129), and before_probe feeds that directory into daemon dispatch (target_seed.rs:874-905). Seed then acquires .cargo-lock at destination and donor intermediate profiles (695 and 716). These are leads, not admitted defects: no real Cargo split lock layout or corrupted-blob failure was executed here.

Unexecuted work and stopping condition

unexecuted.json retains two unresolved investigations: same-length middle-blob corruption, and split-build-directory exclusion across cleanup/share/seed. Proposed Cargo fixtures block a generated build script using fixture-owned sentinel files, inspect lock availability from a separate process and compare split layout to default layout; none of those child processes were launched. Seed needs its own actual daemon-reachable reproduction and is not covered by those proposed CLI cases. No primary Cargo documentation was verified in this checkpoint, so the earlier report's Cargo lock semantics remain a lead rather than an independently established claim.

The coordinator first held compiler/load probes for another agent's quiet timing window. Only read/source work occurred during that hold. Immediately after release, the coordinator requested a checkpoint and explicitly prohibited new probes because root received an agent-runtime error: `Agent errored: This content was flagged for possible cybersecurity risk.` This was not an automatic tool approval rejection. Work stopped at the saved valid control; no corruption or concurrency assertion is silently promoted to evidence. Resume requires coordinator authorization before executing additional probes.
