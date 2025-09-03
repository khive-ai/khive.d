/**
 * System Metrics Chart Component
 * Real-time visualization of CPU, memory, and network usage
 * Includes performance thresholds and alerts
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Computer as CPUIcon,
  Memory as MemoryIcon,
  NetworkCheck as NetworkIcon,
  TrendingUp as TrendingIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

interface SystemMetrics {
  cpu: number;
  memory: number;
  network: number;
  timestamp: number;
}

interface MemoryUsage {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
  utilization: number;
}

interface PerformanceThresholds {
  cpuUsage: number;
  memoryUsage: number;
  responseTime: number;
  errorRate: number;
  taskFailureRate: number;
}

interface SystemMetricsChartProps {
  metrics: SystemMetrics;
  memoryUsage: MemoryUsage | null;
  thresholds: PerformanceThresholds;
}

interface MetricCardProps {
  title: string;
  icon: React.ReactNode;
  value: number;
  unit: string;
  threshold: number;
  color: string;
  trend?: "up" | "down" | "stable";
  details?: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
  title,
  icon,
  value,
  unit,
  threshold,
  color,
  trend,
  details,
}) => {
  const theme = useTheme();
  const isWarning = value > threshold;
  const progressColor = isWarning ? "error" : "success";

  const getTrendIcon = () => {
    if (!trend) return null;

    const trendColor = trend === "up"
      ? "error.main"
      : trend === "down"
      ? "success.main"
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
          alpha(theme.palette[color as keyof typeof theme.palette].main, 0.05)
        }, ${
          alpha(theme.palette[color as keyof typeof theme.palette].light, 0.02)
        })`,
        border: `1px solid ${
          alpha(theme.palette[color as keyof typeof theme.palette].main, 0.12)
        }`,
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
                backgroundColor: alpha(
                  theme.palette[color as keyof typeof theme.palette].main,
                  0.1,
                ),
                color: theme.palette[color as keyof typeof theme.palette].main,
              }}
            >
              {icon}
            </Box>
            <Typography variant="subtitle1" fontWeight={600}>
              {title}
            </Typography>
          </Box>

          {isWarning && (
            <Chip
              icon={<WarningIcon />}
              label="Alert"
              color="error"
              size="small"
              variant="outlined"
            />
          )}
        </Box>

        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, mb: 1 }}>
            <Typography
              variant="h3"
              sx={{
                fontWeight: 700,
                color: isWarning ? "error.main" : `${color}.main`,
              }}
            >
              {value.toFixed(1)}
            </Typography>
            <Typography variant="h6" color="text.secondary">
              {unit}
            </Typography>
            {getTrendIcon()}
          </Box>

          {details && (
            <Typography variant="body2" color="text.secondary">
              {details}
            </Typography>
          )}
        </Box>

        <Box>
          <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Usage
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Threshold: {threshold}
              {unit}
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={Math.min((value / threshold) * 100, 100)}
            color={progressColor}
            sx={{
              height: 8,
              borderRadius: 4,
              backgroundColor: alpha(theme.palette.grey[300], 0.3),
              "& .MuiLinearProgress-bar": {
                borderRadius: 4,
              },
            }}
          />
        </Box>
      </CardContent>
    </Card>
  );
};

// Historical data storage (in production, this would come from a time-series database)
const HISTORY_LENGTH = 50;
const historicalData: SystemMetrics[] = [];

export const SystemMetricsChart: React.FC<SystemMetricsChartProps> = ({
  metrics,
  memoryUsage,
  thresholds,
}) => {
  const theme = useTheme();
  const [history, setHistory] = useState<SystemMetrics[]>([]);

  // Update historical data
  useEffect(() => {
    setHistory((prev) => {
      const updated = [...prev, metrics];
      if (updated.length > HISTORY_LENGTH) {
        updated.shift();
      }
      return updated;
    });
  }, [metrics]);

  // Calculate trends
  const trends = useMemo(() => {
    if (history.length < 2) {
      return { cpu: "stable", memory: "stable", network: "stable" };
    }

    const recent = history.slice(-5);
    const older = history.slice(-10, -5);

    if (recent.length === 0 || older.length === 0) {
      return { cpu: "stable", memory: "stable", network: "stable" };
    }

    const recentAvg = {
      cpu: recent.reduce((sum, m) => sum + m.cpu, 0) / recent.length,
      memory: recent.reduce((sum, m) => sum + m.memory, 0) / recent.length,
      network: recent.reduce((sum, m) => sum + m.network, 0) / recent.length,
    };

    const olderAvg = {
      cpu: older.reduce((sum, m) => sum + m.cpu, 0) / older.length,
      memory: older.reduce((sum, m) => sum + m.memory, 0) / older.length,
      network: older.reduce((sum, m) => sum + m.network, 0) / older.length,
    };

    const getTrend = (recent: number, older: number) => {
      const diff = recent - older;
      if (Math.abs(diff) < 2) return "stable";
      return diff > 0 ? "up" : "down";
    };

    return {
      cpu: getTrend(recentAvg.cpu, olderAvg.cpu),
      memory: getTrend(recentAvg.memory, olderAvg.memory),
      network: getTrend(recentAvg.network, olderAvg.network),
    };
  }, [history]);

  // Calculate memory details
  const memoryDetails = useMemo(() => {
    if (!memoryUsage) return "Memory info unavailable";

    const usedMB = Math.round(memoryUsage.usedJSHeapSize / 1024 / 1024);
    const totalMB = Math.round(memoryUsage.totalJSHeapSize / 1024 / 1024);
    const limitMB = Math.round(memoryUsage.jsHeapSizeLimit / 1024 / 1024);

    return `${usedMB}MB of ${totalMB}MB allocated (limit: ${limitMB}MB)`;
  }, [memoryUsage]);

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
        Real-time System Performance
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <MetricCard
            title="CPU Usage"
            icon={<CPUIcon />}
            value={metrics.cpu}
            unit="%"
            threshold={thresholds.cpuUsage}
            color="primary"
            trend={trends.cpu as any}
            details="Current processor utilization"
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <MetricCard
            title="Memory Usage"
            icon={<MemoryIcon />}
            value={metrics.memory}
            unit="%"
            threshold={thresholds.memoryUsage}
            color="secondary"
            trend={trends.memory as any}
            details={memoryDetails}
          />
        </Grid>

        <Grid item xs={12} md={4}>
          <MetricCard
            title="Network I/O"
            icon={<NetworkIcon />}
            value={metrics.network}
            unit="%"
            threshold={90} // Network threshold
            color="info"
            trend={trends.network as any}
            details="Network bandwidth utilization"
          />
        </Grid>
      </Grid>

      {/* Mini Chart Visualization */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
          Performance History (Last {HISTORY_LENGTH} readings)
        </Typography>

        <Grid container spacing={3}>
          {["cpu", "memory", "network"].map((metric) => (
            <Grid item xs={12} md={4} key={metric}>
              <Box>
                <Typography
                  variant="subtitle2"
                  sx={{ mb: 2, textTransform: "capitalize" }}
                >
                  {metric} Usage Trend
                </Typography>
                <Box
                  sx={{
                    height: 60,
                    position: "relative",
                    bgcolor: alpha(theme.palette.grey[100], 0.5),
                    borderRadius: 1,
                    overflow: "hidden",
                  }}
                >
                  {history.map((point, index) => {
                    const value =
                      point[metric as keyof SystemMetrics] as number;
                    const height = Math.max((value / 100) * 60, 2);
                    const color =
                      value > (thresholds as any)[`${metric}Usage`] ||
                        value > 80
                        ? theme.palette.error.main
                        : theme.palette.primary.main;

                    return (
                      <Box
                        key={index}
                        sx={{
                          position: "absolute",
                          bottom: 0,
                          left: `${(index / HISTORY_LENGTH) * 100}%`,
                          width: `${100 / HISTORY_LENGTH}%`,
                          height: `${height}px`,
                          bgcolor: alpha(color, 0.7),
                          transition: "all 0.3s ease-in-out",
                        }}
                      />
                    );
                  })}
                </Box>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mt: 1,
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    0%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    100%
                  </Typography>
                </Box>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Paper>
    </Box>
  );
};
