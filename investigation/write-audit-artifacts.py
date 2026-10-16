#!/usr/bin/env python3
"""Serialize this audit's source coverage, executed proofs, and report."""
import datetime
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent
WORKTREE = ROOT.parent
BASELINE = '4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
run = dict(ts=datetime.datetime.now(datetime.timezone.utc).isoformat(), commit=BASELINE, model='Codex', mode='production-readiness', slice='cc-cuda-adapters')
source = (ROOT / 'cc-integrity-probes.py').read_text()

def save(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2) + '\n')

proofs = [
    dict(id='cc-header-permutation', case='header-swap', summary='C compile keys lose the association between header paths and header contents, restoring obsolete objects after contents are exchanged.', scenario='unit.c includes a.h then b.h; both undefine VALUE and define it as 1 and 2 respectively. Swapping those complete header contents leaves the source and included filenames unchanged. Kache returns a local cache hit whose program exits 2; current direct Clang exits 1.', evidence=[dict(path='src/compiler/cc.rs', lines='6102-6130', point='cc_direct_inputs_digest sorts and deduplicates content hashes without hashing their associated header names.'), dict(path='src/compiler/cc.rs', lines='7248-7260,7325-7335', point='Both compile-first discovery and full preprocessing use that content-set digest; the preprocessor expansion hash is discarded when dependency fingerprints exist.')], trace='wrapper::run_cc -> run_cc_with_store -> CcCompiler::cache_key_under -> memo invalidation/full preprocess -> cc_direct_inputs_digest equal to old content set -> unchanged include-name digest -> local lookup -> restore old unit.o -> successful wrapper exit; real linked program runs obsolete code.', severity='Default enabled C/C++ compile caching can silently return code inconsistent with the current headers. Header permutations preserve the digest even after dependency stamps detect changes and trigger fresh preprocessing. Proven for real Apple Clang with deferred discovery both enabled and disabled. Concrete trigger requires preserving the header-content set; this does not establish a collision for arbitrary edits.', actual=2, expected=1, priority='P1'),
    dict(id='cc-optional-header', case='has-include', summary='C read-set reuse misses a newly created header tested through __has_include and restores an obsolete object.', scenario='unit.c tests __has_include("optional.h"), uses VALUE=1 while absent, and includes the header if present. After a cold miss and warm hit, create optional.h defining VALUE=2. Kache still restores the old object and its program exits 1; direct Clang exits 2.', evidence=[dict(path='src/compiler/cc.rs', lines='5490-5525', point='cc_shadowing_names derives candidate filenames solely from files the earlier compile actually read; an absent optional.h is not among them.'), dict(path='src/compiler/cc.rs', lines='7279-7297,7389-7412', point='A valid read-set memo supplies its stored digest and old read inputs; include shadowing resolves only names obtained from that read set.')], trace='wrapper::run_cc -> run_cc_with_store -> CcCompiler::cache_key_under -> previous read inputs unchanged -> preprocess memo hit -> optional.h absent from cc_shadowing_names -> old key -> local restore of unit.o -> successful wrapper exit with outdated executable behavior.', severity='Default enabled compile caching can silently omit a newly enabled feature or generated configuration header. __has_include is a normal C/C++ availability probe. Proven with actual Apple Clang and both deferred-discovery settings. Existing included-header edits invalidate correctly; the failure concerns previously absent inputs.', actual=1, expected=2, priority='P1'),
    dict(id='cc-link-library', case='link-library', summary='Opt-in C/C++ link keys do not hash libraries selected with -l, restoring obsolete executables after a library changes.', scenario='Enable KACHE_CACHE_CC_LINKS=1. Cache clang main.o -L. -lvalue -o app with libvalue.a implementing value()=1. Replace the archive with value()=2 while main.o and arguments stay unchanged. Kache returns local_hit and app exits 1; direct Clang link exits 2.', evidence=[dict(path='src/compiler/cc.rs', lines='6414-6480', point='cache_key_for_link hashes argv and explicit source/positional file inputs; it hashes the compiler version but does not resolve and hash -l libraries.'), dict(path='src/compiler/cc.rs', lines='7727-7752', point='cc_link_file_inputs skips arguments beginning with a dash, so -lvalue and -L. contribute no selected library content.')], trace='KACHE_CACHE_CC_LINKS -> CcCompiler::refuse_reasons removes link-mode refusal -> cache_key_under link branch -> cache_key_for_link -> main.o hashed, -lvalue only argv-spelling keyed -> library update leaves key unchanged -> run_cc_with_store restores cached app -> successful exit, obsolete behavior.', severity='A changed dependency produces an obsolete executable without a compiler error. Reachable only when the user enables experimental/opt-in cache_cc_links; default links pass through. Proven for a local static archive selected by -l with real Apple Clang. Explicit positional libvalue.a updates miss correctly. Dynamic libraries, Linux and Windows remain unexecuted.', actual=1, expected=2, priority='P2'),
]
findings = []
for item in proofs:
    case = item['case']
    output = (ROOT / (case + '-1.log')).read_text()
    message = f'CACHE_INTEGRITY_FAILURE: {case}: cached {item["actual"]}, direct compiler expected {item["expected"]}; result=local_hit'
    replay = dict(argv=['python3', str(ROOT / 'cc-integrity-probes.py'), case, '--discovery', '1'], workdir=str(WORKTREE), timeout_seconds=60, expected_failure_regex='AssertionError: ' + message, assertion_regex=message)
    save(item['id'] + '.replay.json', replay)
    findings.append(dict(id=item['id'], kind='finding', run=run, category='defect', domain='code', summary=item['summary'], scenario=item['scenario'], evidence=item['evidence'] + [dict(path='investigation/' + case + '-1.log', lines='1-11', point=message)], trace=item['trace'], authority=dict(source='failure-mode; docs/getting-started/c-cpp.mdx:117', quote='The key includes the content of the source and of every header the compile reads, the compiler identity, modeled code-generation options, and normalized paths. Header changes therefore invalidate the entry.'), proof=dict(red_test=source, name=case, fails_on=BASELINE, output=output, replay_case='investigation/' + item['id'] + '.replay.json'), severity=item['severity'], priority=item['priority'], status='open'))

for case, checked, closed_by, reopens_if in [
    ('epoch', 'Changing SOURCE_DATE_EPOCH from 0 to 946684800 with unchanged source using __DATE__/__TIME__. Suspected direct-input digest might discard the change.', 'Executed black-box real-Clang oracle: initial miss and warm hit print Jan 1 1970; epoch change misses with a different key and prints Jan 1 2000, equal to direct compiler. investigation/epoch-1.log and fixtures-epoch-1/observations.json.', 'A supported compiler which omits the effective epoch from resolved invocation produces a stale result, or resolved-token hashing changes.'),
    ('has-include-control', 'Changing a header that was already present and included on the cold build.', 'Executed black-box real-Clang control: changed included header yields miss with a new key and output 2, agreeing with direct compilation. investigation/has-include-1-control.log.', 'Ordinary included-header edits stop invalidating, or negative dependencies are newly modeled and optional-header defect should be retested.'),
    ('header-swap-control', 'Replacing the read-set content multiset with a genuinely new header value, instead of only permuting existing contents.', 'Executed real-Clang control: changing b.h to VALUE=3 produces a new key, miss, output 3 equal to direct compiler. investigation/header-swap-1-control.log.', 'Read-set hash representation changes, or source-to-path associations become keyed and the permutation defect should be retested.'),
    ('link-library-control', 'Replacing a static archive passed as an explicit positional link input.', 'Executed real-Clang control: clang main.o libvalue.a -o app misses after library mutation and runs value()=2, equal to direct link. investigation/link-library-1-control.log; src/compiler/cc.rs:7727-7752 recognizes .a positional inputs.', 'Library input discovery changes or named-library resolution is implemented; reexecute the -l failure and positional control together.'),
]:
    findings.append(dict(id='cc-dismiss-' + case, kind='dismissal', run=run, category='defect', domain='code', summary='Bounded integrity candidate dismissed: ' + checked, checked=checked, closed_by=closed_by, reopens_if=reopens_if, evidence=[dict(path='investigation/' + ('epoch-1.log' if case=='epoch' else case.removesuffix('-control')+'-1-control.log'), point='Executed cache miss/hit result and independently linked program oracle.')], status='dismissed'))
save('findings.json', findings)

ranges = {
 'src/compiler/cc/tests.rs': [[1,640],[6588,7170],[7463,7600]],
 'src/compiler/mod.rs': [[1,1400]],
 'src/compiler/nvcc.rs': [[1,1400]],
 'src/compiler/platform.rs': [[1,670]],
 'src/probe/mod.rs': [[1,950]],
}
production_ends = {'src/compiler/mod.rs':995, 'src/compiler/nvcc.rs':1333, 'src/compiler/platform.rs':500, 'src/probe/mod.rs':786}
points = {
 'src/compiler/cc.rs': 'Full production read: argument parser/classification, eligibility gates, prefix maps, epoch, preprocess/deferred discovery, memo revalidation, include shadowing, compile/link keys and execution/artifact discovery. Three executed integrity findings; compile controls pass.',
 'src/compiler/cc/tests.rs': 'Samples target parsing, flags, memo/epoch, direct digest and shadowing invariants. Sampling does not establish absence of all regressions; actual baseline CLI probes supply finding oracles.',
 'src/compiler/flags.rs': 'Full flag table and capability classification; unsupported/preprocess/assembly/modules/PCH exclusions reviewed against C parser. No generic unsupported-flag admission claim without compiler execution.',
 'src/compiler/mod.rs': 'All production adapter interface, tool-family recognition, generic dispatch, diagnostic/artifact structure, argument/environment keying reviewed. Large inline test body sampled explicitly.',
 'src/compiler/nvcc.rs': 'All production NVCC parsing, eligibility, dependency discovery, host/toolkit identity probe, prefix mapping, key, epoch execution, dependency rewriting, artifact collection read. No real toolkit installed/executed. Inline tests sampled.',
 'src/compiler/platform.rs': 'All production macOS codesign and debug bundle handling read: signature repair, deterministic tar packing, regular-file admission, safe extraction bounds and name checks. Linux/Windows branches and bundle runtime unexecuted; inline tests sampled.',
 'src/probe/cache.rs': 'Full probe identity and cache persistence/fault fallback read: executable stat, argv/environment fingerprint, version reuse, atomic publication. CUDA host executable invalidation remains unexecuted.',
 'src/probe/mod.rs': 'All production Cc/NVCC probing, --version/-### handling, LC_ALL normalization, flag/env validation, and memo fallback read; inline tests sampled.',
 'src/probe/resolve.rs': 'Entire parser and inline tests read: Clang/GCC/Windows quoting, command splitting, selected compile stage, path/volatile token replacement, stable resolution. Fixture text reviewed. Actual runtime only Apple Clang.',
 'src/probe_memo.rs': 'Entire isolated memo-key and read/write implementation read, including executable replacement fingerprints and retry semantics.',
 'docs/getting-started/c-cpp.mdx': 'Full documented contract/setup/eligibility/deferred discovery/epoch/path normalization read. Header invalidation claim compared against executed failures.',
 'docs/getting-started/cuda.mdx': 'Full CUDA contract read, including deliberately unkeyed SOURCE_DATE_EPOCH disclosure. Real CUDA implications not established by a simulated nvcc.',
}
coverage = []
for item in json.loads((ROOT/'worklist.json').read_text())['primary_paths']:
    path = item['path']; n = item['text_lines']
    reviewed = ranges.get(path, [[1,n]])
    omitted=[]; cursor=1
    for lo,hi in reviewed:
        if cursor<lo: omitted.append([cursor,lo-1])
        cursor=hi+1
    if cursor<=n: omitted.append([cursor,n])
    evidence = points.get(path)
    if evidence is None:
        if 'src/probe/testdata/' in path:
            evidence = 'All literal driver-output fixture lines read; compared with resolve parser/token normalization and its inline tests. Fixture snapshots do not prove current GCC/Windows execution.'
        elif path.startswith('tests/fixtures/'):
            evidence = 'Full fixture text read; role checked against integration regression, passthrough or mock-compiler callers. Existing fixture not separately executed in this audit.'
        else:
            evidence = 'Full integration test text read; assertions, compiler discovery/skip conditions, isolated caches and diagnostic/exit-code oracles inspected. Committed integration suite not executed; focused baseline real-Clang probes executed separately.'
    coverage.append(dict(path=path, state='sampled' if omitted else 'reviewed', evidence=evidence, reviewed_ranges=reviewed, omitted_ranges=omitted, production_fully_read=path in production_ends or (path.endswith('.rs') and '/tests' not in path and path!='src/compiler/cc/tests.rs' and not omitted), production_end_line=production_ends.get(path), runtime='focused real Apple Clang black-box probes' if path=='src/compiler/cc.rs' else 'source review; runtime limits in report', reopen_conditions='Reopen on changes to this file or affected dispatch/key/probe/restore seams; expand omitted tests and execute supported toolchains before asserting whole-suite or cross-platform correctness.'))
coverage.append(dict(path='src/wrapper.rs', state='collateral', evidence='Consulted public CC/NVCC dispatch, key/store/restore guards; primary ownership belongs to rust-wrapper agent. Runtime reproduction reaches normal public wrapper dispatch.', reviewed_ranges=[[1190,1515],[1882,2015],[2030,2240],[2360,2435]], omitted_ranges='All remaining wrapper lines are outside this slice; no claim of full wrapper review.', reopen_conditions='Reopen if CC/NVCC dispatch, restore or store gate changes; real CUDA concurrency needed to assess unlocked NVCC publication lead.'))
save('coverage.json', coverage)
save('unresolved.json', [
 dict(id='cuda-runtime-inputs', status='unresolved', paths=['src/compiler/nvcc.rs','src/probe/cache.rs','src/probe/mod.rs'], evidence='Source inspection: NVCC honors effective epoch only at execute; documentation says it is absent from key. Probe memo tracks NVCC executable stat while host executable version is discovered by a cached invocation. No actual toolkit installed; no simulated proof admitted.', next='Run real nvcc on supported Linux/Windows toolkit, varying SOURCE_DATE_EPOCH and replacing host executable at identical path after cache warmup; compare actual artifacts/diagnostics. Distinguish documented behavior from defect.'),
 dict(id='cuda-unlocked-publication', status='unresolved', paths=['src/wrapper.rs:1404-1515'], evidence='Consultation from wrapper owner confirmed by source read: claim_build contention/error can reach clean NVCC compile/store without _build_lock Some. No executed concurrency consequence; redundant publishers alone do not prove integrity failure.', next='Use real CUDA compiler and controlled contention/input schedules to determine externally observable correctness consequence, consulting store/scheduler owners.'),
])
rows=[]
for case, discovery, control in [('header-swap','1',False),('header-swap','0',False),('has-include','1',False),('has-include','0',False),('link-library','1',False),('epoch','1',False),('header-swap','1',True),('has-include','1',True),('link-library','1',True)]:
    tag=case+'-'+discovery+('-control' if control else '')
    observation=json.loads((ROOT/('fixtures-'+tag)/'observations.json').read_text())
    changed=observation['rows'][-1]
    rows.append('| '+tag+' | '+changed['result']+' | '+str(changed['actual'])+' | '+str(observation['expected'])+' | '+('PASS control' if changed['actual']==observation['expected'] else 'expected RED')+' |')
count=len(subprocess.check_output(['git','ls-files','--others','--exclude-standard','investigation'],cwd=WORKTREE,text=True).splitlines())+int(not (ROOT/'report.md').exists())
report=f'''STATUS: DONE
COMMIT: {BASELINE}
CHANGED: {count} files
OPEN: 2 unresolved items
BLOCKERS: none for this audit; no CUDA toolkit for remaining runtime investigations
CONFIRMED: 3
LIMITS: real Apple Clang 17 on arm64 macOS only; dedicated/large inline test bodies sampled; no real GCC, clang-cl, CUDA, Linux/Windows, remote, concurrency, or performance execution
---

Three silent stale-output defects are confirmed on untouched baseline production source. Default C/C++ compile caching is affected by lost header-path/content association and untracked absent optional headers. A third defect affects opt-in C/C++ link caching when libraries are selected through `-l`. No production repair is included.

`cc-header-permutation` is the strongest key-integrity result. The source includes a.h then b.h, each redefining VALUE. Moving the complete existing contents between those header names preserves the sorted/deduplicated content hashes used by `cc_direct_inputs_digest` (`src/compiler/cc.rs:6102`). The memo notices changed stamps and fresh preprocessing can run, but its actual expansion is replaced with the same content-set digest (`src/compiler/cc.rs:7333`). The changed build restores a cached object whose linked program exits 2; direct compilation of the current tree exits 1. This occurs with deferred discovery both enabled and disabled. A non-permutation edit adding VALUE=3 correctly misses and agrees with the oracle. A remediation should preserve the association between normalized input identity and content, or use the actual expansion semantics, while maintaining portable checkout reuse.

`cc-optional-header` arises when `__has_include("optional.h")` changes from false to true. The initial read set never contains that absent filename. `cc_shadowing_names` only extracts names from previously read files (`src/compiler/cc.rs:5490`), so creating optional.h leaves the warm key unchanged. Cached code exits 1 while a direct compile exits 2. Both deferred-discovery settings reproduce this. Editing an already included optional.h correctly misses. A remediation needs negative/existence dependencies or a conservative refusal/invalidation mechanism for preprocessor availability probes; turning deferred discovery off does not fix this warm-hit gap.

`cc-link-library` requires `KACHE_CACHE_CC_LINKS=1`, which defaults off. A real static archive update behind identical `clang main.o -L. -lvalue -o app` arguments restores an obsolete app returning 1; a current direct link returns 2. `cache_key_for_link` hashes explicit positional inputs, and `cc_link_file_inputs` skips dash-prefixed flags (`src/compiler/cc.rs:6414`, `:7727`). Passing libvalue.a positionally correctly misses on update. A remediation must resolve/hash the compiler's selected library inputs or refuse unresolved named-library links. The proof establishes local static -l behavior; it does not establish dynamic or platform-specific linker behavior.

Every failure includes a cold miss, an unchanged warm local hit, identical changed-build key, zero changed-build compiler executions, and an independent direct-Clang oracle. Output objects/apps are removed before wrapper invocation to force restore. Input changes settle for 2.1 seconds, excluding recent-write timestamp guards. Fixture HOME/config/cache/runtime are isolated under investigation. Real compilers and the untouched baseline CLI execute through their public interfaces; there are no test-only production hooks. Normalization in the direct compiler oracle matches the wrapper's file-prefix map; numeric cases do not depend on paths. Program exits encode intentional return values, distinct from compiler process exit success.

| Replay / control | Changed-build event | Cached program | Direct program | Verdict |
| --- | --- | --- | --- | --- |
'''+ '\n'.join(rows)+f'''

Replay each admitted finding using its `*.replay.json` argv/workdir. Expected assertion failure is success for this audit. Full reusable source is `cc-integrity-probes.py`; `findings.json` embeds that source and exact red output per finding. Each fixture directory preserves source/header/archive/object/app, `commands.json` (exact real process argv/status/stdout/stderr), `observations.json`, per-phase wrapper diagnostics and local cache events. Root `*-1.log`/`*-0.log` files contain complete executed stdout and assertion. The baseline CLI is `/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache`; its SHA-256 is recorded in `baseline-cli-sha256.txt`, and compiler identity in `clang-version.txt`. `git diff --exit-code -- src tests docs` passed and the worktree remains at {BASELINE}. All changed files are investigation artifacts.

The initial Clang epoch-underkey candidate was refuted: SOURCE_DATE_EPOCH 0 -> 946684800 causes a different cache key, a miss, and direct-equivalent Jan 1 2000 output. Do not infer that CUDA behaves the same: its documentation explicitly describes an unkeyed epoch, and no actual nvcc is available here. Four bounded dismissals are in `findings.json`; passing controls do not establish whole-adapter correctness.

All assigned production implementation bodies were read in full, including CC argument classification and exclusions; unsafe assembly/PCH/module gates; diagnostic and exit handling; memo identities/revalidation; compiler identity/argument/environment probes; C/CUDA dependency extraction; prefix-map handling; linker artifact capture; and macOS signature/debug-bundle packing/extraction. Documents, small integration tests, probe snapshots and shell fixtures were fully read. `coverage.json` records every one of the 32 primary paths plus consulted wrapper ranges. Large test-body omissions are exact:

- `src/compiler/cc/tests.rs`: reviewed 1-640, 6588-7170, 7463-7600; omitted 641-6587, 7171-7462, 7601-8602.
- `src/compiler/mod.rs`: reviewed 1-1400; omitted 1401-2631 (tests; production ends 995).
- `src/compiler/nvcc.rs`: reviewed 1-1400; omitted 1401-2726 (tests; production ends 1333).
- `src/compiler/platform.rs`: reviewed 1-670; omitted 671-1121 (tests; production ends 500).
- `src/probe/mod.rs`: reviewed 1-950; omitted 951-1739 (tests; production ends 786).

Existing committed integration/unit suites were inspected rather than run; focused real compiler probes above are the executed verification. The host cannot exercise CUDA, native GNU GCC, Windows clang-cl, Linux/Windows filesystem/locking/signing or GPU toolchains. No mock NVCC proof is presented as toolkit behavior. Daemon/remote stores, concurrency races, publication failure injection and performance were not executed. No load-sensitive benchmark or broad performance inference was made. After the coordinator released its quiet window, only bounded compiler fixtures ran; no baseline or dependency build was needed.

Structural exploration used the installed codebase-memory skill and baseline project `Users-viktor-Developer-github-kache-investigations-coordinator`, ready index at 2026-10-11T05:36:35Z, with 26,827 nodes and 149,258 edges. Rust coverage is semantic_partial because binding oracle, expanded calls and impl relationships are unavailable. Project unresolved-site counts are 127,041 calls and 193,239 references. Graph architecture/symbol/inbound queries provided navigation; all relevant production was checked in source. Partial graph edges and zero-name search results are not exhaustive caller/absence evidence. `graph-status.txt` preserves current coverage metadata. No claim that the index is exhaustive or that source review proves runtime safety is made.

Two unresolved groups remain in `unresolved.json`: real-toolkit CUDA epoch/host executable identity behavior, and an NVCC lock/publication seam consulted from the wrapper owner. The source allows a contention/error path to compile and reach storage with no retained build lock, but no externally observable concurrency consequence was executed; redundant publication alone is not an admitted defect. These are follow-up leads with explicit proof conditions. They do not dilute the three executed CC results.
'''
(ROOT/'report.md').write_text(report)
