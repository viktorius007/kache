# Investigation scope and evidence inventory

Skills loaded: codebase-memory, coding-standards (including tooling/review
references), testing-standards, verification-standards, hunt-defects, and the
shared evidence-core/findings contract. The task permits instrumenting only and
requires deliberately declared sampling limits rather than a whole-file audit.

Scope: Rust warm cache restoration, prediction/tree guards, and selected adaptive
and event-bookkeeping costs. The sampled production path is:

`main::run_wrapper_mode` → `wrapper::run` → `compute_rustc_cache_key` →
`cache_key::compute_key_into` → `resolve_key_inputs` → `predicted_key_inputs` →
`workspace_tree_digest` → `tree_digest_memoised` → `stamp_roots` →
`Stamper::walk_skipping`, then cached-artifact restoration and event reporting.

Compiler-key fields, cache lookup, emit coverage, blob materialization, restored
file hash seeding, adaptive hit observation and event assembly are examined only
where they intersect that warm path. Registry packages, remote stores, native
compiles, compiler correctness and crash consistency are outside this task's
bounded audit. No source file is certified defect-free as a whole.

Entry point: Cargo through RUSTC_WRAPPER. Actors: Cargo's four concurrent jobs,
independent wrapper processes, local filesystem, and the fixture editor. Fixtures
have no remote configuration or reachable daemon. Invariants: baseline production
source is untouched for main/v1 wall-clock measurements; each version's cache is
seeded separately; every sample owns an empty target; hits/misses are counted from
new events; diagnostic output never decides a timing verdict; source/doc edits
are explicit and cache snapshots are fixed. External observation is build wall
clock and emitted telemetry, not an internal helper return alone.

Graph project: Users-viktor-Developer-github-kache-investigations-coordinator.
Indexed root: /Users/viktor/Developer/github/kache-investigations/coordinator.
Indexed source: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9, byte-identical to this
worktree before instrumentation. `index_status`, symbol queries and coverage
results are saved under raw/graph-*.log. The five inspected Rust files have no
recorded parse problem but semantic_partial coverage: binding oracle, expanded
calls and impl relationships are unavailable, with many unresolved sites.
.cargo is excluded and was read directly. Graph edges are navigation candidates;
production call sites and behavior have been corroborated in source. No negative,
exhaustive caller, or whole-repository claim rests on these partial edges.

Evidence hierarchy: executed paired builds/profile reports; production source;
current official hotpath docs and GitHub API snapshots; release performance-gate
criteria; maintainer benchmark testimony. PR percentages remain testimony about
that separate host/workload. Passing fixture builds and profiler gating do not
prove integrity or general performance. No mutation testing is run locally; the
repository directs mutations to CI. No production repair is made.
