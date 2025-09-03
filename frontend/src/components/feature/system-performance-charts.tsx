/**
 * System Performance Charts - CPU and Memory Usage Visualization
 * Part of the Observability Console MVP
 */

"use client";

import { useMemo, useState } from "react";
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Memory as MemoryIcon,
  ShowChart as MetricsIcon,
  Speed as CpuIcon,
  Timeline as TrendsIcon,
} from "@mui/icons-material";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useSystemPerformance } from "@/lib/api/hooks";
import type { MetricDataPoint, SystemPerformanceMetrics } from "@/lib/types";

type TimeRange = "1h" | "6h" | "24h" | "7d";

interface SystemPerformanceChartsProps {
  className?: string;
}

export function SystemPerformanceCharts(
  { className }: SystemPerformanceChartsProps,
) {
  const theme = useTheme();
  const [timeRange, setTimeRange] = useState<TimeRange>("1h");
  const { data: performanceData, isLoading, error } = useSystemPerformance();

  // Filter data based on time range
  const filteredData = useMemo(() => {
    if (!performanceData) return { cpu: [], memory: [] };

    const now = new Date();
    let hoursBack: number;

    switch (timeRange) {
      case "1h":
        hoursBack = 1;
        break;
      case "6h":
        hoursBack = 6;
        break;
      case "24h":
        hoursBack = 24;
        break;
      case "7d":
        hoursBack = 24 * 7;
        break;
      default:
        hoursBack = 1;
    }

    const cutoffTime = new Date(now.getTime() - hoursBack * 60 * 60 * 1000);

    const filterByTime = (data: MetricDataPoint[]) =>
      data.filter((point) => new Date(point.timestamp) >= cutoffTime);

    return {
      cpu: filterByTime(performanceData.cpu.history),
      memory: filterByTime(performanceData.memory.history),
    };
  }, [performanceData, timeRange]);

  // Combine data for dual-axis chart
  const combinedData = useMemo(() => {
    if (!performanceData) return [];

    const { cpu, memory } = filteredData;
    const dataMap = new Map();

    // Add CPU data
    cpu.forEach((point) => {
      dataMap.set(point.timestamp, {
        timestamp: point.timestamp,
        cpu: point.value,
        time: new Date(point.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      });
    });

    // Add memory data
    memory.forEach((point) => {
      const existing = dataMap.get(point.timestamp) ||
        { timestamp: point.timestamp };
      dataMap.set(point.timestamp, {
        ...existing,
        memory: point.value,
        time: new Date(point.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      });
    });

    return Array.from(dataMap.values()).sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }, [filteredData, performanceData]);

  const handleTimeRangeChange = (
    _: React.MouseEvent<HTMLElement>,
    newTimeRange: TimeRange | null,
  ) => {
    if (newTimeRange) {
      setTimeRange(newTimeRange);
    }
  };

  const formatMemoryValue = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const formatCpuValue = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const getPerformanceStatus = (cpu: number, memory: number) => {
    if (cpu > 80 || memory > 85) return { level: "high", color: "error" };
    if (cpu > 60 || memory > 70) return { level: "moderate", color: "warning" };
    return { level: "normal", color: "success" };
  };

  // Custom tooltip component
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const cpuData = payload.find((p: any) => p.dataKey === "cpu");
      const memoryData = payload.find((p: any) => p.dataKey === "memory");

      return (
        <Card sx={{ p: 1, boxShadow: theme.shadows[8] }}>
          <CardContent sx={{ p: 1, "&:last-child": { pb: 1 } }}>
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
            {cpuData && (
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}
              >
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: theme.palette.primary.main,
                  }}
                />
                <Typography variant="body2">
                  CPU: {formatCpuValue(cpuData.value)}
                </Typography>
              </Box>
            )}
            {memoryData && (
              <Box
                sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}
              >
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: theme.palette.secondary.main,
                  }}
                />
                <Typography variant="body2">
                  Memory: {formatMemoryValue(memoryData.value)}
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <Card className={className}>
        <CardContent>
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: 200,
            }}
          >
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error || !performanceData) {
    return (
      <Card className={className}>
        <CardContent>
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: 200,
            }}
          >
            <Typography color="text.secondary">
              Unable to load performance data
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const currentStatus = getPerformanceStatus(
    performanceData.cpu.usage,
    performanceData.memory.usage,
  );

  return (
    <Box className={className}>
      {/* Header with Controls */}
      <Box sx={{ mb: 3 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            mb: 2,
          }}
        >
          <Box>
            <Typography variant="h5" gutterBottom sx={{ fontWeight: 700 }}>
              System Performance
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Real-time CPU and memory usage monitoring
            </Typography>
          </Box>
          <ToggleButtonGroup
            value={timeRange}
            exclusive
            onChange={handleTimeRangeChange}
            size="small"
          >
            <ToggleButton value="1h">1H</ToggleButton>
            <ToggleButton value="6h">6H</ToggleButton>
            <ToggleButton value="24h">24H</ToggleButton>
            <ToggleButton value="7d">7D</ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {/* Current Status Cards */}
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Card
              sx={{
                background: `linear-gradient(135deg, ${
                  alpha(theme.palette.primary.main, 0.1)
                }, ${alpha(theme.palette.primary.light, 0.05)})`,
                border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
              }}
            >
              <CardContent sx={{ p: 2 }}>
                <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                  <CpuIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2">CPU Usage</Typography>
                </Box>
                <Typography
                  variant="h4"
                  color="primary.main"
                  sx={{ fontWeight: 700 }}
                >
                  {formatCpuValue(performanceData.cpu.usage)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card
              sx={{
                background: `linear-gradient(135deg, ${
                  alpha(theme.palette.secondary.main, 0.1)
                }, ${alpha(theme.palette.secondary.light, 0.05)})`,
                border: `1px solid ${alpha(theme.palette.secondary.main, 0.2)}`,
              }}
            >
              <CardContent sx={{ p: 2 }}>
                <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                  <MemoryIcon color="secondary" sx={{ mr: 1 }} />
                  <Typography variant="subtitle2">Memory Usage</Typography>
                </Box>
                <Typography
                  variant="h4"
                  color="secondary.main"
                  sx={{ fontWeight: 700 }}
                >
                  {formatMemoryValue(performanceData.memory.usage)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {Math.round(performanceData.memory.used)}MB /{" "}
                  {Math.round(performanceData.memory.total)}MB
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ p: 2 }}>
                <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                  <MetricsIcon sx={{ mr: 1 }} />
                  <Typography variant="subtitle2">Status</Typography>
                </Box>
                <Chip
                  label={currentStatus.level.toUpperCase()}
                  color={currentStatus.color as any}
                  size="small"
                />
                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                  sx={{ mt: 0.5 }}
                >
                  System health
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent sx={{ p: 2 }}>
                <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                  <TrendsIcon sx={{ mr: 1 }} />
                  <Typography variant="subtitle2">Data Points</Typography>
                </Box>
                <Typography variant="h4" sx={{ fontWeight: 700 }}>
                  {combinedData.length}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Last {timeRange}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>

      {/* Performance Charts */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            Performance Trends
          </Typography>
          <Box sx={{ height: 350, width: "100%" }}>
            <ResponsiveContainer>
              <AreaChart data={combinedData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke={alpha(theme.palette.divider, 0.5)}
                />
                <XAxis
                  dataKey="time"
                  tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
                  tickLine={{ stroke: theme.palette.divider }}
                />
                <YAxis
                  tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
                  tickLine={{ stroke: theme.palette.divider }}
                  domain={[0, 100]}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip content={<CustomTooltip />} />

                {/* Warning thresholds */}
                <ReferenceLine
                  y={80}
                  stroke={theme.palette.warning.main}
                  strokeDasharray="5 5"
                />
                <ReferenceLine
                  y={90}
                  stroke={theme.palette.error.main}
                  strokeDasharray="5 5"
                />

                <Area
                  type="monotone"
                  dataKey="cpu"
                  stroke={theme.palette.primary.main}
                  fill={alpha(theme.palette.primary.main, 0.2)}
                  strokeWidth={2}
                  name="CPU Usage"
                />
                <Area
                  type="monotone"
                  dataKey="memory"
                  stroke={theme.palette.secondary.main}
                  fill={alpha(theme.palette.secondary.main, 0.2)}
                  strokeWidth={2}
                  name="Memory Usage"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
