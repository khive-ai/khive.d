import { useState, useEffect, useCallback, useRef } from 'react';
import { OrchestrationSession, SessionFilter, SessionGroup } from '@/lib/types/khive';

interface PersistedSessionData {
  sessions: OrchestrationSession[];
  groups: SessionGroup[];
  filters: SessionFilter;
  activeSessionId?: string;
  favoriteCoordinationIds: string[];
  costBudgets: Record<string, number>;
  lastUpdate: number;
  version: string;
}

interface SessionPersistenceOptions {
  storageKey?: string;
  syncAcrossTabs?: boolean;
  maxStorageSize?: number; // in bytes
  autoSave?: boolean;
  saveInterval?: number; // in milliseconds
  enableCompression?: boolean;
}

/**
 * useSessionPersistence - Browser storage management for session state
 * 
 * Features:
 * - Persistent session data across browser restarts
 * - Tab synchronization for multi-window workflows
 * - Configurable storage limits and cleanup
 * - Data compression for large session datasets
 * - Conflict resolution for concurrent updates
 * - Recovery from corrupted storage
 */
export function useSessionPersistence(options: SessionPersistenceOptions = {}) {
  const {
    storageKey = 'khive_session_data',
    syncAcrossTabs = true,
    maxStorageSize = 5 * 1024 * 1024, // 5MB default
    autoSave = true,
    saveInterval = 10000, // 10 seconds
    enableCompression = true
  } = options;

  const [persistedData, setPersistedData] = useState<PersistedSessionData>(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Validate version compatibility
        if (parsed.version === '1.0') {
          return {
            ...parsed,
            lastUpdate: Date.now()
          };
        }
      }
    } catch (error) {
      console.warn('Failed to load persisted session data:', error);
    }

    // Return default structure
    return {
      sessions: [],
      groups: [],
      filters: {},
      favoriteCoordinationIds: [],
      costBudgets: {},
      lastUpdate: Date.now(),
      version: '1.0'
    };
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastSaveRef = useRef<number>(Date.now());

  // Compress data if enabled
  const compressData = useCallback((data: string): string => {
    if (!enableCompression) return data;
    
    // Simple compression: remove extra whitespace and use shorter keys
    return data
      .replace(/\s+/g, ' ')
      .replace(/"/g, "'")
      .trim();
  }, [enableCompression]);

  // Decompress data if needed
  const decompressData = useCallback((data: string): string => {
    if (!enableCompression) return data;
    
    // Reverse compression
    return data.replace(/'/g, '"');
  }, [enableCompression]);

  // Calculate storage size
  const getStorageSize = useCallback((): number => {
    try {
      const data = localStorage.getItem(storageKey);
      return data ? new Blob([data]).size : 0;
    } catch {
      return 0;
    }
  }, [storageKey]);

  // Save data to localStorage
  const saveData = useCallback(async (data: PersistedSessionData, force = false): Promise<boolean> => {
    if (!force && Date.now() - lastSaveRef.current < 1000) {
      // Rate limiting: don't save more than once per second
      return false;
    }

    try {
      setIsLoading(true);
      setError(null);

      const dataToSave = {
        ...data,
        lastUpdate: Date.now(),
        version: '1.0'
      };

      let serialized = JSON.stringify(dataToSave);
      
      // Check size before compression
      const uncompressedSize = new Blob([serialized]).size;
      if (uncompressedSize > maxStorageSize) {
        // Clean up old sessions to reduce size
        const sortedSessions = dataToSave.sessions
          .sort((a, b) => b.startTime - a.startTime)
          .slice(0, 50); // Keep only 50 most recent sessions
        
        dataToSave.sessions = sortedSessions;
        serialized = JSON.stringify(dataToSave);
      }

      // Apply compression
      const compressed = compressData(serialized);
      
      // Final size check
      const finalSize = new Blob([compressed]).size;
      if (finalSize > maxStorageSize) {
        throw new Error(`Data size (${finalSize} bytes) exceeds limit (${maxStorageSize} bytes)`);
      }

      localStorage.setItem(storageKey, compressed);
      lastSaveRef.current = Date.now();
      
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save session data';
      setError(errorMessage);
      console.error('Session persistence error:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [storageKey, maxStorageSize, compressData]);

  // Load data from localStorage
  const loadData = useCallback((): PersistedSessionData | null => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (!stored) return null;

      const decompressed = decompressData(stored);
      const parsed = JSON.parse(decompressed);

      // Validate data structure
      if (parsed && typeof parsed === 'object' && parsed.version === '1.0') {
        return parsed;
      }
    } catch (error) {
      console.error('Failed to load persisted data:', error);
      setError('Failed to load saved session data');
    }

    return null;
  }, [storageKey, decompressData]);

  // Auto-save with debouncing
  useEffect(() => {
    if (!autoSave) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(() => {
      saveData(persistedData);
    }, saveInterval);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [persistedData, autoSave, saveInterval, saveData]);

  // Tab synchronization
  useEffect(() => {
    if (!syncAcrossTabs) return;

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === storageKey && e.newValue) {
        try {
          const decompressed = decompressData(e.newValue);
          const newData = JSON.parse(decompressed);
          
          // Only update if the data is newer
          if (newData.lastUpdate > persistedData.lastUpdate) {
            setPersistedData(newData);
          }
        } catch (error) {
          console.error('Failed to sync session data across tabs:', error);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [storageKey, syncAcrossTabs, decompressData, persistedData.lastUpdate]);

  // Public API methods
  const updateSessions = useCallback((sessions: OrchestrationSession[]) => {
    setPersistedData(prev => ({
      ...prev,
      sessions,
      lastUpdate: Date.now()
    }));
  }, []);

  const updateGroups = useCallback((groups: SessionGroup[]) => {
    setPersistedData(prev => ({
      ...prev,
      groups,
      lastUpdate: Date.now()
    }));
  }, []);

  const updateFilters = useCallback((filters: SessionFilter) => {
    setPersistedData(prev => ({
      ...prev,
      filters,
      lastUpdate: Date.now()
    }));
  }, []);

  const setActiveSession = useCallback((sessionId: string | undefined) => {
    setPersistedData(prev => ({
      ...prev,
      activeSessionId: sessionId,
      lastUpdate: Date.now()
    }));
  }, []);

  const addFavoriteCoordination = useCallback((coordinationId: string) => {
    setPersistedData(prev => ({
      ...prev,
      favoriteCoordinationIds: [...new Set([...prev.favoriteCoordinationIds, coordinationId])],
      lastUpdate: Date.now()
    }));
  }, []);

  const removeFavoriteCoordination = useCallback((coordinationId: string) => {
    setPersistedData(prev => ({
      ...prev,
      favoriteCoordinationIds: prev.favoriteCoordinationIds.filter(id => id !== coordinationId),
      lastUpdate: Date.now()
    }));
  }, []);

  const setBudget = useCallback((coordinationId: string, budget: number) => {
    setPersistedData(prev => ({
      ...prev,
      costBudgets: {
        ...prev.costBudgets,
        [coordinationId]: budget
      },
      lastUpdate: Date.now()
    }));
  }, []);

  const clearData = useCallback(async () => {
    try {
      localStorage.removeItem(storageKey);
      setPersistedData({
        sessions: [],
        groups: [],
        filters: {},
        favoriteCoordinationIds: [],
        costBudgets: {},
        lastUpdate: Date.now(),
        version: '1.0'
      });
      setError(null);
    } catch (error) {
      setError('Failed to clear session data');
    }
  }, [storageKey]);

  const exportData = useCallback((): string => {
    return JSON.stringify(persistedData, null, 2);
  }, [persistedData]);

  const importData = useCallback((jsonData: string): boolean => {
    try {
      const imported = JSON.parse(jsonData);
      if (imported && imported.version === '1.0') {
        setPersistedData({
          ...imported,
          lastUpdate: Date.now()
        });
        return true;
      }
      setError('Invalid data format');
      return false;
    } catch (error) {
      setError('Failed to import data');
      return false;
    }
  }, []);

  const getStorageInfo = useCallback(() => {
    const size = getStorageSize();
    const utilization = (size / maxStorageSize) * 100;
    
    return {
      size,
      maxSize: maxStorageSize,
      utilization: Math.round(utilization),
      sessionCount: persistedData.sessions.length,
      groupCount: persistedData.groups.length,
      favoriteCount: persistedData.favoriteCoordinationIds.length,
      lastUpdate: new Date(persistedData.lastUpdate).toLocaleString()
    };
  }, [getStorageSize, maxStorageSize, persistedData]);

  return {
    // Data access
    sessions: persistedData.sessions,
    groups: persistedData.groups,
    filters: persistedData.filters,
    activeSessionId: persistedData.activeSessionId,
    favoriteCoordinationIds: persistedData.favoriteCoordinationIds,
    costBudgets: persistedData.costBudgets,
    
    // State
    isLoading,
    error,
    
    // Update methods
    updateSessions,
    updateGroups,
    updateFilters,
    setActiveSession,
    addFavoriteCoordination,
    removeFavoriteCoordination,
    setBudget,
    
    // Utility methods
    saveData: () => saveData(persistedData, true),
    loadData,
    clearData,
    exportData,
    importData,
    getStorageInfo
  };
}