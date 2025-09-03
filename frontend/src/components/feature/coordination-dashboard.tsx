/**
 * Coordination Dashboard Component
 * Main container for live coordination monitoring with real-time updates
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  Collapse,
  FormControlLabel,
  Grid,
  IconButton,
  Switch,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Dashboard as DashboardIcon,
  Fullscreen as FullscreenIcon,
  Pause as PauseIcon,
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
} from "@mui/icons-material";
import { AgentActivityStream } from "./agent-activity-stream";
import { ConflictAlertPanel } from "./conflict-alert-panel";
import { CollaborationMetricsPanel } from "./collaboration-metrics-panel";
import { Card, CardContent, CardHeader } from "@/components/ui";
import { Agent, CoordinationMetrics, FileLock, HookEvent } from "@/lib/types";

export interface CoordinationDashboardProps {
  agents?: Agent[];
  fileLocks?: FileLock[];
  events?: HookEvent[];
  metrics?: CoordinationMetrics;
  refreshInterval?: number;
  autoRefresh?: boolean;
  onDataRefresh?: () => Promise<void>;
  className?: string;
}

export const CoordinationDashboard: React.FC<CoordinationDashboardProps> = ({
  agents = [],
  fileLocks = [],
  events = [],
  metrics = {
    conflictsPrevented: 0,
    taskDeduplicationRate: 0,
    averageTaskCompletionTime: 0,
    activeAgents: 0,
    activeSessions: 0,
  },
  refreshInterval = 5000, // 5 seconds for real-time updates
  autoRefresh = true,
  onDataRefresh,
  className,
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isPaused, setIsPaused] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [refreshIntervalLocal, setRefreshIntervalLocal] = useState(
    refreshInterval,
  );
  const [error, setError] = useState<string | null>(null);

  // Mock data generation for demo purposes when no real data is provided
  const [mockAgents] = useState<Agent[]>([
    {
      id: "agent-001",
      role: "implementer",
      domain: "agentic-systems",
      status: "active",
      currentTask: "Live Coordination Monitor MVP Development",
      duration: 1200000, // 20 minutes
      sessionId: "session-001",
    },
    {
      id: "agent-002",
      role: "commentator",
      domain: "agentic-systems",
      status: "active",
      currentTask: "Documentation for coordination features",
      duration: 900000, // 15 minutes
      sessionId: "session-001",
    },
    {
      id: "agent-003",
      role: "tester",
      domain: "agentic-systems",
      status: "idle",
      sessionId: "session-001",
    },
  ]);

  const [mockEvents] = useState<HookEvent[]>([
    {
      id: "event-001",
      coordinationId: "plan_1756842242",
      agentId: "agent-001",
      eventType: "post_edit",
      timestamp: new Date(Date.now() - 120000).toISOString(),
      metadata: { operation: "create" },
      filePath:
        "/Users/lion/khived/frontend/src/components/feature/agent-activity-stream.tsx",
    },
    {
      id: "event-002",
      coordinationId: "plan_1756842242",
      agentId: "agent-002",
      eventType: "pre_edit",
      timestamp: new Date(Date.now() - 180000).toISOString(),
      metadata: { operation: "update" },
      filePath:
        "/Users/lion/khived/frontend/src/app/(dashboard)/coordination/page.tsx",
    },
    {
      id: "event-003",
      coordinationId: "plan_1756842242",
      agentId: "agent-001",
      eventType: "post_command",
      timestamp: new Date(Date.now() - 240000).toISOString(),
      metadata: { exitCode: 0 },
      command: "uv run khive coordinate pre-task",
    },
  ]);

  const [mockFileLocks] = useState<FileLock[]>([
    {
      filePath:
        "/Users/lion/khived/frontend/src/app/(dashboard)/coordination/page.tsx",
      agentId: "agent-002",
      expiration: new Date(Date.now() + 300000).toISOString(), // 5 minutes from now
      isStale: false,
    },
  ]);

  // Use provided data or fallback to mock data for demo
  const displayAgents = agents.length > 0 ? agents : mockAgents;
  const displayEvents = events.length > 0 ? events : mockEvents;
  const displayFileLocks = fileLocks.length > 0 ? fileLocks : mockFileLocks;

  // Auto-refresh mechanism
  useEffect(() => {
    if (!autoRefresh || isPaused) return;

    const interval = setInterval(async () => {
      try {
        setIsRefreshing(true);
        await refreshData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to refresh data");
      } finally {
        setIsRefreshing(false);
      }
    }, refreshIntervalLocal);

    return () => clearInterval(interval);
  }, [autoRefresh, isPaused, refreshIntervalLocal, onDataRefresh]);

  const refreshData = useCallback(async () => {
    setLastUpdate(new Date());
    setError(null);

    if (onDataRefresh) {
      await onDataRefresh();
    }
  }, [onDataRefresh]);

  const handleManualRefresh = async () => {
    if (isRefreshing) return;

    setIsRefreshing(true);
    try {
      await refreshData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh data");
    } finally {
      setIsRefreshing(false);
    }
  };

  const togglePause = () => {
    setIsPaused(!isPaused);
  };

  const getSystemStatus = () => {
    const activeAgentsCount =
      displayAgents.filter((a) => a.status === "active").length;
    const errorAgentsCount =
      displayAgents.filter((a) => a.status === "error").length;
    const conflictsCount =
      displayFileLocks.filter((lock) =>
        displayFileLocks.filter((l) => l.filePath === lock.filePath).length > 1
      ).length;

    if (errorAgentsCount > 0 || conflictsCount > 0) return "warning";
    if (activeAgentsCount === 0) return "idle";
    return "healthy";
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
        return "success";
      case "warning":
        return "warning";
      case "idle":
        return "info";
      default:
        return "default";
    }
  };

  const systemStatus = getSystemStatus();

  return (
    <Box className={className}>
      {/* Header */}
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardHeader
          title={
            <Box display="flex" alignItems="center" gap={2}>
              <DashboardIcon color="primary" />
              <Typography variant="h5" component="h1">
                Live Coordination Monitor
              </Typography>
              <Chip
                label={systemStatus}
                color={getStatusColor(systemStatus) as any}
                variant="filled"
                size="small"
              />
              <Chip
                label={isPaused ? "Paused" : "Live"}
                color={isPaused ? "warning" : "success"}
                variant="outlined"
                size="small"
              />
            </Box>
          }
          subtitle={
            <Typography variant="body2" color="text.secondary">
              Real-time monitoring of agent coordination, conflicts, and
              collaboration
            </Typography>
          }
          action={
            <Box display="flex" alignItems="center" gap={1}>
              <Typography variant="caption" color="text.secondary">
                Last update: {lastUpdate.toLocaleTimeString()}
              </Typography>

              <Tooltip title={isPaused ? "Resume updates" : "Pause updates"}>
                <IconButton onClick={togglePause} color="primary">
                  {isPaused ? <PlayIcon /> : <PauseIcon />}
                </IconButton>
              </Tooltip>

              <Tooltip title="Manual refresh">
                <IconButton
                  onClick={handleManualRefresh}
                  disabled={isRefreshing}
                  color="primary"
                >
                  <RefreshIcon className={isRefreshing ? "animate-spin" : ""} />
                </IconButton>
              </Tooltip>

              <Tooltip title="Dashboard settings">
                <IconButton
                  onClick={() => setShowSettings(!showSettings)}
                  color="primary"
                >
                  <SettingsIcon />
                </IconButton>
              </Tooltip>
            </Box>
          }
        />

        <Collapse in={showSettings}>
          <CardContent>
            <Grid container spacing={2} alignItems="center">
              <Grid item>
                <FormControlLabel
                  control={
                    <Switch
                      checked={autoRefresh}
                      onChange={(e) =>
                        setRefreshIntervalLocal(
                          e.target.checked ? refreshInterval : 0,
                        )}
                    />
                  }
                  label="Auto-refresh"
                />
              </Grid>
              <Grid item>
                <Typography variant="body2" color="text.secondary">
                  Refresh interval: {refreshIntervalLocal / 1000}s
                </Typography>
              </Grid>
            </Grid>
          </CardContent>
        </Collapse>
      </Card>

      {/* Error Banner */}
      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      {/* Main Dashboard Grid */}
      <Grid container spacing={2}>
        {/* Metrics Panel - Top Row */}
        <Grid item xs={12}>
          <CollaborationMetricsPanel
            metrics={metrics}
            agents={displayAgents}
            fileLocks={displayFileLocks}
            events={displayEvents}
            onRefresh={handleManualRefresh}
          />
        </Grid>

        {/* Activity Stream - Left Column */}
        <Grid item xs={12} lg={8}>
          <AgentActivityStream
            events={displayEvents}
            agents={displayAgents}
            maxEvents={20}
            autoRefresh={!isPaused}
          />
        </Grid>

        {/* Conflict Alerts - Right Column */}
        <Grid item xs={12} lg={4}>
          <ConflictAlertPanel
            fileLocks={displayFileLocks}
            agents={displayAgents}
            events={displayEvents}
            autoGenerateAlerts={true}
          />
        </Grid>
      </Grid>

      {/* Status Footer */}
      <Card variant="outlined" sx={{ mt: 2, backgroundColor: "grey.50" }}>
        <CardContent sx={{ py: 1 }}>
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
          >
            <Typography variant="caption" color="text.secondary">
              Monitoring {displayAgents.length} agents across{" "}
              {displayFileLocks.length} file locks • {displayEvents.length}{" "}
              recent events
            </Typography>
            <Box display="flex" alignItems="center" gap={1}>
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  backgroundColor: isPaused ? "warning.main" : "success.main",
                }}
              />
              <Typography variant="caption" color="text.secondary">
                {isPaused ? "Updates paused" : "Live monitoring active"}
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};
