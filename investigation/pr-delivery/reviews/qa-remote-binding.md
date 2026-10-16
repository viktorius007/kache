PASS
Verified SHA: b06aba292b0cabb5d47fa0ad6a7c0a77b31206a1; clean worktree and git diff --check.
Evidence directory: /Users/viktor/Developer/github/kache-investigations/qa-remote-validation/investigation/pr-delivery/qa-remote-binding.
Commit split: test-only 8abea96f17c48f425d733da01d51803b3c817fa8, then production-only b06aba292b0cabb5d47fa0ad6a7c0a77b31206a1; only src/remote_layout.rs changes.
Old red: red.log:35-43 fails at “a valid pack for another entry must be rejected”; 0 passed, 1 failed on unrepaired production.
New green: green.log:22-34 has exact identity regression and prefetch controls green; 27 passed, 0 failed; gate.log:5712 has 4382 passed, 0 failed, 14 ignored.
Gate: delivery.json binds build-slot.py just check to this SHA with gate_exit=0; gate.log completes workspace fmt, Clippy and tests; reused evidence, no repeated gate.
Identity: download_entry_observed src/remote_layout.rs:216 supplies requested key/crate; extract_entry_pack_until:737 rejects either mismatch before destination replacement/publication at :793.
Digest/cache compatibility: extract_verified_prefetch_entry:445 retains Some(meta_digest); :1308 checks valid wrong digest and :1323 matching digest/bytes; schema/wire format unchanged, existing matching and CC restores green.
Oracle/portability: :1639 independently varies matching, key-only and crate-only requests; exact diagnostic and absent destination at :1670 guard rejection. Genuine Store packs, temporary stores, transport-only double, no host/global state or platform-specific additions.
Shape/PR: existing binding/validator reused (bounded coordinator graph search returns 2 symbols, baseline 4ee0f9e; delivered source verified); no new production function/trait/variant or duplicate policy; 40-word PR body links the defective baseline call; no generated artifacts.
Findings: none blocking. CI mutation testing remains required by AGENTS.md before landing; not run locally.
