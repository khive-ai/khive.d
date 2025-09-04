/**
 * React Hooks for Intelligent Multi-Level Caching
 * Built by architect+software-architecture for Ocean's Agentic ERP Command Center
 * 
 * Provides optimized React integration with intelligent caching:
 * - Automatic cache strategy selection
 * - Cache-aware query optimization
 * - Background cache warming
 * - Cache metrics and debugging
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { intelligentCache, CacheMetrics } from '../architecture/IntelligentCaching';

// ============================================================================
// CORE CACHING HOOKS
// ============================================================================

/**
 * Enhanced useQuery with intelligent caching
 */
interface UseCachedQueryOptions {
  cacheStrategy?: string;
  enabled?: boolean;
  refetchOnWindowFocus?: boolean;
  refetchInterval?: number | false;
  staleTime?: number;
  onCacheHit?: (data: any) => void;
  onCacheMiss?: () => void;
}

export function useCachedQuery<TData>(
  queryKey: string[],
  queryFn: () => Promise<TData>,
  options: UseCachedQueryOptions = {}
) {
  const {
    cacheStrategy = queryKey[0],
    enabled = true,
    refetchOnWindowFocus = false,
    refetchInterval = false,
    staleTime = 30000,
    onCacheHit,
    onCacheMiss
  } = options;

  const [cacheHit, setCacheHit] = useState(false);
  const queryClient = useQueryClient();

  // Enhanced query function that checks cache first
  const enhancedQueryFn = useCallback(async (): Promise<TData> => {
    const cacheKey = queryKey.join(':');
    
    console.log(`[USE-CACHED-QUERY] Checking cache for: ${cacheKey}`);
    
    // Check intelligent cache first
    const cachedData = await intelligentCache.get<TData>(cacheStrategy, cacheKey);
    
    if (cachedData !== null) {
      console.log(`[USE-CACHED-QUERY] Cache hit for: ${cacheKey}`);
      setCacheHit(true);
      onCacheHit?.(cachedData);
      return cachedData;
    }

    console.log(`[USE-CACHED-QUERY] Cache miss for: ${cacheKey}, fetching from source`);
    setCacheHit(false);
    onCacheMiss?.();
    
    // Fetch from source
    const freshData = await queryFn();
    
    // Store in intelligent cache
    await intelligentCache.set(cacheStrategy, cacheKey, freshData);
    console.log(`[USE-CACHED-QUERY] Cached fresh data for: ${cacheKey}`);
    
    return freshData;
  }, [queryKey.join(':'), cacheStrategy, queryFn, onCacheHit, onCacheMiss]);

  const query = useQuery({
    queryKey,
    queryFn: enhancedQueryFn,
    enabled,
    refetchOnWindowFocus,
    refetchInterval,
    staleTime,
    // Optimize React Query behavior for caching
    gcTime: staleTime * 2, // Keep in memory longer if we have cache
    retry: (failureCount, error) => {
      // Don't retry if we have cached data
      return !cacheHit && failureCount < 3;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)
  });

  // Cache invalidation helper
  const invalidateCache = useCallback(() => {
    const cacheKey = queryKey.join(':');
    intelligentCache.invalidate(cacheStrategy, cacheKey);
    queryClient.invalidateQueries({ queryKey });
    console.log(`[USE-CACHED-QUERY] Invalidated cache for: ${cacheKey}`);
  }, [queryKey.join(':'), cacheStrategy, queryClient]);

  return {
    ...query,
    cacheHit,
    invalidateCache,
    cacheStrategy
  };
}

/**
 * Hook for prefetching data with intelligent caching
 */
export function useCachePrefetch() {
  const queryClient = useQueryClient();

  const prefetch = useCallback(async <TData>(
    queryKey: string[],
    queryFn: () => Promise<TData>,
    cacheStrategy: string = queryKey[0]
  ) => {
    const cacheKey = queryKey.join(':');
    
    // Check if already cached
    const cached = await intelligentCache.get<TData>(cacheStrategy, cacheKey);
    if (cached !== null) {
      console.log(`[USE-CACHE-PREFETCH] Data already cached: ${cacheKey}`);
      return;
    }

    console.log(`[USE-CACHE-PREFETCH] Prefetching: ${cacheKey}`);
    
    try {
      // Prefetch without triggering UI updates
      queryClient.prefetchQuery({
        queryKey,
        queryFn: async () => {
          const data = await queryFn();
          await intelligentCache.set(cacheStrategy, cacheKey, data);
          return data;
        },
        staleTime: 60000 // Consider prefetched data fresh for 1 minute
      });
    } catch (error) {
      console.error(`[USE-CACHE-PREFETCH] Failed to prefetch ${cacheKey}:`, error);
    }
  }, [queryClient]);

  const prefetchBatch = useCallback(async (
    prefetchItems: Array<{
      queryKey: string[];
      queryFn: () => Promise<any>;
      cacheStrategy?: string;
    }>
  ) => {
    console.log(`[USE-CACHE-PREFETCH] Batch prefetching ${prefetchItems.length} items`);
    
    const promises = prefetchItems.map(item => 
      prefetch(item.queryKey, item.queryFn, item.cacheStrategy)
    );
    
    await Promise.allSettled(promises);
  }, [prefetch]);

  return {
    prefetch,
    prefetchBatch
  };
}

// ============================================================================
// SPECIALIZED CACHING HOOKS
// ============================================================================

/**
 * Hook for caching agent status data with real-time updates
 */
export function useCachedAgentStatus(agentId: string) {
  const { data, isLoading, error, cacheHit, invalidateCache } = useCachedQuery(
    ['agent.status', agentId],
    async () => {
      // Mock API call - would be real API in production
      console.log(`[CACHED-AGENT-STATUS] Fetching status for agent: ${agentId}`);
      await new Promise(resolve => setTimeout(resolve, 100)); // Simulate network delay
      
      return {
        agent_id: agentId,
        status: 'active',
        current_task: `Processing task for ${agentId}`,
        progress: Math.random(),
        last_activity: Date.now()
      };
    },
    {
      cacheStrategy: 'agent.status',
      refetchInterval: 5000, // Refresh every 5 seconds
      staleTime: 2500, // Consider stale after 2.5 seconds
      onCacheHit: () => console.log(`[CACHED-AGENT-STATUS] Served from cache: ${agentId}`),
      onCacheMiss: () => console.log(`[CACHED-AGENT-STATUS] Fetching fresh data: ${agentId}`)
    }
  );

  return {
    agentStatus: data,
    isLoading,
    error,
    cacheHit,
    invalidateStatus: invalidateCache
  };
}

/**
 * Hook for caching role and domain data (static data with long TTL)
 */
export function useCachedRolesAndDomains() {
  const roles = useCachedQuery(
    ['agent.roles'],
    async () => {
      console.log('[CACHED-ROLES] Fetching roles from API');
      // Mock API call
      return [
        { id: 'implementer', name: 'Implementer', description: 'Builds and deploys systems' },
        { id: 'researcher', name: 'Researcher', description: 'Discovers and analyzes information' },
        { id: 'architect', name: 'Architect', description: 'Designs system architecture' }
      ];
    },
    {
      cacheStrategy: 'agent.roles',
      staleTime: 300000, // 5 minutes
      refetchOnWindowFocus: false
    }
  );

  const domains = useCachedQuery(
    ['agent.domains'],
    async () => {
      console.log('[CACHED-DOMAINS] Fetching domains from API');
      // Mock API call
      return [
        { id: 'agentic-systems', name: 'Agentic Systems', type: 'research' },
        { id: 'software-architecture', name: 'Software Architecture', type: 'technical' }
      ];
    },
    {
      cacheStrategy: 'agent.domains',
      staleTime: 300000, // 5 minutes
      refetchOnWindowFocus: false
    }
  );

  return {
    roles: roles.data,
    domains: domains.data,
    isLoadingRoles: roles.isLoading,
    isLoadingDomains: domains.isLoading,
    rolesError: roles.error,
    domainsError: domains.error,
    rolesCacheHit: roles.cacheHit,
    domainsCacheHit: domains.cacheHit
  };
}

/**
 * Hook for caching session data with persistence
 */
export function useCachedSessionData(sessionId: string) {
  const { data, isLoading, error, invalidateCache } = useCachedQuery(
    ['session.data', sessionId],
    async () => {
      console.log(`[CACHED-SESSION] Fetching session data: ${sessionId}`);
      return {
        sessionId,
        userId: 'ocean',
        startTime: Date.now(),
        preferences: {
          theme: 'dark',
          language: 'en',
          autoSave: true
        },
        agentHistory: [],
        lastActivity: Date.now()
      };
    },
    {
      cacheStrategy: 'session.data',
      staleTime: 86400000, // 24 hours
      refetchOnWindowFocus: false
    }
  );

  const updateSessionData = useCallback(async (updates: Partial<any>) => {
    if (!data) return;
    
    const updatedData = { ...data, ...updates, lastActivity: Date.now() };
    await intelligentCache.set('session.data', `session.data:${sessionId}`, updatedData);
    
    // Invalidate to trigger re-fetch with updated data
    invalidateCache();
  }, [data, sessionId, invalidateCache]);

  return {
    sessionData: data,
    isLoading,
    error,
    updateSessionData
  };
}

// ============================================================================
// CACHE MONITORING AND OPTIMIZATION HOOKS
// ============================================================================

/**
 * Hook for monitoring cache performance and metrics
 */
export function useCacheMetrics() {
  const [metrics, setMetrics] = useState<Record<string, any>>({});
  const [isMonitoring, setIsMonitoring] = useState(false);

  useEffect(() => {
    if (!isMonitoring) return;

    const interval = setInterval(() => {
      const newMetrics = intelligentCache.getMetrics();
      setMetrics(newMetrics);
      console.log('[CACHE-METRICS] Updated cache metrics:', newMetrics);
    }, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, [isMonitoring]);

  const startMonitoring = useCallback(() => {
    setIsMonitoring(true);
    console.log('[CACHE-METRICS] Started monitoring cache metrics');
  }, []);

  const stopMonitoring = useCallback(() => {
    setIsMonitoring(false);
    console.log('[CACHE-METRICS] Stopped monitoring cache metrics');
  }, []);

  const getOverallHitRatio = useCallback(() => {
    if (!metrics.l1 || !metrics.l2) return 0;
    
    const totalHits = (metrics.l1.hitCount || 0) + (metrics.l2.hitCount || 0);
    const totalRequests = (metrics.l1.totalRequests || 0) + (metrics.l2.totalRequests || 0);
    
    return totalRequests > 0 ? totalHits / totalRequests : 0;
  }, [metrics]);

  return {
    metrics,
    isMonitoring,
    startMonitoring,
    stopMonitoring,
    overallHitRatio: getOverallHitRatio()
  };
}

/**
 * Hook for cache warming and optimization
 */
export function useCacheOptimization() {
  const [isOptimizing, setIsOptimizing] = useState(false);
  const { prefetchBatch } = useCachePrefetch();

  const warmEssentialCaches = useCallback(async () => {
    setIsOptimizing(true);
    console.log('[CACHE-OPTIMIZATION] Starting essential cache warming');

    try {
      await prefetchBatch([
        {
          queryKey: ['agent.roles'],
          queryFn: async () => {
            // Mock roles data
            return [
              { id: 'implementer', name: 'Implementer' },
              { id: 'researcher', name: 'Researcher' },
              { id: 'architect', name: 'Architect' }
            ];
          },
          cacheStrategy: 'agent.roles'
        },
        {
          queryKey: ['agent.domains'],
          queryFn: async () => {
            // Mock domains data
            return [
              { id: 'agentic-systems', name: 'Agentic Systems' },
              { id: 'software-architecture', name: 'Software Architecture' }
            ];
          },
          cacheStrategy: 'agent.domains'
        }
      ]);

      console.log('[CACHE-OPTIMIZATION] Essential cache warming completed');
    } catch (error) {
      console.error('[CACHE-OPTIMIZATION] Cache warming failed:', error);
    } finally {
      setIsOptimizing(false);
    }
  }, [prefetchBatch]);

  const clearAllCaches = useCallback(() => {
    // Clear intelligent cache
    intelligentCache.invalidate('agent.status');
    intelligentCache.invalidate('agent.roles');
    intelligentCache.invalidate('agent.domains');
    intelligentCache.invalidate('session.data');
    intelligentCache.invalidate('coordination.state');
    
    console.log('[CACHE-OPTIMIZATION] All caches cleared');
  }, []);

  const optimizeMemoryUsage = useCallback(() => {
    console.log('[CACHE-OPTIMIZATION] Starting memory optimization');
    
    // In a real implementation, this would:
    // 1. Analyze cache hit ratios
    // 2. Identify least-used entries
    // 3. Adjust cache sizes dynamically
    // 4. Compress data where beneficial
    
    // For now, just log the optimization attempt
    const metrics = intelligentCache.getMetrics();
    console.log('[CACHE-OPTIMIZATION] Current memory usage:', metrics.l1?.memoryUsage || 0);
  }, []);

  return {
    isOptimizing,
    warmEssentialCaches,
    clearAllCaches,
    optimizeMemoryUsage
  };
}

// ============================================================================
// DEBUGGING AND DEVELOPMENT HOOKS
// ============================================================================

/**
 * Hook for debugging cache behavior (development only)
 */
export function useCacheDebug() {
  const [debugInfo, setDebugInfo] = useState({
    totalCacheHits: 0,
    totalCacheMisses: 0,
    averageResponseTime: 0,
    memoryUsage: 0,
    lastActivity: null as number | null
  });

  const [isDebugging, setIsDebugging] = useState(false);

  useEffect(() => {
    if (!isDebugging || process.env.NODE_ENV === 'production') return;

    const interval = setInterval(() => {
      const metrics = intelligentCache.getMetrics();
      
      setDebugInfo({
        totalCacheHits: (metrics.l1?.hitCount || 0) + (metrics.l2?.hitCount || 0),
        totalCacheMisses: (metrics.l1?.missCount || 0) + (metrics.l2?.missCount || 0),
        averageResponseTime: metrics.l1?.averageResponseTime || 0,
        memoryUsage: (metrics.l1?.memoryUsage || 0) + (metrics.l2?.memoryUsage || 0),
        lastActivity: Date.now()
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [isDebugging]);

  const logCacheState = useCallback(() => {
    const metrics = intelligentCache.getMetrics();
    console.group('[CACHE-DEBUG] Current Cache State');
    console.log('Metrics:', metrics);
    console.log('Debug Info:', debugInfo);
    console.groupEnd();
  }, [debugInfo]);

  return {
    debugInfo,
    isDebugging,
    startDebugging: () => setIsDebugging(true),
    stopDebugging: () => setIsDebugging(false),
    logCacheState
  };
}

// Export convenience functions
export const cacheUtils = {
  invalidateAgentData: (agentId: string) => {
    intelligentCache.invalidate('agent.status', `agent.status:${agentId}`);
    intelligentCache.invalidate('agent.performance', `agent.performance:${agentId}`);
  },
  
  invalidateAllAgentData: () => {
    intelligentCache.invalidate('agent.status');
    intelligentCache.invalidate('agent.performance');
  },
  
  preloadEssentials: async () => {
    // Would implement essential data preloading here
    console.log('[CACHE-UTILS] Preloading essential data');
  }
};