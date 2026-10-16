import json,os,pathlib,subprocess,tempfile,shutil,time,sys
root=pathlib.Path(__file__).resolve().parent
mode=sys.argv[1] if len(sys.argv)>1 else '__kache_cwd__'
case=pathlib.Path(tempfile.mkdtemp(prefix='sentinel-',dir=root/'fixtures'))
project=case/'project';source=project/mode
source.mkdir(parents=True)
(project/'Cargo.toml').write_text('[package]\nname="sentinel_probe"\nversion="0.1.0"\nedition="2024"\n[[bin]]\nname="sentinel_probe"\npath="'+mode+'/main.rs"\n')
code='fn main() { println!("1"); }\n'
(source/'main.rs').write_text(code)
# The wrong expanded dependency resolves, so the existence-only restore gate cannot reject it.
(project/'main.rs').write_text(code)
(case/'home').mkdir(); (case/'config.toml').write_text('[cache]\nlocal_only = true\n')
env={k:v for k,v in os.environ.items() if not k.startswith(('KACHE_','RUSTC_WRAPPER','CARGO_TARGET_DIR','CARGO_HOME','XDG_'))}
env.update(HOME=str(case/'home'),RUSTUP_HOME='/Users/viktor/.rustup',CARGO_HOME=str(case/'cargo-home'),KACHE_CONFIG=str(case/'config.toml'),KACHE_CACHE_DIR=str(case/'store'),KACHE_RUNTIME_DIR=str(case/'runtime'),KACHE_LOCAL_ONLY='1',KACHE_CACHE_EXECUTABLES='1',KACHE_LOG='kache=debug',RUSTC_WRAPPER='/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache',CC='clang',CXX='clang++',HOST_CC='clang',HOST_CXX='clang++')
steps=[]
def build(label):
 p=subprocess.run(['cargo','build','--offline','-vv'],cwd=project,env=env,capture_output=True,text=True,timeout=90)
 (root/'evidence'/f'{mode}-{label}.log').write_text(p.stdout+p.stderr)
 assert p.returncode==0,(label,p.stdout,p.stderr)
 result=subprocess.check_output([project/'target/debug/sentinel_probe'],text=True).strip()
 ds={str(f.relative_to(project)):f.read_text() for f in (project/'target').rglob('*.d')}
 steps.append({'label':label,'result':result,'dep_info':ds})
 print(label,result,ds,flush=True)
 return result
build('cold');shutil.rmtree(project/'target');build('restore')
(source/'main.rs').write_text('fn main() { println!("2"); }\n')
new_time=time.time()+2
os.utime(source/'main.rs',(new_time,new_time))
actual=build('after-source-change')
report={'mode':mode,'case':str(case),'steps':steps,'actual':actual,'expected':'2'}
(root/'evidence'/f'{mode}-result.json').write_text(json.dumps(report,indent=2)+'\n')
assert actual=='2',f'changed compiler input returned stale executable output {actual}, expected 2'
