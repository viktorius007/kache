#!/usr/bin/env bash
# usage: stress.sh ID WORKERS ITERS THREADS test1 [test2 ...]
# Runs the unmodified kache unit-test binary directly (as cargo test does, cwd =
# package root) WORKERS-way parallel, ITERS times per worker, exact filters.
id="$1"; workers="$2"; iters="$3"; threads="$4"; shift 4
bin=${BIN:-/private/tmp/kache-flaky/assess-opus/bin/kache-unmodified}
cd /Users/viktor/Developer/github/kache-investigations/flaky-assess-opus || exit 1
export CARGO_MANIFEST_DIR=$PWD CARGO_PKG_NAME=kache
out=/private/tmp/kache-flaky/assess-opus/logs/$id
mkdir -p "$out"
echo "ID=$id START=$(date -u +%FT%TZ) LOAD=$(sysctl -n vm.loadavg) workers=$workers iters=$iters threads=$threads tests=$*" > "$out/summary.txt"
for w in $(seq 1 "$workers"); do
  (
    for i in $(seq 1 "$iters"); do
      "$bin" --exact "$@" --test-threads="$threads" > "$out/w$w-i$i.log" 2>&1
      rc=$?
      grep -h "^MEASURE" "$out/w$w-i$i.log" >> "$out/measure-w$w.txt" 2>/dev/null
      if [ $rc -eq 0 ]; then rm -f "$out/w$w-i$i.log"; else echo "w$w i$i rc=$rc load=$(sysctl -n vm.loadavg)" >> "$out/fails.txt"; fi
    done
  ) &
done
wait
echo "END=$(date -u +%FT%TZ) LOAD=$(sysctl -n vm.loadavg)" >> "$out/summary.txt"
cat "$out/summary.txt"; echo "fails:"; cat "$out/fails.txt" 2>/dev/null | wc -l
