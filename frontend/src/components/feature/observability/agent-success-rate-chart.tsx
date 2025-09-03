/**
 * Agent Success Rate Chart Component
 * Visualizes agent task success/failure rates and performance metrics
 * MVP feature: Basic success/failure tracking and trending
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
  LinearProgress,
  Paper,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Psychology as AgentIcon,
  Speed as PerformanceIcon,
  Timeline as TrendIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import { AgentPerformanceMetrics } from "@/lib/types/system-metrics";

export interface AgentSuccessRateChartProps {
  agentMetrics: AgentPerformanceMetrics[];
  isLoading?: boolean;
  refreshRate?: number;
  showTrends?: boolean;
  className?: string;
}

interface AgentSummaryCardProps {
  agent: AgentPerformanceMetrics;
  rank: number;
}

const CHART_COLORS = {
  success: "#4caf50",
  failure: "#f44336",
  warning: "#ff9800",
  info: "#2196f3",
  secondary: "#9c27b0",
};

const AgentSummaryCard: React.FC<AgentSummaryCardProps> = ({ agent, rank }) => {
  const theme = useTheme();

  const getPerformanceStatus = (successRate: number) => {
    if (successRate >= 90) return { status: "Excellent", color: "success" };
    if (successRate >= 75) return { status: "Good", color: "info" };
    if (successRate >= 60) return { status: "Fair", color: "warning" };
    return { status: "Poor", color: "error" };
  };

  const performance = getPerformanceStatus(agent.successRate);
  const avgTaskTime = agent.averageTaskDuration / 1000; // Convert to seconds

  return (
    <Card
      sx={{
        height: "100%",
        transition: "all 0.2s ease-in-out",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: theme.shadows[4],
        },
      }}
    >
      <CardContent>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            mb: 2,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Box
              sx={{
                p: 1,
                borderRadius: 2,
                backgroundColor: alpha(theme.palette.primary.main, 0.1),
                color: "primary.main",
              }}
            >
              <AgentIcon />
            </Box>
            <Box>
              <Typography variant="subtitle1" fontWeight={600}>
                {agent.role}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {agent.domain}
              </Typography>
            </Box>
          </Box>

          <Chip
            label={`#${rank}`}
            size="small"
            color="primary"
            variant="outlined"
          />
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Box textAlign="center">
              <Typography variant="h4" color="success.main" fontWeight="bold">
                {agent.successRate.toFixed(1)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Success Rate
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={6}>
            <Box textAlign="center">
              <Typography variant="h4" color="info.main" fontWeight="bold">
                {agent.totalTasks}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Total Tasks
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Box sx={{ mt: 2 }}>
          <LinearProgress
            variant="determinate"
            value={agent.successRate}
            sx={{
              height: 8,
              borderRadius: 4,
              backgroundColor: alpha(theme.palette.grey[300], 0.3),
            }}
            color={performance.color as any}
          />

          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mt: 1,
            }}
          >
            <Chip
              label={performance.status}
              size="small"
              color={performance.color as any}
              sx={{ height: 20 }}
            />
            <Typography variant="caption" color="text.secondary">
              Avg: {avgTaskTime.toFixed(1)}s
            </Typography>
          </Box>
        </Box>

        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            mt: 2,
            pt: 2,
            borderTop: `1px solid ${theme.palette.divider}`,
          }}
        >
          <Box textAlign="center">
            <Typography
              variant="body2"
              color="success.main"
              fontWeight="medium"
            >
              {agent.successfulTasks}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Success
            </Typography>
          </Box>
          <Box textAlign="center">
            <Typography variant="body2" color="error.main" fontWeight="medium">
              {agent.failedTasks}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Failed
            </Typography>
          </Box>
          <Box textAlign="center">
            <Typography
              variant="body2"
              color="warning.main"
              fontWeight="medium"
            >
              {agent.errorRate.toFixed(1)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Error Rate
            </Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export const AgentSuccessRateChart: React.FC<AgentSuccessRateChartProps> = ({
  agentMetrics,
  isLoading = false,
  refreshRate = 10000,
  showTrends = true,
  className,
}) => {
  const theme = useTheme();
  const [viewMode, setViewMode] = useState<
    "overview" | "individual" | "comparison"
  >("overview");

  // Calculate aggregate metrics
  const aggregateMetrics = useMemo(() => {
    if (agentMetrics.length === 0) {
      return {
        totalTasks: 0,
        totalSuccess: 0,
        totalFailures: 0,
        avgSuccessRate: 0,
        avgErrorRate: 0,
        avgTaskDuration: 0,
      };
    }

    const totals = agentMetrics.reduce(
      (acc, agent) => ({
        totalTasks: acc.totalTasks + agent.totalTasks,
        totalSuccess: acc.totalSuccess + agent.successfulTasks,
        totalFailures: acc.totalFailures + agent.failedTasks,
        avgSuccessRate: acc.avgSuccessRate + agent.successRate,
        avgErrorRate: acc.avgErrorRate + agent.errorRate,
        avgTaskDuration: acc.avgTaskDuration + agent.averageTaskDuration,
      }),
      {
        totalTasks: 0,
        totalSuccess: 0,
        totalFailures: 0,
        avgSuccessRate: 0,
        avgErrorRate: 0,
        avgTaskDuration: 0,
      },
    );

    return {
      ...totals,
      avgSuccessRate: totals.avgSuccessRate / agentMetrics.length,
      avgErrorRate: totals.avgErrorRate / agentMetrics.length,
      avgTaskDuration: totals.avgTaskDuration / agentMetrics.length,
    };
  }, [agentMetrics]);

  // Prepare data for charts
  const pieChartData = [
    {
      name: "Successful Tasks",
      value: aggregateMetrics.totalSuccess,
      color: CHART_COLORS.success,
    },
    {
      name: "Failed Tasks",
      value: aggregateMetrics.totalFailures,
      color: CHART_COLORS.failure,
    },
  ];

  const barChartData = agentMetrics.map((agent) => ({
    name: agent.role,
    successRate: agent.successRate,
    errorRate: agent.errorRate,
    totalTasks: agent.totalTasks,
  }));

  // Sort agents by success rate for ranking
  const rankedAgents = [...agentMetrics].sort((a, b) =>
    b.successRate - a.successRate
  );

  if (isLoading) {
    return (
      <Box className={className} sx={{ p: 3 }}>
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          height={300}
        >
          <Stack spacing={2} alignItems="center">
            <CircularProgress />
            <Typography variant="body2" color="text.secondary">
              Loading agent performance metrics...
            </Typography>
          </Stack>
        </Box>
      </Box>
    );
  }

  if (agentMetrics.length === 0) {
    return (
      <Box className={className} sx={{ p: 3 }}>
        <Paper sx={{ p: 4, textAlign: "center" }}>
          <AgentIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No Agent Performance Data
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Agent success/failure metrics will appear once agents start
            executing tasks
          </Typography>
        </Paper>
      </Box>
    );
  }

  return (
    <Box className={className}>
      {/* Header with Controls */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <Box>
          <Typography
            variant="h6"
            fontWeight="bold"
            sx={{ display: "flex", alignItems: "center", gap: 1 }}
          >
            <PerformanceIcon color="primary" />
            Agent Success & Performance Metrics
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Real-time tracking of agent task completion and success rates
          </Typography>
        </Box>

        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={(_, value) => value && setViewMode(value)}
          size="small"
        >
          <ToggleButton value="overview">Overview</ToggleButton>
          <ToggleButton value="individual">Individual</ToggleButton>
          <ToggleButton value="comparison">Compare</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      {/* Aggregate Metrics Summary */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="h4" color="primary.main" fontWeight="bold">
              {agentMetrics.length}
            </Typography>
            <Typography variant="subtitle2" color="text.secondary">
              Active Agents
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="h4" color="success.main" fontWeight="bold">
              {aggregateMetrics.avgSuccessRate.toFixed(1)}%
            </Typography>
            <Typography variant="subtitle2" color="text.secondary">
              Avg Success Rate
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="h4" color="info.main" fontWeight="bold">
              {aggregateMetrics.totalTasks}
            </Typography>
            <Typography variant="subtitle2" color="text.secondary">
              Total Tasks
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="h4" color="warning.main" fontWeight="bold">
              {aggregateMetrics.avgErrorRate.toFixed(1)}%
            </Typography>
            <Typography variant="subtitle2" color="text.secondary">
              Avg Error Rate
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Charts Section */}
      {viewMode === "overview" && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {/* Success/Failure Pie Chart */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                Overall Task Success Distribution
              </Typography>
              <ResponsiveContainer width="100%" height="90%">
                <PieChart>
                  <Pie
                    data={pieChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={120}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip
                    formatter={(value: any) => [value, "Tasks"]}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          {/* Agent Comparison Bar Chart */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                Agent Success Rate Comparison
              </Typography>
              <ResponsiveContainer width="100%" height="90%">
                <BarChart data={barChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 12 }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis domain={[0, 100]} />
                  <RechartsTooltip
                    formatter={(value: any, name: string) => [
                      `${value.toFixed(1)}%`,
                      name === "successRate" ? "Success Rate" : "Error Rate",
                    ]}
                  />
                  <Bar
                    dataKey="successRate"
                    fill={CHART_COLORS.success}
                    name="Success Rate"
                  />
                  <Bar
                    dataKey="errorRate"
                    fill={CHART_COLORS.failure}
                    name="Error Rate"
                  />
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Individual Agent Cards */}
      {(viewMode === "individual" || viewMode === "comparison") && (
        <Grid container spacing={3}>
          {rankedAgents.map((agent, index) => (
            <Grid item xs={12} sm={6} md={4} key={agent.agentId}>
              <AgentSummaryCard agent={agent} rank={index + 1} />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Performance Insights */}
      <Paper sx={{ p: 3, mt: 4 }}>
        <Typography
          variant="h6"
          gutterBottom
          sx={{ display: "flex", alignItems: "center", gap: 1 }}
        >
          <TrendIcon color="info" />
          Performance Insights
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              {aggregateMetrics.avgSuccessRate >= 85
                ? <SuccessIcon sx={{ color: "success.main", fontSize: 20 }} />
                : aggregateMetrics.avgSuccessRate >= 70
                ? <WarningIcon sx={{ color: "warning.main", fontSize: 20 }} />
                : <ErrorIcon sx={{ color: "error.main", fontSize: 20 }} />}
              <Typography variant="body2">
                System Performance: {aggregateMetrics.avgSuccessRate >= 85
                  ? "Excellent"
                  : aggregateMetrics.avgSuccessRate >= 70
                  ? "Good"
                  : "Needs Attention"}
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={12} md={4}>
            <Typography variant="body2" color="text.secondary">
              <strong>Best Performer:</strong> {rankedAgents[0]?.role || "N/A"}
              {" "}
              ({rankedAgents[0]?.successRate.toFixed(1)}%)
            </Typography>
          </Grid>

          <Grid item xs={12} md={4}>
            <Typography variant="body2" color="text.secondary">
              <strong>Avg Task Duration:</strong>{" "}
              {(aggregateMetrics.avgTaskDuration / 1000).toFixed(1)}s
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
};
