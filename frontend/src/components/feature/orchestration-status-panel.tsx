/**
 * Orchestration Status Panel Component
 * Comprehensive status monitoring for multi-agent orchestration systems
 * Provides real-time insights into coordination patterns and system health
 */

import React, { useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Collapse,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemSecondaryAction,
  ListItemText,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  CheckCircle as SuccessIcon,
  Dashboard as DashboardIcon,
  Error as ErrorIcon,
  ExpandLess,
  ExpandMore,
  Groups as CoordinationIcon,
  Info as InfoIcon,
  Memory as ResourceIcon,
  Notifications as AlertIcon,
  Refresh as RefreshIcon,
  Security as HealthIcon,
  Speed as PerformanceIcon,
  Timeline as FlowIcon,
  TrendingUp as MetricsIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import {
  useAgents,
  useCoordinationMetrics,
  useEvents,
  useSessions,
} from "@/lib/api/hooks";

export interface OrchestrationStatusPanelProps {
  coordinationId?: string;
  refreshInterval?: number;
  onStatusAlert?: (alert: StatusAlert) => void;
  className?: string;
}

export interface StatusAlert {
  id: string;
  severity: "error" | "warning" | "info" | "success";
  title: string;
  message: string;
  timestamp: string;
  source: "agent" | "coordination" | "system" | "resource";
}

export interface SystemHealthMetrics {
  cpu: number;
  memory: number;
  activeConnections: number;
  responseTime: number;
  errorRate: number;
  throughput: number;
}

export interface CoordinationFlow {
  id: string;
  pattern: "FAN_OUT_SYNTHESIZE" | "PIPELINE" | "PARALLEL";
  agents: number;
  progress: number;
  status: "active" | "blocked" | "completed" | "error";
  bottleneck?: string;
}

export const OrchestrationStatusPanel: React.FC<OrchestrationStatusPanelProps> =
  ({
    coordinationId,
    refreshInterval = 5000,
    onStatusAlert,
    className,
  }) => {
    const [expandedSections, setExpandedSections] = useState<string[]>([
      "health",
      "coordination",
    ]);
    const [alerts, setAlerts] = useState<StatusAlert[]>([]);
    const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

    // API hooks for real-time data
    const { data: metrics, refetch: refetchMetrics } = useCoordinationMetrics();
    const { data: events, refetch: refetchEvents } = useEvents(coordinationId);
    const { data: sessions, refetch: refetchSessions } = useSessions();
    const { data: agents, refetch: refetchAgents } = useAgents();

    // Auto-refresh mechanism
    useEffect(() => {
      const interval = setInterval(() => {
        refetchMetrics();
        refetchEvents();
        refetchSessions();
        refetchAgents();
        setLastUpdate(new Date());
      }, refreshInterval);

      return () => clearInterval(interval);
    }, [
      refreshInterval,
      refetchMetrics,
      refetchEvents,
      refetchSessions,
      refetchAgents,
    ]);

    // Mock system health metrics (in real app, would come from monitoring API)
    const systemHealth: SystemHealthMetrics = {
      cpu: 45,
      memory: 67,
      activeConnections: metrics?.activeAgents || 0,
      responseTime: 125,
      errorRate: 2.1,
      throughput: 450,
    };

    // Mock coordination flows (in real app, would be derived from active sessions and plans)
    const coordinationFlows: CoordinationFlow[] = [
      {
        id: "flow-001",
        pattern: "FAN_OUT_SYNTHESIZE",
        agents: 5,
        progress: 78,
        status: "active",
      },
      {
        id: "flow-002",
        pattern: "PIPELINE",
        agents: 3,
        progress: 34,
        status: "blocked",
        bottleneck: "Data dependency waiting",
      },
      {
        id: "flow-003",
        pattern: "PARALLEL",
        agents: 8,
        progress: 95,
        status: "active",
      },
    ];

    // Generate status alerts based on metrics
    useEffect(() => {
      const newAlerts: StatusAlert[] = [];

      if (systemHealth.cpu > 80) {
        newAlerts.push({
          id: "cpu-high",
          severity: "warning",
          title: "High CPU Usage",
          message: `CPU usage at ${systemHealth.cpu}%`,
          timestamp: new Date().toISOString(),
          source: "system",
        });
      }

      if (systemHealth.errorRate > 5) {
        newAlerts.push({
          id: "error-rate-high",
          severity: "error",
          title: "High Error Rate",
          message: `Error rate at ${systemHealth.errorRate}%`,
          timestamp: new Date().toISOString(),
          source: "system",
        });
      }

      if (coordinationFlows.some((f) => f.status === "blocked")) {
        newAlerts.push({
          id: "coordination-blocked",
          severity: "warning",
          title: "Coordination Flow Blocked",
          message: "One or more coordination flows are experiencing delays",
          timestamp: new Date().toISOString(),
          source: "coordination",
        });
      }

      if (newAlerts.length > 0) {
        setAlerts((prev) => [...prev.slice(-10), ...newAlerts]);
        newAlerts.forEach((alert) => onStatusAlert?.(alert));
      }
    }, [systemHealth, coordinationFlows, onStatusAlert]);

    const toggleSection = (section: string) => {
      setExpandedSections((prev) =>
        prev.includes(section)
          ? prev.filter((s) => s !== section)
          : [...prev, section]
      );
    };

    const getHealthColor = (
      value: number,
      thresholds: { good: number; warning: number },
    ) => {
      if (value <= thresholds.good) return "success";
      if (value <= thresholds.warning) return "warning";
      return "error";
    };

    const getFlowStatusColor = (status: string) => {
      switch (status) {
        case "active":
          return "success";
        case "blocked":
          return "warning";
        case "error":
          return "error";
        case "completed":
          return "info";
        default:
          return "default";
      }
    };

    const formatDuration = (seconds: number) => {
      if (seconds < 60) return `${seconds}s`;
      if (seconds < 3600) {
        return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
      }
      return `${Math.floor(seconds / 3600)}h ${
        Math.floor((seconds % 3600) / 60)
      }m`;
    };

    return (
      <Card className={className} variant="outlined">
        <CardHeader
          avatar={<DashboardIcon color="primary" />}
          title="Orchestration Status"
          subheader={`Last updated: ${lastUpdate.toLocaleTimeString()}`}
          action={
            <Stack direction="row" spacing={1}>
              <Badge badgeContent={alerts.length} color="error">
                <Tooltip title="System Alerts">
                  <IconButton size="small">
                    <AlertIcon />
                  </IconButton>
                </Tooltip>
              </Badge>
              <Tooltip title="Manual Refresh">
                <IconButton
                  size="small"
                  onClick={() => setLastUpdate(new Date())}
                >
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Stack>
          }
        />

        <CardContent>
          {/* Recent Alerts */}
          {alerts.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Stack spacing={1}>
                {alerts.slice(-3).map((alert) => (
                  <Alert
                    key={alert.id}
                    severity={alert.severity}
                    size="small"
                    onClose={() =>
                      setAlerts((prev) =>
                        prev.filter((a) => a.id !== alert.id)
                      )}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {alert.title}
                    </Typography>
                    {alert.message}
                  </Alert>
                ))}
              </Stack>
              <Divider sx={{ mt: 2, mb: 3 }} />
            </Box>
          )}

          <Grid container spacing={3}>
            {/* System Health Section */}
            <Grid item xs={12}>
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    cursor: "pointer",
                    mb: 2,
                  }}
                  onClick={() => toggleSection("health")}
                >
                  <HealthIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6" sx={{ flex: 1 }}>
                    System Health
                  </Typography>
                  {expandedSections.includes("health")
                    ? <ExpandLess />
                    : <ExpandMore />}
                </Box>

                <Collapse in={expandedSections.includes("health")}>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={3}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          CPU Usage
                        </Typography>
                        <Box
                          sx={{ display: "flex", alignItems: "center", mt: 1 }}
                        >
                          <LinearProgress
                            variant="determinate"
                            value={systemHealth.cpu}
                            sx={{ flex: 1, height: 8, borderRadius: 4 }}
                            color={getHealthColor(systemHealth.cpu, {
                              good: 50,
                              warning: 80,
                            })}
                          />
                          <Typography
                            variant="caption"
                            sx={{ ml: 1, minWidth: 40 }}
                          >
                            {systemHealth.cpu}%
                          </Typography>
                        </Box>
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Memory Usage
                        </Typography>
                        <Box
                          sx={{ display: "flex", alignItems: "center", mt: 1 }}
                        >
                          <LinearProgress
                            variant="determinate"
                            value={systemHealth.memory}
                            sx={{ flex: 1, height: 8, borderRadius: 4 }}
                            color={getHealthColor(systemHealth.memory, {
                              good: 60,
                              warning: 85,
                            })}
                          />
                          <Typography
                            variant="caption"
                            sx={{ ml: 1, minWidth: 40 }}
                          >
                            {systemHealth.memory}%
                          </Typography>
                        </Box>
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" color="primary">
                          {systemHealth.responseTime}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Response Time (ms)
                        </Typography>
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography
                          variant="h4"
                          color={systemHealth.errorRate > 5
                            ? "error"
                            : "success"}
                        >
                          {systemHealth.errorRate}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Error Rate
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Collapse>
              </Box>
            </Grid>

            {/* Coordination Flows Section */}
            <Grid item xs={12}>
              <Divider sx={{ my: 3 }} />
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    cursor: "pointer",
                    mb: 2,
                  }}
                  onClick={() => toggleSection("coordination")}
                >
                  <CoordinationIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6" sx={{ flex: 1 }}>
                    Coordination Flows
                  </Typography>
                  <Chip
                    label={`${
                      coordinationFlows.filter((f) => f.status === "active")
                        .length
                    } active`}
                    size="small"
                    color="success"
                    sx={{ mr: 1 }}
                  />
                  {expandedSections.includes("coordination")
                    ? <ExpandLess />
                    : <ExpandMore />}
                </Box>

                <Collapse in={expandedSections.includes("coordination")}>
                  <List dense>
                    {coordinationFlows.map((flow) => (
                      <ListItem key={flow.id}>
                        <ListItemIcon>
                          <FlowIcon color="action" />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box
                              sx={{
                                display: "flex",
                                alignItems: "center",
                                gap: 1,
                              }}
                            >
                              <Typography variant="body2">
                                {flow.pattern.replace(/_/g, " ")}
                              </Typography>
                              <Chip
                                label={`${flow.agents} agents`}
                                size="small"
                                variant="outlined"
                              />
                            </Box>
                          }
                          secondary={
                            <Box sx={{ mt: 1 }}>
                              <Box
                                sx={{
                                  display: "flex",
                                  alignItems: "center",
                                  mb: 0.5,
                                }}
                              >
                                <LinearProgress
                                  variant="determinate"
                                  value={flow.progress}
                                  sx={{ flex: 1, height: 4, borderRadius: 2 }}
                                  color={getFlowStatusColor(flow.status)}
                                />
                                <Typography
                                  variant="caption"
                                  sx={{ ml: 1, minWidth: 35 }}
                                >
                                  {flow.progress}%
                                </Typography>
                              </Box>
                              {flow.bottleneck && (
                                <Typography
                                  variant="caption"
                                  color="warning.main"
                                >
                                  🚧 {flow.bottleneck}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                        <ListItemSecondaryAction>
                          <Chip
                            label={flow.status}
                            size="small"
                            color={getFlowStatusColor(flow.status) as any}
                            variant={flow.status === "active"
                              ? "filled"
                              : "outlined"}
                          />
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                </Collapse>
              </Box>
            </Grid>

            {/* Performance Metrics Section */}
            <Grid item xs={12}>
              <Divider sx={{ my: 3 }} />
              <Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    cursor: "pointer",
                    mb: 2,
                  }}
                  onClick={() => toggleSection("performance")}
                >
                  <PerformanceIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6" sx={{ flex: 1 }}>
                    Performance Metrics
                  </Typography>
                  {expandedSections.includes("performance")
                    ? <ExpandLess />
                    : <ExpandMore />}
                </Box>

                <Collapse in={expandedSections.includes("performance")}>
                  <Grid container spacing={3}>
                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" color="primary">
                          {metrics?.conflictsPrevented || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Conflicts Prevented
                        </Typography>
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" color="success.main">
                          {systemHealth.throughput}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Tasks/Hour
                        </Typography>
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" color="info.main">
                          {((metrics?.averageTaskCompletionTime || 0) / 1000)
                            .toFixed(1)}s
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Avg Completion Time
                        </Typography>
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Box sx={{ textAlign: "center" }}>
                        <Typography variant="h4" color="secondary.main">
                          {metrics?.activeAgents || 0}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Active Agents
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </Collapse>
              </Box>
            </Grid>

            {/* Resource Utilization */}
            <Grid item xs={12}>
              <Divider sx={{ my: 3 }} />
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <ResourceIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">
                  Resource Utilization
                </Typography>
              </Box>

              <Stack direction="row" spacing={3} flexWrap="wrap">
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Active Sessions
                  </Typography>
                  <Typography variant="h6">
                    {sessions?.filter((s) => s.status === "running").length ||
                      0}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Queued Tasks
                  </Typography>
                  <Typography variant="h6">
                    {coordinationFlows.filter((f) => f.status === "blocked")
                      .length}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Memory Pools
                  </Typography>
                  <Typography variant="h6">
                    {Math.floor(Math.random() * 5) + 3} active
                  </Typography>
                </Box>
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  };
