# Release performance investigation reproduction

Baseline main source: `4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9`.
Comparison release tag: `v1.0.0` (`36d50814a9379392d5ee637290015193d7f206ce`).
Instrumentation dependency: optional `hotpath = 0.28.6`; enable `profile-hotpath`.

All commands run in this assigned worktree with `/bin/bash`, `login=false`.
Binaries stay in `investigation/bin/`; generated source/cache fixtures stay in
`investigation/fixture/`. They are reproducible generated artifacts excluded from
Git. Raw evidence, source provenance and benchmark scripts are preserved.

Create baseline v1 source with `git archive v1.0.0 | tar -x -C investigation/baseline`.
Build the unmodified main release before applying the instrumentation diff:

```bash
RUSTC_WRAPPER= HOST_CC=clang HOST_CXX=clang++ CC=clang CXX=clang++ \
CARGO_TARGET_DIR=/private/tmp/kache-release-performance-target \
cargo build --release --bin kache -j 4
cp /private/tmp/kache-release-performance-target/release/kache investigation/bin/main-disabled
```

Build v1 with `--manifest-path investigation/baseline/Cargo.toml`, an independent
`/private/tmp/kache-release-performance-v1-target`, and the same environment;
copy the result to `investigation/bin/v1`. Build the instrumented main with
`--features profile-hotpath`; copy it to `investigation/bin/main-enabled`.

The summarizer imports the repository statistics module, which requires Python
3.10 or newer (`zip(strict=True)`); this host used Python 3.14.

After reserving a quiet machine window:

```bash
python3 investigation/paired.py --files 0 --samples 6
python3 investigation/paired.py --files 4000 --samples 6
/opt/homebrew/bin/python3.14 investigation/summarize.py
```

The fixture contains 24 independent local library crates. The only compiler
inputs are the generated `src/lib.rs` files. The 4,000 optional documentation
files and README are outside those closures. The experiment varies their
presence and README contents. It uses four Cargo jobs, `cargo build --workspace
--offline`, no incremental state, distinct isolated homes/configs/cache stores,
input predictions enabled, prediction verification off, GC and daemon publishing
disabled. The real rustc path is explicit. No daemon or launchd service is started.

Each version gets two initial seed builds. Source stamps settle for 2.1 seconds
before seeds, satisfying `TreeStamp::SETTLE`. Each unprofiled sample restores the
same version's cache snapshot and removes its target directory outside the timer.
Version order alternates by pair. Documentation samples rewrite README immediately
before each arm, so its metadata age is consistent with a first edit rather than
a previously settled edit. Events are captured from the new tail of each
log, allowing hit/miss counts and integer millisecond timing to be checked.

After both workloads, README is reset and the main seed re-primed against its new
metadata stamp. Three enabled/disabled pairs measure hotpath overhead using the
same seed. A separate disabled-binary trace run avoids conflating phase tracing
with hotpath overhead. A final instrumented documentation-edit run records both
hotpath and phase evidence for attribution. Profiler wall times never decide the
main/v1 comparison.

`summary.json` uses the median of per-pair percentage changes and the repository's existing `bench.stats.paired_change` 10,000-resample bootstrap interval and
5% / 250 ms regression gate. Six samples are a bounded local experiment;
three profiler-overhead samples are descriptive. Nested function durations and
parallel wrapper timings overlap: their sums are attribution evidence, not
wall-clock savings.

Official profiler sources consulted:

- https://github.com/pawurb/hotpath-rs
- https://hotpath.rs/functions
- https://hotpath.rs/configuration
- https://hotpath.rs/profiling_overhead

The upstream release reports a Biome workload on the maintainer's Kobe host.
Its exact Biome revision, command, environment and raw paired artifacts were
not supplied by PRs 1494/1497, their comments, or the checked-in bench scenarios.
`bench-kobe` in the source is a separate Kobe project fixture, not proof of the
maintainer's Biome benchmark configuration. This experiment cannot clear that
release gate or reproduce its precise percentage.
