#!/usr/bin/env python3
"""Observe production CLI upload headers with isolated Actions and service fixtures."""
import argparse, base64, http.server, json, os, pathlib, subprocess, tempfile, threading, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_BIN = "/Users/viktor/Developer/github/kache-investigations/coordinator/target/debug/kache"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", default=DEFAULT_BIN)
    parser.add_argument("--static-control", action="store_true")
    args = parser.parse_args()
    payload = base64.urlsafe_b64encode(json.dumps({"exp": int(time.time()) + 3600}).encode()).decode().rstrip("=")
    token = "eyJhbGciOiJSUzI1NiJ9." + payload + ".fixture-signature"
    calls = []
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def reply(self, status, value):
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            calls.append({"method": "GET", "path": self.path, "authorization": self.headers.get("Authorization")})
            if self.path.startswith("/token?"):
                self.reply(200, {"value": token})
            else:
                self.reply(404, {"error": "no discovery"})
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            auth = self.headers.get("Authorization")
            calls.append({"method": "POST", "path": self.path, "authorization": auth, "encoding": self.headers.get("Content-Encoding"), "body_bytes": len(body)})
            if auth != "Bearer " + token:
                self.reply(401, {"error": "build timelines need the service's credentials"})
            else:
                self.reply(200, {"stored": "inserted"})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory(prefix="timeline-auth-", dir=ROOT / "investigation") as scratch:
            directory = pathlib.Path(scratch)
            cache, home = directory / "cache", directory / "home"
            cache.mkdir(); home.mkdir()
            config = directory / "config.toml"
            config.write_text('[cache]\nlocal_store = "' + str(cache) + '"\nauto_gc = false\n')
            event = {"ts":"2026-10-11T01:00:00Z", "crate_name":"audit_fixture", "result":"miss", "elapsed_ms":10, "size":1, "cache_key":"audit-key", "schema":26, "session_id":"audit-session", "root":str(directory)}
            (cache / "events.jsonl").write_text(json.dumps(event) + "\n")
            env = {key:value for key,value in os.environ.items() if not key.startswith(("KACHE_", "KUNOBI_", "ACTIONS_", "CARGO_", "RUST_"))}
            env.update({"HOME":str(home), "XDG_CONFIG_HOME":str(home / "config"), "KACHE_CONFIG":str(config), "KACHE_STORE":str(cache), "KACHE_PLANNER_ENDPOINT":f"http://127.0.0.1:{server.server_port}", "ACTIONS_ID_TOKEN_REQUEST_URL":f"http://127.0.0.1:{server.server_port}/token?api-version=2.0", "ACTIONS_ID_TOKEN_REQUEST_TOKEN":"fixture-runtime", "RUSTC_WRAPPER":""})
            if args.static_control:
                env["KACHE_PLANNER_TOKEN"] = token
            run = subprocess.run([args.binary, "telemetry", "push", "--all"], cwd=directory, env=env, capture_output=True, text=True, timeout=20)
            evidence = {"control":args.static_control, "exit_code":run.returncode, "stdout":run.stdout, "stderr":run.stderr, "calls":calls}
            output = ROOT / "investigation" / ("timeline_auth_control.json" if args.static_control else "timeline_auth_red.json")
            output.write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(evidence, indent=2), flush=True)
            posts = [call for call in calls if call["method"] == "POST"]
            assert len(posts) == 1 and posts[0]["path"] == "/v1/build-timelines", "fixture must reach production timeline upload"
            assert posts[0]["body_bytes"] > 0 and posts[0]["encoding"] == "zstd", "fixture must upload the assembled compressed record"
            assert posts[0]["authorization"] == "Bearer " + token, "TIMELINE_WORKLOAD_AUTH_MISSING: available Actions credential was omitted from production timeline upload"
            assert "sent session audit-session" in run.stdout, "authenticated fixture upload must report stored session"
            print("CONTROL_PASS: authenticated upload reached fixture service")
    finally:
        server.shutdown(); server.server_close()

if __name__ == "__main__":
    main()
