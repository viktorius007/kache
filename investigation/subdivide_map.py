"""Apply requested eleven-agent source-boundary subdivisions to map generator."""
from pathlib import Path
p=Path(__file__).parent/'generate_map.py'
s=p.read_text()
block='''
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
'''
s=s.replace('\ndef git(*args):', block+'\ndef git(*args):')
s=s.replace("return 'cli-operations'", "return 'cli-config'").replace("return 'compiler-reuse'", "return 'cc-cuda-adapters'")
s=s.replace("relative='/'.join(parts[1:])", "relative='/'.join(parts[1:])\n  if parts[1] in ['commands'] or relative == 'monitor.mdx': return 'observability'")
s=s.replace("def reading_batches(slice_id, files):\n", "def reading_batches(slice_id, files):\n    slice_id = PARENT[slice_id]\n")
s=s.replace('7 slices; uncovered=0', '11 slices; uncovered=0')
p.write_text(s)
