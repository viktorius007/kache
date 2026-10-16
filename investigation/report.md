STATUS: DONE
COMMIT: none
CHANGED: 79 files
OPEN: 1 unresolved production-provenance item
BLOCKERS: none for checkpoint; further probe execution explicitly stopped by root
CONFIRMED: 1 conditional rollback root cause with 2 executed consequences
LIMITS: Generated missing-meta state and injected SQLite ABORT; no natural missing-meta origin, actual disk-full/commit failure, crash cut point, full compiler replay, or non-macOS runtime tested.
---

Evidence checkpoint at untouched baseline 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9. No production or committed test source was edited. Every reported test was executed against the coordinator’s existing baseline kache_store/rusqlite libraries. This report completes root’s checkpoint instruction; it does not close the production-provenance question.

The executed conditional finding is filesystem/SQL generation mismatch after failed republication. From two generated committed entries A→old and B→peer, the test explicitly removes A/meta.json. get(A) then returns None, and the ordinary claim_build API acquires A’s build lock. Republishing A with peer bytes replaces filesystem metadata and then encounters a recoverable SQLite insertion error (generated BEFORE INSERT trigger, RAISE(ABORT), code 1811). SQL rolls back to A→old and B→peer with peer refcount 1. Filesystem A/meta.json continues to list peer. The mapping and metadata therefore name different generations.

Two separately executed consequences pin this root cause:

- replacement-error exits 101 at the peer-survival assertion. After removing A, peer_blob_exists=false, peer_hit=false, peer_refcount=-1. The source additionally indicates that old references can remain after their mapping is removed; that consequence was not independently asserted by this probe. This is loss of another entry’s cache reuse, not demonstrated loss of user source or build output.
- replacement-hit-error exits 101 at the no-hit-after-failed-replacement assertion. get(A) returns a hit despite the publication error and unchanged old SQL mapping. This establishes visibility of uncommitted replacement metadata; it does not by itself establish incorrect compile bytes or a miscompilation.

Reachability has two distinct parts. Source and execution prove that a committed row with missing metadata is admitted to ordinary publication: contains requires metadata existence (store.rs 2418–2434), claim_build calls get and returns Acquired on None (2565–2578), and Rust wrapper publication uses that claim (wrapper.rs 4445 onward) before put_with_compile_time (4899). Source’s replacement commentary explicitly mentions committed-but-stranded rows (store.rs 2864 onward). However, the fixture itself manufactures the missing-meta precondition with fs::remove_file in its generated store. No natural production event was reproduced that creates this state; commentary is testimony, not proof of frequency or origin. The report therefore retains this as a conditional integrity finding with a production-provenance limitation. Root should not describe it as an unqualified naturally occurring defect without additional evidence.

The prior healthy-key direct-put lead was rejected as a production-reachability proof. healthy-claim exits 0 and observes BuildClaim::Committed; a normal caller does not publish that healthy key. The new fixture includes the cache miss and acquired lock discriminator rather than invoking unconditional replacement.

Five controls all exited 0:

- healthy-claim: the committed-entry claim bypasses publication.
- replacement-control: successful stranded replacement yields peer refcount 2; removing A returns it to 1 and preserves B’s hit.
- fresh-error: first-publication insertion failure leaves no committed A/hit; removal of uncommitted A preserves B/refcount 1.
- remove-entry-error: exact recoverable SQL error before logical entry deletion preserves metadata and both hits.
- remove-blob-error: exact recoverable SQL error during blob updates preserves metadata and both hits.

The control/failure discriminator is the presence of the generated publication ABORT trigger under the same missing-meta replacement premise. All errors are checked for their injected messages. SQL mapping/refcount checks establish that the SQL transaction rolled back; the externally observable assertions are cache hit and peer blob survival. These controls rule out a fixture that always destroys a peer or always bypasses publication.

Artifacts: transaction_probe.rs is the complete executed test source; run_probe.py creates a new fixture per replay and explicitly assigns fixture-only HOME, KACHE_CONFIG, KACHE_CACHE_DIR, KACHE_RUNTIME_DIR, CARGO_HOME, TMPDIR, TMP and TEMP. The Rust child asserts every path and resolved index/store directory stays under FIXTURE_ROOT before operations. The compiler invocation preserved real RUSTUP_HOME, cleared RUSTC_WRAPPER, used the installed rustc and existing read-only baseline rlibs; it required no dependency rebuild. Build command/env and log are in evidence/build-command.json and evidence/build.log. Probe argv/env and raw stdout/stderr are in evidence/<case>.log; the summary is evidence/results.json. Fixtures and the small standalone binary remain in investigation/. No Kache CLI, daemon, external network, user store, credentials or live cache was accessed by these probes.

cases.json contains gate-ready argv/workdir/timeout_seconds/expected_failure_regex/assertion_regex for both executed red consequences. controls.json contains replay commands and expected exit 0. findings.json embeds full red source and records four meaningful dismissals. prior-repro-publication-rollback.rs is the previous lead, preserved for context; it was not compiled or executed in this checkpoint. source-excerpts.txt preserves the source ranges inspected. graph-status.txt and put-callers.txt record the shared ready graph at baseline, with partial Rust semantic coverage (binding oracle, expanded calls and implementation relationships unavailable); caller lists are lower bounds and source corroborates the paths used here.

Sampling limits: only the described insertion and removal statement errors were executed. ABORT is an injected recoverable SQL constraint failure, not an actual disk-full, disk I/O, lock timeout, commit failure or process crash. Tests use independent publication policy without hardlinking; they do not settle the hardlinked-staging lead assigned elsewhere. No remote import, migration, index rebuild, repair, broader concurrency suite, GC invocation or Linux/Windows runtime was exercised. The cache hit consequence and metadata mismatch share the peer-loss root cause and are not counted as separate defects.

Runtime checkpoint block: root reported an agent-runtime final error, “This content was flagged for possible cybersecurity risk. If this seems wrong, try rephrasing your request.” This was outside this agent’s visible tool results and is separate from sandbox approval. No executed tool call in this checkpoint received a content-filter or approval rejection. Root explicitly instructed an evidence checkpoint without additional probes after that runtime event; no subsequent probes were run. Further fault classes and natural stranded-state provenance remain unexecuted, with no claims made from them.
