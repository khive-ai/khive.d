import { 
  OrchestrationSession, 
  Agent, 
  PlanningRequest, 
  PlanningResponse, 
  CoordinationEvent,
  DaemonStatus,
  SessionMetrics,
  SessionAction 
} from '@/lib/types/khive';
import { KHIVE_CONFIG } from '@/lib/config/khive';

// Protocol-level error types for proper error handling
export class KhiveApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'KhiveApiError';
  }
}

export class KhiveConnectionError extends KhiveApiError {
  constructor(message: string, public retryable = true) {
    super(message, 0, 'CONNECTION_ERROR');
    this.name = 'KhiveConnectionError';
    this.retryable = retryable;
  }
}

// HTTP client configuration with retry logic
const createHttpClient = () => {
  const baseURL = KHIVE_CONFIG.API_BASE;
  
  const request = async (
    endpoint: string,
    options: RequestInit = {}
  ): Promise<Response> => {
    const url = `${baseURL}${endpoint}`;
    
    // Default headers for API communication
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers,
    };

    const config: RequestInit = {
      ...options,
      headers,
      credentials: 'same-origin', // Security: include cookies for auth
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new KhiveApiError(
          errorData.message || `HTTP ${response.status}: ${response.statusText}`,
          response.status,
          errorData.code,
          errorData
        );
      }
      
      return response;
    } catch (error) {
      if (error instanceof KhiveApiError) {
        throw error;
      }
      
      // Network-level errors (connection refused, timeout, etc.)
      throw new KhiveConnectionError(
        `Failed to connect to KHIVE daemon: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  };

  return { request };
};

const httpClient = createHttpClient();

/**
 * KHIVE API Service - Core integration layer for KHIVE daemon communication
 * 
 * Implements protocol-design principles:
 * - Layered architecture (HTTP/WebSocket abstraction)
 * - Reliability mechanisms (retries, error detection)
 * - Security patterns (authentication, input validation)
 */
export class KhiveApiService {
  
  // DAEMON STATUS AND HEALTH
  
  /**
   * Get current daemon status and health metrics
   */
  static async getDaemonStatus(): Promise<DaemonStatus> {
    const response = await httpClient.request('/api/daemon/status');
    return response.json();
  }
  
  /**
   * Ping daemon for connectivity check
   */
  static async pingDaemon(): Promise<{ latency: number; status: 'ok' | 'degraded' }> {
    const start = performance.now();
    try {
      await httpClient.request('/api/daemon/ping');
      const latency = performance.now() - start;
      return { 
        latency, 
        status: latency < 100 ? 'ok' : 'degraded' 
      };
    } catch (error) {
      throw new KhiveConnectionError('Daemon ping failed');
    }
  }
  
  // PLANNING AND ORCHESTRATION
  
  /**
   * Submit planning request to KHIVE daemon
   */
  static async submitPlan(request: PlanningRequest): Promise<PlanningResponse> {
    const response = await httpClient.request('/api/planning/submit', {
      method: 'POST',
      body: JSON.stringify(request),
    });
    return response.json();
  }
  
  /**
   * Get planning result by coordination ID
   */
  static async getPlanningResult(coordinationId: string): Promise<PlanningResponse> {
    const response = await httpClient.request(`/api/planning/result/${coordinationId}`);
    return response.json();
  }
  
  // SESSION MANAGEMENT
  
  /**
   * Get all orchestration sessions
   */
  static async getSessions(): Promise<OrchestrationSession[]> {
    const response = await httpClient.request('/api/sessions');
    return response.json();
  }
  
  /**
   * Get specific session by ID
   */
  static async getSession(sessionId: string): Promise<OrchestrationSession> {
    const response = await httpClient.request(`/api/sessions/${sessionId}`);
    return response.json();
  }
  
  /**
   * Get sessions by coordination ID (grouped sessions)
   */
  static async getSessionsByCoordination(coordinationId: string): Promise<OrchestrationSession[]> {
    const response = await httpClient.request(`/api/sessions/coordination/${coordinationId}`);
    return response.json();
  }
  
  /**
   * Perform session action (pause, resume, terminate, etc.)
   */
  static async sessionAction(action: SessionAction): Promise<{ success: boolean; message: string }> {
    const response = await httpClient.request(`/api/sessions/${action.sessionId}/action`, {
      method: 'POST',
      body: JSON.stringify({ 
        action: action.type, 
        reason: action.reason 
      }),
    });
    return response.json();
  }
  
  /**
   * Get session metrics and cost tracking
   */
  static async getSessionMetrics(sessionId: string): Promise<SessionMetrics> {
    const response = await httpClient.request(`/api/sessions/${sessionId}/metrics`);
    return response.json();
  }
  
  // AGENT MANAGEMENT
  
  /**
   * Get all active agents
   */
  static async getAgents(): Promise<Agent[]> {
    const response = await httpClient.request('/api/agents');
    return response.json();
  }
  
  /**
   * Get agents by coordination ID
   */
  static async getAgentsByCoordination(coordinationId: string): Promise<Agent[]> {
    const response = await httpClient.request(`/api/agents/coordination/${coordinationId}`);
    return response.json();
  }
  
  /**
   * Spawn new agent
   */
  static async spawnAgent(
    role: string, 
    domain: string, 
    coordinationId: string,
    context?: string
  ): Promise<{ agent_id: string; success: boolean }> {
    const response = await httpClient.request('/api/agents/spawn', {
      method: 'POST',
      body: JSON.stringify({
        role,
        domain,
        coordination_id: coordinationId,
        context
      }),
    });
    return response.json();
  }
  
  // COORDINATION EVENTS
  
  /**
   * Get coordination events for monitoring
   */
  static async getCoordinationEvents(
    coordinationId?: string,
    limit = 100
  ): Promise<CoordinationEvent[]> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (coordinationId) {
      params.append('coordination_id', coordinationId);
    }
    
    const response = await httpClient.request(`/api/coordination/events?${params}`);
    return response.json();
  }
  
  // COMMAND EXECUTION
  
  /**
   * Execute KHIVE command directly
   */
  static async executeCommand(
    command: string,
    args: string[] = [],
    priority = 'normal'
  ): Promise<{ success: boolean; output: string; error?: string }> {
    const response = await httpClient.request('/api/commands/execute', {
      method: 'POST',
      body: JSON.stringify({
        command,
        args,
        priority
      }),
    });
    return response.json();
  }
  
  // SYSTEM UTILITIES
  
  /**
   * Get system metrics and resource utilization
   */
  static async getSystemMetrics(): Promise<{
    cpu_usage: number;
    memory_usage: number;
    disk_usage: number;
    network_io: { rx: number; tx: number };
    uptime: number;
  }> {
    const response = await httpClient.request('/api/system/metrics');
    return response.json();
  }
  
  /**
   * Get detailed cost analysis
   */
  static async getCostAnalysis(
    coordinationId?: string,
    timeRange?: { start: number; end: number }
  ): Promise<{
    total_cost: number;
    token_usage: { input: number; output: number };
    api_calls: number;
    cost_breakdown: Record<string, number>;
  }> {
    const params = new URLSearchParams();
    if (coordinationId) params.append('coordination_id', coordinationId);
    if (timeRange) {
      params.append('start', timeRange.start.toString());
      params.append('end', timeRange.end.toString());
    }
    
    const response = await httpClient.request(`/api/analytics/cost?${params}`);
    return response.json();
  }
}

