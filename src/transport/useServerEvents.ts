import { useEffect, useRef } from "react";
import { WS_URL } from "../config";
import { useAppStore } from "../store";

/**
 * Live WebSocket client. Connects to the Sentry-CD gateway, forwards every
 * server message into the zustand store, and auto-reconnects with backoff so
 * the operator UI recovers from drops mid-scenario (the gateway replays the
 * recent event buffer on reconnect via `state_sync`).
 */
export function useServerEvents() {
  const ingest = useAppStore((s) => s.ingest);
  const setConnected = useAppStore((s) => s.setConnected);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const closedRef = useRef(false);

  useEffect(() => {
    closedRef.current = false;

    const connect = () => {
      if (closedRef.current) return;
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setConnected(true);
      };

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data as string);
          ingest(msg);
        } catch (err) {
          console.warn("[ws] bad message:", err);
        }
      };

      ws.onerror = () => {
        // onclose handles reconnect; avoid duplicate scheduling here.
      };

      ws.onclose = () => {
        setConnected(false);
        if (closedRef.current) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 8000);
        retryRef.current += 1;
        setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      closedRef.current = true;
      wsRef.current?.close();
    };
  }, [ingest, setConnected]);
}
