# Patched kache

`local/sync-patched` builds the kache this machine runs: upstream `main` plus every
open PR by the author plus the branches in `local/extra-branches`, checked with the
same recipes as `just check`, then installed to `~/.cargo/bin` with the daemon
restarted. The merged result is the `patched` branch in `../kache-patched`.

`local/` is kept out of commits by `.git/info/exclude`. Its source of truth is the
fork's `tools/sync-patched` branch.

## A new machine

```sh
gh auth login
gh repo clone viktorius007/kache && cd kache
git config user.name "…" && git config user.email "…"   # merge commits need one
mkdir -p local && for f in sync-patched extra-branches skip-prs README.md; do
  git show origin/tools/sync-patched:local/$f > local/$f; done && chmod +x local/sync-patched
local/sync-patched
```

It needs `git`, `gh`, `cargo` (rustup reads the pin in `rust-toolchain.toml`) and
`just` on `PATH`. The first run adds the `upstream` remote, turns on rerere, creates
the worktree and, if the fork has a `patched` branch, learns every conflict
resolution in it.

## Every sync

```sh
local/sync-patched            # fetch, merge, check, install; prints a timing table
local/sync-patched --push     # also push the build to the fork for other machines
```

Timings are appended to `~/.local/state/kache-patched/timings.log`; the last install
is described in `installed.txt` beside it.

## When a PR conflicts

A conflict nobody has resolved is skipped, and the build goes on without that PR.
To resolve it:

```sh
local/sync-patched --resolve --no-check --no-install
# fix the files it lists in ../kache-patched, then
git -C ../kache-patched add -A && git -C ../kache-patched commit --no-edit
local/sync-patched --resolve  # repeat until nothing stops
```

`--resolve` stops in the same merge order and with the same merge settings as a
normal run, so rerere replays the resolution on every later sync. Resolving by hand
with a plain `git merge`, or on top of a different set of PRs, records a resolution
no later run matches.

## When upstream replaces a PR

The maintainer usually lands a reworked copy of a PR and closes the original a day
or two later. Until then the original is still open and conflicts with its own
replacement. Put its number in `local/skip-prs` (with a `#` note) rather than
resolving that conflict; remove the line once the PR is closed.

To build a PR from a local branch before it is pushed (a fresh rebase, say), add
`<number> <branch>` to `local/pr-overrides`. Delete the line after pushing: the PR
then carries the same commits.

If `gh` is logged out, the PR list comes from GitHub's public API; everything but
`--push` still works.

## Other options

- `--clean` deletes untracked files in the worktree. A failed test run can leave
  some (`proptest-regressions/`), and the script refuses to start over them.
- `--no-check`, `--no-install` skip those phases.
- `KACHE_PATCHED_WORKTREE`, `KACHE_UPSTREAM`, `KACHE_AUTHOR` override the defaults.

If `TMPDIR` is on a different filesystem from the worktree, the tests get
`<mount>/tmp/kache-patched-check` instead: some tests hard-link the built binary into
a temp dir, and others need one outside any checkout.
