PASS
Reviewed exact clean tip bbe72d7a4f0f219dc6a7c6a0ba59311510b79563; no source edits or repeated tests/gate.
Evidence: /Users/viktor/Developer/github/kache-investigations/audit-observability/investigation/pr-delivery/observability-001/{delivery.json,red.log,green.log,gate.log,production-green.log}.
Test-only 17ec179fc72c9acfc4b94ee58f19fc5ed2ec3f87 precedes fix; only report.rs and report/tests.rs changed.
Corrected baseline red asserts leaked Skipped/Passthrough root literals; documented initial fixture-cardinality error is preserved separately.
Report suite: 100 passes; empty-root fixture discriminator fails the fixed policy oracle, restored regression passes.
Exact-tip just check exits 0; final root suite 4381 passes, zero failures, 14 ignored; corrected environment and earlier harness logs preserved.
Source report.rs:2808 applies existing redact_owned to every bypass root; empty semantics and all other fields remain intact.
Source report/tests.rs:3906 independent literal-vector oracle covers Skipped/Passthrough/empty and preserves result, crate and elapsed time.
Existing trace/root/key/path/error/transfer assertions remain; actual compiler proof retains unredacted workspace root and identical summary while redacted root is hidden.
Portable collection traversal, no new API/helper; 43-word body links pinned baseline redact_report and states the narrow cause/fix/test outcome.
Findings: none. No skip-reason fix or general privacy claim; CI mutation checks remain a landing requirement.
