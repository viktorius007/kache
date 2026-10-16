import json, os, pathlib, subprocess, tempfile
from probe_support import BIN, ROOT, config, ipc, run, start, stop

def main():
    rustc=os.environ.get('KACHE_AUDIT_RUSTC') or subprocess.check_output(['rustup','which','rustc'],text=True).strip()
    with tempfile.TemporaryDirectory(prefix='kache-rds-',dir='/private/tmp') as temp:
        d=pathlib.Path(temp);(d/'home').mkdir();(d/'remote').mkdir();(d/'out').mkdir();(d/'volume').mkdir()
        source=d/'fixture.rs';source.write_text('pub fn value() -> u32 { 11 }\n')
        seed,env=config(d,'seed');handle=start(seed,env)
        try:
            run([BIN,rustc,'--crate-name','fixture','--crate-type','rlib','--emit','link,dep-info','--out-dir',str(d/'out'),str(source)],env,d)
            metas=list((seed/'cache'/'store').glob('*/meta.json'));assert len(metas)==1,'seed fixture must cache one entry'
            key=json.loads(metas[0].read_text())['cache_key'];run([BIN,'sync','--push'],env,d)
        finally: stop(seed,handle)
        cold,env=config(d,'cold',volumes=True);handle=start(cold,env)
        main_entry=cold/'cache'/'store'/key;shard_entry=cold/'shard'/'store'/key
        checks=[{'key':key,'crate_name':'fixture','entry_dir':str(main_entry),'deadline_ms':3000},{'key':key,'crate_name':'fixture','entry_dir':str(shard_entry),'shard_dir':str(cold/'shard'),'deadline_ms':3000}]
        try:
            response=ipc(cold,{'batch_remote_check':{'checks':checks}})
            print('batch_response:',json.dumps(response,sort_keys=True),flush=True)
            print('main_committed_metadata:',(main_entry/'meta.json').exists(),'shard_committed_metadata:',(shard_entry/'meta.json').exists(),flush=True)
            assert response.get('ok') is True,'fixture batch must succeed'
            found=response.get('batch_found') or response.get('found_keys') or response.get('results')
            print('response_found_field:',found,flush=True)
            assert (main_entry/'meta.json').exists() and (shard_entry/'meta.json').exists(), 'SHARD_SINGLEFLIGHT_FALSE_HIT: batch reports requested key found but one requested store has no entry'
        finally: stop(cold,handle);(ROOT/'probe_shards.daemon.log').write_bytes((cold/'daemon.log').read_bytes())
if __name__=='__main__':main()
