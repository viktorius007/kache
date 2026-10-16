[push_timeline](https://github.com/kunobi-ninja/kache/blob/4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9/src/timeline_client.rs#L50-L69) read only the explicit token, omitting automatic planner credentials from timeline uploads.
Reuse the workload/session resolver with one deadline shared by authentication and upload, preserving explicit-token precedence and advisory missing-auth behavior.
CLI auth controls and delayed/exhausted-auth regressions pass; `just check` passes.
