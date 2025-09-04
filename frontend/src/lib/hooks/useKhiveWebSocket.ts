import { useState, useCallback, useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { OrchestrationSession, CoordinationEvent, DaemonStatus, Agent } from '@/lib/types/khive';
import { KhiveApiService, KhiveApiError, KhiveConnectionError } from '@/lib/services/khiveApiService';
import { khiveWebSocketService, ConnectionHealth, WebSocketStats } from '@/lib/services/khiveWebSocketService';
import { KHIVE_CONFIG } from '@/lib/config/khive';

interface WebSocketState {
  connected: boolean;
  sessions: OrchestrationSession[];
  events: CoordinationEvent[];
  agents: Agent[];
  sendCommand: (command: string, priority?: number) => Promise<boolean>;
  reconnect: () => Promise<void>;
  joinCoordination: (coordinationId: string) => void;
  leaveCoordination: (coordinationId: string) => void;
  subscribeToSession: (sessionId: string) => void;
  unsubscribeFromSession: (sessionId: string) => void;
  daemonStatus: DaemonStatus;
  connectionHealth: ConnectionHealth;
  stats: WebSocketStats;
  error: string | null;
}

const QUERY_KEYS = {
  daemonStatus: ['daemon', 'status'],
  sessions: ['sessions'],
  agents: ['agents'],
  events: ['coordination', 'events'],
} as const;

/**
 * Real KHIVE WebSocket Hook - Integration with KHIVE daemon
 * 
 * Combines HTTP API calls for initial data fetching with WebSocket
 * for real-time updates. Implements proper error handling, reconnection
 * logic, and state synchronization.
 */
export function useKhiveWebSocket(): WebSocketState {
  // Component state for real-time data
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<CoordinationEvent[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [connectionHealth, setConnectionHealth] = useState<ConnectionHealth>({
    status: 'disconnected',
    latency: 0,
    consecutiveFailures: 0,
    queueSize: 0,
    reconnectCount: 0,
  });
  const [stats, setStats] = useState<WebSocketStats>({
    messagesReceived: 0,
    messagesSent: 0,
    duplicatesFiltered: 0,
    reconnectCount: 0,
    averageLatency: 0,
  });
  const [error, setError] = useState<string | null>(null);
  
  const queryClient = useQueryClient();
  const wsInitialized = useRef(false);
  const eventBuffer = useRef<CoordinationEvent[]>([]);
  
  // Query daemon status with automatic polling
  const { 
    data: daemonStatus = {
      running: false,
      health: 'unhealthy' as const,
      uptime: 0,
      active_sessions: 0,
      total_agents: 0,
      memory_usage: 0,
      cpu_usage: 0,
    },
    error: daemonError
  } = useQuery({
    queryKey: QUERY_KEYS.daemonStatus,
    queryFn: KhiveApiService.getDaemonStatus,
    refetchInterval: KHIVE_CONFIG.POLLING.DAEMON_STATUS_INTERVAL_MS,
    retry: (failureCount, error) => {
      // Retry on connection errors, but not on API errors
      if (error instanceof KhiveConnectionError) {
        return failureCount < 3;
      }
      return false;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });
  
  // Query sessions with polling when daemon is running
  const { data: sessions = [] } = useQuery({
    queryKey: QUERY_KEYS.sessions,
    queryFn: KhiveApiService.getSessions,
    refetchInterval: daemonStatus.running ? KHIVE_CONFIG.POLLING.SESSION_UPDATE_INTERVAL_MS : false,
    enabled: daemonStatus.running,
    retry: 2,
  });
  
  // Initialize WebSocket connection
  useEffect(() => {
    if (!daemonStatus.running || wsInitialized.current) {
      return;
    }
    
    const initializeWebSocket = async () => {
      try {
        await khiveWebSocketService.connect();
        wsInitialized.current = true;
        setError(null);
      } catch (error) {
        setError(error instanceof Error ? error.message : 'Failed to connect to WebSocket');
        console.error('WebSocket connection failed:', error);
      }
    };
    
    initializeWebSocket();
    
    return () => {
      if (wsInitialized.current) {
        khiveWebSocketService.disconnect();
        wsInitialized.current = false;
      }
    };
  }, [daemonStatus.running]);
  
  // Set up WebSocket event listeners
  useEffect(() => {
    if (!wsInitialized.current) return;
    
    const handleConnect = () => {
      setConnected(true);
      setError(null);
    };
    
    const handleDisconnect = () => {
      setConnected(false);
    };
    
    const handleCoordinationEvent = (event: CoordinationEvent) => {
      // Add to event buffer with size limit
      eventBuffer.current = [event, ...eventBuffer.current].slice(0, KHIVE_CONFIG.UI.MAX_ACTIVITY_STREAM_ITEMS);
      setEvents([...eventBuffer.current]);
      
      // Invalidate related queries for consistency
      if (event.type === 'agent_spawn') {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.agents });
      } else if (event.type === 'task_complete' || event.type === 'task_start') {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.sessions });
      }
    };
    
    const handleSessionUpdated = (session: OrchestrationSession) => {
      // Update session in query cache
      queryClient.setQueryData(QUERY_KEYS.sessions, (oldSessions: OrchestrationSession[] = []) => {
        const sessionIndex = oldSessions.findIndex(s => s.sessionId === session.sessionId);
        if (sessionIndex >= 0) {
          const newSessions = [...oldSessions];
          newSessions[sessionIndex] = session;
          return newSessions;
        } else {
          return [...oldSessions, session];
        }
      });
    };
    
    const handleAgentUpdated = (agent: Agent) => {
      setAgents(prevAgents => {
        const agentIndex = prevAgents.findIndex(a => a.id === agent.id);
        if (agentIndex >= 0) {
          const newAgents = [...prevAgents];
          newAgents[agentIndex] = agent;
          return newAgents;
        } else {
          return [...prevAgents, agent];
        }
      });
    };
    
    const handleDaemonStatusUpdated = (status: DaemonStatus) => {
      // Update daemon status in query cache
      queryClient.setQueryData(QUERY_KEYS.daemonStatus, status);
    };
    
    const handleError = (wsError: { message: string; code?: string }) => {
      setError(wsError.message);
      console.error('WebSocket error:', wsError);
    };
    
    // Subscribe to WebSocket events
    khiveWebSocketService.on('connect', handleConnect);
    khiveWebSocketService.on('disconnect', handleDisconnect);
    khiveWebSocketService.on('coordination_event', handleCoordinationEvent);
    khiveWebSocketService.on('session_updated', handleSessionUpdated);
    khiveWebSocketService.on('agent_updated', handleAgentUpdated);
    khiveWebSocketService.on('daemon_status_updated', handleDaemonStatusUpdated);
    khiveWebSocketService.on('error', handleError);
    
    return () => {
      // Cleanup event listeners
      khiveWebSocketService.off('connect', handleConnect);
      khiveWebSocketService.off('disconnect', handleDisconnect);
      khiveWebSocketService.off('coordination_event', handleCoordinationEvent);
      khiveWebSocketService.off('session_updated', handleSessionUpdated);
      khiveWebSocketService.off('agent_updated', handleAgentUpdated);
      khiveWebSocketService.off('daemon_status_updated', handleDaemonStatusUpdated);
      khiveWebSocketService.off('error', handleError);
    };
  }, [queryClient]);
  
  // Update connection health and stats periodically
  useEffect(() => {
    if (!wsInitialized.current) return;
    
    const updateHealthStats = () => {
      setConnectionHealth(khiveWebSocketService.getConnectionHealth());
      setStats(khiveWebSocketService.getStats());
    };
    
    const interval = setInterval(updateHealthStats, 1000);
    return () => clearInterval(interval);
  }, []);
  
  // Command execution with proper error handling
  const sendCommand = useCallback(async (command: string, priority?: number): Promise<boolean> => {
    try {
      // Map numeric priority to string priority
      const priorityMap: Record<number, 'low' | 'normal' | 'high' | 'critical'> = {
        0: 'low',
        1: 'normal', 
        2: 'high',
        3: 'critical'
      };
      
      const priorityStr = priority !== undefined ? priorityMap[priority] || 'normal' : 'normal';
      
      const result = await KhiveApiService.executeCommand(
        command, 
        [],
        priorityStr
      );
      
      if (!result.success) {
        setError(result.error || 'Command execution failed');
        return false;
      }
      
      setError(null);
      return true;
    } catch (error) {
      const errorMessage = error instanceof KhiveApiError 
        ? error.message 
        : 'Failed to execute command';
      setError(errorMessage);
      return false;
    }
  }, []);
  
  // Manual reconnection
  const reconnect = useCallback(async (): Promise<void> => {
    try {
      khiveWebSocketService.disconnect();
      await khiveWebSocketService.connect();
      setError(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Reconnection failed';
      setError(errorMessage);
      throw error;
    }
  }, []);
  
  // Coordination room management
  const joinCoordination = useCallback((coordinationId: string) => {
    khiveWebSocketService.joinCoordination(coordinationId);
  }, []);
  
  const leaveCoordination = useCallback((coordinationId: string) => {
    khiveWebSocketService.leaveCoordination(coordinationId);
  }, []);
  
  // Session subscription management
  const subscribeToSession = useCallback((sessionId: string) => {
    khiveWebSocketService.subscribeToSession(sessionId);
  }, []);
  
  const unsubscribeFromSession = useCallback((sessionId: string) => {
    khiveWebSocketService.unsubscribeFromSession(sessionId);
  }, []);
  
  // Update error state based on daemon connection
  useEffect(() => {
    if (daemonError) {
      setError(daemonError instanceof Error ? daemonError.message : 'Daemon connection failed');
    } else if (!daemonStatus.running && error?.includes('Daemon')) {
      setError(null); // Clear daemon errors when status is resolved
    }
  }, [daemonError, daemonStatus.running, error]);

  return {
    connected,
    sessions,
    events,
    agents,
    sendCommand,
    reconnect,
    joinCoordination,
    leaveCoordination,
    subscribeToSession,
    unsubscribeFromSession,
    daemonStatus,
    connectionHealth,
    stats,
    error,
  };
}

// Export WebSocket service for direct access if needed
export { khiveWebSocketService };