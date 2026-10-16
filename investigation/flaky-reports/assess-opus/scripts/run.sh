#!/usr/bin/env bash
# usage: run.sh ID cmd...   (runs from the worktree, logs to assess-opus/logs/ID.log)
id="$1"; shift
cd /Users/viktor/Developer/github/kache-investigations/flaky-assess-opus || exit 1
export CARGO_TARGET_DIR=/private/tmp/kache-flaky/opus/target
log=/private/tmp/kache-flaky/assess-opus/logs/$id.log
load="$(sysctl -n vm.loadavg)"
start="$(date -u +%FT%TZ)"
{ echo "ID=$id START=$start LOAD=$load"; echo "CMD=$*"; } > "$log"
"$@" >> "$log" 2>&1
rc=$?
end="$(date -u +%FT%TZ)"
echo "END=$end RC=$rc LOAD_END=$(sysctl -n vm.loadavg)" >> "$log"
echo "$id rc=$rc start=$start end=$end load_start=$load"
