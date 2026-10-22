#!/usr/bin/env bash
# rerun.sh TREE LABEL TARGET_DIR BIN...   -- reference recipe: RUSTUP_TOOLCHAIN=1.99.1, empty CARGO_HOME, shim dir off PATH
set -u
tree=$1 label=$2 target=$3; shift 3
out=/scratch/agent/merge-cmp/$label; mkdir -p "$out"
export RUSTUP_TOOLCHAIN=1.99.1 CARGO_HOME=/scratch/agent/merge-cmp/cargo-home-empty RUSTC_WRAPPER= CARGO_TARGET_DIR=$target
export PATH=$(printf '%s' "$PATH" | tr ':' '\n' | grep -v '/.local/lib/kache/shims' | paste -sd:)
cd "$tree"
for bin in "$@"; do
  if [ "$bin" = lib ]; then sel=(--lib); else sel=(--test "$bin"); fi
  timeout 1500 ./scripts/with-test-resources.sh cargo test -p kache "${sel[@]}" --no-fail-fast > "$out/$bin.log" 2>&1
  code=$?
  res=$(grep -E '^test result' "$out/$bin.log" | tail -1 | sed -E 's/test result: (\w+)\. ([0-9]+) passed; ([0-9]+) failed.*/\1 \2 passed, \3 failed/')
  grep -E '^test .* FAILED$' "$out/$bin.log" | sed -E 's/^test (.*) \.\.\. FAILED$/\1/' | sort > "$out/$bin.failed"
  echo "$bin exit=$code ${res:-no-result}"
done
