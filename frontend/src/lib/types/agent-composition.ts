// Agent composition types for Ocean's role+domain system

export interface Role {
  id: string;
  purpose: string;
  core_actions: string[];
  inputs: string[];
  outputs: string[];
  authority: string;
  tools: string[];
  handoff_to: string[];
  handoff_from: string[];
  kpis: string[];
  description?: string;
  decision_logic?: string;
  unique_characteristics?: string[];
  output_focus?: string;
}

export interface Domain {
  id: string;
  type: string;
  parent: string | null;
  knowledge_patterns: Record<string, any>;
  decision_rules: Record<string, any>;
  specialized_tools: Record<string, any>;
  metrics: string[];
  best_practices: Record<string, any>;
  description?: string;
}

export interface AgentComposition {
  role: Role;
  domain: Domain;
  id: string;
  reasoning: string;
  priority: number;
  capabilities: string[];
  estimated_performance: {
    task_completion_rate: number;
    avg_task_time: number;
    resource_efficiency: number;
  };
}

export interface AgentSpawnRequest {
  composition: AgentComposition;
  task_context: string;
  coordination_id: string;
  session_id?: string;
  priority: 'low' | 'normal' | 'high' | 'critical';
}

export interface AgentCapability {
  name: string;
  description: string;
  category: 'technical' | 'coordination' | 'analysis' | 'execution' | 'validation';
  proficiency: 'beginner' | 'intermediate' | 'advanced' | 'expert';
  dependencies: string[];
}

export interface RoleDomainMatch {
  role: Role;
  domain: Domain;
  compatibility_score: number;
  synergy_factors: string[];
  potential_challenges: string[];
  recommended_patterns: string[];
}

export interface AgentLifecycleEvent {
  timestamp: number;
  agent_id: string;
  event_type: 'spawned' | 'started' | 'progress' | 'completed' | 'failed' | 'paused' | 'terminated';
  description: string;
  metadata: Record<string, any>;
}

export interface DataFlowPattern {
  id: string;
  name: string;
  description: string;
  agents_involved: string[];
  data_flow: {
    source: string;
    destination: string;
    data_type: string;
    processing_required: boolean;
  }[];
  optimization_suggestions: string[];
}

export interface StreamProcessor {
  id: string;
  name: string;
  input_stream: string;
  output_stream: string;
  processing_function: string;
  buffer_size: number;
  batch_interval: number;
  error_handling: 'retry' | 'skip' | 'escalate';
}

export interface StateSync {
  id: string;
  agents: string[];
  sync_frequency: number;
  conflict_resolution: 'first_wins' | 'last_wins' | 'consensus' | 'manual';
  consistency_level: 'eventual' | 'strong' | 'weak';
}

export interface AgentRealTimeStatus {
  agent_id: string;
  status: 'spawning' | 'active' | 'working' | 'completed' | 'failed' | 'blocked' | 'idle';
  current_task: string;
  progress: number;
  resource_usage: {
    cpu: number;
    memory: number;
    tokens_used: number;
    api_calls: number;
  };
  performance_metrics: {
    tasks_completed: number;
    avg_task_time: number;
    success_rate: number;
    cost: number;
  };
  coordination: {
    locks_held: string[];
    waiting_for: string[];
    conflicts: string[];
  };
  last_activity: number;
}