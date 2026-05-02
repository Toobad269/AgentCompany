from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def terminate(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main() -> int:
    port = os.environ.get("WEB_PORT", "7842")
    runtime_proc = subprocess.Popen([sys.executable, "-u", "/app/docker_runtime.py"])
    web_proc = subprocess.Popen([sys.executable, "-u", "/app/webapp.py", port])

    stop = False

    def _handle_signal(signum, frame):  # type: ignore[no-untyped-def]
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        while not stop:
            runtime_code = runtime_proc.poll()
            web_code = web_proc.poll()
            if runtime_code is not None:
                terminate(web_proc)
                return runtime_code
            if web_code is not None:
                terminate(runtime_proc)
                return web_code
            time.sleep(0.5)
    finally:
        terminate(runtime_proc)
        terminate(web_proc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
