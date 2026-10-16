# Scheduling-latency probe: sleeps 1 ms in a loop and records how late each
# wakeup is. Runs at default priority beside the test suite; prints a summary
# on SIGTERM/SIGINT or after the given duration.
import sys, time, signal, json
dur = float(sys.argv[1]) if len(sys.argv) > 1 else 600
out = sys.argv[2] if len(sys.argv) > 2 else None
bounds = [10, 50, 100, 200, 250, 500, 950]
counts = {b: 0 for b in bounds}
worst = []
n = 0
stop = False
def h(*_):
    global stop; stop = True
signal.signal(signal.SIGTERM, h); signal.signal(signal.SIGINT, h)
t_end = time.monotonic() + dur
while not stop and time.monotonic() < t_end:
    t0 = time.monotonic()
    time.sleep(0.001)
    late = (time.monotonic() - t0) * 1000 - 1.0
    n += 1
    for b in bounds:
        if late >= b: counts[b] += 1
    if late >= 50:
        worst.append((round(late, 1), time.strftime('%H:%M:%S')))
worst.sort(reverse=True)
res = {"samples": n, "late_ge_ms": counts, "worst": worst[:20]}
s = json.dumps(res)
print(s)
if out:
    open(out, 'w').write(s + "\n")
