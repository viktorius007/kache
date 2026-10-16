STATUS: READY
COMMIT: 50ec03ca1462a3316a8ba4fa61c15e4989dc7aff
CHANGED: 4 files
OPEN: 0 confirmed defects; independent review and CI mutation lane follow
BLOCKERS: none
---

Explicit emit destinations now follow the existing explicit dep-info passthrough policy. `parse_emit_value` retains destination presence, including an empty destination, and `rustc_refuse_reasons` leaves file placement and invalid-input diagnostics to rustc. A Rust-only key tag excludes legacy entries whose producer filenames were stored under ordinary emit-kind keys. Ordinary destination requests keep cache reuse; the global key version and other adapters are unchanged. Existing Rust entries need a one-time rebuild under the new key tag.

The real-compiler regression warms metadata at `out/first.rmeta`, removes outputs, then requests `out/second.rmeta` using separated emit spelling. Baseline production exits successfully but fails the requested-file assertion (`cached emit omitted requested destination`, exit 101). The repaired run creates the requested file and leaves the old filename absent. It also checks a destination outside --out-dir, direct rustc, and ordinary metadata cold/hit reuse. Output presence is nonvacuous; all compiler calls must succeed and cache events distinguish explicit passthrough from ordinary reuse.

Focused evidence: metadata suite 2/2 passes; admission matrix 1/1 passes, covering metadata/link/obj/dep-info, attached/separated spelling, an empty explicit destination, and ordinary defaults. Only metadata was exercised with real rustc; other kinds are admission controls. Fixtures isolate HOME/config/cache/runtime/output under a short external temporary root and retain installed RUSTUP_HOME; the temporary-root choice is portable.

The full `just check` gate passed (exit 0) at the recorded commit through the bounded build wrapper with the writer's inactive rust-wrapper-001 target reused exclusively. Commands and logs are recorded in delivery.json. Local mutation testing is excluded by the common brief; CI owns that verdict. Independent review and publication belong to root.

Shape: no new production function, indirection or duplicate emit parser. The existing parser and refusal branch own the policy, and key invalidation reuses fold_field. Codebase-memory search for artifact_target_path/explicit emit/parse_emit returned four hits with no truncation; existing admission test is strengthened. The previous integration helper fixes emit argv, so a local closure exercises explicit output placement. Changed production behavior is confined to args.rs, compiler/rustc.rs and cache_key.rs; metadata_streaming_test.rs carries the behavioral proof.

The final source tree is clean. Test commit: 3ababeb85177cdb50b0b6e7045bf8a65c7274d9b. Production fix commit: 50ec03ca1462a3316a8ba4fa61c15e4989dc7aff. Delivery metadata includes per-path evidence and runnable validation commands; independent review is the next handoff.
