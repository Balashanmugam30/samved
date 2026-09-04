"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { EventEnvelope, EventType } from "@samved/schemas";

export type WsStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected"
  | "error";

interface UseOperatorWebSocketOptions {
  url?: string;
  initialCallId?: string | null;
  autoConnect?: boolean;
  maxReconnectAttempts?: number;
  onSnapshot?: (payload: Record<string, any>) => void;
  onEvent?: (envelope: EventEnvelope) => void;
}

export function useOperatorWebSocket({
  url,
  initialCallId = null,
  autoConnect = true,
  maxReconnectAttempts = 8,
  onSnapshot,
  onEvent,
}: UseOperatorWebSocketOptions = {}) {
  const [status, setStatus] = useState<WsStatus>("disconnected");
  const [reconnectCount, setReconnectCount] = useState(0);
  const [lastEvent, setLastEvent] = useState<EventEnvelope | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const intentionalCloseRef = useRef(false);
  const activeCallIdRef = useRef<string | null>(initialCallId);

  // Derive default WS URL
  const defaultWsUrl = () => {
    if (typeof window !== "undefined") {
      const loc = window.location;
      const proto = loc.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${loc.hostname}:8000/ws/operator`;
    }
    return "ws://localhost:8000/ws/operator";
  };

  const wsUrl = url || defaultWsUrl();

  const connect = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus(reconnectCount > 0 ? "reconnecting" : "connecting");
    intentionalCloseRef.current = false;

    const fullUrl = activeCallIdRef.current
      ? `${wsUrl}?call_id=${encodeURIComponent(activeCallIdRef.current)}`
      : wsUrl;

    try {
      const ws = new WebSocket(fullUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        setReconnectCount(0);
        // If we have an active call subscription, send subscribe action
        if (activeCallIdRef.current) {
          ws.send(
            JSON.stringify({
              action: "SUBSCRIBE_CALL",
              call_id: activeCallIdRef.current,
            })
          );
        }
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as EventEnvelope;
          setLastEvent(parsed);

          if (parsed.event_type === EventType.OPERATOR_SNAPSHOT) {
            onSnapshot?.(parsed.payload as Record<string, any>);
          } else {
            onEvent?.(parsed);
          }
        } catch {
          console.warn("Operator WebSocket: Unparseable message received:", event.data);
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
  }, [wsUrl, reconnectCount, maxReconnectAttempts, onSnapshot, onEvent]);

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

  const subscribeCall = useCallback((callId: string) => {
    activeCallIdRef.current = callId;
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          action: "SUBSCRIBE_CALL",
          call_id: callId,
        })
      );
    }
  }, []);

  const subscribeAll = useCallback(() => {
    activeCallIdRef.current = null;
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          action: "SUBSCRIBE_ALL",
        })
      );
    }
  }, []);

  const ping = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          action: "PING",
        })
      );
    }
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    status,
    lastEvent,
    reconnectCount,
    connect,
    disconnect,
    subscribeCall,
    subscribeAll,
    ping,
    wsUrl,
  };
}
