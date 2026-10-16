#!/usr/bin/env python3
"""Replay actual baseline CLI: a recognized fetch line must reject either stream.

The local subject and cache CLI are explicit fixture adapters, not real cache or
network measurements. The production scenario CLI/build/FetchCount path runs
unchanged. The stdout cell is the detector's positive control.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ENGINE = Path(sys.argv[1]).resolve()
FIXTURE = Path(tempfile.mkdtemp(dir=ROOT / "investigation", prefix="fetch-replay-"))
repo = FIXTURE / "subject"
repo.mkdir()
(repo / "README").write_text("local subject; no compilations or downloads\n")
for command in (["git", "init", "-q", str(repo)], ["git", "-C", str(repo), "add", "README"],
                ["git", "-C", str(repo), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"]):
    subprocess.run(command, check=True)
revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
adapter = FIXTURE / "kache-adapter"
adapter.write_text("#!" + sys.executable + "\n" + """import json, sys
if sys.argv[1:] == ["--version"]:
    print("kache fixture-adapter 1.0")
elif sys.argv[1:2] == ["report"]:
    if "json" in sys.argv:
        print(json.dumps({"schema_version": 1, "summary": {"hit_rate_pct": 100.0,
          "total_crates": 1, "local_hits": 1, "prefetch_hits": 0,
          "remote_hits": 0, "dups": 0, "misses": 0}}))
    elif "perfetto" in sys.argv:
        print('{"traceEvents": []}')
    else:
        print("fixture report")
""")
adapter.chmod(0o755)
home = FIXTURE / "home"
home.mkdir()
env = {k: v for k, v in os.environ.items() if not k.startswith(("KACHE_", "RUSTC_", "CARGO_"))}
env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"), KACHE_HOST_CONFIG="",
           KACHE_RUNTIME_DIR=str(FIXTURE / "runtime"), RUSTC_WRAPPER="")
observations = []
for stream in ("stdout", "stderr"):
    scenarios = FIXTURE / (stream + "-scenarios")
    profile = scenarios / "bench-fetch-proof"
    profile.mkdir(parents=True)
    redirection = " >&2" if stream == "stderr" else ""
    command = "mkdir -p target; printf '  Downloaded anyhow v1.0.100\\n'" + redirection
    content = 'name = "bench-fetch-proof"\nbuild = ' + json.dumps(command) + '\n[source]\nkind = "clone"\nrepo = ' + json.dumps(str(repo)) + '\nref = ' + json.dumps(revision) + '\nobjdir = "target"\n'
    (profile / "scenario.toml").write_text(content)
    work = FIXTURE / (stream + "-work")
    run = subprocess.run([str(ENGINE), "--kache", str(adapter), "--scenarios", str(scenarios),
                          "--select", "name:fetch-proof", "--work-dir", str(work)],
                         cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    (FIXTURE / (stream + "-cli.stdout")).write_text(run.stdout)
    (FIXTURE / (stream + "-cli.stderr")).write_text(run.stderr)
    build_log = (work / "build-cold.log").read_text()
    result = work / "bench-fetch-proof.json"
    observations.append({"stream": stream, "exit": run.returncode,
        "download_in_build_log": "Downloaded anyhow" in build_log,
        "guardrail_error": "timed build fetched dependencies" in run.stderr,
        "result_written": result.exists(),
        "verdict": json.loads(result.read_text()).get("verdict") if result.exists() else None})
assert observations[0]["download_in_build_log"] and observations[0]["guardrail_error"] and observations[0]["exit"] != 0, "stdout positive control did not reach the detector"
assert observations[1]["download_in_build_log"], "stderr fixture line did not reach the actual timed build log"
(FIXTURE / "observations.json").write_text(json.dumps(observations, indent=2) + "\n")
print(json.dumps({"fixture": str(FIXTURE), "observations": observations}, indent=2), flush=True)
assert observations[1]["guardrail_error"] and observations[1]["exit"] != 0, "Timed Cargo fetch message on stderr was accepted; the same message on stdout was refused"
