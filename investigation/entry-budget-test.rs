
#[tokio::test]
async fn investigation_packed_prefetch_obeys_the_configured_entry_budget() {
    let dir = tempfile::tempdir().unwrap();
    let mut config = test_config(dir.path());
    config.remote_key_listing = true;
    config.remote = Some(test_remote_config());
    config.prefetch_max_bytes = 0;
    let limit = if std::env::var_os("KACHE_INV_ALLOW_TWO").is_some() { 2 } else { 1 };
    config.prefetch_max_keys = limit;
    let backend = test_remote_backend();
    let daemon = Arc::new(Daemon::new(config));
    assert!(daemon.remote_backend.set(backend.clone()).is_ok());
    let context = PackPrefetchContext::from_deps(
        crate::identity::host_target_triple(), "linux/toolchain/release",
        &[("serde".into(), "1.0.0".into())],
    ).unwrap();
    let key_a = test_cache_key("investigation-budget-a");
    let key_b = test_cache_key("investigation-budget-b");
    let (payload_a, meta_a) = build_entry_pack_with_meta(&key_a, "serde");
    let (payload_b, meta_b) = build_entry_pack_with_meta(&key_b, "tokio");
    seed_packed_catalog(&backend, &context, vec![
        crate::remote_pack::PackInputEntry {cache_key:key_a.clone(),crate_name:"serde".into(),meta_digest:meta_a,payload:payload_a},
        crate::remote_pack::PackInputEntry {cache_key:key_b.clone(),crate_name:"tokio".into(),meta_digest:meta_b,payload:payload_b},
    ], None).await;
    let response = daemon.handle_prefetch_with_context(&PrefetchRequest {
        keys:vec![(key_a.clone(),"serde".into()),(key_b.clone(),"tokio".into())],
        warm_all:false,origin:None,candidate_sources:HashMap::new(),
    }, Some(context), Instant::now()).await;
    assert!(response.ok);
    wait_for_store_entry(&daemon,&key_a).await;
    let present = daemon.with_store(|store| Ok(
        [&key_a,&key_b].into_iter().filter(|key|store.get(key).unwrap().is_some()).count()
    )).unwrap();
    assert_eq!(present, limit as usize,
        "packed prefetch must honor the configured maximum entries per plan");
}
