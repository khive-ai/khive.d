/**
 * Performance Trends Chart Component
 * Visualizes performance trends over time including Web Vitals and resource timing
 */

import React, { useMemo } from "react";
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Memory as MemoryIcon,
  NetworkWifi as NetworkIcon,
  Speed as PerformanceIcon,
  Timeline as TrendsIcon,
  Timer as TimerIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

interface WebVitals {
  fcp?: number;
  lcp?: number;
  fid?: number;
  cls?: number;
  ttfb?: number;
}

interface ResourceTiming {
  name: string;
  duration: number;
  transferSize: number;
  decodedSize: number;
}

interface RenderMetrics {
  renderTime: number;
  renderCount: number;
  averageRenderTime: number;
  lastRenderTime: number;
}

interface PerformanceTrendsChartProps {
  webVitals: WebVitals;
  resourceTiming: ResourceTiming[];
  renderMetrics: RenderMetrics;
}

interface WebVitalMetric {
  name: string;
  value?: number;
  threshold: number;
  unit: string;
  description: string;
  status: "good" | "needs-improvement" | "poor";
}

const getWebVitalStatus = (
  value: number | undefined,
  thresholds: { good: number; poor: number },
): "good" | "needs-improvement" | "poor" => {
  if (!value) return "good";
  if (value <= thresholds.good) return "good";
  if (value <= thresholds.poor) return "needs-improvement";
  return "poor";
};

const getStatusColor = (status: "good" | "needs-improvement" | "poor") => {
  switch (status) {
    case "good":
      return "success";
    case "needs-improvement":
      return "warning";
    case "poor":
      return "error";
    default:
      return "default";
  }
};

const getStatusIcon = (status: "good" | "needs-improvement" | "poor") => {
  switch (status) {
    case "good":
      return <SuccessIcon sx={{ fontSize: 16 }} />;
    case "needs-improvement":
      return <WarningIcon sx={{ fontSize: 16 }} />;
    case "poor":
      return <ErrorIcon sx={{ fontSize: 16 }} />;
    default:
      return null;
  }
};

export const PerformanceTrendsChart: React.FC<PerformanceTrendsChartProps> = ({
  webVitals,
  resourceTiming,
  renderMetrics,
}) => {
  const theme = useTheme();

  // Web Vitals analysis
  const webVitalMetrics: WebVitalMetric[] = useMemo(() => {
    return [
      {
        name: "First Contentful Paint (FCP)",
        value: webVitals.fcp,
        threshold: 1800,
        unit: "ms",
        description: "Time until first content renders",
        status: getWebVitalStatus(webVitals.fcp, { good: 1800, poor: 3000 }),
      },
      {
        name: "Largest Contentful Paint (LCP)",
        value: webVitals.lcp,
        threshold: 2500,
        unit: "ms",
        description: "Time until largest content renders",
        status: getWebVitalStatus(webVitals.lcp, { good: 2500, poor: 4000 }),
      },
      {
        name: "First Input Delay (FID)",
        value: webVitals.fid,
        threshold: 100,
        unit: "ms",
        description: "Time until page becomes interactive",
        status: getWebVitalStatus(webVitals.fid, { good: 100, poor: 300 }),
      },
      {
        name: "Cumulative Layout Shift (CLS)",
        value: webVitals.cls,
        threshold: 0.1,
        unit: "",
        description: "Visual stability measure",
        status: getWebVitalStatus(webVitals.cls, { good: 0.1, poor: 0.25 }),
      },
      {
        name: "Time to First Byte (TTFB)",
        value: webVitals.ttfb,
        threshold: 800,
        unit: "ms",
        description: "Server response time",
        status: getWebVitalStatus(webVitals.ttfb, { good: 800, poor: 1800 }),
      },
    ];
  }, [webVitals]);

  // Resource analysis
  const resourceAnalysis = useMemo(() => {
    const slowResources = resourceTiming.filter((r) => r.duration > 1000);
    const largeResources = resourceTiming.filter((r) =>
      r.transferSize > 500 * 1024
    ); // > 500KB
    const totalTransferSize = resourceTiming.reduce(
      (sum, r) => sum + r.transferSize,
      0,
    );
    const avgDuration = resourceTiming.length > 0
      ? resourceTiming.reduce((sum, r) => sum + r.duration, 0) /
        resourceTiming.length
      : 0;

    return {
      slowResources,
      largeResources,
      totalTransferSize,
      avgDuration,
      totalResources: resourceTiming.length,
    };
  }, [resourceTiming]);

  // Performance score calculation
  const performanceScore = useMemo(() => {
    let score = 100;

    webVitalMetrics.forEach((metric) => {
      if (metric.status === "poor") score -= 20;
      else if (metric.status === "needs-improvement") score -= 10;
    });

    // Factor in resource performance
    if (resourceAnalysis.avgDuration > 1000) score -= 10;
    if (resourceAnalysis.slowResources.length > 3) score -= 10;

    // Factor in render performance
    if (renderMetrics.averageRenderTime > 16) score -= 5; // 60fps threshold

    return Math.max(score, 0);
  }, [webVitalMetrics, resourceAnalysis, renderMetrics]);

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
        Performance Trends Analysis
      </Typography>

      <Grid container spacing={3}>
        {/* Performance Score Overview */}
        <Grid item xs={12} md={4}>
          <Card
            sx={{
              height: "100%",
              background: `linear-gradient(135deg, ${
                alpha(theme.palette.primary.main, 0.1)
              }, ${alpha(theme.palette.primary.light, 0.05)})`,
              border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <PerformanceIcon sx={{ color: "primary.main", mr: 1 }} />
                <Typography variant="h6" fontWeight={600}>
                  Performance Score
                </Typography>
              </Box>

              <Typography
                variant="h2"
                sx={{ fontWeight: 700, color: "primary.main", mb: 2 }}
              >
                {performanceScore}
                <Typography
                  component="span"
                  variant="h5"
                  color="text.secondary"
                >
                  /100
                </Typography>
              </Typography>

              <LinearProgress
                variant="determinate"
                value={performanceScore}
                color={performanceScore > 80
                  ? "success"
                  : performanceScore > 60
                  ? "warning"
                  : "error"}
                sx={{ height: 8, borderRadius: 4, mb: 2 }}
              />

              <Typography variant="body2" color="text.secondary">
                Based on Web Vitals, resource loading, and render performance
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Render Performance */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <TimerIcon sx={{ color: "secondary.main", mr: 1 }} />
                <Typography variant="h6" fontWeight={600}>
                  Render Performance
                </Typography>
              </Box>

              <Stack spacing={2}>
                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Average Render Time</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {renderMetrics.averageRenderTime.toFixed(2)}ms
                  </Typography>
                </Box>

                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Last Render Time</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {renderMetrics.lastRenderTime.toFixed(2)}ms
                  </Typography>
                </Box>

                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Total Renders</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {renderMetrics.renderCount}
                  </Typography>
                </Box>

                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Target: &lt;16ms for 60fps
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(
                      (16 / renderMetrics.averageRenderTime) * 100,
                      100,
                    )}
                    color={renderMetrics.averageRenderTime <= 16
                      ? "success"
                      : "warning"}
                    sx={{ height: 4, borderRadius: 2, mt: 1 }}
                  />
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Resource Summary */}
        <Grid item xs={12} md={4}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <NetworkIcon sx={{ color: "info.main", mr: 1 }} />
                <Typography variant="h6" fontWeight={600}>
                  Resource Loading
                </Typography>
              </Box>

              <Stack spacing={2}>
                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Total Resources</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {resourceAnalysis.totalResources}
                  </Typography>
                </Box>

                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Avg Load Time</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {resourceAnalysis.avgDuration.toFixed(0)}ms
                  </Typography>
                </Box>

                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Total Transfer</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {(resourceAnalysis.totalTransferSize / 1024 / 1024).toFixed(
                      1,
                    )}MB
                  </Typography>
                </Box>

                <Box sx={{ display: "flex", gap: 1 }}>
                  {resourceAnalysis.slowResources.length > 0 && (
                    <Chip
                      label={`${resourceAnalysis.slowResources.length} slow`}
                      size="small"
                      color="warning"
                    />
                  )}
                  {resourceAnalysis.largeResources.length > 0 && (
                    <Chip
                      label={`${resourceAnalysis.largeResources.length} large`}
                      size="small"
                      color="error"
                    />
                  )}
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Web Vitals Details */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom sx={{ mb: 2, fontWeight: 600 }}>
          Web Vitals Breakdown
        </Typography>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Metric</TableCell>
                <TableCell>Current Value</TableCell>
                <TableCell>Threshold</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Description</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {webVitalMetrics.map((metric) => (
                <TableRow key={metric.name}>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {metric.name}
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2">
                      {metric.value
                        ? `${
                          metric.value.toFixed(metric.unit === "ms" ? 0 : 3)
                        }${metric.unit}`
                        : "N/A"}
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      ≤ {metric.threshold}
                      {metric.unit}
                    </Typography>
                  </TableCell>

                  <TableCell>
                    <Chip
                      icon={getStatusIcon(metric.status)}
                      label={metric.status.replace("-", " ")}
                      size="small"
                      color={getStatusColor(metric.status) as any}
                      variant="outlined"
                    />
                  </TableCell>

                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {metric.description}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* Resource Details */}
      {resourceTiming.length > 0 && (
        <Box sx={{ mt: 4 }}>
          <Typography variant="h6" gutterBottom sx={{ mb: 2, fontWeight: 600 }}>
            Resource Loading Details (Top 10 by Duration)
          </Typography>

          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Resource</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Transfer Size</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {resourceTiming
                  .sort((a, b) => b.duration - a.duration)
                  .slice(0, 10)
                  .map((resource, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{
                            maxWidth: 300,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {resource.name}
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {resource.duration.toFixed(0)}ms
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Typography variant="body2">
                          {(resource.transferSize / 1024).toFixed(1)}KB
                        </Typography>
                      </TableCell>

                      <TableCell>
                        <Chip
                          label={resource.duration > 1000
                            ? "Slow"
                            : resource.transferSize > 500 * 1024
                            ? "Large"
                            : "Good"}
                          size="small"
                          color={resource.duration > 1000
                            ? "error"
                            : resource.transferSize > 500 * 1024
                            ? "warning"
                            : "success"}
                          variant="outlined"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}
    </Box>
  );
};
