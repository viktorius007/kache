#!/usr/bin/env python3
"""Save delivery only after the final full gate has returned its exit status."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--gate-exit', type=int, required=True)
args = parser.parse_args()
assert args.gate_exit == 0, 'a failed gate cannot be delivered READY'
root = Path(__file__).resolve().parent
worktree = Path('/Users/viktor/Developer/github/kache-prs/cc-optional-header')
base = '4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'

def git(*argv):
    return subprocess.check_output(['git', *argv], cwd=worktree, text=True).strip()

assert not git('status', '--short'), 'preserve and resolve unexpected dirty-tree state before delivery'
assert git('rev-list', '--count', base + '..HEAD') == '2', 'deliver exactly two commits'
files = git('diff', '--name-only', base + '...HEAD').splitlines()
fix = git('rev-parse', 'HEAD')
test = git('rev-parse', 'HEAD^')
body = root / 'pr-body.md'
assert len(body.read_text().split()) <= 75
assert 'cc_header_availability_creation_uses_current_compiler_output ... ok' in (root / 'gate-final.log').read_text()
command = 'CARGO_TARGET_DIR=' + str(worktree / 'target') + ' python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check'
data = dict(id='cc-optional-header', branch=git('branch', '--show-current'), worktree=str(worktree), test_commit=test, fix_commit=fix, title='Avoid stale C objects when optional headers appear', body_file=str(body), base_sha=base, gate_command=command, gate_exit=args.gate_exit, red_log=str(root/'red.log'), green_log=str(root/'gate-final.log'), gate_log=str(root/'gate-final.log'), changed_files=files)
(root/'delivery.json').write_text(json.dumps(data, indent=2)+'\n')
report = f'''STATUS: DONE
COMMIT: {fix}
CHANGED: {len(files)} files
OPEN: 0
BLOCKERS: none
---

The PR contains test-only commit {test}, followed by production fix {fix}, each based independently on upstream {base}. No original investigation evidence or generated output is committed. The tree is clean. The 50-word PR body names cc_shadowing_names, links the upstream cause, and states the conservative caching tradeoff.

The baseline real-compiler regression failed at its behavioral assertion: after optional.h was created, the executable returned 11 while the independent fixture expectation was 23 (red.log). Its first discriminating case uses discovery=0 and an operator in the source. The retained test also covers discovery=1, an operator in an included header, and CRLF identifier continuation. Cold and unchanged program results remain 11; creation requires 23. The compiler and linker are real /usr/bin/cc, caches/config/HOME are fixture-owned, and objects are removed before every wrapper invocation. The oracle is the linked program exit code, not a cache-event proxy. self-check: KEEP.

cc_check_header_availability_inputs scans all read-set paths before cache lookup or publication and refuses units spelling availability operators, including __has_include_next by prefix. It conservatively joins continued identifiers without interpreting full C preprocessing. Comment/string matches may also refuse caching. This policy intentionally trades cache reuse for correctness in those units; ordinary caching remains supported. Arbitrarily synthesized operator identifiers are not claimed as a complete lexical-analysis guarantee. Fresh-expansion caching requires additional compile-first and negative-dependency publication guards; design-assessment.md records the bounded assessment and coordinator approval outside the PR.

The affected integration suite passed all 10 tests (green.log), including changed positive headers and ordinary warm-hit controls. The first full just check passed formatting, clippy and preceding tests, then exposed the host-dependent direct-mode fixture: macOS stdio.h contains an availability probe and therefore intentionally refuses caching. Its fixture now uses a local macro-built asm alias, preserving the original real-compiler macro-safety and exact miss/hit/preprocessor-count assertions. The targeted direct-mode control passed (ordinary-control.log). The final full gate at {fix} exited 0 (gate-final.log), including the changed tests and whole workspace. Gate command: {command}.

Gap search: codebase-memory search_code '__has_include' returned 0 indexed matches; search_graph 'cc_.*(include|direct|source)|.*has_include' in src/compiler returned 28 symbols. Source fallback search '__has_include|optional.*header|missing.*header|shadowing' located existing include shadowing tests; src/compiler/cc/tests.rs:6631 deliberately ignores a name never read, and tests/cc_passthrough_args_test.rs:89 only mutates an already included header. Neither asserts compiler-visible behavior after a formerly absent header appears. The graph is the baseline coordinator index with partial Rust semantics, so no exhaustive graph-absence claim is made.

Shape self-check: the new guard is below the function size threshold, introduces no type/trait/variant/visibility hook, and reuses existing raw file reading and memchr. Existing shadowing resolution cannot validate negative dependencies; that is the recorded reason for the dedicated guard. No unrelated structural cleanup. CI owns changed-line mutation testing; no local cargo-mutants ran. Parent independently reviews and publishes, and this worker remains available for CI follow-up.
'''
(root/'report.md').write_text(report)
print('READY ' + str(root/'delivery.json'))
