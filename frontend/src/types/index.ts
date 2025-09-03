/**
 * Type definitions for the Live Coordination Monitor
 * Defines data structures for agent coordination, sessions, and monitoring
 */

export type AgentStatus = "active" | "idle" | "error" | "terminated";
export type SessionStatus =
  | "running"
  | "completed"
  | "failed"
  | "pending"
  | "paused";
export type TaskStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "paused";
export type TaskPriority = "low" | "normal" | "high" | "critical";

/**
 * Agent coordination data structure
 */
export interface Agent {
  id: string;
  role: string;
  domain: string;
  status: AgentStatus;
  sessionId: string;
  currentTask?: string;
  duration?: number;
  startTime?: string;
  lastActivity?: string;
  capabilities: string[];
  coordinates?: {
    x: number;
    y: number;
  };
}

/**
 * Session orchestration data structure
 */
export interface Session {
  id: string;
  coordinationId: string;
  objective: string;
  status: SessionStatus;
  confidence: number;
  complexity: number;
  createdAt: string;
  updatedAt: string;
  context?: string;
  agents: Agent[];
  metrics: SessionMetrics;
}

/**
 * Session performance metrics
 */
export interface SessionMetrics {
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  activeAgents: number;
  conflictsResolved: number;
  avgTaskDuration: number;
  collaborationScore: number;
}

/**
 * Coordination event for activity stream
 */
export interface CoordinationEvent {
  id: string;
  timestamp: string;
  type:
    | "task_start"
    | "task_complete"
    | "conflict_detected"
    | "conflict_resolved"
    | "agent_spawn"
    | "agent_terminate"
    | "file_lock"
    | "file_unlock";
  agentId: string;
  agentRole: string;
  message: string;
  details?: Record<string, any>;
  severity: "info" | "warning" | "error" | "success";
}

/**
 * File conflict information
 */
export interface FileConflict {
  id: string;
  filePath: string;
  lockedBy: string;
  lockedAt: string;
  expiresIn: number;
  conflictingAgents: string[];
  status: "active" | "resolved" | "expired";
}

/**
 * Collaboration metrics data
 */
export interface CollaborationMetrics {
  totalAgents: number;
  activeAgents: number;
  conflictsPrevented: number;
  duplicatesAvoided: number;
  artifactsShared: number;
  avgResponseTime: number;
  successRate: number;
  coordinationEfficiency: number;
}

/**
 * Live coordination status
 */
export interface CoordinationStatus {
  active: boolean;
  totalAgents: number;
  activeWork: Array<{
    agent: string;
    task: string;
    duration_seconds: number;
  }>;
  lockedFiles: FileConflict[];
  availableArtifacts: string[];
  metrics: CollaborationMetrics;
  lastUpdated: string;
}

/**
 * Real-time dashboard data
 */
export interface DashboardData {
  status: CoordinationStatus;
  recentEvents: CoordinationEvent[];
  activeConflicts: FileConflict[];
  sessions: Session[];
  agents: Agent[];
}

/**
 * Component props for coordination monitoring
 */
export interface CoordinationMonitorProps {
  coordinationId?: string;
  refreshInterval?: number;
  maxEvents?: number;
  onEventClick?: (event: CoordinationEvent) => void;
  onConflictResolve?: (conflict: FileConflict) => void;
  className?: string;
}
