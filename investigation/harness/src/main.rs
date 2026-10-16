use kache_store::{
    ArtifactPolicy, ArtifactStore,
    eviction::{EvictionPolicy, ValueDensityPolicy, would_evict_for_budget},
};
use rusqlite::Connection;
use serde_json::{Value, json};

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

fn fixture(pinned_cheap: bool) -> (tempfile::TempDir, Store, Connection) {
    let dir = tempfile::tempdir().unwrap();
    let cfg = kache_store::config::Config {
        cache_dir: dir.path().to_owned(),
        max_size: 450_000,
        gc_evict_shared: true,
        upload_spool_max_jobs: 100,
        deferred_durability: false,
    };
    let store = Store::open(&cfg).unwrap();
    for (key, bytes, fill, cost) in [
        ("expensive", 400_000, b'a', 60_000),
        ("cheap", 100_000, b'b', 7),
    ] {
        let source = dir.path().join(format!("{key}.rlib"));
        std::fs::write(&source, vec![fill; bytes]).unwrap();
        store
            .put_with_compile_time(
                key,
                "fixture",
                &["lib".into()],
                &[],
                "",
                "dev",
                &[(source, "lib.rlib".into())],
                "",
                "",
                cost,
            )
            .unwrap();
    }
    let db = Connection::open(cfg.index_db_path()).unwrap();
    db.execute(
        "UPDATE entries SET last_accessed=datetime('now','-1 hour')",
        [],
    )
    .unwrap();
    if pinned_cheap {
        db.execute(
            "UPDATE entries SET last_accessed=datetime('now') WHERE cache_key='cheap'",
            [],
        )
        .unwrap();
    }
    (dir, store, db)
}

fn replay(policy: &str, demands: &[&str]) -> Value {
    let (_dir, store, db) = fixture(false);
    let before = store.physical_size().unwrap();
    let budget = before - 405_000;
    if policy == "size-pressure" {
        let stats = store.evict().unwrap();
        assert_eq!(stats.entries_evicted, 1);
        assert_eq!(stats.bytes_freed, 400_000);
    } else {
        let candidates = store.eviction_candidates().unwrap();
        let ranking = ValueDensityPolicy.select(&candidates);
        let selected = would_evict_for_budget(&candidates, &ranking, budget);
        assert_eq!(selected, ["cheap".to_owned()].into_iter().collect());
        // All blobs are unique, entries eligible, no contention. The snapshot
        // budget is exact in this fixture; removal uses production storage.
        for key in selected {
            store.remove_entry(&key).unwrap();
        }
    }
    let retained: Vec<_> = ["expensive", "cheap"]
        .into_iter()
        .filter(|k| store.contains(k))
        .collect();
    let mut events = Vec::new();
    let mut gross_miss_ms = 0;
    let mut net_miss_ms = 0;
    for key in demands {
        let (compile_ms, serve_ms) = if *key == "expensive" {
            (60_000, 30)
        } else {
            (7, 1)
        };
        let missed = store.get(key).unwrap().is_none();
        if missed {
            gross_miss_ms += compile_ms;
            net_miss_ms += compile_ms - serve_ms;
        }
        events.push(
            json!({"key":key,"miss":missed,"compile_ms":compile_ms,"assumed_serve_ms":serve_ms}),
        );
    }
    // Advance fixture observations to a common completed horizon. This is a
    // generated clock, not a wait or wall-time performance measurement.
    db.execute("UPDATE eviction_tombstones SET evicted_at=datetime(100,'unixepoch'), demanded_at=CASE WHEN demanded_at IS NOT NULL THEN datetime(200,'unixepoch') END",[]).unwrap();
    db.execute(
        "UPDATE shadow_victims SET swept_at=datetime(100,'unixepoch')",
        [],
    )
    .unwrap();
    db.execute(
        "UPDATE entries SET last_accessed=datetime(200,'unixepoch')",
        [],
    )
    .unwrap();
    json!({"policy":policy,"before_bytes":before,"requested_reclaim_bytes":budget,"after_bytes":store.physical_size().unwrap(),"retained":retained,"events":events,"gross_miss_cost_ms":gross_miss_ms,"net_miss_cost_ms":net_miss_ms,"horizon_evidence":store.eviction_horizon_evidence(604_901,604_800).unwrap()})
}

fn main() {
    let mut traces = Vec::new();
    for (name, demands) in [
        ("expensive_requested", vec!["expensive", "cheap"]),
        ("expensive_obsolete", vec!["cheap"]),
    ] {
        traces.push(json!({"name":name,"generated_future_demands":demands,"results":[replay("size-pressure",&demands),replay("value-density",&demands)]}));
    }
    let (_dir, store, db) = fixture(true);
    let sweep = store.evict().unwrap();
    let shadow_rows: i64 = db
        .query_row("SELECT COUNT(*) FROM shadow_victims", [], |r| r.get(0))
        .unwrap();
    let observation = store.shadow_counterfactual().unwrap();
    let result = json!({"status":"DONE","objective":"sum of fixture net compile-minus-cache-serving cost on future misses after one eviction; serving costs are assumptions, not timings","capacity_bytes":450_000,"target_bytes":405_000,"inventory":[{"key":"expensive","bytes":400_000,"compile_ms":60_000},{"key":"cheap","bytes":100_000,"compile_ms":7}],"traces":traces,"protected_prefix_limit":{"live_evicted":sweep.entries_evicted,"shadow_only_rows":shadow_rows,"legacy_live_evicted":observation.live.evicted,"legacy_shadow_evicted":observation.shadow.evicted},"limits":["Generated costs, not measured compiler or cache timings","One initial sweep, unique blobs, no concurrency, no remote cache","Pure density uses public ranking and removal in a separate world; it is not enabled as live policy","No population policy winner inferred"]});
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
