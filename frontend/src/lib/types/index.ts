// Core Khive Dashboard Types

export interface Session {
  id: string;
  coordinationId: string;
  status: "running" | "failed" | "completed" | "pending";
  complexity: number;
  confidence: number;
  createdAt: string;
  updatedAt: string;
  objective: string;
  context: string;
}

export interface Agent {
  id: string;
  role: string;
  domain: string;
  status: "active" | "idle" | "error";
  currentTask?: string;
  duration?: number;
  sessionId: string;
}

export interface FileLock {
  filePath: string;
  agentId: string;
  expiration: string;
  isStale: boolean;
}

export interface HookEvent {
  id: string;
  coordinationId: string;
  agentId: string;
  eventType:
    | "pre_command"
    | "post_command"
    | "pre_edit"
    | "post_edit"
    | "pre_agent_spawn"
    | "post_agent_spawn";
  timestamp: string;
  metadata: Record<string, any>;
  filePath?: string;
  command?: string;
}

export interface CoordinationMetrics {
  conflictsPrevented: number;
  taskDeduplicationRate: number;
  averageTaskCompletionTime: number;
  activeAgents: number;
  activeSessions: number;
  systemPerformance?: SystemPerformanceMetrics;
  agentAnalytics?: AgentAnalytics;
}

export interface SystemPerformanceMetrics {
  cpu: {
    usage: number; // Current CPU usage percentage
    history: MetricDataPoint[]; // Historical CPU usage data
  };
  memory: {
    usage: number; // Current memory usage percentage
    total: number; // Total system memory in MB
    used: number; // Used memory in MB
    history: MetricDataPoint[]; // Historical memory usage data
  };
  timestamp: string;
}

export interface MetricDataPoint {
  timestamp: string;
  value: number;
}

export interface AgentAnalytics {
  successRate: number; // Overall success rate percentage
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  performanceByRole: RolePerformanceMetrics[];
  performanceByDomain: DomainPerformanceMetrics[];
  recentActivity: AgentActivityPoint[];
}

export interface RolePerformanceMetrics {
  role: string;
  successRate: number;
  totalTasks: number;
  averageCompletionTime: number;
}

export interface DomainPerformanceMetrics {
  domain: string;
  successRate: number;
  totalTasks: number;
  averageCompletionTime: number;
}

export interface AgentActivityPoint {
  timestamp: string;
  successful: number;
  failed: number;
}

export interface PlanNode {
  id: string;
  phase: string;
  status: "pending" | "running" | "completed" | "failed";
  agents: string[];
  tasks: string[];
  coordinationStrategy: "FAN_OUT_SYNTHESIZE" | "PIPELINE" | "PARALLEL";
  expectedArtifacts: string[];
  dependencies: string[];
}

export interface Plan {
  id: string;
  sessionId: string;
  nodes: PlanNode[];
  edges: Array<{ from: string; to: string }>;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  capabilities: string[];
  filePath: string;
}

export interface Domain {
  id: string;
  name: string;
  parent?: string;
  description: string;
  knowledgePatterns: Record<string, any>;
  decisionRules: Record<string, any>;
  specializedTools: string[];
  metrics: string[];
  filePath: string;
}
