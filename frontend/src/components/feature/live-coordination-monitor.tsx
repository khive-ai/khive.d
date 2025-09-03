/**
 * Live Coordination Monitor MVP
 * Real-time dashboard showing agent coordination, file conflicts, and collaboration metrics
 * Implements agentic-systems patterns for multi-agent orchestration monitoring
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  AlertTitle,
  Avatar,
  Badge,
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Analytics as MetricsIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Group as AgentsIcon,
  Lock as LockIcon,
  Refresh as RefreshIcon,
  Schedule as PendingIcon,
  Security as SecurityIcon,
  Share as ShareIcon,
  Speed as PerformanceIcon,
  Task as TaskIcon,
  Timeline as ActivityIcon,
  Warning as ConflictIcon,
} from "@mui/icons-material";
import {
  CollaborationMetrics,
  CoordinationEvent,
  CoordinationMonitorProps,
  CoordinationStatus,
  FileConflict,
} from "@/types";
import { formatDate, formatDuration } from "@/lib/utils";

// Mock data generator for MVP demonstration
const generateMockCoordinationStatus = (): CoordinationStatus => ({
  active: true,
  totalAgents: 5,
  activeWork: [
    {
      agent: "researcher_memory-systems",
      task: "Memory architecture analysis",
      duration_seconds: 1845,
    },
    {
      agent: "analyst_agentic-systems",
      task: "Live Coordination Monitor MVP",
      duration_seconds: 156,
    },
    {
      agent: "architect_distributed-systems",
      task: "Protocol design review",
      duration_seconds: 892,
    },
  ],
  lockedFiles: [
    {
      id: "lock-001",
      filePath: "/frontend/src/components/feature/coordination-panel.tsx",
      lockedBy: "implementer_frontend-systems",
      lockedAt: new Date(Date.now() - 300000).toISOString(),
      expiresIn: 1500,
      conflictingAgents: ["tester_ui-systems"],
      status: "active" as const,
    },
  ],
  availableArtifacts: [
    "Memory Systems Analysis Report",
    "Coordination Protocol Specification",
    "UI Component Library Update",
  ],
  metrics: {
    totalAgents: 5,
    activeAgents: 3,
    conflictsPrevented: 29,
    duplicatesAvoided: 47,
    artifactsShared: 12,
    avgResponseTime: 1.2,
    successRate: 0.94,
    coordinationEfficiency: 0.87,
  },
  lastUpdated: new Date().toISOString(),
});

const generateMockEvents = (): CoordinationEvent[] => [
  {
    id: "event-001",
    timestamp: new Date(Date.now() - 30000).toISOString(),
    type: "task_start",
    agentId: "analyst_agentic-systems",
    agentRole: "analyst",
    message: "Started Live Coordination Monitor MVP development",
    severity: "info",
  },
  {
    id: "event-002",
    timestamp: new Date(Date.now() - 120000).toISOString(),
    type: "conflict_resolved",
    agentId: "implementer_frontend-systems",
    agentRole: "implementer",
    message: "Resolved file conflict on coordination-panel.tsx",
    details: {
      filePath: "/frontend/src/components/feature/coordination-panel.tsx",
    },
    severity: "success",
  },
  {
    id: "event-003",
    timestamp: new Date(Date.now() - 180000).toISOString(),
    type: "conflict_detected",
    agentId: "system",
    agentRole: "coordinator",
    message:
      "File conflict detected: multiple agents attempting to edit same file",
    details: {
      conflictingAgents: ["tester_ui-systems", "implementer_frontend-systems"],
    },
    severity: "warning",
  },
  {
    id: "event-004",
    timestamp: new Date(Date.now() - 240000).toISOString(),
    type: "agent_spawn",
    agentId: "researcher_memory-systems",
    agentRole: "researcher",
    message: "Agent spawned for memory architecture analysis",
    severity: "info",
  },
  {
    id: "event-005",
    timestamp: new Date(Date.now() - 300000).toISOString(),
    type: "task_complete",
    agentId: "critic_performance-systems",
    agentRole: "critic",
    message: "Performance optimization review completed successfully",
    severity: "success",
  },
];

export const LiveCoordinationMonitor: React.FC<CoordinationMonitorProps> = ({
  coordinationId,
  refreshInterval = 5000,
  maxEvents = 20,
  onEventClick,
  onConflictResolve,
  className,
}) => {
  const [coordinationStatus, setCoordinationStatus] = useState<
    CoordinationStatus
  >(generateMockCoordinationStatus());
  const [recentEvents, setRecentEvents] = useState<CoordinationEvent[]>(
    generateMockEvents(),
  );
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setCoordinationStatus(generateMockCoordinationStatus());
      // Add new events periodically
      if (Math.random() > 0.7) {
        setRecentEvents((prev) => [
          {
            id: `event-${Date.now()}`,
            timestamp: new Date().toISOString(),
            type: Math.random() > 0.5 ? "task_start" : "file_lock",
            agentId: `agent_${Math.random().toString(36).substr(2, 9)}`,
            agentRole: [
              "researcher",
              "analyst",
              "implementer",
            ][Math.floor(Math.random() * 3)],
            message: "Real-time coordination activity detected",
            severity: "info" as const,
          },
          ...prev.slice(0, maxEvents - 1),
        ]);
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval, maxEvents]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Simulate API call delay
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setCoordinationStatus(generateMockCoordinationStatus());
    setRecentEvents(generateMockEvents());
    setIsRefreshing(false);
  };

  const getEventIcon = (type: CoordinationEvent["type"]) => {
    switch (type) {
      case "task_start":
      case "task_complete":
        return <TaskIcon fontSize="small" />;
      case "conflict_detected":
      case "conflict_resolved":
        return <ConflictIcon fontSize="small" />;
      case "agent_spawn":
      case "agent_terminate":
        return <AgentsIcon fontSize="small" />;
      case "file_lock":
      case "file_unlock":
        return <LockIcon fontSize="small" />;
      default:
        return <ActivityIcon fontSize="small" />;
    }
  };

  const getSeverityColor = (severity: CoordinationEvent["severity"]) => {
    switch (severity) {
      case "success":
        return "success";
      case "warning":
        return "warning";
      case "error":
        return "error";
      default:
        return "info";
    }
  };

  const activeConflicts = coordinationStatus.lockedFiles.filter((f) =>
    f.status === "active"
  );
  const metrics = coordinationStatus.metrics;

  return (
    <Box className={className}>
      <Grid container spacing={3}>
        {/* Header with refresh */}
        <Grid item xs={12}>
          <Box
            display="flex"
            justifyContent="between"
            alignItems="center"
            mb={2}
          >
            <Typography variant="h4" component="h1" fontWeight="bold">
              Live Coordination Monitor
            </Typography>
            <Tooltip title="Refresh Data">
              <IconButton onClick={handleRefresh} disabled={isRefreshing}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Box>

          {coordinationId && (
            <Typography variant="body2" color="text.secondary" mb={2}>
              Coordination Session: {coordinationId}
            </Typography>
          )}
        </Grid>

        {/* Key Metrics Overview */}
        <Grid item xs={12} md={6} lg={3}>
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Avatar sx={{ bgcolor: "primary.main" }}>
                  <AgentsIcon />
                </Avatar>
                <Box>
                  <Typography variant="h6" fontWeight="bold">
                    {metrics.activeAgents}/{metrics.totalAgents}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Agents
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} lg={3}>
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Avatar sx={{ bgcolor: "success.main" }}>
                  <SecurityIcon />
                </Avatar>
                <Box>
                  <Typography variant="h6" fontWeight="bold">
                    {metrics.conflictsPrevented}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Conflicts Prevented
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} lg={3}>
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Avatar sx={{ bgcolor: "info.main" }}>
                  <ShareIcon />
                </Avatar>
                <Box>
                  <Typography variant="h6" fontWeight="bold">
                    {metrics.artifactsShared}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Artifacts Shared
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6} lg={3}>
          <Card variant="outlined">
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Avatar sx={{ bgcolor: "warning.main" }}>
                  <PerformanceIcon />
                </Avatar>
                <Box>
                  <Typography variant="h6" fontWeight="bold">
                    {(metrics.coordinationEfficiency * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Efficiency Score
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Conflicts Alert */}
        {activeConflicts.length > 0 && (
          <Grid item xs={12}>
            <Alert severity="warning" variant="outlined">
              <AlertTitle>Active File Conflicts</AlertTitle>
              {activeConflicts.map((conflict) => (
                <Box key={conflict.id} mt={1}>
                  <Typography variant="body2">
                    <strong>{conflict.filePath}</strong> locked by{" "}
                    <em>{conflict.lockedBy}</em>
                    {conflict.conflictingAgents.length > 0 && (
                      <>• {conflict.conflictingAgents.length} agents waiting</>
                    )}
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={(1 - conflict.expiresIn / 1800) * 100}
                    color="warning"
                    sx={{ mt: 0.5, height: 4, borderRadius: 2 }}
                  />
                </Box>
              ))}
            </Alert>
          </Grid>
        )}

        {/* Agent Activity Stream */}
        <Grid item xs={12} md={8}>
          <Card variant="outlined">
            <CardHeader
              avatar={<ActivityIcon color="primary" />}
              title="Agent Activity Stream"
              subheader={`${recentEvents.length} recent events • Auto-refresh every ${
                refreshInterval / 1000
              }s`}
            />
            <CardContent sx={{ p: 0, maxHeight: 400, overflow: "auto" }}>
              <List>
                {recentEvents.map((event, index) => (
                  <React.Fragment key={event.id}>
                    <ListItem
                      button={!!onEventClick}
                      onClick={() =>
                        onEventClick?.(event)}
                      sx={{ py: 1.5 }}
                    >
                      <ListItemAvatar>
                        <Badge
                          badgeContent=""
                          color={getSeverityColor(event.severity)}
                          variant="dot"
                          anchorOrigin={{
                            vertical: "bottom",
                            horizontal: "right",
                          }}
                        >
                          <Avatar
                            sx={{ width: 32, height: 32, bgcolor: "grey.100" }}
                          >
                            {getEventIcon(event.type)}
                          </Avatar>
                        </Badge>
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" gap={1}>
                            <Typography variant="body2" fontWeight="medium">
                              {event.message}
                            </Typography>
                            <Chip
                              label={event.agentRole}
                              size="small"
                              variant="outlined"
                              color="primary"
                            />
                          </Box>
                        }
                        secondary={
                          <Typography variant="caption" color="text.secondary">
                            {formatDate(event.timestamp)} • {event.agentId}
                          </Typography>
                        }
                      />
                    </ListItem>
                    {index < recentEvents.length - 1 && (
                      <Divider variant="inset" />
                    )}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Collaboration Metrics */}
        <Grid item xs={12} md={4}>
          <Card variant="outlined">
            <CardHeader
              avatar={<MetricsIcon color="primary" />}
              title="Collaboration Metrics"
              subheader="Real-time coordination statistics"
            />
            <CardContent>
              <Stack spacing={2}>
                <Box>
                  <Box
                    display="flex"
                    justifyContent="between"
                    alignItems="center"
                    mb={0.5}
                  >
                    <Typography variant="body2" color="text.secondary">
                      Success Rate
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {(metrics.successRate * 100).toFixed(1)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={metrics.successRate * 100}
                    color="success"
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                </Box>

                <Box>
                  <Box
                    display="flex"
                    justifyContent="between"
                    alignItems="center"
                    mb={0.5}
                  >
                    <Typography variant="body2" color="text.secondary">
                      Avg Response Time
                    </Typography>
                    <Typography variant="body2" fontWeight="medium">
                      {metrics.avgResponseTime.toFixed(1)}s
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.max(
                      0,
                      100 - (metrics.avgResponseTime / 5) * 100,
                    )}
                    color={metrics.avgResponseTime < 2
                      ? "success"
                      : metrics.avgResponseTime < 4
                      ? "warning"
                      : "error"}
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                </Box>

                <Divider />

                <Box>
                  <Typography
                    variant="subtitle2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Coordination Stats
                  </Typography>
                  <Stack spacing={1}>
                    <Box display="flex" justifyContent="between">
                      <Typography variant="body2">
                        Duplicates Avoided
                      </Typography>
                      <Chip
                        label={metrics.duplicatesAvoided}
                        size="small"
                        color="info"
                      />
                    </Box>
                    <Box display="flex" justifyContent="between">
                      <Typography variant="body2">Active Work Items</Typography>
                      <Chip
                        label={coordinationStatus.activeWork.length}
                        size="small"
                        color="primary"
                      />
                    </Box>
                    <Box display="flex" justifyContent="between">
                      <Typography variant="body2">
                        Available Artifacts
                      </Typography>
                      <Chip
                        label={coordinationStatus.availableArtifacts.length}
                        size="small"
                        color="success"
                      />
                    </Box>
                  </Stack>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* System Status Footer */}
        <Grid item xs={12}>
          <Paper
            elevation={0}
            sx={{ p: 2, bgcolor: "grey.50", borderRadius: 2 }}
          >
            <Box display="flex" justifyContent="between" alignItems="center">
              <Typography variant="body2" color="text.secondary">
                Last updated: {formatDate(coordinationStatus.lastUpdated)}
              </Typography>
              <Box display="flex" alignItems="center" gap={1}>
                <Box
                  width={8}
                  height={8}
                  bgcolor={coordinationStatus.active
                    ? "success.main"
                    : "error.main"}
                  borderRadius="50%"
                />
                <Typography variant="body2" color="text.secondary">
                  Coordination{" "}
                  {coordinationStatus.active ? "Active" : "Inactive"}
                </Typography>
              </Box>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};
