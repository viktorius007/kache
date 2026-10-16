# Planning, scheduling, authentication and service state

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 25; bytes: 560410.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- http-service-state-and-auth: 12 paths, 6841 text lines; subdivide into the listed contiguous file sections when needed.
- planning-scheduling-and-resources: 13 paths, 8193 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace intent and manifest planning, fallback disposition, client-side prediction/prefetch decisions, resource permits, machine memory limits, demand signaling and service request/response schemas.
- Trace static/OIDC/GitHub auth, credential origin/trusted endpoint decisions, request/decompression bounds, SQLite writes, concurrent planner requests, timeline ingestion, metrics/health/readiness and HA leases.
- Review server startup and deployment configuration composition with Helm/Nix and CLI login/config; establish actual production consumers before relying on public API names or comments.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- compiler-flight-permits: consult rust-wrapper; scheduler/demand/machine → wrapper compile/discovery flights; permit and per-key lock lifetimes
- daemon-planner: consult remote-daemon; daemon build sessions/manifests ↔ planner_client/build_intent/remote_plan; fallback and bounded prefetch
- auth-login-client: consult cli-config; cli/login + config ↔ planner_auth/client/server auth; credential origin and trusted endpoint binding

## Sampling declarations

- Fixture HTTP/SQLite paths can run locally; Kubernetes HA leases and external OIDC key rotation are source/documentation review unless isolated emulation is executed.
- Resource/admission/load measurements require coordination for a quiet window; measured workloads do not establish global performance.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `crates/kache-core/Cargo.toml` (config-or-delivery-collateral; 1111 bytes; 32 text lines)
- `crates/kache-core/README.md` (contract-doc-or-ci; 1332 bytes; 30 text lines)
- `crates/kache-core/src/lib.rs` (source-or-script; 56308 bytes; 1522 text lines)
- `crates/kache-core/src/timeline.rs` (source-or-script; 19799 bytes; 536 text lines)
- `crates/kache-service/Cargo.toml` (config-or-delivery-collateral; 1407 bytes; 37 text lines)
- `crates/kache-service/src/auth.rs` (source-or-script; 17745 bytes; 452 text lines)
- `crates/kache-service/src/lib.rs` (source-or-script; 45616 bytes; 1273 text lines)
- `crates/kache-service/src/main.rs` (source-or-script; 7748 bytes; 232 text lines)
- `crates/kache-service/src/metrics.rs` (source-or-script; 15803 bytes; 423 text lines)
- `crates/kache-service/src/state.rs` (source-or-script; 72138 bytes; 1878 text lines)
- `crates/kache-service/src/timelines.rs` (source-or-script; 31659 bytes; 895 text lines)
- `crates/kache-service/tests/cli.rs` (test-or-fixture; 1139 bytes; 38 text lines)
- `crates/kache-service/tests/concurrent_planner_db.rs` (test-or-fixture; 6329 bytes; 170 text lines)
- `docs/how-it-works/limits.mdx` (contract-doc-or-ci; 4099 bytes; 24 text lines)
- `docs/remote-service.mdx` (contract-doc-or-ci; 7432 bytes; 130 text lines)
- `src/build_intent.rs` (source-or-script; 30014 bytes; 859 text lines)
- `src/demand.rs` (source-or-script; 4291 bytes; 140 text lines)
- `src/fallback_planner.rs` (source-or-script; 33181 bytes; 855 text lines)
- `src/machine.rs` (source-or-script; 15953 bytes; 481 text lines)
- `src/planner_auth.rs` (source-or-script; 34200 bytes; 934 text lines)
- `src/planner_client.rs` (source-or-script; 9380 bytes; 258 text lines)
- `src/remote_plan.rs` (source-or-script; 5274 bytes; 153 text lines)
- `src/scheduler.rs` (source-or-script; 119803 bytes; 3172 text lines)
- `src/scheduler/pressure.rs` (source-or-script; 9418 bytes; 259 text lines)
- `src/timeline_client.rs` (source-or-script; 9231 bytes; 251 text lines)
