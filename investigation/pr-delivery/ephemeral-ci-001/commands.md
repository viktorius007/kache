Worktree: /Users/viktor/Developer/github/kache-prs/ephemeral-ci-001
Base: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9
Private target: /Users/viktor/Developer/github/kache-prs/ephemeral-ci-001/target

Every test/gate runs through run-check.py and coordinator build-slot.py.
Initial private-target compile used an unqualified --exact filter; it is build setup only, not the behavioral red proof.
Red: cargo test --locked --bin kache cli::tests::sync_with_client_pull_recovers_uncommitted_extracted_entry -- --exact
Green/control: cargo test --locked --bin kache cli::tests::sync_with_client_
Final gate: just check

Oracle: Real V3 download publishes metadata and authentic artifact but no committed index row. Before sync the artifact exists and contains is false. After successful sync get must return the entry and its blob bytes must equal the independently supplied fixture bytes. A second sync must make no additional GET. The test retains real extraction, filesystem and SQLite; only remote transport uses the existing in-memory backend.
