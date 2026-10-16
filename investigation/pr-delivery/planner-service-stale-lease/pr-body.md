An inherited marker from an exited test owner made [`lease_covers`](https://github.com/kunobi-ninja/kache/blob/4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9/src/scheduler.rs#L685-L695) bypass admission because it checked only the scheduler directory.

Require the marker’s live OS lock so released leases restore admission and active leases preserve nested reuse.

`exited_test_lease_owner_restores_admission` covers real owner exit, compile permits and runner scheduling; live-lease controls and `just check` pass.
