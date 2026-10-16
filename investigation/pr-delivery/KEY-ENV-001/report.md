STATUS: DONE
COMMIT: 0bf475d9f614217b973deddd842e023403e9ba06
CHANGED: src/cache_key.rs, src/cache_key/tests.rs, src/prediction_share.rs, tests/cache_key_underkeying_test.rs
OPEN: 0 implementation issues
BLOCKERS: none
---

An unset compile-time environment variable and a present empty value can produce different `option_env!` code. The parser previously recorded both as an empty string, allowing a cached unset artifact to satisfy a present-empty request.

The fix retains `None` and `Some("")` in dependency records, local predictions, portable predictions and shared plain rows. Prediction validation compares raw environment presence, and the key includes a presence field. New prediction schemas reject old ambiguous records; the added key field prevents restoration of artifacts keyed by the old encoding. Existing test fixtures follow the new recorded-value type. No skip annotations or production helper functions were added.

The test-only commit is f55e7983962f3aa6ca7fe4884b417f98aafeb410. The fix commit is 0bf475d9f614217b973deddd842e023403e9ba06. Both branch from 4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9, and the working tree is clean.

`option_env_presence_changes_cached_behavior` compares real compiled behavior with a direct-rustc oracle for absent, empty, nonempty and restored-absence values, with predictions enabled and disabled. Each unchanged repeat must report a local hit. Before repair, the present-empty wrapped artifact returned `unset`, while direct rustc returned `empty` (red.log, exit 101). Parser and prediction-validation tests independently failed on the absent/empty distinction (parser-red.log and prediction-red.log). Portable and shared-row serialization tests preserve all three states.

After repair, green.log records 410 cache-key tests passed (2 existing ignored subprocess helpers), 11 prediction-sharing tests passed, and all 12 cache-key integration tests passed. record-green.log records the parser and both serialization controls passing. The full final-tip `just check` exited 0 (gate.log), including workspace formatting, lint and test checks. All compiler and validation commands use the shared build-slot wrapper with this agent's private target directory. Validation ran on macOS; the regression preserves RUSTUP_HOME and uses portable HOME/USERPROFILE handling, but Windows execution was not performed locally. CI mutation testing and independent publication review remain with the coordinator.
