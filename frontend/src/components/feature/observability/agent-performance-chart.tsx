/**
 * Agent Performance Chart Component
 * MVP focus: Agent success/failure rates, task completion metrics
 * Visualizes agent effectiveness and coordination health
 */

import React, { useMemo, useState } from "react";
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  IconButton,
  LinearProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  FilterList as FilterIcon,
  Psychology as AgentIcon,
  Refresh as RefreshIcon,
  Speed as PerformanceIcon,
  Timer as TimerIcon,
  TrendingDown as TrendingDownIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

interface Agent {
  id: string;
  role: string;
  domain: string;
  status: "active" | "idle" | "error";
  currentTask?: string;
  duration?: number;
  sessionId: string;
}

interface CoordinationMetrics {
  conflictsPrevented: number;
  taskDeduplicationRate: number;
  averageTaskCompletionTime: number;
  activeAgents: number;
  activeSessions: number;
}

interface AgentPerformanceChartProps {
  agents: Agent[];
  coordinationMetrics?: CoordinationMetrics;
  isLoading: boolean;
}

interface AgentStats {
  id: string;
  role: string;
  domain: string;
  status: "active" | "idle" | "error";
  successRate: number;
  tasksCompleted: number;
  avgCompletionTime: number;
  lastActivity: string;
  efficiency: number;
}

// Simulate historical agent performance data
const generateAgentStats = (agents: Agent[]): AgentStats[] => {
  return agents.map((agent) => {
    // Simulate performance metrics (in production, this would come from analytics service)
    const successRate = agent.status === "error"
      ? Math.random() * 50 + 20 // 20-70% for error agents
      : Math.random() * 30 + 70; // 70-100% for active/idle agents

    const tasksCompleted = Math.floor(Math.random() * 20) + 1;
    const avgCompletionTime = Math.random() * 5000 + 1000; // 1-6 seconds
    const efficiency = successRate * 0.7 +
      (6000 - avgCompletionTime) / 6000 * 0.3 * 100;

    return {
      id: agent.id,
      role: agent.role,
      domain: agent.domain,
      status: agent.status,
      successRate,
      tasksCompleted,
      avgCompletionTime,
      lastActivity: agent.status === "active"
        ? "Just now"
        : `${Math.floor(Math.random() * 60)} min ago`,
      efficiency: Math.min(efficiency, 100),
    };
  });
};

interface PerformanceOverviewProps {
  agents: Agent[];
  stats: AgentStats[];
  coordinationMetrics?: CoordinationMetrics;
}

const PerformanceOverview: React.FC<PerformanceOverviewProps> = ({
  agents,
  stats,
  coordinationMetrics,
}) => {
  const theme = useTheme();

  const overallMetrics = useMemo(() => {
    const totalAgents = agents.length;
    const activeAgents = agents.filter((a) => a.status === "active").length;
    const errorAgents = agents.filter((a) => a.status === "error").length;
    const idleAgents = agents.filter((a) => a.status === "idle").length;

    const avgSuccessRate = stats.length > 0
      ? stats.reduce((sum, stat) => sum + stat.successRate, 0) / stats.length
      : 0;

    const totalTasksCompleted = stats.reduce(
      (sum, stat) => sum + stat.tasksCompleted,
      0,
    );
    const avgEfficiency = stats.length > 0
      ? stats.reduce((sum, stat) => sum + stat.efficiency, 0) / stats.length
      : 0;

    return {
      totalAgents,
      activeAgents,
      errorAgents,
      idleAgents,
      avgSuccessRate,
      totalTasksCompleted,
      avgEfficiency,
      healthScore: (activeAgents / Math.max(totalAgents, 1)) * 100,
    };
  }, [agents, stats]);

  return (
    <Grid container spacing={3}>
      {/* Overall Success Rate */}
      <Grid item xs={12} sm={6} md={3}>
        <Card
          sx={{
            background: `linear-gradient(135deg, ${
              alpha(theme.palette.success.main, 0.1)
            }, ${alpha(theme.palette.success.light, 0.05)})`,
            border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
          }}
        >
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
              <SuccessIcon sx={{ color: "success.main", mr: 1 }} />
              <Typography variant="subtitle2" fontWeight={600}>
                Overall Success Rate
              </Typography>
            </Box>
            <Typography
              variant="h3"
              sx={{ fontWeight: 700, color: "success.main", mb: 1 }}
            >
              {overallMetrics.avgSuccessRate.toFixed(1)}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Across all agents
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      {/* Active Agents */}
      <Grid item xs={12} sm={6} md={3}>
        <Card
          sx={{
            background: `linear-gradient(135deg, ${
              alpha(theme.palette.primary.main, 0.1)
            }, ${alpha(theme.palette.primary.light, 0.05)})`,
            border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
          }}
        >
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
              <AgentIcon sx={{ color: "primary.main", mr: 1 }} />
              <Typography variant="subtitle2" fontWeight={600}>
                Agent Status
              </Typography>
            </Box>
            <Box
              sx={{ display: "flex", alignItems: "baseline", gap: 1, mb: 1 }}
            >
              <Typography
                variant="h3"
                sx={{ fontWeight: 700, color: "primary.main" }}
              >
                {overallMetrics.activeAgents}
              </Typography>
              <Typography variant="h6" color="text.secondary">
                / {overallMetrics.totalAgents}
              </Typography>
            </Box>
            <Stack direction="row" spacing={1}>
              <Chip
                label={`${overallMetrics.errorAgents} errors`}
                size="small"
                color="error"
              />
              <Chip
                label={`${overallMetrics.idleAgents} idle`}
                size="small"
                color="default"
              />
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      {/* Task Throughput */}
      <Grid item xs={12} sm={6} md={3}>
        <Card
          sx={{
            background: `linear-gradient(135deg, ${
              alpha(theme.palette.info.main, 0.1)
            }, ${alpha(theme.palette.info.light, 0.05)})`,
            border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
          }}
        >
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
              <PerformanceIcon sx={{ color: "info.main", mr: 1 }} />
              <Typography variant="subtitle2" fontWeight={600}>
                Task Throughput
              </Typography>
            </Box>
            <Typography
              variant="h3"
              sx={{ fontWeight: 700, color: "info.main", mb: 1 }}
            >
              {overallMetrics.totalTasksCompleted}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Tasks completed
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      {/* System Health */}
      <Grid item xs={12} sm={6} md={3}>
        <Card
          sx={{
            background: `linear-gradient(135deg, ${
              alpha(theme.palette.warning.main, 0.1)
            }, ${alpha(theme.palette.warning.light, 0.05)})`,
            border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
          }}
        >
          <CardContent>
            <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
              <TimerIcon sx={{ color: "warning.main", mr: 1 }} />
              <Typography variant="subtitle2" fontWeight={600}>
                Avg Efficiency
              </Typography>
            </Box>
            <Typography
              variant="h3"
              sx={{ fontWeight: 700, color: "warning.main", mb: 1 }}
            >
              {overallMetrics.avgEfficiency.toFixed(1)}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Performance score
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export const AgentPerformanceChart: React.FC<AgentPerformanceChartProps> = ({
  agents,
  coordinationMetrics,
  isLoading,
}) => {
  const theme = useTheme();
  const [sortBy, setSortBy] = useState<
    "successRate" | "efficiency" | "tasksCompleted"
  >("successRate");

  const agentStats = useMemo(() => generateAgentStats(agents), [agents]);

  const sortedStats = useMemo(() => {
    return [...agentStats].sort((a, b) => b[sortBy] - a[sortBy]);
  }, [agentStats, sortBy]);

  if (isLoading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: 400,
        }}
      >
        <Stack spacing={2} alignItems="center">
          <CircularProgress />
          <Typography variant="body2" color="text.secondary">
            Loading agent performance data...
          </Typography>
        </Stack>
      </Box>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "success";
      case "idle":
        return "default";
      case "error":
        return "error";
      default:
        return "default";
    }
  };

  const getPerformanceIcon = (rate: number) => {
    if (rate >= 90) {
      return <SuccessIcon sx={{ color: "success.main", fontSize: 20 }} />;
    }
    if (rate >= 70) {
      return <WarningIcon sx={{ color: "warning.main", fontSize: 20 }} />;
    }
    return <ErrorIcon sx={{ color: "error.main", fontSize: 20 }} />;
  };

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Typography variant="h6" fontWeight={600}>
          Agent Performance Analytics
        </Typography>

        <Box sx={{ display: "flex", gap: 1 }}>
          <Tooltip title="Refresh data">
            <IconButton size="small">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Filter options">
            <IconButton size="small">
              <FilterIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Performance Overview Cards */}
      <Box sx={{ mb: 4 }}>
        <PerformanceOverview
          agents={agents}
          stats={agentStats}
          coordinationMetrics={coordinationMetrics}
        />
      </Box>

      {/* Detailed Agent Performance Table */}
      <Paper>
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <Typography variant="h6" fontWeight={600}>
            Individual Agent Performance
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Detailed metrics for each agent including success rates and task
            completion data
          </Typography>
        </Box>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Agent</TableCell>
                <TableCell>Status</TableCell>
                <TableCell
                  sx={{ cursor: "pointer" }}
                  onClick={() => setSortBy("successRate")}
                >
                  Success Rate{" "}
                  {sortBy === "successRate" && (
                    <TrendingDownIcon sx={{ fontSize: 16 }} />
                  )}
                </TableCell>
                <TableCell
                  sx={{ cursor: "pointer" }}
                  onClick={() => setSortBy("tasksCompleted")}
                >
                  Tasks{" "}
                  {sortBy === "tasksCompleted" && (
                    <TrendingDownIcon sx={{ fontSize: 16 }} />
                  )}
                </TableCell>
                <TableCell>Avg Time</TableCell>
                <TableCell
                  sx={{ cursor: "pointer" }}
                  onClick={() => setSortBy("efficiency")}
                >
                  Efficiency{" "}
                  {sortBy === "efficiency" && (
                    <TrendingDownIcon sx={{ fontSize: 16 }} />
                  )}
                </TableCell>
                <TableCell>Last Activity</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedStats.map((stat) => (
                <TableRow
                  key={stat.id}
                  sx={{
                    "&:hover": {
                      bgcolor: alpha(theme.palette.primary.main, 0.04),
                    },
                    opacity: stat.status === "error" ? 0.7 : 1,
                  }}
                >
                  <TableCell>
                    <Box>
                      <Typography variant="body2" fontWeight={600}>
                        {stat.role}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {stat.domain} • {stat.id.slice(-8)}
                      </Typography>
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Chip
                      label={stat.status}
                      size="small"
                      color={getStatusColor(stat.status) as any}
                      variant={stat.status === "active" ? "filled" : "outlined"}
                    />
                  </TableCell>

                  <TableCell>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      {getPerformanceIcon(stat.successRate)}
                      <Box>
                        <Typography variant="body2" fontWeight={600}>
                          {stat.successRate.toFixed(1)}%
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={stat.successRate}
                          sx={{
                            width: 60,
                            height: 4,
                            backgroundColor: alpha(
                              theme.palette.grey[300],
                              0.3,
                            ),
                          }}
                          color={stat.successRate >= 90
                            ? "success"
                            : stat.successRate >= 70
                            ? "warning"
                            : "error"}
                        />
                      </Box>
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {stat.tasksCompleted}
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2">
                      {(stat.avgCompletionTime / 1000).toFixed(1)}s
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="body2" fontWeight={600}>
                        {stat.efficiency.toFixed(1)}%
                      </Typography>
                      {stat.efficiency >= 80
                        ? (
                          <TrendingUpIcon
                            sx={{ fontSize: 16, color: "success.main" }}
                          />
                        )
                        : (
                          <TrendingDownIcon
                            sx={{ fontSize: 16, color: "error.main" }}
                          />
                        )}
                    </Box>
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {stat.lastActivity}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {sortedStats.length === 0 && (
          <Box sx={{ p: 4, textAlign: "center" }}>
            <AgentIcon sx={{ fontSize: 48, color: "text.secondary", mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No Agents Available
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Deploy agents to start tracking performance metrics
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
};
