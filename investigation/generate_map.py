#!/usr/bin/env python3
"""Generate pinned tracked-path ownership and reviewer worklists."""
import collections
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'investigation'
PIN = '4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
PROJECT = 'Users-viktor-Developer-github-kache-investigations-coordinator'
COORD = Path('/Users/viktor/Developer/github/kache-investigations/coordinator/investigation')
GROUPS = {
 'compiler-reuse': 'Compiler identity, input discovery, keys and hit/miss execution',
 'cargo-build': 'Cargo environment, build scripts, incremental and fallback behavior',
 'store-filesystem': 'Local metadata, blobs, publication, restore, target lifetime and reclamation',
 'remote-daemon': 'Remote object transport, synchronization and daemon lifecycle/concurrency',
 'planner-service': 'Planning, scheduling, planner authentication and HTTP service state',
 'cli-operations': 'Dispatch, configuration, installed services and observable reports',
 'guardrails': 'Test and benchmark harnesses, CI, release/package delivery and collateral',
}
SRC = {
 'compiler-reuse': 'args cache_key checked_regions compile compiler extra_inputs identity key_env native_archive native_link_key path_normalizer policy probe probe_memo toolchain_dylib tree_stamp verify_compare wrapper',
 'cargo-build': 'build_script build_script_inputs cargo_env cargo_layout cargo_proxy fallback incremental_policy out_dir_alias test_runner',
 'store-filesystem': 'blob_heal cache_fs compiler_store disk_recovery index_compact link_probe maintenance opcounts prestage store_view target_cleanup target_dedup target_liveness target_seed target_use unit_prune volume_gc worktree_discovery',
 'remote-daemon': 'cache_remote daemon daemon_control daemon_lifecycle daemon_publish heartbeat prediction_share remote remote_backend remote_layout remote_pack remote_resilience shards transport',
 'planner-service': 'build_intent demand fallback_planner machine planner_auth planner_client remote_plan scheduler timeline_client',
 'cli-operations': 'cli config config_tui events explain init_shell main miss_chain notice otel phase_trace platform report run_diff savings service since term timeline tui tui_sessions wrapper_config',
 'guardrails': 'test_support',
}
MODULE_OWNER = {m: s for s, words in SRC.items() for m in words.split()}
TESTS = {
 'compiler-reuse': 'cache_key_underkeying cached_units_regression cc_family_probe cc_passthrough_args cc_release_regression codegen_backend extra_inputs_warm_target input_prediction macos_adaptive_debug_info macos_native_install_name metadata_streaming nvcc_cuda_toolchain proc_macro_env_key stale_artifact unknown_compiler_probe workspace_extra_inputs worktree_depinfo',
 'cargo-build': 'adaptive_incremental adaptive_incremental_workspace build_script_declared_inputs build_script_inputs build_script_launcher cargo_proxy custom_harness fallback_recovery incremental_passthrough out_dir_alias test_runner',
 'store-filesystem': 'eviction_evidence readonly_store',
 'remote-daemon': 'filesystem_remote s3_remote',
 'cli-operations': 'cli_commands host_config macos_local_network_metadata',
 'guardrails': 'binstall_metadata integration',
}
TEST_OWNER = {m+'_test.rs': s for s, names in TESTS.items() for m in names.split()}
DOC_OWNER = {
 'how-it-works/cache-key.mdx':'compiler-reuse', 'how-it-works/build-scripts.mdx':'cargo-build',
 'deduplication.mdx':'store-filesystem', 'remote-service.mdx':'planner-service',
 'how-it-works/limits.mdx':'planner-service', 'benchmarks.mdx':'guardrails',
 'getting-started/mutation-testing.mdx':'guardrails', 'getting-started/c-cpp.mdx':'compiler-reuse',
 'getting-started/cuda.mdx':'compiler-reuse', 'getting-started/rustdoc.mdx':'compiler-reuse',
}
CRATE_OWNER = {'kache-format':'store-filesystem','kache-store':'store-filesystem','kache-fs':'store-filesystem','kache-shims':'cargo-build','kache-core':'planner-service','kache-service':'planner-service','kache-e2e':'guardrails','kache-proofs':'guardrails'}
OBLIGATIONS = {
 'compiler-reuse': [
 'Trace Rust, rustdoc, C/C++ and CUDA entry paths from compiler detection through eligibility, dependency discovery, key derivation, compile/passthrough and restore; preserve compiler exit status and diagnostic/artifact behavior.',
 'Account for every compiler-observable input, mutation between discovery/compile/publication, prediction validity, native linking, target specs, proc macros, diagnostic flags and path normalization; compare same-input reuse across worktrees and changed-input invalidation.',
 'Review inline tests and regression fixtures fully; vary real observable compiler output or exit status for candidate proofs. Public degree-zero methods are not evidence of dead code.',
 ],
 'cargo-build': [
 'Trace Cargo shim and wrapper chains, argument/environment overrides, manifest/target/Cargo-home identities, build directory isolation, inherited jobserver behavior and compile/test child lifetimes.',
 'Trace build-script installation, launch fallback, declared file/environment inputs, package walks, hermetic out directories, replayed outputs outside OUT_DIR, symlinks, permissions and paths across relocation.',
 'Trace adaptive incremental state, seed-to-incremental transitions, explicit user controls, fallback wrappers and test-result reuse; inspect cancellation, stdout drains and side effects under isolated fixtures.',
 ],
 'store-filesystem': [
 'Trace entry and blob lifecycle through metadata validation, hash memoization, SQLite/index state, staged writes, atomic publication, failed restore, entry deletion and blob reclamation.',
 'Review reflink/hardlink/copy choices, carrier leases, reader/writer mutation isolation, executable bits, readonly stores, cross-volume fallback, symlinks, concurrent processes and crash/partial-write ordering.',
 'Trace target cleanup, deduplication, seeding, liveness and recovery so user files and active artifacts remain safe; distinguish measured physical space from logical counters.',
 ],
 'remote-daemon': [
 'Trace exact remote reads, bounded metadata/blob/pack downloads, validation before local import, publish/merge/conditional-update conflict paths, retry/offline behavior, queued uploads and bounded growth.',
 'Trace daemon startup, readiness negotiation, exclusive replacement, peer admission, socket identity, draining/shutdown, task cancellation, compile handoff and transfer spools under multiple clients.',
 'Review credentials and CI read-only policy through the daemon environment and every transport (S3/GCS/filesystem/OCI); input source and publisher trust determine consequences.',
 ],
 'planner-service': [
 'Trace intent and manifest planning, fallback disposition, client-side prediction/prefetch decisions, resource permits, machine memory limits, demand signaling and service request/response schemas.',
 'Trace static/OIDC/GitHub auth, credential origin/trusted endpoint decisions, request/decompression bounds, SQLite writes, concurrent planner requests, timeline ingestion, metrics/health/readiness and HA leases.',
 'Review server startup and deployment configuration composition with Helm/Nix and CLI login/config; establish actual production consumers before relying on public API names or comments.',
 ],
 'cli-operations': [
 'Trace main dispatch for CLI, compiler shim, build-script launcher, Cargo shim and test runner; command parsing, environment/config precedence, defaults, migration and path derivation must compose with owning domains.',
 'Review init/doctor/clean/sync/reporting/service-install operations for isolated fixture correctness, machine-readable output/schema consistency, failure exit status and handling of stale/missing installed binaries.',
 'Trace event/timeline/stat aggregation, TUI and report behavior against actual emitted semantics; investigate only external consequences relevant to integrity, reuse, resources and operations.',
 ],
 'guardrails': [
 'Read test/e2e/benchmark framework wiring, assertion oracles, fixture isolation, scenario selection/skip behavior, process control, resource gates and compiler-free restore checks; a green run does not prove integrity.',
 'Review CI, mutation diff scopes, workflow policy/authorization, fuzz target/corpus, benchmark gate statistics, release signing/version consistency and package install/uninstall paths for meaningful guardrails.',
 'Account explicitly for benchmark-only subjects, generated lockfiles, binary fixtures, demo/media assets and licenses; distinguish fully read configuration/frameworks from sampled workload executions.',
 ],
}
SAMPLING = {
 'compiler-reuse': ['macOS host: Linux/Windows linking, filesystem and compiler-specific behavior require source review plus declared execution limits.', 'Rust focus does not permit silently skipping C/C++/CUDA/rustdoc; name every unexecuted toolchain branch.'],
 'cargo-build': ['Build-script arbitrary external probes/side effects need declared scope; fixture subprocesses and cancellation paths can be exercised without real homes.', 'Cargo and Rust version combinations need explicit tested versions; no general compatibility claim from one installed toolchain.'],
 'store-filesystem': ['APFS can run locally; Linux/Windows reflink, cgroup and file permission paths require platform-specific source review and declared runtime limits.', 'Crash/failure injection and multi-process interleavings are sampled, with exact chosen cut points recorded.'],
 'remote-daemon': ['Use fixture filesystem and local wire servers; live cloud/registry credential/ETag semantics require primary documentation and declared nonexecution.', 'Timeout, replacement and cancellation interleavings are selected explicitly; no exhaustive concurrency claim.'],
 'planner-service': ['Fixture HTTP/SQLite paths can run locally; Kubernetes HA leases and external OIDC key rotation are source/documentation review unless isolated emulation is executed.', 'Resource/admission/load measurements require coordination for a quiet window; measured workloads do not establish global performance.'],
 'cli-operations': ['Use isolated HOME/config/runtime paths. Actual launchd/systemd/Task Scheduler modifications are unauthorized; review generated service artifacts and source.', 'Terminal interactivity and unsupported platform branches require explicit read-vs-executed reporting.'],
 'guardrails': ['Read harness/CI/package configurations fully; executing all 70+ scenario subjects and cloud/package ecosystems is outside one local review and must be declared sampled.', 'Binary/media collateral receives identity/purpose/reference accounting, not semantic code-review claims; exported benchmarks are workload-specific.'],
}
SEAMS = [
 ('dispatch-compiler','cli-operations','compiler-reuse','src/main.rs dispatch → compiler detection/wrapper.run; disabled/reentrant/direct invocation and exit propagation'),
 ('dispatch-cargo-launcher','cli-operations','cargo-build','src/main.rs dispatch → cargo_proxy/build_script/test_runner; argv/environment ownership'),
 ('compiler-build-inputs','cargo-build','compiler-reuse','build_script_inputs/extra_inputs/incremental_policy → Rust key/prediction decisions; declarations and mutation validation'),
 ('compiler-store-hit','compiler-reuse','store-filesystem','wrapper/hit/compile → kache-store/compile preclean; output completeness, diagnostics, mtimes, carrier isolation'),
 ('compiler-flight-permits','planner-service','compiler-reuse','scheduler/demand/machine → wrapper compile/discovery flights; permit and per-key lock lifetimes'),
 ('compile-daemon-handoff','remote-daemon','compiler-reuse','wrapper/remote → daemon/daemon_publish; failed handoff, cancellation, child ownership and spooled artifacts'),
 ('store-import-publish','store-filesystem','remote-daemon','kache-format validators + kache-store imported entries ↔ remote_pack/remote_backend; verify sizes/names/hashes before publication'),
 ('daemon-planner','planner-service','remote-daemon','daemon build sessions/manifests ↔ planner_client/build_intent/remote_plan; fallback and bounded prefetch'),
 ('daemon-service-config','remote-daemon','cli-operations','Config/socket paths/service environment ↔ daemon control/replacement; read-only credential lifetime and readiness'),
 ('auth-login-client','planner-service','cli-operations','cli/login + config ↔ planner_auth/client/server auth; credential origin and trusted endpoint binding'),
 ('target-cargo-incremental','store-filesystem','cargo-build','target liveness/cleanup/seeding ↔ Cargo build dirs/incremental/out-dir aliases; active readers and persistent artifacts'),
 ('telemetry-schema','cli-operations','planner-service','events/report/timeline ↔ kache-core timeline and timeline_client/server ingest; schema, counters, bounded retention'),
 ('package-runtime','guardrails','cli-operations','Cargo metadata/build.rs/install assets/scripts/Helm/Nix ↔ service/config/shim behavior; installed artifacts and version contracts'),
 ('guardrail-domain-oracles','guardrails','all','kache-e2e/scripts/CI/scenario oracles ↔ each domain-specific test; real compiler/process/remote observations and meaningful failure discrimination'),
]
CONTRACTS = [
 ('key-equivalence','docs/how-it-works/cache-key.mdx',6,'Kache hashes the inputs that can change compiler output and normalizes machine-local paths that should not. Missing a real input risks a wrong hit; retaining harmless machine identity causes avoidable misses.'),
 ('build-rerun','docs/how-it-works/build-scripts.mdx',36,"Kache reuses Cargo's own rule for when a build script must rerun. A recorded run"),
 ('build-local-only','docs/how-it-works/build-scripts.mdx',91,'Entries stay in the local store: `kache sync` never uploads them.'),
 ('blob-references','docs/deduplication.mdx',16,'Entries refer to blobs through metadata and the SQLite index. Identical bytes share one blob even when they came from different cache keys. Garbage collection removes a blob only after no entry needs it.'),
 ('restore-isolation','docs/deduplication.mdx',26,'C/C++ objects and the files a cached build script wrote are cloned onto their own inode or copied, never hardlinked.'),
 ('remote-publisher-trust','docs/remote-cache/overview.mdx',47,'A remote contains compiler outputs. Only give write access to jobs and people'),
 ('planner-optional','docs/remote-service.mdx',10,'The planner ranks likely artifacts before rustc asks for exact keys. It is optional: local caching, exact remote lookup, sync, and client-side fallback planning work without it.'),
 ('format-validation','crates/kache-format/README.md',16,'Deserializing an entry only decodes it. Callers still validate names and keys, check artifact sizes and hashes, and apply their own import policy.'),
 ('ci-merge-gate','AGENTS.md',3,'`just check` is not the merge gate. CI mutation-tests changed Rust lines in the kache binary. A PR that only ran `cargo test` on the new tests will go red on Mutation testing. That is the usual failure.'),
]

# Subdivide broad seams into independent module contracts before dispatch.
PARENT = {
 'rust-wrapper':'compiler-reuse', 'key-native-inputs':'compiler-reuse', 'cc-cuda-adapters':'compiler-reuse',
 'store-core':'store-filesystem', 'filesystem-targets':'store-filesystem',
 'cli-config':'cli-operations', 'observability':'cli-operations',
 'cargo-build':'cargo-build', 'remote-daemon':'remote-daemon', 'planner-service':'planner-service', 'guardrails':'guardrails',
}
GROUPS = {
 'rust-wrapper':'Rust/rustdoc wrapper, discovery, compilation, hits and diagnostics',
 'key-native-inputs':'Cache-key identity, normalization, external and native inputs',
 'cc-cuda-adapters':'C/C++/CUDA compiler adapters, flags, probes and eligibility',
 'cargo-build':'Cargo, build scripts, incremental, fallback and test reuse',
 'store-core':'Store metadata, blobs, hash memos, atomic publication and restore policy',
 'filesystem-targets':'Filesystem primitives, target lifetime, reclamation and recovery',
 'remote-daemon':'Remote objects and daemon lifecycle, concurrency and trust',
 'planner-service':'Planning, scheduling, authentication and service state',
 'cli-config':'CLI dispatch, configuration, shims and installed services',
 'observability':'Events, timelines, statistics, diagnostics, reports and terminal UI',
 'guardrails':'Frameworks, CI, fuzz, benchmarks, packaging and collateral',
}
RUST_MODULES = set('args compile verify_compare wrapper'.split())
KEY_MODULES = set('cache_key checked_regions extra_inputs identity key_env native_archive native_link_key path_normalizer policy toolchain_dylib tree_stamp'.split())
STORE_CORE_MODULES = set('cache_fs compiler_store opcounts store_view'.split())
OBS_MODULES = set('events explain miss_chain otel phase_trace report run_diff savings since timeline tui tui_sessions term'.split())
for m, old in list(MODULE_OWNER.items()):
 if old == 'compiler-reuse': MODULE_OWNER[m] = 'rust-wrapper' if m in RUST_MODULES else 'key-native-inputs' if m in KEY_MODULES else 'cc-cuda-adapters'
 if old == 'store-filesystem': MODULE_OWNER[m] = 'store-core' if m in STORE_CORE_MODULES else 'filesystem-targets'
 if old == 'cli-operations': MODULE_OWNER[m] = 'observability' if m in OBS_MODULES else 'cli-config'
CC_TESTS = set('cc_family_probe cc_passthrough_args cc_release_regression nvcc_cuda_toolchain unknown_compiler_probe'.split())
RUST_TESTS = set('cached_units_regression macos_adaptive_debug_info metadata_streaming stale_artifact'.split())
for name, old in list(TEST_OWNER.items()):
 base = name.removesuffix('_test.rs')
 if old == 'compiler-reuse': TEST_OWNER[name] = 'cc-cuda-adapters' if base in CC_TESTS else 'rust-wrapper' if base in RUST_TESTS else 'key-native-inputs'
 if old == 'store-filesystem': TEST_OWNER[name] = 'store-core'
 if old == 'cli-operations': TEST_OWNER[name] = 'cli-config'
for name, old in list(DOC_OWNER.items()):
 if old == 'compiler-reuse': DOC_OWNER[name] = 'rust-wrapper' if 'rustdoc' in name else 'cc-cuda-adapters' if any(x in name for x in ['c-cpp','cuda']) else 'key-native-inputs'
 if old == 'store-filesystem': DOC_OWNER[name] = 'filesystem-targets'
 if old == 'cli-operations': DOC_OWNER[name] = 'cli-config'
for name, old in list(CRATE_OWNER.items()):
 if old == 'store-filesystem': CRATE_OWNER[name] = 'filesystem-targets' if name == 'kache-fs' else 'store-core'
OBLIGATIONS = {new:OBLIGATIONS[parent] + ['Restrict primary statements to this exact sub-scope path list; inspect declared neighboring seams as consultation, with no double primary ownership.'] for new,parent in PARENT.items()}
SAMPLING = {new:SAMPLING[parent] + ['Read every assigned production path in full. Large dedicated test suites may be sampled only with named ranges/cases and exact omissions in the report.'] for new,parent in PARENT.items()}
RENAMES = {'compiler-reuse':'rust-wrapper','store-filesystem':'store-core','cli-operations':'cli-config'}
SEAMS = [(i,RENAMES.get(a,a),RENAMES.get(b,b),c) for i,a,b,c in SEAMS]
SEAMS += [
 ('rust-key-inputs','key-native-inputs','rust-wrapper','Rust wrapper discovery/eligibility/compilation ↔ cache key and native dependency closure; predicted and actual inputs, stable reuse, mutation guard'),
 ('cc-key-inputs','cc-cuda-adapters','key-native-inputs','C/C++/CUDA classification/probes/depfiles ↔ cache key/path/native inputs; compiler-observable flags and identity'),
 ('rust-cc-dispatch','rust-wrapper','cc-cuda-adapters','wrapper.run_cc/run_nvcc dispatch and generic adapter interface ↔ concrete compiler execution and restore'),
 ('store-fs-target-isolation','filesystem-targets','store-core','kache-fs clone/copy/identity and target lifetime/reclamation ↔ store publication/link/carrier leases and blob references'),
 ('cli-observable-contract','observability','cli-config','CLI flags/config and command dispatch ↔ events, reports, explain, statistics, schemas and terminal output'),
]

def git(*args):
 return subprocess.check_output(['git',*args],cwd=ROOT)

def owner(path):
 parts=path.split('/')
 if parts[0]=='src':
  if path in ['src/compiler/rustc.rs','src/compiler/rustdoc.rs']: return 'rust-wrapper'
  key=parts[1].removesuffix('.rs')
  if key not in MODULE_OWNER: raise ValueError(f'unowned module {path}')
  return MODULE_OWNER[key]
 if parts[0]=='crates': return CRATE_OWNER[parts[1]]
 if parts[0]=='launcher': return 'cargo-build'
 if parts[0]=='tests':
  if parts[1] in TEST_OWNER: return TEST_OWNER[parts[1]]
  if len(parts)>2 and parts[1]=='fixtures' and parts[2]=='config_editor_legacy.toml': return 'cli-config'
  if len(parts)>2 and parts[1]=='fixtures' and (parts[2].startswith('mock_cc') or parts[2] in ['cc_release_regressions.sh','native_archive_fuzz']): return 'cc-cuda-adapters'
  return 'guardrails'
 if parts[0]=='test-projects': return 'cargo-build'
 if parts[0]=='docs':
  relative='/'.join(parts[1:])
  if parts[1] in ['commands'] or relative == 'monitor.mdx': return 'observability'
  if relative in DOC_OWNER: return DOC_OWNER[relative]
  if parts[1] in ['remote-cache','daemon']: return 'remote-daemon'
  return 'cli-config'
 return 'guardrails'

def kind(path,mode,data):
 if mode=='120000': return 'symlink-collateral'
 if b'\0' in data or Path(path).suffix in ['.gif','.png','.webm','.o']: return 'binary-collateral'
 if path.startswith('assets/'): return 'demo-or-visual-collateral'
 if path.endswith(('LICENSE','Cargo.lock','package-lock.json','flake.lock')): return 'license-or-lock-collateral'
 if path.startswith('scenarios/'): return 'benchmark-fixture' if '/bench-' in path else 'scenario-fixture'
 if '/tests/' in path or path.startswith(('tests/','test-projects/')) or path.endswith('/tests.rs'): return 'test-or-fixture'
 if path.startswith(('docs/','.github/')) or path.endswith(('.md','.mdx')): return 'contract-doc-or-ci'
 if path.endswith(('.rs','.py','.sh','.mjs','.nix')): return 'source-or-script'
 return 'config-or-delivery-collateral'

def reading_batches(slice_id, files):
    slice_id = PARENT[slice_id]
    result = collections.defaultdict(list)
    for item in files:
        p = item['path']
        module = p.split('/')[1].removesuffix('.rs') if p.startswith('src/') else ''
        if slice_id == 'compiler-reuse':
            tag = 'wrapper-execution' if module in ['wrapper','compile','verify_compare'] else 'key-and-prediction' if module in ['cache_key','extra_inputs','tree_stamp','identity','key_env','path_normalizer'] else 'native-and-toolchains' if module in ['native_archive','native_link_key','toolchain_dylib'] else 'compiler-adapters-probes-and-eligibility'
        elif slice_id == 'store-filesystem':
            tag = 'metadata-store-publication' if p.startswith(('crates/kache-format/','crates/kache-store/')) else 'filesystem-primitives' if p.startswith('crates/kache-fs/') else 'targets-recovery-and-maintenance'
        elif slice_id == 'remote-daemon':
            tag = 'daemon-lifecycle-handoff' if module.startswith('daemon') or module in ['heartbeat','transport'] else 'remote-object-backends-and-layout'
        elif slice_id == 'cargo-build':
            tag = 'build-script-execution-and-declarations' if module.startswith('build_script') or p.startswith('launcher/') else 'cargo-incremental-fallback-test-and-shims'
        elif slice_id == 'planner-service':
            tag = 'http-service-state-and-auth' if p.startswith('crates/kache-service/') or module in ['planner_auth','planner_client','timeline_client'] else 'planning-scheduling-and-resources'
        elif slice_id == 'cli-operations':
            tag = 'configuration' if module in ['config','config_tui','wrapper_config'] or 'configuration' in p else 'events-reports-and-terminal' if module in ['events','explain','miss_chain','report','run_diff','savings','since','term','timeline','tui','tui_sessions','otel','phase_trace'] else 'dispatch-commands-installed-services-and-contracts'
        else:
            tag = 'scenario-fixtures-and-benchmark-subjects' if p.startswith(('scenarios/','test-projects/')) else 'test-and-benchmark-frameworks' if p.startswith(('crates/kache-e2e/','crates/kache-proofs/','tests/','fuzz/')) else 'ci-and-tooling' if p.startswith(('.github/','scripts/','.cargo/','.config/')) or p in ['Justfile','AGENTS.md'] else 'delivery-collateral-and-dependency-contracts'
        result[tag].append(item)
    return [{'id':name,'paths':[p['path'] for p in values],'text_lines':sum(p['text_lines'] or 0 for p in values),'review_state':'queued'} for name,values in sorted(result.items())]

def emit():
 assert git('rev-parse','HEAD').decode().strip()==PIN
 inventory=[]
 for item in git('ls-tree','-rz','--long',PIN).split(b'\0'):
  if not item: continue
  head, rawpath=item.split(b'\t',1)
  mode,typ,sha,size=head.decode().split()
  path=rawpath.decode(); data=git('show',f'{PIN}:{path}')
  inventory.append({'path':path,'primary_slice':owner(path),'mode':mode,'git_type':typ,'blob':sha,'bytes':int(size),'text_lines':None if b'\0' in data else len(data.splitlines()),'kind':kind(path,mode,data),'review_state':'mapped-unreviewed','expected_depth':('identity-purpose-reference-accounting' if kind(path,mode,data) in ['binary-collateral','symlink-collateral','demo-or-visual-collateral','license-or-lock-collateral'] else 'full-text-contract-and-risk-review'),'executed_depth':'none','reading_sections':[{'start_line':start,'end_line':min(start+5999,len(data.splitlines())),'state':'queued'} for start in range(1,len(data.splitlines())+1,6000)] if b'\0' not in data and kind(path,mode,data) not in ['binary-collateral','symlink-collateral','demo-or-visual-collateral','license-or-lock-collateral'] else []})
 frontier_bytes=(COORD/'frontier.json').read_bytes()
 (OUT/'raw/frontier-input.json').write_bytes(frontier_bytes)
 frontier=json.loads(frontier_bytes)
 rows=frontier['frontier']; claims=[]
 for i,row in enumerate(rows):
  primary={owner(p) for p in row['paths'] if p!='.'}
  if row['paths']==['.']: primary={'guardrails'}
  if len(primary)!=1: raise ValueError(f'frontier ownership ambiguity {i}')
  claims.append({'input_index':i,'primary_slice':next(iter(primary)),'mode':row['mode'],'paths':row['paths'],'stale_reason':row['stale_reason'],'staleness_commits':row.get('staleness_commits')})
 slices=[]
 for s,title in GROUPS.items():
  files=[p for p in inventory if p['primary_slice']==s]
  contracts=[dict(id=id,path=p,line=line,quote=q,primary_slice=owner(p)) for id,p,line,q in CONTRACTS if owner(p)==s]
  slices.append({'id':s,'title':title,'paths':[p['path'] for p in files],'path_count':len(files),'bytes':sum(p['bytes'] for p in files),'text_lines':sum(p['text_lines'] or 0 for p in files),'kind_counts':dict(collections.Counter(p['kind'] for p in files)),'risk_obligations':OBLIGATIONS[s],'contracts':contracts,'reading_batches':reading_batches(s,files),'sampling_needs':SAMPLING[s],'frontier_rows':sum(c['primary_slice']==s for c in claims),'subdivisions':sorted(set(p['path'].split('/')[1] if p['path'].startswith('crates/') else p['path'].split('/')[0] for p in files))})
  work={'baseline_commit':PIN,'slice':s,'title':title,'primary_paths':files,'reading_batches':reading_batches(s,files),'obligations':OBLIGATIONS[s],'contracts':contracts,'owned_interactions':[dict(id=i,primary_slice=a,consult_slice=b,contract=c) for i,a,b,c in SEAMS if a==s],'consult_interactions':[dict(id=i,primary_slice=a,consult_slice=b,contract=c) for i,a,b,c in SEAMS if b in [s,'all']],'sampling_needs':SAMPLING[s],'expected_coverage_report':'Record every path as fully read, sampled with bounds, or pending. Mapped is not reviewed. Fully read production/framework/configuration paths and explicitly record runtime sampling.'}
  (OUT/f'worklists/{s}.json').write_text(json.dumps(work,indent=2)+'\n')
  markdown=[f'# {title}',f'\nBaseline: `{PIN}`. Primary paths: {len(files)}; bytes: {sum(p["bytes"] for p in files)}.\n','## Planned review depth\n','Code, tests, fixtures, configuration and contract prose: full-text contract/risk review planned. Binary, symlink, demo/media, license and lock collateral: identity, purpose and reference accounting planned. Completed review depth is none for every path. Oversized text files have queued contiguous 6000-line reading sections in JSON; all sections must be read or explicitly marked sampled/pending.\n','## Reading subdivisions\n']+[f'- {b["id"]}: {len(b["paths"])} paths, {b["text_lines"]} text lines; subdivide into the listed contiguous file sections when needed.' for b in reading_batches(s,files)]+['\n## Obligations\n']+[f'- {p}' for p in OBLIGATIONS[s]]+['\n## Owned interactions\n']+[f'- {i}: consult {b}; {c}' for i,a,b,c in SEAMS if a==s]+['\n## Sampling declarations\n']+[f'- {p}' for p in SAMPLING[s]]+['\n## Primary path inventory\n','Every path below has this slice as its sole primary owner. Mapped-unreviewed; no completed review is claimed.\n']+[f'- `{p["path"]}` ({p["kind"]}; {p["bytes"]} bytes; {p["text_lines"]} text lines)' for p in files]
  (OUT/f'worklists/{s}.md').write_text('\n'.join(markdown)+'\n')
 allpaths=[p['path'] for p in inventory]
 assert len(allpaths)==len(set(allpaths))==843
 assert sorted(p for s in slices for p in s['paths'])==sorted(allpaths)
 obj={'schema_version':1,'baseline_commit':PIN,'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'purpose':'Closed primary-ownership map; not a defect hunt or completed review','source_of_truth':'git ls-tree -rz --long at the pinned commit','counts':{'tracked_paths':len(inventory),'assigned_paths':len(inventory),'uncovered':0,'overlaps':0,'slices':len(slices),'bytes':sum(p['bytes'] for p in inventory),'text_lines':sum(p['text_lines'] or 0 for p in inventory),'binary_paths':sum(p['kind']=='binary-collateral' for p in inventory),'symlink_paths':sum(p['mode']=='120000' for p in inventory),'frontier_rows':len(rows),'frontier_assigned_rows':len(claims)},'frontier_input':{'path':str(COORD/'frontier.json'),'sha256':hashlib.sha256(frontier_bytes).hexdigest(),'warnings':frontier.get('warnings'),'global_standards_owner':'guardrails','global_standards_consults':list(GROUPS)},'graph':{'project':PROJECT,'root':'/Users/viktor/Developer/github/kache-investigations/coordinator','indexed_at':'2026-10-11T05:36:35Z','status':'ready','nodes':26827,'edges':149258,'semantic_status':'semantic_partial','reasons':['binding_oracle_unavailable','expanded_calls_unavailable','impl_relationships_unavailable'],'coverage_gap_entries':27,'recorded_partial_files':9,'recorded_excluded_files':17,'recorded_excluded_dir':'.cargo','coverage_pagination_complete':True,'limits':'Rust relationships are positive hints, never exhaustive; graph entry_points is capped at 20; inspect static/dynamic/conditional/macro production wiring and every gap directly.'},'mapping_evidence':['get_architecture structure and boundaries: CLI→config 66; blob_heal→kache-store 33; remote_backend→config/layout 8 each (best effort positive graph edges)','trace_path run_rustc inbound: compiler.rustc.RustcCompiler.execute_with_args, lsp strategy 0.95 confidence; count lower bound due semantic_partial','Source main.rs module declarations 1-100 and dispatcher at 839; crate kache-store lib.rs module declarations 1-19 corroborate boundaries','Cargo.toml workspace members and dependency declarations establish crate boundaries','All 843 blobs were read for line/binary classification; this is inventory inspection, not semantic review'],'slices':slices,'interactions':[dict(id=i,primary_slice=a,consult_slice=b,contract=c) for i,a,b,c in SEAMS],'repository_contracts':[dict(id=id,path=p,line=line,quote=q,primary_slice=owner(p)) for id,p,line,q in CONTRACTS],'inventory':inventory,'frontier_ownership':claims,'review_completion':{'fully_reviewed_paths':0,'sampled_review_paths':0,'mapped_unreviewed_paths':843}}
 (OUT/'audit-map.json').write_text(json.dumps(obj,indent=2)+'\n')
 (OUT/'findings.json').write_text('[]\n')
 print('PASS: 843 tracked paths; 11 slices; uncovered=0; overlaps=0; 2530 frontier rows assigned')
 print(json.dumps([dict(slice=s['id'],paths=s['path_count'],bytes=s['bytes'],lines=s['text_lines']) for s in slices],indent=2))

if __name__=='__main__': emit()
