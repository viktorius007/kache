use crate::config::Config;
use crate::daemon::{Daemon, RemoteCheckRequest};
use crate::remote_backend::{RemoteBackend, anonymous_s3_backend_for_bucket};
use std::path::Path;
use std::sync::{Arc, atomic::{AtomicUsize, Ordering}};
use std::time::{Duration, Instant};
use tokio::io::{AsyncReadExt, AsyncWriteExt};
include!("config_fixture.rs");

async fn run_scenario(pool: usize, occupied: usize, artifact_mib: usize, tiny_budget_ms: u64, poison: bool) -> (bool, u128, usize) {
    let fixture = tempfile::tempdir_in(env!("CARGO_MANIFEST_DIR")).unwrap();
    let mut source_config = test_config(&fixture.path().join("source-cache"));
    source_config.max_size = 4 << 30;
    let source_store = crate::store::Store::open(&source_config).unwrap();
    let artifact = fixture.path().join("libfixture.rlib");
    // Incompressible deterministic fixture, independent from pack admission.
    let mut state = 0x123456789abcdef_u64;
    let bytes: Vec<u8> = (0..artifact_mib * (1 << 20)).map(|_| {
        state ^= state << 13; state ^= state >> 7; state ^= state << 17; state as u8
    }).collect();
    std::fs::write(&artifact, &bytes).unwrap();
    drop(bytes);
    let remote_root = fixture.path().join("remote");
    let remote = crate::config::RemoteConfig {
        prefix: "prefix".into(),
        backend: crate::config::RemoteBackendConfig::Filesystem(crate::config::FilesystemRemoteConfig {
            root: remote_root.clone(), atomic_write_dir: remote_root.join(".tmp"),
        }),
    };
    let file_backend = crate::remote_backend::create_backend(&remote, 30).await.unwrap();
    let mut keys = Vec::new();
    for index in 0..occupied + 4 {
        let key = blake3::hash(format!("permit-fixture-{index}").as_bytes()).to_hex().to_string();
        let input = if index >= occupied {
            let tiny = fixture.path().join("tiny.rlib");
            std::fs::write(&tiny, b"a valid tiny artifact").unwrap(); tiny
        } else { artifact.clone() };
        source_store.put(&key, "fixture", &["lib".into()], &[], "aarch64-apple-darwin", "debug", &[(input, "libfixture.rlib".into())], "", "").unwrap();
        crate::remote_layout::RemoteLayout::new(file_backend.as_ref(), &remote)
            .upload_entry_until(&key, "fixture", &source_store.entry_dir(&key), &source_store.blobs_dir(), 1, None).await.unwrap();
        keys.push(key);
    }
    let total_pack_bytes: u64 = keys.iter().take(occupied).map(|key| {
        let pack = format!("prefix/v3/packs/fixture/{key}.tar.zst");
        std::fs::metadata(remote_root.join(pack)).unwrap().len()
    }).sum();
    println!("FIXTURE slow_packs={occupied} compressed_bytes={total_pack_bytes} artifact_mib={artifact_mib}");
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let endpoint = format!("http://{}", listener.local_addr().unwrap());
    let active = Arc::new(AtomicUsize::new(0));
    let small_requests = Arc::new(AtomicUsize::new(0));
    let release = Arc::new(tokio::sync::Notify::new());
    let small_keys = keys.iter().skip(occupied).cloned().collect::<Vec<_>>();
    let server = {
        let active = active.clone(); let small_requests = small_requests.clone(); let release = release.clone();
        tokio::spawn(async move {
            loop {
                let (mut socket, _) = listener.accept().await.unwrap();
                let root = remote_root.clone(); let active = active.clone(); let small_requests = small_requests.clone();
                let release = release.clone(); let small_keys = small_keys.clone();
                tokio::spawn(async move {
                    let mut request = Vec::new();
                    while !request.ends_with(b"\r\n\r\n") { request.push(socket.read_u8().await.unwrap()); }
                    let request = String::from_utf8(request).unwrap();
                    let line = request.lines().next().unwrap();
                    let path = line.split_whitespace().nth(1).unwrap().trim_start_matches("/bucket/");
                    if line.starts_with("HEAD ") {
                        socket.write_all(b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nConnection: close\r\n\r\n").await.unwrap(); return;
                    }
                    let mut contents = tokio::fs::File::open(root.join(path)).await.unwrap();
                    let length = contents.metadata().await.unwrap().len();
                    socket.write_all(format!("HTTP/1.1 200 OK\r\nContent-Length: {}\r\nConnection: close\r\n\r\n", length).as_bytes()).await.unwrap();
                    if small_keys.iter().any(|key| path.contains(key)) {
                        small_requests.fetch_add(1, Ordering::SeqCst);
                        tokio::io::copy(&mut contents, &mut socket).await.unwrap();
                    } else {
                        let mut prefix = [0; 1024];
                        contents.read_exact(&mut prefix).await.unwrap();
                        socket.write_all(&prefix).await.unwrap();
                        active.fetch_add(1, Ordering::SeqCst);
                        release.notified().await;
                        let _ = tokio::io::copy(&mut contents, &mut socket).await;
                    }
                });
            }
        })
    };
    let mut config = test_config(&fixture.path().join("restore"));
    config.s3_concurrency = pool as u32;
    config.remote_restore_timeout_secs = 30;
    config.remote = Some(crate::config::RemoteConfig::test_s3("bucket", "prefix"));
    let backend: Arc<dyn RemoteBackend> = Arc::new(anonymous_s3_backend_for_bucket(&endpoint, "bucket"));
    let daemon = Arc::new(Daemon::new(config.clone()));
    daemon.set_remote_backend_for_test(backend.clone());
    let mut downloads = Vec::new();
    for key in keys.iter().take(occupied) {
        let request = RemoteCheckRequest {
            key: key.clone(), crate_name: "fixture".into(),
            entry_dir: config.store_dir().join(key).display().to_string(),
            shard_dir: None, deadline_ms: Some(20_000),
        };
        let daemon = daemon.clone();
        downloads.push(tokio::spawn(async move { daemon.handle_remote_check(&request).await }));
    }
    tokio::time::timeout(Duration::from_secs(10), async {
        while active.load(Ordering::SeqCst) < occupied { tokio::time::sleep(Duration::from_millis(5)).await; }
    }).await.expect("all demanded packs must have opened real HTTP bodies");
    let head_start = Instant::now();
    assert!(backend.head("control").await.unwrap());
    let head_ms = head_start.elapsed().as_millis();
    let request = RemoteCheckRequest {
        key: keys.last().unwrap().clone(), crate_name: "fixture".into(),
        entry_dir: config.store_dir().join(keys.last().unwrap()).display().to_string(),
        shard_dir: None, deadline_ms: Some(tiny_budget_ms),
    };
    let start = Instant::now();
    let result = if poison {
        let mut victims = Vec::new();
        for key in keys.iter().skip(occupied).take(3) {
            let daemon = daemon.clone();
            let req = RemoteCheckRequest {
                key: key.clone(), crate_name: "fixture".into(),
                entry_dir: config.store_dir().join(key).display().to_string(),
                shard_dir: None, deadline_ms: Some(tiny_budget_ms),
            };
            victims.push(tokio::spawn(async move { daemon.handle_remote_check(&req).await }));
        }
        for victim in victims {
            let reply = victim.await.unwrap();
            println!("VICTIM found={:?}", reply.found);
        }
        for task in &downloads { task.abort(); }
        for task in downloads.drain(..) { let _ = task.await; }
        let stats = daemon.handle_stats(&crate::daemon::StatsRequest {
            include_entries: false, include_summaries: false, sort_by: None,
            event_hours: None, event_secs: None, client_epoch: 0, client_version: None,
        }).stats.expect("fixture stats must be available");
        assert_eq!(stats.s3_concurrency_used, 0, "aborting demands must release every request permit");
        println!("CAPACITY total={} used={} suppressed={}", stats.s3_concurrency_total, stats.s3_concurrency_used, stats.downloads_suppressed);
        assert!(backend.head("control-after-release").await.unwrap());
        let recovery = Instant::now();
        let reply = daemon.handle_remote_check(&request).await;
        println!("RECOVERY after_capacity_release=true found={:?} elapsed_ms={} tiny_wire_gets={}", reply.found, recovery.elapsed().as_millis(), small_requests.load(Ordering::SeqCst));
        reply
    } else { daemon.handle_remote_check(&request).await };
    let elapsed = start.elapsed().as_millis();
    let sent = small_requests.load(Ordering::SeqCst);
    println!("MEASURE pool={pool} occupied={occupied} artifact_mib={artifact_mib} tiny_budget_ms={tiny_budget_ms} active={} head_ms={head_ms} tiny_found={:?} tiny_ms={elapsed} tiny_wire_gets={sent}", active.load(Ordering::SeqCst), result.found);
    release.notify_waiters();
    for task in downloads { task.abort(); let _ = task.await; }
    server.abort(); let _ = server.await;
    (result.found == Some(true), elapsed, sent)
}

#[tokio::test]
async fn remote_permits_probe_measure() {
    for (pool, occupied, mib) in [(4, 3, 1), (4, 4, 1), (16, 15, 32), (16, 16, 32)] {
        let (found, elapsed, sent) = run_scenario(pool, occupied, mib, 1000, false).await;
        if occupied < pool { assert!(found && sent == 1 && elapsed < 1000); }
        else { assert!(!found && sent == 0 && elapsed >= 990); }
    }
}

#[tokio::test]
async fn remote_permits_probe_small_hit_survives_large_demand() {
    let (found, _, _) = run_scenario(16, 16, 32, 1000, false).await;
    assert!(found, "a tiny valid remote hit was lost behind sixteen large demand restores");
}

#[tokio::test]
async fn remote_permits_probe_default_budget() {
    let (found, _, sent) = run_scenario(16, 16, 32, 3000, false).await;
    assert!(found && sent == 1, "the uniform default caller must reach its valid pack after occupied demands expire");
}

#[tokio::test]
async fn remote_permits_probe_recovery_after_queue_timeout() {
    let (green, _, _) = run_scenario(4, 3, 1, 1000, true).await;
    assert!(green, "control recovery must hit with spare capacity");
    let (found, _, _) = run_scenario(4, 4, 1, 1000, true).await;
    assert!(found, "three local queue timeouts suppressed a healthy remote after all capacity was released");
}
