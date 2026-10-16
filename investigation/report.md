STATUS: DONE
COMMIT: 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9
CHANGED: 233
OPEN: 1
BLOCKERS: none
CONFIRMED: 1
LIMITS: macOS/APFS dependency-free fixtures; bounded source comparison; primary-owner seams linked rather than replayed; no performance or cross-platform verdict
---

The independent public-contract sweep found **CONTRACT-BIN-001**: a Rust invocation with no `--crate-type` produces rustc's default executable, but Kache ignores `cache_executables=false` and caches it instead of routing through the configured fallback. Normal Cargo bin commands explicitly pass `bin`, limiting the common Cargo impact. This is an observable compiler-routing defect for custom Rust build tools and build scripts that invoke the wrapper with rustc's optional crate-type argument omitted.

The full red source, behavioral oracle, production trace, severity drivers and five evidence-cited dismissals are in `findings.json`. The 19 quoted obligations and their implementation/test evidence are in `contract-matrix.json`; `coverage.json` inventories 51 tracked documentation/schema records, the actor/invariant map and omissions.

For the red test, the same source prints `cfg!(fallback_was_used)` and the fallback invokes the real rustc with that flag. Explicit `--crate-type bin` produces `true`; omitted `--crate-type` produces `false`, despite `KACHE_CACHE_EXECUTABLES=0`. `src/args.rs:755` checks only an explicit `bin` vector element or `--test`, and `src/wrapper.rs:3802` uses that predicate for the cache-disable gate. The event evidence records explicit-bin `passthrough` with a successful fallback, followed by an implicit-bin `miss` that stores the output. No missing native-linker identity is claimed: `invokes_linker` already treats an empty crate-type list as linked.

The [Rust Reference](https://doc.rust-lang.org/reference/linkage.html#linkage) specifies that `bin` is the default crate type. Kache's configuration contract says the option controls eligible Rust bins/test executables, and `docs/getting-started/comparison.mdx` says ordinary passthroughs go to the configured fallback. The executed runtime output proves the consequence without relying on event logs alone.

Replay the admitted failure with:

```bash
python3 investigation/default_bin_policy.py
```

Expected exit: **1**, ending with `AssertionError: executable caching disabled must route default-bin rustc invocation through fallback; expected true, observed false`. The machine recipe is `default-bin-policy-case.json`, and raw output is `raw/default-bin-policy.log`. Run `python3 investigation/default_bin_policy.py --negative-control` for the manufactured false-claim control: it exits **0**, so a replay gate requiring a failing property assertion rejects it. Its log and separate case JSON are persisted. Both runs used untouched baseline production code.

The independent positive controls completed:

- `python3 investigation/contract_probes.py` exited **0**: `ALL PUBLIC-CONTRACT PROBES PASSED`. The second checkout restored a 2,822,323-byte binary with `compiler_runs=0`; changing a reported nonempty environment value or Cargo feature produced the expected fresh runtime output. Ordinary `env!("CARGO_MANIFEST_DIR")` kept each checkout's own path.
- The canonical build-script fixture restored its run (`build_script_run local_hit`, 9 output bytes) and generated consumer, then returned `second:old` after its declared file changed and `second:new` after its declared environment changed. This demonstrates declared-input behavior for canonical declaration spelling.
- `python3 investigation/fallback_probes.py` exited **0**. Explicit-bin fallback exit 42 and spawn failure recovered with the direct compiler's runtime output; exits 130 and 143 propagated without creating a direct binary; `KACHE_DISABLED=1` skipped the configured fallback. These assertions observe produced/absent executable output as well as status.

These controls do not refute primary-owner edge findings. The key reviewer relayed **KEY-ENV-001** (unset/empty `option_env!` presence) and **KEY-ENV-002** (shadowed include macro defeats path-locator proof). The Cargo reviewer persisted **cargo-build-001**, showing a padded `rerun-if-env-changed` declaration recognized by real Cargo but missed by Kache's run parser; its canonical control passes. Their report/proof references are recorded separately in the matrix and are not duplicate findings in this sweep.

Meaningful dismissals are grounded in explicit public limits: undeclared build-script PATH/system probes; transformed root values such as hashes/lengths in nonhermetic runs; runtime manifest-path misses needed to preserve embedded values; aggregate compiler-work counters rather than elapsed-speedup guarantees; and unsupported Rust 1.99 rustdoc merge interfaces. Each dismissal records what would reopen it.

Graph orientation used `Users-viktor-Developer-github-kache-investigations-coordinator` at the pinned baseline. Its index reports `semantic_partial` for Rust with binding, expanded-call and impl-relationship omissions; `raw/graph-status.txt` preserves the status. Bounded source reads closed the relevant argument, wrapper, key and fallback wiring. The sweep is not an exhaustive statement-level production audit, and it does not infer integrity from a green suite. Store crash behavior, concurrent coalescing, remote providers, Linux/Windows execution, custom toolchain qualification and performance are delegated or explicit sampling omissions.

All generated state is under this worktree's `investigation/`; the retained scratch fixtures occupy about 108 MiB and raw evidence about 250 KiB. No production source, installed Kache, user configuration, real cache or service was changed. `git diff --exit-code` passed at the reviewed SHA. `raw/baseline-provenance.json` records the baseline CLI path and SHA-256. No repository build, mutation run or production repair was performed; the experimental red is expected evidence, not an incomplete task.
