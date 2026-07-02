import asyncio
import websockets
import json
import random
from websockets.http11 import Response
from websockets.datastructures import Headers
import sys

clients = set()
def handle_subprocess_mode():
    if len(sys.argv) < 3 or sys.argv[1] != "--subprocess":
        return False
    return True

# The current `websockets` library version is stricter and rejects:
# InvalidUpgrade: invalid Connection header: keep-alive, so we need to manually performing the handshake
# using `websockets.http11`.


def _normalize_connection_header(conn, request):
    """Patch the Connection header so websockets>=13 strict validation accepts
    clients (e.g. some proxies/browsers) that send `Connection: keep-alive`
    instead of `Connection: Upgrade`.

    Headers.__setitem__ appends rather than replaces, so we must delete the
    existing value before setting a normalized one.  Returns None to let the
    normal handshake proceed, or a 426 Response for plain-HTTP requests.
    """
    upgrade = request.headers.get("Upgrade", "")
    if "websocket" not in upgrade.lower():
        body = b"This endpoint expects a WebSocket upgrade request.\n"
        headers = Headers()
        headers["Content-Type"] = "text/plain; charset=utf-8"
        headers["Content-Length"] = str(len(body))
        headers["Connection"] = "close"
        headers["Upgrade"] = "websocket"
        return Response(426, "Upgrade Required", headers, body)

    connection_val = request.headers.get("Connection", "")
    if "upgrade" not in connection_val.lower():
        # Delete existing value(s), then set a single normalised header.
        del request.headers["Connection"]
        request.headers["Connection"] = connection_val + ", Upgrade" if connection_val else "Upgrade"
    return None


async def handler(websocket):
    clients.add(websocket)
    try:
        while True:
            # Simulated AI emotion + speech output
            data = {
                "Smile": random.random(),
                "Frown": 0.0,
                "Wink_Left": random.choice([0, 1]),
                "Wink_Right": 0,
                "Viseme_A": random.random(),
                "Viseme_O": random.random(),
                "Viseme_M": random.random()
            }

            await websocket.send(json.dumps(data))
            await asyncio.sleep(0.1)

    except websockets.exceptions.ConnectionClosed:
        # Client disconnected normally
        pass
    except asyncio.CancelledError:
        # Server shutdown
        raise
    except Exception as e:
        # Log unexpected errors instead of silently ignoring them
        print(f"⚠️  WebSocket error: {e}")
    finally:
        clients.remove(websocket)

async def main():
    # Bind to a concrete IP so browser clients using ws://localhost:<port> can connect.
    # Also relax origin checks / headers handling for typical browser environments.
    async with websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        ping_interval=20,
        ping_timeout=20,
        max_queue=32,
        # Best-effort compatibility for browser handshakes.
        # (websockets will validate Sec-WebSocket-* headers and reject invalid ones.)
        origins=None,
        process_request=_normalize_connection_header,
    ):
        print("✅ Avatar control server running on ws://0.0.0.0:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
