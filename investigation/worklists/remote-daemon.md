# Remote objects and daemon lifecycle, concurrency and trust

Baseline: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`. Primary paths: 36; bytes: 1774977.

## Planned review depth

Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.

## Reading subdivisions

- daemon-lifecycle-handoff: 7 paths, 28698 text lines; subdivide into the listed contiguous file sections when needed.
- remote-object-backends-and-layout: 29 paths, 18039 text lines; subdivide into the listed contiguous file sections when needed.

## Obligations

- Trace exact remote reads, bounded metadata/blob/pack downloads, validation before local import, publish/merge/conditional-update conflict paths, retry/offline behavior, queued uploads and bounded growth.
- Trace daemon startup, readiness negotiation, exclusive replacement, peer admission, socket identity, draining/shutdown, task cancellation, compile handoff and transfer spools under multiple clients.
- Review credentials and CI read-only policy through the daemon environment and every transport (S3/GCS/filesystem/OCI); input source and publisher trust determine consequences.
- Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.

## Owned interactions

- compile-daemon-handoff: consult rust-wrapper; wrapper/remote → daemon/daemon_publish; failed handoff, cancellation, child ownership and spooled artifacts
- daemon-service-config: consult cli-config; Config/socket paths/service environment ↔ daemon control/replacement; read-only credential lifetime and readiness

## Sampling declarations

- Use fixture filesystem and local wire servers; live cloud/registry credential/ETag semantics require primary documentation and declared nonexecution.
- Timeout, replacement and cancellation interleavings are selected explicitly; no exhaustive concurrency claim.
- Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.

## Primary path inventory

Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.

- `docs/daemon/lifecycle.mdx` (contract-doc-or-ci; 11712 bytes; 127 text lines)
- `docs/daemon/meta.json` (contract-doc-or-ci; 62 bytes; 4 text lines)
- `docs/daemon/overview.mdx` (contract-doc-or-ci; 5109 bytes; 62 text lines)
- `docs/remote-cache/bounding.mdx` (contract-doc-or-ci; 4601 bytes; 93 text lines)
- `docs/remote-cache/ci.mdx` (contract-doc-or-ci; 11867 bytes; 169 text lines)
- `docs/remote-cache/filesystem-setup.mdx` (contract-doc-or-ci; 2778 bytes; 62 text lines)
- `docs/remote-cache/gcs-setup.mdx` (contract-doc-or-ci; 2237 bytes; 44 text lines)
- `docs/remote-cache/meta.json` (contract-doc-or-ci; 175 bytes; 13 text lines)
- `docs/remote-cache/oci-setup.mdx` (contract-doc-or-ci; 3327 bytes; 74 text lines)
- `docs/remote-cache/overview.mdx` (contract-doc-or-ci; 2571 bytes; 58 text lines)
- `docs/remote-cache/s3-setup.mdx` (contract-doc-or-ci; 8548 bytes; 145 text lines)
- `docs/remote-cache/sync.mdx` (contract-doc-or-ci; 2742 bytes; 45 text lines)
- `src/cache_remote.rs` (source-or-script; 14422 bytes; 457 text lines)
- `src/daemon.rs` (source-or-script; 402027 bytes; 9963 text lines)
- `src/daemon/tests.rs` (test-or-fixture; 530301 bytes; 14900 text lines)
- `src/daemon_control.rs` (source-or-script; 19921 bytes; 491 text lines)
- `src/daemon_lifecycle.rs` (source-or-script; 31184 bytes; 781 text lines)
- `src/daemon_publish.rs` (source-or-script; 77035 bytes; 1806 text lines)
- `src/heartbeat.rs` (source-or-script; 16794 bytes; 448 text lines)
- `src/prediction_share.rs` (source-or-script; 16672 bytes; 435 text lines)
- `src/remote.rs` (source-or-script; 51994 bytes; 1434 text lines)
- `src/remote_backend.rs` (source-or-script; 123736 bytes; 3182 text lines)
- `src/remote_backend/download_memory.rs` (source-or-script; 5297 bytes; 147 text lines)
- `src/remote_backend/oci.rs` (source-or-script; 25450 bytes; 678 text lines)
- `src/remote_backend/oci/auth.rs` (source-or-script; 3794 bytes; 105 text lines)
- `src/remote_backend/oci/tests.rs` (test-or-fixture; 59203 bytes; 1679 text lines)
- `src/remote_backend/oci/transport.rs` (source-or-script; 8944 bytes; 268 text lines)
- `src/remote_backend/s3_credentials.rs` (source-or-script; 18164 bytes; 502 text lines)
- `src/remote_backend/s3_credentials/tests.rs` (test-or-fixture; 21205 bytes; 617 text lines)
- `src/remote_layout.rs` (source-or-script; 82397 bytes; 2156 text lines)
- `src/remote_pack.rs` (source-or-script; 50953 bytes; 1403 text lines)
- `src/remote_resilience.rs` (source-or-script; 71515 bytes; 2012 text lines)
- `src/shards.rs` (source-or-script; 6737 bytes; 228 text lines)
- `src/transport.rs` (source-or-script; 12555 bytes; 309 text lines)
- `tests/filesystem_remote_test.rs` (test-or-fixture; 51303 bytes; 1322 text lines)
- `tests/s3_remote_test.rs` (test-or-fixture; 17645 bytes; 518 text lines)
