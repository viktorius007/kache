# Flaky-test investigation: kache workspace (arm: ARM)

Find the tests in this workspace whose result depends on timing, concurrency, or run order, and prove the mechanism behind each one. Report only: you fix nothing.

## Hypothesis to test, not to confirm

The owner's experience: flaky tests assert the clock rather than the mechanism, so under heavy concurrency the timing of results shifts and the test fails. The one known case below does not obviously fit that class. Classify every finding by the evidence you produce. Candidate classes, as examples and not the full extent: clock or timing assertions (sleep, elapsed, deadline, timeout); shared process state (environment variables, current directory, global statics, rlimits, signal handlers); shared filesystem paths, sockets, or ports; nondeterministic ordering; resource exhaustion (file descriptors, threads, disk).

## Known case

`compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes` (`src/compiler/cc/tests.rs:250`) failed once during a full `just check` on macOS and passed 3 of 3 runs alone:

```
thread 'compiler::cc::tests::terminal_formatting_shares_cc_keys_with_cold_and_warm_probes' panicked at src/compiler/cc/tests.rs:295:9:
assertion `left == right` failed
  left: "6a5dd9ebc2a33d878f7a0ea2cb8942db35b71cc3b4bbf8aca8d1ea4a8d5ae4d7"
 right: "ec170f0d4c633cc97b1a38b9c75e0ee2cbe2781647e22b1dca0817e436d3899a"
```

A cache key changed between two computations in one test. Explain why.

## Environment

- Worktree: `/Users/viktor/Developer/github/kache-investigations/flaky-ARM`, detached at `991c836` (upstream `main`). Read `AGENTS.md` there first; its last bullet describes the environment race with `set_env_for_test` (`src/config/tests.rs:114`).
- Export `CARGO_TARGET_DIR=/private/tmp/kache-flaky/ARM/target` for every cargo command.
- The full-suite command is the one `just test` runs: `./scripts/with-test-resources.sh cargo test --workspace`. Narrow it with `-p`, `--bin`, `--test`, a name filter, and `-- --test-threads=N` as needed.
- A second investigator runs this same task concurrently in another worktree, and unrelated heavy jobs (nextest, cppcheck) run on this machine. Record `sysctl -n vm.loadavg` next to every run. Kill nothing you did not start.

## Fences

- Write only inside your worktree and `/private/tmp/kache-flaky/ARM/`. Temporary instrumentation in your worktree is allowed; include its diff in the report.
- No commits, pushes, PRs, issue filings, or comments anywhere. Do not run `cargo mutants`.
- Do not edit `~/.cargo`, `~/.config`, the kache daemon, or any other repository.

## Budget and stop rule

At most 10 full-workspace test runs and at most 300 repetitions of any single test. Write the report when the budget is spent or after 3 hours of wall time, whichever comes first; an unfinished line of inquiry goes in the report as suspected, with the next probe that would settle it.

## Report

Write `/private/tmp/kache-flaky/ARM/report.md`. Your final message is the same content.

For each flaky test:
- Test path and `file:line`.
- Reproduction command, threads, load average, and observed failure count over runs.
- Failure output, verbatim.
- Mechanism: the specific shared state or timing dependency, cited by `file:line`, and the evidence that proves it. Proven means you made the failure happen on demand (forced interleaving, instrumentation, a controlled env change); otherwise label it suspected and state what is missing.
- Class, from the list above or a new one you name.
- Fix shape: how the test would assert the mechanism instead of the clock or the shared state.
- Severity: high (fails `just check` or CI at a rate a contributor will hit), medium (fails only under load you constructed), low (static risk, never observed failing).

Then: a static sweep summary (test code reading the clock, sleeping, or mutating process-global state outside `set_env_for_test`) with `file:line` per site and whether you observed it fail; a table of every run (command, threads, load, result); and what you checked and found stable. Finding no flaky tests beyond the known case is a valid result.
