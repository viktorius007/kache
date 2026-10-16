`option_env!` could restore an unset-variable artifact when the variable was set to an empty string because [`parse_env_dep_info`](https://github.com/kunobi-ninja/kache/blob/4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9/src/cache_key.rs#L8607-L8621) discarded presence.

Preserve presence in cache keys and prediction records, and invalidate ambiguous records.

`option_env_presence_changes_cached_behavior` checks direct-rustc behavior with predictions on and off; `just check` passes.
