"""
AIOS Terminal Manager

Manages persistent PTY (pseudo-terminal) sessions backed by a real shell.
Sessions survive panel open/close and page reloads; the internal agent can
create, write to, and read from named sessions for long-running tasks.

Architecture:
  - Each session owns an OS-level PTY pair (master fd / slave fd).
  - The shell process (zsh/bash) runs on the slave end.
  - A single background thread polls all master FDs with select() and
    pushes output chunks to the JS frontend via eel.terminal_output().
"""

import base64
import fcntl
import logging
import os
import select
import shutil
import struct
import subprocess
import termios
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("AIOS.terminal")

_SCROLLBACK_LIMIT = 65536   # 64 KB per session
_READ_CHUNK       = 4096
_DEFAULT_COLS     = 220
_DEFAULT_ROWS     = 50


@dataclass
class TerminalSession:
    session_id: str
    name: str
    master_fd: int
    proc: "subprocess.Popen[bytes]"
    cols: int = _DEFAULT_COLS
    rows: int = _DEFAULT_ROWS
    alive: bool = True
    created_at: float = field(default_factory=time.time)
    scrollback: bytearray = field(default_factory=bytearray)

    def write(self, data: bytes) -> None:
        if not self.alive:
            return
        try:
            os.write(self.master_fd, data)
        except OSError:
            self.alive = False

    def resize(self, cols: int, rows: int) -> None:
        self.cols, self.rows = cols, rows
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except OSError:
            pass

    def kill(self) -> None:
        self.alive = False
        try:
            self.proc.terminate()
        except OSError:
            pass
        try:
            os.close(self.master_fd)
        except OSError:
            pass

    def append_scrollback(self, data: bytes) -> None:
        self.scrollback.extend(data)
        excess = len(self.scrollback) - _SCROLLBACK_LIMIT
        if excess > 0:
            del self.scrollback[:excess]


class TerminalManager:
    """Singleton managing all PTY sessions for AIOS."""

    _instance: Optional["TerminalManager"] = None

    @classmethod
    def get(cls) -> "TerminalManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._sessions: Dict[str, TerminalSession] = {}
        self._lock = threading.Lock()
        self._next_id = 0
        self._output_cb: Optional[Callable] = None   # eel.terminal_output
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def set_output_callback(self, cb: Callable) -> None:
        """Register the Eel push-to-JS callback for streaming terminal output."""
        self._output_cb = cb

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._reader_loop, name="AIOSTerminalReader", daemon=True
        )
        self._thread.start()
        logger.info("TerminalManager started")

    def stop(self) -> None:
        self._running = False
        with self._lock:
            for s in list(self._sessions.values()):
                s.kill()
            self._sessions.clear()
        logger.info("TerminalManager stopped")

    # ------------------------------------------------------------------
    # Session API
    # ------------------------------------------------------------------

    def create_session(self, name: str, shell: Optional[str] = None) -> str:
        """Spawn a shell in a new PTY and return the session_id."""
        shell = (
            shell
            or shutil.which("zsh")
            or shutil.which("bash")
            or "/bin/sh"
        )
        master_fd, slave_fd = os.openpty()

        # Set initial window size on slave before the shell reads it
        winsize = struct.pack("HHHH", _DEFAULT_ROWS, _DEFAULT_COLS, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

        env = dict(os.environ)
        env.update({
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "LANG": env.get("LANG", "en_US.UTF-8"),
        })

        proc = subprocess.Popen(
            [shell],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            preexec_fn=os.setsid,
            close_fds=True,
            env=env,
        )
        os.close(slave_fd)

        with self._lock:
            self._next_id += 1
            session_id = f"term_{self._next_id}"
            self._sessions[session_id] = TerminalSession(
                session_id=session_id,
                name=name,
                master_fd=master_fd,
                proc=proc,
            )

        logger.info(f"Created terminal session {session_id!r} name={name!r} shell={shell}")
        return session_id

    def send_input(self, session_id: str, data: str) -> bool:
        """Write raw input (key presses, paste) to the PTY."""
        session = self._get(session_id)
        if session and session.alive:
            session.write(data.encode("utf-8", errors="replace"))
            return True
        return False

    def send_command(self, session_id: str, command: str) -> bool:
        """Write a shell command followed by a newline."""
        return self.send_input(session_id, command + "\n")

    def resize(self, session_id: str, cols: int, rows: int) -> bool:
        session = self._get(session_id)
        if session:
            session.resize(max(1, cols), max(1, rows))
            return True
        return False

    def kill_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            session.kill()
            logger.info(f"Killed terminal session {session_id!r}")
            return True
        return False

    def list_sessions(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "id": s.session_id,
                    "name": s.name,
                    "alive": s.alive and s.proc.poll() is None,
                    "cols": s.cols,
                    "rows": s.rows,
                    "created_at": s.created_at,
                }
                for s in self._sessions.values()
            ]

    def get_scrollback_b64(self, session_id: str) -> str:
        """Return base64-encoded scrollback so the JS can replay on reconnect."""
        session = self._get(session_id)
        if session:
            return base64.b64encode(bytes(session.scrollback)).decode("ascii")
        return ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, session_id: str) -> Optional[TerminalSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def _reader_loop(self) -> None:
        """Continuously read from all PTY master FDs and push to JS."""
        while self._running:
            with self._lock:
                sessions = list(self._sessions.values())

            alive = [s for s in sessions if s.alive]
            if not alive:
                time.sleep(0.05)
                continue

            fds = [s.master_fd for s in alive]
            try:
                readable, _, _ = select.select(fds, [], [], 0.05)
            except (ValueError, OSError):
                time.sleep(0.05)
                continue

            fd_to_session = {s.master_fd: s for s in alive}

            for fd in readable:
                s = fd_to_session.get(fd)
                if s is None:
                    continue
                try:
                    data = os.read(fd, _READ_CHUNK)
                    if data:
                        s.append_scrollback(data)
                        self._push_output(s.session_id, data)
                except OSError:
                    s.alive = False
                    self._push_exit(s.session_id)
                    continue

            # Detect processes that exited without an OSError on the fd
            for s in alive:
                if s.master_fd not in readable and s.proc.poll() is not None:
                    s.alive = False
                    self._push_exit(s.session_id)

    def _push_output(self, session_id: str, data: bytes) -> None:
        if not self._output_cb:
            return
        try:
            b64 = base64.b64encode(data).decode("ascii")
            self._output_cb(session_id, b64)
        except Exception as exc:
            logger.debug(f"terminal_output push failed: {exc}")

    def _push_exit(self, session_id: str) -> None:
        if not self._output_cb:
            return
        try:
            self._output_cb(session_id, None)
        except Exception:
            pass


# Module-level convenience accessor
def get_terminal_manager() -> TerminalManager:
    return TerminalManager.get()


def setup_terminal_manager(eel_module) -> TerminalManager:
    """
    Initialise the TerminalManager and wire it to Eel.

    Call once from start_eel_app() after eel.start() is called so the
    WebSocket connection is up before the reader thread tries to push data.
    """
    mgr = TerminalManager.get()
    # Check if terminal_output is exposed before setting callback
    if hasattr(eel_module, 'terminal_output'):
        mgr.set_output_callback(eel_module.terminal_output)
    else:
        logger.warning("terminal_output not exposed in Eel, terminal output will not be pushed to frontend")
    mgr.start()
    return mgr
