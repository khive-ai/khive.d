/**
 * System Performance and Observability Types
 * MVP feature: CPU/memory usage metrics and agent success/failure rates
 */

// System Resource Metrics
export interface SystemMetrics {
  timestamp: string;
  cpu: CPUMetrics;
  memory: MemoryMetrics;
  disk?: DiskMetrics;
  network?: NetworkMetrics;
}

export interface CPUMetrics {
  usage: number; // Percentage (0-100)
  cores: number;
  loadAverage: {
    load1: number;
    load5: number;
    load15: number;
  };
  processes: number;
}

export interface MemoryMetrics {
  total: number; // Bytes
  used: number; // Bytes
  free: number; // Bytes
  usage: number; // Percentage (0-100)
  swap?: {
    total: number;
    used: number;
    free: number;
  };
}

export interface DiskMetrics {
  total: number; // Bytes
  used: number; // Bytes
  free: number; // Bytes
  usage: number; // Percentage (0-100)
  iops?: {
    read: number;
    write: number;
  };
}

export interface NetworkMetrics {
  bytesIn: number;
  bytesOut: number;
  packetsIn: number;
  packetsOut: number;
  errors: number;
}

// Agent Performance Metrics
export interface AgentPerformanceMetrics {
  agentId: string;
  role: string;
  domain: string;
  totalTasks: number;
  successfulTasks: number;
  failedTasks: number;
  successRate: number; // Percentage (0-100)
  averageTaskDuration: number; // Milliseconds
  errorRate: number; // Percentage (0-100)
  lastActivity: string; // ISO timestamp
  taskHistory: TaskResult[];
}

export interface TaskResult {
  id: string;
  startTime: string;
  endTime: string;
  status: "success" | "failure" | "timeout" | "cancelled";
  duration: number; // Milliseconds
  errorMessage?: string;
  taskType?: string;
}

// System Health Summary
export interface SystemHealthSummary {
  status: "healthy" | "warning" | "critical";
  uptime: number; // Seconds
  systemMetrics: SystemMetrics;
  agentMetrics: {
    totalAgents: number;
    activeAgents: number;
    errorAgents: number;
    averageSuccessRate: number;
  };
  alerts: SystemAlert[];
}

export interface SystemAlert {
  id: string;
  level: "info" | "warning" | "error" | "critical";
  message: string;
  timestamp: string;
  source: "system" | "agent" | "coordinator";
  resolved: boolean;
}

// Time series data for charts
export interface TimeSeriesDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

export interface TimeSeriesData {
  name: string;
  data: TimeSeriesDataPoint[];
  color?: string;
}

// Chart configuration types
export interface ChartConfiguration {
  title: string;
  type: "line" | "bar" | "area" | "pie" | "doughnut";
  yAxisLabel: string;
  xAxisLabel?: string;
  showLegend: boolean;
  refreshRate: number; // Milliseconds
  maxDataPoints: number;
}

// Observability console configuration
export interface ObservabilityConfig {
  refreshInterval: number; // Milliseconds
  maxHistoryPoints: number;
  alerts: {
    cpuThreshold: number; // Percentage
    memoryThreshold: number; // Percentage
    diskThreshold: number; // Percentage
    agentErrorThreshold: number; // Percentage
  };
  charts: {
    cpu: ChartConfiguration;
    memory: ChartConfiguration;
    agentSuccess: ChartConfiguration;
  };
}
