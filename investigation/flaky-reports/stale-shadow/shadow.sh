#!/bin/bash
# usage: run.sh <discovery>
set -e
K=/private/tmp/kache-fix/cc-optional-header/target/debug/kache
R=$(mktemp -d)/r; mkdir -p $R/home $R/first $R/second; cd $R; : > kache.toml
printf '#include "header.h"\nint main(void){return VALUE;}\n' > unit.c; echo '#define VALUE 11' > second/header.h
run() {
  rm -f unit.o
  env -u OUT_DIR -u KACHE_ACTIVE -u KACHE_SOCKET_PATH KACHE_CACHE_DIR=$R/cache KACHE_RUNTIME_DIR=$R/cache KACHE_CONFIG=$R/kache.toml KACHE_HOST_CONFIG= KACHE_BASE_DIR=$R KACHE_LOCAL_ONLY=1 KACHE_DEFERRED_DISCOVERY=$1 KACHE_DAEMON_PUBLISH=0 KACHE_MIN_STORE_COMPILE_MS=0 HOME=$R/home \
    $K /usr/bin/cc -c unit.c -o unit.o -Ifirst -Isecond
  /usr/bin/cc unit.o -o v; set +e; ./v; echo "$2: value=$? $(tail -1 cache/events.jsonl | python3 -c 'import json,sys;e=json.load(sys.stdin);print(e["result"],e["cache_key"][:12])')"; set -e
}
sleep 2.2
run $1 cold; run $1 warm
echo '#define VALUE 23' > first/header.h; sleep 2.2
run $1 created; run $1 created-warm
echo '#define VALUE 42' > first/header.h; sleep 2.2
run $1 edited
rm first/header.h; sleep 2.2
run $1 removed
