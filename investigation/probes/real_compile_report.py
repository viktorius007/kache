#!/usr/bin/env python3
"""Actual untouched Kache + rustc compile proving reports lose skip reasons."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

KACHE = '/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
RUSTC = '/Users/viktor/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('case', choices=['skip-reason', 'redact-root', 'torn-utf8'])
    args = parser.parse_args()
    evidence = Path(__file__).resolve().parents[1] / 'evidence'
    with tempfile.TemporaryDirectory(prefix='obs-', dir='/private/tmp') as tmp:
        fixture = Path(tmp)
        workspace = fixture / ('customer-secret-workspace-€' if args.case == 'torn-utf8' else 'customer-secret-workspace')
        out = workspace / 'target/debug/deps'
        out.mkdir(parents=True)
        source = workspace / 'lib.rs'
        source.write_text('pub fn number() -> u32 { 42 }\n')
        (workspace / 'Cargo.toml').write_text('[package]\nname="fixture"\nversion="0.1.0"\nedition="2024"\n[lib]\npath="lib.rs"\n')
        config = fixture / 'config.toml'
        config.write_text('[cache]\nmin_store_compile_ms=60000\n')
        host = fixture / 'host.toml'
        host.write_text('')
        home = fixture / 'home'
        home.mkdir()
        env = {key: value for key, value in os.environ.items() if not key.startswith(('KACHE_', 'CARGO_', 'RUSTC_', 'RUSTFLAGS'))}
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'), KACHE_CONFIG=str(config),
                   KACHE_HOST_CONFIG=str(host), KACHE_CACHE_DIR=str(fixture / 'cache'),
                   KACHE_RUNTIME_DIR=str(fixture / 'runtime'), KACHE_SOCKET_PATH=str(fixture / 'daemon.sock'),
                   KACHE_PROGRESS='0', CARGO_MANIFEST_DIR=str(workspace), CARGO_PKG_NAME='fixture',
                   CARGO_PRIMARY_PACKAGE='1', CARGO_PKG_VERSION='0.1.0')
        compiler_argv = [KACHE, RUSTC, '--crate-name', 'fixture', '--crate-type', 'rlib', '--edition', '2024',
                         '--emit=dep-info,metadata,link', '-C', 'extra-filename=-fixture',
                         '--out-dir', str(out), str(source)]
        if args.case == 'torn-utf8':
            first = subprocess.run(compiler_argv, env=env, cwd=workspace, capture_output=True, text=True, timeout=30)
            assert first.returncode == 0, 'initial unicode-root production compile failed: ' + first.stderr
            initial = (fixture / 'runtime/events.jsonl').read_bytes()
            unicode_at = initial.index('€'.encode())
            interrupted = initial[:unicode_at + 1]
            (evidence / 'real-torn-utf8.complete-before.bin').write_bytes(initial)
            (evidence / 'real-torn-utf8.interrupted.bin').write_bytes(interrupted)
            (fixture / 'runtime/events.jsonl').write_bytes(interrupted)
        compiled = subprocess.run(compiler_argv, env=env, cwd=workspace, capture_output=True, text=True, timeout=30)
        assert compiled.returncode == 0, 'production compile failed: ' + compiled.stderr
        assert (out / 'libfixture-fixture.rlib').exists(), 'actual rustc artifact missing'
        events_path = fixture / 'runtime/events.jsonl'
        raw = events_path.read_bytes()
        (evidence / ('real-' + args.case + '.events.bin')).write_bytes(raw)
        events = []
        for line in raw.splitlines():
            try:
                events.append(json.loads(line))
            except (ValueError, UnicodeDecodeError):
                pass
        (evidence / ('real-' + args.case + '.events.json')).write_text(json.dumps(events, indent=2))
        skipped = [event for event in events if event.get('result') == 'skipped']
        assert len(skipped) == 1 and skipped[0]['skip_reason'] == 'admission-threshold', 'production skip gate control failed'
        report_argv = [KACHE, 'stats', '--format', 'json']
        if args.case == 'redact-root':
            report_argv.append('--redact')
        reported = subprocess.run(report_argv, env=env, cwd=workspace, capture_output=True, text=True, timeout=20)
        (evidence / ('real-' + args.case + '.report.stderr.txt')).write_text(reported.stderr)
        (evidence / ('real-' + args.case + '.compile.stderr.txt')).write_text(compiled.stderr)
        if args.case == 'torn-utf8':
            print('CONTROL rustc produced rlib; next valid event retained after repaired newline', flush=True)
            print('OBSERVED stats exit = ' + str(reported.returncode) + '; stderr = ' + reported.stderr.strip(), flush=True)
            assert reported.returncode == 0, 'TORN_UTF8_POISONS_REPORT: valid production event unavailable after interrupted unicode log record'
            return
        assert reported.returncode == 0, reported.stderr
        (evidence / ('real-' + args.case + '.report.json')).write_text(reported.stdout)
        (evidence / ('real-' + args.case + '.compile.stderr.txt')).write_text(compiled.stderr)
        report = json.loads(reported.stdout)
        row = report['bypass']['slowest'][0]
        print('CONTROL rustc produced rlib; production event records admission-threshold', flush=True)
        if args.case == 'skip-reason':
            print('OBSERVED report reason = ' + row['reason'], flush=True)
            assert row['reason'] == 'admission-threshold', 'SKIP_REASON_LOST: production skip became unknown in report'
        else:
            assert report['traceEvents'][0]['args']['root'] == 'redacted', 'redaction control failed'
            print('OBSERVED report bypass root = ' + row['root'], flush=True)
            assert row['root'] == 'redacted', 'REDACT_BYPASS_ROOT_LEAK: production root survives --redact'

if __name__ == '__main__':
    main()
