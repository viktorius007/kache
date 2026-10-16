#!/usr/bin/env python3
"""Baseline proof: failed measuring instrument must stop its child group."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from bench.engine import run_measurement

def timeout_control():
    with tempfile.TemporaryDirectory(dir=ROOT/'investigation',prefix='timeout-control-') as tmp:
        home=Path(tmp)
        marker=home/'post-timeout-write'
        pidfile=home/'child-pid'
        child="import pathlib,time; time.sleep(0.35); pathlib.Path(%r).write_text('survived'); time.sleep(15)" % str(marker)
        parent="import pathlib,subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c',%r],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); pathlib.Path(%r).write_text(str(p.pid)); time.sleep(60)" % (child,str(pidfile))
        pid=None
        try:
            try:
                run_measurement([sys.executable,'-c',parent],timeout=0.15)
            except subprocess.TimeoutExpired:
                pass
            else:
                raise AssertionError('timeout positive control did not time out')
            pid=int(pidfile.read_text())
            time.sleep(0.5)
            assert not marker.exists(), 'timeout control left child running'
            print(json.dumps({'timeout_control': 'pass', 'post_timeout_artifact': marker.exists()}),flush=True)
        finally:
            if pid is None and pidfile.exists(): pid=int(pidfile.read_text())
            if pid is not None:
                try: os.kill(pid,signal.SIGKILL)
                except ProcessLookupError: pass

timeout_control()

with tempfile.TemporaryDirectory(dir=ROOT/'investigation',prefix='orphan-fixture-') as tmp:
    home=Path(tmp)
    marker=home/'post-failure-write'
    pidfile=home/'child-pid'
    child="import pathlib,time; time.sleep(0.35); pathlib.Path(%r).write_text('child ran after failure'); time.sleep(15)" % str(marker)
    parent="import pathlib,subprocess,sys; p=subprocess.Popen([sys.executable,'-c',%r],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); pathlib.Path(%r).write_text(str(p.pid)); raise SystemExit(4)" % (child,str(pidfile))
    pid=None
    try:
        try:
            run_measurement([sys.executable,'-c',parent],timeout=3)
        except subprocess.CalledProcessError as error:
            assert error.returncode==4
        else:
            raise AssertionError('fixture did not drive nonzero measurement exit')
        pid=int(pidfile.read_text())
        # A deterministic filesystem consequence, not a load-sensitive benchmark.
        deadline=time.monotonic()+2
        while not marker.exists() and time.monotonic()<deadline:
            time.sleep(0.02)
        actual={'measurement_status':4,'post_failure_artifact':marker.exists(),'child_pid':pid}
        print(json.dumps(actual),flush=True)
        assert not marker.exists(), 'Failed measurement returned while its child survived and wrote an artifact after failure; a subsequent gate run can share its CPU/memory/I/O load'
    finally:
        if pid is None and pidfile.exists(): pid=int(pidfile.read_text())
        if pid is not None:
            try: os.kill(pid,signal.SIGKILL)
            except ProcessLookupError: pass
