STATUS: DONE
COMMIT: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9
CHANGED: 18 files
OPEN: 2
BLOCKERS: none
CONFIRMED: 2
LIMITS: Seven embedded test modules sampled; live service/JWT, Kubernetes HA, Linux/Windows admission, crash recovery and aggregate load unexecuted.
---

Audited the planner-service worklist at the pinned upstream commit. No production or committed test-suite edits were made. All changes are investigation artifacts, and the two open findings await owner triage. An experimental red proof is the expected result, so task completion is DONE rather than FAIL.

## Confirmed findings

### planner-service-timeline-auth — automatic authentication missing on timeline uploads

`src/timeline_client.rs:50-69` constructs the production timeline request and attaches only `config.token`. It never calls the automatic resolver that `src/planner_client.rs:43-58` uses for planning. The public CI command is wired through `src/cli.rs:484-526`; service timeline ingestion checks the same configured-auth requirement before storing (`crates/kache-service/src/timelines.rs:244-254`). The documented providers cover both POST endpoints (`docs/remote-service.mdx:42-61`).

An isolated fixture creates one real-format wrapper event, invokes the untouched baseline `kache telemetry push --all`, provides the Actions runtime URL and bearer, and records the HTTP request. The command uploads a 357-byte zstd body to `/v1/build-timelines` with **no Authorization header**, makes **no token request**, and receives the fixture's 401. It prints `warning: session audit-session not sent: service answered 401 Unauthorized: build timelines need the service's credentials` and exits 0. The expected independent assertion fails with `TIMELINE_WORKLOAD_AUTH_MISSING`.

Changing only fixture credentials to the static planner token makes the same upload carry the expected bearer and return `sent session audit-session (1 units): inserted`. This discriminates credential omission from invalid events, endpoint configuration, compression, transport failure or inability to store in the fixture.

Affected workloads: Actions jobs and users relying exclusively on the documented automatic OIDC/session providers. Static-token and open services are unaffected. The externally observed effect is lost build telemetry and a warning; builds continue. The trace also omits stored Kunobi session resolution, but the executed fixture is the Actions source. No credential disclosure is claimed.

Proof source: `investigation/probes/timeline_workload_auth.py`. Replay: `investigation/timeline-auth-replay.json`. Raw evidence: `timeline_auth_red.json`, `timeline-auth-red.log`; passing discriminator: `timeline_auth_control.json`, `timeline-auth-control.log`. `findings.json` embeds the full test source and red output.

The fixture service preserves the client authentication boundary by recording the actual outgoing header and rejecting absent credentials. It is not a live kache-service JWT verifier and its synthetic token has no valid signature. Actual service authentication refusal is source-traced; issuer/JWKS behavior is not established by this fixture.

### planner-service-stale-lease — admission bypass after the inherited lease owner exits

`src/scheduler.rs:685-695` treats a path as covering whenever its canonical parent matches this scheduler's `tests/` directory. It never checks marker existence or whether the marker's OS lock is held. `src/test_runner.rs:144-158` therefore chooses unscheduled execution for stale inherited environment. `Scheduler::begin_miss` and `keyless_compile` also suppress compile permits using this predicate (`src/scheduler.rs:379-409`), and compiler configuration reads `KACHE_TEST_LEASE` unchanged (`src/config.rs:2049`).

The isolated baseline probe first runs a Cargo-style hashed test fixture through the real `kache test-runner`. While that runner is alive, the child independently probes permit files with nonblocking shared OS locks and observes **one held slot**; it records the actual inherited marker. Once that runner has exited, an independent exclusive lock succeeds on the marker, establishing that the lease is released. Starting the second runner with the captured inherited marker then makes its child observe **zero held slots**. The assertion fails with `STALE_LEASE_BYPASS`.

Clearing only the stale environment from the second runner makes it observe **one held slot**. Both observations happen while the child and runner are alive; process-exit cleanup cannot make an absent lease appear held. The fixture recreates the environment retained by a child that outlives its test parent; it does not manufacture a fake marker or modify production.

Affected workloads: detached/deferred descendants of opt-in scheduled tests, or another process retaining such a marker after its owner has finished. They can run tests and compiler misses outside the shared concurrency and memory pool. This establishes missing admission, not an executed OOM or a throughput benchmark. Ordinary children of a still-running leased parent are a separate case.

Proof source: `investigation/probes/stale_test_lease.py`. Replay: `investigation/stale-lease-replay.json`. Raw evidence: `stale_lease_red.json`, `stale-lease-red.log`; passing discriminator: `stale_lease_control.json`, `stale-lease-control.log`. `findings.json` embeds full source/output. Runtime proof is the macOS test-runner path; compiler consequences are source-traced through the shared predicate.

## Scope, accounting and provenance

`investigation/coverage.json` accounts for every one of the 25 primary worklist paths plus consequential collateral seams. Every assigned production body, schema/configuration document and framework entry point was read. Eighteen primary files were read in full. The following seven contain deliberately sampled embedded test modules; their production regions were fully read:

| Path | Reviewed source ranges | Production region |
|---|---|---|
| crates/kache-core/src/lib.rs | 1–800 | 1–627 |
| crates/kache-service/src/lib.rs | 1–610 | 1–517 |
| crates/kache-service/src/state.rs | 1–920 | 1–696 |
| src/build_intent.rs | 1–499 | 1–361 |
| src/fallback_planner.rs | 1–493 | 1–333 |
| src/planner_auth.rs | 1–485 | 1–344 |
| src/scheduler.rs | 1–1660, 2765–2810 | 1–1435 |

Full-file reads include auth, timeline schemas/client/ingest, metrics, machine output, scheduler pressure, main/CLI/config manifests, remote layout types and the concurrent-planner test. Coverage states mark partial embedded suites as `sampled`, never complete suite coverage. No baseline Rust suite was run in this slice. Existing tests were read as clues, not accepted as proof of integrity.

The shared graph project was `Users-viktor-Developer-github-kache-investigations-coordinator`, recorded root `/Users/viktor/Developer/github/kache-investigations/coordinator`. `graph_status.txt` reports ready but Rust `semantic_partial` with binding-oracle, expanded-call and impl-relationship gaps. `graph_coverage.txt` records all 25 requested paths with no remaining page. Consequential wiring was checked in direct source; this report makes no exhaustive graph-only caller claim.

`provenance.json` records matching Git blobs for all 25 assigned paths and a clean tracked-source diff at the pinned commit. The read-only coordinator debug CLI used for proofs has SHA-256 `45840941809ca7c45622027f84d2c653c737e7ff35d375cfbf355b619456120f`. No new compiler build, real cache access, user configuration change, launchd change, external publication or local mutation run occurred.

## Meaningful dismissals and explicit limits

Six dismissal records in `findings.json` name their examined contract, closing evidence tier and reopen condition:

- Client-controlled planner/timeline values use bound SQL parameters; migration identifiers come from fixed arrays (`state.rs:341-361,365-424,466-644`).
- Projection replacement shares delete and insert in one transaction; readiness follows successful loading; legacy storage is refused without a non-empty reseed and quarantined when replaced (`state.rs:102-149,208-241`; service `lib.rs:273-276,308-334`). This is a source-level atomicity conclusion; crash and disk-full campaigns were not executed.
- Timeline compressed and decoded limits are enforced in the ingestion source (`timelines.rs:174-211,265-302`). This closes a claim of absent per-request byte limits, not aggregate-memory or retention safety.
- Planner request failures, fallback dispositions and execute-empty plans reach daemon fallback, with unresolved speculative identity work cancelled and retried through ordinary admission (`daemon.rs:6471-6661`; `fallback_planner.rs:127-174`). Full daemon runtime validation belongs to its owning slice.
- Automatic planning credentials have transport and stored-trust gates and shared refresh locking (`planner_auth.rs:49-92,161-244,298-342`, local pinned `kunobi-auth` workload source). Live login, redirects, external key rotation and issuer semantics were not emulated.
- Normal miss paths hold their guarded flight/permit through the coordinated compile and release permits before flight (`scheduler.rs:220-257,379-409`; wrapper seam ranges in coverage). The stale inherited marker is the separately executed exception; filesystem lock-sweep races belong to the store slice.

Deployment composition was read across the Helm values/Deployment and Nix module. Auth settings flow to the CLI env, HA controls readiness, PVC rollout is explicitly single writer with Recreate, and Nix settings propagate through generated TOML. No Kubernetes cluster, Helm render, Nix evaluation or HA lease loss emulation was executed. No general load, aggregate memory bound, unbounded retention safety, real cgroup behavior, power-loss durability or benchmark claim is made.

## Mechanical replay

Each replay JSON supplies the exact argv array, workdir, 30-second timeout and specific assertion/failure regex. It operates on the untouched coordinator baseline binary. Both red commands exit 1 with their expected assertion; both fixture controls exit 0. The coordinator can replay these cases and run the static/clear controls as rejected manufactured-failure cases. Test source remains experimental under investigation until a fix is approved.
