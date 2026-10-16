STATUS: DONE
COMMIT: none
CHANGED: 27 files
OPEN: 2 unresolved findings
BLOCKERS: none
CONFIRMED: 2
LIMITS: Isolated seeded-pack fixtures; no representative remote benchmark or production publisher exists at the audited SHA.
---

Audited baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Production source is unchanged. Investigation artifacts remain in this worktree. No real user cache, service, launchd configuration or installed executable was modified. The failed experimental test is the requested red proof, not a failed investigation.

The current reader works, while the requested publisher is unfinished. There are two confirmed existing resource-control defects: packed prefetch imports entries excluded by the per-plan entry limit, and it starts new pack GETs after the configured plan deadline. The ordinary v3-only path is unaffected. The missing publisher remains a tracked enhancement rather than an admitted regression.

**Current production behavior and risk map**

| Seam | Current behavior | Source |
| --- | --- | --- |
| Planning entry | Namespaced Cargo.lock context from BuildStarted and startup manifest prefetch supplies manifest key, namespace and sorted dependency shard hashes. Explicit prefetch without context stays on v3. | `src/daemon.rs:1191-1235`, `6498-6502`, `8429` |
| Publication | `build_pack`, `encode_catalog`, `PackMeta` and pack metadata keys are helpers; all calls found in Rust source are tests. The production remote upload still publishes a single-entry v3 tar.zst plus v3 manifest. | `investigation/publisher-calls.log`, `src/remote_layout.rs:239-321`, `src/cache_remote.rs:65-97` |
| Catalog discovery | Reader requires listing enabled and not refused. It LISTs one selector directory, chooses the newest syntactically valid timestamp/digest filename, GETs it, verifies digest, schema, expiry and exact manifest/namespace/shard binding. Invalid/missing newest catalog falls back to v3 rather than trying older catalogs. | `src/daemon.rs:5134-5260`, `src/remote_pack.rs:365-429` |
| Pack selection | A pack is selected when any descriptor key intersects the admitted candidate keys. Compressed pack sizes are reserved against the configured byte budget; this is followed by bounded concurrent pack GETs. | `src/daemon.rs:5260-5334` |
| Pack validation | Size must equal the catalog, full BLAKE3 must match, index version/schema/order must match, nonempty frames must be contiguous without gaps/overlap/trailing bytes, index descriptors must equal catalog descriptors. Pack cap 256 MiB, index cap 16 MiB, catalog cap 64 MiB, catalog total entries 65,536. | `src/remote_pack.rs:19-31`, `292-342`, `431-455`, `475-621` |
| Per-entry extraction | Rejects unsafe binding fields, zstd windows above 128 MiB, extraction above 8 GiB per entry, rooted/traversing/link paths; verifies current key schema, exact cache-key/crate binding, exact streamed meta.json digest and each declared artifact blob hash. | `src/remote_layout.rs:408-448`, `639-791` |
| Batch import | Store preflight checks exact on-disk metadata, safe/unique names and hashes, exact artifact sizes; it does not rehash artifacts already streamed. Installs blobs and registers the verified batch in one SQLite transaction. | `crates/kache-store/src/store.rs:3200-3370` |
| Fallback | Only successfully imported candidate keys are removed from the existing v3 coordinator. Bad/missing/incompatible/incomplete pack entries therefore remain eligible for v3; valid siblings can survive a bad entry. Pack-only unrequested siblings have no candidate-v3 fallback obligation. | `src/daemon.rs:5480-5517`, `5810-5831` |
| Concurrency | Pack catalog/GET work acquires daemon-wide speculative gate before the shared remote permit. Download claims are taken per entry after pack retrieval; unrelated on-demand v3 reads can use reserved permits during a stalled pack GET. | `src/daemon.rs:4980-5115`, `5370-5403`, `7913-7921` |

Actors examined: BuildStarted/startup planner, user-configured budgets and listing permissions, remote publishers or corrupt remote bytes, concurrent demand checks, shutdown/task cancellation, filesystem and SQLite import. No first-party concurrent pack publisher exists to execute today. Existing backend create-only behavior and the absence of production pack writers are distinct from a completed publisher concurrency contract.

**Confirmed: entry budget bypass**

`prefetch_max_keys` is documented as the maximum entries one plan may download (`src/config.rs:200-204`; `docs/getting-started/configuration.mdx:539`). Candidate truncation at `src/daemon.rs:5746-5754` applies the limit, but after selecting a pack by an admitted key, `src/daemon.rs:5370-5403` extracts every descriptor and `5413-5464` imports the entire verified batch. It never filters siblings against the admitted candidate set or remaining entry allowance.

Executed on untouched baseline production: two requested keys, `prefetch_max_keys=1`, a valid two-entry seeded catalog/pack, no local entries. The first admitted key selects the pack; both keys become committed local `Store.get` hits. The independent observable oracle expected one hit and observed two:

```text
assertion `left == right` failed: packed prefetch must honor the configured maximum entries per plan
  left: 2
 right: 1
test result: FAILED. 0 passed; 1 failed
```

Changing only the fixture's configured limit to two passes. Evidence: `entry-budget-test.rs`, `entry-budget-red.log`, `entry-budget-green.log`, `findings.json`. The double stubs only transport I/O and retains actual catalog/pack parsing, stream hashing, filesystem extraction and Store/SQLite import. The oracle checks committed availability, not a proxy counter. This satisfies the real-bug/red and manufactured-nonbug/green discriminator pair.

Severity drivers: a valid catalog may contain 65,536 entries, so a pack intersecting a single admitted candidate can trigger substantial extra extraction/hashing/disk/import work beyond a configured limit of one or default 2,000. That can contend with Rust build work and occupy node-local cache space. This is a resource-control failure; no wrong artifact bytes were admitted by this fixture. Current exposure requires externally seeded packs because baseline has no first-party publisher. The same reader will be exercised once #812 publication ships.

**Confirmed: plan deadline bypass**

The documented plan deadline limits how long a plan may keep starting downloads and is measured from dispatch (`src/config.rs:214-218`; `docs/getting-started/configuration.mdx:541`). It permits transfers already in flight to finish. The packed phase never receives that deadline: each catalog/pack GET uses a fresh restore timeout (`src/daemon.rs:5045-5115`), and the v3 phase initializes its own plan deadline only after `try_packed_prefetch` returns (`5810-5851`).

Executed fixture: plan deadline one second, restore timeout ten seconds, valid catalog GET delayed 1.5 seconds. Completing that already-started catalog transfer is allowed; starting the next pack GET after it is not. The fake transport recorded one pack GET started after dispatch plus one second. The independent oracle expected zero late starts and failed:

```text
assertion `left == right` failed: packed prefetch must not start another object after the plan dispatch deadline
  left: 1
 right: 0
test result: FAILED. 0 passed; 1 failed
```

With only catalog latency changed to zero, the same valid pack imports successfully and the no-late-start assertion passes. Evidence: `plan-deadline-test.rs`, `plan-deadline-red.log`, `plan-deadline-green.log`. `run-probes.py` clears both fixture environment toggles, runs each red/control in a separate process, and mechanically checks expected exit codes 101/0. All four runs matched expectations. The fake remote preserves real production scheduling and deadline composition; it records the actual transport start boundary rather than treating total elapsed time as a performance proxy.

Severity drivers: slow catalog discovery can allow new packed transfer, extraction and import work beyond the user-configured admission period. The following v3 coordinator also gets a fresh budget rather than the remaining dispatch budget. A multiple-pack plan can therefore keep admitting work well after its declared duration. Transfers remain individually bounded by restore timeouts; no indefinite hang or invalid artifact was demonstrated. Current first-party publication is absent, so exposure is conditional on externally seeded packs.

**Executed controls and meaningful dismissals**

The existing baseline release test binary has coordinator-declared untouched production with D5 test-only experiments. I ran seven bounded filters with `--test-threads=1`: 19 remote-pack parser/encoder tests, one independent outer/inner binding test, five packed-prefetch tests (successful batch, LIST off/refused, immediate response, bounded download-memory draining, discovery), one corruption/fallback test, one traversal/sibling/fallback test, one unrelated-demand concurrency test and one catalog timestamp mismatch/fallback test. All 29 passed. Raw commands/results: `baseline-reader-0.log` through `baseline-reader-6.log`.

Those executions close the sampled corruption, traversal, context and unrelated-demand claims; `findings.json` carries evidence and reopen conditions. They do not establish exhaustive integrity or general performance. Store size preflight is confirmed by wired source but is not presented as an independently executed importer matrix. Missing/expired/incompatible catalogs are sampled in parsing fixtures; the full daemon fallback cross-product for every catalog failure is not claimed tested here.

**Evidence-backed publisher path**

1. Select one exact manifest/namespace/shard context and an authoritative candidate inventory. Fetch and verify source v3 entries before building packs; current `build_pack` validates descriptor syntax and framing but does not decompress or verify payload artifacts. Reuse the production extraction/binding gates, including exact metadata digests, artifact names/sizes and hashes. Take a stable source snapshot while verifying so concurrent eviction/local modification cannot invalidate checked bytes before packing.
2. Group deterministic candidate payloads into capped immutable packs, favoring the same plan's likely useful entries. Reuse content-addressed pack keys and canonical catalog helpers. Emit explicit v3 fallback entries for oversize/unavailable entries. Enforce the entry/time guardrails at packed admission/import as well as the v3 path before enabling publication.
3. Publish pack bodies create-only, confirm successful or already-present content-addressed objects, then publish the immutable catalog last. Concurrent identical publishers converge on pack digests; different snapshots get different immutable catalogs. Keep v3 objects available. Do not copy `RemoteLayout::put_immutable`'s plain-PUT fallback for a new create-only requirement: `Unsupported` must retain v3 rather than silently weaken pack immutability. `RemoteBackend::put_if_absent` explicitly distinguishes Created, AlreadyExists and Unsupported (`src/remote_backend.rs:87-96`, `620-645`). S3 conditional writes use If-None-Match and first-completed-write-wins behavior, with retry handling for conflict responses documented by [AWS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html).
4. Bound catalog retention and ensure all referenced objects are durable/visible before the catalog is discoverable. Current readers select the newest filename only; publishing an incomplete newest catalog temporarily forces v3 even if an older healthy catalog exists. Catalog-last ordering avoids that window. A malformed/newest catalog falling back safely is already implemented; scanning older catalogs is a separate optimization decision.
5. Add publisher fixtures for simultaneous same/different snapshots, unsupported conditional writes, an already-present wrong body under a digest key, failure after any subset of pack writes, failure before/after catalog publication, catalog expiry and retention/GC races. Reader fixtures need a daemon-level missing-object/fallback matrix and same-key demand after extraction but before the shared batch commit. No production implementation was made in this investigation.

The [current issue](https://github.com/kunobi-ninja/kache/issues/812) asks for immutable bounded packs, pre-publication verification, batched import, v3 fallback and measured request/byte reductions. The source matches its stated reader/publisher split. This is feature-completion work; it cannot be represented as a measured production acceptance result while nothing publishes packs.

**Request and byte acceptance model, not a benchmark**

A healthy single-page, no-retry reader uses `P + 2` backend operations for P packs: one catalog LIST, one catalog GET, P pack GETs. The executed successful reader fixture asserts exactly three operations for one pack and zero v3 operations (`src/daemon/tests.rs:7644-7670`; `baseline-reader-2.log`). The object arm uses one v3 payload GET per selected entry for this phase. Therefore, excluding common discovery work, 90% reduction requires `N >= 10(P + 2)`; one pack reaches the threshold only at 30 entries. Packing two entries uses three discovery/pack operations and cannot meet the target.

For an end-to-end cold arm with Q identical planner/discovery operations, compare `(Q + P + 2)/(Q + N)`, not just the prefetch transfer phase. The condition becomes `N >= 9Q + 10P + 20`. Any full remote-key refresh LIST, HTTP retries, paginated LIST requests, HEADs, fallback GETs, publisher traffic included by the experiment, or surplus fetches must be counted on the correct arm. Existing daemon `request_count=1` values are logical backend-call receipts (`src/daemon.rs:5021-5025`, `5083-5088`); `RemoteBackend::list` drains a lister (`src/remote_backend.rs:649-700`). They alone do not demonstrate actual wire request counts. Instrument the test S3 endpoint or transport counters for acceptance and reconcile them with receipts.

For B total compressed v3 bytes of exactly the selected entries, the same payload bytes plus all catalog/framing/index bytes, surplus entries and fallback/failed downloads must stay <= 1.1B. The pack has no additional compression layer, so packing can reduce request fan-out while retaining entry-payload bytes (`src/remote_pack.rs:1-10`, `271-279`). Whether catalog/index overhead and unrequested siblings satisfy 10% depends on the representative workload. No representative reduction, cloud latency, bytes overhead or CPU tradeoff is established by the small seeded fixtures.

Acceptance experiment: preserve the same candidate inventory and remote v3 payloads for both arms; start clean isolated L1 homes/stores per run; explicitly enable catalog listing and use a valid exact selector; seed/publish catalog-last; record actual wire requests, returned bytes including LIST response bodies, receipts and real plan-start-to-availability wall time; run five clean representative object arms and five pack arms in quiet windows. Separate preparation/publication from hydration measurements and name which costs the acceptance metric includes. Coordinate whole-build and L1 lifecycle measurements with the #810 owner.

**Reproduction and provenance**

`python3 investigation/build-probe.py` regenerates a source overlay with only test-module location changed and both experimental tests appended. It links read-only prebuilt baseline dependency artifacts from `/private/tmp/kache-d5-release-target/release`; set `KACHE_INV_DEP_TARGET` to another baseline Cargo test target directory if needed. Output belongs to `investigation/pack-probe`, no shared target writes. `rustc-command.json` records the exact successful invocation; the final harness is 113,005,560 bytes (about 108 MiB); `source-hashes.json` records audited baseline hashes. Root-only thin-LTO linking was needed because the prebuilt release dependencies contain LLVM bitcode. No extra dependency build was run.

```bash
investigation/pack-probe daemon::tests::investigation_packed_prefetch_obeys_the_configured_entry_budget --exact --nocapture --test-threads=1
KACHE_INV_ALLOW_TWO=1 investigation/pack-probe daemon::tests::investigation_packed_prefetch_obeys_the_configured_entry_budget --exact --nocapture --test-threads=1
python3 investigation/run-probes.py
```

Graph: `Users-viktor-Developer-github-kache-investigations-coordinator`, pinned baseline, ready index, recorded 17 excluded files and `.cargo`, nine partial files mostly Helm. Every cited Rust path had matching graph freshness; Rust binding/expanded-call/impl relationship coverage is semantic_partial. `graph-status.log` and `graph-coverage.log` declare these gaps. Graph navigation was followed by direct source reads and an exhaustive Rust symbol-name scan over `src` and `crates` for the narrow publication-helper absence claim. Conditional compilation, dynamic dispatch and external pack writers remain static-analysis limits. No whole-codebase or no-defect claim is made.
