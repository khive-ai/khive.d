/**
 * Performance Metrics Chart Component
 * Displays real-time CPU and memory usage graphs
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  Box,
  Chip,
  Grid,
  LinearProgress,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  Timeline as TimelineIcon,
} from "@mui/icons-material";

interface PerformanceDataPoint {
  timestamp: string;
  memoryUsage: number;
  memoryUtilization: number;
  renderTime: number;
  fcp?: number;
  lcp?: number;
  cls?: number;
}

export interface PerformanceMetricsChartProps {
  performanceData: {
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
  };
  refreshInterval: number;
  enableRealTime: boolean;
  className?: string;
}

export const PerformanceMetricsChart: React.FC<PerformanceMetricsChartProps> = (
  {
    performanceData,
    refreshInterval,
    enableRealTime,
    className,
  },
) => {
  const [chartType, setChartType] = useState<"memory" | "vitals" | "rendering">(
    "memory",
  );
  const [dataPoints, setDataPoints] = useState<PerformanceDataPoint[]>([]);
  const [maxDataPoints] = useState(50); // Keep last 50 data points

  // Update data points when performance data changes
  useEffect(() => {
    if (!performanceData.memoryUsage) return;

    const newDataPoint: PerformanceDataPoint = {
      timestamp: new Date().toLocaleTimeString(),
      memoryUsage: performanceData.memoryUsage.usedJSHeapSize / (1024 * 1024), // Convert to MB
      memoryUtilization: performanceData.memoryUsage.utilization,
      renderTime: performanceData.renderTime,
      fcp: performanceData.webVitals.fcp,
      lcp: performanceData.webVitals.lcp,
      cls: performanceData.webVitals.cls
        ? performanceData.webVitals.cls * 100
        : undefined, // Convert to percentage
    };

    setDataPoints((prev) => {
      const updated = [...prev, newDataPoint];
      return updated.slice(-maxDataPoints); // Keep only last N points
    });
  }, [performanceData, maxDataPoints]);

  // Chart configuration based on selected type
  const chartConfig = useMemo(() => {
    switch (chartType) {
      case "memory":
        return {
          title: "Memory Usage",
          lines: [
            {
              dataKey: "memoryUsage",
              stroke: "#1976d2",
              name: "Memory (MB)",
              strokeWidth: 2,
            },
            {
              dataKey: "memoryUtilization",
              stroke: "#dc004e",
              name: "Utilization (%)",
              strokeWidth: 2,
            },
          ],
          yAxisDomain: [0, "auto"],
        };
      case "vitals":
        return {
          title: "Web Vitals Performance",
          lines: [
            {
              dataKey: "fcp",
              stroke: "#2e7d32",
              name: "FCP (ms)",
              strokeWidth: 2,
            },
            {
              dataKey: "lcp",
              stroke: "#ed6c02",
              name: "LCP (ms)",
              strokeWidth: 2,
            },
            {
              dataKey: "cls",
              stroke: "#9c27b0",
              name: "CLS (%)",
              strokeWidth: 2,
            },
          ],
          yAxisDomain: [0, "auto"],
        };
      case "rendering":
        return {
          title: "Component Rendering Performance",
          lines: [
            {
              dataKey: "renderTime",
              stroke: "#00acc1",
              name: "Render Time (ms)",
              strokeWidth: 2,
            },
          ],
          yAxisDomain: [0, "auto"],
        };
      default:
        return { title: "", lines: [], yAxisDomain: [0, "auto"] as const };
    }
  }, [chartType]);

  // Current performance stats
  const currentStats = useMemo(() => {
    if (!performanceData.memoryUsage) {
      return {
        memoryUsage: 0,
        memoryUtilization: 0,
        renderTime: 0,
        status: "No data",
      };
    }

    const { memoryUsage, renderTime } = performanceData;
    const memoryMB = memoryUsage.usedJSHeapSize / (1024 * 1024);
    const utilization = memoryUsage.utilization;

    const status = utilization > 80
      ? "Critical"
      : utilization > 60
      ? "Warning"
      : "Good";

    return {
      memoryUsage: memoryMB,
      memoryUtilization: utilization,
      renderTime,
      status,
    };
  }, [performanceData]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Critical":
        return "error";
      case "Warning":
        return "warning";
      case "Good":
        return "success";
      default:
        return "default";
    }
  };

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
          <ToggleButton value="memory">
            <MemoryIcon sx={{ mr: 1 }} />
            Memory
          </ToggleButton>
          <ToggleButton value="vitals">
            <SpeedIcon sx={{ mr: 1 }} />
            Web Vitals
          </ToggleButton>
          <ToggleButton value="rendering">
            <TimelineIcon sx={{ mr: 1 }} />
            Rendering
          </ToggleButton>
        </ToggleButtonGroup>

        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
          <Chip
            label={enableRealTime ? "Live" : "Paused"}
            color={enableRealTime ? "success" : "warning"}
            size="small"
          />
          <Chip
            label={`${refreshInterval / 1000}s refresh`}
            variant="outlined"
            size="small"
          />
        </Box>
      </Box>

      {/* Performance Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">
              Memory Usage
            </Typography>
            <Typography variant="h6" color="primary.main">
              {currentStats.memoryUsage.toFixed(1)} MB
            </Typography>
            <LinearProgress
              variant="determinate"
              value={currentStats.memoryUtilization}
              sx={{ mt: 1, height: 4, borderRadius: 2 }}
              color={currentStats.memoryUtilization > 80 ? "error" : "primary"}
            />
          </Paper>
        </Grid>

        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">
              Utilization
            </Typography>
            <Typography
              variant="h6"
              color={getStatusColor(currentStats.status) + ".main"}
            >
              {currentStats.memoryUtilization.toFixed(1)}%
            </Typography>
            <Chip
              label={currentStats.status}
              size="small"
              color={getStatusColor(currentStats.status) as any}
              sx={{ mt: 1 }}
            />
          </Paper>
        </Grid>

        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">
              Render Time
            </Typography>
            <Typography variant="h6" color="secondary.main">
              {currentStats.renderTime.toFixed(2)} ms
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Component
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} md={3}>
          <Paper sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="caption" color="text.secondary">
              Data Points
            </Typography>
            <Typography variant="h6" color="info.main">
              {dataPoints.length}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Last {maxDataPoints}
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Performance Chart */}
      <Paper sx={{ p: 2, height: 400 }}>
        <Typography variant="h6" gutterBottom>
          {chartConfig.title}
        </Typography>

        {dataPoints.length > 0
          ? (
            <ResponsiveContainer width="100%" height="90%">
              <AreaChart data={dataPoints}>
                <defs>
                  {chartConfig.lines.map((line, index) => (
                    <linearGradient
                      key={line.dataKey}
                      id={`color-${line.dataKey}`}
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="5%"
                        stopColor={line.stroke}
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="95%"
                        stopColor={line.stroke}
                        stopOpacity={0}
                      />
                    </linearGradient>
                  ))}
                </defs>

                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis
                  dataKey="timestamp"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => {
                    const parts = value.split(":");
                    return `${parts[0]}:${parts[1]}`;
                  }}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  domain={chartConfig.yAxisDomain}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "rgba(255, 255, 255, 0.95)",
                    border: "1px solid #e0e0e0",
                    borderRadius: "8px",
                  }}
                  labelFormatter={(value) => `Time: ${value}`}
                />
                <Legend />

                {chartConfig.lines.map((line) => (
                  <Area
                    key={line.dataKey}
                    type="monotone"
                    dataKey={line.dataKey}
                    stroke={line.stroke}
                    strokeWidth={line.strokeWidth}
                    fill={`url(#color-${line.dataKey})`}
                    name={line.name}
                    connectNulls={false}
                  />
                ))}
              </AreaChart>
            </ResponsiveContainer>
          )
          : (
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                height: "90%",
                flexDirection: "column",
                color: "text.secondary",
              }}
            >
              <TimelineIcon sx={{ fontSize: 64, mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Collecting Performance Data
              </Typography>
              <Typography variant="body2">
                Charts will appear once enough data points are collected
              </Typography>
            </Box>
          )}
      </Paper>

      {/* Resource Performance Summary */}
      {performanceData.resourceTiming.length > 0 && (
        <Paper sx={{ p: 2, mt: 2 }}>
          <Typography variant="h6" gutterBottom>
            Resource Loading Performance
          </Typography>
          <Box sx={{ maxHeight: 200, overflow: "auto" }}>
            {performanceData.resourceTiming.slice(0, 5).map((
              resource,
              index,
            ) => (
              <Box
                key={index}
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  py: 1,
                  borderBottom: index < 4 ? "1px solid" : "none",
                  borderColor: "divider",
                }}
              >
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="body2" noWrap>
                    {resource.name.split("/").pop() || resource.name}
                  </Typography>
                </Box>
                <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
                  <Typography variant="caption" color="text.secondary">
                    {resource.duration.toFixed(1)}ms
                  </Typography>
                  <Chip
                    label={`${(resource.transferSize / 1024).toFixed(1)} KB`}
                    size="small"
                    variant="outlined"
                  />
                </Box>
              </Box>
            ))}
          </Box>
        </Paper>
      )}
    </Box>
  );
};
