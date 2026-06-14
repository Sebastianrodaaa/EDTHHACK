/**
 * Backend connection config.
 *
 * The mobile app talks to the Sentry-CD FastAPI gateway over HTTP (control) and
 * WebSocket (live event stream).
 *
 * - iOS Simulator / web: `localhost` reaches the host machine.
 * - Physical device on the same LAN: set EXPO_PUBLIC_SERVER_HOST to the host's
 *   LAN IP (e.g. "192.168.1.42") before `expo start`, or edit DEFAULT_HOST.
 */
const DEFAULT_HOST = "localhost";
const PORT = 8000;

const HOST =
  (process.env.EXPO_PUBLIC_SERVER_HOST as string | undefined) || DEFAULT_HOST;

export const SERVER_HOST = HOST;
export const HTTP_BASE = `http://${HOST}:${PORT}`;
export const WS_URL = `ws://${HOST}:${PORT}/ws`;
export const DEMO_SCENARIO = "demo-alpha";
