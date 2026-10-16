
struct InvestigationSlowCatalog {
    inner: Arc<dyn crate::remote_backend::RemoteBackend>,
    dispatch: Instant,
    delay: Duration,
    late_pack_gets: Arc<AtomicU64>,
}

#[async_trait::async_trait]
impl crate::remote_backend::RemoteBackend for InvestigationSlowCatalog {
    async fn head(&self, key: &str) -> Result<bool> { self.inner.head(key).await }
    async fn get(&self, key: &str, max: Option<u64>) -> Result<Option<crate::remote_backend::GetObject>> {
        if key.contains("/v4/prefetch/catalogs/") {
            tokio::time::sleep(self.delay).await;
        }
        if key.contains("/v4/prefetch/packs/") && self.dispatch.elapsed() >= Duration::from_secs(1) {
            self.late_pack_gets.fetch_add(1, Ordering::Relaxed);
        }
        self.inner.get(key, max).await
    }
    async fn put(&self, key: &str, body: Vec<u8>, ct: Option<&str>) -> Result<()> { self.inner.put(key,body,ct).await }
    async fn list(&self, prefix: &str) -> Result<Vec<String>> { self.inner.list(prefix).await }
    fn describe(&self, key: &str) -> String { self.inner.describe(key) }
}

#[tokio::test]
async fn investigation_packed_prefetch_stops_starting_objects_after_plan_deadline() {
    let dir = tempfile::tempdir().unwrap();
    let mut config = test_config(dir.path());
    config.remote_key_listing = true;
    config.remote = Some(test_remote_config());
    config.prefetch_deadline_secs = 1;
    config.remote_restore_timeout_secs = 10;
    let inner = test_remote_backend();
    let context = PackPrefetchContext::from_deps(
        crate::identity::host_target_triple(), "linux/toolchain/release",
        &[("serde".into(), "1.0.0".into())],
    ).unwrap();
    let key = test_cache_key("investigation-plan-deadline");
    let (payload, meta_digest) = build_entry_pack_with_meta(&key,"serde");
    seed_packed_catalog(&inner,&context,vec![crate::remote_pack::PackInputEntry {
        cache_key:key.clone(),crate_name:"serde".into(),meta_digest,payload,
    }],None).await;
    let dispatch=Instant::now();
    let late_pack_gets=Arc::new(AtomicU64::new(0));
    let delay=if std::env::var_os("KACHE_INV_FAST_CATALOG").is_some() {Duration::ZERO} else {Duration::from_millis(1500)};
    let backend: Arc<dyn crate::remote_backend::RemoteBackend>=Arc::new(InvestigationSlowCatalog {
        inner,dispatch,delay,late_pack_gets:late_pack_gets.clone(),
    });
    let daemon=Arc::new(Daemon::new(config));
    assert!(daemon.remote_backend.set(backend).is_ok());
    let response=daemon.handle_prefetch_with_context(&PrefetchRequest {
        keys:vec![(key.clone(),"serde".into())],warm_all:false,origin:None,candidate_sources:HashMap::new(),
    },Some(context),dispatch).await;
    assert!(response.ok);
    let mut tasks={ std::mem::take(&mut *daemon.prefetch_tasks.lock().unwrap()) };
    tokio::time::timeout(Duration::from_secs(10),async {
        while let Some(result)=tasks.join_next().await {result.unwrap();}
    }).await.expect("fixture transfers finish independently of the plan deadline");
    if delay.is_zero() {
        assert!(daemon.with_store(|store| Ok(store.get(&key)?.is_some())).unwrap(),
            "the fast control must successfully import its valid pack");
    }
    assert_eq!(late_pack_gets.load(Ordering::Relaxed),0,
        "packed prefetch must not start another object after the plan dispatch deadline");
}
