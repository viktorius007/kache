Investigation artifacts for the delegated store-link source review.

`acl-probe.rs` is the only executed probe; its result is green and its replay case is in `evidence/acl-case.json`.

`sentinel-replay.py` and `behavior-probe.rs` were prepared but never executed. The coordinator directed this review to finish without executing or extending sentinel/path or readonly-state experiments. Their presence is provenance, not proof or a recommendation to run them. No finding is supported by those scripts.

No production repair was made. The earlier #1034 report remains in its original cache-poisoning-audit worktree.
