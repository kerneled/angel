"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getWsUrl } from "../lib/api";

interface WSMessage {
  type: string;
  content?: string;
  payload?: Record<string, unknown>;
  message?: string;
}

interface UseWebSocketOptions {
  sessionId: string;
  mode: "audio" | "video" | "combined";
  onResult?: (payload: Record<string, unknown>) => void;
  onToken?: (token: string) => void;
  onError?: (message: string) => void;
  onConnected?: () => void;
}

export function useWebSocket({
  sessionId,
  mode,
  onResult,
  onToken,
  onError,
  onConnected,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectAttempt = useRef(0);
  const maxReconnect = 5;

  // Stable refs for callbacks
  const onResultRef = useRef(onResult);
  const onTokenRef = useRef(onToken);
  const onErrorRef = useRef(onError);
  const onConnectedRef = useRef(onConnected);
  onResultRef.current = onResult;
  onTokenRef.current = onToken;
  onErrorRef.current = onError;
  onConnectedRef.current = onConnected;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = getWsUrl(sessionId, mode);
    console.log("[DogSense WS] Connecting to", url);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[DogSense WS] Connected");
      setConnected(true);
      reconnectAttempt.current = 0;
      onConnectedRef.current?.();
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        if (msg.type === "result" && msg.payload)
          onResultRef.current?.(msg.payload);
        else if (msg.type === "token" && msg.content)
          onTokenRef.current?.(msg.content);
        else if (msg.type === "error" && msg.message)
          onErrorRef.current?.(msg.message);
      } catch {
        // binary or non-JSON
      }
    };

    ws.onclose = (event) => {
      console.log("[DogSense WS] Closed", event.code, event.reason);
      setConnected(false);
      wsRef.current = null;
      if (reconnectAttempt.current < maxReconnect) {
        const delay = Math.min(1000 * 2 ** reconnectAttempt.current, 16000);
        reconnectAttempt.current++;
        console.log(`[DogSense WS] Reconnecting in ${delay}ms...`);
        setTimeout(connect, delay);
      }
    };

    ws.onerror = (event) => {
      console.error("[DogSense WS] Error", event);
      ws.close();
    };
  }, [sessionId, mode]);

  const disconnect = useCallback(() => {
    console.log("[DogSense WS] Disconnecting");
    reconnectAttempt.current = maxReconnect;
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  const sendText = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  const sendBinary = useCallback((data: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  useEffect(() => {
    return () => {
      reconnectAttempt.current = maxReconnect;
      wsRef.current?.close();
    };
  }, []);

  return { connect, disconnect, sendText, sendBinary, connected };
}
