"""Owner and idle watcher of the Agent Reach browser (`python -m agent_reach.runtime.browser_watcher`).

Started detached by runtime.browser. Holds ~/.agent-reach/browser/watcher.lock
so only one runs.

With --launch it owns a system Google Chrome pipe on POSIX or watches Windows Chrome.
The same 600-second idle timer handles the browser. Website extraction is done
by upstream tools. Snapshot writes are serialized with logout/removal.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess
import sys
import time
from typing import Optional

from . import bridge, browser


def _launch_with_pipe(chrome: str, url: str, *, headless: bool = True):
    """Start Chrome with the CDP pipe on its fds 3 (commands in) and 4 (replies out)."""
    if sys.platform == "win32":  # pragma: no cover
        raise NotImplementedError("pipe launch is not supported on Windows")
    import fcntl

    from .cdp import PipeConnection
    from .result import NEED_SETUP, ReachError

    if browser.platform.system() != "Darwin" and chrome != browser.chrome_binary():
        raise ReachError(NEED_SETUP, "Only installed system Google Chrome may be launched")
    verified_identity = browser.verify_chrome(chrome)
    to_chrome_r, to_chrome_w = os.pipe()
    from_chrome_r, from_chrome_w = os.pipe()
    # Child ends above 4 so placing them on 3/4 never overwrites one with the other.
    child_in = fcntl.fcntl(to_chrome_r, fcntl.F_DUPFD_CLOEXEC, 10)
    child_out = fcntl.fcntl(from_chrome_w, fcntl.F_DUPFD_CLOEXEC, 10)
    for fd in (to_chrome_r, from_chrome_w):
        os.close(fd)

    def place_pipe() -> None:  # in the child, after fork: dup2 leaves 3/4 inheritable
        os.dup2(child_in, 3)
        os.dup2(child_out, 4)

    try:
        if browser.verify_chrome(chrome) != verified_identity:
            raise ReachError(NEED_SETUP, "Google Chrome executable changed before launch; browser was not launched")
        proc = subprocess.Popen(
            browser.chrome_argv(chrome, url, pipe=True, headless=headless),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=False,  # Python fds are non-inheritable by default; only 3/4 get through
            preexec_fn=place_pipe,  # noqa: PLW1509 - single-threaded here
            start_new_session=True,
        )
    except BaseException:
        os.close(to_chrome_w)
        os.close(from_chrome_r)
        raise
    finally:
        os.close(child_in)
        os.close(child_out)
    return proc, PipeConnection(to_chrome_w, from_chrome_r)


def _load_extension(conn) -> None:
    if browser._load_state().get("extension_sha256") != browser.OPENCLI_EXTENSION_SHA256:
        from .result import NEED_SETUP, ReachError
        raise ReachError(NEED_SETUP, "OpenCLI extension has no matching verified hash; run agent-reach browser setup")
    ext = browser.extension_dir()
    if not (ext / "manifest.json").is_file():
        print("OpenCLI extension missing; browser opened without it", file=sys.stderr, flush=True)
        return
    reply = conn.call("Extensions.loadUnpacked", {"path": str(ext)}, timeout=60)
    if "result" in reply:
        browser.update_state(extension_id=reply["result"].get("id"))
        print(f"extension loaded: {reply['result'].get('id')}", file=sys.stderr, flush=True)
    else:
        print(f"Extensions.loadUnpacked failed: {reply.get('error')}", file=sys.stderr, flush=True)


def watch(idle: Optional[float] = None, poll: float = 2.0, *, launch: Optional[str] = None,
          chrome: Optional[str] = None, headless: bool = True) -> str:
    """Run until the browser is gone. Returns why it stopped."""
    idle = browser.IDLE_LIMIT if idle is None else idle
    fd = browser._open_lock(browser.watcher_lock_path())
    proc = conn = bridge_proc = None
    try:
        # A probe (watcher_running) holds the lock for an instant; a live watcher holds it for good.
        # A watcher of a browser that just closed may still be on its way out: give it a moment.
        if not browser.wait_for(lambda: browser.try_lock(fd), 10.0 if launch else 2.0, interval=0.1):
            return "another watcher is running"
        bridge_proc = bridge.start()
        if launch is not None:
            if browser.is_running():
                return "a browser is already using the debugging port"
            browser.refresh_extension()
            proc, conn = _launch_with_pipe(chrome or browser.ensure_chrome(), "about:blank", headless=headless)
            _load_extension(conn)
            browser.update_state(running_backend="chrome", headless=headless)
            browser.restore_session()
            if launch != "about:blank":
                browser.open_url(launch)
        browser.update_state(bridge_pid=bridge_proc.pid if bridge_proc else None, bridge_note=None)
        began = time.time()

        def gone() -> bool:
            if conn is not None:
                return conn.closed.is_set() or (proc is not None and proc.poll() is not None)
            return not browser.is_running()

        while True:
            if gone():
                return "browser closed"
            if bridge_proc is not None and bridge_proc.poll() is not None:
                return "owned Bridge exited; browser closed with it"
            browser.observe_activity()
            browser.save_session()
            used = max(began, browser.last_used() or 0.0)
            left = used + idle - time.time()
            if left <= 0:
                with contextlib.suppress(Exception), browser.start_lock(wait=5.0):
                    used = max(began, browser.last_used() or 0.0)
                    if used + idle <= time.time() and browser.stop():
                        return "closed after idle"
                left = poll  # used again meanwhile, or close failed: check later
            pause = min(poll, left + 0.5)
            if conn is not None:
                conn.closed.wait(pause)  # wake the moment Chrome exits
            else:
                time.sleep(pause)
    finally:
        if conn is not None:
            conn.close()  # Chrome exits when its pipe closes
        if proc is not None:
            try:
                proc.wait(15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(5)
        bridge.close(bridge_proc)
        browser.update_state(bridge_note=None, bridge_pid=None)
        os.close(fd)


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent_reach.runtime.browser_watcher")
    parser.add_argument("--idle", type=float, default=None, help="seconds without use before closing")
    parser.add_argument("--launch", default=None, help="start Chrome with this URL and own it (macOS/Linux)")
    parser.add_argument("--chrome", default=None, help="Chrome binary for --launch")
    parser.add_argument("--headed", action="store_true", help="show a window for human login")
    ns = parser.parse_args()
    reason = watch(ns.idle, launch=ns.launch, chrome=ns.chrome, headless=not ns.headed)
    print(reason, file=sys.stderr, flush=True)
    sys.exit(0 if reason in ("browser closed", "closed after idle") else 1)


if __name__ == "__main__":
    main()
