const http = require('http');
const { WebSocketServer } = require('ws');

// DARTRIX Telemetry Configuration
const PORT = 8000;
const UPDATE_INTERVAL = 100;

// Global System State (Mock)
let systemState = {
  fusionScore: 0.65,
  vestibular: 0.82,
  error: 0.05,
  m: 0.85,
  state: "ADAPT",
  tick: 0,
  watchdog: "OK"
};

/**
 * Initialize HTTP Server
 * Supports basic status check and manual telemetry injection via POST
 */
const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/telemetry') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(systemState));
  } else if (req.method === 'POST' && req.url === '/telemetry') {
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    req.on('end', () => {
      try {
        const update = JSON.parse(body);
        systemState = { ...systemState, ...update };
        broadcastState();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ status: 'UPDATED' }));
      } catch (err) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'INVALID_JSON' }));
      }
    });
  } else {
    res.writeHead(404);
    res.end();
  }
});

/**
 * Initialize WebSocket Server
 */
const wss = new WebSocketServer({ server });

wss.on('connection', (ws) => {
  console.log('[TELEMETRY] Client connected');
  ws.send(JSON.stringify({ type: 'INIT', payload: systemState }));
  
  ws.on('error', console.error);
});

/**
 * Broadcast current state to all connected WS clients
 */
function broadcastState() {
  const data = JSON.stringify({ type: 'UPDATE', payload: systemState });
  wss.clients.forEach((client) => {
    if (client.readyState === 1) { // OPEN
      client.send(data);
    }
  });
}

/**
 * Simulation Loop - Increments tick and applies slight variance to score
 */
setInterval(() => {
  systemState.tick++;
  // Mock slight fluctuation
  systemState.fusionScore = Math.max(0, Math.min(1, systemState.fusionScore + (Math.random() * 0.02 - 0.01)));
  broadcastState();
}, UPDATE_INTERVAL);

server.listen(PORT, () => {
  console.log(`[DARTRIX] Telemetry Server running on http://localhost:${PORT}`);
  console.log(`[DARTRIX] WebSocket streaming enabled`);
});

process.on('uncaughtException', (err) => {
  console.error('[CRITICAL] Telemetry Server error:', err);
});
