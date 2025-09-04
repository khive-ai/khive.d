/**
 * React Hooks for Real-time Agent Monitoring
 * Built by architect+software-architecture for Ocean's Agentic ERP Command Center
 * 
 * Provides React integration with real-time monitoring system:
 * - WebSocket/SSE connection management
 * - Real-time agent status updates
 * - Task progress monitoring
 * - System alerts and notifications
 * - Connection health monitoring
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Subscription } from 'rxjs';
import { 
  realTimeMonitor,
  RealTimeMessage,
  AgentStatusUpdate,
  TaskProgressUpdate,
  CoordinationEvent,
  SystemAlert,
  ConnectionState,
  ConnectionConfig
} from '../architecture/RealTimeMonitoring';
import { AgentRealTimeStatus } from '../types/agent-composition';

// ============================================================================
// CONNECTION MANAGEMENT HOOKS
// ============================================================================

/**
 * Hook for managing real-time connection lifecycle
 */
export function useRealTimeConnection(
  connectionId: string,
  config: ConnectionConfig,
  enabled: boolean = true
) {
  const [connectionState, setConnectionState] = useState<ConnectionState | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const subscriptionRef = useRef<Subscription | null>(null);

  const connect = useCallback(() => {
    if (!enabled || subscriptionRef.current) return;

    console.log(`[USE-RT-CONNECTION] Connecting to real-time monitoring: ${connectionId}`);
    setIsConnecting(true);

    subscriptionRef.current = realTimeMonitor
      .createConnection(connectionId, config, true) // Enable SSE fallback
      .subscribe({
        next: (state) => {
          setConnectionState(state);
          setIsConnecting(state.status === 'connecting');
          console.log(`[USE-RT-CONNECTION] Connection state: ${state.status} (${state.protocol})`);
        },
        error: (error) => {
          console.error(`[USE-RT-CONNECTION] Connection error:`, error);
          setIsConnecting(false);
        }
      });
  }, [connectionId, config, enabled]);

  const disconnect = useCallback(() => {
    if (subscriptionRef.current) {
      subscriptionRef.current.unsubscribe();
      subscriptionRef.current = null;
    }
    
    realTimeMonitor.closeConnection(connectionId);
    setConnectionState(null);
    setIsConnecting(false);
    console.log(`[USE-RT-CONNECTION] Disconnected: ${connectionId}`);
  }, [connectionId]);

  const sendMessage = useCallback((message: Omit<RealTimeMessage, 'id' | 'timestamp'>) => {
    const fullMessage: RealTimeMessage = {
      ...message,
      id: `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      timestamp: Date.now()
    };

    return realTimeMonitor.sendMessage(connectionId, fullMessage);
  }, [connectionId]);

  // Auto-connect/disconnect based on enabled state
  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  const isConnected = useMemo(() => 
    connectionState?.status === 'connected'
  , [connectionState?.status]);

  const connectionInfo = useMemo(() => ({
    isConnected,
    isConnecting,
    protocol: connectionState?.protocol || 'none',
    latency: connectionState?.latency || 0,
    reconnectAttempts: connectionState?.reconnectAttempts || 0,
    messagesReceived: connectionState?.messagesReceived || 0,
    messagesSent: connectionState?.messagesSent || 0
  }), [connectionState, isConnected, isConnecting]);

  return {
    connectionState,
    connectionInfo,
    isConnected,
    isConnecting,
    connect,
    disconnect,
    sendMessage
  };
}

/**
 * Hook for monitoring all connection states
 */
export function useConnectionMonitor() {
  const [connectionStates, setConnectionStates] = useState<Map<string, ConnectionState>>(new Map());
  const subscriptionRef = useRef<Subscription | null>(null);

  useEffect(() => {
    subscriptionRef.current = realTimeMonitor
      .getConnectionStates()
      .subscribe(states => {
        setConnectionStates(new Map(states));
        console.log(`[USE-CONNECTION-MONITOR] Updated ${states.size} connection states`);
      });

    return () => {
      if (subscriptionRef.current) {
        subscriptionRef.current.unsubscribe();
        subscriptionRef.current = null;
      }
    };
  }, []);

  const connectionList = useMemo(() => 
    Array.from(connectionStates.entries()).map(([id, state]) => ({
      id,
      ...state
    }))
  , [connectionStates]);

  const connectedCount = useMemo(() => 
    connectionList.filter(conn => conn.status === 'connected').length
  , [connectionList]);

  const totalLatency = useMemo(() => 
    connectionList.reduce((sum, conn) => sum + conn.latency, 0)
  , [connectionList]);

  const averageLatency = useMemo(() => 
    connectedCount > 0 ? totalLatency / connectedCount : 0
  , [totalLatency, connectedCount]);

  return {
    connections: connectionList,
    connectedCount,
    totalConnections: connectionList.length,
    averageLatency,
    getConnectionState: useCallback((connectionId: string) => 
      connectionStates.get(connectionId)
    , [connectionStates])
  };
}

// ============================================================================
// MESSAGE SUBSCRIPTION HOOKS
// ============================================================================

/**
 * Hook for subscribing to specific message types
 */
export function useRealTimeSubscription<T extends RealTimeMessage>(
  subscriberId: string,
  messageTypes: string[],
  filter?: (message: RealTimeMessage) => boolean,
  enabled: boolean = true
) {
  const [messages, setMessages] = useState<T[]>([]);
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const subscriptionRef = useRef<Subscription | null>(null);

  useEffect(() => {
    if (!enabled) {
      if (subscriptionRef.current) {
        subscriptionRef.current.unsubscribe();
        subscriptionRef.current = null;
        realTimeMonitor.unsubscribe(subscriberId);
      }
      return;
    }

    console.log(`[USE-RT-SUBSCRIPTION] Subscribing ${subscriberId} to:`, messageTypes);

    subscriptionRef.current = realTimeMonitor
      .subscribe(subscriberId, messageTypes, filter)
      .subscribe({
        next: (message) => {
          const typedMessage = message as T;
          setLastMessage(typedMessage);
          setMessages(prev => [...prev.slice(-49), typedMessage]); // Keep last 50 messages
          console.log(`[USE-RT-SUBSCRIPTION] Received message: ${message.type} for ${subscriberId}`);
        },
        error: (error) => {
          console.error(`[USE-RT-SUBSCRIPTION] Subscription error for ${subscriberId}:`, error);
        }
      });

    return () => {
      if (subscriptionRef.current) {
        subscriptionRef.current.unsubscribe();
        subscriptionRef.current = null;
      }
      realTimeMonitor.unsubscribe(subscriberId, messageTypes);
    };
  }, [subscriberId, messageTypes.join(','), enabled, filter]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setLastMessage(null);
  }, []);

  return {
    messages,
    lastMessage,
    messageCount: messages.length,
    clearMessages
  };
}

/**
 * Hook for real-time agent status updates
 */
export function useRealTimeAgentStatus(
  connectionId: string,
  agentIds: string[],
  config?: ConnectionConfig
) {
  const defaultConfig: ConnectionConfig = {
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080/ws/agents',
    maxReconnectAttempts: 5,
    reconnectDelay: 2000,
    heartbeatInterval: 30000,
    messageTimeout: 10000,
    compressionEnabled: true,
    ...config
  };

  const { isConnected } = useRealTimeConnection(connectionId, defaultConfig, agentIds.length > 0);
  
  const { messages: statusUpdates, lastMessage } = useRealTimeSubscription<AgentStatusUpdate>(
    `agent_status_${connectionId}`,
    ['agent.status.update'],
    (message) => {
      const statusUpdate = message as AgentStatusUpdate;
      return agentIds.length === 0 || agentIds.includes(statusUpdate.payload.agentId);
    },
    isConnected && agentIds.length > 0
  );

  // Convert to agent status map
  const agentStatusMap = useMemo(() => {
    const statusMap = new Map<string, AgentRealTimeStatus>();
    
    statusUpdates.forEach(update => {
      const agentId = update.payload.agentId;
      statusMap.set(agentId, {
        agent_id: agentId,
        status: update.payload.status as any,
        current_task: update.payload.currentTask,
        progress: update.payload.progress,
        resource_usage: {
          cpu: update.payload.resourceUsage.cpu,
          memory: update.payload.resourceUsage.memory,
          tokens_used: update.payload.resourceUsage.tokens,
          api_calls: 0 // Would be provided in real implementation
        },
        performance_metrics: {
          tasks_completed: 0, // Would be tracked over time
          avg_task_time: 0,
          success_rate: 0.85, // Default value
          cost: 0
        },
        coordination: {
          locks_held: [],
          waiting_for: [],
          conflicts: []
        },
        last_activity: update.timestamp
      });
    });

    return statusMap;
  }, [statusUpdates]);

  const getAgentStatus = useCallback((agentId: string): AgentRealTimeStatus | undefined => {
    return agentStatusMap.get(agentId);
  }, [agentStatusMap]);

  const latestUpdate = useMemo(() => lastMessage?.payload || null, [lastMessage]);

  return {
    agentStatusMap,
    agentStatuses: Array.from(agentStatusMap.values()),
    getAgentStatus,
    latestUpdate,
    updateCount: statusUpdates.length,
    isConnected
  };
}

/**
 * Hook for real-time task progress monitoring
 */
export function useRealTimeTaskProgress(
  connectionId: string,
  taskIds: string[] = [],
  config?: ConnectionConfig
) {
  const defaultConfig: ConnectionConfig = {
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080/ws/tasks',
    maxReconnectAttempts: 3,
    reconnectDelay: 1500,
    heartbeatInterval: 25000,
    messageTimeout: 8000,
    compressionEnabled: true,
    ...config
  };

  const { isConnected } = useRealTimeConnection(connectionId, defaultConfig, true);
  
  const { messages: progressUpdates, lastMessage } = useRealTimeSubscription<TaskProgressUpdate>(
    `task_progress_${connectionId}`,
    ['task.progress.update'],
    (message) => {
      const progressUpdate = message as TaskProgressUpdate;
      return taskIds.length === 0 || taskIds.includes(progressUpdate.payload.taskId);
    },
    isConnected
  );

  const taskProgressMap = useMemo(() => {
    const progressMap = new Map();
    
    progressUpdates.forEach(update => {
      progressMap.set(update.payload.taskId, {
        taskId: update.payload.taskId,
        agentId: update.payload.agentId,
        progress: update.payload.progress,
        estimatedCompletion: update.payload.estimatedCompletion,
        currentStep: update.payload.currentStep,
        logs: update.payload.logs,
        lastUpdated: update.timestamp
      });
    });

    return progressMap;
  }, [progressUpdates]);

  const getTaskProgress = useCallback((taskId: string) => {
    return taskProgressMap.get(taskId);
  }, [taskProgressMap]);

  const getTasksForAgent = useCallback((agentId: string) => {
    return Array.from(taskProgressMap.values())
      .filter(task => task.agentId === agentId);
  }, [taskProgressMap]);

  return {
    taskProgressMap,
    allTaskProgress: Array.from(taskProgressMap.values()),
    getTaskProgress,
    getTasksForAgent,
    latestProgress: lastMessage?.payload || null,
    isConnected
  };
}

/**
 * Hook for real-time coordination events
 */
export function useRealTimeCoordination(
  connectionId: string,
  coordinationId?: string,
  config?: ConnectionConfig
) {
  const defaultConfig: ConnectionConfig = {
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080/ws/coordination',
    maxReconnectAttempts: 8,
    reconnectDelay: 3000,
    heartbeatInterval: 20000,
    messageTimeout: 12000,
    compressionEnabled: true,
    ...config
  };

  const { isConnected } = useRealTimeConnection(connectionId, defaultConfig, true);
  
  const { messages: coordinationEvents, lastMessage } = useRealTimeSubscription<CoordinationEvent>(
    `coordination_${connectionId}`,
    ['coordination.event'],
    (message) => {
      return !coordinationId || message.metadata.coordinationId === coordinationId;
    },
    isConnected
  );

  const eventsByType = useMemo(() => {
    const typeMap = new Map<string, CoordinationEvent[]>();
    
    coordinationEvents.forEach(event => {
      const eventType = event.payload.eventType;
      if (!typeMap.has(eventType)) {
        typeMap.set(eventType, []);
      }
      typeMap.get(eventType)!.push(event);
    });

    return typeMap;
  }, [coordinationEvents]);

  const criticalEvents = useMemo(() => 
    coordinationEvents.filter(event => 
      event.payload.severity === 'error' || 
      event.priority === 'critical'
    )
  , [coordinationEvents]);

  const getEventsOfType = useCallback((eventType: string) => {
    return eventsByType.get(eventType) || [];
  }, [eventsByType]);

  return {
    events: coordinationEvents,
    eventsByType,
    criticalEvents,
    getEventsOfType,
    latestEvent: lastMessage?.payload || null,
    isConnected
  };
}

/**
 * Hook for real-time system alerts
 */
export function useRealTimeAlerts(
  connectionId: string,
  alertTypes: string[] = [],
  config?: ConnectionConfig
) {
  const defaultConfig: ConnectionConfig = {
    url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8080/ws/alerts',
    maxReconnectAttempts: 10,
    reconnectDelay: 5000,
    heartbeatInterval: 15000,
    messageTimeout: 15000,
    compressionEnabled: true,
    ...config
  };

  const { isConnected } = useRealTimeConnection(connectionId, defaultConfig, true);
  
  const { messages: alerts, lastMessage, clearMessages } = useRealTimeSubscription<SystemAlert>(
    `alerts_${connectionId}`,
    ['system.alert'],
    (message) => {
      const alert = message as SystemAlert;
      return alertTypes.length === 0 || alertTypes.includes(alert.payload.alertType);
    },
    isConnected
  );

  const alertsByType = useMemo(() => {
    const typeMap = new Map<string, SystemAlert[]>();
    
    alerts.forEach(alert => {
      const alertType = alert.payload.alertType;
      if (!typeMap.has(alertType)) {
        typeMap.set(alertType, []);
      }
      typeMap.get(alertType)!.push(alert);
    });

    return typeMap;
  }, [alerts]);

  const criticalAlerts = useMemo(() => 
    alerts.filter(alert => 
      alert.payload.severity === 'critical' || 
      alert.priority === 'critical'
    )
  , [alerts]);

  const unacknowledgedAlerts = useMemo(() => 
    alerts.filter(alert => 
      !alert.metadata.acknowledged &&
      alert.payload.actionRequired
    )
  , [alerts]);

  const acknowledgeAlert = useCallback((alertId: string) => {
    // Would send acknowledgment to server
    console.log(`[USE-RT-ALERTS] Acknowledged alert: ${alertId}`);
  }, []);

  return {
    alerts,
    alertsByType,
    criticalAlerts,
    unacknowledgedAlerts,
    latestAlert: lastMessage?.payload || null,
    clearAlerts: clearMessages,
    acknowledgeAlert,
    isConnected
  };
}

// ============================================================================
// UTILITY HOOKS
// ============================================================================

/**
 * Hook for real-time monitoring statistics
 */
export function useRealTimeStatistics() {
  const [statistics, setStatistics] = useState({
    connections: 0,
    activeConnections: 0,
    totalSubscribers: 0,
    messageRate: 0
  });

  useEffect(() => {
    const interval = setInterval(() => {
      const stats = realTimeMonitor.getStatistics();
      setStatistics(stats);
    }, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  return statistics;
}

/**
 * Hook for connection health monitoring
 */
export function useConnectionHealth(connectionId: string) {
  const { connectionStates } = useConnectionMonitor();
  const [healthHistory, setHealthHistory] = useState<Array<{
    timestamp: number;
    status: string;
    latency: number;
  }>>([]);

  useEffect(() => {
    const state = connectionStates.get(connectionId);
    if (state) {
      setHealthHistory(prev => [...prev.slice(-19), {
        timestamp: Date.now(),
        status: state.status,
        latency: state.latency
      }]);
    }
  }, [connectionId, connectionStates]);

  const currentHealth = useMemo(() => {
    const state = connectionStates.get(connectionId);
    if (!state) return 'unknown';
    
    if (state.status === 'connected' && state.latency < 100) return 'excellent';
    if (state.status === 'connected' && state.latency < 300) return 'good';
    if (state.status === 'connected') return 'fair';
    return 'poor';
  }, [connectionId, connectionStates]);

  const averageLatency = useMemo(() => {
    const recentLatencies = healthHistory.slice(-10).map(h => h.latency);
    return recentLatencies.length > 0 
      ? recentLatencies.reduce((sum, lat) => sum + lat, 0) / recentLatencies.length 
      : 0;
  }, [healthHistory]);

  return {
    currentHealth,
    healthHistory,
    averageLatency,
    isStable: healthHistory.slice(-5).every(h => h.status === 'connected')
  };
}