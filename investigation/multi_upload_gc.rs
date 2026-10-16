use super::*;

struct BusyStore {
    config: Config,
    store: Store,
    writer: rusqlite::Connection,
}

struct PipelineProbe {
    root: tempfile::TempDir,
    daemon: Arc<Daemon>,
    busy: Vec<BusyStore>,
    jobs: Vec<UploadJob>,
}

struct PipelineResult {
    health_before_release: bool,
    health_ms: f64,
    peers_before_release: usize,
    finished_before_release: usize,
    finished_total: usize,
}

fn busy_store(config: Config, root: &Path, victim: &str) -> BusyStore {
    let store = Store::open(&config).unwrap();
    put_upload_evict_entry(&store, root, victim, 200, false);
    let writer = rusqlite::Connection::open(config.index_db_path()).unwrap();
    BusyStore { config, store, writer }
}

fn pipeline_fixture(shards: usize, upload_workers: usize) -> PipelineProbe {
    let root = tempfile::tempdir().unwrap();
    let mut config = test_config(&root.path().join("main"));
    config.max_size = 100;
    config.s3_concurrency = upload_workers as u32;
    config.remote = Some(test_remote_config());
    let mut busy = Vec::new();
    for index in 0..shards {
        let cache_dir = root.path().join(format!("shard{index}"));
        let volume = crate::config::VolumeStore {
            volume: cache_dir.to_string_lossy().into_owned(),
            store: cache_dir,
            max_size: Some(100),
        };
        let shard_config = config.for_volume_store(&volume, |_| None);
        busy.push(busy_store(shard_config, root.path(), &format!("shard_victim_{index}")));
        config.volume_stores.push(volume);
    }
    busy.insert(0, busy_store(config.clone(), root.path(), "main_victim"));
    let jobs = (0..32).map(|index| {
        let key = test_cache_key(&format!("pipeline-gc-{index}"));
        seed_store_entry(&config, &key, "serde", root.path());
        persist_upload_job(&config, &UploadJob {
            entry_dir: String::new(), key, crate_name: "serde".into(),
            client_epoch: 0, client_version: None,
        }).unwrap()
    }).collect();
    let daemon = daemon_on(config, &test_remote_backend());
    daemon.with_store(|_| Ok(())).unwrap();
    // Intent publication also takes gc.lock; clear its diagnostic before the probe.
    fs::write(busy[0].config.store_dir().join("gc.lock"), b"").unwrap();
    PipelineProbe { root, daemon, busy, jobs }
}

fn begin_writers(probe: &PipelineProbe) {
    for busy in &probe.busy {
        busy.writer.execute_batch("BEGIN IMMEDIATE").unwrap();
    }
}

fn release_writers(probe: &PipelineProbe) {
    for busy in &probe.busy {
        busy.writer.execute_batch("ROLLBACK").unwrap();
    }
}

fn wait_for_sweep(probe: &PipelineProbe, index: usize) {
    let path = probe.busy[index].config.store_dir().join("gc.lock");
    let deadline = Instant::now() + Duration::from_secs(5);
    while fs::read_to_string(&path).unwrap_or_default().trim().is_empty() {
        if Instant::now() >= deadline {
            release_writers(probe);
            panic!("the production upload pipeline must enter store {index}'s sweep");
        }
        std::thread::sleep(Duration::from_millis(1));
    }
}

fn launch_workers(
    runtime: &tokio::runtime::Runtime, daemon: &Arc<Daemon>, workers: usize,
    receiver: tokio::sync::mpsc::Receiver<UploadJob>,
) -> (Vec<tokio::task::JoinHandle<()>>, mpsc::Receiver<(String, Response)>) {
    let receiver = Arc::new(tokio::sync::Mutex::new(receiver));
    let (done_tx, done_rx) = mpsc::channel();
    let handles = (0..workers).map(|_| {
        let receiver = receiver.clone();
        let daemon = daemon.clone();
        let done_tx = done_tx.clone();
        runtime.spawn(async move {
            while let Some(job) = next_upload_job(&receiver).await {
                let response = run_upload_job(&daemon, &job).await;
                done_tx.send((job.key, response)).unwrap();
            }
        })
    }).collect();
    (handles, done_rx)
}

fn finish_and_validate(
    probe: &PipelineProbe, runtime: &tokio::runtime::Runtime,
    handles: Vec<tokio::task::JoinHandle<()>>, done: &mpsc::Receiver<(String, Response)>,
    responses: &mut Vec<(String, Response)>,
) {
    runtime.block_on(async {
        for handle in handles { handle.await.unwrap(); }
    });
    responses.extend(done.try_iter());
    assert_eq!(responses.len(), 32, "every durable job must finish");
    for (key, response) in responses {
        assert!(response.ok, "upload {key} failed: {response:?}");
        assert!(!upload_spool_path(&probe.daemon.config, key).exists());
    }
    for (index, busy) in probe.busy.iter().enumerate() {
        let victim = if index == 0 { "main_victim".into() } else { format!("shard_victim_{}", index - 1) };
        assert!(!busy.store.contains(&victim), "GC must evict {victim}");
        assert!(crate::report::read_gc_stats(&busy.config.cache_dir).is_some());
    }
    assert!(probe.root.path().is_dir());
}

fn probe_pipeline_gc(async_workers: usize, upload_workers: usize, shards: usize) -> PipelineResult {
    let mut probe = pipeline_fixture(shards, upload_workers);
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .worker_threads(async_workers).enable_all().build().unwrap();
    runtime.block_on(async {
        let mut pending = probe.daemon.pending_uploads.write().await;
        pending.extend(probe.jobs.iter().map(|job| job.key.clone()));
    });
    let (sender, receiver) = tokio::sync::mpsc::channel(upload_workers * 2);
    let (handles, done) = launch_workers(&runtime, &probe.daemon, upload_workers, receiver);
    let first = probe.jobs.remove(0);
    let first_key = first.key.clone();
    begin_writers(&probe);
    sender.blocking_send(first).unwrap();
    wait_for_sweep(&probe, 0);
    // A separate thread feeds the bounded queue even while all async workers wait.
    let jobs = std::mem::take(&mut probe.jobs);
    let feed = std::thread::spawn(move || {
        for job in jobs { sender.blocking_send(job).unwrap(); }
    });
    for index in 1..probe.busy.len() { wait_for_sweep(&probe, index); }
    let (health_tx, health_rx) = mpsc::channel();
    let daemon = probe.daemon.clone();
    let start = Instant::now();
    runtime.spawn(async move { health_tx.send((daemon.handle_health(), start.elapsed())).unwrap(); });
    let early = health_rx.recv_timeout(Duration::from_millis(400));
    std::thread::sleep(Duration::from_millis(400).saturating_sub(start.elapsed()));
    let mut responses: Vec<_> = done.try_iter().collect();
    let finished_before_release = responses.len();
    let peers_before_release = responses.iter().filter(|(key, _)| key != &first_key).count();
    release_writers(&probe);
    feed.join().unwrap();
    let health_before_release = early.is_ok();
    let (health, elapsed) = early.unwrap_or_else(|_| health_rx.recv_timeout(Duration::from_secs(5)).unwrap());
    assert!(health.ok && health.health.is_some());
    finish_and_validate(&probe, &runtime, handles, &done, &mut responses);
    PipelineResult {
        health_before_release, health_ms: elapsed.as_secs_f64() * 1000.0,
        peers_before_release, finished_before_release, finished_total: responses.len(),
    }
}

#[test]
#[ignore = "isolated production upload-pipeline scheduling probe"]
fn measure_pipeline_gc_capacity() {
    for (async_workers, upload_workers, shards) in [(1,16,0), (2,1,0), (2,16,0), (16,16,0), (2,16,1), (16,16,1)] {
        for repetition in 0..3 {
            let result = probe_pipeline_gc(async_workers, upload_workers, shards);
            println!("D5_PIPELINE async_workers={async_workers} upload_workers={upload_workers} stores={} repetition={repetition} health_before_release={} health_ms={:.3} peers_before_release={} finished_before_release={} finished_total={}",
                shards + 1, result.health_before_release, result.health_ms,
                result.peers_before_release, result.finished_before_release, result.finished_total);
        }
    }
}

#[test]
fn two_async_workers_allow_health_while_main_and_shard_sweeps_wait_for_writers() {
    let result = probe_pipeline_gc(2, 16, 1);
    assert!(result.health_before_release,
        "health must progress before writers release during main+shard post-upload sweeps; latency {:.3} ms", result.health_ms);
}

#[test]
fn two_async_workers_allow_health_while_one_store_sweep_waits_for_a_writer() {
    let result = probe_pipeline_gc(2, 16, 0);
    assert!(result.health_before_release);
    assert_eq!(result.peers_before_release, 31, "peer uploads should skip the held GC lock and finish");
}
