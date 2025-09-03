/**
 * Observability Console MVP - Main Dashboard
 * Real-time system performance monitoring and agent effectiveness analytics
 */

"use client";

import React, { useEffect, useState } from "react";
import {
  Alert,
  AlertTitle,
  Box,
  Card,
  CardContent,
  CardHeader,
  Divider,
  FormControlLabel,
  Grid,
  Paper,
  Switch,
  Typography,
} from "@mui/material";
import {
  Assessment as AssessmentIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Memory as MemoryIcon,
  Psychology as AgentIcon,
  Speed as CpuIcon,
  Timeline as TimelineIcon,
} from "@mui/icons-material";

import { usePerformance } from "@/lib/hooks/usePerformance";
import {
  useAgents,
  useCoordinationMetrics,
  useSessions,
} from "@/lib/api/hooks";
import { CollaborationMetricsPanel } from "@/components/feature/collaboration-metrics-panel";
import { AgentStatus } from "@/components/feature/agent-status";
import { SessionMonitor } from "@/components/feature/session-monitor";
import { PerformanceMetricsChart } from "@/components/feature/performance-metrics-chart";
import { AgentSuccessRateChart } from "@/components/feature/agent-success-rate-chart";

export default function ObservabilityPage() {
  const [refreshInterval, setRefreshInterval] = useState(5000); // 5 seconds
  const [enableRealTime, setEnableRealTime] = useState(true);

  // Fetch real-time data
  const performanceData = usePerformance("ObservabilityConsole", true);
  const { data: coordinationMetrics, isLoading: metricsLoading } =
    useCoordinationMetrics();
  const { data: agents, isLoading: agentsLoading } = useAgents();
  const { data: sessions, isLoading: sessionsLoading } = useSessions();

  // Auto-refresh logic
  useEffect(() => {
    if (!enableRealTime) return;

    const interval = setInterval(() => {
      // Trigger data refetch - this would normally use a refetch function from react-query
      console.log("Refreshing observability data...");
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [enableRealTime, refreshInterval]);

  // Calculate agent success/failure rates
  const agentMetrics = React.useMemo(() => {
    if (!agents) {
      return {
        successRate: 0,
        totalAgents: 0,
        activeAgents: 0,
        errorAgents: 0,
      };
    }

    const totalAgents = agents.length;
    const activeAgents = agents.filter((a) => a.status === "active").length;
    const errorAgents = agents.filter((a) => a.status === "error").length;
    const successRate = totalAgents > 0
      ? ((totalAgents - errorAgents) / totalAgents) * 100
      : 100;

    return { successRate, totalAgents, activeAgents, errorAgents };
  }, [agents]);

  // System health status
  const systemHealth = React.useMemo(() => {
    const memoryUtilization = performanceData.memoryUsage?.utilization || 0;
    const isHealthy = memoryUtilization < 80 && agentMetrics.errorAgents === 0;

    return {
      status: isHealthy ? "healthy" : "warning",
      memoryUtilization,
      webVitals: performanceData.webVitals,
    };
  }, [performanceData, agentMetrics]);

  return (
    <Box sx={{ p: 3 }}>
      {/* Header with Controls */}
      <Box sx={{ mb: 4 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            mb: 2,
          }}
        >
          <Box>
            <Typography
              variant="h4"
              component="h1"
              gutterBottom
              sx={{ fontWeight: 700 }}
            >
              Observability Console
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Real-time system performance and agent effectiveness monitoring
            </Typography>
          </Box>

          <Paper sx={{ p: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={enableRealTime}
                  onChange={(e) => setEnableRealTime(e.target.checked)}
                />
              }
              label="Real-time Updates"
            />
          </Paper>
        </Box>

        {/* System Health Alert */}
        {systemHealth.status === "warning" && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            <AlertTitle>System Performance Notice</AlertTitle>
            High memory usage detected ({systemHealth.memoryUtilization.toFixed(
              1,
            )}%) or agent errors present. Monitor system resources and check
            agent status.
          </Alert>
        )}
      </Box>

      <Grid container spacing={3}>
        {/* CPU/Memory Usage Section */}
        <Grid item xs={12} lg={8}>
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardHeader
              title={
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <MemoryIcon color="primary" />
                  <Typography variant="h6">System Performance</Typography>
                </Box>
              }
              subheader="CPU and Memory usage over time"
            />
            <CardContent>
              <PerformanceMetricsChart
                performanceData={performanceData}
                refreshInterval={refreshInterval}
                enableRealTime={enableRealTime}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Stats */}
        <Grid item xs={12} lg={4}>
          <Grid container spacing={2}>
            {/* Memory Usage */}
            <Grid item xs={12}>
              <Card
                variant="outlined"
                sx={{
                  background: systemHealth.memoryUtilization > 80
                    ? "linear-gradient(135deg, rgba(244, 67, 54, 0.1), rgba(244, 67, 54, 0.05))"
                    : "linear-gradient(135deg, rgba(76, 175, 80, 0.1), rgba(76, 175, 80, 0.05))",
                }}
              >
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                    <MemoryIcon
                      sx={{
                        mr: 1,
                        color: systemHealth.memoryUtilization > 80
                          ? "error.main"
                          : "success.main",
                      }}
                    />
                    <Typography variant="subtitle1" fontWeight={600}>
                      Memory Usage
                    </Typography>
                  </Box>
                  <Typography
                    variant="h3"
                    color={systemHealth.memoryUtilization > 80
                      ? "error.main"
                      : "success.main"}
                    fontWeight={700}
                  >
                    {systemHealth.memoryUtilization.toFixed(1)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {performanceData.memoryUsage
                      ? `${
                        (performanceData.memoryUsage.usedJSHeapSize / 1024 /
                          1024).toFixed(1)
                      } MB used`
                      : "Data not available"}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* Agent Success Rate */}
            <Grid item xs={12}>
              <Card
                variant="outlined"
                sx={{
                  background: agentMetrics.successRate > 80
                    ? "linear-gradient(135deg, rgba(76, 175, 80, 0.1), rgba(76, 175, 80, 0.05))"
                    : "linear-gradient(135deg, rgba(255, 152, 0, 0.1), rgba(255, 152, 0, 0.05))",
                }}
              >
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                    <AgentIcon
                      sx={{
                        mr: 1,
                        color: agentMetrics.successRate > 80
                          ? "success.main"
                          : "warning.main",
                      }}
                    />
                    <Typography variant="subtitle1" fontWeight={600}>
                      Agent Success Rate
                    </Typography>
                  </Box>
                  <Typography
                    variant="h3"
                    color={agentMetrics.successRate > 80
                      ? "success.main"
                      : "warning.main"}
                    fontWeight={700}
                  >
                    {agentMetrics.successRate.toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {agentMetrics.activeAgents} active,{" "}
                    {agentMetrics.errorAgents} errors
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>

        {/* Agent Success/Failure Chart */}
        <Grid item xs={12} lg={6}>
          <Card variant="outlined">
            <CardHeader
              title={
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <AssessmentIcon color="primary" />
                  <Typography variant="h6">Agent Effectiveness</Typography>
                </Box>
              }
              subheader="Success and failure rates over time"
            />
            <CardContent>
              <AgentSuccessRateChart
                agents={agents || []}
                refreshInterval={refreshInterval}
                enableRealTime={enableRealTime}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Collaboration Metrics */}
        <Grid item xs={12} lg={6}>
          <CollaborationMetricsPanel
            metrics={coordinationMetrics || {
              conflictsPrevented: 0,
              averageTaskCompletionTime: 0,
              taskDeduplicationRate: 0,
            }}
            agents={agents || []}
            fileLocks={[]}
            events={[]}
            refreshInterval={refreshInterval}
          />
        </Grid>

        {/* Recent Agent Status */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mt: 2 }}>
            Agent Status Overview
          </Typography>
          <Grid container spacing={2}>
            {agents?.slice(0, 4).map((agent) => (
              <Grid item xs={12} sm={6} lg={3} key={agent.id}>
                <AgentStatus
                  agent={agent}
                  onViewDetails={(id) =>
                    console.log("View agent details:", id)}
                />
              </Grid>
            ))}
          </Grid>

          {agents && agents.length === 0 && (
            <Paper sx={{ p: 4, textAlign: "center" }}>
              <AgentIcon
                sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
              />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No Agents Active
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Deploy agents to start monitoring their performance and status.
              </Typography>
            </Paper>
          )}
        </Grid>

        {/* Recent Sessions */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mt: 2 }}>
            Active Sessions
          </Typography>
          <Grid container spacing={2}>
            {sessions?.filter((s) => s.status === "running").slice(0, 3).map((
              session,
            ) => (
              <Grid item xs={12} md={4} key={session.id}>
                <SessionMonitor
                  session={session}
                  onRefresh={(id) => console.log("Refresh session:", id)}
                />
              </Grid>
            ))}
          </Grid>

          {(!sessions ||
            sessions.filter((s) => s.status === "running").length === 0) && (
            <Paper sx={{ p: 4, textAlign: "center" }}>
              <TimelineIcon
                sx={{ fontSize: 48, color: "text.secondary", mb: 2 }}
              />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No Active Sessions
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Start an orchestration session to monitor its progress here.
              </Typography>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
