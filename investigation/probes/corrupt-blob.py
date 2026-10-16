import json, os, pathlib, sqlite3, subprocess, tempfile
HERE = pathlib.Path(__file__).resolve().parent
BIN = pathlib.Path('/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache')
with tempfile.TemporaryDirectory(prefix='dedup-corruption-', dir=HERE) as tmp:
    root = pathlib.Path(tmp)
    cache = root / 'cache'
    target = root / 'target'
    target.joinpath('debug/deps').mkdir(parents=True)
    source = target / 'debug/deps/libvalid.rlib'
    body = bytes(range(256)) * 512
    source.write_bytes(body)
    config = root / 'config.toml'
    config.write_text(f'[cache]\nlocal_store = {json.dumps(str(cache))}\nruntime_dir = {json.dumps(str(root / 'runtime'))}\nauto_gc = false\n')
    env = os.environ.copy()
    env.update(KACHE_CACHE_DIR=str(cache), KACHE_RUNTIME_DIR=str(root / 'runtime'), KACHE_CONFIG=str(config), KACHE_HOST_CONFIG='', KACHE_NO_DAEMON='1', RUSTC_WRAPPER='')
    def run():
        result = subprocess.run([str(BIN), 'targets', 'share', '--apply', '--json', str(target)], env=env, cwd=root, text=True, capture_output=True, timeout=30)
        print(result.stdout, result.stderr)
        assert result.returncode == 0, 'fixture CLI failed before deduplication'
        return json.loads(result.stdout)
    run()
    digest = subprocess.check_output([str(HERE / 'blake3-file'), str(source)], text=True).strip()
    blob = cache / 'store/blobs' / digest[:2] / digest
    blob.parent.mkdir(parents=True, exist_ok=True)
    corrupt = bytearray(body)
    corrupt[len(corrupt)//2] ^= 0xff
    blob.write_bytes(corrupt)
    with sqlite3.connect(cache / 'index.db') as db:
        db.execute('INSERT OR REPLACE INTO blobs (hash, size, refcount) VALUES (?, ?, 1)', (digest, len(body)))
    # The setup invocation remembered a size rejection before the blob existed.
    with sqlite3.connect(cache / 'target-dedup.db') as db:
        db.execute('DELETE FROM reject')
    result = run()
    observed = source.read_bytes()
    print(json.dumps({'good_hash':digest, 'target_is_good': observed == body, 'target_equals_corrupt_blob': observed == bytes(corrupt), 'changed_offset': len(body)//2, 'report': result}, sort_keys=True))
    assert observed == body, 'DEDUP_CORRUPTION: sharing replaced a valid target artifact with a blob corrupted in its middle'
