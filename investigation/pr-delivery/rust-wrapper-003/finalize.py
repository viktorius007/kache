from pathlib import Path
import json
import subprocess

p = Path(__file__).parent
worktree = Path('/Users/viktor/Developer/github/kache-prs/rust-wrapper-003')
assert (p / 'gate-exit.txt').read_text().strip() == '0'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=worktree, text=True).strip() == '19b0c7418b5f92b5bc364a7a8510b7d6bb49f163'
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=worktree, text=True)
target = 'CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/rust-wrapper-001/target '
slot = 'python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py '
record = dict(
    id='rust-wrapper-003', branch='fix/rust-wrapper-003', worktree=str(worktree),
    test_commit='41f16171d63659d3f9ef333b5f09152918d7d743',
    fix_commit='19b0c7418b5f92b5bc364a7a8510b7d6bb49f163',
    title='fix: include nested module sources in rustdoc cache keys',
    body_file=str(p / 'pr-body.md'), base_sha='4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9',
    gate_command=target + slot + 'just check', gate_exit=0,
    red_log=str(p / 'red.log'), green_log=str(p / 'green.log'), gate_log=str(p / 'gate.log'),
    changed_files=['src/compiler/rustdoc.rs', 'tests/rustdoc_nested_module_test.rs'],
    regression_command=target + slot + 'cargo test --test rustdoc_nested_module_test',
    unit_command=target + slot + 'cargo test --bin kache compiler::rustdoc::tests',
    unit_log=str(p / 'rustdoc-suite.log'), review_red_log=str(p / 'review-red.log'),
    supersedes='71dc3d5117e04d7272976562ef051be345b5d953',
    per_path_evidence={
        'src/compiler/rustdoc.rs': '41 rustdoc unit tests pass, including custom root, nested module, mod.rs, includes and explicit-path child inventories',
        'tests/rustdoc_nested_module_test.rs': 'Real rustdoc OLD_MARKER to NEW_MARKER, direct compiler agreement, and cold/warm miss/hit controls; baseline fails the requested-output assertion'
    })
(p / 'delivery.json').write_text(json.dumps(record, indent=2) + '\n')
s = (p / 'report.md').read_text().replace('STATUS: VALIDATING', 'STATUS: READY').replace('The full gate is running at the listed commit.', '`just check` exited 0 at the listed commit (gate.log and gate-exit.txt).')
(p / 'report.md').write_text(s)
(p / 'queue-state.json').write_text(json.dumps({'id': 'rust-wrapper-003', 'status': 'ready', 'worktree': str(worktree), 'branch': 'fix/rust-wrapper-003', 'fix_commit': record['fix_commit']}, indent=2) + '\n')
