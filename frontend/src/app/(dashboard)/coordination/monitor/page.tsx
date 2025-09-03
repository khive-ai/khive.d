/**
 * Live Coordination Monitor MVP
 * Real-time dashboard showing agent coordination, file conflicts, and collaboration metrics
 */

"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  alpha,
  Box,
  Card,
  CardContent,
  Divider,
  FormControlLabel,
  Grid,
  IconButton,
  Stack,
  Switch,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  FilterList as FilterIcon,
  Notifications as NotificationsIcon,
  Pause as PauseIcon,
  PlayArrow as PlayIcon,
  Psychology as AgentIcon,
  Refresh as RefreshIcon,
  Speed as MetricsIcon,
  Timeline as TimelineIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

import {
  useAgents,
  useCoordinationMetrics,
  useEvents,
  useFileLocks,
  useInvalidateQueries,
} from "@/lib/api/hooks";
import { AgentActivityStream } from "@/components/feature/coordination/agent-activity-stream";
import { ConflictAlertsPanel } from "@/components/feature/coordination/conflict-alerts-panel";
import { CollaborationMetricsDashboard } from "@/components/feature/coordination/collaboration-metrics-dashboard";
import { LiveStatusIndicator } from "@/components/feature/coordination/live-status-indicator";

export default function LiveCoordinationMonitorPage() {
  const theme = useTheme();
  const [isRealTimeEnabled, setIsRealTimeEnabled] = useState(true);
  const [refreshRate, setRefreshRate] = useState(2000); // 2 seconds default
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());
  const { invalidateAll } = useInvalidateQueries();

  // Real-time data fetching
  const {
    data: events,
    refetch: refetchEvents,
    isLoading: eventsLoading,
  } = useEvents(undefined, {
    refetchInterval: isRealTimeEnabled ? refreshRate : false,
    onSuccess: () => setLastUpdateTime(new Date()),
  });

  const {
    data: metrics,
    refetch: refetchMetrics,
    isLoading: metricsLoading,
  } = useCoordinationMetrics({
    refetchInterval: isRealTimeEnabled ? 10000 : false, // 10 seconds for metrics
  });

  const {
    data: agents,
    refetch: refetchAgents,
  } = useAgents({
    refetchInterval: isRealTimeEnabled ? 5000 : false, // 5 seconds for agents
  });

  const {
    data: fileLocks,
    refetch: refetchFileLocks,
  } = useFileLocks({
    refetchInterval: isRealTimeEnabled ? 3000 : false, // 3 seconds for file locks
  });

  // Manual refresh function
  const handleManualRefresh = () => {
    invalidateAll();
    setLastUpdateTime(new Date());
  };

  // Toggle real-time monitoring
  const toggleRealTime = () => {
    setIsRealTimeEnabled(!isRealTimeEnabled);
    if (!isRealTimeEnabled) {
      setLastUpdateTime(new Date());
    }
  };

  // Auto-refresh every 30 seconds as fallback
  useEffect(() => {
    if (!isRealTimeEnabled) return;

    const interval = setInterval(() => {
      handleManualRefresh();
    }, 30000);

    return () => clearInterval(interval);
  }, [isRealTimeEnabled]);

  return (
    <Box sx={{ p: 3 }}>
      {/* Header with Controls */}
      <Box sx={{ mb: 4 }}>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="flex-start"
        >
          <Box>
            <Typography
              variant="h4"
              component="h1"
              gutterBottom
              sx={{ fontWeight: 700 }}
            >
              Live Coordination Monitor
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Real-time dashboard for agent coordination, conflict detection,
              and collaboration metrics
            </Typography>
          </Box>

          <Box display="flex" alignItems="center" gap={2}>
            <LiveStatusIndicator
              isLive={isRealTimeEnabled}
              lastUpdate={lastUpdateTime}
            />

            <Stack direction="row" spacing={1} alignItems="center">
              <FormControlLabel
                control={
                  <Switch
                    checked={isRealTimeEnabled}
                    onChange={toggleRealTime}
                    color="primary"
                  />
                }
                label="Real-time"
                sx={{ m: 0 }}
              />

              <Tooltip title="Manual Refresh">
                <IconButton onClick={handleManualRefresh} color="primary">
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Stack>
          </Box>
        </Box>

        {/* System Status Alert */}
        <Box sx={{ mt: 2 }}>
          <Alert
            severity={metrics?.activeAgents ? "success" : "warning"}
            variant="outlined"
            icon={metrics?.activeAgents ? <CheckCircleIcon /> : <WarningIcon />}
          >
            <Typography variant="body2">
              {metrics?.activeAgents
                ? `Coordination system operational - ${metrics.activeAgents} active agents, ${metrics.activeSessions} sessions`
                : "No active coordination detected - System ready for agent spawning"}
            </Typography>
          </Alert>
        </Box>
      </Box>

      {/* Main Dashboard Grid */}
      <Grid container spacing={3}>
        {/* Collaboration Metrics Dashboard - Top Row */}
        <Grid item xs={12}>
          <CollaborationMetricsDashboard
            metrics={metrics}
            agents={agents}
            fileLocks={fileLocks}
            isLoading={metricsLoading}
            isRealTime={isRealTimeEnabled}
          />
        </Grid>

        {/* Agent Activity Stream - Left Column */}
        <Grid item xs={12} lg={8}>
          <Card sx={{ height: 600 }}>
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <TimelineIcon color="primary" />
                  <Typography variant="h6">
                    Agent Activity Stream
                  </Typography>
                  {events && (
                    <Typography variant="caption" color="text.secondary">
                      ({events.length} events)
                    </Typography>
                  )}
                </Box>

                <Stack direction="row" spacing={1}>
                  <Tooltip title="Filter Events">
                    <IconButton size="small">
                      <FilterIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Box>

              <AgentActivityStream
                events={events || []}
                agents={agents || []}
                isLoading={eventsLoading}
                isRealTime={isRealTimeEnabled}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Conflict Alerts Panel - Right Column */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ height: 600 }}>
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <WarningIcon color="warning" />
                  <Typography variant="h6">
                    Conflict Alerts
                  </Typography>
                </Box>

                <Tooltip title="Alert Settings">
                  <IconButton size="small">
                    <NotificationsIcon />
                  </IconButton>
                </Tooltip>
              </Box>

              <ConflictAlertsPanel
                fileLocks={fileLocks || []}
                events={events || []}
                isRealTime={isRealTimeEnabled}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Footer Info */}
      <Box
        sx={{ mt: 4, pt: 3, borderTop: `1px solid ${theme.palette.divider}` }}
      >
        <Typography variant="caption" color="text.secondary" display="block">
          Live Coordination Monitor MVP - Agent coordination dashboard with
          real-time updates
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Last updated: {lastUpdateTime.toLocaleTimeString()} • Refresh rate:
          {" "}
          {refreshRate / 1000}s • Real-time: {isRealTimeEnabled ? "ON" : "OFF"}
        </Typography>
      </Box>
    </Box>
  );
}
