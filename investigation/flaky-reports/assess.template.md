# Cross-model assessment of flaky-test findings: kache workspace (assessor: ARM)

Two investigators, run on different models, each searched this workspace for flaky tests. Each listed findings the other did not prove. You assess the findings below, which come from the OTHER investigator's report. For each one, decide whether it is a real flake in an unmodified run of the test suite, and whether the stated mechanism is the one that causes it. Report only: you fix nothing.

## Findings to assess

SOURCE_REPORT is the full report. Read each finding's section there, including its reproduction command and instrumentation. The instrumentation it used is in INSTRUMENTATION.

FINDINGS

Assess these findings only. The findings both investigators agree on are out of scope: the known `terminal_formatting_shares_cc_keys_with_cold_and_warm_probes` case, `cli::tests::test_is_macos_protected`, and `sandbox_preflight_bypasses_denied_server_but_keeps_allowed_server`.

## What each verdict means

Every finding gets exactly one of these verdicts.

- **REAL**: an unmodified `./scripts/with-test-resources.sh cargo test --workspace` run, or a CI run, can reach the failing state, and the stated mechanism causes it. You need either an unforced failure, or both of the following: a forced reproduction you executed, and a cited `file:line` showing that the forced condition also occurs without instrumentation. Examples of such a condition: a real sibling test that writes that variable concurrently, or a real scheduling gap the OS can produce.
- **REAL, DIFFERENT MECHANISM**: the test can fail without instrumentation, but for a cause other than the one stated. Name it, with evidence.
- **NOT A FLAKE**: the forced condition cannot occur without instrumentation, or the failure comes from the instrumentation, the launch environment, or the investigator's own probe rather than from the test. State which, with evidence.
- **UNSETTLED**: your budget ran out before either of the above was established. State the next probe that would settle it.

A reproduction that fails under instrumentation is not REAL by itself. The question is whether the forced condition happens in an unmodified run. Re-run the investigator's reproduction before you judge it, and judge independently whether its forcing is legitimate. A verdict of NOT A FLAKE on every finding is a valid result. So is REAL on every finding.

## Environment

- Worktree: `/Users/viktor/Developer/github/kache-investigations/flaky-assess-ARM`, detached at `991c836` (upstream `main`), clean. Read `AGENTS.md` there first.
- Export `CARGO_TARGET_DIR=TARGET` for every cargo command. It already holds a build of this commit.
- The full-suite command is `./scripts/with-test-resources.sh cargo test --workspace`. Narrow it with `-p`, `--bin`, `--test`, a name filter, and `-- --test-threads=N`.
- This machine runs unrelated heavy jobs, and another assessor may run alongside you. Record `sysctl -n vm.loadavg` next to every run. Kill nothing you did not start.

## Fences

- Write only inside your worktree and `/private/tmp/kache-flaky/assess-ARM/`. Apply instrumentation in your worktree only. Revert it before you finish, and confirm with `git status --short` that the tree is clean.
- Do not edit the investigators' files under `/private/tmp/kache-flaky/opus/` or `/private/tmp/kache-flaky/sol/`; read them only.
- No commits, pushes, PRs, issue filings, or comments anywhere. Do not run `cargo mutants`.

## Budget and stop rule

At most 4 full-workspace test runs and at most 300 repetitions of any single test. Write the report when every finding has a verdict, or after 2 hours of wall time, whichever comes first. Any finding without a verdict at that point is UNSETTLED.

## Report

Write `/private/tmp/kache-flaky/assess-ARM/report.md`. Your final message is the same content.

For each finding:
- Test path.
- Verdict.
- Severity: high (fails `just check` or CI at a rate a contributor will hit), medium (fails only under load or scheduling a contributor's machine can produce but rarely does), or low (static risk).
- The investigator's claim you tested, in one sentence.
- Evidence. Commands, thread counts, load averages, failure counts, and failure output verbatim. For REAL, the `file:line` showing that the forcing condition occurs without instrumentation. For NOT A FLAKE, the evidence that it does not.
- Where your view differs from the investigator's on the mechanism, the fix shape, or the severity, and why.

Then add a run table (command, threads, load, result), and a list of what you checked and found correct in the investigator's analysis.
