# Maintaining the installed fork

The `patched` branch contains upstream plus the retained local fixes. Keep one
checkout on that branch. `local/installed.json` identifies the verified source
commit and hashes of the installed binary pair; later documentation and tooling
commits need not change the running binary.

## Next upstream sync

From a clean `patched` checkout:

```sh
local/sync-patched --push
```

The script fast-forwards from `origin/patched`, merges `upstream/main` into the
existing history, runs `just check`, builds and installs both binaries, restarts
the daemon, and verifies `doctor --probe`. It commits the installation receipt
and pushes `patched` without force. Temporary build products and rollback copies
are removed on success or failure. On Linux, leftover executables running from
that build tree are stopped before deletion, so detached test daemons cannot
recreate their fixture directories. A failed installation restores the previous
binary pair and Cargo installation metadata.

This preserves fixes from closed PRs and unsubmitted branches. It does not rebuild
from a list of open PRs, silently skip conflicts, create extra worktrees, or stash
changes. Resolve a stopped merge, commit it, then run:

```sh
local/sync-patched --no-sync --push
```

Useful options are `--no-install` for validation only, and
`--no-check --no-install` for merging source only. `--no-sync` validates or rebuilds
the current commit. `KACHE_SYNC_BUILD_ROOT` selects an existing directory for the
temporary build tree; otherwise the system temporary directory is used.

Requirements: Python 3.11+, Git, rustup with the repository's pinned toolchain,
`just`, and the native compiler/build dependencies. The remotes are `origin`
(the fork, with a `patched` branch) and `upstream` (kunobi-ninja/kache).

For a new machine:

```sh
git clone --branch patched https://github.com/viktorius007/kache
cd kache
git remote add upstream https://github.com/kunobi-ninja/kache
local/sync-patched --push
```

`python3 local/test-sync-patched` exercises the merge and push workflow against
isolated local repositories without compiling Rust or touching the installation.
