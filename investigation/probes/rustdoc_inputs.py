import os,pathlib,subprocess,tempfile,shutil,json,sys
root=pathlib.Path(__file__).resolve().parent.parent
case=pathlib.Path(tempfile.mkdtemp(prefix='rustdoc-'+sys.argv[1]+'-',dir=root))
kache='/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache'
toolchain=os.environ.get('AUDIT_RUSTDOC_TOOLCHAIN')
lookup=['rustup','which','rustdoc']+(['--toolchain',toolchain] if toolchain else [])
rustdoc=subprocess.check_output(lookup,text=True).strip()
(case/'config.toml').write_text('[cache]\nauto_gc = false\ndaemon_publish = false\n')
(case/'home').mkdir(); (case/'foo').mkdir()
mode=sys.argv[1]
if mode=='nested':
 (case/'lib.rs').write_text('pub mod foo;\n')
 (case/'foo.rs').write_text('pub mod child;\n')
 watched=case/'foo/child.rs'; watched.write_text('/// OLD_MARKER\npub fn thing() {}\n')
elif mode=='doc_include':
 (case/'lib.rs').write_text('#![doc = include_str!("README.md")]\npub fn thing() {}\n')
 watched=case/'README.md';watched.write_text('OLD_MARKER\n')
elif mode=='outer_doc_include':
 (case/'lib.rs').write_text('#[doc = include_str!("README.md")]\npub fn thing() {}\n')
 watched=case/'README.md';watched.write_text('OLD_MARKER\n')
elif mode=='env':
 (case/'lib.rs').write_text('#![doc = env!("DOC_TEXT")]\npub fn thing() {}\n')
env={k:v for k,v in os.environ.items() if not k.startswith(('KACHE_','CARGO_','RUSTC_'))}
env.update(HOME=str(case/'home'),XDG_CONFIG_HOME=str(case/'home'),KACHE_CONFIG=str(case/'config.toml'),KACHE_HOST_CONFIG=str(case/'absent.toml'),KACHE_CACHE_DIR=str(case/'cache'),KACHE_AUTO_GC='0',KACHE_DAEMON_PUBLISH='0',KACHE_PROGRESS='off',RUSTC_BOOTSTRAP='1',RUSTC_WRAPPER='',DOC_TEXT='OLD_MARKER')
args=[rustdoc,'lib.rs','--crate-name','docprobe','--crate-type','rlib','--edition','2021','-Z','unstable-options','--merge=none','--parts-out-dir',str(case/'parts'),'-o',str(case/'out')]
def run(label,wrapped):
 p=subprocess.run(([kache] if wrapped else [])+args,cwd=case,env=env,capture_output=True,text=True,timeout=30)
 (case/(label+'.stderr')).write_text(p.stderr); print(label,'exit',p.returncode,repr(p.stderr[:180]));assert p.returncode==0
 text=''.join(p.read_text(errors='replace') for p in (case/'out/docprobe').rglob('*.html'))
 (case/(label+'.markers.json')).write_text(json.dumps({'old': 'OLD_MARKER' in text, 'new':'NEW_MARKER' in text}))
 return text
cold=run('cold',True); assert 'OLD_MARKER' in cold
shutil.rmtree(case/'out');shutil.rmtree(case/'parts')
if mode=='env': env['DOC_TEXT']='NEW_MARKER'
else: watched.write_text(watched.read_text().replace('OLD_MARKER','NEW_MARKER'))
warm=run('warm',True)
shutil.rmtree(case/'out');shutil.rmtree(case/'parts')
fresh=run('direct',False)
print('CASE',case,'warm_old=', 'OLD_MARKER' in warm,'warm_new=', 'NEW_MARKER' in warm,'direct_new=', 'NEW_MARKER' in fresh)
assert 'NEW_MARKER' in fresh, 'direct control failed'
assert 'NEW_MARKER' in warm, 'RUSTDOC_STALE_INPUT_'+mode+': warm cache returned docs predating changed compiler input'
