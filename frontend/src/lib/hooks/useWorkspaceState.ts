import { useState, useEffect, useCallback } from 'react';

export interface WorkspaceState {
  activeView: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings';
  focused: boolean;
  fullscreen: boolean;
  preferences: {
    autoRefresh: boolean;
    refreshInterval: number;
    defaultAgentPriority: number;
    showNotifications: boolean;
    compactView: boolean;
  };
  planningWizard: {
    lastTaskDescription: string;
    lastContext: string;
    defaultComplexity?: 'simple' | 'medium' | 'complex' | 'very_complex';
    defaultPattern?: 'P∥' | 'P→' | 'P⊕' | 'Pⓕ' | 'P⊗' | 'Expert';
    defaultMaxAgents: number;
  };
  analytics: {
    timeRange: '7d' | '30d' | '90d' | '1y';
    selectedMetric: 'cost' | 'performance' | 'usage';
  };
  agentManagement: {
    activeTab: number;
    filterStatus: string[];
    sortBy: 'name' | 'status' | 'priority' | 'created';
    sortOrder: 'asc' | 'desc';
  };
}

const DEFAULT_WORKSPACE_STATE: WorkspaceState = {
  activeView: 'monitoring',
  focused: false,
  fullscreen: false,
  preferences: {
    autoRefresh: true,
    refreshInterval: 5000,
    defaultAgentPriority: 1,
    showNotifications: true,
    compactView: false,
  },
  planningWizard: {
    lastTaskDescription: '',
    lastContext: '',
    defaultMaxAgents: 8,
  },
  analytics: {
    timeRange: '30d',
    selectedMetric: 'cost',
  },
  agentManagement: {
    activeTab: 0,
    filterStatus: [],
    sortBy: 'created',
    sortOrder: 'desc',
  },
};

const STORAGE_KEY = 'khive-workspace-state';

export function useWorkspaceState() {
  const [state, setState] = useState<WorkspaceState>(DEFAULT_WORKSPACE_STATE);
  const [isLoading, setIsLoading] = useState(true);

  // Load state from localStorage on mount
  useEffect(() => {
    try {
      const savedState = localStorage.getItem(STORAGE_KEY);
      if (savedState) {
        const parsed = JSON.parse(savedState);
        // Merge with defaults to handle schema changes
        setState(prev => ({
          ...prev,
          ...parsed,
          preferences: { ...prev.preferences, ...parsed.preferences },
          planningWizard: { ...prev.planningWizard, ...parsed.planningWizard },
          analytics: { ...prev.analytics, ...parsed.analytics },
          agentManagement: { ...prev.agentManagement, ...parsed.agentManagement },
        }));
      }
    } catch (error) {
      console.error('Failed to load workspace state:', error);
      // Reset to defaults if corrupted
      localStorage.removeItem(STORAGE_KEY);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Save state to localStorage when it changes
  useEffect(() => {
    if (!isLoading) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      } catch (error) {
        console.error('Failed to save workspace state:', error);
      }
    }
  }, [state, isLoading]);

  // Update methods
  const updateWorkspaceState = useCallback((updates: Partial<WorkspaceState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  const updatePreferences = useCallback((preferences: Partial<WorkspaceState['preferences']>) => {
    setState(prev => ({
      ...prev,
      preferences: { ...prev.preferences, ...preferences }
    }));
  }, []);

  const updatePlanningWizard = useCallback((planningWizard: Partial<WorkspaceState['planningWizard']>) => {
    setState(prev => ({
      ...prev,
      planningWizard: { ...prev.planningWizard, ...planningWizard }
    }));
  }, []);

  const updateAnalytics = useCallback((analytics: Partial<WorkspaceState['analytics']>) => {
    setState(prev => ({
      ...prev,
      analytics: { ...prev.analytics, ...analytics }
    }));
  }, []);

  const updateAgentManagement = useCallback((agentManagement: Partial<WorkspaceState['agentManagement']>) => {
    setState(prev => ({
      ...prev,
      agentManagement: { ...prev.agentManagement, ...agentManagement }
    }));
  }, []);

  const resetWorkspace = useCallback(() => {
    setState(DEFAULT_WORKSPACE_STATE);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const exportWorkspace = useCallback(() => {
    const dataStr = JSON.stringify(state, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = `khive-workspace-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [state]);

  const importWorkspace = useCallback((file: File) => {
    return new Promise<void>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const imported = JSON.parse(e.target?.result as string);
          // Validate and merge with current state
          setState(prev => ({
            ...prev,
            ...imported,
            preferences: { ...prev.preferences, ...imported.preferences },
            planningWizard: { ...prev.planningWizard, ...imported.planningWizard },
            analytics: { ...prev.analytics, ...imported.analytics },
            agentManagement: { ...prev.agentManagement, ...imported.agentManagement },
          }));
          resolve();
        } catch (error) {
          reject(error);
        }
      };
      reader.onerror = () => reject(reader.error);
      reader.readAsText(file);
    });
  }, []);

  // Workspace templates
  const applyTemplate = useCallback((template: 'developer' | 'researcher' | 'manager' | 'analyst') => {
    const templates = {
      developer: {
        activeView: 'agents' as const,
        preferences: {
          ...state.preferences,
          autoRefresh: true,
          refreshInterval: 2000,
          compactView: true,
        },
        agentManagement: {
          ...state.agentManagement,
          activeTab: 0,
          sortBy: 'priority' as const,
        }
      },
      researcher: {
        activeView: 'planning' as const,
        preferences: {
          ...state.preferences,
          autoRefresh: false,
          compactView: false,
        },
        planningWizard: {
          ...state.planningWizard,
          defaultComplexity: 'complex' as const,
          defaultPattern: 'P∥' as const,
        }
      },
      manager: {
        activeView: 'monitoring' as const,
        preferences: {
          ...state.preferences,
          autoRefresh: true,
          refreshInterval: 5000,
          showNotifications: true,
        }
      },
      analyst: {
        activeView: 'analytics' as const,
        analytics: {
          timeRange: '30d' as const,
          selectedMetric: 'performance' as const,
        },
        preferences: {
          ...state.preferences,
          autoRefresh: true,
          refreshInterval: 10000,
        }
      }
    };

    setState(prev => ({ ...prev, ...templates[template] }));
  }, [state]);

  return {
    state,
    isLoading,
    updateWorkspaceState,
    updatePreferences,
    updatePlanningWizard,
    updateAnalytics,
    updateAgentManagement,
    resetWorkspace,
    exportWorkspace,
    importWorkspace,
    applyTemplate,
  };
}