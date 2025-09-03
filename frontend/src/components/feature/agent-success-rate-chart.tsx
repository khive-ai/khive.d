/**
 * Agent Success Rate Chart Component
 * Displays agent effectiveness metrics and success/failure rates over time
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  Avatar,
  Box,
  Chip,
  Grid,
  LinearProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
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
  Pause as IdleIcon,
  PlayArrow as ActiveIcon,
} from "@mui/icons-material";

interface Agent {
  id: string;
  role: string;
  domain: string;
  status: "active" | "idle" | "error";
  currentTask?: string;
  duration?: number;
  sessionId: string;
  name?: string;
  tasks?: number;
  lastActivity?: string;
}

interface AgentMetricDataPoint {
  timestamp: string;
  successRate: number;
  activeAgents: number;
  totalAgents: number;
  errorAgents: number;
  taskCompletions: number;
}

export interface AgentSuccessRateChartProps {
  agents: Agent[];
  refreshInterval: number;
  enableRealTime: boolean;
  className?: string;
}

export const AgentSuccessRateChart: React.FC<AgentSuccessRateChartProps> = ({
  agents,
  refreshInterval,
  enableRealTime,
  className,
}) => {
  const [chartType, setChartType] = useState<"overview" | "trends" | "details">(
    "overview",
  );
  const [dataPoints, setDataPoints] = useState<AgentMetricDataPoint[]>([]);
  const [maxDataPoints] = useState(30);

  // Calculate current agent metrics
  const agentMetrics = useMemo(() => {
    const totalAgents = agents.length;
    const activeAgents = agents.filter((a) => a.status === "active").length;
    const errorAgents = agents.filter((a) => a.status === "error").length;
    const idleAgents = agents.filter((a) => a.status === "idle").length;

    const successRate = totalAgents > 0
      ? ((totalAgents - errorAgents) / totalAgents) * 100
      : 100;
    const efficiency = totalAgents > 0 ? (activeAgents / totalAgents) * 100 : 0;

    return {
      totalAgents,
      activeAgents,
      errorAgents,
      idleAgents,
      successRate,
      efficiency,
    };
  }, [agents]);

  // Update metrics over time for trend analysis
  useEffect(() => {
    if (!enableRealTime) return;

    const newDataPoint: AgentMetricDataPoint = {
      timestamp: new Date().toLocaleTimeString(),
      successRate: agentMetrics.successRate,
      activeAgents: agentMetrics.activeAgents,
      totalAgents: agentMetrics.totalAgents,
      errorAgents: agentMetrics.errorAgents,
      taskCompletions: agents.reduce(
        (sum, agent) => sum + (agent.tasks || 0),
        0,
      ),
    };

    setDataPoints((prev) => {
      const updated = [...prev, newDataPoint];
      return updated.slice(-maxDataPoints);
    });
  }, [agentMetrics, agents, enableRealTime, maxDataPoints]);

  // Data for pie chart
  const statusDistribution = [
    { name: "Active", value: agentMetrics.activeAgents, color: "#4caf50" },
    { name: "Idle", value: agentMetrics.idleAgents, color: "#ff9800" },
    { name: "Error", value: agentMetrics.errorAgents, color: "#f44336" },
  ].filter((item) => item.value > 0);

  // Data for role distribution
  const roleDistribution = useMemo(() => {
    const roleCount = agents.reduce((acc, agent) => {
      acc[agent.role] = (acc[agent.role] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(roleCount).map(([role, count]) => ({
      role,
      count,
      successRate: agents.filter((a) =>
        a.role === role && a.status !== "error"
      ).length / count * 100,
    }));
  }, [agents]);

  const getStatusIcon = (status: Agent["status"]) => {
    switch (status) {
      case "active":
        return <ActiveIcon color="success" />;
      case "idle":
        return <IdleIcon color="warning" />;
      case "error":
        return <ErrorIcon color="error" />;
      default:
        return null;
    }
  };

  const getAvatarColor = (role: string) => {
    const colors = [
      "#1976d2",
      "#dc004e",
      "#2e7d32",
      "#ed6c02",
      "#9c27b0",
      "#00acc1",
    ];
    return colors[role.charCodeAt(0) % colors.length];
  };

  const renderOverviewChart = () => (
    <Grid container spacing={3}>
      {/* Status Distribution Pie Chart */}
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2, height: 300 }}>
          <Typography variant="h6" gutterBottom>
            Agent Status Distribution
          </Typography>
          {statusDistribution.length > 0
            ? (
              <ResponsiveContainer width="100%" height="80%">
                <PieChart>
                  <Pie
                    data={statusDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {statusDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip
                    formatter={(
                      value: number,
                      name: string,
                    ) => [value, `${name} Agents`]}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )
            : (
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "80%",
                }}
              >
                <Typography color="text.secondary">
                  No agents available
                </Typography>
              </Box>
            )}
        </Paper>
      </Grid>

      {/* Role Performance Bar Chart */}
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2, height: 300 }}>
          <Typography variant="h6" gutterBottom>
            Performance by Role
          </Typography>
          {roleDistribution.length > 0
            ? (
              <ResponsiveContainer width="100%" height="80%">
                <BarChart data={roleDistribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="role" tick={{ fontSize: 12 }} />
                  <YAxis />
                  <RechartsTooltip
                    formatter={(value: number, name: string) => [
                      `${value}${name === "successRate" ? "%" : ""}`,
                      name === "successRate" ? "Success Rate" : "Agent Count",
                    ]}
                  />
                  <Bar dataKey="count" fill="#1976d2" name="Agent Count" />
                  <Bar
                    dataKey="successRate"
                    fill="#4caf50"
                    name="Success Rate"
                  />
                </BarChart>
              </ResponsiveContainer>
            )
            : (
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "80%",
                }}
              >
                <Typography color="text.secondary">
                  No role data available
                </Typography>
              </Box>
            )}
        </Paper>
      </Grid>
    </Grid>
  );

  const renderTrendsChart = () => (
    <Paper sx={{ p: 2, height: 400 }}>
      <Typography variant="h6" gutterBottom>
        Agent Performance Trends
      </Typography>
      {dataPoints.length > 2
        ? (
          <ResponsiveContainer width="100%" height="90%">
            <LineChart data={dataPoints}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="timestamp"
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => {
                  const parts = value.split(":");
                  return `${parts[0]}:${parts[1]}`;
                }}
              />
              <YAxis />
              <RechartsTooltip
                formatter={(value: number, name: string) => [
                  name === "successRate" ? `${value.toFixed(1)}%` : value,
                  name === "successRate"
                    ? "Success Rate"
                    : name === "activeAgents"
                    ? "Active Agents"
                    : name === "errorAgents"
                    ? "Error Agents"
                    : name,
                ]}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="successRate"
                stroke="#4caf50"
                strokeWidth={2}
                name="Success Rate"
              />
              <Line
                type="monotone"
                dataKey="activeAgents"
                stroke="#1976d2"
                strokeWidth={2}
                name="Active Agents"
              />
              <Line
                type="monotone"
                dataKey="errorAgents"
                stroke="#f44336"
                strokeWidth={2}
                name="Error Agents"
              />
            </LineChart>
          </ResponsiveContainer>
        )
        : (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "90%",
            }}
          >
            <Typography color="text.secondary">
              Collecting trend data... Need at least 3 data points
            </Typography>
          </Box>
        )}
    </Paper>
  );

  const renderDetailsTable = () => (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Agent</TableCell>
            <TableCell>Role</TableCell>
            <TableCell>Domain</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Current Task</TableCell>
            <TableCell>Performance</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {agents.map((agent) => (
            <TableRow key={agent.id}>
              <TableCell>
                <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                  <Avatar
                    sx={{
                      width: 32,
                      height: 32,
                      bgcolor: getAvatarColor(agent.role),
                      fontSize: "0.875rem",
                    }}
                  >
                    {agent.role.charAt(0).toUpperCase()}
                  </Avatar>
                  <Box>
                    <Typography variant="body2" fontWeight={600}>
                      {agent.name || `Agent ${agent.id.slice(-8)}`}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {agent.id.slice(-8)}
                    </Typography>
                  </Box>
                </Box>
              </TableCell>
              <TableCell>
                <Chip
                  label={agent.role}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
              </TableCell>
              <TableCell>
                <Chip
                  label={agent.domain}
                  size="small"
                  color="secondary"
                  variant="outlined"
                />
              </TableCell>
              <TableCell>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  {getStatusIcon(agent.status)}
                  <Typography variant="body2">
                    {agent.status}
                  </Typography>
                </Box>
              </TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ maxWidth: 200 }} noWrap>
                  {agent.currentTask || "No active task"}
                </Typography>
              </TableCell>
              <TableCell>
                <Box sx={{ minWidth: 120 }}>
                  <Box
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 1,
                      mb: 1,
                    }}
                  >
                    <LinearProgress
                      variant="determinate"
                      value={agent.status === "error"
                        ? 0
                        : agent.status === "active"
                        ? 75
                        : 50}
                      sx={{
                        flex: 1,
                        height: 6,
                        borderRadius: 3,
                        "& .MuiLinearProgress-bar": {
                          backgroundColor: agent.status === "error"
                            ? "error.main"
                            : agent.status === "active"
                            ? "success.main"
                            : "warning.main",
                        },
                      }}
                    />
                    <Typography variant="caption">
                      {agent.tasks || 0}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {agent.lastActivity || "No recent activity"}
                  </Typography>
                </Box>
              </TableCell>
            </TableRow>
          ))}
          {agents.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} align="center">
                <Typography color="text.secondary" sx={{ py: 4 }}>
                  No agents available for monitoring
                </Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <Box className={className}>
      {/* Chart Controls */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 3,
        }}
      >
        <ToggleButtonGroup
          value={chartType}
          exclusive
          onChange={(_, value) => value && setChartType(value)}
          size="small"
        >
          <ToggleButton value="overview">
            <SuccessIcon sx={{ mr: 1 }} />
            Overview
          </ToggleButton>
          <ToggleButton value="trends">
            Trends
          </ToggleButton>
          <ToggleButton value="details">
            Details
          </ToggleButton>
        </ToggleButtonGroup>

        <Box sx={{ display: "flex", gap: 1 }}>
          <Chip
            label={`${agentMetrics.successRate.toFixed(1)}% Success`}
            color="success"
            size="small"
          />
          <Chip
            label={`${agentMetrics.totalAgents} Total Agents`}
            variant="outlined"
            size="small"
          />
        </Box>
      </Box>

      {/* Metrics Summary */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}>
          <Paper sx={{ p: 2, textAlign: "center", bgcolor: "success.light" }}>
            <Typography variant="h4" color="success.main" fontWeight="bold">
              {agentMetrics.activeAgents}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Active Agents
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={6} md={3}>
          <Paper sx={{ p: 2, textAlign: "center", bgcolor: "warning.light" }}>
            <Typography variant="h4" color="warning.main" fontWeight="bold">
              {agentMetrics.idleAgents}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Idle Agents
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={6} md={3}>
          <Paper sx={{ p: 2, textAlign: "center", bgcolor: "error.light" }}>
            <Typography variant="h4" color="error.main" fontWeight="bold">
              {agentMetrics.errorAgents}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Error Agents
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={6} md={3}>
          <Paper sx={{ p: 2, textAlign: "center", bgcolor: "info.light" }}>
            <Typography variant="h4" color="info.main" fontWeight="bold">
              {agentMetrics.efficiency.toFixed(0)}%
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Efficiency
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Dynamic Chart Content */}
      {chartType === "overview" && renderOverviewChart()}
      {chartType === "trends" && renderTrendsChart()}
      {chartType === "details" && renderDetailsTable()}
    </Box>
  );
};
