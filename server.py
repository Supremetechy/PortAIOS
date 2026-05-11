import asyncio
import websockets
import json
import random
from websockets.http11 import Response
from websockets.datastructures import Headers

clients = set()

# Fix for browsers/clients that send a non-standard Connection header.
# The current `websockets` library version is stricter and rejects:
#   invalid Connection header: keep-alive
# We implement a minimal handshake prefilter by manually performing the handshake
# using `websockets.http11`.


def _normalize_connection_header(_connection, request):
    """Append `Upgrade` to the Connection header if missing, so websockets>=13
    strict validation accepts handshakes from clients that send only
    `Connection: keep-alive`.

    If a browser or health check hits this port with plain HTTP, return a
    small 426 response rather than raising `InvalidUpgrade: missing Upgrade
    header` during handshake validation.
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

    connection = request.headers.get("Connection", "")
    tokens = [t.strip() for t in connection.split(",") if t.strip()]
    if not any(t.lower() == "upgrade" for t in tokens):
        tokens.append("Upgrade")
        request.headers["Connection"] = ", ".join(tokens) or "Upgrade"
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

    except:
        pass
    finally:
        clients.remove(websocket)

async def main():
    # Bind to a concrete IP so browser clients using ws://localhost:<port> can connect.
    # Also relax origin checks / headers handling for typical browser environments.
    async with websockets.serve(
        handler,
        "127.0.0.1",
        8765,
        ping_interval=20,
        ping_timeout=20,
        max_queue=32,
        # Best-effort compatibility for browser handshakes.
        # (websockets will validate Sec-WebSocket-* headers and reject invalid ones.)
        origins=None,
        process_request=_normalize_connection_header,
    ):
        print("✅ Avatar control server running on ws://127.0.0.1:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
