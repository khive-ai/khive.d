/**
 * Agent Effectiveness Panel Component
 * Analytics dashboard for agent performance, success/failure rates, and productivity metrics
 * MVP Focus: Basic agent success/failure rates with performance trend analysis
 */

import React, { useMemo, useState } from "react";
import {
  alpha,
  Box,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Assignment as TaskIcon,
  BarChart as ChartIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  ExpandLess as CollapseIcon,
  ExpandMore as ExpandIcon,
  Psychology as AgentIcon,
  Refresh as RefreshIcon,
  Speed as PerformanceIcon,
  Timer as DurationIcon,
  TrendingDown as TrendingDownIcon,
  TrendingUp as TrendingUpIcon,
} from "@mui/icons-material";
import { Card, CardContent, CardHeader } from "@/components/ui";
import type { Agent } from "@/lib/types";

interface AgentEffectivenessMetrics {
  totalAgents: number;
  activeAgents: number;
  successRate: number;
  failureRate: number;
  completionRate: number;
  averageTaskDuration: number;
  throughput: number;
}

interface AgentEffectivenessPanelProps {
  metrics: AgentEffectivenessMetrics;
  agents: Agent[];
  isLoading?: boolean;
  detailed?: boolean;
  refreshInterval?: number;
  onRefresh?: () => void;
  className?: string;
}

interface EffectivenessMetricProps {
  label: string;
  value: number | string;
  unit?: string;
  trend?: "up" | "down" | "stable";
  status: "excellent" | "good" | "warning" | "critical" | "info";
  icon: React.ElementType;
  subtitle?: string;
  progress?: number;
  target?: number;
}

const EffectivenessMetric: React.FC<EffectivenessMetricProps> = ({
  label,
  value,
  unit,
  trend,
  status,
  icon: Icon,
  subtitle,
  progress,
  target,
}) => {
  const theme = useTheme();

  const getStatusColor = () => {
    switch (status) {
      case "excellent":
        return "success";
      case "good":
        return "info";
      case "warning":
        return "warning";
      case "critical":
        return "error";
      default:
        return "primary";
    }
  };

  const getTrendIcon = () => {
    switch (trend) {
      case "up":
        return (
          <TrendingUpIcon fontSize="small" sx={{ color: "success.main" }} />
        );
      case "down":
        return (
          <TrendingDownIcon fontSize="small" sx={{ color: "error.main" }} />
        );
      case "stable":
        return <ChartIcon fontSize="small" sx={{ color: "info.main" }} />;
      default:
        return null;
    }
  };

  const formatValue = () => {
    if (typeof value === "number") {
      if (
        label.toLowerCase().includes("rate") ||
        label.toLowerCase().includes("success")
      ) {
        return `${value.toFixed(1)}%`;
      }
      return value % 1 === 0 ? value.toString() : value.toFixed(1);
    }
    return value;
  };

  const statusColor = getStatusColor();

  return (
    <Paper
      sx={{
        p: 2,
        height: "100%",
        background: `linear-gradient(135deg, ${
          alpha(theme.palette[statusColor].main, 0.08)
        } 0%, ${alpha(theme.palette[statusColor].main, 0.03)} 100%)`,
        border: `1px solid ${alpha(theme.palette[statusColor].main, 0.15)}`,
        transition: "all 0.2s ease-in-out",
        "&:hover": {
          transform: "translateY(-1px)",
          boxShadow: theme.shadows[4],
        },
      }}
    >
      <Box
        display="flex"
        alignItems="flex-start"
        justifyContent="space-between"
        mb={1.5}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <Icon sx={{ fontSize: 20, color: `${statusColor}.main` }} />
          <Typography
            variant="body2"
            color="text.secondary"
            fontWeight="medium"
          >
            {label}
          </Typography>
        </Box>
        {getTrendIcon()}
      </Box>

      <Typography
        variant="h5"
        fontWeight="bold"
        color={`${statusColor}.main`}
        sx={{ mb: 0.5, lineHeight: 1.2 }}
      >
        {formatValue()}
        {unit && (
          <Typography
            component="span"
            variant="body1"
            color="text.secondary"
            ml={0.5}
          >
            {unit}
          </Typography>
        )}
      </Typography>

      {subtitle && (
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          mb={1}
        >
          {subtitle}
        </Typography>
      )}

      {progress !== undefined && (
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
              {progress.toFixed(1)}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={Math.min(progress, 100)}
            color={statusColor}
            sx={{
              height: 4,
              borderRadius: 2,
              backgroundColor: alpha(theme.palette[statusColor].main, 0.1),
            }}
          />
          {target && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ fontSize: "0.7rem", mt: 0.5, display: "block" }}
            >
              Target: {target}%
            </Typography>
          )}
        </Box>
      )}
    </Paper>
  );
};

interface AgentPerformanceRowProps {
  agent: Agent;
  metrics: {
    successRate: number;
    productivity: number;
    currentTaskProgress: number;
  };
}

const AgentPerformanceRow: React.FC<AgentPerformanceRowProps> = (
  { agent, metrics },
) => {
  const theme = useTheme();

  const getStatusColor = (status: Agent["status"]) => {
    switch (status) {
      case "active":
        return "success";
      case "idle":
        return "warning";
      case "error":
        return "error";
      default:
        return "info";
    }
  };

  const formatDuration = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
    return `${seconds}s`;
  };

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        "&:hover": {
          backgroundColor: alpha(theme.palette.primary.main, 0.02),
        },
      }}
    >
      <Grid container spacing={2} alignItems="center">
        <Grid item xs={12} sm={3}>
          <Box display="flex" alignItems="center" gap={1}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: `${getStatusColor(agent.status)}.main`,
              }}
            />
            <Box>
              <Typography variant="body2" fontWeight="medium">
                {agent.role}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {agent.domain}
              </Typography>
            </Box>
          </Box>
        </Grid>

        <Grid item xs={6} sm={2}>
          <Typography variant="caption" color="text.secondary">
            Success Rate
          </Typography>
          <Typography variant="body2" fontWeight="medium">
            {metrics.successRate.toFixed(1)}%
          </Typography>
        </Grid>

        <Grid item xs={6} sm={2}>
          <Typography variant="caption" color="text.secondary">
            Productivity
          </Typography>
          <Typography variant="body2" fontWeight="medium">
            {metrics.productivity.toFixed(1)}
          </Typography>
        </Grid>

        <Grid item xs={6} sm={2}>
          <Typography variant="caption" color="text.secondary">
            Duration
          </Typography>
          <Typography variant="body2" fontWeight="medium">
            {agent.duration ? formatDuration(agent.duration) : "N/A"}
          </Typography>
        </Grid>

        <Grid item xs={6} sm={3}>
          <Typography variant="caption" color="text.secondary">
            Current Task
          </Typography>
          <Typography variant="body2" fontWeight="medium" noWrap>
            {agent.currentTask || "Idle"}
          </Typography>
          {agent.currentTask && (
            <LinearProgress
              variant="determinate"
              value={metrics.currentTaskProgress}
              size="small"
              sx={{ mt: 0.5, height: 3, borderRadius: 1.5 }}
            />
          )}
        </Grid>
      </Grid>
    </Paper>
  );
};

export const AgentEffectivenessPanel: React.FC<AgentEffectivenessPanelProps> = (
  {
    metrics,
    agents,
    isLoading = false,
    detailed = false,
    onRefresh,
    className,
  },
) => {
  const [showDetailedView, setShowDetailedView] = useState(detailed);
  const theme = useTheme();

  // Calculate agent-specific performance metrics
  const agentPerformanceData = useMemo(() => {
    return agents.map((agent) => {
      // Mock calculations based on agent data - in production would use historical data
      const baseSuccessRate = agent.status === "error"
        ? 45
        : agent.status === "active"
        ? 85
        : 70;
      const roleMultiplier = {
        "implementer": 1.1,
        "tester": 0.95,
        "analyst": 1.05,
        "researcher": 0.9,
        "architect": 1.2,
      }[agent.role] || 1.0;

      const successRate = Math.min(
        baseSuccessRate * roleMultiplier + Math.random() * 10,
        98,
      );
      const productivity = agent.duration
        ? Math.min((agent.duration / 60000) * 0.8 + Math.random() * 0.4, 3.0)
        : 0;
      const currentTaskProgress = agent.currentTask && agent.duration
        ? Math.min((agent.duration / 60000) * 15, 90) + Math.random() * 10
        : 0;

      return {
        agent,
        metrics: {
          successRate,
          productivity,
          currentTaskProgress,
        },
      };
    });
  }, [agents]);

  // Calculate performance insights
  const performanceInsights = useMemo(() => {
    const totalTasks = agents.filter((a) => a.currentTask).length;
    const completedEstimate = Math.round(
      totalTasks * (metrics.successRate / 100),
    );
    const avgProductivity = agentPerformanceData.reduce((sum, data) =>
          sum + data.metrics.productivity, 0) / agents.length || 0;

    return {
      completedTasks: completedEstimate,
      pendingTasks: totalTasks - completedEstimate,
      avgProductivity,
      topPerformer: agentPerformanceData.sort((a, b) =>
        b.metrics.successRate - a.metrics.successRate
      )[0]?.agent,
      lowPerformer: agentPerformanceData.sort((a, b) =>
        a.metrics.successRate - b.metrics.successRate
      )[0]?.agent,
    };
  }, [agents, metrics, agentPerformanceData]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent>
          <Box
            display="flex"
            justifyContent="center"
            alignItems="center"
            height={200}
          >
            <Stack spacing={2} alignItems="center">
              <CircularProgress />
              <Typography variant="body2" color="text.secondary">
                Analyzing agent effectiveness...
              </Typography>
            </Stack>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={2}>
            <AgentIcon color="primary" />
            <Typography variant="h6" fontWeight="bold">
              Agent Effectiveness Analytics
            </Typography>
            <Chip
              label={`${metrics.activeAgents} Active`}
              color="primary"
              size="small"
              variant="outlined"
            />
          </Box>
        }
        subtitle="Performance metrics and success rates for intelligent agents"
        action={
          <Stack direction="row" spacing={1} alignItems="center">
            <Tooltip title="Refresh metrics">
              <IconButton size="small" onClick={onRefresh}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title={showDetailedView ? "Collapse" : "Expand"}>
              <IconButton
                size="small"
                onClick={() => setShowDetailedView(!showDetailedView)}
              >
                {showDetailedView ? <CollapseIcon /> : <ExpandIcon />}
              </IconButton>
            </Tooltip>
          </Stack>
        }
      />

      <CardContent>
        {/* Key Performance Metrics */}
        <Grid container spacing={2} mb={3}>
          <Grid item xs={6} md={3}>
            <EffectivenessMetric
              label="Success Rate"
              value={metrics.successRate}
              status={metrics.successRate > 80
                ? "excellent"
                : metrics.successRate > 60
                ? "good"
                : "warning"}
              trend={metrics.successRate > 75
                ? "up"
                : metrics.successRate < 50
                ? "down"
                : "stable"}
              icon={SuccessIcon}
              subtitle="Task completion rate"
              progress={metrics.successRate}
              target={85}
            />
          </Grid>

          <Grid item xs={6} md={3}>
            <EffectivenessMetric
              label="Active Agents"
              value={metrics.activeAgents}
              unit={`/${metrics.totalAgents}`}
              status={metrics.activeAgents > metrics.totalAgents * 0.7
                ? "excellent"
                : "good"}
              icon={AgentIcon}
              subtitle="Currently working"
              progress={(metrics.activeAgents / metrics.totalAgents) * 100}
            />
          </Grid>

          <Grid item xs={6} md={3}>
            <EffectivenessMetric
              label="Avg Duration"
              value={metrics.averageTaskDuration}
              unit="s"
              status={metrics.averageTaskDuration < 30
                ? "excellent"
                : metrics.averageTaskDuration < 60
                ? "good"
                : "warning"}
              trend={metrics.averageTaskDuration < 45 ? "down" : "stable"}
              icon={DurationIcon}
              subtitle="Per task completion"
            />
          </Grid>

          <Grid item xs={6} md={3}>
            <EffectivenessMetric
              label="Throughput"
              value={metrics.throughput}
              unit="tasks/min"
              status={metrics.throughput > 2
                ? "excellent"
                : metrics.throughput > 1
                ? "good"
                : "info"}
              icon={PerformanceIcon}
              subtitle="System productivity"
            />
          </Grid>
        </Grid>

        {/* Performance Summary */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Performance Summary
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <TaskIcon sx={{ fontSize: 16, color: "success.main" }} />
                <Typography variant="body2">
                  Completed: {performanceInsights.completedTasks} tasks
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <Timer sx={{ fontSize: 16, color: "warning.main" }} />
                <Typography variant="body2">
                  Pending: {performanceInsights.pendingTasks} tasks
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <TrendingUpIcon sx={{ fontSize: 16, color: "info.main" }} />
                <Typography variant="body2">
                  Avg Productivity:{" "}
                  {performanceInsights.avgProductivity.toFixed(1)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <ErrorIcon sx={{ fontSize: 16, color: "error.main" }} />
                <Typography variant="body2">
                  Failure Rate: {metrics.failureRate.toFixed(1)}%
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Box>

        {/* Detailed Agent Performance (when expanded) */}
        {showDetailedView && (
          <>
            <Divider sx={{ my: 2 }} />
            <Box>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                gutterBottom
              >
                Individual Agent Performance
              </Typography>
              <Stack spacing={1}>
                {agentPerformanceData.map((
                  { agent, metrics: agentMetrics },
                ) => (
                  <AgentPerformanceRow
                    key={agent.id}
                    agent={agent}
                    metrics={agentMetrics}
                  />
                ))}
              </Stack>
            </Box>
          </>
        )}

        {/* Performance Insights */}
        {performanceInsights.topPerformer && (
          <Box
            sx={{
              mt: 3,
              pt: 2,
              borderTop: `1px solid ${theme.palette.divider}`,
            }}
          >
            <Typography
              variant="caption"
              color="text.secondary"
              gutterBottom
              display="block"
            >
              Performance Insights
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Box display="flex" alignItems="center" gap={1}>
                  <SuccessIcon sx={{ fontSize: 16, color: "success.main" }} />
                  <Typography variant="body2">
                    Top Performer:{" "}
                    <strong>{performanceInsights.topPerformer.role}</strong>
                    ({performanceInsights.topPerformer.domain})
                  </Typography>
                </Box>
              </Grid>
              {performanceInsights.lowPerformer && (
                <Grid item xs={12} md={6}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <ErrorIcon sx={{ fontSize: 16, color: "warning.main" }} />
                    <Typography variant="body2">
                      Needs Attention:{" "}
                      <strong>{performanceInsights.lowPerformer.role}</strong>
                      ({performanceInsights.lowPerformer.domain})
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};
