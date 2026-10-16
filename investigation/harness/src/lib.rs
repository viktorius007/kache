#![cfg(test)]
use kache_store::{ArtifactPolicy, ArtifactStore};

struct FixturePolicy;
impl ArtifactPolicy for FixturePolicy {
    fn allow_hardlink(_: &str) -> bool {
        false
    }
    fn allow_empty(_: &str, _: &[String]) -> bool {
        false
    }
    fn emit_kind(_: &str) -> Option<&'static str> {
        Some("link")
    }
    fn stable_after_store(_: &str) -> bool {
        true
    }
}
type Store = ArtifactStore<FixturePolicy>;

fn config(path: &std::path::Path) -> kache_store::config::Config {
    kache_store::config::Config {
        cache_dir: path.to_owned(),
        max_size: 450_000,
        gc_evict_shared: true,
        upload_spool_max_jobs: 100,
        deferred_durability: false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rusqlite::{Connection, params};

    // The asserted cost is the fixture's metadata cost, independent of the
    // SQL selection. A zero-cost prefix is the discriminator; removing one
    // prefix row puts the recoverable entry within the batch and goes green.
    fn recover_legacy_cost(blocking_rows: usize) -> (Vec<usize>, i64) {
        let fixture = tempfile::tempdir().unwrap();
        let cfg = config(fixture.path());
        let store = Store::open(&cfg).unwrap();
        let artifact = fixture.path().join("artifact.rlib");
        std::fs::write(&artifact, b"valid legacy artifact").unwrap();
        store
            .put_with_compile_time(
                "template",
                "legacy",
                &["lib".into()],
                &[],
                "",
                "dev",
                &[(artifact, "lib.rlib".into())],
                "",
                "",
                60_000,
            )
            .unwrap();
        let mut template = serde_json::to_value(store.stored_meta("template").unwrap()).unwrap();
        let hash = template["files"][0]["hash"].as_str().unwrap().to_owned();
        let mut db = Connection::open(cfg.index_db_path()).unwrap();
        db.execute("DELETE FROM entries WHERE cache_key='template'", [])
            .unwrap();
        db.execute("DELETE FROM entry_blobs WHERE cache_key='template'", [])
            .unwrap();
        db.execute("UPDATE blobs SET refcount=0", []).unwrap();
        let tx = db.transaction().unwrap();
        for i in 0..=blocking_rows {
            let expensive = i == blocking_rows;
            let key = format!("{i:064x}");
            template["cache_key"] = key.clone().into();
            template["compile_time_ms"] = if expensive { 60_000 } else { 0 }.into();
            let dir = store.entry_dir(&key);
            std::fs::create_dir_all(&dir).unwrap();
            std::fs::write(
                dir.join("meta.json"),
                serde_json::to_vec(&template).unwrap(),
            )
            .unwrap();
            tx.execute("INSERT INTO entries(cache_key,crate_name,size,committed,compile_time_ms) VALUES(?1,'legacy',21,1,0)", params![key]).unwrap();
            tx.execute(
                "INSERT INTO entry_blobs(cache_key,hash,refs) VALUES(?1,?2,1)",
                params![key, hash],
            )
            .unwrap();
            tx.execute(
                "UPDATE blobs SET refcount=refcount+1 WHERE hash=?1",
                params![hash],
            )
            .unwrap();
        }
        tx.commit().unwrap();
        let passes = (0..3)
            .map(|_| store.backfill_compile_times().unwrap())
            .collect();
        let cost = db
            .query_row(
                "SELECT compile_time_ms FROM entries WHERE cache_key=?1",
                params![format!("{blocking_rows:064x}")],
                |r| r.get(0),
            )
            .unwrap();
        println!("blocking_rows={blocking_rows} passes={passes:?} recovered_cost_ms={cost}");
        (passes, cost)
    }

    #[test]
    fn compile_cost_backfill_does_not_starve_legacy_expensive_entry() {
        let (_, cost) = recover_legacy_cost(10_000);
        assert_eq!(
            cost, 60_000,
            "successive backfill sweeps must reach a recoverable expensive entry behind a full batch of valid zero-cost legacy entries"
        );
    }

    #[test]
    fn backfill_control_recovers_expensive_entry_inside_the_batch() {
        let (passes, cost) = recover_legacy_cost(9_999);
        assert_eq!(cost, 60_000);
        assert_eq!(passes, vec![1, 0, 0]);
    }
}
