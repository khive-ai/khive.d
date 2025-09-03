/**
 * Agents Page - Detailed Agent Management Interface
 * Provides comprehensive agent monitoring, configuration, and management
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
  Grid,
  IconButton,
  LinearProgress,
  Menu,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  MoreVert as MoreIcon,
  Pause as PauseIcon,
  PlayArrow as StartIcon,
  Psychology as AgentIcon,
  Refresh as RefreshIcon,
  Speed as PerformanceIcon,
  Stop as StopIcon,
  Timeline as HistoryIcon,
  Visibility as ViewIcon,
} from "@mui/icons-material";

import { useAgent, useAgents, useDomains, useRoles } from "@/lib/api/hooks";
import { DataTable } from "@/components/ui/table";
import { StatusCell } from "@/components/ui/table";
import type { ColumnDef } from "@/components/ui/table";
import type { Agent } from "@/lib/types";
import { FormBuilder, FormSection } from "@/components/ui/form-builder";

// Agent composition form data structure
interface AgentCompositionForm {
  role: string;
  domain: string;
  taskDescription: string;
  maxConcurrentTasks: number;
  timeout: number;
}

// Extended agent interface for the detailed view
interface ExtendedAgent extends Agent {
  performance?: {
    tasksCompleted: number;
    averageTaskTime: number;
    successRate: number;
    lastActivity: string;
  };
  configuration?: {
    maxConcurrentTasks: number;
    timeout: number;
    retryCount: number;
  };
}

// Agent details dialog component
function AgentDetailsDialog({
  agent,
  open,
  onClose,
}: {
  agent: ExtendedAgent | null;
  open: boolean;
  onClose: () => void;
}) {
  const theme = useTheme();

  if (!agent) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <AgentIcon color="primary" />
          <Typography variant="h6">{agent.role}+{agent.domain}</Typography>
          <StatusCell
            status={agent.status}
            color={agent.status === "active"
              ? "success"
              : agent.status === "error"
              ? "error"
              : "default"}
          />
        </Box>
      </DialogTitle>
      <DialogContent>
        <Grid container spacing={3} sx={{ mt: 1 }}>
          {/* Basic Information */}
          <Grid item xs={12}>
            <Typography variant="h6" gutterBottom>Basic Information</Typography>
            <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.grey[50], 0.5) }}>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Agent ID
                  </Typography>
                  <Typography variant="body1" fontFamily="monospace">
                    {agent.id}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Session ID
                  </Typography>
                  <Typography variant="body1" fontFamily="monospace">
                    {agent.sessionId}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Current Task
                  </Typography>
                  <Typography variant="body1">
                    {agent.currentTask || "No active task"}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Duration
                  </Typography>
                  <Typography variant="body1">
                    {agent.duration ? `${agent.duration}s` : "N/A"}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* Performance Metrics */}
          {agent.performance && (
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Performance Metrics
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Paper
                    sx={{
                      p: 2,
                      textAlign: "center",
                      bgcolor: alpha(theme.palette.success.main, 0.1),
                    }}
                  >
                    <Typography
                      variant="h4"
                      color="success.main"
                      fontWeight="bold"
                    >
                      {agent.performance.tasksCompleted}
                    </Typography>
                    <Typography variant="caption">Tasks Completed</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Paper
                    sx={{
                      p: 2,
                      textAlign: "center",
                      bgcolor: alpha(theme.palette.primary.main, 0.1),
                    }}
                  >
                    <Typography
                      variant="h4"
                      color="primary.main"
                      fontWeight="bold"
                    >
                      {agent.performance.averageTaskTime}s
                    </Typography>
                    <Typography variant="caption">Avg Task Time</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Paper
                    sx={{
                      p: 2,
                      textAlign: "center",
                      bgcolor: alpha(theme.palette.warning.main, 0.1),
                    }}
                  >
                    <Typography
                      variant="h4"
                      color="warning.main"
                      fontWeight="bold"
                    >
                      {(agent.performance.successRate * 100).toFixed(1)}%
                    </Typography>
                    <Typography variant="caption">Success Rate</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Paper
                    sx={{
                      p: 2,
                      textAlign: "center",
                      bgcolor: alpha(theme.palette.secondary.main, 0.1),
                    }}
                  >
                    <Typography
                      variant="body2"
                      color="secondary.main"
                      fontWeight="bold"
                    >
                      {agent.performance.lastActivity}
                    </Typography>
                    <Typography variant="caption">Last Activity</Typography>
                  </Paper>
                </Grid>
              </Grid>
            </Grid>
          )}

          {/* Configuration */}
          {agent.configuration && (
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Configuration</Typography>
              <Paper sx={{ p: 2, bgcolor: alpha(theme.palette.grey[50], 0.5) }}>
                <Grid container spacing={2}>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="text.secondary">
                      Max Concurrent Tasks
                    </Typography>
                    <Typography variant="body1">
                      {agent.configuration.maxConcurrentTasks}
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="text.secondary">
                      Timeout (seconds)
                    </Typography>
                    <Typography variant="body1">
                      {agent.configuration.timeout}
                    </Typography>
                  </Grid>
                  <Grid item xs={4}>
                    <Typography variant="body2" color="text.secondary">
                      Retry Count
                    </Typography>
                    <Typography variant="body1">
                      {agent.configuration.retryCount}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>
            </Grid>
          )}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button variant="contained" startIcon={<EditIcon />}>
          Configure
        </Button>
      </DialogActions>
    </Dialog>
  );
}

// Agent actions menu component
function AgentActionsMenu({
  agent,
  anchorEl,
  open,
  onClose,
  onAction,
}: {
  agent: ExtendedAgent;
  anchorEl: HTMLElement | null;
  open: boolean;
  onClose: () => void;
  onAction: (action: string, agent: ExtendedAgent) => void;
}) {
  const handleAction = (action: string) => {
    onAction(action, agent);
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
      <MenuItem onClick={() => handleAction("performance")}>
        <PerformanceIcon sx={{ mr: 1 }} />
        Performance
      </MenuItem>
      <MenuItem onClick={() => handleAction("history")}>
        <HistoryIcon sx={{ mr: 1 }} />
        Task History
      </MenuItem>
      <MenuItem onClick={() => handleAction("configure")}>
        <EditIcon sx={{ mr: 1 }} />
        Configure
      </MenuItem>
      {agent.status === "active"
        ? (
          <MenuItem onClick={() => handleAction("pause")}>
            <PauseIcon sx={{ mr: 1 }} />
            Pause
          </MenuItem>
        )
        : (
          <MenuItem onClick={() => handleAction("start")}>
            <StartIcon sx={{ mr: 1 }} />
            Start
          </MenuItem>
        )}
      <MenuItem
        onClick={() => handleAction("stop")}
        sx={{ color: "error.main" }}
      >
        <StopIcon sx={{ mr: 1 }} />
        Stop
      </MenuItem>
      <MenuItem
        onClick={() => handleAction("delete")}
        sx={{ color: "error.main" }}
      >
        <DeleteIcon sx={{ mr: 1 }} />
        Delete
      </MenuItem>
    </Menu>
  );
}

// Helper function to create form sections for agent composer
function getComposerFormSections(
  roles: any[] | undefined,
  domains: any[] | undefined,
): FormSection[] {
  return [
    {
      title: "Agent Composition",
      description: "Define the role and domain expertise for your agent",
      fields: [
        {
          name: "role",
          label: "Role",
          type: "select",
          placeholder: "Select agent role...",
          required: true,
          helperText:
            "The behavioral archetype that defines how the agent operates",
          options: (roles || []).map((role) => ({
            label: `${role.name} - ${role.description}`,
            value: role.name,
          })),
          grid: { xs: 12, md: 6 },
          validation: {
            required: "Please select a role",
          },
        },
        {
          name: "domain",
          label: "Domain",
          type: "select",
          placeholder: "Select domain expertise...",
          required: true,
          helperText: "The specialized knowledge area the agent will master",
          options: (domains || []).map((domain) => ({
            label: `${domain.name} - ${domain.description}`,
            value: domain.name,
          })),
          grid: { xs: 12, md: 6 },
          validation: {
            required: "Please select a domain",
          },
        },
        {
          name: "taskDescription",
          label: "Task Description",
          type: "textarea",
          placeholder: "Describe the specific task context for this agent...",
          required: true,
          rows: 4,
          helperText:
            "Provide context about the specific task this agent will be assigned",
          grid: { xs: 12 },
          validation: {
            required: "Please provide a task description",
            minLength: {
              value: 20,
              message: "Task description must be at least 20 characters",
            },
          },
        },
        {
          name: "maxConcurrentTasks",
          label: "Max Concurrent Tasks",
          type: "number",
          placeholder: "3",
          helperText:
            "Maximum number of tasks the agent can handle simultaneously",
          min: 1,
          max: 10,
          grid: { xs: 12, md: 6 },
          validation: {
            required: "Please specify max concurrent tasks",
            min: {
              value: 1,
              message: "Must be at least 1",
            },
            max: {
              value: 10,
              message: "Cannot exceed 10",
            },
          },
        },
        {
          name: "timeout",
          label: "Timeout (seconds)",
          type: "number",
          placeholder: "300",
          helperText: "Maximum time allowed for task execution",
          min: 30,
          max: 3600,
          step: 30,
          grid: { xs: 12, md: 6 },
          validation: {
            required: "Please specify timeout",
            min: {
              value: 30,
              message: "Must be at least 30 seconds",
            },
            max: {
              value: 3600,
              message: "Cannot exceed 1 hour",
            },
          },
        },
      ],
    },
  ];
}

export default function AgentsPage() {
  const theme = useTheme();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<ExtendedAgent | null>(
    null,
  );
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [actionsMenuAnchor, setActionsMenuAnchor] = useState<
    HTMLElement | null
  >(null);
  const [actionsMenuAgent, setActionsMenuAgent] = useState<
    ExtendedAgent | null
  >(null);
  const [composerDialogOpen, setComposerDialogOpen] = useState(false);
  const [composerLoading, setComposerLoading] = useState(false);

  // Fetch data
  const { data: agents, isLoading, refetch } = useAgents();
  const { data: roles } = useRoles();
  const { data: domains } = useDomains();

  // Transform agents data with mock extended information
  const extendedAgents: ExtendedAgent[] = (agents || []).map((
    agent,
    index,
  ) => ({
    ...agent,
    performance: {
      tasksCompleted: Math.floor(Math.random() * 50) + 10,
      averageTaskTime: Math.floor(Math.random() * 30) + 5,
      successRate: 0.85 + Math.random() * 0.14,
      lastActivity: index % 3 === 0
        ? "just now"
        : index % 3 === 1
        ? "5m ago"
        : "15m ago",
    },
    configuration: {
      maxConcurrentTasks: 3,
      timeout: 300,
      retryCount: 3,
    },
  }));

  // Filter agents based on search term
  const filteredAgents = extendedAgents.filter((agent) =>
    agent.role.toLowerCase().includes(searchTerm.toLowerCase()) ||
    agent.domain.toLowerCase().includes(searchTerm.toLowerCase()) ||
    agent.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (agent.currentTask || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Table columns
  const columns: ColumnDef<ExtendedAgent>[] = [
    {
      accessorKey: "id",
      header: "Agent ID",
      cell: ({ row }) => (
        <Typography variant="body2" fontFamily="monospace">
          {row.original.id.substring(0, 8)}...
        </Typography>
      ),
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
            : row.original.status === "error"
            ? "error"
            : "default"}
        />
      ),
    },
    {
      accessorKey: "currentTask",
      header: "Current Task",
      cell: ({ row }) => (
        <Typography variant="body2" sx={{ maxWidth: 200 }}>
          {row.original.currentTask || "No active task"}
        </Typography>
      ),
    },
    {
      accessorKey: "performance.tasksCompleted",
      header: "Tasks",
      cell: ({ row }) => (
        <Typography variant="body2">
          {row.original.performance?.tasksCompleted || 0}
        </Typography>
      ),
    },
    {
      accessorKey: "performance.lastActivity",
      header: "Last Activity",
      cell: ({ row }) => (
        <Typography variant="body2" color="text.secondary">
          {row.original.performance?.lastActivity || "Unknown"}
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
            setActionsMenuAgent(row.original);
          }}
          size="small"
        >
          <MoreIcon />
        </IconButton>
      ),
    },
  ];

  const handleAgentAction = (action: string, agent: ExtendedAgent) => {
    switch (action) {
      case "view":
        setSelectedAgent(agent);
        setDetailsDialogOpen(true);
        break;
      case "start":
        console.log("Starting agent:", agent.id);
        break;
      case "pause":
        console.log("Pausing agent:", agent.id);
        break;
      case "stop":
        console.log("Stopping agent:", agent.id);
        break;
      case "delete":
        console.log("Deleting agent:", agent.id);
        break;
      case "configure":
        console.log("Configuring agent:", agent.id);
        break;
      case "performance":
        console.log("Viewing performance for agent:", agent.id);
        break;
      case "history":
        console.log("Viewing history for agent:", agent.id);
        break;
      default:
        console.log("Unknown action:", action);
    }
  };

  // Handle agent composition form submission
  const handleAgentComposition = async (data: AgentCompositionForm) => {
    setComposerLoading(true);
    try {
      console.log("Composing agent with:", data);

      // In a real implementation, this would call the khive compose API
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Close dialog and show success
      setComposerDialogOpen(false);
      alert(
        `Agent composed successfully!\n\nComposition: ${data.role}+${data.domain}\nTask: ${data.taskDescription}`,
      );

      // Refresh agents list to show the new agent
      refetch();
    } catch (error) {
      console.error("Failed to compose agent:", error);
      alert("Failed to compose agent. Please try again.");
    } finally {
      setComposerLoading(false);
    }
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
            Agent Management
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Monitor and manage all agents in the orchestration system
          </Typography>
        </Box>

        <Stack direction="row" spacing={2}>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setComposerDialogOpen(true)}
            sx={{ fontWeight: 600 }}
          >
            Compose Agent
          </Button>
          <Tooltip title="Refresh data">
            <IconButton onClick={() => refetch()} color="primary">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
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
                    {extendedAgents.filter((a) => a.status === "active").length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Agents
                  </Typography>
                </Box>
                <AgentIcon
                  sx={{
                    fontSize: 40,
                    color: alpha(theme.palette.success.main, 0.5),
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
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
                    {extendedAgents.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Agents
                  </Typography>
                </Box>
                <AgentIcon
                  sx={{
                    fontSize: 40,
                    color: alpha(theme.palette.primary.main, 0.5),
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
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
                    {roles?.length || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Available Roles
                  </Typography>
                </Box>
                <AgentIcon
                  sx={{
                    fontSize: 40,
                    color: alpha(theme.palette.warning.main, 0.5),
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
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
                    color="secondary.main"
                    fontWeight="bold"
                  >
                    {domains?.length || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Available Domains
                  </Typography>
                </Box>
                <AgentIcon
                  sx={{
                    fontSize: 40,
                    color: alpha(theme.palette.secondary.main, 0.5),
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Search and Filters */}
      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          placeholder="Search agents by ID, role, domain, or current task..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          variant="outlined"
          sx={{ maxWidth: 500 }}
        />
      </Box>

      {/* Agents Table */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          <DataTable
            data={filteredAgents}
            columns={columns}
            loading={isLoading}
            searchable={false} // We're handling search manually above
            emptyStateMessage="No agents found"
            emptyStateDescription="Agents will appear here when they are spawned"
            pageSize={10}
          />
        </CardContent>
      </Card>

      {/* Agent Details Dialog */}
      <AgentDetailsDialog
        agent={selectedAgent}
        open={detailsDialogOpen}
        onClose={() => {
          setDetailsDialogOpen(false);
          setSelectedAgent(null);
        }}
      />

      {/* Agent Actions Menu */}
      <AgentActionsMenu
        agent={actionsMenuAgent!}
        anchorEl={actionsMenuAnchor}
        open={Boolean(actionsMenuAnchor)}
        onClose={() => {
          setActionsMenuAnchor(null);
          setActionsMenuAgent(null);
        }}
        onAction={handleAgentAction}
      />

      {/* Agent Composer Dialog */}
      <Dialog
        open={composerDialogOpen}
        onClose={() => setComposerDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <AddIcon color="primary" />
            <Typography variant="h6">Compose New Agent</Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <FormBuilder
              sections={getComposerFormSections(roles, domains)}
              onSubmit={handleAgentComposition}
              loading={composerLoading}
              submitText="Compose Agent"
              showReset={true}
              mode="onChange"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setComposerDialogOpen(false)}>
            Cancel
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
