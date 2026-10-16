use kache_store::{ArtifactPolicy, ArtifactStore, BuildClaim};
use kache_store::config::Config;
use rusqlite::Connection;
use std::{fs, path::{Path, PathBuf}};
struct Policy;
impl ArtifactPolicy for Policy {
    fn allow_hardlink(_: &str) -> bool { false }
    fn allow_empty(_: &str, _: &[String]) -> bool { false }
    fn emit_kind(_: &str) -> Option<&'static str> { Some("link") }
    fn stable_after_store(_: &str) -> bool { false }
}
fn refs(db: &Connection, hash: &str) -> i64 {
    db.query_row("SELECT refcount FROM blobs WHERE hash=?1", [hash], |r| r.get(0)).unwrap_or(-1)
}
fn main() {
    let mode = std::env::args().nth(1).unwrap();
    let root = PathBuf::from(std::env::var_os("FIXTURE_ROOT").unwrap()).canonicalize().unwrap();
    for key in ["HOME", "KACHE_CONFIG", "KACHE_CACHE_DIR", "KACHE_RUNTIME_DIR", "CARGO_HOME", "TMPDIR", "TMP", "TEMP"] {
        let path = PathBuf::from(std::env::var_os(key).unwrap());
        assert!(path.starts_with(&root), "fixture escape in {key}: {}", path.display());
    }
    let cache = PathBuf::from(std::env::var_os("KACHE_CACHE_DIR").unwrap());
    let config = Config { cache_dir: cache.clone(), max_size: 1<<20, gc_evict_shared: true, upload_spool_max_jobs: 128, deferred_durability: false };
    assert!(config.index_db_path().starts_with(&root));
    assert!(config.store_dir().starts_with(&root));
    println!("ASSERTED fixture root={} config={} store={}",root.display(), std::env::var("KACHE_CONFIG").unwrap(),config.store_dir().display());
    let store = ArtifactStore::<Policy>::open(config.clone()).unwrap();
    let old = root.join("old.rlib"); let peer = root.join("peer.rlib");
    fs::write(&old,b"old artifact").unwrap(); fs::write(&peer,b"peer artifact").unwrap();
    let a="a".repeat(64); let b="b".repeat(64);
    let put=|key: &str, source: &Path| store.put_with_compile_time_independent(key,"fixture", &["rlib".into()], &[],"","dev", &[(source.to_path_buf(), "fixture.rlib".into())], "","",1);
    put(&b,&peer).unwrap();
    if mode != "fresh-error" { put(&a,&old).unwrap(); }
    let old_meta=store.stored_meta(&a);
    let peer_meta=store.stored_meta(&b).unwrap();
    let peer_hash=&peer_meta.files[0].hash;
    let db=Connection::open(config.index_db_path()).unwrap();
    if mode=="healthy-claim" {
        assert!(matches!(store.claim_build(&a).unwrap(), BuildClaim::Committed(_)), "healthy key must bypass publication");
        println!("PASS healthy committed claim bypasses publication"); return;
    }
    if mode.starts_with("remove-") {
        let table = if mode=="remove-entry-error" {"entries"} else {"blobs"};
        let op = if table=="entries" {"DELETE"} else {"UPDATE"};
        db.execute_batch(&format!("CREATE TRIGGER fail_remove BEFORE {op} ON {table} BEGIN SELECT RAISE(ABORT, 'recoverable removal failure'); END;")).unwrap();
        let error=store.remove_entry(&a).unwrap_err();
        assert!(format!("{error:#}").contains("recoverable removal failure"));
        println!("EXPECTED removal SQLite error: {error:#}");
        assert!(store.contains(&a));
        assert_eq!(store.stored_meta(&a).unwrap().files[0].hash,old_meta.unwrap().files[0].hash);
        assert!(store.get(&a).unwrap().is_some());
        assert!(store.get(&b).unwrap().is_some());
        println!("PASS removal rollback preserves old metadata, both hits, and blob references"); return;
    }
    if mode!="fresh-error" {
        fs::remove_file(store.entry_dir(&a).join("meta.json")).unwrap();
        assert!(store.get(&a).unwrap().is_none());
    }
    let lock=match store.claim_build(&a).unwrap() { BuildClaim::Acquired(lock)=>lock, _=>panic!("stranded or fresh key must reach publication through a production build claim") };
    println!("ASSERTED production build claim acquired after cache miss");
    if mode!="replacement-control" {
        db.execute_batch("CREATE TRIGGER fail_publication BEFORE INSERT ON entries WHEN NEW.cache_key='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' BEGIN SELECT RAISE(ABORT, 'recoverable publication failure'); END;").unwrap();
        let error=put(&a,&peer).unwrap_err();
        assert!(format!("{error:#}").contains("recoverable publication failure"));
        println!("EXPECTED publication SQLite error: {error:#}");
    } else { put(&a,&peer).unwrap(); }
    drop(lock);
    let indexed: Option<String>=db.query_row("SELECT hash FROM entry_blobs WHERE cache_key=?1",[&a],|r|r.get(0)).ok();
    let persisted=store.stored_meta(&a).unwrap().files[0].hash.clone();
    println!("STATE indexed={indexed:?} filesystem={persisted} peer={peer_hash} peer_refcount={}",refs(&db,peer_hash));
    if mode=="fresh-error" {
        assert!(!store.contains(&a)); assert!(store.get(&a).unwrap().is_none());
        store.remove_entry(&a).unwrap();
        assert!(store.get(&b).unwrap().is_some()); assert_eq!(refs(&db,peer_hash),1);
        println!("PASS first-publication rollback leaves no committed entry and preserves peer"); return;
    }
    if mode!="replacement-control" {
        assert_eq!(indexed.as_deref(),Some(old_meta.unwrap().files[0].hash.as_str()),"SQL references should roll back");
        assert_eq!(refs(&db,peer_hash),1);
    }
    if mode=="replacement-hit-error" {
        let hit=store.get(&a).unwrap().is_some();
        println!("OBSERVED failed replacement produces cache hit={hit}");
        assert!(!hit,"failed replacement of stranded entry must not publish a new cache hit under old committed row"); return;
    }
    store.remove_entry(&a).unwrap();
    let blob_exists=store.blob_path(peer_hash).exists();
    let peer_hit=store.get(&b).unwrap().is_some();
    println!("OBSERVED peer_blob_exists={blob_exists} peer_hit={peer_hit} peer_refcount={}",refs(&db,peer_hash));
    assert!(peer_hit,"failed republication must not let removal reclaim a peer entry's only blob");
    assert_eq!(refs(&db,peer_hash),1);
    println!("PASS replacement and removal preserve peer");
}
