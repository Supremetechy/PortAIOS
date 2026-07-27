import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Prevent OpenMP runtime crash on macOS
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import asyncio
import logging
import argparse
import threading
import websockets
import bottle
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# 1. Pre-load mock_eel to override the 'eel' package globally
import kernel.mock_eel as mock_eel
sys.modules['eel'] = mock_eel

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("AIOS.Daemon")

# 2. Load onboarding_gui to initialize all systems and register exposed methods
from kernel.onboarding_gui import start_eel_app

ROOT_DIR = Path(__file__).resolve().parent.parent
WEB_FOLDER = ROOT_DIR / "web"
MODELS_FOLDER = ROOT_DIR / "models"
ASSETS_FOLDER = ROOT_DIR / "assets"

# Establish static serving Bottle app
app = bottle.Bottle()

# Register MIME types for browser compatibility (ESM, GLB, glTF)
import mimetypes
mimetypes.add_type("application/javascript", ".jsx")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/gltf+json", ".gltf")

_JS_MODULE_EXTS = (".jsx", ".mjs", ".js")

@app.route("/assets/<filename:path>")
def serve_static_assets(filename):
    if filename.lower().endswith(_JS_MODULE_EXTS):
        return bottle.static_file(
            filename,
            root=str(ASSETS_FOLDER),
            mimetype="application/javascript",
        )
    return bottle.static_file(filename, root=str(ASSETS_FOLDER))

@app.route("/eel.js")
@app.route("/<path:path>/eel.js")
def serve_eel_js(path=None):
    return bottle.static_file("portaios-bridge-client.js", root=str(WEB_FOLDER), mimetype="application/javascript")

@app.route("/models/<filename:path>")
def serve_models(filename):
    lower = filename.lower()
    if lower.endswith(".glb"):
        return bottle.static_file(
            filename,
            root=str(MODELS_FOLDER),
            mimetype="model/gltf-binary",
        )
    if lower.endswith(".gltf"):
        return bottle.static_file(
            filename,
            root=str(MODELS_FOLDER),
            mimetype="model/gltf+json",
        )
    return bottle.static_file(filename, root=str(MODELS_FOLDER))

@app.route("/")
@app.route("/<filename:path>")
def serve_web(filename="index.html"):
    if not filename or filename.endswith("/"):
        filename += "index.html"
    return bottle.static_file(filename, root=str(WEB_FOLDER))


async def ws_handler(websocket, expected_token: str):
    """Handles incoming WebSocket RPC connection and authentication"""
    # Authenticate via token in query params
    path = websocket.request.path
    query = urlparse(path).query
    params = parse_qs(query)
    token = params.get("token", [None])[0]
    
    if token != expected_token:
        logger.warning(f"WebSocket authentication failed: invalid token from {websocket.remote_address}")
        await websocket.close(1008, "Unauthorized")
        return
        
    logger.info(f"WebSocket client authenticated successfully: {websocket.remote_address}")
    mock_eel.ACTIVE_CLIENTS.add(websocket)
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get("type")
                msg_id = data.get("id")
                
                if msg_type == "call":
                    method = data.get("method")
                    args = data.get("args", [])
                    
                    logger.debug(f"RPC Call: {method}({args})")
                    func = mock_eel.EXPOSED_METHODS.get(method)
                    
                    if not func:
                        logger.warning(f"Exposed method not found: {method}")
                        await websocket.send(json.dumps({
                            "type": "response",
                            "id": msg_id,
                            "success": False,
                            "error": f"Exposed method '{method}' not found"
                        }))
                        continue
                        
                    try:
                        # Call method: check if async or sync
                        if asyncio.iscoroutinefunction(func):
                            result = await func(*args)
                        else:
                            result = await asyncio.get_event_loop().run_in_executor(None, func, *args)
                            
                        await websocket.send(json.dumps({
                            "type": "response",
                            "id": msg_id,
                            "success": True,
                            "result": result
                        }))
                    except Exception as e:
                        logger.error(f"Error executing exposed method '{method}': {e}", exc_info=True)
                        await websocket.send(json.dumps({
                            "type": "response",
                            "id": msg_id,
                            "success": False,
                            "error": str(e)
                        }))
                        
                elif msg_type == "callback_response":
                    # Callback returned from frontend
                    with mock_eel.PENDING_CALLBACKS_LOCK:
                        item = mock_eel.PENDING_CALLBACKS.get(msg_id)
                    if item:
                        event, res_box = item
                        res_box["result"] = data.get("result")
                        res_box["error"] = data.get("error")
                        event.set()
                        
            except json.JSONDecodeError:
                logger.warning("Received malformed WebSocket packet")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"WebSocket client disconnected: {websocket.remote_address}")
    finally:
        mock_eel.ACTIVE_CLIENTS.remove(websocket)


def run_http_server(host: str, port: int):
    logger.info(f"Starting static HTTP server on http://{host}:{port}")
    try:
        bottle.run(app, host=host, port=port, quiet=True)
    except Exception as e:
        logger.critical(f"HTTP Server failed to start: {e}")


async def main():
    parser = argparse.ArgumentParser(description="PortAIOS Standalone Agent Daemon")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP & WS Bind Host")
    parser.add_argument("--port", type=int, default=8001, help="HTTP Server Port")
    parser.add_argument("--ws-port", type=int, default=9000, help="WebSocket Server Port")
    parser.add_argument("--token", default="portaios-secret-2026", help="Security Secret Token")
    args = parser.parse_args()

    # Share the current loop with MockEel for threadsafe communication
    mock_eel.WS_LOOP = asyncio.get_running_loop()

    logger.info("Initializing PortAIOS backend components...")
    # Invoke onboarding gui setup functions detaching Eel browser start
    start_eel_app()

    # Launch Bottle HTTP server in background thread
    http_thread = threading.Thread(
        target=run_http_server, 
        args=(args.host, args.port), 
        daemon=True,
        name="BottleHTTPServer"
    )
    http_thread.start()

    logger.info(f"Starting secure WebSocket server on ws://{args.host}:{args.ws_port}")
    logger.info(f"Access Token: {args.token}")
    logger.info(f"UI url: http://localhost:{args.port}/avatar-integration.html?token={args.token}")

    # Start WebSocket Server
    from functools import partial
    async with websockets.serve(
        partial(ws_handler, expected_token=args.token),
        args.host,
        args.ws_port
    ):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Daemon shutdown complete.")
