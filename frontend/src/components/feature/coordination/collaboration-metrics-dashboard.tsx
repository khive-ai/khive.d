/**
 * Collaboration Metrics Dashboard Component
 * Simple collaboration metric display showing key coordination statistics
 */

import React, { useMemo } from "react";
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  AccessTime as TimeIcon,
  CheckCircle as SuccessIcon,
  Group as SessionIcon,
  Lock as LockIcon,
  Psychology as AgentIcon,
  Security as ConflictIcon,
  Speed as MetricsIcon,
  Timeline as EfficiencyIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import { Agent, CoordinationMetrics, FileLock } from "@/lib/types";

export interface CollaborationMetricsDashboardProps {
  metrics?: CoordinationMetrics;
  agents?: Agent[];
  fileLocks?: FileLock[];
  isLoading?: boolean;
  isRealTime?: boolean;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  color: "primary" | "secondary" | "success" | "warning" | "error" | "info";
  trend?: "up" | "down" | "stable";
  progress?: number;
  maxProgress?: number;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  trend,
  progress,
  maxProgress = 100,
}) => {
  const theme = useTheme();

  const getTrendColor = () => {
    switch (trend) {
      case "up":
        return "success";
      case "down":
        return "error";
      case "stable":
        return "info";
      default:
        return "default";
    }
  };

  const formatValue = () => {
    if (typeof value === "number") {
      if (value > 1000) {
        return `${(value / 1000).toFixed(1)}k`;
      }
      return value.toLocaleString();
    }
    return value;
  };

  return (
    <Paper
      sx={{
        p: 2.5,
        height: "100%",
        background: `linear-gradient(135deg, ${
          alpha(theme.palette[color].main, 0.05)
        } 0%, ${alpha(theme.palette[color].main, 0.02)} 100%)`,
        border: `1px solid ${alpha(theme.palette[color].main, 0.12)}`,
        transition: "all 0.3s ease-in-out",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: theme.shadows[8],
          border: `1px solid ${alpha(theme.palette[color].main, 0.25)}`,
        },
      }}
    >
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="flex-start"
        mb={2}
      >
        <Box>
          <Typography
            variant="body2"
            color="text.secondary"
            fontWeight="medium"
            sx={{ mb: 0.5 }}
          >
            {title}
          </Typography>
          <Typography
            variant="h4"
            fontWeight="bold"
            color={`${color}.main`}
            sx={{ lineHeight: 1.2 }}
          >
            {formatValue()}
          </Typography>
        </Box>

        <Box
          sx={{
            p: 1,
            borderRadius: "12px",
            backgroundColor: alpha(theme.palette[color].main, 0.1),
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon sx={{ fontSize: 24, color: `${color}.main` }} />
        </Box>
      </Box>

      {subtitle && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ mb: 1, display: "block" }}
        >
          {subtitle}
        </Typography>
      )}

      {progress !== undefined && (
        <Box sx={{ mt: 1.5 }}>
          <LinearProgress
            variant="determinate"
            value={(progress / maxProgress) * 100}
            color={color}
            sx={{
              height: 6,
              borderRadius: 3,
              backgroundColor: alpha(theme.palette[color].main, 0.1),
            }}
          />
        </Box>
      )}

      {trend && (
        <Box sx={{ mt: 1 }}>
          <Chip
            size="small"
            label={trend}
            color={getTrendColor() as any}
            sx={{ height: 20, fontSize: "0.75rem" }}
          />
        </Box>
      )}
    </Paper>
  );
};

export const CollaborationMetricsDashboard: React.FC<
  CollaborationMetricsDashboardProps
> = ({
  metrics,
  agents = [],
  fileLocks = [],
  isLoading = false,
  isRealTime = true,
}) => {
  const theme = useTheme();

  // Calculate additional metrics from available data
  const calculatedMetrics = useMemo(() => {
    const activeAgents = agents.filter((a) => a.status === "active").length;
    const errorAgents = agents.filter((a) => a.status === "error").length;
    const activeFileLocks = fileLocks.filter((lock) => !lock.isStale).length;
    const staleFileLocks = fileLocks.filter((lock) => lock.isStale).length;

    // Calculate efficiency score based on conflicts prevented vs total operations
    const totalOperations = (metrics?.conflictsPrevented || 0) +
      activeAgents * 5; // Rough estimate
    const efficiencyScore = totalOperations > 0
      ? Math.min(
        ((totalOperations - (metrics?.conflictsPrevented || 0)) /
          totalOperations) * 100,
        100,
      )
      : 100;

    return {
      activeAgents,
      errorAgents,
      activeFileLocks,
      staleFileLocks,
      efficiencyScore,
      totalOperations,
    };
  }, [agents, fileLocks, metrics]);

  if (isLoading) {
    return (
      <Card>
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
                Loading collaboration metrics...
              </Typography>
            </Stack>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={3}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <MetricsIcon color="primary" />
            <Typography variant="h6" fontWeight="bold">
              Collaboration Metrics
            </Typography>
            {isRealTime && (
              <Chip
                label="Live"
                color="success"
                size="small"
                variant="outlined"
                sx={{ height: 22 }}
              />
            )}
          </Box>

          <Typography variant="caption" color="text.secondary">
            Real-time coordination insights
          </Typography>
        </Box>

        <Grid container spacing={3}>
          {/* Active Agents */}
          <Grid item xs={6} sm={4} md={2}>
            <MetricCard
              title="Active Agents"
              value={calculatedMetrics.activeAgents}
              subtitle={`${calculatedMetrics.errorAgents} with errors`}
              icon={AgentIcon}
              color="primary"
              trend={calculatedMetrics.activeAgents > 0 ? "up" : "stable"}
            />
          </Grid>

          {/* Active Sessions */}
          <Grid item xs={6} sm={4} md={2}>
            <MetricCard
              title="Sessions"
              value={metrics?.activeSessions || 0}
              subtitle="Coordination sessions"
              icon={SessionIcon}
              color="secondary"
              trend={metrics?.activeSessions && metrics.activeSessions > 0
                ? "up"
                : "stable"}
            />
          </Grid>

          {/* Conflicts Prevented */}
          <Grid item xs={6} sm={4} md={2}>
            <MetricCard
              title="Conflicts Prevented"
              value={metrics?.conflictsPrevented || 0}
              subtitle="File & task conflicts"
              icon={ConflictIcon}
              color="success"
              trend="stable"
            />
          </Grid>

          {/* Efficiency Score */}
          <Grid item xs={6} sm={4} md={2}>
            <MetricCard
              title="Efficiency"
              value={`${calculatedMetrics.efficiencyScore.toFixed(1)}%`}
              subtitle="Coordination effectiveness"
              icon={EfficiencyIcon}
              color="info"
              progress={calculatedMetrics.efficiencyScore}
              trend={calculatedMetrics.efficiencyScore > 80
                ? "up"
                : calculatedMetrics.efficiencyScore > 60
                ? "stable"
                : "down"}
            />
          </Grid>

          {/* Average Completion Time */}
          <Grid item xs={6} sm={4} md={2}>
            <MetricCard
              title="Avg Time"
              value={metrics?.averageTaskCompletionTime
                ? `${(metrics.averageTaskCompletionTime / 1000).toFixed(1)}s`
                : "N/A"}
              subtitle="Task completion"
              icon={TimeIcon}
              color="warning"
              trend="stable"
            />
          </Grid>

          {/* File Locks */}
          <Grid item xs={6} sm={4} md={2}>
            <MetricCard
              title="File Locks"
              value={calculatedMetrics.activeFileLocks}
              subtitle={`${calculatedMetrics.staleFileLocks} stale`}
              icon={LockIcon}
              color={calculatedMetrics.staleFileLocks > 0 ? "error" : "success"}
              trend={calculatedMetrics.activeFileLocks > 0 ? "up" : "stable"}
            />
          </Grid>
        </Grid>

        {/* Performance Summary */}
        <Box
          sx={{ mt: 3, pt: 3, borderTop: `1px solid ${theme.palette.divider}` }}
        >
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Performance Summary
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={4}>
              <Box display="flex" alignItems="center" gap={1}>
                <SuccessIcon sx={{ fontSize: 16, color: "success.main" }} />
                <Typography variant="body2">
                  Task Deduplication: {metrics?.taskDeduplicationRate
                    ? `${(metrics.taskDeduplicationRate * 100).toFixed(1)}%`
                    : "N/A"}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Box display="flex" alignItems="center" gap={1}>
                {calculatedMetrics.errorAgents > 0
                  ? <WarningIcon sx={{ fontSize: 16, color: "warning.main" }} />
                  : (
                    <SuccessIcon
                      sx={{ fontSize: 16, color: "success.main" }}
                    />
                  )}
                <Typography variant="body2">
                  Agent Health: {calculatedMetrics.activeAgents > 0
                    ? `${
                      Math.round(
                        (1 -
                          calculatedMetrics.errorAgents /
                            calculatedMetrics.activeAgents) * 100,
                      )
                    }%`
                    : "N/A"}
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={12} sm={6} md={4}>
              <Box display="flex" alignItems="center" gap={1}>
                {calculatedMetrics.staleFileLocks > 0
                  ? <WarningIcon sx={{ fontSize: 16, color: "warning.main" }} />
                  : (
                    <SuccessIcon
                      sx={{ fontSize: 16, color: "success.main" }}
                    />
                  )}
                <Typography variant="body2">
                  File Lock Health: {fileLocks.length > 0
                    ? `${
                      Math.round(
                        (1 -
                          calculatedMetrics.staleFileLocks / fileLocks.length) *
                          100,
                      )
                    }%`
                    : "100%"}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </Box>
      </CardContent>
    </Card>
  );
};
