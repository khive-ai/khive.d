/**
 * Sessions Page - Session Management Interface
 * Provides session monitoring, creation, and management capabilities
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
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  LinearProgress,
  Menu,
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
  Assessment as MetricsIcon,
  CheckCircle as CompletedIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Error as ErrorIcon,
  HourglassEmpty as PendingIcon,
  MoreVert as MoreIcon,
  Pause as PauseIcon,
  PlayArrow as StartIcon,
  Refresh as RefreshIcon,
  Stop as StopIcon,
  Timeline as TimelineIcon,
  Visibility as ViewIcon,
} from "@mui/icons-material";

import {
  useCoordinationMetrics,
  useCreateSession,
  useSessions,
} from "@/lib/api/hooks";
import { DataTable } from "@/components/ui/table";
import { StatusCell } from "@/components/ui/table";
import type { ColumnDef } from "@/components/ui/table";
import type { Session } from "@/lib/types";

// Extended session interface for detailed view
interface ExtendedSession extends Session {
  agents: Array<{
    id: string;
    role: string;
    domain: string;
    status: string;
  }>;
  coordinator: string;
  duration: string;
  progress: number;
  performance?: {
    tasksCompleted: number;
    averageTaskTime: number;
    conflictsPrevented: number;
  };
}

// Session creation form component
function SessionCreationForm({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (sessionData: any) => void;
}) {
  const [formData, setFormData] = useState({
    objective: "",
    context: "",
    coordinationStrategy: "fan_out_synthesize",
    qualityGate: "thorough",
    maxAgents: 5,
  });

  const handleSubmit = () => {
    if (formData.objective && formData.context) {
      onSubmit(formData);
      setFormData({
        objective: "",
        context: "",
        coordinationStrategy: "fan_out_synthesize",
        qualityGate: "thorough",
        maxAgents: 5,
      });
      onClose();
    }
  };

  const isFormValid = formData.objective && formData.context;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <AddIcon color="primary" />
          <Typography variant="h6">Create New Session</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={3} sx={{ mt: 1 }}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Session Objective"
              value={formData.objective}
              onChange={(e) =>
                setFormData({ ...formData, objective: e.target.value })}
              placeholder="Describe the main goal of this orchestration session..."
              multiline
              rows={2}
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Context & Requirements"
              value={formData.context}
              onChange={(e) =>
                setFormData({ ...formData, context: e.target.value })}
              placeholder="Provide additional context, constraints, or requirements..."
              multiline
              rows={3}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Coordination Strategy</InputLabel>
              <Select
                value={formData.coordinationStrategy}
                label="Coordination Strategy"
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    coordinationStrategy: e.target.value,
                  })}
              >
                <MenuItem value="fan_out_synthesize">
                  Fan-out & Synthesize
                </MenuItem>
                <MenuItem value="parallel_discovery">
                  Parallel Discovery
                </MenuItem>
                <MenuItem value="hierarchical_delegation">
                  Hierarchical Delegation
                </MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Quality Gate</InputLabel>
              <Select
                value={formData.qualityGate}
                label="Quality Gate"
                onChange={(e) =>
                  setFormData({ ...formData, qualityGate: e.target.value })}
              >
                <MenuItem value="basic">Basic</MenuItem>
                <MenuItem value="thorough">Thorough</MenuItem>
                <MenuItem value="critical">Critical</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              type="number"
              label="Max Agents"
              value={formData.maxAgents}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  maxAgents: parseInt(e.target.value) || 5,
                })}
              inputProps={{ min: 1, max: 20 }}
            />
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
          Create Session
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// Session actions menu component
function SessionActionsMenu({
  session,
  anchorEl,
  open,
  onClose,
  onAction,
}: {
  session: ExtendedSession;
  anchorEl: HTMLElement | null;
  open: boolean;
  onClose: () => void;
  onAction: (action: string, session: ExtendedSession) => void;
}) {
  const handleAction = (action: string) => {
    onAction(action, session);
    onClose();
  };

  return (
    <Menu
      anchorEl={anchorEl}
      open={open}
      onClose={onClose}
      transformOrigin={{ horizontal: "right", vertical: "top" }}
      anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
    >
      <MenuItem onClick={() => handleAction("view")}>
        <ViewIcon sx={{ mr: 1 }} />
        View Details
      </MenuItem>
      <MenuItem onClick={() => handleAction("timeline")}>
        <TimelineIcon sx={{ mr: 1 }} />
        View Timeline
      </MenuItem>
      <MenuItem onClick={() => handleAction("metrics")}>
        <MetricsIcon sx={{ mr: 1 }} />
        Performance Metrics
      </MenuItem>
      {session.status === "running"
        ? (
          <MenuItem onClick={() => handleAction("pause")}>
            <PauseIcon sx={{ mr: 1 }} />
            Pause Session
          </MenuItem>
        )
        : session.status === "pending"
        ? (
          <MenuItem onClick={() => handleAction("start")}>
            <StartIcon sx={{ mr: 1 }} />
            Start Session
          </MenuItem>
        )
        : null}
      {session.status !== "completed" && (
        <MenuItem
          onClick={() => handleAction("stop")}
          sx={{ color: "error.main" }}
        >
          <StopIcon sx={{ mr: 1 }} />
          Stop Session
        </MenuItem>
      )}
      <MenuItem onClick={() => handleAction("clone")}>
        <EditIcon sx={{ mr: 1 }} />
        Clone Session
      </MenuItem>
      <MenuItem
        onClick={() => handleAction("delete")}
        sx={{ color: "error.main" }}
      >
        <DeleteIcon sx={{ mr: 1 }} />
        Delete Session
      </MenuItem>
    </Menu>
  );
}

export default function SessionsPage() {
  const theme = useTheme();
  const [searchTerm, setSearchTerm] = useState("");
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [actionsMenuAnchor, setActionsMenuAnchor] = useState<
    HTMLElement | null
  >(null);
  const [actionsMenuSession, setActionsMenuSession] = useState<
    ExtendedSession | null
  >(null);

  // Fetch data
  const { data: sessions, isLoading, refetch } = useSessions();
  const { data: metrics } = useCoordinationMetrics();
  const createSession = useCreateSession();

  // Transform sessions data with mock extended information
  const extendedSessions: ExtendedSession[] = (sessions || []).map((
    session,
    index,
  ) => ({
    ...session,
    agents: [
      {
        id: "1",
        role: "researcher",
        domain: "memory-systems",
        status: "active",
      },
      {
        id: "2",
        role: "architect",
        domain: "distributed-systems",
        status: "active",
      },
      {
        id: "3",
        role: "implementer",
        domain: "software-architecture",
        status: "idle",
      },
    ],
    coordinator: "lion",
    duration: `${Math.floor(Math.random() * 120) + 10}m`,
    progress: Math.floor(Math.random() * 100),
    performance: {
      tasksCompleted: Math.floor(Math.random() * 20) + 5,
      averageTaskTime: Math.floor(Math.random() * 60) + 15,
      conflictsPrevented: Math.floor(Math.random() * 5),
    },
  }));

  // Filter sessions based on search term
  const filteredSessions = extendedSessions.filter((session) =>
    session.objective.toLowerCase().includes(searchTerm.toLowerCase()) ||
    session.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    session.coordinator.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Table columns
  const columns: ColumnDef<ExtendedSession>[] = [
    {
      accessorKey: "id",
      header: "Session ID",
      cell: ({ row }) => (
        <Typography variant="body2" fontFamily="monospace">
          {row.original.id.substring(0, 8)}...
        </Typography>
      ),
    },
    {
      accessorKey: "objective",
      header: "Objective",
      cell: ({ row }) => (
        <Typography variant="body2" sx={{ maxWidth: 300 }}>
          {row.original.objective}
        </Typography>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
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
      ),
    },
    {
      accessorKey: "coordinator",
      header: "Coordinator",
      cell: ({ row }) => (
        <Chip
          label={row.original.coordinator}
          size="small"
          color="primary"
          variant="outlined"
        />
      ),
    },
    {
      accessorKey: "agents",
      header: "Agents",
      cell: ({ row }) => (
        <Typography variant="body2">
          {row.original.agents.length}
        </Typography>
      ),
    },
    {
      accessorKey: "progress",
      header: "Progress",
      cell: ({ row }) => (
        <Box
          sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 120 }}
        >
          <LinearProgress
            variant="determinate"
            value={row.original.progress}
            sx={{ flex: 1, height: 6, borderRadius: 3 }}
          />
          <Typography variant="caption" color="text.secondary">
            {row.original.progress}%
          </Typography>
        </Box>
      ),
    },
    {
      accessorKey: "duration",
      header: "Duration",
      cell: ({ row }) => (
        <Typography variant="body2">
          {row.original.duration}
        </Typography>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <IconButton
          onClick={(e) => {
            setActionsMenuAnchor(e.currentTarget);
            setActionsMenuSession(row.original);
          }}
          size="small"
        >
          <MoreIcon />
        </IconButton>
      ),
    },
  ];

  const handleCreateSession = (sessionData: any) => {
    createSession.mutate(sessionData, {
      onSuccess: () => {
        refetch();
      },
    });
  };

  const handleSessionAction = (action: string, session: ExtendedSession) => {
    switch (action) {
      case "view":
        console.log("Viewing session details:", session.id);
        break;
      case "timeline":
        console.log("Viewing timeline for session:", session.id);
        break;
      case "metrics":
        console.log("Viewing metrics for session:", session.id);
        break;
      case "start":
        console.log("Starting session:", session.id);
        break;
      case "pause":
        console.log("Pausing session:", session.id);
        break;
      case "stop":
        console.log("Stopping session:", session.id);
        break;
      case "clone":
        console.log("Cloning session:", session.id);
        break;
      case "delete":
        console.log("Deleting session:", session.id);
        break;
      default:
        console.log("Unknown action:", action);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CompletedIcon color="success" />;
      case "running":
        return <StartIcon color="primary" />;
      case "failed":
        return <ErrorIcon color="error" />;
      case "pending":
        return <PendingIcon color="warning" />;
      default:
        return <PendingIcon color="disabled" />;
    }
  };

  const getStatusCount = (status: string) => {
    return extendedSessions.filter((s) => s.status === status).length;
  };

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
    }, 30000);

    return () => clearInterval(interval);
  }, [refetch]);

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
            Session Management
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Monitor and manage orchestration sessions and their coordination
            activities
          </Typography>
        </Box>

        <Stack direction="row" spacing={2}>
          <Tooltip title="Refresh data">
            <IconButton onClick={() => refetch()} color="primary">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setCreateDialogOpen(true)}
            sx={{ fontWeight: 600 }}
          >
            New Session
          </Button>
        </Stack>
      </Box>

      {/* Status Overview Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={6} sm={3}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
              >
                <Box>
                  <Typography
                    variant="h4"
                    color="primary.main"
                    fontWeight="bold"
                  >
                    {getStatusCount("running")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Running
                  </Typography>
                </Box>
                {getStatusIcon("running")}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6} sm={3}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
              >
                <Box>
                  <Typography
                    variant="h4"
                    color="success.main"
                    fontWeight="bold"
                  >
                    {getStatusCount("completed")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Completed
                  </Typography>
                </Box>
                {getStatusIcon("completed")}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6} sm={3}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
              >
                <Box>
                  <Typography
                    variant="h4"
                    color="warning.main"
                    fontWeight="bold"
                  >
                    {getStatusCount("pending")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Pending
                  </Typography>
                </Box>
                {getStatusIcon("pending")}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={6} sm={3}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
              >
                <Box>
                  <Typography variant="h4" color="error.main" fontWeight="bold">
                    {getStatusCount("failed")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Failed
                  </Typography>
                </Box>
                {getStatusIcon("failed")}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Search */}
      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          placeholder="Search sessions by ID, objective, or coordinator..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          variant="outlined"
          sx={{ maxWidth: 500 }}
        />
      </Box>

      {/* Sessions Table */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          <DataTable
            data={filteredSessions}
            columns={columns}
            loading={isLoading}
            searchable={false} // We're handling search manually above
            emptyStateMessage="No sessions found"
            emptyStateDescription="Create a new session to start orchestrating agents"
            pageSize={10}
          />
        </CardContent>
      </Card>

      {/* System Health Alert */}
      {metrics && (
        <Box sx={{ mt: 3 }}>
          <Alert severity="info" variant="outlined">
            <Typography variant="body2">
              System Health: {metrics.activeAgents} active agents across{" "}
              {metrics.activeSessions} sessions.
              {metrics.conflictsPrevented > 0 &&
                ` ${metrics.conflictsPrevented} conflicts prevented today.`}
            </Typography>
          </Alert>
        </Box>
      )}

      {/* Session Creation Dialog */}
      <SessionCreationForm
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSubmit={handleCreateSession}
      />

      {/* Session Actions Menu */}
      <SessionActionsMenu
        session={actionsMenuSession!}
        anchorEl={actionsMenuAnchor}
        open={Boolean(actionsMenuAnchor)}
        onClose={() => {
          setActionsMenuAnchor(null);
          setActionsMenuSession(null);
        }}
        onAction={handleSessionAction}
      />
    </Box>
  );
}
