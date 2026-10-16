A locally shadowed `include!` could restore another checkout's runtime `OUT_DIR` because [`source_env_dep_use`](https://github.com/kunobi-ninja/kache/blob/4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9/src/cache_key.rs#L5749-L5821) assumed builtin semantics from macro names.

Keep ambiguous include-family uses absolute and invalidate old scanner memos.

`shadowed_include_macro_keeps_checkout_environment_value` compares runtime paths with direct rustc, verifies unchanged hits, and checks both prediction modes; `just check` passes.
