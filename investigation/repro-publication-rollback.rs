use kache_store::{ArtifactPolicy, ArtifactStore};
use kache_store::config::Config;
use rusqlite::Connection;
use std::{fs, path::PathBuf};
struct Policy;
impl ArtifactPolicy for Policy {
    fn allow_hardlink(_: &str) -> bool { false }
    fn allow_empty(_: &str, _: &[String]) -> bool { false }
    fn emit_kind(_: &str) -> Option<&'static str> { Some("link") }
    fn stable_after_store(_: &str) -> bool { false }
}
fn main() {
    let dir = tempfile::tempdir().unwrap();
    let config = Config { cache_dir: dir.path().join("cache"), max_size: 1 << 20, gc_evict_shared: true, upload_spool_max_jobs: 128, deferred_durability: false };
    let store = ArtifactStore::<Policy>::open(config.clone()).unwrap();
    let old = dir.path().join("old.rlib");
    let peer = dir.path().join("peer.rlib");
    fs::write(&old, b"old artifact").unwrap();
    fs::write(&peer, b"peer artifact").unwrap();
    let a = "a".repeat(64); let b = "b".repeat(64);
    let put = |key: &str, path: &PathBuf| store.put_with_compile_time_independent(key, "fixture", &["rlib".into()], &[], "", "dev", &[(path.clone(), "fixture.rlib".into())], "", "", 1);
    put(&a, &old).unwrap(); put(&b, &peer).unwrap();
    let original_meta = store.stored_meta(&a).unwrap();
    let peer_meta = store.stored_meta(&b).unwrap();
    let db = Connection::open(config.index_db_path()).unwrap();
    if std::env::var_os("CONTROL").is_none() {
        db.execute_batch("CREATE TRIGGER fail_publication BEFORE INSERT ON entries WHEN NEW.cache_key = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' BEGIN SELECT RAISE(ABORT, 'injected publication failure'); END;").unwrap();
        let error = put(&a, &peer).unwrap_err();
        println!("put error: {error:#}");
    }
    let persisted_meta = store.stored_meta(&a).unwrap();
    println!("old hash: {}", original_meta.files[0].hash);
    println!("persisted hash after failure: {}", persisted_meta.files[0].hash);
    println!("peer hash: {}", peer_meta.files[0].hash);
    let indexed: String = db.query_row("SELECT hash FROM entry_blobs WHERE cache_key = ?1", [&a], |r| r.get(0)).unwrap();
    println!("indexed hash after failure: {indexed}");
    println!("drift: {:?}", store.blob_index_drift().unwrap());
    store.remove_entry(&a).unwrap();
    let peer_blob = store.blob_path(&peer_meta.files[0].hash);
    println!("peer blob exists after removing failed key: {}", peer_blob.exists());
    let peer_hit = store.get(&b).unwrap().is_some();
    println!("peer cache hit after removing failed key: {peer_hit}");
    assert!(peer_hit, "a failed republication must not let removal reclaim a peer entry's only blob");
}
