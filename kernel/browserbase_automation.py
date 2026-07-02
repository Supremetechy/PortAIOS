"""
Browserbase Automation Module
Integrates Browserbase cloud browsers into PortAIOS as a default browser
option for automation tasks, voice-controlled navigation, and web scraping.

Config (env vars or ~/.portaios/browserbase.json):
    BROWSERBASE_API_KEY     — your Browserbase API key
    BROWSERBASE_PROJECT_ID  — your Browserbase project ID
"""

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AIOS.Browserbase")

CONFIG_PATH = Path.home() / ".portaios" / "browserbase.json"

try:
    import eel
    EEL_AVAILABLE = True
except ImportError:
    EEL_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# Config helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load_config() -> Dict[str, str]:
    cfg: Dict[str, str] = {}
    # 1. File-based config
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    # 2. Env vars take precedence
    if os.environ.get("BROWSERBASE_API_KEY"):
        cfg["api_key"] = os.environ["BROWSERBASE_API_KEY"]
    if os.environ.get("BROWSERBASE_PROJECT_ID"):
        cfg["project_id"] = os.environ["BROWSERBASE_PROJECT_ID"]
    return cfg


def _save_config(api_key: str, project_id: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({"api_key": api_key, "project_id": project_id}, indent=2))


# ──────────────────────────────────────────────────────────────────────────────
# Session manager
# ──────────────────────────────────────────────────────────────────────────────

class BrowserbaseManager:
    """Manages Browserbase remote browser sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._bb = None  # lazy-loaded Browserbase client

    def _get_client(self):
        """Lazy-load and return the Browserbase client."""
        if self._bb is not None:
            return self._bb
        try:
            from browserbase import Browserbase
        except ImportError as exc:
            raise RuntimeError(
                "browserbase package not installed. Run: pip install browserbase"
            ) from exc
        cfg = _load_config()
        api_key = cfg.get("api_key")
        if not api_key:
            raise RuntimeError(
                "BROWSERBASE_API_KEY not set. Configure via voice command "
                "'configure browserbase' or set the env var."
            )
        self._bb = Browserbase(api_key=api_key)
        return self._bb

    def create_session(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new remote Browserbase session.
        Returns: {session_id, live_view_url, connect_url, created_at}
        """
        bb = self._get_client()
        cfg = _load_config()
        pid = project_id or cfg.get("project_id")
        if not pid:
            raise RuntimeError(
                "BROWSERBASE_PROJECT_ID not set. Configure via 'configure browserbase'."
            )

        session = bb.sessions.create(project_id=pid)
        session_id = session.id
        connect_url = session.connect_url

        # Get the live debugger URL
        live_view_url = f"https://www.browserbase.com/sessions/{session_id}"
        try:
            debug_info = bb.sessions.debug(session_id)
            if hasattr(debug_info, "debugger_url") and debug_info.debugger_url:
                live_view_url = debug_info.debugger_url
        except Exception:
            pass  # fall back to the session URL

        record = {
            "session_id": session_id,
            "connect_url": connect_url,
            "live_view_url": live_view_url,
            "current_url": "",
            "created_at": datetime.now().isoformat(),
            "status": "active",
        }
        with self._lock:
            self._sessions[session_id] = record

        logger.info("Created Browserbase session %s", session_id)
        return record

    def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        """Navigate the session's browser to a URL using Playwright."""
        self._assert_session(session_id)
        record = self._sessions[session_id]

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright package not installed. Run: pip install playwright && playwright install chromium"
            ) from exc

        def _do_navigate():
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(record["connect_url"])
                ctx = browser.contexts[0] if browser.contexts else browser.new_context()
                page = ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                with self._lock:
                    self._sessions[session_id]["current_url"] = url
                browser.close()

        t = threading.Thread(target=_do_navigate, daemon=True)
        t.start()
        t.join(timeout=35)
        return {"success": True, "message": f"Navigated to {url}"}

    def run_task(self, session_id: str, task: str) -> Dict[str, Any]:
        """
        Run a high-level automation task described in plain English.
        Currently supports structured tasks; AI-driven routing can be added later.
        """
        self._assert_session(session_id)
        task_lower = task.lower()

        # Route simple patterns to concrete operations
        import re

        nav = re.search(r"(?:go to|navigate to|open|visit)\s+(.+)", task_lower)
        if nav:
            url = nav.group(1).strip()
            if not url.startswith("http"):
                url = "https://" + url
            return self.navigate(session_id, url)

        search = re.search(r"(?:search for|google)\s+(.+)", task_lower)
        if search:
            q = search.group(1).strip()
            return self.navigate(session_id, f"https://www.google.com/search?q={q.replace(' ', '+')}")

        return {"success": False, "message": f"Task not recognized: '{task}'"}

    def stop_session(self, session_id: str) -> Dict[str, Any]:
        """Terminate a Browserbase session."""
        self._assert_session(session_id)
        try:
            bb = self._get_client()
            bb.sessions.update(session_id, status="REQUEST_RELEASE")
        except Exception as exc:
            logger.warning("Could not cleanly close session %s: %s", session_id, exc)

        with self._lock:
            self._sessions.pop(session_id, None)
        logger.info("Stopped Browserbase session %s", session_id)
        return {"success": True, "message": "Session stopped"}

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._sessions.values())

    def _assert_session(self, session_id: str) -> None:
        if session_id not in self._sessions:
            raise RuntimeError(f"No active Browserbase session: {session_id}")


_manager = BrowserbaseManager()


# ──────────────────────────────────────────────────────────────────────────────
# Eel-exposed API
# ──────────────────────────────────────────────────────────────────────────────

def setup_browserbase(eel_instance=None):
    """Register eel endpoints. Call from onboarding_gui.py startup."""

    @eel.expose
    def browserbase_get_config() -> Dict[str, Any]:
        cfg = _load_config()
        return {
            "configured": bool(cfg.get("api_key") and cfg.get("project_id")),
            "project_id": cfg.get("project_id", ""),
            "has_api_key": bool(cfg.get("api_key")),
        }

    @eel.expose
    def browserbase_set_config(api_key: str, project_id: str) -> Dict[str, Any]:
        if not api_key or not project_id:
            return {"success": False, "message": "API key and Project ID are required"}
        _save_config(api_key.strip(), project_id.strip())
        _manager._bb = None  # reset client so it picks up new key
        return {"success": True, "message": "Browserbase configuration saved"}

    @eel.expose
    def browserbase_create_session() -> Dict[str, Any]:
        try:
            record = _manager.create_session()
            return {
                "success": True,
                "session": record,
                "speak": "Browserbase cloud browser session started",
            }
        except Exception as exc:
            logger.error("Create session error: %s", exc)
            return {"success": False, "message": str(exc), "speak": str(exc)}

    @eel.expose
    def browserbase_navigate(session_id: str, url: str) -> Dict[str, Any]:
        try:
            result = _manager.navigate(session_id, url)
            return {**result, "speak": f"Navigating cloud browser to {url}"}
        except Exception as exc:
            logger.error("Navigate error: %s", exc)
            return {"success": False, "message": str(exc)}

    @eel.expose
    def browserbase_run_task(session_id: str, task: str) -> Dict[str, Any]:
        try:
            result = _manager.run_task(session_id, task)
            return {**result, "speak": f"Running automation task: {task}"}
        except Exception as exc:
            logger.error("Task error: %s", exc)
            return {"success": False, "message": str(exc)}

    @eel.expose
    def browserbase_stop_session(session_id: str) -> Dict[str, Any]:
        try:
            result = _manager.stop_session(session_id)
            return {**result, "speak": "Cloud browser session closed"}
        except Exception as exc:
            logger.error("Stop session error: %s", exc)
            return {"success": False, "message": str(exc)}

    @eel.expose
    def browserbase_list_sessions() -> List[Dict[str, Any]]:
        return _manager.list_sessions()

    logger.info("Browserbase eel endpoints registered")
