// Development-server proxy helper (used by vite.config.js only).
// Without it, Vite answers /api/* with an empty "500 Internal Server Error" when the
// backend is not running, which looks exactly like a crash inside the API.
export const BACKEND_UNREACHABLE = 'backend_unreachable';

export function backendUnreachableHandler(target, log = console.error) {
  return (err, req, res) => {
    log(`[USIUBOT dev proxy] ${req?.method} ${req?.url}: backend at ${target} is not reachable (${err?.code || err?.message})`);
    // For WebSocket upgrades res is a socket, not a response.
    if (!res || typeof res.writeHead !== 'function' || res.headersSent || res.writableEnded) return;
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      error: 'The USIUBOT server is not running or not reachable, so your question could not be answered. ' +
        'Please try again later.',
      code: BACKEND_UNREACHABLE,
    }));
  };
}
