/**
 * Agent Analytics Charts - Success/Failure Rate Visualization
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
  Divider,
  Grid,
  LinearProgress,
  Stack,
  Tab,
  Tabs,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Assessment as AnalyticsIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Psychology as AgentIcon,
  Timeline as ActivityIcon,
  TrendingDown as TrendingDownIcon,
  TrendingUp as TrendingUpIcon,
} from "@mui/icons-material";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useAgentAnalytics } from "@/lib/api/hooks";
import type {
  AgentActivityPoint,
  AgentAnalytics,
  DomainPerformanceMetrics,
  RolePerformanceMetrics,
} from "@/lib/types";

type AnalyticsTab = "overview" | "roles" | "domains" | "activity";

interface AgentAnalyticsChartsProps {
  className?: string;
}

export function AgentAnalyticsCharts({ className }: AgentAnalyticsChartsProps) {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState<AnalyticsTab>("overview");
  const { data: analyticsData, isLoading, error } = useAgentAnalytics();

  const handleTabChange = (_: React.SyntheticEvent, newValue: AnalyticsTab) => {
    setActiveTab(newValue);
  };

  // Prepare data for pie chart
  const successFailureData = useMemo(() => {
    if (!analyticsData) return [];
    return [
      {
        name: "Successful",
        value: analyticsData.completedTasks,
        color: theme.palette.success.main,
      },
      {
        name: "Failed",
        value: analyticsData.failedTasks,
        color: theme.palette.error.main,
      },
    ];
  }, [analyticsData, theme]);

  // Prepare role performance data for bar chart
  const rolePerformanceData = useMemo(() => {
    if (!analyticsData?.performanceByRole) return [];
    return analyticsData.performanceByRole.map((role) => ({
      ...role,
      successRate: Math.round(role.successRate),
      avgTime: Math.round(role.averageCompletionTime),
    }));
  }, [analyticsData]);

  // Prepare domain performance data for bar chart
  const domainPerformanceData = useMemo(() => {
    if (!analyticsData?.performanceByDomain) return [];
    return analyticsData.performanceByDomain.map((domain) => ({
      ...domain,
      successRate: Math.round(domain.successRate),
      avgTime: Math.round(domain.averageCompletionTime),
    }));
  }, [analyticsData]);

  // Prepare activity timeline data
  const activityTimelineData = useMemo(() => {
    if (!analyticsData?.recentActivity) return [];
    return analyticsData.recentActivity.map((activity) => ({
      ...activity,
      time: new Date(activity.timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      total: activity.successful + activity.failed,
      successRate: activity.successful + activity.failed > 0
        ? Math.round(
          (activity.successful / (activity.successful + activity.failed)) * 100,
        )
        : 0,
    }));
  }, [analyticsData]);

  // Custom tooltip for charts
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <Card sx={{ p: 1, boxShadow: theme.shadows[8] }}>
          <CardContent sx={{ p: 1, "&:last-child": { pb: 1 } }}>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              {label}
            </Typography>
            {payload.map((entry: any, index: number) => (
              <Box
                key={index}
                sx={{ display: "flex", alignItems: "center", gap: 1, mt: 0.5 }}
              >
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: entry.color,
                  }}
                />
                <Typography variant="body2">
                  {entry.name}: {entry.value}
                  {entry.name.includes("Rate") ? "%" : ""}
                </Typography>
              </Box>
            ))}
          </CardContent>
        </Card>
      );
    }
    return null;
  };

  const getPerformanceColor = (rate: number) => {
    if (rate >= 90) return theme.palette.success.main;
    if (rate >= 75) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  const getPerformanceIcon = (rate: number) => {
    if (rate >= 90) return <TrendingUpIcon color="success" />;
    if (rate >= 75) return <TrendingUpIcon color="warning" />;
    return <TrendingDownIcon color="error" />;
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
              height: 300,
            }}
          >
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (error || !analyticsData) {
    return (
      <Card className={className}>
        <CardContent>
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              height: 300,
            }}
          >
            <Typography color="text.secondary">
              Unable to load agent analytics data
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box className={className}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 700 }}>
          Agent Performance Analytics
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Success rates, task completion metrics, and agent effectiveness
          analysis
        </Typography>
      </Box>

      {/* Overview Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card
            sx={{
              background: `linear-gradient(135deg, ${
                alpha(theme.palette.success.main, 0.1)
              }, ${alpha(theme.palette.success.light, 0.05)})`,
              border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
            }}
          >
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <SuccessIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="subtitle2">Success Rate</Typography>
              </Box>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Typography
                  variant="h4"
                  color="success.main"
                  sx={{ fontWeight: 700 }}
                >
                  {Math.round(analyticsData.successRate)}%
                </Typography>
                {getPerformanceIcon(analyticsData.successRate)}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <AgentIcon sx={{ mr: 1 }} />
                <Typography variant="subtitle2">Total Tasks</Typography>
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {analyticsData.totalTasks.toLocaleString()}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                All time
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <SuccessIcon
                  sx={{ mr: 1, color: theme.palette.success.main }}
                />
                <Typography variant="subtitle2">Completed</Typography>
              </Box>
              <Typography
                variant="h4"
                color="success.main"
                sx={{ fontWeight: 700 }}
              >
                {analyticsData.completedTasks.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ p: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <ErrorIcon sx={{ mr: 1, color: theme.palette.error.main }} />
                <Typography variant="subtitle2">Failed</Typography>
              </Box>
              <Typography
                variant="h4"
                color="error.main"
                sx={{ fontWeight: 700 }}
              >
                {analyticsData.failedTasks.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs for different views */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs value={activeTab} onChange={handleTabChange}>
            <Tab
              label="Overview"
              value="overview"
              icon={<AnalyticsIcon />}
              iconPosition="start"
            />
            <Tab
              label="By Role"
              value="roles"
              icon={<AgentIcon />}
              iconPosition="start"
            />
            <Tab
              label="By Domain"
              value="domains"
              icon={<AgentIcon />}
              iconPosition="start"
            />
            <Tab
              label="Activity"
              value="activity"
              icon={<ActivityIcon />}
              iconPosition="start"
            />
          </Tabs>
        </Box>

        <CardContent>
          {/* Overview Tab */}
          {activeTab === "overview" && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  Task Distribution
                </Typography>
                <Box
                  sx={{
                    height: 250,
                    display: "flex",
                    justifyContent: "center",
                  }}
                >
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={successFailureData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, percent }) =>
                          `${name}: ${(percent * 100).toFixed(1)}%`}
                      >
                        {successFailureData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  Performance Summary
                </Typography>
                <Stack spacing={2}>
                  <Box>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        mb: 1,
                      }}
                    >
                      <Typography variant="body2">
                        Overall Success Rate
                      </Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {Math.round(analyticsData.successRate)}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={analyticsData.successRate}
                      sx={{
                        height: 8,
                        borderRadius: 4,
                        "& .MuiLinearProgress-bar": {
                          backgroundColor: getPerformanceColor(
                            analyticsData.successRate,
                          ),
                        },
                      }}
                    />
                  </Box>

                  <Divider />

                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Top Performing Roles
                    </Typography>
                    {rolePerformanceData.slice(0, 3).map((role, index) => (
                      <Box
                        key={role.role}
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          mb: 1,
                        }}
                      >
                        <Typography variant="body2">
                          {index + 1}. {role.role}
                        </Typography>
                        <Chip
                          size="small"
                          label={`${role.successRate}%`}
                          color={role.successRate >= 90
                            ? "success"
                            : role.successRate >= 75
                            ? "warning"
                            : "error"}
                        />
                      </Box>
                    ))}
                  </Box>
                </Stack>
              </Grid>
            </Grid>
          )}

          {/* Roles Tab */}
          {activeTab === "roles" && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Performance by Role
              </Typography>
              <Box sx={{ height: 400, width: "100%" }}>
                <ResponsiveContainer>
                  <BarChart data={rolePerformanceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="role"
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar
                      dataKey="successRate"
                      fill={theme.palette.primary.main}
                      name="Success Rate"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </Box>
          )}

          {/* Domains Tab */}
          {activeTab === "domains" && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Performance by Domain
              </Typography>
              <Box sx={{ height: 400, width: "100%" }}>
                <ResponsiveContainer>
                  <BarChart data={domainPerformanceData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="domain"
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar
                      dataKey="successRate"
                      fill={theme.palette.secondary.main}
                      name="Success Rate"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </Box>
          )}

          {/* Activity Tab */}
          {activeTab === "activity" && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Recent Activity Timeline
              </Typography>
              <Box sx={{ height: 400, width: "100%" }}>
                <ResponsiveContainer>
                  <AreaChart data={activityTimelineData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="successful"
                      stackId="1"
                      stroke={theme.palette.success.main}
                      fill={alpha(theme.palette.success.main, 0.6)}
                      name="Successful Tasks"
                    />
                    <Area
                      type="monotone"
                      dataKey="failed"
                      stackId="1"
                      stroke={theme.palette.error.main}
                      fill={alpha(theme.palette.error.main, 0.6)}
                      name="Failed Tasks"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
