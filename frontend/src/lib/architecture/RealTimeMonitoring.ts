/**
 * Real-time Architecture with WebSocket/SSE for Agent Monitoring
 * Built by architect+software-architecture for Ocean's Agentic ERP Command Center
 * 
 * Architecture Patterns:
 * - WebSocket connection management with auto-reconnection
 * - Server-Sent Events (SSE) as fallback mechanism
 * - Intelligent event routing and subscription management
 * - Connection pooling and resource optimization
 * - Message queuing during connection interruptions
 * - Graceful degradation from WebSocket → SSE → Polling
 */

import { BehaviorSubject, Observable, Subject, fromEvent, merge, timer, EMPTY } from 'rxjs';
import { 
  map, 
  filter, 
  catchError, 
  retry, 
  retryWhen, 
  delay, 
  take, 
  tap,
  switchMap,
  distinctUntilChanged,
  share,
  startWith
} from 'rxjs/operators';

// ============================================================================
// REAL-TIME MESSAGE TYPES
// ============================================================================

export interface RealTimeMessage {
  id: string;
  type: string;
  timestamp: number;
  source: 'agent' | 'coordinator' | 'system';
  target?: string; // Specific client/session target
  priority: 'low' | 'normal' | 'high' | 'critical';
  payload: any;
  metadata: {
    sessionId?: string;
    coordinationId?: string;
    agentId?: string;
    retry?: number;
    ttl?: number;
  };
}

export interface AgentStatusUpdate extends RealTimeMessage {
  type: 'agent.status.update';
  payload: {
    agentId: string;
    status: string;
    progress: number;
    currentTask: string;
    resourceUsage: {
      cpu: number;
      memory: number;
      tokens: number;
    };
    timestamp: number;
  };
}

export interface TaskProgressUpdate extends RealTimeMessage {
  type: 'task.progress.update';
  payload: {
    taskId: string;
    agentId: string;
    progress: number;
    estimatedCompletion: number;
    currentStep: string;
    logs: string[];
  };
}

export interface CoordinationEvent extends RealTimeMessage {
  type: 'coordination.event';
  payload: {
    eventType: 'agent_spawned' | 'task_assigned' | 'workflow_started' | 'resource_locked';
    description: string;
    affectedEntities: string[];
    severity: 'info' | 'warning' | 'error';
  };
}

export interface SystemAlert extends RealTimeMessage {
  type: 'system.alert';
  payload: {
    alertType: 'performance' | 'resource' | 'error' | 'security';
    severity: 'low' | 'medium' | 'high' | 'critical';
    title: string;
    description: string;
    actionRequired: boolean;
    suggestedActions: string[];
  };
}

// ============================================================================
// CONNECTION MANAGEMENT
// ============================================================================

export interface ConnectionConfig {
  url: string;
  protocols?: string[];
  maxReconnectAttempts: number;
  reconnectDelay: number;
  heartbeatInterval: number;
  messageTimeout: number;
  compressionEnabled: boolean;
  authToken?: string;
}

export interface ConnectionState {
  status: 'connecting' | 'connected' | 'disconnected' | 'error' | 'reconnecting';
  protocol: 'websocket' | 'sse' | 'polling' | 'none';
  connectedAt?: number;
  lastHeartbeat?: number;
  reconnectAttempts: number;
  latency: number;
  messagesSent: number;
  messagesReceived: number;
  bytesTransferred: number;
}

export class WebSocketConnection {
  private ws: WebSocket | null = null;
  private config: ConnectionConfig;
  private stateSubject = new BehaviorSubject<ConnectionState>({
    status: 'disconnected',
    protocol: 'websocket',
    reconnectAttempts: 0,
    latency: 0,
    messagesSent: 0,
    messagesReceived: 0,
    bytesTransferred: 0
  });
  private messageSubject = new Subject<RealTimeMessage>();
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private messageQueue: RealTimeMessage[] = [];
  private pendingPings = new Map<string, number>();

  constructor(config: ConnectionConfig) {
    this.config = {
      maxReconnectAttempts: 10,
      reconnectDelay: 1000,
      heartbeatInterval: 30000,
      messageTimeout: 10000,
      compressionEnabled: true,
      ...config
    };

    console.log(`[WS-CONNECTION] Initializing WebSocket connection to ${config.url}`);
  }

  connect(): Observable<ConnectionState> {
    this.updateState({ status: 'connecting' });
    
    try {
      const wsUrl = this.buildWebSocketUrl();
      this.ws = new WebSocket(wsUrl, this.config.protocols);
      
      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      
      console.log(`[WS-CONNECTION] Connecting to ${wsUrl}`);
    } catch (error) {
      console.error('[WS-CONNECTION] Failed to create WebSocket:', error);
      this.updateState({ status: 'error' });
    }

    return this.stateSubject.asObservable();
  }

  disconnect(): void {
    console.log('[WS-CONNECTION] Disconnecting WebSocket');
    
    this.clearTimers();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.updateState({ 
      status: 'disconnected',
      reconnectAttempts: 0
    });
  }

  send(message: RealTimeMessage): boolean {
    if (!this.isConnected()) {
      console.log('[WS-CONNECTION] Connection not ready, queuing message');
      this.queueMessage(message);
      return false;
    }

    try {
      const serialized = this.serializeMessage(message);
      this.ws!.send(serialized);
      
      this.updateState(state => ({
        ...state,
        messagesSent: state.messagesSent + 1,
        bytesTransferred: state.bytesTransferred + serialized.length
      }));
      
      console.log(`[WS-CONNECTION] Sent message: ${message.type}`);
      return true;
    } catch (error) {
      console.error('[WS-CONNECTION] Failed to send message:', error);
      this.queueMessage(message);
      return false;
    }
  }

  getMessageStream(): Observable<RealTimeMessage> {
    return this.messageSubject.asObservable();
  }

  getConnectionState(): Observable<ConnectionState> {
    return this.stateSubject.asObservable();
  }

  private buildWebSocketUrl(): string {
    const url = new URL(this.config.url);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    
    if (this.config.authToken) {
      url.searchParams.set('token', this.config.authToken);
    }
    
    url.searchParams.set('compression', this.config.compressionEnabled.toString());
    url.searchParams.set('v', '1.0'); // API version
    
    return url.toString();
  }

  private handleOpen(event: Event): void {
    console.log('[WS-CONNECTION] WebSocket connected');
    
    this.updateState({
      status: 'connected',
      connectedAt: Date.now(),
      reconnectAttempts: 0
    });

    this.startHeartbeat();
    this.processMessageQueue();
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message = this.deserializeMessage(event.data);
      
      if (message.type === 'pong') {
        this.handlePong(message);
        return;
      }

      this.updateState(state => ({
        ...state,
        messagesReceived: state.messagesReceived + 1,
        bytesTransferred: state.bytesTransferred + event.data.length,
        lastHeartbeat: Date.now()
      }));

      console.log(`[WS-CONNECTION] Received message: ${message.type}`);
      this.messageSubject.next(message);
    } catch (error) {
      console.error('[WS-CONNECTION] Failed to process message:', error);
    }
  }

  private handleClose(event: CloseEvent): void {
    console.log(`[WS-CONNECTION] WebSocket closed: ${event.code} - ${event.reason}`);
    
    this.clearTimers();
    this.ws = null;
    
    if (event.code !== 1000) { // Not normal closure
      this.attemptReconnect();
    } else {
      this.updateState({ status: 'disconnected' });
    }
  }

  private handleError(event: Event): void {
    console.error('[WS-CONNECTION] WebSocket error:', event);
    this.updateState({ status: 'error' });
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      this.sendPing();
    }, this.config.heartbeatInterval);
  }

  private sendPing(): void {
    const pingId = Date.now().toString();
    const pingMessage: RealTimeMessage = {
      id: `ping_${pingId}`,
      type: 'ping',
      timestamp: Date.now(),
      source: 'system',
      priority: 'low',
      payload: { id: pingId },
      metadata: {}
    };

    this.pendingPings.set(pingId, Date.now());
    this.send(pingMessage);

    // Clean up old pending pings
    setTimeout(() => {
      this.pendingPings.delete(pingId);
    }, this.config.messageTimeout);
  }

  private handlePong(message: RealTimeMessage): void {
    const pingId = message.payload?.id;
    const pingTime = this.pendingPings.get(pingId);
    
    if (pingTime) {
      const latency = Date.now() - pingTime;
      this.updateState(state => ({ ...state, latency }));
      this.pendingPings.delete(pingId);
      console.log(`[WS-CONNECTION] Ping/Pong latency: ${latency}ms`);
    }
  }

  private attemptReconnect(): void {
    const state = this.stateSubject.getValue();
    
    if (state.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('[WS-CONNECTION] Max reconnect attempts reached');
      this.updateState({ status: 'error' });
      return;
    }

    const delay = this.config.reconnectDelay * Math.pow(2, state.reconnectAttempts);
    
    console.log(`[WS-CONNECTION] Reconnecting in ${delay}ms (attempt ${state.reconnectAttempts + 1})`);
    
    this.updateState({ 
      status: 'reconnecting',
      reconnectAttempts: state.reconnectAttempts + 1
    });

    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private queueMessage(message: RealTimeMessage): void {
    // Add TTL if not present
    if (!message.metadata.ttl) {
      message.metadata.ttl = Date.now() + 300000; // 5 minutes
    }

    this.messageQueue.push(message);
    
    // Limit queue size
    if (this.messageQueue.length > 100) {
      this.messageQueue.shift();
    }
  }

  private processMessageQueue(): void {
    const now = Date.now();
    
    // Remove expired messages
    this.messageQueue = this.messageQueue.filter(msg => 
      !msg.metadata.ttl || msg.metadata.ttl > now
    );

    // Send queued messages
    const toSend = this.messageQueue.splice(0);
    toSend.forEach(message => {
      if (!this.send(message)) {
        // If send fails, it will be re-queued
        console.warn(`[WS-CONNECTION] Failed to send queued message: ${message.type}`);
      }
    });

    console.log(`[WS-CONNECTION] Processed ${toSend.length} queued messages`);
  }

  private serializeMessage(message: RealTimeMessage): string {
    if (this.config.compressionEnabled) {
      // Simple compression - in production would use more sophisticated compression
      return JSON.stringify(message);
    }
    return JSON.stringify(message);
  }

  private deserializeMessage(data: string): RealTimeMessage {
    return JSON.parse(data);
  }

  private isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private updateState(update: Partial<ConnectionState> | ((state: ConnectionState) => ConnectionState)): void {
    if (typeof update === 'function') {
      this.stateSubject.next(update(this.stateSubject.getValue()));
    } else {
      this.stateSubject.next({ ...this.stateSubject.getValue(), ...update });
    }
  }

  private clearTimers(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
  }
}

// ============================================================================
// SERVER-SENT EVENTS (SSE) CONNECTION
// ============================================================================

export class SSEConnection {
  private eventSource: EventSource | null = null;
  private config: ConnectionConfig;
  private stateSubject = new BehaviorSubject<ConnectionState>({
    status: 'disconnected',
    protocol: 'sse',
    reconnectAttempts: 0,
    latency: 0,
    messagesSent: 0,
    messagesReceived: 0,
    bytesTransferred: 0
  });
  private messageSubject = new Subject<RealTimeMessage>();

  constructor(config: ConnectionConfig) {
    this.config = config;
    console.log(`[SSE-CONNECTION] Initializing SSE connection to ${config.url}`);
  }

  connect(): Observable<ConnectionState> {
    this.updateState({ status: 'connecting' });
    
    try {
      const sseUrl = this.buildSSEUrl();
      this.eventSource = new EventSource(sseUrl);
      
      this.eventSource.onopen = this.handleOpen.bind(this);
      this.eventSource.onmessage = this.handleMessage.bind(this);
      this.eventSource.onerror = this.handleError.bind(this);
      
      console.log(`[SSE-CONNECTION] Connecting to ${sseUrl}`);
    } catch (error) {
      console.error('[SSE-CONNECTION] Failed to create EventSource:', error);
      this.updateState({ status: 'error' });
    }

    return this.stateSubject.asObservable();
  }

  disconnect(): void {
    console.log('[SSE-CONNECTION] Disconnecting SSE');
    
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    
    this.updateState({ status: 'disconnected', reconnectAttempts: 0 });
  }

  getMessageStream(): Observable<RealTimeMessage> {
    return this.messageSubject.asObservable();
  }

  getConnectionState(): Observable<ConnectionState> {
    return this.stateSubject.asObservable();
  }

  private buildSSEUrl(): string {
    const url = new URL(this.config.url.replace(/^ws/, 'http'));
    url.pathname = url.pathname.replace('/ws/', '/sse/');
    
    if (this.config.authToken) {
      url.searchParams.set('token', this.config.authToken);
    }
    
    return url.toString();
  }

  private handleOpen(event: Event): void {
    console.log('[SSE-CONNECTION] SSE connected');
    
    this.updateState({
      status: 'connected',
      connectedAt: Date.now(),
      reconnectAttempts: 0
    });
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: RealTimeMessage = JSON.parse(event.data);
      
      this.updateState(state => ({
        ...state,
        messagesReceived: state.messagesReceived + 1,
        bytesTransferred: state.bytesTransferred + event.data.length
      }));

      console.log(`[SSE-CONNECTION] Received message: ${message.type}`);
      this.messageSubject.next(message);
    } catch (error) {
      console.error('[SSE-CONNECTION] Failed to process SSE message:', error);
    }
  }

  private handleError(event: Event): void {
    console.error('[SSE-CONNECTION] SSE error:', event);
    
    const state = this.stateSubject.getValue();
    if (state.reconnectAttempts < this.config.maxReconnectAttempts) {
      setTimeout(() => {
        console.log(`[SSE-CONNECTION] Reconnecting (attempt ${state.reconnectAttempts + 1})`);
        this.updateState({ reconnectAttempts: state.reconnectAttempts + 1 });
        this.connect();
      }, this.config.reconnectDelay * Math.pow(2, state.reconnectAttempts));
    } else {
      this.updateState({ status: 'error' });
    }
  }

  private updateState(update: Partial<ConnectionState>): void {
    this.stateSubject.next({ ...this.stateSubject.getValue(), ...update });
  }
}

// ============================================================================
// REAL-TIME MONITORING MANAGER
// ============================================================================

export class RealTimeMonitoringManager {
  private connections: Map<string, WebSocketConnection | SSEConnection> = new Map();
  private subscriptions: Map<string, Set<string>> = new Map(); // topic -> subscriber IDs
  private messageStream = new Subject<RealTimeMessage>();
  private stateStream = new BehaviorSubject<Map<string, ConnectionState>>(new Map());
  
  constructor() {
    console.log('[RT-MONITOR] Real-time monitoring manager initialized');
  }

  /**
   * Create WebSocket connection with fallback to SSE
   */
  createConnection(
    connectionId: string, 
    config: ConnectionConfig,
    fallbackToSSE: boolean = true
  ): Observable<ConnectionState> {
    console.log(`[RT-MONITOR] Creating connection: ${connectionId}`);
    
    // Try WebSocket first
    const wsConnection = new WebSocketConnection(config);
    this.connections.set(connectionId, wsConnection);
    
    const connectionState$ = wsConnection.connect().pipe(
      tap(state => this.updateConnectionState(connectionId, state)),
      switchMap(state => {
        if (state.status === 'error' && fallbackToSSE) {
          console.log(`[RT-MONITOR] WebSocket failed, falling back to SSE for ${connectionId}`);
          return this.fallbackToSSE(connectionId, config);
        }
        return [state];
      }),
      share()
    );

    // Subscribe to messages
    wsConnection.getMessageStream().subscribe(message => {
      this.routeMessage(message);
    });

    return connectionState$;
  }

  /**
   * Subscribe to specific message types
   */
  subscribe(
    subscriberId: string, 
    topics: string[],
    filter?: (message: RealTimeMessage) => boolean
  ): Observable<RealTimeMessage> {
    console.log(`[RT-MONITOR] Subscriber ${subscriberId} subscribing to topics:`, topics);
    
    // Register subscription
    topics.forEach(topic => {
      if (!this.subscriptions.has(topic)) {
        this.subscriptions.set(topic, new Set());
      }
      this.subscriptions.get(topic)!.add(subscriberId);
    });

    // Return filtered message stream
    return this.messageStream.pipe(
      filter(message => topics.includes(message.type)),
      filter(message => !filter || filter(message)),
      tap(message => console.log(`[RT-MONITOR] Delivering ${message.type} to ${subscriberId}`))
    );
  }

  /**
   * Unsubscribe from topics
   */
  unsubscribe(subscriberId: string, topics?: string[]): void {
    if (topics) {
      topics.forEach(topic => {
        this.subscriptions.get(topic)?.delete(subscriberId);
      });
    } else {
      // Unsubscribe from all topics
      this.subscriptions.forEach(subscribers => {
        subscribers.delete(subscriberId);
      });
    }
    
    console.log(`[RT-MONITOR] Subscriber ${subscriberId} unsubscribed from ${topics?.length || 'all'} topics`);
  }

  /**
   * Send message through connection
   */
  sendMessage(connectionId: string, message: RealTimeMessage): boolean {
    const connection = this.connections.get(connectionId);
    if (!connection) {
      console.error(`[RT-MONITOR] Connection ${connectionId} not found`);
      return false;
    }

    if (connection instanceof WebSocketConnection) {
      return connection.send(message);
    } else {
      console.warn(`[RT-MONITOR] SSE connections cannot send messages`);
      return false;
    }
  }

  /**
   * Get connection states
   */
  getConnectionStates(): Observable<Map<string, ConnectionState>> {
    return this.stateStream.asObservable();
  }

  /**
   * Get connection state for specific connection
   */
  getConnectionState(connectionId: string): ConnectionState | null {
    const states = this.stateStream.getValue();
    return states.get(connectionId) || null;
  }

  /**
   * Close connection
   */
  closeConnection(connectionId: string): void {
    const connection = this.connections.get(connectionId);
    if (connection) {
      connection.disconnect();
      this.connections.delete(connectionId);
      
      const states = new Map(this.stateStream.getValue());
      states.delete(connectionId);
      this.stateStream.next(states);
      
      console.log(`[RT-MONITOR] Closed connection: ${connectionId}`);
    }
  }

  /**
   * Close all connections
   */
  closeAllConnections(): void {
    console.log(`[RT-MONITOR] Closing all ${this.connections.size} connections`);
    
    this.connections.forEach((connection, id) => {
      connection.disconnect();
    });
    
    this.connections.clear();
    this.subscriptions.clear();
    this.stateStream.next(new Map());
  }

  /**
   * Get monitoring statistics
   */
  getStatistics(): {
    connections: number;
    activeConnections: number;
    totalSubscribers: number;
    messageRate: number;
  } {
    const states = this.stateStream.getValue();
    const activeConnections = Array.from(states.values())
      .filter(state => state.status === 'connected').length;
    
    const totalSubscribers = Array.from(this.subscriptions.values())
      .reduce((total, subscribers) => total + subscribers.size, 0);

    return {
      connections: this.connections.size,
      activeConnections,
      totalSubscribers,
      messageRate: 0 // Would calculate from message history
    };
  }

  private fallbackToSSE(connectionId: string, config: ConnectionConfig): Observable<ConnectionState> {
    console.log(`[RT-MONITOR] Setting up SSE fallback for ${connectionId}`);
    
    const sseConnection = new SSEConnection(config);
    this.connections.set(connectionId, sseConnection);
    
    // Subscribe to SSE messages
    sseConnection.getMessageStream().subscribe(message => {
      this.routeMessage(message);
    });

    return sseConnection.connect().pipe(
      tap(state => this.updateConnectionState(connectionId, state))
    );
  }

  private routeMessage(message: RealTimeMessage): void {
    console.log(`[RT-MONITOR] Routing message: ${message.type}`);
    
    // Check if there are subscribers for this message type
    const subscribers = this.subscriptions.get(message.type);
    if (subscribers && subscribers.size > 0) {
      this.messageStream.next(message);
    }
  }

  private updateConnectionState(connectionId: string, state: ConnectionState): void {
    const states = new Map(this.stateStream.getValue());
    states.set(connectionId, state);
    this.stateStream.next(states);
  }
}

// Export singleton instance for application use
export const realTimeMonitor = new RealTimeMonitoringManager();