import { useState, useEffect, useCallback, useMemo } from 'react';
import { KhiveApiService, KhiveApiError } from '@/lib/services/khiveApiService';
import { khiveWebSocketService } from '@/lib/services/khiveWebSocketService';
import {
  PlanningRequest,
  PlanningResponse,
  CoordinationEvent,
  OrchestrationSession,
  Agent
} from '@/lib/types/khive';

// Enhanced planning workflow types
export interface PlanningWorkflowState {
  // Core planning state
  request: Partial<PlanningRequest>;
  response: PlanningResponse | null;
  coordinationId: string | null;
  
  // Execution state
  status: 'idle' | 'planning' | 'consensus' | 'executing' | 'completed' | 'failed';
  currentPhase: number;
  totalPhases: number;
  
  // Real-time data
  sessions: OrchestrationSession[];
  agents: Agent[];
  events: CoordinationEvent[];
  
  // Consensus data
  consensusRounds: ConsensusRound[];
  consensusComplete: boolean;
  
  // Error handling
  error: string | null;
  retryCount: number;
}

export interface ConsensusRound {
  round: number;
  agents: AgentConsensus[];
  convergence: number;
  timeoutMs: number;
  status: 'active' | 'completed' | 'timeout';
  strategies: string[];
  votes: Record<string, number>;
  startTime: number;
  endTime?: number;
}

export interface AgentConsensus {
  agentId: string;
  role: string;
  domain: string;
  vote: string | null;
  confidence: number;
  reasoning: string;
  status: 'thinking' | 'voted' | 'timeout';
  priority: number;
  reputation: number;
}

export interface PlanningMetrics {
  totalCost: number;
  totalTokens: { input: number; output: number };
  executionTime: number;
  successRate: number;
  agentUtilization: number;
}

export interface UsePlanningWorkflowOptions {
  autoConnect?: boolean;
  consensusTimeout?: number;
  maxRetries?: number;
  enableMetrics?: boolean;
}

export function usePlanningWorkflow(
  options: UsePlanningWorkflowOptions = {}
) {
  const {
    autoConnect = true,
    consensusTimeout = 30000,
    maxRetries = 3,
    enableMetrics = true
  } = options;

  // Core state
  const [state, setState] = useState<PlanningWorkflowState>({
    request: { complexity: 'medium', pattern: 'P∥', max_agents: 5 },
    response: null,
    coordinationId: null,
    status: 'idle',
    currentPhase: 0,
    totalPhases: 0,
    sessions: [],
    agents: [],
    events: [],
    consensusRounds: [],
    consensusComplete: false,
    error: null,
    retryCount: 0
  });

  // Metrics calculation
  const metrics = useMemo<PlanningMetrics>(() => {
    if (!enableMetrics) {
      return {
        totalCost: 0,
        totalTokens: { input: 0, output: 0 },
        executionTime: 0,
        successRate: 0,
        agentUtilization: 0
      };
    }

    const totalCost = state.sessions.reduce((sum, session) => 
      sum + (session.metrics?.cost || 0), 0);
    
    const totalTokens = state.sessions.reduce(
      (acc, session) => ({
        input: acc.input + (session.metrics?.tokensUsed || 0),
        output: acc.output + (session.metrics?.tokensUsed || 0) // Simplified
      }),
      { input: 0, output: 0 }
    );

    const executionTime = state.response 
      ? (Date.now() - (state.sessions[0]?.startTime || Date.now())) / 1000
      : 0;

    const successRate = state.agents.length > 0
      ? state.agents.filter(a => a.status === 'completed').length / state.agents.length
      : 0;

    const agentUtilization = state.agents.length > 0
      ? state.agents.filter(a => a.status === 'working' || a.status === 'active').length / state.agents.length
      : 0;

    return {
      totalCost,
      totalTokens,
      executionTime,
      successRate,
      agentUtilization
    };
  }, [state.sessions, state.agents, state.response, enableMetrics]);

  // WebSocket event handlers
  const handleCoordinationEvent = useCallback((event: CoordinationEvent) => {
    setState(prev => ({
      ...prev,
      events: [event, ...prev.events.slice(0, 99)] // Keep last 100 events
    }));

    // Update consensus rounds based on planning events
    if (event.type === 'agent_spawn' && event.coordination_id === state.coordinationId) {
      updateConsensusFromEvent(event);
    }
  }, [state.coordinationId]);

  const handleSessionUpdated = useCallback((session: OrchestrationSession) => {
    setState(prev => ({
      ...prev,
      sessions: prev.sessions.map(s => 
        s.sessionId === session.sessionId ? session : s
      ).concat(prev.sessions.find(s => s.sessionId === session.sessionId) ? [] : [session])
    }));
  }, []);

  const handleAgentUpdated = useCallback((agent: Agent) => {
    if (agent.coordination_id === state.coordinationId) {
      setState(prev => ({
        ...prev,
        agents: prev.agents.map(a => 
          a.id === agent.id ? agent : a
        ).concat(prev.agents.find(a => a.id === agent.id) ? [] : [agent])
      }));

      // Update consensus state
      updateConsensusFromAgent(agent);
    }
  }, [state.coordinationId]);

  // WebSocket setup
  useEffect(() => {
    if (!autoConnect) return;

    khiveWebSocketService.on('coordination_event', handleCoordinationEvent);
    khiveWebSocketService.on('session_updated', handleSessionUpdated);
    khiveWebSocketService.on('agent_updated', handleAgentUpdated);

    if (state.coordinationId) {
      khiveWebSocketService.joinCoordination(state.coordinationId);
    }

    return () => {
      khiveWebSocketService.off('coordination_event', handleCoordinationEvent);
      khiveWebSocketService.off('session_updated', handleSessionUpdated);
      khiveWebSocketService.off('agent_updated', handleAgentUpdated);
      
      if (state.coordinationId) {
        khiveWebSocketService.leaveCoordination(state.coordinationId);
      }
    };
  }, [
    autoConnect,
    state.coordinationId,
    handleCoordinationEvent,
    handleSessionUpdated,
    handleAgentUpdated
  ]);

  // Helper functions
  const updateConsensusFromEvent = useCallback((event: CoordinationEvent) => {
    setState(prev => ({
      ...prev,
      consensusRounds: prev.consensusRounds.map(round => ({
        ...round,
        // Update based on event type and content
        convergence: Math.min(round.convergence + 0.1, 1)
      }))
    }));
  }, []);

  const updateConsensusFromAgent = useCallback((agent: Agent) => {
    setState(prev => ({
      ...prev,
      consensusRounds: prev.consensusRounds.map(round => ({
        ...round,
        agents: round.agents.map(a => 
          a.agentId === agent.id
            ? { 
                ...a, 
                status: agent.status === 'working' ? 'thinking' as const : 'voted' as const,
                confidence: agent.progress || a.confidence
              }
            : a
        )
      }))
    }));
  }, []);

  // Main actions
  const submitPlanningRequest = useCallback(async (request: PlanningRequest) => {
    setState(prev => ({ ...prev, status: 'planning', error: null }));

    try {
      const response = await KhiveApiService.submitPlan(request);
      
      setState(prev => ({
        ...prev,
        request,
        response,
        coordinationId: response.coordination_id,
        status: 'consensus',
        totalPhases: response.phases.length,
        currentPhase: 0
      }));

      // Initialize consensus rounds
      initializeConsensusRounds(response);

      return response;
    } catch (error) {
      const errorMsg = error instanceof KhiveApiError 
        ? error.message 
        : 'Failed to submit planning request';
      
      setState(prev => ({ 
        ...prev, 
        status: 'failed', 
        error: errorMsg,
        retryCount: prev.retryCount + 1
      }));

      throw error;
    }
  }, []);

  const initializeConsensusRounds = useCallback((response: PlanningResponse) => {
    const initialRound: ConsensusRound = {
      round: 1,
      agents: response.phases[0]?.agents.map(agent => ({
        agentId: agent.id,
        role: agent.role,
        domain: agent.domain,
        vote: null,
        confidence: 0,
        reasoning: '',
        status: 'thinking',
        priority: agent.priority,
        reputation: 0.8 // Default reputation
      })) || [],
      convergence: 0,
      timeoutMs: consensusTimeout,
      status: 'active',
      strategies: [],
      votes: {},
      startTime: Date.now()
    };

    setState(prev => ({
      ...prev,
      consensusRounds: [initialRound]
    }));
  }, [consensusTimeout]);

  const executePlan = useCallback(async () => {
    if (!state.response || !state.coordinationId) {
      throw new Error('No plan to execute');
    }

    setState(prev => ({ ...prev, status: 'executing' }));

    try {
      // Execute spawn commands
      const spawnPromises = state.response.spawn_commands.map(async (command) => {
        const [, role, domain] = command.match(/spawn (\w+) (\w+)/) || [];
        if (role && domain) {
          return KhiveApiService.spawnAgent(role, domain, state.coordinationId!);
        }
      });

      await Promise.all(spawnPromises);

      setState(prev => ({ 
        ...prev, 
        status: 'completed',
        consensusComplete: true
      }));

    } catch (error) {
      const errorMsg = error instanceof KhiveApiError 
        ? error.message 
        : 'Failed to execute plan';
      
      setState(prev => ({ 
        ...prev, 
        status: 'failed', 
        error: errorMsg 
      }));

      throw error;
    }
  }, [state.response, state.coordinationId]);

  const retryWithBackoff = useCallback(async (action: () => Promise<void>) => {
    if (state.retryCount >= maxRetries) {
      throw new Error('Max retries exceeded');
    }

    const delay = Math.pow(2, state.retryCount) * 1000; // Exponential backoff
    await new Promise(resolve => setTimeout(resolve, delay));
    
    return action();
  }, [state.retryCount, maxRetries]);

  const resetWorkflow = useCallback(() => {
    setState({
      request: { complexity: 'medium', pattern: 'P∥', max_agents: 5 },
      response: null,
      coordinationId: null,
      status: 'idle',
      currentPhase: 0,
      totalPhases: 0,
      sessions: [],
      agents: [],
      events: [],
      consensusRounds: [],
      consensusComplete: false,
      error: null,
      retryCount: 0
    });

    if (state.coordinationId) {
      khiveWebSocketService.leaveCoordination(state.coordinationId);
    }
  }, [state.coordinationId]);

  const updateRequest = useCallback((updates: Partial<PlanningRequest>) => {
    setState(prev => ({
      ...prev,
      request: { ...prev.request, ...updates }
    }));
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // Computed values
  const isLoading = state.status === 'planning' || state.status === 'executing';
  const canExecute = state.status === 'consensus' && state.consensusComplete;
  const isComplete = state.status === 'completed';
  const hasFailed = state.status === 'failed';

  return {
    // State
    state,
    metrics,
    
    // Computed values
    isLoading,
    canExecute,
    isComplete,
    hasFailed,
    
    // Actions
    submitPlanningRequest,
    executePlan,
    retryWithBackoff,
    resetWorkflow,
    updateRequest,
    clearError,
    
    // WebSocket actions
    joinCoordination: (id: string) => khiveWebSocketService.joinCoordination(id),
    leaveCoordination: (id: string) => khiveWebSocketService.leaveCoordination(id)
  };
}