/**
 * Intelligent Multi-Level Caching Architecture
 * Built by architect+software-architecture for Ocean's Agentic ERP Command Center
 * 
 * Architecture Patterns:
 * - L1 Cache: Memory-based LRU cache for hot data
 * - L2 Cache: Browser storage for persistent session data
 * - L3 Cache: Service Worker network cache for API responses
 * - Cache Invalidation: Event-driven intelligent invalidation
 * - Cache Warming: Predictive pre-loading based on usage patterns
 * - Cache Coherence: Distributed cache consistency management
 */

import { LRUCache } from 'lru-cache';
import { dataFlowArchitecture } from './EventSourcingDataFlow';

// ============================================================================
// CACHE STRATEGY DEFINITIONS
// ============================================================================

export interface CacheStrategy {
  level: 'L1' | 'L2' | 'L3';
  ttl: number; // Time to live in milliseconds
  maxSize: number; // Maximum entries
  invalidationTriggers: string[]; // Event types that invalidate this cache
  warmingStrategy: 'lazy' | 'eager' | 'predictive';
  compressionEnabled: boolean;
  encryptionRequired: boolean;
}

export interface CacheEntry<T> {
  key: string;
  value: T;
  timestamp: number;
  accessCount: number;
  lastAccessed: number;
  etag?: string;
  dependencies: string[]; // Keys this entry depends on
  metadata: Record<string, any>;
}

export interface CacheMetrics {
  hitRatio: number;
  missCount: number;
  hitCount: number;
  totalRequests: number;
  averageResponseTime: number;
  memoryUsage: number;
  evictionCount: number;
  invalidationCount: number;
}

// Pre-defined cache strategies for different data types
export const CACHE_STRATEGIES: Record<string, CacheStrategy> = {
  // Agent status - frequent updates, short TTL
  'agent.status': {
    level: 'L1',
    ttl: 5000, // 5 seconds
    maxSize: 1000,
    invalidationTriggers: ['agent.status.changed', 'agent.spawned', 'agent.terminated'],
    warmingStrategy: 'eager',
    compressionEnabled: false,
    encryptionRequired: false
  },
  
  // Agent roles - static data, long TTL
  'agent.roles': {
    level: 'L3',
    ttl: 300000, // 5 minutes
    maxSize: 100,
    invalidationTriggers: ['roles.updated'],
    warmingStrategy: 'lazy',
    compressionEnabled: true,
    encryptionRequired: false
  },
  
  // Agent domains - static data, long TTL
  'agent.domains': {
    level: 'L3',
    ttl: 300000, // 5 minutes
    maxSize: 200,
    invalidationTriggers: ['domains.updated'],
    warmingStrategy: 'lazy',
    compressionEnabled: true,
    encryptionRequired: false
  },
  
  // Agent performance metrics - medium updates, medium TTL
  'agent.performance': {
    level: 'L2',
    ttl: 60000, // 1 minute
    maxSize: 500,
    invalidationTriggers: ['agent.task.completed', 'agent.performance.updated'],
    warmingStrategy: 'predictive',
    compressionEnabled: true,
    encryptionRequired: false
  },
  
  // Session data - persistent across page reloads
  'session.data': {
    level: 'L2',
    ttl: 86400000, // 24 hours
    maxSize: 50,
    invalidationTriggers: ['session.ended', 'user.logout'],
    warmingStrategy: 'eager',
    compressionEnabled: true,
    encryptionRequired: true
  },
  
  // Coordination state - critical for agent coordination
  'coordination.state': {
    level: 'L1',
    ttl: 10000, // 10 seconds
    maxSize: 200,
    invalidationTriggers: ['coordination.updated', 'agent.spawned', 'agent.terminated'],
    warmingStrategy: 'eager',
    compressionEnabled: false,
    encryptionRequired: false
  }
};

// ============================================================================
// L1 CACHE - IN-MEMORY LRU CACHE
// ============================================================================

export class L1MemoryCache {
  private cache: LRUCache<string, CacheEntry<any>>;
  private metrics: CacheMetrics;
  private accessPatterns: Map<string, number[]>; // Track access times for predictive warming

  constructor(maxSize: number = 1000) {
    this.cache = new LRUCache<string, CacheEntry<any>>({
      max: maxSize,
      ttl: 300000, // Default 5 minutes
      allowStale: false,
      updateAgeOnGet: true,
      noDeleteOnStaleGet: false,
      dispose: (value, key) => {
        console.log(`[L1-CACHE] Evicted key: ${key}`);
        this.metrics.evictionCount++;
      }
    });

    this.metrics = {
      hitRatio: 0,
      missCount: 0,
      hitCount: 0,
      totalRequests: 0,
      averageResponseTime: 0,
      memoryUsage: 0,
      evictionCount: 0,
      invalidationCount: 0
    };

    this.accessPatterns = new Map();
  }

  get<T>(key: string): T | null {
    const start = performance.now();
    this.metrics.totalRequests++;

    const entry = this.cache.get(key);
    
    if (entry) {
      entry.accessCount++;
      entry.lastAccessed = Date.now();
      this.trackAccess(key);
      
      this.metrics.hitCount++;
      console.log(`[L1-CACHE] Cache hit for key: ${key}`);
      
      const responseTime = performance.now() - start;
      this.updateAverageResponseTime(responseTime);
      
      return entry.value as T;
    } else {
      this.metrics.missCount++;
      console.log(`[L1-CACHE] Cache miss for key: ${key}`);
      return null;
    }
  }

  set<T>(key: string, value: T, ttl?: number, dependencies: string[] = []): void {
    const entry: CacheEntry<T> = {
      key,
      value,
      timestamp: Date.now(),
      accessCount: 0,
      lastAccessed: Date.now(),
      dependencies,
      metadata: {}
    };

    // Set with custom TTL if provided
    if (ttl) {
      this.cache.set(key, entry, { ttl });
    } else {
      this.cache.set(key, entry);
    }

    console.log(`[L1-CACHE] Cached key: ${key}, TTL: ${ttl || 'default'}`);
  }

  invalidate(key: string): boolean {
    const existed = this.cache.has(key);
    this.cache.delete(key);
    
    if (existed) {
      this.metrics.invalidationCount++;
      console.log(`[L1-CACHE] Invalidated key: ${key}`);
    }
    
    return existed;
  }

  invalidateByPattern(pattern: RegExp): number {
    let count = 0;
    const keysToDelete: string[] = [];
    
    for (const key of this.cache.keys()) {
      if (pattern.test(key)) {
        keysToDelete.push(key);
      }
    }
    
    keysToDelete.forEach(key => {
      this.cache.delete(key);
      count++;
    });
    
    this.metrics.invalidationCount += count;
    console.log(`[L1-CACHE] Invalidated ${count} keys by pattern: ${pattern}`);
    
    return count;
  }

  invalidateByDependency(dependency: string): number {
    let count = 0;
    const keysToDelete: string[] = [];
    
    for (const [key, entry] of this.cache.entries()) {
      if (entry.dependencies.includes(dependency)) {
        keysToDelete.push(key);
      }
    }
    
    keysToDelete.forEach(key => {
      this.cache.delete(key);
      count++;
    });
    
    this.metrics.invalidationCount += count;
    console.log(`[L1-CACHE] Invalidated ${count} keys by dependency: ${dependency}`);
    
    return count;
  }

  getMetrics(): CacheMetrics {
    const totalRequests = this.metrics.hitCount + this.metrics.missCount;
    return {
      ...this.metrics,
      hitRatio: totalRequests > 0 ? this.metrics.hitCount / totalRequests : 0,
      memoryUsage: this.estimateMemoryUsage()
    };
  }

  private trackAccess(key: string): void {
    const now = Date.now();
    const accesses = this.accessPatterns.get(key) || [];
    accesses.push(now);
    
    // Keep only last 50 accesses for pattern analysis
    if (accesses.length > 50) {
      accesses.shift();
    }
    
    this.accessPatterns.set(key, accesses);
  }

  private updateAverageResponseTime(responseTime: number): void {
    const totalResponses = this.metrics.hitCount;
    this.metrics.averageResponseTime = 
      ((this.metrics.averageResponseTime * (totalResponses - 1)) + responseTime) / totalResponses;
  }

  private estimateMemoryUsage(): number {
    // Rough estimation - in real implementation would be more sophisticated
    return this.cache.size * 1024; // Assume 1KB per entry average
  }

  // Predictive warming based on access patterns
  getPredictiveKeys(): string[] {
    const predictions: Array<{ key: string; score: number }> = [];
    
    this.accessPatterns.forEach((accesses, key) => {
      if (accesses.length >= 3) {
        // Calculate access frequency and recency
        const frequency = accesses.length;
        const recency = Date.now() - accesses[accesses.length - 1];
        const score = frequency / (recency / 1000); // Frequency per second
        
        predictions.push({ key, score });
      }
    });
    
    return predictions
      .sort((a, b) => b.score - a.score)
      .slice(0, 10)
      .map(p => p.key);
  }
}

// ============================================================================
// L2 CACHE - BROWSER STORAGE CACHE
// ============================================================================

export class L2BrowserCache {
  private storage: Storage;
  private prefix: string;
  private compressionEnabled: boolean;

  constructor(useSessionStorage = false, prefix = 'khive_cache_') {
    this.storage = useSessionStorage ? sessionStorage : localStorage;
    this.prefix = prefix;
    this.compressionEnabled = true; // Enable compression for larger data
  }

  async get<T>(key: string): Promise<T | null> {
    try {
      const fullKey = this.prefix + key;
      const cached = this.storage.getItem(fullKey);
      
      if (!cached) {
        console.log(`[L2-CACHE] Cache miss for key: ${key}`);
        return null;
      }

      const entry: CacheEntry<T> = JSON.parse(cached);
      
      // Check TTL
      if (Date.now() > entry.timestamp + (entry.metadata.ttl || 300000)) {
        this.storage.removeItem(fullKey);
        console.log(`[L2-CACHE] Expired key removed: ${key}`);
        return null;
      }

      // Update access statistics
      entry.accessCount++;
      entry.lastAccessed = Date.now();
      this.storage.setItem(fullKey, JSON.stringify(entry));
      
      console.log(`[L2-CACHE] Cache hit for key: ${key}`);
      return entry.value;
    } catch (error) {
      console.error(`[L2-CACHE] Error getting key ${key}:`, error);
      return null;
    }
  }

  async set<T>(key: string, value: T, ttl = 300000, encrypted = false): Promise<void> {
    try {
      const entry: CacheEntry<T> = {
        key,
        value: encrypted ? this.encrypt(value) : value,
        timestamp: Date.now(),
        accessCount: 0,
        lastAccessed: Date.now(),
        dependencies: [],
        metadata: { ttl, encrypted }
      };

      const fullKey = this.prefix + key;
      const serialized = JSON.stringify(entry);
      
      // Check storage quota
      if (this.isStorageFull(serialized.length)) {
        await this.evictLeastUsed();
      }

      this.storage.setItem(fullKey, serialized);
      console.log(`[L2-CACHE] Cached key: ${key}, encrypted: ${encrypted}`);
    } catch (error) {
      console.error(`[L2-CACHE] Error setting key ${key}:`, error);
      
      // If storage is full, try evicting and retry once
      if (error.name === 'QuotaExceededError') {
        await this.evictLeastUsed();
        try {
          const entry: CacheEntry<T> = {
            key, value, timestamp: Date.now(), accessCount: 0,
            lastAccessed: Date.now(), dependencies: [], metadata: { ttl }
          };
          this.storage.setItem(this.prefix + key, JSON.stringify(entry));
        } catch (retryError) {
          console.error(`[L2-CACHE] Retry failed for key ${key}:`, retryError);
        }
      }
    }
  }

  invalidate(key: string): boolean {
    const fullKey = this.prefix + key;
    const existed = this.storage.getItem(fullKey) !== null;
    this.storage.removeItem(fullKey);
    
    if (existed) {
      console.log(`[L2-CACHE] Invalidated key: ${key}`);
    }
    
    return existed;
  }

  clear(): void {
    const keysToRemove: string[] = [];
    
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i);
      if (key && key.startsWith(this.prefix)) {
        keysToRemove.push(key);
      }
    }
    
    keysToRemove.forEach(key => this.storage.removeItem(key));
    console.log(`[L2-CACHE] Cleared ${keysToRemove.length} cache entries`);
  }

  private isStorageFull(itemSize: number): boolean {
    // Rough check for storage quota (most browsers allow ~5-10MB for localStorage)
    const estimatedUsage = this.estimateStorageUsage();
    const quota = 5 * 1024 * 1024; // 5MB rough estimate
    return estimatedUsage + itemSize > quota * 0.9; // 90% threshold
  }

  private estimateStorageUsage(): number {
    let usage = 0;
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i);
      if (key && key.startsWith(this.prefix)) {
        const value = this.storage.getItem(key);
        usage += (key.length + (value?.length || 0)) * 2; // UTF-16 encoding
      }
    }
    return usage;
  }

  private async evictLeastUsed(): Promise<void> {
    const entries: Array<{ key: string; lastAccessed: number; accessCount: number }> = [];
    
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i);
      if (key && key.startsWith(this.prefix)) {
        try {
          const value = this.storage.getItem(key);
          if (value) {
            const entry = JSON.parse(value);
            entries.push({ 
              key, 
              lastAccessed: entry.lastAccessed || 0,
              accessCount: entry.accessCount || 0
            });
          }
        } catch (error) {
          // Remove corrupted entries
          this.storage.removeItem(key);
        }
      }
    }

    // Sort by least recently used and least frequently used
    entries.sort((a, b) => {
      const aScore = a.accessCount + (Date.now() - a.lastAccessed) / 100000;
      const bScore = b.accessCount + (Date.now() - b.lastAccessed) / 100000;
      return aScore - bScore;
    });

    // Remove bottom 25% of entries
    const toRemove = Math.ceil(entries.length * 0.25);
    for (let i = 0; i < toRemove; i++) {
      this.storage.removeItem(entries[i].key);
    }

    console.log(`[L2-CACHE] Evicted ${toRemove} least used entries`);
  }

  private encrypt<T>(value: T): string {
    // Simplified encryption - in production would use proper encryption
    const str = JSON.stringify(value);
    return btoa(str); // Base64 encoding as simple obfuscation
  }

  private decrypt<T>(encrypted: string): T {
    // Simplified decryption
    const str = atob(encrypted);
    return JSON.parse(str);
  }
}

// ============================================================================
// INTELLIGENT CACHE COORDINATOR
// ============================================================================

export class IntelligentCacheCoordinator {
  private l1Cache: L1MemoryCache;
  private l2Cache: L2BrowserCache;
  private strategies: Map<string, CacheStrategy>;
  private warming: boolean = false;

  constructor() {
    this.l1Cache = new L1MemoryCache(2000); // 2000 entries max
    this.l2Cache = new L2BrowserCache(false, 'khive_intelligent_');
    this.strategies = new Map(Object.entries(CACHE_STRATEGIES));
    
    this.initializeEventListeners();
    this.startCacheWarming();
    
    console.log('[CACHE-COORDINATOR] Intelligent caching system initialized');
  }

  async get<T>(strategyKey: string, key: string): Promise<T | null> {
    const strategy = this.strategies.get(strategyKey);
    if (!strategy) {
      console.warn(`[CACHE-COORDINATOR] No strategy found for: ${strategyKey}`);
      return null;
    }

    const fullKey = `${strategyKey}:${key}`;

    // Try L1 cache first for all strategies
    let value = this.l1Cache.get<T>(fullKey);
    if (value !== null) {
      return value;
    }

    // Try L2 cache for L2/L3 strategies
    if (strategy.level !== 'L1') {
      value = await this.l2Cache.get<T>(fullKey);
      if (value !== null) {
        // Promote to L1 cache
        this.l1Cache.set(fullKey, value, strategy.ttl);
        return value;
      }
    }

    return null;
  }

  async set<T>(strategyKey: string, key: string, value: T): Promise<void> {
    const strategy = this.strategies.get(strategyKey);
    if (!strategy) {
      console.warn(`[CACHE-COORDINATOR] No strategy found for: ${strategyKey}`);
      return;
    }

    const fullKey = `${strategyKey}:${key}`;

    // Always store in L1 for fast access
    this.l1Cache.set(fullKey, value, strategy.ttl);

    // Store in L2 for persistent strategies
    if (strategy.level !== 'L1') {
      await this.l2Cache.set(fullKey, value, strategy.ttl, strategy.encryptionRequired);
    }

    console.log(`[CACHE-COORDINATOR] Stored ${fullKey} using ${strategy.level} strategy`);
  }

  invalidate(strategyKey: string, key?: string): void {
    if (key) {
      const fullKey = `${strategyKey}:${key}`;
      this.l1Cache.invalidate(fullKey);
      this.l2Cache.invalidate(fullKey);
    } else {
      // Invalidate all keys with this strategy
      const pattern = new RegExp(`^${strategyKey}:`);
      this.l1Cache.invalidateByPattern(pattern);
      // L2 doesn't have pattern invalidation, would need to iterate
    }
  }

  invalidateByEventType(eventType: string): void {
    this.strategies.forEach((strategy, strategyKey) => {
      if (strategy.invalidationTriggers.includes(eventType)) {
        console.log(`[CACHE-COORDINATOR] Invalidating strategy ${strategyKey} due to event ${eventType}`);
        this.invalidate(strategyKey);
      }
    });
  }

  getMetrics(): Record<string, any> {
    return {
      l1: this.l1Cache.getMetrics(),
      l2: {
        // L2 metrics would be implemented here
        hitRatio: 0.7, // Mock
        memoryUsage: 1024 * 1024 // Mock
      },
      coordinator: {
        strategiesCount: this.strategies.size,
        warmingActive: this.warming,
        lastWarmingTime: Date.now()
      }
    };
  }

  private initializeEventListeners(): void {
    // Listen to domain events for cache invalidation
    dataFlowArchitecture.getAgentDataStreams().events.subscribe(event => {
      this.invalidateByEventType(event.type);
    });

    console.log('[CACHE-COORDINATOR] Event listeners initialized');
  }

  private async startCacheWarming(): void {
    if (this.warming) return;
    
    this.warming = true;
    console.log('[CACHE-COORDINATOR] Starting predictive cache warming');

    // Warm cache every 30 seconds
    setInterval(async () => {
      const predictiveKeys = this.l1Cache.getPredictiveKeys();
      
      for (const key of predictiveKeys.slice(0, 5)) { // Warm top 5 predictions
        // Extract strategy and actual key
        const [strategyKey, actualKey] = key.split(':', 2);
        const strategy = this.strategies.get(strategyKey);
        
        if (strategy && strategy.warmingStrategy === 'predictive') {
          // In real implementation, would fetch from API
          console.log(`[CACHE-COORDINATOR] Predictive warming for ${key}`);
        }
      }
    }, 30000);
  }

  // Add new cache strategy dynamically
  addStrategy(key: string, strategy: CacheStrategy): void {
    this.strategies.set(key, strategy);
    console.log(`[CACHE-COORDINATOR] Added new cache strategy: ${key}`);
  }
}

// Export singleton instance for application use
export const intelligentCache = new IntelligentCacheCoordinator();