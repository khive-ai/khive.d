/**
 * WebSocket Hook
 * Provides real-time communication with automatic reconnection
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { env } from "@/config/env";

export interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
}

export interface UseWebSocketOptions {
  url?: string;
  protocols?: string | string[];
  reconnectAttempts?: number;
  reconnectInterval?: number;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export interface WebSocketState {
  socket: WebSocket | null;
  lastMessage: WebSocketMessage | null;
  readyState: number;
  isConnected: boolean;
  sendMessage: (message: any) => void;
  disconnect: () => void;
  reconnect: () => void;
}

export function useWebSocket(
  url: string = env.WEBSOCKET_URL,
  options: UseWebSocketOptions = {},
): WebSocketState {
  const {
    protocols,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = options;

  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [readyState, setReadyState] = useState<number>(WebSocket.CONNECTING);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const isConnected = readyState === WebSocket.OPEN;

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url, protocols);

      ws.addEventListener("open", () => {
        setReadyState(WebSocket.OPEN);
        reconnectAttemptsRef.current = 0;
        onOpen?.();
      });

      ws.addEventListener("close", () => {
        setReadyState(WebSocket.CLOSED);
        onClose?.();

        // Attempt to reconnect
        if (reconnectAttemptsRef.current < reconnectAttempts) {
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval * reconnectAttemptsRef.current);
        }
      });

      ws.addEventListener("error", (error) => {
        setReadyState(WebSocket.CLOSED);
        onError?.(error);
      });

      ws.addEventListener("message", (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.warn("Failed to parse WebSocket message:", event.data);
        }
      });

      setSocket(ws);
      setReadyState(WebSocket.CONNECTING);
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
    }
  }, [
    url,
    protocols,
    reconnectAttempts,
    reconnectInterval,
    onOpen,
    onClose,
    onError,
    onMessage,
  ]);

  const sendMessage = useCallback((message: any) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      const messageWithTimestamp = {
        ...message,
        timestamp: new Date().toISOString(),
      };
      socket.send(JSON.stringify(messageWithTimestamp));
    } else {
      console.warn("WebSocket is not connected");
    }
  }, [socket]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    if (socket) {
      socket.close();
      setSocket(null);
      setReadyState(WebSocket.CLOSED);
    }
  }, [socket]);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptsRef.current = 0;
    connect();
  }, [disconnect, connect]);

  // Initialize connection
  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    socket,
    lastMessage,
    readyState,
    isConnected,
    sendMessage,
    disconnect,
    reconnect,
  };
}

// Specialized hooks for different message types
export function useCoordinationWebSocket(coordinationId?: string) {
  return useWebSocket(
    coordinationId
      ? `${env.WEBSOCKET_URL}/coordination/${coordinationId}`
      : `${env.WEBSOCKET_URL}/coordination`,
    {
      onMessage: (message) => {
        // Handle coordination-specific messages
        console.log("Coordination message:", message);
      },
    },
  );
}

export function useAgentWebSocket(agentId?: string) {
  return useWebSocket(
    agentId
      ? `${env.WEBSOCKET_URL}/agents/${agentId}`
      : `${env.WEBSOCKET_URL}/agents`,
    {
      onMessage: (message) => {
        // Handle agent-specific messages
        console.log("Agent message:", message);
      },
    },
  );
}
