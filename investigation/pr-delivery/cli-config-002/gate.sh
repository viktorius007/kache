#!/bin/bash
set -eu
env -u KACHE_RUNTIME_DIR -u KACHE_HOST_CONFIG -u KACHE_CONFIG -u KACHE_CACHE_DIR \
  CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/cargo-build-001/target \
  python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check
