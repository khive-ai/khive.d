/**
 * Metrics Overview Cards Component
 * High-level system and agent metrics display
 */

import React from "react";
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as SuccessIcon,
  Computer as CPUIcon,
  Memory as MemoryIcon,
  NetworkCheck as NetworkIcon,
  Psychology as AgentIcon,
  Speed as PerformanceIcon,
  Timer as TimerIcon,
  TrendingUp as TrendingIcon,
} from "@mui/icons-material";

interface SystemMetrics {
  cpu: number;
  memory: number;
  network: number;
  timestamp: number;
}

interface AgentMetrics {
  total: number;
  active: number;
  error: number;
  successRate: number;
}

interface PerformanceData {
  webVitals: {
    fcp?: number;
    lcp?: number;
    fid?: number;
    cls?: number;
    ttfb?: number;
  };
  resourceTiming: Array<{
    name: string;
    duration: number;
    transferSize: number;
    decodedSize: number;
  }>;
  memoryUsage: {
    usedJSHeapSize: number;
    totalJSHeapSize: number;
    jsHeapSizeLimit: number;
    utilization: number;
  } | null;
  renderTime: number;
}

interface CoordinationMetrics {
  conflictsPrevented: number;
  taskDeduplicationRate: number;
  averageTaskCompletionTime: number;
  activeAgents: number;
  activeSessions: number;
}

interface MetricsOverviewCardsProps {
  systemMetrics: SystemMetrics;
  agentMetrics: AgentMetrics;
  performanceData: PerformanceData;
  coordinationMetrics?: CoordinationMetrics;
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: React.ReactNode;
  color: "primary" | "secondary" | "success" | "warning" | "error" | "info";
  progress?: number;
  trend?: "up" | "down" | "stable";
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  color,
  progress,
  trend,
}) => {
  const theme = useTheme();

  const getTrendIcon = () => {
    if (!trend) return null;

    const trendColor = trend === "up"
      ? "success.main"
      : trend === "down"
      ? "error.main"
      : "info.main";
    return (
      <TrendingIcon
        sx={{
          fontSize: 16,
          color: trendColor,
          transform: trend === "down" ? "scaleY(-1)" : "none",
        }}
      />
    );
  };

  return (
    <Card
      sx={{
        height: "100%",
        background: `linear-gradient(135deg, ${
          alpha(theme.palette[color].main, 0.08)
        }, ${alpha(theme.palette[color].light, 0.04)})`,
        border: `1px solid ${alpha(theme.palette[color].main, 0.15)}`,
        transition: "all 0.2s ease-in-out",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: theme.shadows[4],
        },
      }}
    >
      <CardContent sx={{ p: 3 }}>
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
                backgroundColor: alpha(theme.palette[color].main, 0.12),
                color: theme.palette[color].main,
              }}
            >
              {icon}
            </Box>
            <Typography variant="subtitle1" fontWeight={600}>
              {title}
            </Typography>
          </Box>
          {getTrendIcon()}
        </Box>

        <Typography
          variant="h3"
          sx={{
            fontWeight: 700,
            color: `${color}.main`,
            mb: 1,
          }}
        >
          {typeof value === "number" ? value.toFixed(1) : value}
        </Typography>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: progress !== undefined ? 2 : 0 }}
        >
          {subtitle}
        </Typography>

        {progress !== undefined && (
          <LinearProgress
            variant="determinate"
            value={progress}
            color={color}
            sx={{
              height: 6,
              borderRadius: 3,
              backgroundColor: alpha(theme.palette[color].main, 0.1),
            }}
          />
        )}
      </CardContent>
    </Card>
  );
};

export const MetricsOverviewCards: React.FC<MetricsOverviewCardsProps> = ({
  systemMetrics,
  agentMetrics,
  performanceData,
  coordinationMetrics,
}) => {
  // Calculate performance scores
  const webVitalsScore = (() => {
    const { fcp, lcp, cls, fid } = performanceData.webVitals;
    let score = 100;
    if (fcp && fcp > 2000) score -= 20;
    if (lcp && lcp > 2500) score -= 25;
    if (cls && cls > 0.1) score -= 30;
    if (fid && fid > 100) score -= 25;
    return Math.max(score, 0);
  })();

  const systemHealthScore = (
    (100 - systemMetrics.cpu * 0.4) +
    (100 - systemMetrics.memory * 0.4) +
    (100 - systemMetrics.network * 0.2)
  ) / 3;

  return (
    <Grid container spacing={3}>
      {/* System Health */}
      <Grid item xs={12} sm={6} lg={3}>
        <MetricCard
          title="System Health"
          value={`${systemHealthScore.toFixed(1)}%`}
          subtitle="CPU, Memory, Network"
          icon={<CPUIcon />}
          color={systemHealthScore > 80
            ? "success"
            : systemHealthScore > 60
            ? "warning"
            : "error"}
          progress={systemHealthScore}
          trend={systemHealthScore > 85
            ? "up"
            : systemHealthScore < 70
            ? "down"
            : "stable"}
        />
      </Grid>

      {/* Agent Success Rate */}
      <Grid item xs={12} sm={6} lg={3}>
        <MetricCard
          title="Agent Success"
          value={`${agentMetrics.successRate.toFixed(1)}%`}
          subtitle={`${agentMetrics.active} active, ${agentMetrics.error} errors`}
          icon={<AgentIcon />}
          color={agentMetrics.successRate > 90
            ? "success"
            : agentMetrics.successRate > 75
            ? "warning"
            : "error"}
          progress={agentMetrics.successRate}
          trend={agentMetrics.error === 0 ? "up" : "down"}
        />
      </Grid>

      {/* Memory Usage */}
      <Grid item xs={12} sm={6} lg={3}>
        <MetricCard
          title="Memory Usage"
          value={`${systemMetrics.memory.toFixed(1)}%`}
          subtitle={performanceData.memoryUsage
            ? `${
              Math.round(
                performanceData.memoryUsage.usedJSHeapSize / 1024 / 1024,
              )
            }MB used`
            : "System memory"}
          icon={<MemoryIcon />}
          color={systemMetrics.memory > 85
            ? "error"
            : systemMetrics.memory > 70
            ? "warning"
            : "success"}
          progress={systemMetrics.memory}
          trend={systemMetrics.memory > 80 ? "up" : "stable"}
        />
      </Grid>

      {/* Performance Score */}
      <Grid item xs={12} sm={6} lg={3}>
        <MetricCard
          title="Web Vitals"
          value={`${webVitalsScore.toFixed(0)}/100`}
          subtitle={`Render: ${performanceData.renderTime.toFixed(1)}ms`}
          icon={<PerformanceIcon />}
          color={webVitalsScore > 80
            ? "success"
            : webVitalsScore > 60
            ? "warning"
            : "error"}
          progress={webVitalsScore}
          trend={webVitalsScore > 85
            ? "up"
            : webVitalsScore < 70
            ? "down"
            : "stable"}
        />
      </Grid>

      {/* Task Completion */}
      {coordinationMetrics && (
        <>
          <Grid item xs={12} sm={6} lg={3}>
            <MetricCard
              title="Avg Task Time"
              value={`${
                (coordinationMetrics.averageTaskCompletionTime / 1000).toFixed(
                  1,
                )
              }s`}
              subtitle="Task completion time"
              icon={<TimerIcon />}
              color={coordinationMetrics.averageTaskCompletionTime < 5000
                ? "success"
                : coordinationMetrics.averageTaskCompletionTime < 10000
                ? "warning"
                : "error"}
              trend={coordinationMetrics.averageTaskCompletionTime < 5000
                ? "up"
                : "down"}
            />
          </Grid>

          <Grid item xs={12} sm={6} lg={3}>
            <MetricCard
              title="Conflicts Prevented"
              value={coordinationMetrics.conflictsPrevented}
              subtitle="File and task conflicts"
              icon={<SuccessIcon />}
              color="info"
              trend="stable"
            />
          </Grid>

          <Grid item xs={12} sm={6} lg={3}>
            <MetricCard
              title="Active Sessions"
              value={coordinationMetrics.activeSessions}
              subtitle="Coordination sessions"
              icon={<NetworkIcon />}
              color="secondary"
              trend={coordinationMetrics.activeSessions > 0 ? "up" : "stable"}
            />
          </Grid>

          <Grid item xs={12} sm={6} lg={3}>
            <MetricCard
              title="Deduplication"
              value={`${
                (coordinationMetrics.taskDeduplicationRate * 100).toFixed(1)
              }%`}
              subtitle="Task deduplication rate"
              icon={<PerformanceIcon />}
              color="primary"
              progress={coordinationMetrics.taskDeduplicationRate * 100}
              trend="stable"
            />
          </Grid>
        </>
      )}
    </Grid>
  );
};
