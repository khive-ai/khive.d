// Core KHIVE orchestration types aligned with Ocean's backend

export interface OrchestrationSession {
  sessionId: string;
  flowName: string;
  status: 'initializing' | 'ready' | 'executing' | 'completed' | 'failed' | 'stopped' | 'paused';
  startTime: number;
  duration: number;
  results: Record<string, unknown>;
  coordination_id: string;
  phase?: number;
  totalPhases?: number;
  pattern?: 'P∥' | 'P→' | 'P⊕' | 'Pⓕ' | 'P⊗' | 'Expert';
  agents?: Agent[];
  dependencies?: string[];
  metrics?: SessionMetrics;
  priority?: 'low' | 'normal' | 'high' | 'critical';
  tags?: string[];
  parentSessionId?: string;
  childSessionIds?: string[];
}

export interface Agent {
  id: string;
  role: string;
  domain: string;
  priority: number;
  status: 'spawning' | 'active' | 'working' | 'completed' | 'failed' | 'blocked' | 'idle';
  coordination_id: string;
  reasoning: string;
  sessionId?: string;
  progress?: number;
  currentTask?: string;
  metrics?: AgentMetrics;
  createdAt: number;
  lastActivity?: number;
}

export interface PlanningRequest {
  task_description: string;
  context?: string;
  complexity?: 'simple' | 'medium' | 'complex' | 'very_complex';
  pattern?: 'P∥' | 'P→' | 'P⊕' | 'Pⓕ' | 'P⊗' | 'Expert';
  max_agents?: number;
}

export interface PlanningResponse {
  success: boolean;
  summary: string;
  complexity: string;
  complexity_score: number;
  pattern: string;
  recommended_agents: number;
  phases: TaskPhase[];
  coordination_id: string;
  confidence: number;
  spawn_commands: string[];
  cost?: number;
  tokens?: { input: number; output: number };
}

export interface TaskPhase {
  name: string;
  description: string;
  agents: Agent[];
  dependencies: string[];
  quality_gate: 'basic' | 'thorough' | 'critical';
  coordination_strategy: string;
  expected_artifacts: string[];
}

export interface CoordinationEvent {
  timestamp: number;
  type: 'agent_spawn' | 'task_start' | 'task_complete' | 'conflict' | 'resolution';
  agent_id?: string;
  session_id: string;
  coordination_id: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface CommandPaletteItem {
  id: string;
  title: string;
  subtitle?: string;
  category: 'orchestration' | 'agents' | 'files' | 'system' | 'planning' | 'navigation';
  shortcut?: string;
  action: () => void | Promise<void>;
  icon?: string;
  parameterHints?: string[];
  chainable?: boolean;
}

export interface CommandWithParams {
  command: string;
  parameters: Record<string, any>;
}

export interface CommandHistory {
  command: string;
  timestamp: number;
  executionTime: number;
  success: boolean;
  error?: string;
  context?: {
    view: 'agents' | 'planning' | 'analytics' | 'monitoring';
    sessionId?: string;
    agentId?: string;
  };
}

export interface CommandFavorite {
  commandId: string;
  command: CommandPaletteItem;
  timestamp: number;
}

export interface DaemonStatus {
  running: boolean;
  health: 'healthy' | 'degraded' | 'unhealthy';
  uptime: number;
  active_sessions: number;
  total_agents: number;
  memory_usage: number;
  cpu_usage: number;
}

export interface SessionMetrics {
  tokensUsed: number;
  apiCalls: number;
  cost: number;
  avgResponseTime: number;
  successRate: number;
  resourceUtilization: {
    cpu: number;
    memory: number;
    network: number;
  };
}

export interface AgentMetrics {
  tasksCompleted: number;
  avgTaskTime: number;
  successRate: number;
  tokensUsed: number;
  cost: number;
}

export interface SessionAction {
  type: 'pause' | 'resume' | 'terminate' | 'restart' | 'clone';
  sessionId: string;
  reason?: string;
}

export interface SessionFilter {
  status?: OrchestrationSession['status'][];
  pattern?: OrchestrationSession['pattern'][];
  coordination_id?: string;
  priority?: OrchestrationSession['priority'][];
  tags?: string[];
  dateRange?: {
    start: number;
    end: number;
  };
  search?: string;
}

export interface SessionGroup {
  coordination_id: string;
  sessions: OrchestrationSession[];
  pattern: string;
  status: 'active' | 'completed' | 'failed' | 'mixed';
  totalAgents: number;
  startTime: number;
  duration: number;
  metrics: SessionMetrics;
}