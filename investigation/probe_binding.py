import json, os, pathlib, shutil, subprocess, tempfile
from probe_support import BIN, ROOT, config, run, start, stop

def main():
    rustc=os.environ.get('KACHE_AUDIT_RUSTC') or subprocess.check_output(['rustup','which','rustc'],text=True).strip()
    with tempfile.TemporaryDirectory(prefix='kache-rdb-',dir='/private/tmp') as temp:
        d=pathlib.Path(temp);(d/'home').mkdir();(d/'remote').mkdir();(d/'out').mkdir()
        source=d/'fixture.rs'; source.write_text('pub fn value() -> u32 { 11 }\n')
        args=[BIN,rustc,'--crate-name','fixture','--crate-type','rlib','--emit','link,dep-info','-C','metadata=audit','-C','extra-filename=-audit','--out-dir',str(d/'out'),str(source)]
        seed,seedenv=config(d,'seed');handle=start(seed,seedenv)
        try:
            run(args,seedenv,d)
            metas=list((seed/'cache'/'store').glob('*/meta.json')); assert len(metas)==1, 'fixture A was not cached'
            key_a=json.loads(metas[0].read_text())['cache_key']
            source.write_text('pub fn value() -> u32 { 29 }\n')
            run(args,seedenv,d)
            metas=list((seed/'cache'/'store').glob('*/meta.json')); assert len(metas)==2, 'fixture B was not cached distinctly'
            key_b=next(json.loads(p.read_text())['cache_key'] for p in metas if json.loads(p.read_text())['cache_key']!=key_a)
            run([BIN,'sync','--push'],seedenv,d)
        finally:
            stop(seed,handle);(ROOT/'probe_binding.seed.log').write_bytes((seed/'daemon.log').read_bytes())
        pack=d/'remote'/'artifacts'/'v3'/'packs'/'fixture'
        assert (pack/(key_a+'.tar.zst')).is_file() and (pack/(key_b+'.tar.zst')).is_file(), 'seed packs missing'
        print('requested_key:',key_a,'substituted_metadata_key:',key_b,flush=True)
        shutil.copyfile(pack/(key_b+'.tar.zst'),pack/(key_a+'.tar.zst'))
        source.write_text('pub fn value() -> u32 { 11 }\n')
        for p in (d/'out').iterdir(): p.unlink()
        cold,coldenv=config(d,'cold');handle=start(cold,coldenv)
        try:
            run(args,coldenv,d)
            imported=cold/'cache'/'store'/key_a/'meta.json'
            print('requested_entry_imported:',imported.exists(),flush=True)
            if imported.exists(): print('imported_metadata_key:',json.loads(imported.read_text())['cache_key'],flush=True)
            consumer=d/'consumer.rs';consumer.write_text('fn main(){println!("{}", fixture::value());}\n')
            run([rustc,'--extern','fixture='+str(d/'out'/'libfixture-audit.rlib'),str(consumer),'-o',str(d/'consumer')],coldenv,d)
            result=run([str(d/'consumer')],coldenv,d).stdout.decode().strip()
            print('expected_value: 11 observed_value:',result,flush=True)
            assert result=='11', 'WRONG_REMOTE_BINDING: request for source value 11 reused valid artifact from source value '+result
        finally:
            stop(cold,handle);(ROOT/'probe_binding.cold.log').write_bytes((cold/'daemon.log').read_bytes())
if __name__=='__main__': main()
