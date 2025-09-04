// Optimized agent composition services with architectural performance patterns
// Built by architect+software-architecture for Ocean's Agentic ERP Command Center

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect, useRef, useCallback } from 'react';
import { 
  AgentRealTimeStatus,
  AgentComposition,
  AgentSpawnRequest,
  DataFlowPattern,
  StreamProcessor,
  StateSync
} from '../types/agent-composition';

// ============================================================================
// ARCHITECTURAL PATTERNS: Advanced Query Optimization
// ============================================================================

/**
 * Batch Query Pattern: Eliminates N+1 query problems
 * Architecture: Single request for multiple agent statuses with intelligent batching
 */
export interface BatchQueryOptions {
  batchSize?: number;
  enabled?: boolean;
  refetchInterval?: number | false;
  staleTime?: number;
}

export interface BatchAgentStatusResponse {
  agents: AgentRealTimeStatus[];
  metadata: {
    total_count: number;
    batch_id: string;
    timestamp: number;
    cache_hit_ratio: number;
  };
}

/**
 * Optimized batch agent status query with intelligent caching
 */
export const useBatchAgentStatus = (
  agentIds: string[], 
  options: BatchQueryOptions = {}
) => {
  const {
    batchSize = 50,
    enabled = true,
    refetchInterval = 5000,
    staleTime = 2500
  } = options;

  return useQuery({
    queryKey: ['batch-agent-status', agentIds.sort().join(',')],
    queryFn: async (): Promise<AgentRealTimeStatus[]> => {
      // TODO: Replace with actual batch API endpoint
      // POST /api/khive/agents/batch-status
      // Body: { agent_ids: string[], batch_size: number }
      
      console.log(`[ARCH] Batch fetching status for ${agentIds.length} agents`);
      
      // Simulate batch API response with performance optimizations
      const batchResponse: BatchAgentStatusResponse = await simulateBatchAgentStatus(agentIds, batchSize);
      
      console.log(`[ARCH] Batch response: ${batchResponse.agents.length} agents, cache hit ratio: ${(batchResponse.metadata.cache_hit_ratio * 100).toFixed(1)}%`);
      
      return batchResponse.agents;
    },
    enabled: enabled && agentIds.length > 0,
    refetchInterval,
    staleTime,
    // Performance optimizations
    refetchOnWindowFocus: false,
    refetchOnMount: true,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    // Advanced caching strategy
    structuralSharing: (oldData, newData) => {
      if (!oldData || !newData) return newData;
      
      // Only update agents that actually changed to prevent unnecessary re-renders
      const hasChanges = oldData.some((oldAgent, index) => {
        const newAgent = newData[index];
        return !newAgent || 
               oldAgent.status !== newAgent.status ||
               oldAgent.progress !== newAgent.progress ||
               oldAgent.last_activity !== newAgent.last_activity;
      });
      
      return hasChanges ? newData : oldData;
    }
  });
};

// ============================================================================
// ARCHITECTURAL PATTERNS: Real-time Event Architecture
// ============================================================================

/**
 * Real-time Subscription Pattern: WebSocket/SSE architecture for live updates
 * Architecture: Event-driven updates with connection management and fallback
 */
export interface SubscriptionOptions {
  enabled?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export interface ConnectionStatus {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastConnected?: number;
  reconnectAttempts: number;
}

/**
 * Real-time agent status subscription with connection management
 */
export const useAgentStatusSubscription = (
  agentIds: string[],
  options: SubscriptionOptions = {}
) => {
  const {
    enabled = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5
  } = options;

  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus['status']>('disconnected');
  const [lastUpdate, setLastUpdate] = useState<number | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const queryClient = useQueryClient();

  const connect = useCallback(() => {
    if (!enabled || agentIds.length === 0) return;

    setConnectionStatus('connecting');
    
    // TODO: Replace with actual WebSocket endpoint
    // const wsUrl = `/ws/khive/agents/status?agents=${agentIds.join(',')}`;
    
    // For now, simulate WebSocket connection
    console.log(`[ARCH] Establishing WebSocket connection for ${agentIds.length} agents`);
    
    // Simulate connection success
    setTimeout(() => {
      setConnectionStatus('connected');
      setLastUpdate(Date.now());
      setReconnectAttempts(0);
      
      // Simulate periodic updates
      const interval = setInterval(() => {
        setLastUpdate(Date.now());
        
        // Invalidate cache to trigger refresh with new data
        queryClient.invalidateQueries({ queryKey: ['batch-agent-status'] });
        
        console.log('[ARCH] Real-time agent status update received');
      }, 10000); // Update every 10 seconds

      // Store cleanup function
      wsRef.current = { close: () => clearInterval(interval) } as any;
      
    }, 1000);

  }, [enabled, agentIds, queryClient]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    setConnectionStatus('disconnected');
  }, []);

  const reconnect = useCallback(() => {
    if (reconnectAttempts >= maxReconnectAttempts) {
      console.warn('[ARCH] Max reconnect attempts reached');
      setConnectionStatus('error');
      return;
    }

    setReconnectAttempts(prev => prev + 1);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      console.log(`[ARCH] Attempting reconnection (${reconnectAttempts + 1}/${maxReconnectAttempts})`);
      connect();
    }, reconnectInterval);
    
  }, [reconnectAttempts, maxReconnectAttempts, reconnectInterval, connect]);

  // Connection lifecycle management
  useEffect(() => {
    if (enabled && agentIds.length > 0) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [enabled, agentIds.length, connect, disconnect]);

  // Handle connection errors and reconnection
  useEffect(() => {
    if (connectionStatus === 'error' && reconnectAttempts < maxReconnectAttempts) {
      reconnect();
    }
  }, [connectionStatus, reconnectAttempts, maxReconnectAttempts, reconnect]);

  return {
    connectionStatus,
    lastUpdate,
    reconnectAttempts,
    connect,
    disconnect
  };
};

// ============================================================================
// ARCHITECTURAL PATTERNS: Intelligent Caching Layer
// ============================================================================

/**
 * Multi-level caching strategy for agent data
 * Architecture: L1 (Memory) + L2 (Browser) + L3 (CDN) caching
 */
interface CacheStrategy {
  level: 'memory' | 'browser' | 'cdn';
  ttl: number;
  invalidation: 'time' | 'event' | 'manual';
}

const CACHE_STRATEGIES: Record<string, CacheStrategy> = {
  agent_roles: { level: 'cdn', ttl: 300000, invalidation: 'time' }, // 5 minutes
  agent_domains: { level: 'cdn', ttl: 300000, invalidation: 'time' },
  agent_status: { level: 'memory', ttl: 5000, invalidation: 'event' }, // 5 seconds
  agent_performance: { level: 'browser', ttl: 60000, invalidation: 'time' }, // 1 minute
};

/**
 * Optimized caching hook with intelligent invalidation
 */
export const useCachedQuery = <T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  cacheStrategy?: CacheStrategy
) => {
  const strategy = cacheStrategy || CACHE_STRATEGIES[queryKey[0]] || {
    level: 'memory',
    ttl: 30000,
    invalidation: 'time'
  };

  return useQuery({
    queryKey,
    queryFn,
    staleTime: strategy.ttl,
    cacheTime: strategy.level === 'memory' ? strategy.ttl : strategy.ttl * 2,
    refetchOnWindowFocus: strategy.level === 'memory',
    // Advanced cache invalidation based on strategy
    refetchInterval: strategy.invalidation === 'time' ? strategy.ttl : false,
  });
};

// ============================================================================
// ARCHITECTURAL PATTERNS: Stream Processing Architecture  
// ============================================================================

/**
 * Data Flow Stream Processing Pattern
 * Architecture: Event-driven data processing with backpressure handling
 */
export interface StreamProcessingMetrics {
  throughput: number;
  latency: number;
  error_rate: number;
  backpressure_events: number;
}

export const useStreamProcessingMetrics = () => {
  return useQuery({
    queryKey: ['stream-processing-metrics'],
    queryFn: async (): Promise<StreamProcessingMetrics> => {
      // TODO: Replace with actual stream metrics API
      return {
        throughput: Math.floor(Math.random() * 1000) + 500,
        latency: Math.floor(Math.random() * 100) + 20,
        error_rate: Math.random() * 0.05,
        backpressure_events: Math.floor(Math.random() * 10)
      };
    },
    refetchInterval: 5000,
    staleTime: 2500,
  });
};

// ============================================================================
// ARCHITECTURAL PATTERNS: Performance Optimization Utilities
// ============================================================================

/**
 * Request batching utility for reducing network overhead
 */
class RequestBatcher {
  private batches: Map<string, {
    requests: Array<{ resolve: Function; reject: Function; data: any }>;
    timeout: NodeJS.Timeout;
  }> = new Map();

  batch<T>(
    key: string, 
    requestData: any, 
    batchHandler: (requests: any[]) => Promise<T[]>,
    batchWindow = 100
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const batch = this.batches.get(key);
      
      if (batch) {
        batch.requests.push({ resolve, reject, data: requestData });
      } else {
        const newBatch = {
          requests: [{ resolve, reject, data: requestData }],
          timeout: setTimeout(async () => {
            const currentBatch = this.batches.get(key);
            if (currentBatch) {
              this.batches.delete(key);
              
              try {
                const results = await batchHandler(
                  currentBatch.requests.map(req => req.data)
                );
                
                currentBatch.requests.forEach((req, index) => {
                  req.resolve(results[index]);
                });
              } catch (error) {
                currentBatch.requests.forEach(req => req.reject(error));
              }
            }
          }, batchWindow)
        };
        
        this.batches.set(key, newBatch);
      }
    });
  }
}

export const requestBatcher = new RequestBatcher();

// ============================================================================
// MOCK DATA GENERATION (Development Only)
// ============================================================================

/**
 * Simulate batch agent status API with realistic performance characteristics
 */
async function simulateBatchAgentStatus(
  agentIds: string[], 
  batchSize: number
): Promise<BatchAgentStatusResponse> {
  // Simulate network latency based on batch size
  const latency = Math.min(50 + (agentIds.length * 2), 500);
  await new Promise(resolve => setTimeout(resolve, latency));

  const agents = agentIds.map((agentId): AgentRealTimeStatus => ({
    agent_id: agentId,
    status: ['active', 'working', 'idle', 'completed'][Math.floor(Math.random() * 4)] as any,
    current_task: `Processing task for ${agentId}`,
    progress: Math.random(),
    resource_usage: {
      cpu: Math.floor(Math.random() * 80) + 10,
      memory: Math.floor(Math.random() * 400) + 100,
      tokens_used: Math.floor(Math.random() * 5000) + 1000,
      api_calls: Math.floor(Math.random() * 50) + 10
    },
    performance_metrics: {
      tasks_completed: Math.floor(Math.random() * 20) + 1,
      avg_task_time: Math.floor(Math.random() * 3600) + 600,
      success_rate: 0.7 + Math.random() * 0.3,
      cost: Math.random() * 5 + 1
    },
    coordination: {
      locks_held: Math.random() > 0.7 ? [`/workspace/${agentId}`] : [],
      waiting_for: Math.random() > 0.8 ? ['dependency_agent'] : [],
      conflicts: []
    },
    last_activity: Date.now() - Math.floor(Math.random() * 300000) // 0-5 minutes ago
  }));

  return {
    agents,
    metadata: {
      total_count: agents.length,
      batch_id: `batch_${Date.now()}`,
      timestamp: Date.now(),
      cache_hit_ratio: Math.random() * 0.4 + 0.3 // 30-70% cache hit ratio
    }
  };
}

/**
 * Export optimized service functions for compatibility with existing code
 */
export const optimizedAgentCompositionServices = {
  useBatchAgentStatus,
  useAgentStatusSubscription,
  useCachedQuery,
  useStreamProcessingMetrics,
  requestBatcher
};