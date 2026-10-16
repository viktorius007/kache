Concurrent same-key requests for different stores made [`handle_remote_check_started_at`](https://github.com/kunobi-ninja/kache/blob/4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9/src/daemon.rs#L4481-L4533) share a hit although only the leader store received the entry.

Scope singleflight to the validated destination so each requested store commits its entry.

`direct_restore_same_key_commits_to_each_requested_store` covers both leader orders; the same-store alias control and `just check` pass.
