/**
 * Observability Console - Metrics and Analytics Dashboard
 * MVP features: CPU/memory usage graphs, agent success/failure rates
 *
 * Architecture:
 * - Real-time performance monitoring with WebSocket updates
 * - System metrics visualization (CPU, memory, network)
 * - Agent effectiveness tracking (success/failure rates, task completion times)
 * - Performance trend analysis with historical data
 */

"use client";

import { useEffect, useMemo, useState } from "react";
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  Paper,
  Stack,
  Tab,
  Tabs,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as SuccessIcon,
  Computer as SystemIcon,
  Error as ErrorIcon,
  Memory as MemoryIcon,
  NetworkCheck as NetworkIcon,
  Psychology as AgentIcon,
  Speed as PerformanceIcon,
  Timeline as TrendsIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

import {
  useAPIPerformance,
  useComponentPerformance,
  usePerformance,
} from "@/lib/hooks/usePerformance";
import { getMemoryUsage } from "@/lib/utils/performance";
import { useAgents, useCoordinationMetrics } from "@/lib/api/hooks";
import { SystemMetricsChart } from "@/components/feature/observability/system-metrics-chart";
import { AgentPerformanceChart } from "@/components/feature/observability/agent-performance-chart";
import { MetricsOverviewCards } from "@/components/feature/observability/metrics-overview-cards";
import { PerformanceTrendsChart } from "@/components/feature/observability/performance-trends-chart";
import { AlertsPanel } from "@/components/feature/observability/alerts-panel";

// Performance thresholds for alerting
const PERFORMANCE_THRESHOLDS = {
  cpuUsage: 80, // Percentage
  memoryUsage: 85, // Percentage
  responseTime: 2000, // Milliseconds
  errorRate: 5, // Percentage
  taskFailureRate: 10, // Percentage
} as const;

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`observability-tabpanel-${index}`}
      aria-labelledby={`observability-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

export default function ObservabilityConsolePage() {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);
  const [systemMetrics, setSystemMetrics] = useState({
    cpu: 0,
    memory: 0,
    network: 0,
    timestamp: Date.now(),
  });

  // Performance monitoring hooks
  const performanceData = usePerformance("ObservabilityConsole", true);
  const componentMetrics = useComponentPerformance("ObservabilityConsole");
  const { apiMetrics, trackAPICall } = useAPIPerformance();

  // API data hooks
  const { data: coordinationMetrics, isLoading: metricsLoading } =
    useCoordinationMetrics();
  const { data: agents, isLoading: agentsLoading } = useAgents();

  // Real-time system metrics collection
  useEffect(() => {
    const collectSystemMetrics = () => {
      // Simulate CPU usage (in real implementation, would use system API)
      const cpuUsage = Math.random() * 100;

      // Get real memory usage
      const memoryInfo = getMemoryUsage();
      const memoryUsage = memoryInfo?.utilization || 0;

      // Simulate network usage
      const networkUsage = Math.random() * 100;

      setSystemMetrics({
        cpu: cpuUsage,
        memory: memoryUsage,
        network: networkUsage,
        timestamp: Date.now(),
      });
    };

    // Initial collection
    collectSystemMetrics();

    // Update every 5 seconds
    const interval = setInterval(collectSystemMetrics, 5000);

    return () => clearInterval(interval);
  }, []);

  // Calculate derived metrics
  const derivedMetrics = useMemo(() => {
    const activeAgentCount = agents?.filter((agent) =>
      agent.status === "active"
    ).length || 0;
    const errorAgentCount =
      agents?.filter((agent) => agent.status === "error").length || 0;
    const totalAgents = agents?.length || 0;

    const agentSuccessRate = totalAgents > 0
      ? ((totalAgents - errorAgentCount) / totalAgents) * 100
      : 100;
    const systemHealthScore =
      ((100 - systemMetrics.cpu * 0.3) + (100 - systemMetrics.memory * 0.4) +
        (100 - systemMetrics.network * 0.3)) / 3;

    const alerts = [];

    // Generate alerts based on thresholds
    if (systemMetrics.cpu > PERFORMANCE_THRESHOLDS.cpuUsage) {
      alerts.push({
        id: "cpu-high",
        type: "warning" as const,
        title: "High CPU Usage",
        message: `CPU usage is at ${systemMetrics.cpu.toFixed(1)}%`,
        timestamp: new Date().toISOString(),
      });
    }

    if (systemMetrics.memory > PERFORMANCE_THRESHOLDS.memoryUsage) {
      alerts.push({
        id: "memory-high",
        type: "warning" as const,
        title: "High Memory Usage",
        message: `Memory usage is at ${systemMetrics.memory.toFixed(1)}%`,
        timestamp: new Date().toISOString(),
      });
    }

    if (agentSuccessRate < 90) {
      alerts.push({
        id: "agents-failing",
        type: "error" as const,
        title: "Agent Failures",
        message: `${errorAgentCount} agents in error state`,
        timestamp: new Date().toISOString(),
      });
    }

    return {
      activeAgentCount,
      errorAgentCount,
      totalAgents,
      agentSuccessRate,
      systemHealthScore,
      alerts,
    };
  }, [agents, systemMetrics]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
          <PerformanceIcon sx={{ fontSize: 32, color: "primary.main" }} />
          <Box>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 700 }}>
              Observability Console
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Real-time system performance monitoring and agent analytics
              dashboard
            </Typography>
          </Box>
        </Box>

        {/* System Health Indicator */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Chip
            icon={<SystemIcon />}
            label={`System Health: ${
              derivedMetrics.systemHealthScore.toFixed(1)
            }%`}
            color={derivedMetrics.systemHealthScore > 80
              ? "success"
              : derivedMetrics.systemHealthScore > 60
              ? "warning"
              : "error"}
            variant="outlined"
          />
          <Chip
            icon={<AgentIcon />}
            label={`Agent Success: ${
              derivedMetrics.agentSuccessRate.toFixed(1)
            }%`}
            color={derivedMetrics.agentSuccessRate > 90
              ? "success"
              : derivedMetrics.agentSuccessRate > 75
              ? "warning"
              : "error"}
            variant="outlined"
          />
          <Chip
            label={`${derivedMetrics.activeAgentCount} Active Agents`}
            color="primary"
            variant="outlined"
          />
        </Box>
      </Box>

      {/* Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12}>
          <MetricsOverviewCards
            systemMetrics={systemMetrics}
            agentMetrics={{
              total: derivedMetrics.totalAgents,
              active: derivedMetrics.activeAgentCount,
              error: derivedMetrics.errorAgentCount,
              successRate: derivedMetrics.agentSuccessRate,
            }}
            performanceData={performanceData}
            coordinationMetrics={coordinationMetrics}
          />
        </Grid>
      </Grid>

      {/* Alerts Panel */}
      {derivedMetrics.alerts.length > 0 && (
        <Box sx={{ mb: 4 }}>
          <AlertsPanel alerts={derivedMetrics.alerts} />
        </Box>
      )}

      {/* Main Content with Tabs */}
      <Paper sx={{ width: "100%" }}>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            aria-label="observability console tabs"
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab
              icon={<SystemIcon />}
              label="System Metrics"
              id="observability-tab-0"
              aria-controls="observability-tabpanel-0"
            />
            <Tab
              icon={<AgentIcon />}
              label="Agent Performance"
              id="observability-tab-1"
              aria-controls="observability-tabpanel-1"
            />
            <Tab
              icon={<TrendsIcon />}
              label="Performance Trends"
              id="observability-tab-2"
              aria-controls="observability-tabpanel-2"
            />
            <Tab
              icon={<NetworkIcon />}
              label="API Analytics"
              id="observability-tab-3"
              aria-controls="observability-tabpanel-3"
            />
          </Tabs>
        </Box>

        {/* System Metrics Tab */}
        <TabPanel value={activeTab} index={0}>
          <SystemMetricsChart
            metrics={systemMetrics}
            memoryUsage={performanceData.memoryUsage}
            thresholds={PERFORMANCE_THRESHOLDS}
          />
        </TabPanel>

        {/* Agent Performance Tab */}
        <TabPanel value={activeTab} index={1}>
          <AgentPerformanceChart
            agents={agents || []}
            coordinationMetrics={coordinationMetrics}
            isLoading={agentsLoading || metricsLoading}
          />
        </TabPanel>

        {/* Performance Trends Tab */}
        <TabPanel value={activeTab} index={2}>
          <PerformanceTrendsChart
            webVitals={performanceData.webVitals}
            resourceTiming={performanceData.resourceTiming}
            renderMetrics={{
              renderTime: performanceData.renderTime,
              ...componentMetrics,
            }}
          />
        </TabPanel>

        {/* API Analytics Tab */}
        <TabPanel value={activeTab} index={3}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    API Performance Metrics
                  </Typography>
                  <Stack spacing={2}>
                    <Box
                      sx={{ display: "flex", justifyContent: "space-between" }}
                    >
                      <Typography variant="body2">Total Requests</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {apiMetrics.totalRequests.toLocaleString()}
                      </Typography>
                    </Box>
                    <Box
                      sx={{ display: "flex", justifyContent: "space-between" }}
                    >
                      <Typography variant="body2">Failed Requests</Typography>
                      <Typography
                        variant="body2"
                        fontWeight="bold"
                        color={apiMetrics.failedRequests > 0
                          ? "error.main"
                          : "text.primary"}
                      >
                        {apiMetrics.failedRequests.toLocaleString()}
                      </Typography>
                    </Box>
                    <Box
                      sx={{ display: "flex", justifyContent: "space-between" }}
                    >
                      <Typography variant="body2">Avg Response Time</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        {apiMetrics.averageResponseTime.toFixed(2)}ms
                      </Typography>
                    </Box>
                    <Box
                      sx={{ display: "flex", justifyContent: "space-between" }}
                    >
                      <Typography variant="body2">
                        Slow Requests (&gt;1s)
                      </Typography>
                      <Typography
                        variant="body2"
                        fontWeight="bold"
                        color={apiMetrics.slowRequests > 0
                          ? "warning.main"
                          : "text.primary"}
                      >
                        {apiMetrics.slowRequests.toLocaleString()}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Performance Health
                  </Typography>
                  <Stack spacing={2}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      {apiMetrics.failedRequests === 0
                        ? (
                          <SuccessIcon
                            sx={{ fontSize: 16, color: "success.main" }}
                          />
                        )
                        : apiMetrics.failedRequests < 5
                        ? (
                          <WarningIcon
                            sx={{ fontSize: 16, color: "warning.main" }}
                          />
                        )
                        : (
                          <ErrorIcon
                            sx={{ fontSize: 16, color: "error.main" }}
                          />
                        )}
                      <Typography variant="body2">
                        Success Rate: {apiMetrics.totalRequests > 0
                          ? ((apiMetrics.totalRequests -
                            apiMetrics.failedRequests) /
                            apiMetrics.totalRequests * 100).toFixed(1)
                          : 100}%
                      </Typography>
                    </Box>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      {apiMetrics.averageResponseTime < 500
                        ? (
                          <SuccessIcon
                            sx={{ fontSize: 16, color: "success.main" }}
                          />
                        )
                        : apiMetrics.averageResponseTime < 1000
                        ? (
                          <WarningIcon
                            sx={{ fontSize: 16, color: "warning.main" }}
                          />
                        )
                        : (
                          <ErrorIcon
                            sx={{ fontSize: 16, color: "error.main" }}
                          />
                        )}
                      <Typography variant="body2">
                        Response Time: {apiMetrics.averageResponseTime < 500
                          ? "Excellent"
                          : apiMetrics.averageResponseTime < 1000
                          ? "Good"
                          : "Needs Attention"}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </TabPanel>
      </Paper>
    </Box>
  );
}
