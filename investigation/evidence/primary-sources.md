Current issue and maintainer measurement request (API snapshots saved alongside this file):
https://github.com/kunobi-ninja/kache/issues/327
https://github.com/kunobi-ninja/kache/issues/327#issuecomment-5633434057

Tokio semaphore documentation, read on 2026-10-11:
https://docs.rs/tokio/latest/tokio/sync/struct.Semaphore.html
The documented permit policy is FIFO, including acquire_many. A waiter requesting multiple permits at the front can block a later single-permit waiter even while some permits remain. This makes weighted permits alone insufficient to establish priority or small-operation latency guarantees.

Scope of application: Kache's current request pool uses single permits. No modified weighted-permit design was benchmarked or proven by this investigation.

The current documentation resolves to 1.53.2; the baseline lockfile pins 1.53.1. The version-specific 1.53.1 docs URL was unavailable to the web reader. Current-documentation fairness is design context, not an experimental result for a modified implementation.
