"""
Mock Eel Module for PortAIOS Daemon Mode
Intercepts @eel.expose and maps JS callback invocations over a custom WebSocket connection.
Uses Python 3.7+ module-level __getattr__ for dynamic JS function call routing.
"""

import sys
import json
import uuid
import logging
import asyncio
import threading
from typing import Dict, Any, Callable, Optional, Tuple

logger = logging.getLogger("AIOS.MockEel")

# Global registries
EXPOSED_METHODS: Dict[str, Callable] = {}
PENDING_CALLBACKS: Dict[str, Tuple[threading.Event, Dict[str, Any]]] = {}
PENDING_CALLBACKS_LOCK = threading.Lock()
ACTIVE_CLIENTS = set()
WS_LOOP = None

def init(web_folder: str):
    logger.info(f"MockEel initialized with folder: {web_folder}")

def expose(func: Callable, name: Optional[str] = None) -> Callable:
    func_name = name or func.__name__
    EXPOSED_METHODS[func_name] = func
    logger.debug(f"Exposed Python function: {func_name}")
    return func

def start(*args, **kwargs):
    logger.info("MockEel start called (running in daemon mode, ignoring window spawn)")

def broadcast_message(msg_dict: Dict[str, Any]):
    """Send JSON message to all active WebSocket clients"""
    if not WS_LOOP:
        return
    msg_str = json.dumps(msg_dict)
    for client in list(ACTIVE_CLIENTS):
        try:
            asyncio.run_coroutine_threadsafe(client.send(msg_str), WS_LOOP)
        except Exception as e:
            logger.warning(f"Failed to send websocket message to client: {e}")

class JSFunctionCaller:
    """Wrapper that mimics eel.js_function_name(args)() dynamic calls"""
    def __init__(self, name: str):
        self.name = name

    def __call__(self, *args, **kwargs):
        def run_call():
            call_id = str(uuid.uuid4())
            msg = {
                "type": "callback",
                "id": call_id,
                "name": self.name,
                "args": list(args)
            }
            
            event = threading.Event()
            res_box = {"result": None, "error": None}
            
            with PENDING_CALLBACKS_LOCK:
                PENDING_CALLBACKS[call_id] = (event, res_box)
            
            logger.debug(f"Sending JS callback request '{self.name}' (ID: {call_id})")
            broadcast_message(msg)
            
            # Wait up to 5.0 seconds for client to execute JS callback and reply
            success = event.wait(timeout=5.0)
            
            with PENDING_CALLBACKS_LOCK:
                PENDING_CALLBACKS.pop(call_id, None)
            
            if not success:
                logger.warning(f"JS callback '{self.name}' timed out (ID: {call_id})")
                return None
                
            if res_box["error"]:
                logger.error(f"JS callback '{self.name}' returned error: {res_box['error']}")
                return None
                
            return res_box["result"]
        return run_call

def __getattr__(name: str) -> Any:
    """Module-level __getattr__ (Python 3.7+) to catch dynamic JS callback calls"""
    # Check if the name matches a function in this module
    if name in globals():
        return globals()[name]
    # Otherwise, treat it as a dynamic call to a frontend JS function
    return JSFunctionCaller(name)
