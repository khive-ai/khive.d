/**
 * Coordination Center - Main Orchestration Interface
 * Provides agent spawning, task management, and orchestration status
 */

"use client";

import { useEffect, useState } from "react";
import {
  Alert,
  alpha,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemSecondaryAction,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Add as AddIcon,
  CheckCircle,
  CheckCircle as CompletedIcon,
  Delete as DeleteIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Pause as PauseIcon,
  PlayArrow as StartIcon,
  Psychology as AgentIcon,
  Refresh as RefreshIcon,
  Speed as MetricsIcon,
  Stop as StopIcon,
  Task as TaskIcon,
  Timeline as CoordinationIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

import {
  useAgents,
  useCoordinationMetrics,
  useCreateSession,
  useDomains,
  useEvents,
  useFileLocks,
  useRoles,
  useSessions,
} from "@/lib/api/hooks";
import { useCoordinationWebSocket } from "@/lib/hooks/use-websocket";
import { DataTable } from "@/components/ui/table";
import { StatusCell } from "@/components/ui/table";
import type { ColumnDef } from "@/components/ui/table";

// Types for the agent spawning form
interface AgentSpawnRequest {
  role: string;
  domain: string;
  taskDescription: string;
  coordinationId?: string;
  priority: "low" | "normal" | "high";
}

// Types for task management
interface Task {
  id: string;
  description: string;
  agentId?: string;
  status: "pending" | "running" | "completed" | "failed";
  priority: "low" | "normal" | "high";
  createdAt: string;
  estimatedDuration?: number;
  progress?: number;
}

// Agent spawning form component
function AgentSpawnForm({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (request: AgentSpawnRequest) => void;
}) {
  const { data: roles, isLoading: rolesLoading } = useRoles();
  const { data: domains, isLoading: domainsLoading } = useDomains();

  const [formData, setFormData] = useState<AgentSpawnRequest>({
    role: "",
    domain: "",
    taskDescription: "",
    priority: "normal",
  });

  const handleSubmit = () => {
    if (formData.role && formData.domain && formData.taskDescription) {
      onSubmit(formData);
      setFormData({
        role: "",
        domain: "",
        taskDescription: "",
        priority: "normal",
      });
      onClose();
    }
  };

  const isFormValid = formData.role && formData.domain &&
    formData.taskDescription;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <AgentIcon color="primary" />
          <Typography variant="h6">Spawn New Agent</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={3} sx={{ mt: 1 }}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={formData.role}
                label="Role"
                onChange={(e) =>
                  setFormData({ ...formData, role: e.target.value })}
                disabled={rolesLoading}
              >
                {roles?.map((role) => (
                  <MenuItem key={role.id} value={role.name}>
                    <Box>
                      <Typography variant="body1">{role.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {role.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Domain</InputLabel>
              <Select
                value={formData.domain}
                label="Domain"
                onChange={(e) =>
                  setFormData({ ...formData, domain: e.target.value })}
                disabled={domainsLoading}
              >
                {domains?.map((domain) => (
                  <MenuItem key={domain.id} value={domain.name}>
                    <Box>
                      <Typography variant="body1">{domain.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {domain.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Task Description"
              multiline
              rows={3}
              value={formData.taskDescription}
              onChange={(e) =>
                setFormData({ ...formData, taskDescription: e.target.value })}
              placeholder="Describe the specific task for this agent..."
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Priority</InputLabel>
              <Select
                value={formData.priority}
                label="Priority"
                onChange={(e) =>
                  setFormData({ ...formData, priority: e.target.value as any })}
              >
                <MenuItem value="low">
                  <Box display="flex" alignItems="center" gap={1}>
                    <InfoIcon color="info" fontSize="small" />
                    Low Priority
                  </Box>
                </MenuItem>
                <MenuItem value="normal">
                  <Box display="flex" alignItems="center" gap={1}>
                    <TaskIcon color="primary" fontSize="small" />
                    Normal Priority
                  </Box>
                </MenuItem>
                <MenuItem value="high">
                  <Box display="flex" alignItems="center" gap={1}>
                    <WarningIcon color="warning" fontSize="small" />
                    High Priority
                  </Box>
                </MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={!isFormValid}
          startIcon={<StartIcon />}
        >
          Spawn Agent
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// Task list component
function TaskList({ tasks }: { tasks: Task[] }) {
  const theme = useTheme();

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "success";
      case "running":
        return "primary";
      case "failed":
        return "error";
      default:
        return "default";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CompletedIcon />;
      case "running":
        return <StartIcon />;
      case "failed":
        return <ErrorIcon />;
      default:
        return <TaskIcon />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return theme.palette.error.main;
      case "normal":
        return theme.palette.primary.main;
      case "low":
        return theme.palette.grey[500];
      default:
        return theme.palette.grey[500];
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Task Queue ({tasks.length})
        </Typography>

        {tasks.length === 0
          ? (
            <Box
              display="flex"
              flexDirection="column"
              alignItems="center"
              justifyContent="center"
              py={4}
              color="text.secondary"
            >
              <TaskIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
              <Typography variant="body1">No tasks in queue</Typography>
              <Typography variant="body2">
                Spawn agents to start coordinating tasks
              </Typography>
            </Box>
          )
          : (
            <List>
              {tasks.map((task, index) => (
                <Box key={task.id}>
                  <ListItem>
                    <ListItemIcon>
                      {getStatusIcon(task.status)}
                    </ListItemIcon>
                    <ListItemText
                      primary={task.description}
                      secondary={
                        <Box component="span">
                          <Typography variant="caption" color="text.secondary">
                            Created: {new Date(task.createdAt).toLocaleString()}
                          </Typography>
                          {task.progress !== undefined && (
                            <Box sx={{ mt: 1 }}>
                              <LinearProgress
                                variant="determinate"
                                value={task.progress}
                                sx={{ height: 6, borderRadius: 3 }}
                              />
                            </Box>
                          )}
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Chip
                          size="small"
                          label={task.priority}
                          sx={{
                            backgroundColor: alpha(
                              getPriorityColor(task.priority),
                              0.1,
                            ),
                            color: getPriorityColor(task.priority),
                            fontWeight: 600,
                          }}
                        />
                        <Chip
                          size="small"
                          label={task.status}
                          color={getStatusColor(task.status) as any}
                        />
                        <Tooltip title="Remove task">
                          <IconButton size="small">
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    </ListItemSecondaryAction>
                  </ListItem>
                  {index < tasks.length - 1 && <Divider />}
                </Box>
              ))}
            </List>
          )}
      </CardContent>
    </Card>
  );
}

// Orchestration status indicator
function OrchestrationStatus() {
  const { data: metrics, isLoading } = useCoordinationMetrics();
  const { data: events } = useEvents();
  const theme = useTheme();

  if (isLoading) {
    return <LinearProgress />;
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Orchestration Status
        </Typography>

        <Grid container spacing={2}>
          <Grid item xs={6} sm={3}>
            <Paper
              sx={{
                p: 2,
                textAlign: "center",
                bgcolor: alpha(theme.palette.success.main, 0.1),
                border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
              }}
            >
              <Typography variant="h4" color="success.main" fontWeight="bold">
                {metrics?.activeAgents || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Active Agents
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={6} sm={3}>
            <Paper
              sx={{
                p: 2,
                textAlign: "center",
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
              }}
            >
              <Typography variant="h4" color="primary.main" fontWeight="bold">
                {metrics?.activeSessions || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Active Sessions
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={6} sm={3}>
            <Paper
              sx={{
                p: 2,
                textAlign: "center",
                bgcolor: alpha(theme.palette.warning.main, 0.1),
                border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
              }}
            >
              <Typography variant="h4" color="warning.main" fontWeight="bold">
                {metrics?.conflictsPrevented || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Conflicts Prevented
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={6} sm={3}>
            <Paper
              sx={{
                p: 2,
                textAlign: "center",
                bgcolor: alpha(theme.palette.secondary.main, 0.1),
                border: `1px solid ${alpha(theme.palette.secondary.main, 0.2)}`,
              }}
            >
              <Typography variant="h4" color="secondary.main" fontWeight="bold">
                {events?.length || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Recent Events
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        <Box mt={2}>
          <Alert severity="info" variant="outlined">
            <Typography variant="body2">
              System operational - All coordination services running normally
            </Typography>
          </Alert>
        </Box>
      </CardContent>
    </Card>
  );
}

// Live Agent Activity Stream - MVP Feature 1
function AgentActivityStream() {
  const { data: events, isLoading } = useEvents();
  const theme = useTheme();

  const getEventTypeColor = (eventType: string) => {
    switch (eventType) {
      case "pre_command":
      case "post_command":
        return theme.palette.primary.main;
      case "pre_edit":
      case "post_edit":
        return theme.palette.warning.main;
      case "pre_agent_spawn":
      case "post_agent_spawn":
        return theme.palette.success.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case "pre_command":
      case "post_command":
        return <StartIcon fontSize="small" />;
      case "pre_edit":
      case "post_edit":
        return <WarningIcon fontSize="small" />;
      case "pre_agent_spawn":
      case "post_agent_spawn":
        return <AgentIcon fontSize="small" />;
      default:
        return <InfoIcon fontSize="small" />;
    }
  };

  const formatEventDescription = (event: any) => {
    switch (event.eventType) {
      case "pre_command":
        return `Starting: ${event.command || "Command"}`;
      case "post_command":
        return `Completed: ${event.command || "Command"}`;
      case "pre_edit":
        return `Editing: ${event.filePath?.split("/").pop() || "File"}`;
      case "post_edit":
        return `Modified: ${event.filePath?.split("/").pop() || "File"}`;
      case "pre_agent_spawn":
        return `Spawning agent: ${event.metadata?.role || "Unknown"}`;
      case "post_agent_spawn":
        return `Agent spawned: ${event.metadata?.role || "Unknown"}`;
      default:
        return event.eventType.replace(/_/g, " ");
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Agent Activity Stream
          </Typography>
          <LinearProgress />
        </CardContent>
      </Card>
    );
  }

  const recentEvents = events?.slice(0, 10) || [];

  return (
    <Card>
      <CardContent>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
        >
          <Typography variant="h6">
            Agent Activity Stream
          </Typography>
          <Chip
            size="small"
            label={`${recentEvents.length} recent`}
            color="primary"
            variant="outlined"
          />
        </Box>

        {recentEvents.length === 0
          ? (
            <Box
              display="flex"
              flexDirection="column"
              alignItems="center"
              justifyContent="center"
              py={3}
              color="text.secondary"
            >
              <CoordinationIcon sx={{ fontSize: 40, mb: 1, opacity: 0.5 }} />
              <Typography variant="body2">No recent activity</Typography>
            </Box>
          )
          : (
            <Stack spacing={1}>
              {recentEvents.map((event, index) => (
                <Paper
                  key={`${event.id}-${index}`}
                  sx={{
                    p: 2,
                    border: `1px solid ${
                      alpha(getEventTypeColor(event.eventType), 0.2)
                    }`,
                    bgcolor: alpha(getEventTypeColor(event.eventType), 0.05),
                  }}
                >
                  <Box display="flex" alignItems="flex-start" gap={1}>
                    <Box
                      sx={{
                        color: getEventTypeColor(event.eventType),
                        mt: 0.25,
                      }}
                    >
                      {getEventIcon(event.eventType)}
                    </Box>
                    <Box flex={1}>
                      <Typography variant="body2" fontWeight="medium">
                        {formatEventDescription(event)}
                      </Typography>
                      <Box
                        display="flex"
                        justifyContent="space-between"
                        alignItems="center"
                        mt={0.5}
                      >
                        <Typography variant="caption" color="text.secondary">
                          Agent: {event.agentId?.split("_")[0] || "system"}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </Typography>
                      </Box>
                    </Box>
                  </Box>
                </Paper>
              ))}
            </Stack>
          )}
      </CardContent>
    </Card>
  );
}

// Basic Conflict Alerts - MVP Feature 2
function ConflictAlerts() {
  const { data: fileLocks, isLoading } = useFileLocks();
  const { data: metrics } = useCoordinationMetrics();
  const theme = useTheme();

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Conflict Monitor
          </Typography>
          <LinearProgress />
        </CardContent>
      </Card>
    );
  }

  const activeLocks = fileLocks?.filter((lock) => !lock.isStale) || [];
  const staleLocks = fileLocks?.filter((lock) => lock.isStale) || [];

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Conflict Monitor
        </Typography>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={4}>
            <Paper
              sx={{
                p: 1.5,
                textAlign: "center",
                bgcolor: alpha(theme.palette.success.main, 0.1),
                border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
              }}
            >
              <Typography variant="h6" color="success.main" fontWeight="bold">
                {metrics?.conflictsPrevented || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Prevented
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={4}>
            <Paper
              sx={{
                p: 1.5,
                textAlign: "center",
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
              }}
            >
              <Typography variant="h6" color="primary.main" fontWeight="bold">
                {activeLocks.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Active Locks
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={4}>
            <Paper
              sx={{
                p: 1.5,
                textAlign: "center",
                bgcolor: alpha(theme.palette.warning.main, 0.1),
                border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
              }}
            >
              <Typography variant="h6" color="warning.main" fontWeight="bold">
                {staleLocks.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Stale Locks
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        {staleLocks.length > 0 && (
          <Alert severity="warning" sx={{ mb: 1 }}>
            <Typography variant="body2">
              {staleLocks.length}{" "}
              stale file lock(s) detected - cleanup may be needed
            </Typography>
          </Alert>
        )}

        {activeLocks.length > 0 && (
          <Stack spacing={1}>
            <Typography variant="subtitle2" color="text.secondary">
              Active File Locks:
            </Typography>
            {activeLocks.map((lock, index) => (
              <Paper
                key={index}
                sx={{
                  p: 1.5,
                  bgcolor: alpha(theme.palette.primary.main, 0.05),
                  border: `1px solid ${alpha(theme.palette.primary.main, 0.1)}`,
                }}
              >
                <Box
                  display="flex"
                  justifyContent="space-between"
                  alignItems="center"
                >
                  <Box>
                    <Typography variant="body2" fontWeight="medium">
                      {lock.filePath.split("/").pop()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Agent: {lock.agentId?.split("_")[0]}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    Expires: {new Date(lock.expiration).toLocaleTimeString()}
                  </Typography>
                </Box>
              </Paper>
            ))}
          </Stack>
        )}

        {activeLocks.length === 0 && staleLocks.length === 0 && (
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            py={2}
            color="text.secondary"
          >
            <CheckCircle sx={{ fontSize: 32, mb: 1, color: "success.main" }} />
            <Typography variant="body2">No conflicts detected</Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

// Simple Collaboration Metrics - MVP Feature 3
function CollaborationMetrics() {
  const { data: metrics, isLoading } = useCoordinationMetrics();
  const { data: agents } = useAgents();
  const { data: events } = useEvents();
  const theme = useTheme();

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Collaboration Metrics
          </Typography>
          <LinearProgress />
        </CardContent>
      </Card>
    );
  }

  const activeAgentsCount =
    agents?.filter((agent) => agent.status === "active").length || 0;
  const recentEventsCount =
    events?.filter((event) =>
      new Date(event.timestamp) > new Date(Date.now() - 5 * 60 * 1000)
    ).length || 0;

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Live Collaboration Metrics
        </Typography>

        <Grid container spacing={2}>
          <Grid item xs={6}>
            <Paper
              sx={{
                p: 2,
                textAlign: "center",
                bgcolor: alpha(theme.palette.primary.main, 0.1),
                border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
              }}
            >
              <Typography variant="h4" color="primary.main" fontWeight="bold">
                {activeAgentsCount}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active Collaborators
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={6}>
            <Paper
              sx={{
                p: 2,
                textAlign: "center",
                bgcolor: alpha(theme.palette.secondary.main, 0.1),
                border: `1px solid ${alpha(theme.palette.secondary.main, 0.2)}`,
              }}
            >
              <Typography variant="h4" color="secondary.main" fontWeight="bold">
                {recentEventsCount}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Recent Activities (5m)
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={6}>
            <Paper
              sx={{
                p: 2,
                textAlign: "center",
                bgcolor: alpha(theme.palette.success.main, 0.1),
                border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
              }}
            >
              <Typography variant="h4" color="success.main" fontWeight="bold">
                {Math.round((metrics?.taskDeduplicationRate || 0) * 100)}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Task Efficiency
              </Typography>
            </Paper>
          </Grid>

          <Grid item xs={6}>
            <Paper
              sx={{
                p: 2,
                textAlign: "center",
                bgcolor: alpha(theme.palette.info.main, 0.1),
                border: `1px solid ${alpha(theme.palette.info.main, 0.2)}`,
              }}
            >
              <Typography variant="h4" color="info.main" fontWeight="bold">
                {Math.round(metrics?.averageTaskCompletionTime || 0)}s
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Avg Completion Time
              </Typography>
            </Paper>
          </Grid>
        </Grid>

        <Box mt={2}>
          <Alert severity="info" variant="outlined">
            <Typography variant="body2">
              Metrics update every 10 seconds • Activity stream updates every 2
              seconds
            </Typography>
          </Alert>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function CoordinationPage() {
  const theme = useTheme();
  const [spawnDialogOpen, setSpawnDialogOpen] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Fetch data
  const { data: agents, refetch: refetchAgents } = useAgents();
  const { data: sessions } = useSessions();

  // Mock task data for demonstration
  const [mockTasks] = useState<Task[]>([
    {
      id: "1",
      description: "Research authentication patterns for distributed systems",
      status: "running",
      priority: "high",
      createdAt: new Date().toISOString(),
      progress: 45,
    },
    {
      id: "2",
      description: "Implement user interface components for agent spawning",
      status: "pending",
      priority: "normal",
      createdAt: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: "3",
      description: "Optimize database queries for session management",
      status: "completed",
      priority: "low",
      createdAt: new Date(Date.now() - 7200000).toISOString(),
    },
  ]);

  const handleSpawnAgent = (request: AgentSpawnRequest) => {
    console.log("Spawning agent:", request);
    // TODO: Implement actual agent spawning API call
    // For now, just show the request in console and trigger a refresh
    setTimeout(() => {
      refetchAgents();
    }, 1000);
  };

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
    refetchAgents();
  };

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      handleRefresh();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box
        sx={{
          mb: 4,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box>
          <Typography
            variant="h4"
            component="h1"
            gutterBottom
            sx={{ fontWeight: 700 }}
          >
            Orchestration Center
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Live coordination monitoring • Agent spawning • Task management •
            Conflict prevention
          </Typography>
        </Box>

        <Stack direction="row" spacing={2}>
          <Tooltip title="Refresh data">
            <IconButton onClick={handleRefresh} color="primary">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setSpawnDialogOpen(true)}
            sx={{ fontWeight: 600 }}
          >
            Spawn Agent
          </Button>
        </Stack>
      </Box>

      {/* Orchestration Status */}
      <Box sx={{ mb: 4 }}>
        <OrchestrationStatus />
      </Box>

      {/* Live Coordination Monitor MVP */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
          Live Coordination Monitor
        </Typography>

        <Grid container spacing={3}>
          {/* Agent Activity Stream - MVP Feature 1 */}
          <Grid item xs={12} lg={6}>
            <AgentActivityStream />
          </Grid>

          {/* Conflict Alerts & Collaboration Metrics - MVP Features 2 & 3 */}
          <Grid item xs={12} lg={6}>
            <Stack spacing={3}>
              <ConflictAlerts />
              <CollaborationMetrics />
            </Stack>
          </Grid>
        </Grid>
      </Box>

      {/* Main Content Grid */}
      <Grid container spacing={3}>
        {/* Task Management */}
        <Grid item xs={12} lg={6}>
          <TaskList tasks={mockTasks} />
        </Grid>

        {/* Active Agents */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Active Agents ({agents?.length || 0})
              </Typography>

              {!agents || agents.length === 0
                ? (
                  <Box
                    display="flex"
                    flexDirection="column"
                    alignItems="center"
                    justifyContent="center"
                    py={4}
                    color="text.secondary"
                  >
                    <AgentIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
                    <Typography variant="body1">No agents active</Typography>
                    <Typography variant="body2">
                      Click "Spawn Agent" to start coordinating
                    </Typography>
                  </Box>
                )
                : (
                  <List>
                    {agents.map((agent, index) => (
                      <Box key={agent.id}>
                        <ListItem>
                          <ListItemIcon>
                            <AgentIcon color="primary" />
                          </ListItemIcon>
                          <ListItemText
                            primary={`${agent.role}+${agent.domain}`}
                            secondary={agent.currentTask || "Idle"}
                          />
                          <ListItemSecondaryAction>
                            <StatusCell
                              status={agent.status}
                              color={agent.status === "active"
                                ? "success"
                                : agent.status === "error"
                                ? "error"
                                : "default"}
                            />
                          </ListItemSecondaryAction>
                        </ListItem>
                        {index < agents.length - 1 && <Divider />}
                      </Box>
                    ))}
                  </List>
                )}
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Actions */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>

              <Stack direction="row" spacing={2} flexWrap="wrap">
                <Button
                  variant="outlined"
                  startIcon={<CoordinationIcon />}
                  onClick={() => console.log("Start coordination flow")}
                >
                  Start Coordination Flow
                </Button>

                <Button
                  variant="outlined"
                  startIcon={<PauseIcon />}
                  onClick={() => console.log("Pause all tasks")}
                >
                  Pause All Tasks
                </Button>

                <Button
                  variant="outlined"
                  startIcon={<StopIcon />}
                  color="error"
                  onClick={() => console.log("Stop all agents")}
                >
                  Emergency Stop
                </Button>

                <Button
                  variant="outlined"
                  startIcon={<MetricsIcon />}
                  onClick={() => console.log("View detailed metrics")}
                >
                  View Metrics
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Agent Spawn Dialog */}
      <AgentSpawnForm
        open={spawnDialogOpen}
        onClose={() => setSpawnDialogOpen(false)}
        onSubmit={handleSpawnAgent}
      />
    </Box>
  );
}
