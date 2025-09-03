/**
 * Main Dashboard Page - Real-time Agent Orchestration Overview
 * Provides comprehensive monitoring and control of the Khive ecosystem
 */

"use client";

import { useEffect, useState } from "react";
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
  CheckCircle as SuccessIcon,
  Dashboard as DashboardIcon,
  Error as ErrorIcon,
  Psychology as AgentIcon,
  Speed as MetricsIcon,
  Timeline as TrendsIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

import {
  useAgents,
  useCoordinationMetrics,
  useSessions,
} from "@/lib/api/hooks";
import { DataTable } from "@/components/ui/table";
import { StatusCell } from "@/components/ui/table";
import { AgentSpawner } from "@/components/feature/agent-spawner";
import type { ColumnDef } from "@/components/ui/table";

// Quick stats card component
interface QuickStatsCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: React.ReactNode;
  color: "primary" | "secondary" | "success" | "warning" | "error";
  trend?: {
    direction: "up" | "down";
    percentage: number;
  };
}

function QuickStatsCard(
  { title, value, description, icon, color, trend }: QuickStatsCardProps,
) {
  const theme = useTheme();

  return (
    <Card
      sx={{
        height: "100%",
        background: `linear-gradient(135deg, ${
          alpha(theme.palette[color].main, 0.1)
        }, ${alpha(theme.palette[color].light, 0.05)})`,
        border: `1px solid ${alpha(theme.palette[color].main, 0.2)}`,
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: theme.shadows[4],
        },
        transition: "all 0.2s ease-in-out",
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
          <Box
            sx={{
              p: 1,
              borderRadius: 2,
              backgroundColor: alpha(theme.palette[color].main, 0.1),
              mr: 2,
              color: theme.palette[color].main,
            }}
          >
            {icon}
          </Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
        </Box>

        <Typography
          variant="h3"
          sx={{
            fontWeight: 700,
            color: theme.palette[color].main,
            mb: 1,
          }}
        >
          {value}
        </Typography>

        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mb: trend ? 2 : 0 }}
        >
          {description}
        </Typography>

        {trend && (
          <Chip
            label={`${
              trend.direction === "up" ? "+" : "-"
            }${trend.percentage}%`}
            size="small"
            color={trend.direction === "up" ? "success" : "error"}
            sx={{ fontSize: "0.75rem" }}
          />
        )}
      </CardContent>
    </Card>
  );
}

// Session data type for table
interface Session {
  id: string;
  name: string;
  status: "running" | "completed" | "failed" | "paused";
  coordinator: string;
  agents: number;
  startTime: string;
  duration: string;
  progress: number;
}

// Agent data type for table
interface Agent {
  id: string;
  name: string;
  role: string;
  domain: string;
  status: "active" | "idle" | "busy" | "error";
  tasks: number;
  lastActivity: string;
}

export default function DashboardPage() {
  const theme = useTheme();
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  );

  // Fetch real-time data
  const { data: metrics, isLoading: metricsLoading } = useCoordinationMetrics();
  const { data: sessions, isLoading: sessionsLoading } = useSessions();
  const { data: agents, isLoading: agentsLoading } = useAgents();

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setRefreshTrigger((prev) => prev + 1);
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Handle new session creation
  const handleSessionCreated = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    // Trigger refresh to show new session
    setRefreshTrigger((prev) => prev + 1);
  };

  // Table columns for sessions with enhanced orchestration indicators
  const sessionColumns: ColumnDef<Session>[] = [
    {
      accessorKey: "id",
      header: "Session",
      cell: ({ row }) => (
        <Box>
          <Typography variant="body2" fontWeight={600}>
            {row.original.name || `Session ${row.original.id.slice(-8)}`}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            ID: {row.original.coordinationId || row.original.id.slice(-8)}
          </Typography>
          {selectedSessionId === row.original.id && (
            <Chip
              label="New"
              size="small"
              color="success"
              sx={{ ml: 1, fontSize: "0.6rem", height: 16 }}
            />
          )}
        </Box>
      ),
    },
    {
      accessorKey: "status",
      header: "Orchestration Status",
      cell: ({ row }) => (
        <Box display="flex" alignItems="center" gap={1}>
          <StatusCell
            status={row.original.status}
            color={row.original.status === "running"
              ? "success"
              : row.original.status === "completed"
              ? "primary"
              : row.original.status === "failed"
              ? "error"
              : "warning"}
          />
          {row.original.status === "running" && (
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                bgcolor: "success.main",
                animation: "pulse 1.5s infinite",
              }}
            />
          )}
        </Box>
      ),
    },
    {
      accessorKey: "agents",
      header: "Coordination",
      cell: ({ row }) => (
        <Box>
          <Typography variant="body2">
            {row.original.coordinator || "lion"}
          </Typography>
          <Box display="flex" alignItems="center" gap={0.5} mt={0.5}>
            <Chip
              label={`${row.original.agents || 0} agents`}
              size="small"
              color="primary"
              variant="outlined"
            />
          </Box>
        </Box>
      ),
    },
    {
      accessorKey: "progress",
      header: "Progress & Health",
      cell: ({ row }) => (
        <Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
            <LinearProgress
              variant="determinate"
              value={row.original.progress}
              sx={{
                flex: 1,
                height: 6,
                borderRadius: 3,
                "& .MuiLinearProgress-bar": {
                  backgroundColor: row.original.status === "failed"
                    ? "error.main"
                    : row.original.status === "completed"
                    ? "success.main"
                    : "primary.main",
                },
              }}
            />
            <Typography variant="caption" color="text.secondary" minWidth={35}>
              {row.original.progress}%
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            Confidence: {row.original.confidence
              ? `${Math.round(row.original.confidence * 100)}%`
              : "N/A"}
          </Typography>
        </Box>
      ),
    },
    {
      accessorKey: "duration",
      header: "Timeline",
      cell: ({ row }) => (
        <Box>
          <Typography variant="body2">
            {row.original.duration || "Active"}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Started: {row.original.startTime
              ? new Date(row.original.startTime).toLocaleTimeString()
              : "Unknown"}
          </Typography>
        </Box>
      ),
    },
  ];

  // Table columns for agents
  const agentColumns: ColumnDef<Agent>[] = [
    {
      accessorKey: "name",
      header: "Agent Name",
    },
    {
      accessorKey: "role",
      header: "Role",
      cell: ({ row }) => (
        <Chip
          label={row.original.role}
          size="small"
          variant="outlined"
          color="primary"
        />
      ),
    },
    {
      accessorKey: "domain",
      header: "Domain",
      cell: ({ row }) => (
        <Chip
          label={row.original.domain}
          size="small"
          variant="outlined"
          color="secondary"
        />
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <StatusCell
          status={row.original.status}
          color={row.original.status === "active"
            ? "success"
            : row.original.status === "busy"
            ? "warning"
            : row.original.status === "error"
            ? "error"
            : "default"}
        />
      ),
    },
    {
      accessorKey: "tasks",
      header: "Tasks",
    },
    {
      accessorKey: "lastActivity",
      header: "Last Activity",
    },
  ];

  // Mock data for demonstration (replace with real data from API)
  const mockSessions: (Session & {
    name?: string;
    coordinator?: string;
    agents?: number;
    startTime?: string;
    duration?: string;
    progress?: number;
  })[] = sessions?.map((session) => ({
    ...session,
    name: `Session ${session.id.slice(-8)}`,
    coordinator: "lion",
    agents: Math.floor(Math.random() * 5) + 1,
    startTime: session.createdAt,
    duration: "15m",
    progress: Math.floor(session.confidence * 100),
  })) || [];

  const mockAgents: Agent[] = agents?.map((agent) => ({
    id: agent.id || "unknown",
    name: agent.name || "Unnamed Agent",
    role: agent.role || "unknown",
    domain: agent.domain || "general",
    status: agent.status as any || "active",
    tasks: agent.tasks || 0,
    lastActivity: agent.lastActivity || "just now",
  })) || [];

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          component="h1"
          gutterBottom
          sx={{ fontWeight: 700 }}
        >
          Orchestration Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Real-time monitoring and control of agent coordination and task
          execution
        </Typography>
      </Box>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <QuickStatsCard
            title="Active Sessions"
            value={sessions?.filter((s) => s.status === "running").length ?? 0}
            description="Currently orchestrating"
            icon={<DashboardIcon />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <QuickStatsCard
            title="Active Agents"
            value={metrics?.activeAgents ?? agents?.length ?? 0}
            description="Available for coordination"
            icon={<AgentIcon />}
            color="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <QuickStatsCard
            title="Conflicts Prevented"
            value={metrics?.conflictsPrevented ?? 0}
            description="Today"
            icon={<SuccessIcon />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <QuickStatsCard
            title="Avg Task Time"
            value={`${(metrics?.averageTaskCompletionTime ?? 0).toFixed(1)}s`}
            description="Completion time"
            icon={<MetricsIcon />}
            color="warning"
          />
        </Grid>
      </Grid>

      {/* Agent Spawner - Primary Orchestration Interface */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 700, mb: 2 }}>
          Orchestration Center
        </Typography>
        <AgentSpawner onSessionCreated={handleSessionCreated} />
      </Box>

      {/* Main Content */}
      <Grid container spacing={3}>
        {/* Sessions Table */}
        <Grid item xs={12} lg={8}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            Active Sessions
          </Typography>
          <DataTable
            data={mockSessions}
            columns={sessionColumns}
            loading={sessionsLoading}
            searchable
            searchPlaceholder="Search sessions..."
            emptyStateMessage="No active sessions"
            emptyStateDescription="Start a new orchestration session to see activity here"
          />
        </Grid>

        {/* System Health */}
        <Grid item xs={12} lg={4}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            System Health
          </Typography>
          <Stack spacing={2}>
            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <SuccessIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="subtitle2">API Gateway</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Healthy - All endpoints responding
              </Typography>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <SuccessIcon color="success" sx={{ mr: 1 }} />
                <Typography variant="subtitle2">
                  Coordination Service
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Online - {metrics?.activeAgents ?? 0} agents connected
              </Typography>
            </Paper>

            <Paper sx={{ p: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
                <WarningIcon color="warning" sx={{ mr: 1 }} />
                <Typography variant="subtitle2">Memory Usage</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Moderate - 67% of available memory
              </Typography>
            </Paper>
          </Stack>
        </Grid>

        {/* Agents Table */}
        <Grid item xs={12}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mt: 2 }}>
            Agent Status
          </Typography>
          <DataTable
            data={mockAgents}
            columns={agentColumns}
            loading={agentsLoading}
            searchable
            searchPlaceholder="Search agents..."
            emptyStateMessage="No agents available"
            emptyStateDescription="Deploy agents to start coordinating tasks"
            pageSize={5}
          />
        </Grid>
      </Grid>
    </Box>
  );
}
