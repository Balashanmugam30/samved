"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { EventEnvelope, EventType } from "@samved/schemas";

export type WsStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "error";

interface UseWebSocketOptions {
  url?: string;
  sessionId?: string;
  autoConnect?: boolean;
  maxReconnectAttempts?: number;
  onEvent?: (envelope: EventEnvelope) => void;
}

export function useWebSocket({
  url = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws",
  sessionId = "operator-console-01",
  autoConnect = true,
  maxReconnectAttempts = 5,
  onEvent,
}: UseWebSocketOptions = {}) {
  const [status, setStatus] = useState<WsStatus>("disconnected");
  const [lastEvent, setLastEvent] = useState<EventEnvelope | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const intentionalCloseRef = useRef(false);

  const connect = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus(reconnectCount > 0 ? "reconnecting" : "connecting");
    intentionalCloseRef.current = false;

    const fullUrl = `${url}?session_id=${encodeURIComponent(sessionId)}`;
    try {
      const ws = new WebSocket(fullUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        setReconnectCount(0);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as EventEnvelope;
          setLastEvent(parsed);
          onEvent?.(parsed);
        } catch {
          console.warn("Received unparseable WebSocket message:", event.data);
        }
      };

      ws.onerror = () => {
        setStatus("error");
      };

      ws.onclose = () => {
        socketRef.current = null;
        if (!intentionalCloseRef.current) {
          if (reconnectCount < maxReconnectAttempts) {
            setStatus("reconnecting");
            const delay = Math.min(1000 * 2 ** reconnectCount, 15000);
            reconnectTimeoutRef.current = setTimeout(() => {
              setReconnectCount((prev) => prev + 1);
              connect();
            }, delay);
          } else {
            setStatus("disconnected");
          }
        } else {
          setStatus("disconnected");
        }
      };
    } catch {
      setStatus("error");
    }
  }, [url, sessionId, reconnectCount, maxReconnectAttempts, onEvent]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setStatus("disconnected");
  }, []);

  const sendEvent = useCallback(
    (eventType: EventType, payload: Record<string, unknown>, callId = "default-call") => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        const envelope: EventEnvelope = {
          event_id: crypto.randomUUID(),
          event_type: eventType,
          schema_version: "1.0",
          timestamp: new Date().toISOString(),
          session_id: sessionId,
          call_id: callId,
          payload,
        };
        socketRef.current.send(JSON.stringify(envelope));
        return true;
      }
      return false;
    },
    [sessionId]
  );

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return { status, lastEvent, reconnectCount, connect, disconnect, sendEvent, wsUrl: url };
}
