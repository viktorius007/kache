from pathlib import Path
import json, subprocess
art = Path(__file__).resolve().parent
work = Path('/Users/viktor/Developer/github/kache-prs/cc-header-permutation')
base = '4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=work, text=True).strip()
assert not git('status', '--porcelain')
commits = git('rev-list', '--reverse', base + '..HEAD').splitlines()
assert len(commits) == 2
assert set(git('diff-tree', '--no-commit-id', '--name-only', '-r', commits[0]).splitlines()) == {'src/compiler/cc/tests.rs', 'tests/cc_passthrough_args_test.rs'}
assert git('diff-tree', '--no-commit-id', '--name-only', '-r', commits[1]) == 'src/compiler/cc.rs'
assert 'left: Some(23)' in (art/'red.log').read_text()
assert 'right: Some(11)' in (art/'red.log').read_text()
assert 'a memo storing a content-only digest' in (art/'red-memo.log').read_text()
assert 'exchanging contents between mapped names' in (art/'red-unit.log').read_text()
assert '10 passed; 0 failed' in (art/'green.log').read_text()
assert (art/'gate-exit.txt').read_text().strip() == '0'
gate = (art/'gate.log').read_text()
assert 'exchanged_header_contents_compile_current_output_and_keep_checkout_hits ... ok' in gate
assert 'direct_inputs_digest_follows_names_and_content_only ... ok' in gate
assert 'a_memo_key_from_before_the_settle_rules_is_never_todays ... ok' in gate
assert len((art/'pr-body.md').read_text().split()) <= 75
files = git('diff', '--name-only', base, 'HEAD').splitlines()
cmd = 'CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/cc-optional-header/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check'
delivery = dict(id='cc-header-permutation', branch=git('branch','--show-current'), worktree=str(work), test_commit=commits[0], fix_commit=commits[1], title='Avoid stale C objects when headers exchange contents', body_file=str(art/'pr-body.md'), base_sha=base, gate_command=cmd, gate_exit=0, red_log=str(art/'red.log'), green_log=str(art/'green.log'), gate_log=str(art/'gate.log'), changed_files=files)
(art/'delivery.json').write_text(json.dumps(delivery, indent=2) + '\n')
(art/'delivery.patch').write_text(git('diff', base, 'HEAD') + '\n')
report = f"""STATUS DONE
COMMIT {commits[1]}
CHANGED {len(files)}
OPEN 0
BLOCKERS none
---

Two independent main-based commits: test-only {commits[0]}, production-only {commits[1]}. Worktree clean. Scope: one header-permutation correctness bug, no production API or new helper.

The previous digest discarded header names and sorted/deduplicated content hashes. A source including a.h then b.h therefore reused the same object key after exchanging the two files' contents. The fix hashes sorted unique pairs of prefix-mapped input names and selected hashes using existing fold_cc_memo_field. Physical fingerprint paths/stamps remain outside the digest; system headers still use raw content and project inputs mapped content. The direct-input domain changes v2 to v3 and memo identity v6 to v7, preventing persisted content-only memos from answering the new code.

Validation:
- red.log: real-cc regression failed at exchanged executable output, left Some(23), right Some(11), discovery=0. Cold, warm and relocated controls passed before the intended assertion failed.
- red-unit.log: mapping/content permutation assertion failed before production changes.
- red-memo.log: prior-v6 memo identity exclusion assertion failed before production changes.
- green.log: cargo test --test cc_passthrough_args_test; 10 passed, 0 failed. Includes both discovery modes, exact current output after swapping and warm/relocated/restored cache hits.
- gate.log: {cmd}; exit 0 at final tip. Fmt, clippy and full workspace tests passed, including strengthened direct-input and prior-v6 memo tests.

Criteria → evidence:
| Criterion | Evidence |
|---|---|
| Exchanged headers cannot return obsolete object | exchanged_header_contents_compile_current_output_and_keep_checkout_hits, real executable returns 11 after exchange instead of baseline 23 |
| Both discovery paths | same regression iterates discovery 0 and 1 |
| Equivalent checkouts retain hits | relocated phase requires local_hit and current output 23 |
| Unchanged/restored states retain hits | warm, exchanged-warm and restored phases require local_hit |
| Path/content association | direct_inputs_digest_follows_names_and_content_only requires distinct digest for swapped assignments and renamed normalized input |
| Ordering and duplicate stability | strengthened unit test includes reversed and repeated input controls |
| Old persisted memo cannot serve lossy digest | a_memo_key_from_before_the_settle_rules_is_never_todays now excludes v6 as well as v5 |
| Separate tests/fix commits and required gate | manifest SHA/file partitions, gate.log exit 0 |

Oracle and scope evidence: oracle-notes.md records exact suite search, nearest-test distinctions, fixture values, normalization controls and graph reuse result. Existing fold_cc_memo_field was reused after search_graph name-pattern '(fold_cc_memo_field|cc_direct_inputs_digest|cc_mapped_path)' file-pattern src/compiler/cc.rs returned 3 symbols. Baseline graph has Rust semantic_partial coverage; no exhaustive absence claim. The real compiler and link/executable seam remains unstubbed, expectations are test-owned literals, and telemetry asserts exact reuse outcomes after artifact assertions. Tests own temp HOME/config/cache/runtime and clear wrapper; no host state/global environment writes.

Shape: no new production symbol, module, trait, type, error or I/O seam. Existing digest remains under 100 lines and unchanged interfaces. Hash framing uses existing helper. Comments explain association and migration invariants. No suppression, skip annotation, unrelated cleanup or production test hook.

Limits: executed on macOS with host cc (Apple Clang 17.0.0, arm64-apple-darwin24.6.0); no Linux/Windows execution claimed. CI mutation testing and independent review remain parent/CI responsibilities. This repair retains normalized name associations; it does not model absent optional headers or named link-library inputs, which are independent PRs. Publication is owned by the parent.
"""
(art/'report.md').write_text(report)
print('READY ' + str(art/'delivery.json'))
