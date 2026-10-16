import json, os, pathlib, shutil, subprocess, sys, tempfile, time
ROOT = pathlib.Path(__file__).resolve().parent
BASE = pathlib.Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug')

def environment(case):
    env = {k:v for k,v in os.environ.items() if not k.startswith(('KACHE_', 'CARGO_', 'RUSTC_', 'XDG_'))}
    for name in ('home','cargo-home','runtime','store','tmp'):
        (case/name).mkdir(exist_ok=True)
    (case/'config.toml').write_text('[cache]\nlocal_only = true\n')
    env.update(HOME=str(case/'home'), RUSTUP_HOME=os.environ.get('RUSTUP_HOME','/Users/viktor/.rustup'), CARGO_HOME=str(case/'cargo-home'), KACHE_CONFIG=str(case/'config.toml'), KACHE_CACHE_DIR=str(case/'store'), KACHE_RUNTIME_DIR=str(case/'runtime'), TMPDIR=str(case/'tmp'), TMP=str(case/'tmp'), TEMP=str(case/'tmp'), KACHE_LOCAL_ONLY='1', KACHE_CACHE_EXECUTABLES='1', KACHE_LOG='kache=debug', RUSTC_WRAPPER='', CC='clang', CXX='clang++', HOST_CC='clang', HOST_CXX='clang++')
    for key in ('HOME','CARGO_HOME','KACHE_CONFIG','KACHE_CACHE_DIR','KACHE_RUNTIME_DIR','TMPDIR','TMP','TEMP'):
        assert pathlib.Path(env[key]).resolve().is_relative_to(ROOT.resolve()), (key,env[key])
    return env

def run(argv, cwd, env, label, timeout=90):
    p = subprocess.run([str(a) for a in argv],cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
    (ROOT/'evidence'/f'{label}.log').write_text('ARGV '+json.dumps([str(a) for a in argv])+'\nCWD '+str(cwd)+'\nENV '+json.dumps({k:env[k] for k in ('HOME','RUSTUP_HOME','CARGO_HOME','KACHE_CONFIG','KACHE_CACHE_DIR','KACHE_RUNTIME_DIR','TMPDIR','RUSTC_WRAPPER')})+'\nEXIT '+str(p.returncode)+'\n'+p.stdout+p.stderr)
    if p.returncode:
        print(p.stdout+p.stderr,flush=True)
    assert p.returncode == 0, f'{label} exited {p.returncode}'
    return p.stdout+p.stderr

def rust_marker(marker):
    case = pathlib.Path(tempfile.mkdtemp(prefix='rust-'+marker+'-', dir=ROOT/'fixtures'))
    env = environment(case); project=case/'project'; source=project/marker
    source.mkdir(parents=True)
    (project/'Cargo.toml').write_text('[workspace]\n[package]\nname="restoration_probe"\nversion="0.1.0"\nedition="2024"\n[[bin]]\nname="restoration_probe"\npath="'+marker+'/main.rs"\n')
    code='fn main() { println!("1"); }\n'
    (source/'main.rs').write_text(code)
    (project/'main.rs').write_text(code)
    # A literal marker resolves to the wrong existing source after expansion.
    (project/'target').mkdir()
    if marker in ('__kache_root__','__kache_target_rule__'):
        (project/'target'/'main.rs').write_text(code)
    env['RUSTC_WRAPPER']=str(BASE/'kache')
    steps=[]
    def build(label):
        output=run(['cargo','build','--offline','-vv'],project,env,marker+'-'+label)
        value=run([project/'target/debug/restoration_probe'],project,env,marker+'-'+label+'-output').strip()
        deps={str(f.relative_to(project)):f.read_text() for f in (project/'target').rglob('*.d')}
        steps.append(dict(label=label,value=value,deps=deps,cache_hit='cache hit' in output.lower()))
        print(marker,label,value,json.dumps(deps),flush=True)
        return value
    build('cold')
    # Keep only the stand-in required by root/target marker expansions.
    shutil.rmtree(project/'target')
    if marker in ('__kache_root__','__kache_target_rule__'):
        (project/'target').mkdir(); (project/'target/main.rs').write_text(code)
    build('restore')
    time.sleep(1.1)
    (source/'main.rs').write_text('fn main() { println!("2"); }\n')
    actual=build('after-source-change')
    result=dict(marker=marker,case=str(case),steps=steps,actual=actual,expected='2')
    (ROOT/'evidence'/f'{marker}-result.json').write_text(json.dumps(result,indent=2)+'\n')
    assert actual=='2', f'RESTORATION_SOURCE_CHANGE_MISSED: literal {marker} dependency changed but executable returned {actual}, expected 2'
    print('SOURCE_CHANGE_TRACKED',marker)

if __name__=='__main__':
    rust_marker(sys.argv[1] if len(sys.argv)>1 else '__kache_cwd__')
