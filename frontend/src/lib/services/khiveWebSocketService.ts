import { io, Socket } from 'socket.io-client';
import { KHIVE_CONFIG } from '@/lib/config/khive';
import { 
  CoordinationEvent, 
  OrchestrationSession, 
  Agent, 
  DaemonStatus 
} from '@/lib/types/khive';

// WebSocket event types for type-safe communication
export interface KhiveWebSocketEvents {
  // Outbound events (client -> server)
  join_coordination: (coordinationId: string) => void;
  leave_coordination: (coordinationId: string) => void;
  subscribe_session: (sessionId: string) => void;
  unsubscribe_session: (sessionId: string) => void;
  ping: () => void;
  
  // Inbound events (server -> client)
  coordination_event: (event: CoordinationEvent) => void;
  session_updated: (session: OrchestrationSession) => void;
  agent_updated: (agent: Agent) => void;
  daemon_status_updated: (status: DaemonStatus) => void;
  pong: (timestamp: number) => void;
  error: (error: { message: string; code?: string }) => void;
  connect: () => void;
  disconnect: (reason: string) => void;
  reconnect: (attemptNumber: number) => void;
  reconnect_error: (error: Error) => void;
}

export interface ConnectionHealth {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'disconnected';
  latency: number;
  consecutiveFailures: number;
  queueSize: number;
  lastPingTime?: number;
  reconnectCount: number;
}

export interface WebSocketStats {
  messagesReceived: number;
  messagesSent: number;
  duplicatesFiltered: number;
  reconnectCount: number;
  averageLatency: number;
}

// Message deduplication for reliability
interface MessageRecord {
  id: string;
  timestamp: number;
  type: string;
}

/**
 * KHIVE WebSocket Service - Real-time communication layer
 * 
 * Protocol design principles implemented:
 * - Connection state management with exponential backoff
 * - Message deduplication using sliding window
 * - Health monitoring with latency tracking  
 * - Automatic reconnection with circuit breaker pattern
 * - Message queuing for offline resilience
 */
export class KhiveWebSocketService {
  private socket: Socket | null = null;
  private connectionHealth: ConnectionHealth = {
    status: 'disconnected',
    latency: 0,
    consecutiveFailures: 0,
    queueSize: 0,
    reconnectCount: 0,
  };
  
  private stats: WebSocketStats = {
    messagesReceived: 0,
    messagesSent: 0,
    duplicatesFiltered: 0,
    reconnectCount: 0,
    averageLatency: 0,
  };
  
  // Message deduplication - sliding window of recent messages
  private messageHistory: MessageRecord[] = [];
  private readonly MESSAGE_HISTORY_SIZE = 1000;
  private readonly DUPLICATE_WINDOW_MS = 30000; // 30 seconds
  
  // Message queue for offline resilience
  private messageQueue: Array<{ event: string; data: any }> = [];
  private readonly MAX_QUEUE_SIZE = 100;
  
  // Ping/pong for latency monitoring
  private pingInterval: NodeJS.Timeout | null = null;
  private readonly PING_INTERVAL_MS = 5000;
  
  // Event listeners registry
  private eventListeners = new Map<keyof KhiveWebSocketEvents, Set<Function>>();
  
  constructor() {
    this.setupEventListeners();
  }
  
  /**
   * Connect to KHIVE WebSocket server
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket?.connected) {
        resolve();
        return;
      }
      
      // Disconnect existing socket if any
      if (this.socket) {
        this.socket.disconnect();
      }
      
      // Create new socket with proper configuration
      this.socket = io(KHIVE_CONFIG.WEBSOCKET_URL, {
        autoConnect: true,
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 10,
        timeout: 20000,
        forceNew: true,
        transports: ['websocket', 'polling'], // Fallback to polling if WebSocket fails
      });
      
      // Connection event handlers
      this.socket.on('connect', () => {
        this.connectionHealth.status = 'healthy';
        this.connectionHealth.consecutiveFailures = 0;
        this.startPingMonitoring();
        this.flushMessageQueue();
        this.emit('connect');
        resolve();
      });
      
      this.socket.on('connect_error', (error: Error) => {
        this.connectionHealth.consecutiveFailures++;
        this.connectionHealth.status = 'unhealthy';
        this.emit('reconnect_error', error);
        reject(error);
      });
      
      this.socket.on('disconnect', (reason: string) => {
        this.connectionHealth.status = 'disconnected';
        this.stopPingMonitoring();
        this.emit('disconnect', reason);
      });
      
      this.socket.on('reconnect', (attemptNumber: number) => {
        this.stats.reconnectCount++;
        this.connectionHealth.reconnectCount = this.stats.reconnectCount;
        this.emit('reconnect', attemptNumber);
      });
      
      // Protocol-specific event handlers
      this.setupProtocolHandlers();
    });
  }
  
  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.stopPingMonitoring();
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.connectionHealth.status = 'disconnected';
  }
  
  /**
   * Send message with queuing support for offline resilience
   */
  emit<K extends keyof KhiveWebSocketEvents>(
    event: K,
    ...args: Parameters<KhiveWebSocketEvents[K]>
  ): void {
    if (!this.socket?.connected) {
      // Queue message if offline and queue not full
      if (this.messageQueue.length < this.MAX_QUEUE_SIZE) {
        this.messageQueue.push({ event: event as string, data: args[0] });
        this.connectionHealth.queueSize = this.messageQueue.length;
      }
      return;
    }
    
    this.socket.emit(event as string, ...args);
    this.stats.messagesSent++;
  }
  
  /**
   * Subscribe to WebSocket events with deduplication
   */
  on<K extends keyof KhiveWebSocketEvents>(
    event: K,
    listener: KhiveWebSocketEvents[K]
  ): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(listener);
  }
  
  /**
   * Unsubscribe from WebSocket events
   */
  off<K extends keyof KhiveWebSocketEvents>(
    event: K,
    listener: KhiveWebSocketEvents[K]
  ): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.delete(listener);
    }
  }
  
  /**
   * Get current connection health status
   */
  getConnectionHealth(): ConnectionHealth {
    return { ...this.connectionHealth };
  }
  
  /**
   * Get WebSocket statistics
   */
  getStats(): WebSocketStats {
    return { ...this.stats };
  }
  
  /**
   * Join coordination room for real-time updates
   */
  joinCoordination(coordinationId: string): void {
    this.emit('join_coordination', coordinationId);
  }
  
  /**
   * Leave coordination room
   */
  leaveCoordination(coordinationId: string): void {
    this.emit('leave_coordination', coordinationId);
  }
  
  /**
   * Subscribe to session updates
   */
  subscribeToSession(sessionId: string): void {
    this.emit('subscribe_session', sessionId);
  }
  
  /**
   * Unsubscribe from session updates
   */
  unsubscribeFromSession(sessionId: string): void {
    this.emit('unsubscribe_session', sessionId);
  }
  
  // Private implementation methods
  
  private setupProtocolHandlers(): void {
    if (!this.socket) return;
    
    // Handle incoming coordination events with deduplication
    this.socket.on('coordination_event', (event: CoordinationEvent) => {
      if (this.isDuplicateMessage(event.timestamp.toString(), 'coordination_event')) {
        this.stats.duplicatesFiltered++;
        return;
      }
      
      this.stats.messagesReceived++;
      this.broadcastToListeners('coordination_event', event);
    });
    
    // Handle session updates
    this.socket.on('session_updated', (session: OrchestrationSession) => {
      this.stats.messagesReceived++;
      this.broadcastToListeners('session_updated', session);
    });
    
    // Handle agent updates
    this.socket.on('agent_updated', (agent: Agent) => {
      this.stats.messagesReceived++;
      this.broadcastToListeners('agent_updated', agent);
    });
    
    // Handle daemon status updates
    this.socket.on('daemon_status_updated', (status: DaemonStatus) => {
      this.stats.messagesReceived++;
      this.broadcastToListeners('daemon_status_updated', status);
    });
    
    // Handle pong for latency calculation
    this.socket.on('pong', (timestamp: number) => {
      const latency = Date.now() - timestamp;
      this.updateLatencyStats(latency);
      this.connectionHealth.latency = latency;
      this.connectionHealth.lastPingTime = Date.now();
      
      // Update health status based on latency
      if (latency < 100) {
        this.connectionHealth.status = 'healthy';
      } else if (latency < 500) {
        this.connectionHealth.status = 'degraded';
      } else {
        this.connectionHealth.status = 'unhealthy';
      }
    });
    
    // Handle server errors
    this.socket.on('error', (error: { message: string; code?: string }) => {
      this.connectionHealth.consecutiveFailures++;
      this.broadcastToListeners('error', error);
    });
  }
  
  private setupEventListeners(): void {
    // Initialize event listener sets for all event types
    const eventTypes: Array<keyof KhiveWebSocketEvents> = [
      'coordination_event', 'session_updated', 'agent_updated', 
      'daemon_status_updated', 'connect', 'disconnect', 
      'reconnect', 'reconnect_error', 'error', 'pong'
    ];
    
    eventTypes.forEach(event => {
      this.eventListeners.set(event, new Set());
    });
  }
  
  private broadcastToListeners<K extends keyof KhiveWebSocketEvents>(
    event: K,
    ...args: Parameters<KhiveWebSocketEvents[K]>
  ): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          (listener as any)(...args);
        } catch (error) {
          console.error(`Error in WebSocket event listener for ${event}:`, error);
        }
      });
    }
  }
  
  private isDuplicateMessage(messageId: string, type: string): boolean {
    const now = Date.now();
    
    // Clean old messages outside the duplicate window
    this.messageHistory = this.messageHistory.filter(
      msg => now - msg.timestamp <= this.DUPLICATE_WINDOW_MS
    );
    
    // Check if message is duplicate
    const isDuplicate = this.messageHistory.some(
      msg => msg.id === messageId && msg.type === type
    );
    
    if (!isDuplicate) {
      // Add to history
      this.messageHistory.push({ id: messageId, timestamp: now, type });
      
      // Limit history size
      if (this.messageHistory.length > this.MESSAGE_HISTORY_SIZE) {
        this.messageHistory = this.messageHistory.slice(-this.MESSAGE_HISTORY_SIZE);
      }
    }
    
    return isDuplicate;
  }
  
  private startPingMonitoring(): void {
    this.stopPingMonitoring(); // Clear any existing interval
    
    this.pingInterval = setInterval(() => {
      if (this.socket?.connected) {
        this.socket.emit('ping', Date.now());
      }
    }, this.PING_INTERVAL_MS);
  }
  
  private stopPingMonitoring(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
  
  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.socket?.connected) {
      const { event, data } = this.messageQueue.shift()!;
      this.socket.emit(event, data);
      this.stats.messagesSent++;
    }
    this.connectionHealth.queueSize = this.messageQueue.length;
  }
  
  private updateLatencyStats(latency: number): void {
    // Simple exponential moving average for latency
    const alpha = 0.1; // Smoothing factor
    this.stats.averageLatency = this.stats.averageLatency === 0 
      ? latency 
      : alpha * latency + (1 - alpha) * this.stats.averageLatency;
  }
}

// Singleton instance for application-wide use
export const khiveWebSocketService = new KhiveWebSocketService();