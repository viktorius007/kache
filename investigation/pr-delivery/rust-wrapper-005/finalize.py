from pathlib import Path
import json
import subprocess

p = Path(__file__).parent
worktree = Path('/Users/viktor/Developer/github/kache-prs/rust-wrapper-005')
assert (p / 'gate-exit.txt').read_text().strip() == '0'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=worktree, text=True).strip() == 'eb8fb0045eea4f44adf62e61789a57f83d7d5d82'
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=worktree, text=True)
target = 'CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/rust-wrapper-001/target '
slot = 'python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py '
record = dict(
    id='rust-wrapper-005', branch='fix/rust-wrapper-005', worktree=str(worktree),
    test_commit='7fea52a8502ea0e8a4a594843afd98d5920cfab9',
    fix_commit='eb8fb0045eea4f44adf62e61789a57f83d7d5d82',
    title='fix: pass Rust environment macros through to rustdoc',
    body_file=str(p / 'pr-body.md'), base_sha='4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9',
    gate_command=target + slot + 'just check', gate_exit=0,
    red_log=str(p / 'red.log'), green_log=str(p / 'green.log'), gate_log=str(p / 'gate.log'), admission_policy='Source environment macro invocations pass through until compiler environment dependencies are tracked',
    changed_files=['src/compiler/rustdoc.rs', 'tests/rustdoc_environment_test.rs'],
    regression_command=target + slot + 'cargo test --test rustdoc_environment_test',
    unit_command=target + slot + 'cargo test --bin kache compiler::rustdoc::tests',
    unit_log=str(p / 'rustdoc-suite.log'),
    per_path_evidence={
        'src/compiler/rustdoc.rs': '39 rustdoc unit controls pass, including environment invocation refusal, inner/outer attributes, delimiters and comments/string/function/inequality controls',
        'tests/rustdoc_environment_test.rs': 'Real DOC_TEXT OLD_MARKER to NEW_MARKER and direct rustdoc agreement through passthrough; separate ordinary-docs fixture retains miss/hit reuse across an unrelated env change'
    })
(p / 'delivery.json').write_text(json.dumps(record, indent=2) + '\n')
s = (p / 'report.md').read_text().replace('STATUS: VALIDATING', 'STATUS: READY').replace('OPEN: Full gate, independent review and CI mutation verdict pending', 'OPEN: Independent review and CI mutation verdict pending').replace('No READY or independent PASS claim until the required gate completes.', 'Writer READY; independent review and CI mutation verdict remain pending.').replace('The full gate is running at the listed commit.', '`just check` exited 0 at the listed commit (gate.log and gate-exit.txt).')
(p / 'report.md').write_text(s)
(p / 'queue-state.json').write_text(json.dumps({'id': 'rust-wrapper-005', 'status': 'ready', 'worktree': str(worktree), 'branch': 'fix/rust-wrapper-005', 'fix_commit': record['fix_commit']}, indent=2) + '\n')
