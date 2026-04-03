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
}

export function useWebSocket({
  sessionId,
  mode,
  onResult,
  onToken,
  onError,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const reconnectAttempt = useRef(0);
  const maxReconnect = 5;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const url = getWsUrl(sessionId, mode);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectAttempt.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        if (msg.type === "result" && msg.payload) onResult?.(msg.payload);
        else if (msg.type === "token" && msg.content) onToken?.(msg.content);
        else if (msg.type === "error" && msg.message) onError?.(msg.message);
      } catch {
        // binary or non-JSON
      }
    };

    ws.onclose = () => {
      setConnected(false);
      if (reconnectAttempt.current < maxReconnect) {
        const delay = Math.min(1000 * 2 ** reconnectAttempt.current, 16000);
        reconnectAttempt.current++;
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [sessionId, mode, onResult, onToken, onError]);

  const disconnect = useCallback(() => {
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
