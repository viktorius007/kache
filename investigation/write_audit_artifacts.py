#!/usr/bin/env python3
"""Assemble the audit's machine-readable results without touching source."""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKTREE = ROOT.parent
SHA = '4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
RUN = dict(ts=datetime.datetime.now(datetime.timezone.utc).isoformat(), commit=SHA,
           model='Codex', mode='production-readiness', slice='cli-config')


def finding(identifier, summary, scenario, evidence, trace, authority, script, output, severity):
    return dict(id=identifier, kind='finding', run=RUN, category='defect', domain='code',
                summary=summary, scenario=scenario, evidence=evidence, trace=trace,
                authority=authority, proof=dict(red_test=(ROOT / script).read_text(),
                name=Path(script).stem, fails_on=SHA, output=(ROOT / output).read_text()),
                severity=severity, status='open')


def ev(path, lines, point):
    return dict(path=path, lines=lines, point=point)


findings = [
    finding('cli-config-001', 'Unix init corrupts a valid Cargo config when its build table has a trailing comment.',
            'CARGO_HOME/config.toml already contains a working rustc-wrapper="kache", complete native env settings, an unset rustdoc, and the valid header [build] # Existing compiler configuration. Running init --yes --no-service exits 0 and says Ready for Cargo builds, but appends a second [build]. Cargo metadata --offline then exits 101 with duplicate key; the same setup with a plain header stays usable.',
            [ev('src/main.rs', '1119-1131', 'Ordinary init dispatch reaches cli::init with shell setup enabled by default.'),
             ev('src/cli.rs', '9082-9091', 'apply_rustdoc_edit recognizes only trimmed == "[build]".'),
             ev('src/cli.rs', '9122-9131', 'An unrecognized build header causes an unconditional appended [build] table.'),
             ev('src/cli.rs', '9207-9249', 'configure_cargo_rustdoc parses the input to choose Write, then writes edited text without validating the result.'),
             ev('src/cli.rs', '9440-9447', 'init calls configure_cargo_rustdoc after compiler/shell setup.')],
            'main init -> cli::init -> existing wrapper/native settings already ready -> init_compiler_setup installs rustdoc shim -> configure_cargo_rustdoc chooses Write -> apply_rustdoc_edit appends duplicate table -> std::fs::write overwrites valid Cargo config -> init returns success -> real Cargo refuses configuration.',
            dict(source='failure-mode; docs/getting-started/quick-start.mdx:19', quote='kache init configures Cargo’s Rust wrapper; successful setup must leave Cargo able to load its configuration.'),
            'repro_rustdoc_config.py', 'rustdoc-config-output.txt',
            'The ordinary Unix setup command causes persistent failure for every Cargo project using the edited user/CARGO_HOME config. A trailing table comment is valid and commonplace. The command reports success, so users continue with broken setup. A backup exists, limiting recovery cost, but manual restoration/editing is required. No cache artifact integrity claim is made.'),
    finding('cli-config-002', 'Doctor migration turns a working absolute sccache wrapper path into a nonexistent kache path.',
            'CARGO_HOME/config.toml sets build.rustc-wrapper to an existing absolute old-wrapper/sccache executable, while kache is available separately on PATH. A dependency-free Cargo check passes. doctor --fix exits 0 and changes the value to old-wrapper/kache, which is absent. The next real Cargo check exits 101 before rustc executes with OS error 2.',
            [ev('src/main.rs', '1133-1153', 'doctor --fix dispatch reaches cli::doctor.'),
             ev('src/cli.rs', '7169-7172', 'The fix branch invokes migrate(purge_sccache).'),
             ev('src/cli.rs', '7311-7325', 'Migration rewrites the entire Cargo configuration with content.replace("sccache", "kache") and writes it in place; it does not select a real replacement executable.')],
            'main doctor --fix -> cli::doctor -> migrate(false) -> Cargo home config contains sccache -> global substring replacement -> absolute executable path rewritten -> success report -> Cargo cannot launch rewritten wrapper.',
            dict(source='failure-mode; src/cli.rs:7293', quote='Migrate from sccache to kache (called by doctor --fix).'),
            'repro_migration_path.py', 'migration-path-output.txt',
            'Existing absolute wrapper paths are supported Cargo configurations and common when PATH is controlled. All projects sharing that Cargo home fail after the repair command. The mutation is persistent and the migration path creates no backup. The same indiscriminate replacement also touches unrelated sccache strings, but the admitted proof is limited to executable-path breakage.')
]
findings.extend([
    dict(id='cli-config-dismiss-001', kind='dismissal', run=RUN, category='defect', domain='code',
         summary='The ordinary Rust wrapper editor rejects an invalid edited config before writing it.',
         checked='A valid [build] # comment with no wrapper is passed to init --yes --no-service --no-shell; the formatting editor generates a duplicate table internally.',
         evidence=[ev('src/cli.rs','9408-9427','The updated wrapper/native-env text is parsed and its wrapper checked before directory creation, backup, or writing.'),
                   ev('investigation/config-guards-evidence.json','all','Executed baseline init exits 1 for duplicate key and before/after Cargo configuration bytes are equal.')],
         trace='init -> apply_cargo_wrapper_edit -> apply_cargo_env_edit -> toml::from_str(updated)? -> failure before write',
         closed_by='Tier 1: probe_config_guards.py executed baseline rejection and unchanged-file assertions; Tier 2: src/cli.rs:9411 validates the text before saving.',
         reopens_if='A valid input shape reaches the Rust wrapper write with invalid text, or a rejection changes the original file.', status='no-action'),
    dict(id='cli-config-dismiss-002', kind='dismissal', run=RUN, category='defect', domain='code',
         summary='Whole-file fallback on an invalid Kache config is the explicit current contract, not an undisclosed parse-precedence regression.',
         checked='Config::load_resolved reads file_config.as_ref().ok(); one wrong-typed setting drops the chosen and host layers, including pinning/safety settings.',
         evidence=[ev('docs/getting-started/configuration.mdx','33','The documentation explicitly says invalid TOML or a wrong type ignores the whole chosen file and host config, and uses env/defaults without warning.'),
                   ev('src/config.rs','1498-1600','Resolution consumes the fallible loaded file through optional parsed settings.')],
         trace='load chosen config -> parse/schema error -> load_resolved optional file settings absent -> environment/default resolution',
         closed_by='Tier 4: docs/getting-started/configuration.mdx:33 expressly declares this behavior. This closes the contract-divergence claim only; it does not establish the behavior is safe for every policy workload.',
         reopens_if='A policy or authority requires fail-closed pinning despite malformed config, or a concrete artifact/egress consequence is demonstrated in the owning domain.', status='no-action')
])
(ROOT / 'findings.json').write_text(json.dumps(findings, indent=2) + '\n')

cases = [dict(id='cli-config-001', argv=['/opt/homebrew/bin/python3.14', str(ROOT / 'repro_rustdoc_config.py')],
              workdir=str(WORKTREE), timeout_seconds=90,
              expected_failure_regex='AssertionError: RUSTDOC_CONFIG_CORRUPTED', assertion_regex='duplicate key'),
         dict(id='cli-config-002', argv=['/opt/homebrew/bin/python3.14', str(ROOT / 'repro_migration_path.py')],
              workdir=str(WORKTREE), timeout_seconds=90,
              expected_failure_regex='AssertionError: MIGRATION_WRAPPER_BROKEN', assertion_regex='No such file or directory')]
(ROOT / 'replay-cases.json').write_text(json.dumps(cases, indent=2) + '\n')

partial = {
 'src/cli/tests.rs': [(2780,3125),(7810,8010)],
 'src/config/tests.rs': [(1233,1475)],
 'src/config_tui.rs': [(1,1500)],
 'src/init_shell.rs': [(1,390)],
 'src/main.rs': [(1,2205)],
 'src/platform.rs': [(1,440)],
 'src/service.rs': [(1,1500)],
 'tests/cli_commands_test.rs': [(1,75),(1250,1411),(1656,1715),(2690,2760)],
}
production_ends = {'src/config_tui.rs':1370,'src/init_shell.rs':287,'src/main.rs':1834,'src/platform.rs':328,'src/service.rs':1284}
notes = {
 'src/cli.rs':'Full production command, reporting, sync, integrity verify, cleanup, setup, migration and shim-install text reviewed. Executed Cargo breakage proofs and wrapper-edit control; other command/platform behavior source-reviewed only.',
 'src/config.rs':'Full layered config, env/pinning, path/socket, remote policy, persistence and provenance text reviewed. Malformed whole-file behavior reconciled with the explicit contract.',
 'src/config_tui.rs':'Production editor fields, validation, preservation, save and input/drawing paths fully reviewed; interactive terminal runtime not exercised. Test sample covers form shape and OCI form preservation.',
 'src/init_shell.rs':'Production shell selection, quoting, regular-file checks, snapshot verification, backup and atomic replacement fully reviewed. Bash fixture setup exercised indirectly by baseline init.',
 'src/main.rs':'Production dispatch, argument/env ownership, JSON selection, config bootstrap, CLI routing and direct/disabled/reentrant wrapper paths fully reviewed. Runtime samples are setup/doctor and C preprocessing; no broad compiler correctness claim.',
 'src/service.rs':'Production launchd/systemd/Task Scheduler generation, install/remove, manager deadline, ownership and status paths fully reviewed. Real managers were never modified or exercised.',
 'src/platform.rs':'Production platform limits, self-spawn naming and process ownership guards fully reviewed. Unsupported platform behavior source-reviewed only.',
 'src/cli/login.rs':'Full login/logout discovery, trust, scoped stores, session locks, bounded revoke and tests read; no live authentication or token storage exercised. Planner/auth remains consulted ownership.',
 'src/cli/miss_diagnosis.rs':'Full diagnosis priorities and shared terminal/JSON facts read, including tests. Emitted-event semantics require observability/planner consultations beyond this primary slice.',
 'src/cli/tests.rs':'Selected setup/rustdoc/wrapper editor and cache cleanup cases read; tests were not executed as a suite. Existing rustdoc edit assertions cover plain headers, not commented table headers.',
 'src/config/tests.rs':'Selected host merge, precedence, remote/planner isolation cases read; no test suite execution.',
 'tests/cli_commands_test.rs':'Selected fixture isolation, tracked cleanup, migration, and rustdoc setup cases read; tests were not run as a suite. Existing migration asserts textual replacement of bare sccache, not usability of absolute replacements.',
}
records=[]
for item in json.loads((ROOT/'worklist.json').read_text())['primary_paths']:
    path=item['path']; total=item['text_lines']; ranges=partial.get(path,[(1,total)])
    omitted=[]; cursor=1
    for start,end in ranges:
        if start>cursor: omitted.append(dict(start_line=cursor,end_line=start-1))
        cursor=end+1
    if cursor<=total: omitted.append(dict(start_line=cursor,end_line=total))
    record=dict(path=path,state='sampled' if path in partial else 'reviewed',
                evidence=[notes.get(path,'Full assigned text read and reconciled with production behavior and scope contracts. Source/test review only unless named in runtime evidence.')],
                reviewed_ranges=[dict(start_line=a,end_line=b) for a,b in ranges],
                unreviewed_ranges=omitted,
                reopen_conditions='Reopen on changes to the cited paths or a new production workload/contradictory event; omitted test ranges require separate review before a test-suite completeness claim.')
    if path in production_ends:
        record['production_reviewed_ranges']=[dict(start_line=1,end_line=production_ends[path])]
        record['test_sampling_only']=True
    records.append(record)
coverage=dict(schema_version=1,baseline_commit=SHA,primary_paths=records,
              graph_coverage=dict(project='Users-viktor-Developer-github-kache-investigations-coordinator',
                evidence='investigation/graph-index-status.txt', rust_status='semantic_partial',
                limits=['binding oracle unavailable','expanded calls unavailable','impl relationships unavailable','.cargo excluded from graph'],
                method='Graph entry-point and config/function searches, source snippets, then source fallback. Missing graph edges are not negative caller evidence.'),
              collateral=[dict(path='src/cargo_env.rs',state='collateral',reviewed_ranges=[dict(start_line=1,end_line=259)],evidence='Full native Cargo env editor read to trace prevalidation and already-ready rustdoc scenario.'),
                          dict(path='.cargo/config.toml',state='collateral',reviewed_ranges=[dict(start_line=1,end_line=8)],evidence='Full ancestor fixture Cargo configuration read; only KACHE_HOST_CONFIG env isolation.'),
                          dict(path='src/compiler/mod.rs',state='collateral',reviewed_ranges=[dict(start_line=2050,end_line=2070)],evidence='Default shim directory seam inspected; not a review of compiler implementation.'),
                          dict(path='src/compiler/cc.rs',state='collateral',reviewed_ranges=[dict(start_line=6641,end_line=6643)],evidence='Graph source snippet of recognizes_family_probe used for dispatch consultation.'),
                          dict(path='src/wrapper.rs',state='collateral',reviewed_ranges=[dict(start_line=919,end_line=928)],evidence='Graph source snippet of run_cc_probe used for dispatch consultation.')])
(ROOT/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')

metadata=dict(baseline_commit=SHA,baseline_binary='/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache',
              binary_sha256='45840941809ca7c45622027f84d2c653c737e7ff35d375cfbf355b619456120f',
              cargo='/Users/viktor/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/cargo',python='/opt/homebrew/bin/python3.14',
              source_diff='git diff --exit-code -- src docs tests .cargo exited 0',
              cleanup='Both rustdoc fixtures returned daemon stopped; all fixture homes/workspaces and short runtime directories deleted by context managers.',
              run_limits='No substantial repository build, whole-suite execution, live credential operation, real service-manager modification, remote egress, or terminal interaction.')
(ROOT/'runtime-provenance.json').write_text(json.dumps(metadata,indent=2)+'\n')

omissions='\n'.join('- '+r['path']+': omitted '+', '.join(str(q['start_line'])+'-'+str(q['end_line']) for q in r['unreviewed_ranges']) for r in records if r['unreviewed_ranges'])
report='''STATUS: DONE
COMMIT: none
CHANGED: {count} files
OPEN: 2 unresolved items
BLOCKERS: none
CONFIRMED: 2
LIMITS: Production text fully reviewed; dedicated and inline test suites sampled; runtime probes on macOS only; real service managers, terminal interaction and live credentials not exercised.
---

Audit baseline: {sha}. No production or committed test source was changed. The unchanged coordinator CLI SHA-256 is 45840941809ca7c45622027f84d2c653c737e7ff35d375cfbf355b619456120f. Audit artifacts are uncommitted in this permanent worktree; COMMIT is therefore none.

**Two persistent Cargo setup failures are confirmed.** Both have executable red tests, before/after configuration snapshots, real Cargo consequences, and an unchanged baseline CLI. The red assertions are successful audit evidence, not failed audit work.

**cli-config-001 — Unix init corrupts a Cargo build table with a trailing comment.** A valid Cargo config containing [build] # Existing compiler configuration and rustc-wrapper="kache" is accepted before setup. With native env settings already complete and rustdoc unset, init --yes --no-service exits 0, says cargo doc is configured and Ready for Cargo builds, and appends a duplicate [build]. Real Cargo metadata exits 101 afterward with duplicate key. The plain [build] control stays valid and usable. The initial input and output are independently parsed with Python tomllib as well.

The source route is main.rs:1119 -> cli.rs:9319 init -> cli.rs:9442 configure_cargo_rustdoc -> cli.rs:9082 exact header recognition -> cli.rs:9129 appended table -> cli.rs:9245 unvalidated write. Every Cargo project using that Cargo home is blocked until the user restores the backup or edits the duplicate table. The proof targets ordinary Unix setup on macOS; it does not make a Windows claim. The backup limits recovery cost but does not prevent the reported-success breakage.

Evidence: [full red test](repro_rustdoc_config.py), [raw command evidence](rustdoc-config-evidence.json), [assertion output](rustdoc-config-output.txt). Replay entry cli-config-001 in [replay-cases.json](replay-cases.json) exits 1 with RUSTDOC_CONFIG_CORRUPTED; the failed Cargo command exits 101. Both fixture daemons were stopped successfully and disposable homes/runtime directories were removed.

**cli-config-002 — Doctor migration rewrites an absolute wrapper path to a missing executable.** A dependency-free library compiles through an existing absolute old-wrapper/sccache passthrough wrapper. Kache is available separately on PATH. doctor --fix exits 0 and globally replaces sccache with kache in the Cargo home config; the resulting old-wrapper/kache path does not exist. The next Cargo check exits 101 before rustc executes, with No such file or directory (os error 2).

The source route is main.rs:1133 doctor -> cli.rs:7171 migrate -> cli.rs:7318 content.replace("sccache", "kache") -> cli.rs:7319 in-place write. This breaks all projects sharing that Cargo config and creates no migration backup. The proof is deliberately limited to a working absolute executable path: other strings can also be rewritten, but no additional integrity claim is admitted from that alone. The test masks pgrep with a fixture executable returning no processes, so no user sccache server is observed or stopped.

Evidence: [full red test](repro_migration_path.py), [raw command evidence](migration-path-evidence.json), [assertion output](migration-path-output.txt). Replay entry cli-config-002 in [replay-cases.json](replay-cases.json) exits 1 with MIGRATION_WRAPPER_BROKEN. The control Cargo check exits 0 and the post-migration Cargo check exits 101. The only compile was a tiny dependency-free fixture; no repository/dependency build was performed.

**Dismissals and controls.** The ordinary Rust wrapper editor validates updated TOML before saving. An executed init --no-shell control with a commented table and no wrapper exits 1 for duplicate key while preserving every original config byte. This guards that editor and distinguishes it from the rustdoc write path. See [control script](probe_config_guards.py), [control output](config-guards-output.txt), and [control observations](config-guards-evidence.json). Documented compiler-prefixed preprocessing (kache cc -E) also passes with KACHE_DISABLED=0 and =1. Bare family-probe dispatch observations are preserved only as a narrow consultation artifact; no actual native-build consequence is asserted here.

Wrong-typed or invalid Kache config dropping the entire chosen/host layer was source-reviewed and reconciled with the explicit current contract at docs/getting-started/configuration.mdx:33. That dismissal closes an undisclosed precedence-regression claim, not the safety of every policy workload. Local-only daemon-start semantics and emitted telemetry were referred to their owning audit slices.

**Coverage and boundaries.** Every assigned production path and all assigned documentation were read in full. The source review traced CLI, shim, wrapper, Cargo/build-script/test-runner entry dispatch; config precedence/pinning and persistence; setup/migration/cleanup/verify/sync/report operations; and installed-service generation, ownership, bounded manager calls and status. Config TUI production code was read through line 1370, init_shell through 287, main through 1834, platform through 328 and service through 1284. Their subsequent inline tests were sampled. This is source review plus the named runtime probes, not an executed platform or whole-program integrity certification.

[coverage.json](coverage.json) records every one of the 28 primary paths, exact reviewed ranges, omissions, evidence and reopening conditions. The large suites and remaining inline test ranges were omitted exactly as follows:

{omissions}

The sampled dedicated tests include setup/rustdoc/editor cases in src/cli/tests.rs:2780-3125, cache cleanup cases at 7810-8010, host config precedence/isolation at src/config/tests.rs:1233-1475, and integration fixture/cleanup/migration/rustdoc cases at the ranges in coverage.json. Existing migration tests assert bare textual replacement, while existing rustdoc edit tests use plain build table headers; neither sample establishes the failing shapes are covered elsewhere.

The codebase-memory baseline graph mapped the main entry point and supplied bounded config/dispatch snippets. Its Rust semantics are partial because binding, expanded calls, and implementation relationships are unavailable; .cargo is intentionally excluded. Source reads were used as fallback, and missing graph edges were never treated as caller absence. See [graph coverage evidence](graph-index-status.txt).

Real launchd, systemd and Task Scheduler state was not changed. Linux/Windows branches and generated service artifacts were source-reviewed only. No interactive terminal run, live login/logout, real remote transfer, full repository test suite or load-sensitive benchmark was attempted. Reports, timeline/event interpretation, cache internals, compiler correctness, daemon lifecycle and auth were treated as consulted seams with their separate primary owners. The audit admits no additional defect based solely on an unexecuted source hypothesis or a green existing test.

Machine-readable admitted findings, full embedded red source and evidence-cited dismissals: [findings.json](findings.json). Runtime/tool/source provenance: [runtime-provenance.json](runtime-provenance.json).
'''
# Include the report itself in the persisted artifact count.
count=len([p for p in ROOT.rglob('*') if p.is_file()])+ (0 if (ROOT/'report.md').exists() else 1)
report=report.format(count=count,sha=SHA,omissions=omissions)
(ROOT/'report.md').write_text(report)
print('Saved',len(records),'primary coverage records,',len(findings),'finding/dismissal records, and',count,'artifacts.')
