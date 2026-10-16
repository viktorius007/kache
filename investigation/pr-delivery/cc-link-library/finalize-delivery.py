from pathlib import Path
import json, subprocess
art = Path(__file__).resolve().parent
work = Path('/Users/viktor/Developer/github/kache-prs/cc-link-library')
base = '4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=work, text=True).strip()
assert not git('status', '--porcelain')
commits = git('rev-list', '--reverse', base + '..HEAD').splitlines()
assert len(commits) == 2
assert (art/'gate-repaired-sha.txt').read_text().strip() == commits[1]
forwarded_red = (art/'red-forwarded-response.log').read_text()
assert 'wl-rsp/changed: a changed archive must run its current code' in forwarded_red
assert 'left: Some(11)' in forwarded_red and 'right: Some(23)' in forwarded_red
assert set(git('diff-tree','--no-commit-id','--name-only','-r',commits[0]).splitlines()) == {'src/compiler/cc/tests.rs','tests/cc_passthrough_args_test.rs'}
assert git('diff-tree','--no-commit-id','--name-only','-r',commits[1]) == 'src/compiler/cc.rs'
red = (art/'red.log').read_text()
assert 'named/changed: a changed archive must run its current code' in red
assert 'left: Some(11)' in red and 'right: Some(23)' in red
assert 'named-library selection must reach the exact untracked-input refusal' in (art/'red-unit.log').read_text()
assert 'response files can hide quoted library options' in (art/'red-response.log').read_text()
assert '10 passed; 0 failed' in (art/'green-repaired.log').read_text()
assert (art/'gate-repaired-exit.txt').read_text().strip() == '0'
gate = (art/'gate-repaired.log').read_text()
for test in ['changed_link_archives_use_current_code_and_explicit_files_keep_cache_hits','opt_in_named_library_links_are_refused_until_selections_are_tracked','opt_in_link_response_files_are_refused_without_compiler_parsing']:
    assert test + ' ... ok' in gate
assert len((art/'pr-body.md').read_text().split()) <= 75
files = git('diff','--name-only',base,'HEAD').splitlines()
cmd = 'CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/cc-optional-header/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check'
delivery = dict(id='cc-link-library',branch=git('branch','--show-current'),worktree=str(work),test_commit=commits[0],fix_commit=commits[1],title='Avoid stale C executables after named libraries change',body_file=str(art/'pr-body.md'),base_sha=base,gate_command=cmd,gate_exit=0,red_log=str(art/'red.log'),green_log=str(art/'green-repaired.log'),gate_log=str(art/'gate-repaired.log'),changed_files=files)
(art/'delivery.json').write_text(json.dumps(delivery,indent=2)+'\n')
(art/'delivery.patch').write_text(git('diff',base,'HEAD')+'\n')
(art/'report.md').write_text(f"""STATUS DONE
COMMIT {commits[1]}
CHANGED {len(files)}
OPEN 0
BLOCKERS none
---

Independent main-based PR, clean worktree, two commits: test-only {commits[0]}, production-only {commits[1]}. No stacked sibling changes. Private target reused sequentially after header-permutation READY.

Root cause: cc_link_file_inputs (baseline src/compiler/cc.rs:7727) skips all option tokens, including -l, and cache_key_for_link (baseline src/compiler/cc.rs:6414) therefore hashes only explicit filenames. Replacing a library selected through -l preserves that key and restores obsolete executable code. Extend existing CcCompiler::refuse_reasons (baseline src/compiler/cc.rs:6802) to pass named-library links through before lookup/publication. Normalize top-level and -Wl comma-forwarded tokens once, then refuse @ response selections as well as joined/separate -l and --library options. -Xlinker @file is refused through its top-level token. Only split -Wl arguments: comma-containing explicit filenames stay eligible. All response-file links also pass through because the existing whitespace-only expansion cannot prove compiler-interpreted library selections. Compiler selection and argv passthrough remain existing wrapper behavior.

Tradeoff: affected opt-in named-library and response-file links compile without caching until their dependencies can be tracked safely. Explicit positional object/archive links retain their existing key and publication behavior. Default links remain ordinary passthrough. No linker search/selection redesign, new helper, API, type, trait, error variant or test hook. No key version bump is needed: preflight refusal prevents old named-selection entries from being looked up.

Evidence:
- red.log: real cc/ar regression fails at named/changed executable output, actual exit11 versus expected23 after archive replacement. Cold/warm runtime outputs were correct before replacement. No production repair existed.
- red-unit.log: exact named-library Unsupported refusal missing at baseline; joined/separate and forwarded forms covered by final test.
- red-response.log: exact response-file Unsupported refusal missing at baseline; visible -o ensures admission is otherwise possible.
- green.log: first repaired runtime output was correct; a test bookkeeping assertion incorrectly treated passthrough telemetry as cache publication. Source inspection of wrapper.rs:1933 and :8155 established passthrough events are intentional. Test was corrected to exact passthrough events and zero indexed artifact entries if the index exists; executable-value assertion preserved.
- green-repaired.log: cargo test --test cc_passthrough_args_test; 10 passed, 0 failed. Real archive replacements exercise named, -Wl, -Xlinker, quoted-response, -Wl,@file, -Xlinker @file, explicit-file and default link cases.
- gate-repaired.log: {cmd}; exit0 at final tip. Fmt, Clippy and full workspace tests pass, including both exact-refusal unit tests and real-compiler regression.

Criteria → proof:
| Criterion | Evidence |
|---|---|
| Changed named archive cannot restore obsolete executable | changed_link_archives_use_current_code_and_explicit_files_keep_cache_hits executes app and requires11→23 |
| Forwarding/quoted-response forms | same real regression cases forwarded, xlinker, response; unit table covers separate/comma/--library variants |
| Preserve explicit-file caching | real explicit archive miss/hit/miss/hit across mutation; unit admits .a, comma-containing .o, -L and non-library -Wl |
| Default no-cache control | real default case and unit exact original link-mode refusal |
| No publication of untracked selections | exact passthrough per phase, zero entries in existing index; production refusal before wrapper key/store |
| Correct refusal identity | unit tests match exact single Unsupported string for named and response selections |
| Separate commits and required gate | file partitions verified by finalizer, gate-repaired-exit.txt0 with gate-repaired-sha.txt binding exact tip |

Oracle and gap/reuse details: oracle-notes.md records independent literal values, real seam, temp fixture isolation, exact executed suite search and nearest-test differences. Codebase-memory search_graph name-pattern '.*(response|link.*input|refuse_reasons).*' file-pattern src/compiler/cc.rs limit10 returned4 symbols. Existing positional input enumerator and whitespace response expander cannot safely resolve selected library bytes; extend existing refusal method and reuse existing index_rows/last_cc_event test helpers. Baseline graph Rust semantic_partial; no exhaustive absence claim. Unit nearest tests mutate explicit .o or execute one explicit link and never replace a named selected archive.

Shape/test discipline: existing method remains below size/complexity thresholds; no new production indirection or duplicated policy. Comments explain tracking/parser limitations and correct old admission comment. No suppression/skip annotations. Test-owned HOME/config/cache/runtime for wrapper and direct tool children; no global environment mutation, installed services, host/user caches or original audit proof changes. Runtime assertions precede telemetry/cache assertions and use independent11/23 values. Full suite preserves existing deferred compile/publication controls. Reviewer found forwarded -Wl,@file escaped the initial top-level @ guard at old tip8c0cd72, whose full gate had completed exit0. red-forwarded-response.log earns the new real executable failure at that old tip (11 versus23). The final gate is rerun after normalizing forwarded tokens and bound to the amended exact SHA; old gate.log remains historical evidence only.

Limits: executed macOS Apple Clang17.0.0 arm64-apple-darwin24.6.0 with real ar. No GNU/Linux, Windows, CUDA or remote concurrency execution claimed. /DEFAULTLIB, frameworks, implicit toolchain libraries, linker scripts and broader dependency discovery are outside this confirmed -l defect. Conservative prefix matching can decline similarly spelled flags, and response-file links sacrifice caching. CI mutation testing and independent review/publication remain parent/CI responsibilities.
""")
print('READY ' + str(art/'delivery.json'))
