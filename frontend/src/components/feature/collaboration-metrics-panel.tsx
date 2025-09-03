/**
 * Collaboration Metrics Panel Component
 * Displays key coordination and collaboration metrics in real-time
 */

import React, { useMemo, useState } from "react";
import {
  Box,
  Chip,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Assignment as TaskIcon,
  Info as InfoIcon,
  People as PeopleIcon,
  Refresh as RefreshIcon,
  Security as SecurityIcon,
  Speed as PerformanceIcon,
  TrendingDown as TrendingDownIcon,
  TrendingUp as TrendingUpIcon,
} from "@mui/icons-material";
import { Card, CardContent, CardHeader } from "@/components/ui";
import { Agent, CoordinationMetrics, FileLock, HookEvent } from "@/lib/types";

export interface MetricCard {
  id: string;
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  trendValue?: number;
  color?: "primary" | "secondary" | "success" | "warning" | "error" | "info";
  icon?: React.ReactNode;
  progress?: number;
}

export interface CollaborationMetricsPanelProps {
  metrics: CoordinationMetrics;
  agents: Agent[];
  fileLocks: FileLock[];
  events: HookEvent[];
  refreshInterval?: number;
  onRefresh?: () => void;
  className?: string;
}

export const CollaborationMetricsPanel: React.FC<
  CollaborationMetricsPanelProps
> = ({
  metrics,
  agents,
  fileLocks,
  events,
  refreshInterval = 30000,
  onRefresh,
  className,
}) => {
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const computedMetrics = useMemo(() => {
    const now = new Date();
    const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);

    // Recent events (last hour)
    const recentEvents = events.filter(
      (event) => new Date(event.timestamp) > oneHourAgo,
    );

    // Active agents by status
    const activeAgents = agents.filter((agent) => agent.status === "active");
    const idleAgents = agents.filter((agent) => agent.status === "idle");
    const errorAgents = agents.filter((agent) => agent.status === "error");

    // File conflict analysis
    const conflictedFiles = fileLocks.filter((lock) =>
      fileLocks.filter((l) => l.filePath === lock.filePath).length > 1
    );

    // Agent efficiency (tasks per hour)
    const taskEvents = recentEvents.filter((e) =>
      e.eventType === "post_command" || e.eventType === "post_edit"
    );
    const avgTasksPerAgent = activeAgents.length > 0
      ? taskEvents.length / activeAgents.length
      : 0;

    // Collaboration rate (inter-agent file sharing)
    const fileAccesses = new Map<string, Set<string>>();
    recentEvents
      .filter((e) => e.filePath)
      .forEach((event) => {
        if (!fileAccesses.has(event.filePath!)) {
          fileAccesses.set(event.filePath!, new Set());
        }
        fileAccesses.get(event.filePath!)!.add(event.agentId);
      });

    const collaborativeFiles = Array.from(fileAccesses.values())
      .filter((agentSet) => agentSet.size > 1).length;

    const collaborationRate = fileAccesses.size > 0
      ? (collaborativeFiles / fileAccesses.size) * 100
      : 0;

    return {
      recentActivity: recentEvents.length,
      activeAgents: activeAgents.length,
      idleAgents: idleAgents.length,
      errorAgents: errorAgents.length,
      conflictedFiles: conflictedFiles.length,
      avgTasksPerAgent: avgTasksPerAgent.toFixed(1),
      collaborationRate: collaborationRate.toFixed(1),
      totalFiles: fileAccesses.size,
    };
  }, [agents, fileLocks, events]);

  const metricCards: MetricCard[] = [
    {
      id: "active-agents",
      title: "Active Agents",
      value: computedMetrics.activeAgents,
      subtitle:
        `${computedMetrics.idleAgents} idle, ${computedMetrics.errorAgents} error`,
      color: computedMetrics.activeAgents > 0 ? "success" : "warning",
      icon: <PeopleIcon />,
      progress: computedMetrics.activeAgents > 0
        ? (computedMetrics.activeAgents / agents.length) * 100
        : 0,
    },
    {
      id: "conflicts-prevented",
      title: "Conflicts Prevented",
      value: metrics.conflictsPrevented,
      subtitle: `${computedMetrics.conflictedFiles} active conflicts`,
      color: computedMetrics.conflictedFiles === 0 ? "success" : "error",
      icon: <SecurityIcon />,
    },
    {
      id: "task-completion",
      title: "Avg Completion Time",
      value: `${metrics.averageTaskCompletionTime.toFixed(1)}m`,
      subtitle: `${computedMetrics.avgTasksPerAgent} tasks/agent/hr`,
      color: metrics.averageTaskCompletionTime < 10 ? "success" : "warning",
      icon: <PerformanceIcon />,
      trend: metrics.averageTaskCompletionTime < 10 ? "down" : "up",
      trendValue: metrics.averageTaskCompletionTime,
    },
    {
      id: "collaboration-rate",
      title: "Collaboration Rate",
      value: `${computedMetrics.collaborationRate}%`,
      subtitle: `${computedMetrics.totalFiles} files accessed`,
      color: parseFloat(computedMetrics.collaborationRate) > 30
        ? "success"
        : "info",
      icon: <TaskIcon />,
      progress: parseFloat(computedMetrics.collaborationRate),
    },
    {
      id: "deduplication-rate",
      title: "Deduplication Rate",
      value: `${(metrics.taskDeduplicationRate * 100).toFixed(1)}%`,
      subtitle: "Duplicate work prevented",
      color: metrics.taskDeduplicationRate > 0.8 ? "success" : "warning",
      icon: <TrendingUpIcon />,
      progress: metrics.taskDeduplicationRate * 100,
    },
    {
      id: "recent-activity",
      title: "Recent Activity",
      value: computedMetrics.recentActivity,
      subtitle: "Events in last hour",
      color: "info",
      icon: <TrendingUpIcon />,
    },
  ];

  const handleRefresh = () => {
    setLastRefresh(new Date());
    onRefresh?.();
  };

  const getTrendIcon = (trend?: "up" | "down" | "neutral") => {
    switch (trend) {
      case "up":
        return <TrendingUpIcon color="error" fontSize="small" />;
      case "down":
        return <TrendingDownIcon color="success" fontSize="small" />;
      default:
        return null;
    }
  };

  return (
    <Card className={className} variant="outlined">
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="h6" component="h3">
              Collaboration Metrics
            </Typography>
            <Chip
              label="Live"
              size="small"
              color="primary"
              variant="filled"
            />
          </Box>
        }
        subtitle={
          <Typography variant="body2" color="text.secondary">
            System coordination and performance indicators
          </Typography>
        }
        action={
          <Tooltip title={`Last updated: ${lastRefresh.toLocaleTimeString()}`}>
            <IconButton size="small" onClick={handleRefresh}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        }
      />

      <CardContent>
        <Grid container spacing={2}>
          {metricCards.map((metric) => (
            <Grid item xs={12} sm={6} md={4} key={metric.id}>
              <Card
                variant="outlined"
                sx={{
                  p: 2,
                  height: "100%",
                  backgroundColor: `${metric.color}.light`,
                  borderColor: `${metric.color}.main`,
                  "&:hover": {
                    elevation: 2,
                  },
                }}
              >
                <Box
                  display="flex"
                  alignItems="flex-start"
                  justifyContent="space-between"
                  mb={1}
                >
                  <Box display="flex" alignItems="center" gap={1}>
                    {metric.icon}
                    <Typography variant="subtitle2" color="text.secondary">
                      {metric.title}
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={0.5}>
                    {getTrendIcon(metric.trend)}
                    <Tooltip title="More info">
                      <IconButton size="small">
                        <InfoIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>

                <Box mb={1}>
                  <Typography
                    variant="h4"
                    component="div"
                    color={`${metric.color}.main`}
                    fontWeight="bold"
                  >
                    {metric.value}
                  </Typography>
                  {metric.subtitle && (
                    <Typography variant="caption" color="text.secondary">
                      {metric.subtitle}
                    </Typography>
                  )}
                </Box>

                {metric.progress !== undefined && (
                  <Box>
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      alignItems="center"
                      mb={0.5}
                    >
                      <Typography variant="caption" color="text.secondary">
                        Progress
                      </Typography>
                      <Typography variant="caption">
                        {metric.progress.toFixed(0)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={Math.min(metric.progress, 100)}
                      color={metric.color}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        backgroundColor: "rgba(0,0,0,0.1)",
                      }}
                    />
                  </Box>
                )}
              </Card>
            </Grid>
          ))}
        </Grid>

        <Divider sx={{ my: 2 }} />

        {/* System Health Summary */}
        <Box>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            System Health Summary
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Box display="flex" alignItems="center" gap={1}>
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor: computedMetrics.activeAgents > 0
                      ? "success.main"
                      : "error.main",
                  }}
                />
                <Typography variant="body2">
                  Agent Coordination:{" "}
                  {computedMetrics.activeAgents > 0 ? "Active" : "Inactive"}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box display="flex" alignItems="center" gap={1}>
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor: computedMetrics.conflictedFiles === 0
                      ? "success.main"
                      : "warning.main",
                  }}
                />
                <Typography variant="body2">
                  File Conflicts: {computedMetrics.conflictedFiles === 0
                    ? "None"
                    : `${computedMetrics.conflictedFiles} active`}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} md={4}>
              <Box display="flex" alignItems="center" gap={1}>
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor: metrics.taskDeduplicationRate > 0.8
                      ? "success.main"
                      : "warning.main",
                  }}
                />
                <Typography variant="body2">
                  Efficiency: {metrics.taskDeduplicationRate > 0.8
                    ? "Optimal"
                    : "Needs Attention"}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Box>
      </CardContent>
    </Card>
  );
};
