const http = require('http');
const WebSocket = require('ws');

const PORT = process.env.WS_PORT ? Number(process.env.WS_PORT) : 8765;

const server = http.createServer();
const wss = new WebSocket.Server({ server });

function makePayload() {
  return {
    Smile: Math.random(),
    Frown: 0.0,
    Wink_Left: Math.random() < 0.5 ? 0 : 1,
    Wink_Right: 0,
    Viseme_A: Math.random(),
    Viseme_O: Math.random(),
    Viseme_M: Math.random(),
  };
}

wss.on('connection', (ws) => {
  const timer = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(makePayload()));
    }
  }, 100);

  ws.on('close', () => clearInterval(timer));
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`✅ WS server running on ws://127.0.0.1:${PORT}`);
});

