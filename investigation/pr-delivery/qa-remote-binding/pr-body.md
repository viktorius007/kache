Exact restores accepted a valid pack for another cache key because [`download_entry_observed`](https://github.com/kunobi-ninja/kache/blob/4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9/src/remote_layout.rs#L216) omitted the entry binding.

Validate key and crate before publication while preserving packed-prefetch digest checks.

`exact_download_rejects_a_valid_pack_for_another_entry` covers matching and independently mismatched identities; digest controls and `just check` pass.
