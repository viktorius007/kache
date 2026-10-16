"""Controls and red tests for untouched baseline exact remote restore and shard scheduling."""
import argparse
import concurrent.futures
import json
import pathlib
from probe_support import (BIN, ROOT, RUSTC, Endpoint, committed, compiler_args,
                           configure, daemon, fixture_directory, ipc, run, seed)


def binding(mode):
    label = 'binding-'+mode
    with fixture_directory() as temp:
        fixture = pathlib.Path(temp)
        keys, objects = seed(fixture, label, two_entries=True)
        requested = '/fixture/artifacts/v3/packs/fixture/'+keys[0]+'.tar.zst'
        substitute = '/fixture/artifacts/v3/packs/fixture/'+keys[1]+'.tar.zst'
        if mode == 'swap':
            objects[requested] = objects[substitute]
        elif mode == 'corrupt':
            objects[requested] = b'not a valid zstd tar pack'
        print('requested_key:', keys[0], 'substitute_key:', keys[1], 'mode:', mode, flush=True)
        (fixture/'fixture.rs').write_text('pub fn value() -> u32 { 11 }\n')
        for output in (fixture/'out').iterdir():
            output.unlink()
        with Endpoint(objects) as remote:
            base, env = configure(fixture, 'cold', endpoint=remote.url)
            with daemon(base, env, label+'.cold'):
                run(compiler_args(fixture), env, fixture)
                meta_path = base/'cache'/'store'/keys[0]/'meta.json'
                meta = json.loads(meta_path.read_text()) if meta_path.exists() else None
                print('imported_metadata_key:', meta['cache_key'] if meta else None,
                      'requested_committed:', committed(base, keys[0]), flush=True)
                assert any(r['path'] == requested and r['status'] == 200 for r in remote.requests), 'EXACT_GET_NOT_EXERCISED'
                consumer = fixture/'consumer.rs'
                consumer.write_text('fn main(){println!("{}", fixture::value());}\n')
                run([RUSTC, '--extern', 'fixture='+str(fixture/'out'/'libfixture-audit.rlib'),
                     str(consumer), '-o', str(fixture/'consumer')], env, fixture)
                observed = run([str(fixture/'consumer')], env, fixture).stdout.decode().strip()
                print('expected_value: 11 observed_value:', observed, flush=True)
                assert observed == '11', 'WRONG_REMOTE_BINDING: source returns 11 but restored valid artifact returns '+observed
                if mode == 'valid':
                    assert meta and meta['cache_key'] == keys[0], 'VALID_CONTROL_NOT_IMPORTED'
        print('PASS:', label, flush=True)


def check(base, key, shard=False):
    cache = base/('shard' if shard else 'cache')
    request = {'key': key, 'crate_name': 'fixture', 'entry_dir': str(cache/'store'/key),
               'deadline_ms': 3000}
    if shard:
        request['shard_dir'] = str(cache)
    return request


def shards(mode):
    label = 'shards-'+mode
    with fixture_directory() as temp:
        fixture = pathlib.Path(temp)
        keys, objects = seed(fixture, label)
        key = keys[0]
        with Endpoint(objects, delay=.15) as remote:
            base, env = configure(fixture, 'cold', endpoint=remote.url, volumes=True)
            with daemon(base, env, label+'.cold'):
                checks = [check(base, key), check(base, key, shard=(mode != 'same-store'))]
                if mode == 'reverse':
                    checks.reverse()
                if mode == 'sequential':
                    results = [ipc(env, {'remote_check': item}) for item in checks]
                elif mode == 'sockets':
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                        jobs = [pool.submit(ipc, env, {'remote_check': item}) for item in checks]
                        results = [job.result(timeout=10) for job in jobs]
                else:
                    reply = ipc(env, {'batch_remote_check': {'checks': checks}})
                    assert reply.get('ok') is True, 'BATCH_REQUEST_FAILED: '+json.dumps(reply)
                    results = reply['batch_results']
                print('checks:', json.dumps(checks, sort_keys=True), flush=True)
                print('results:', json.dumps(results, sort_keys=True), flush=True)
                main_hit, shard_hit = committed(base, key), committed(base, key, shard=True)
                print('main_committed:', main_hit, 'shard_committed:', shard_hit, flush=True)
                assert len(results) == 2 and all(r.get('ok') is True and r.get('found') is True for r in results), 'GENERATED_ENTRY_NOT_FOUND'
                assert main_hit and (mode == 'same-store' or shard_hit), 'SHARD_SINGLEFLIGHT_FALSE_HIT: both requests report found but a requested store has no committed entry'
        print('PASS:', label, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('probe', choices=['binding', 'shards'])
    parser.add_argument('mode')
    args = parser.parse_args()
    choices = {'binding': ['valid', 'swap', 'corrupt'],
               'shards': ['sequential', 'concurrent', 'reverse', 'same-store', 'sockets']}
    assert args.mode in choices[args.probe], choices
    print('probe:', args.probe, 'mode:', args.mode, 'baseline:', BIN, flush=True)
    {'binding': binding, 'shards': shards}[args.probe](args.mode)


if __name__ == '__main__':
    main()
