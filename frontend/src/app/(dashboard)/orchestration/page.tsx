/**
 * Orchestration Center MVP - Agent Spawning and Task Management Interface
 * Core functionality for spawning agents, managing tasks, and orchestration status
 */

"use client";

import React, { useEffect, useState } from "react";
import {
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
  List,
  ListItem,
  ListItemIcon,
  ListItemSecondaryAction,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import {
  Add as AddIcon,
  CheckCircle as CompleteIcon,
  Close as CloseIcon,
  Error as ErrorIcon,
  PlayArrow as PlayIcon,
  Psychology as AgentIcon,
  Refresh as RefreshIcon,
  Schedule as PendingIcon,
} from "@mui/icons-material";
import { FormProvider, useForm } from "react-hook-form";
import { Form } from "@/components/ui/form";
import { DataTable } from "@/components/ui/table";
import { StatusCell } from "@/components/ui/table";
import type { ColumnDef } from "@/components/ui/table";
import { WorkflowDiagramDisplay } from "@/components/feature/workflow-diagram-display";
import {
  useAgents,
  useCoordinationMetrics,
  useCreateSession,
  useDomains,
  useRoles,
  useSessions,
} from "@/lib/api/hooks";

// Types for agent spawning
interface AgentSpawnForm {
  role: string;
  domain: string;
  taskDescription: string;
  priority: "low" | "medium" | "high" | "critical";
  coordinationStrategy:
    | "fan_out_synthesize"
    | "parallel_discovery"
    | "hierarchical_delegation";
  qualityGate: "basic" | "thorough" | "critical";
  maxAgents: number;
}

// Types for task display
interface Task {
  id: string;
  agentId: string;
  description: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  priority: string;
  progress: number;
  startTime?: string;
  estimatedCompletion?: string;
  artifacts: string[];
}

// Types for orchestration status (currently using session data directly)

export default function OrchestrationCenterPage() {
  // Form state
  const form = useForm<AgentSpawnForm>({
    defaultValues: {
      role: "researcher",
      domain: "general",
      taskDescription: "",
      priority: "medium",
      coordinationStrategy: "fan_out_synthesize",
      qualityGate: "thorough",
      maxAgents: 5,
    },
  });

  // UI state
  const [spawnDialogOpen, setSpawnDialogOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // API hooks
  const { data: roles } = useRoles();
  const { data: domains } = useDomains();
  const { data: sessions, refetch: refetchSessions } = useSessions();
  const { data: agents } = useAgents();
  const { data: metrics } = useCoordinationMetrics();
  const { mutate: createSession, isLoading: isCreatingSession } =
    useCreateSession();

  // Mock data for tasks (replace with real API)
  const [tasks] = useState<Task[]>([
    {
      id: "task-1",
      agentId: "researcher-001",
      description: "Analyze market trends for Q4",
      status: "in_progress",
      priority: "high",
      progress: 65,
      startTime: new Date().toISOString(),
      estimatedCompletion: "15 min",
      artifacts: ["market_analysis.md", "trend_data.json"],
    },
    {
      id: "task-2",
      agentId: "analyst-001",
      description: "Review code architecture patterns",
      status: "completed",
      priority: "medium",
      progress: 100,
      startTime: new Date(Date.now() - 1800000).toISOString(),
      artifacts: ["architecture_review.md", "patterns_summary.md"],
    },
    {
      id: "task-3",
      agentId: "implementer-001",
      description: "Update API endpoints documentation",
      status: "pending",
      priority: "low",
      progress: 0,
      artifacts: [],
    },
  ]);

  // Auto-refresh functionality
  useEffect(() => {
    const interval = setInterval(() => {
      if (!refreshing) {
        setRefreshing(true);
        refetchSessions().finally(() => setRefreshing(false));
      }
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [refetchSessions, refreshing]);

  // Handle agent spawn form submission
  const onSpawnAgent = (data: AgentSpawnForm) => {
    const sessionData = {
      name: `${data.role} - ${data.taskDescription.substring(0, 50)}...`,
      coordinator: "lion",
      agents: [
        {
          role: data.role,
          domain: data.domain,
          task: data.taskDescription,
          priority: data.priority,
        },
      ],
      coordinationStrategy: data.coordinationStrategy,
      qualityGate: data.qualityGate,
      maxAgents: data.maxAgents,
    };

    createSession(sessionData, {
      onSuccess: () => {
        setSpawnDialogOpen(false);
        form.reset();
      },
    });
  };

  // Table columns for tasks
  const taskColumns: ColumnDef<Task>[] = [
    {
      accessorKey: "description",
      header: "Task Description",
      cell: ({ row }) => (
        <Box>
          <Typography variant="body2" fontWeight={500}>
            {row.original.description}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Agent: {row.original.agentId}
          </Typography>
        </Box>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => (
        <StatusCell
          status={row.original.status}
          color={row.original.status === "completed"
            ? "success"
            : row.original.status === "in_progress"
            ? "warning"
            : row.original.status === "failed"
            ? "error"
            : "default"}
        />
      ),
    },
    {
      accessorKey: "priority",
      header: "Priority",
      cell: ({ row }) => (
        <Chip
          label={row.original.priority}
          size="small"
          color={row.original.priority === "critical"
            ? "error"
            : row.original.priority === "high"
            ? "warning"
            : row.original.priority === "medium"
            ? "primary"
            : "default"}
        />
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
      accessorKey: "estimatedCompletion",
      header: "ETA",
      cell: ({ row }) => (
        <Typography variant="body2" color="text.secondary">
          {row.original.estimatedCompletion || "N/A"}
        </Typography>
      ),
    },
    {
      accessorKey: "artifacts",
      header: "Artifacts",
      cell: ({ row }) => (
        <Typography variant="body2">
          {row.original.artifacts.length} files
        </Typography>
      ),
    },
  ];

  // Calculate orchestration stats
  const activeOrchestrations =
    sessions?.filter((s) => s.status === "running").length || 0;
  const totalAgents = agents?.length || 0;
  const activeTasks = tasks.filter((t) => t.status === "in_progress").length;
  const completedTasks = tasks.filter((t) => t.status === "completed").length;

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
            Spawn agents, manage tasks, and monitor orchestration status
          </Typography>
        </Box>
        <Stack direction="row" spacing={2}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => refetchSessions()}
            disabled={refreshing}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setSpawnDialogOpen(true)}
          >
            Spawn Agent
          </Button>
        </Stack>
      </Box>

      {/* Quick Status Indicators */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" color="primary" sx={{ fontWeight: 700 }}>
                {activeOrchestrations}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active Orchestrations
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography
                variant="h4"
                color="secondary"
                sx={{ fontWeight: 700 }}
              >
                {totalAgents}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Available Agents
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography
                variant="h4"
                color="warning.main"
                sx={{ fontWeight: 700 }}
              >
                {activeTasks}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active Tasks
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography
                variant="h4"
                color="success.main"
                sx={{ fontWeight: 700 }}
              >
                {completedTasks}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Completed Today
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Task Flow Visualizer MVP */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12}>
          <WorkflowDiagramDisplay
            session={sessions?.[0]}
            agents={agents || []}
            coordinationStrategy="fan_out_synthesize" // Default strategy for MVP
            recentEvents={[]} // TODO: Connect to real events when available
            onNodeClick={(agent) => {
              console.log("Agent clicked:", agent);
              // TODO: Show agent details or navigate to agent page
            }}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Task Management */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 2,
                }}
              >
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Active Tasks
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Chip
                    label={`${activeTasks} active`}
                    size="small"
                    color="warning"
                  />
                  <Chip
                    label={`${completedTasks} completed`}
                    size="small"
                    color="success"
                  />
                </Stack>
              </Box>
              <DataTable
                data={tasks}
                columns={taskColumns}
                searchable
                searchPlaceholder="Search tasks..."
                emptyStateMessage="No tasks running"
                emptyStateDescription="Spawn agents to see tasks appear here"
                pageSize={10}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Orchestration Status */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Active Orchestrations
              </Typography>
              {sessions && sessions.length > 0
                ? (
                  <List dense>
                    {sessions.slice(0, 5).map((session) => (
                      <ListItem key={session.id} sx={{ px: 0 }}>
                        <ListItemIcon>
                          {session.status === "running"
                            ? <PlayIcon color="success" />
                            : session.status === "completed"
                            ? <CompleteIcon color="primary" />
                            : session.status === "failed"
                            ? <ErrorIcon color="error" />
                            : <PendingIcon color="warning" />}
                        </ListItemIcon>
                        <ListItemText
                          primary={session.name || "Unnamed Session"}
                          secondary={`${session.agents?.length || 0} agents • ${
                            session.coordinator || "lion"
                          }`}
                        />
                        <ListItemSecondaryAction>
                          <Typography variant="caption" color="text.secondary">
                            {session.duration || "0m"}
                          </Typography>
                        </ListItemSecondaryAction>
                      </ListItem>
                    ))}
                  </List>
                )
                : (
                  <Box sx={{ textAlign: "center", py: 3 }}>
                    <Typography variant="body2" color="text.secondary">
                      No active orchestrations
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Spawn agents to begin
                    </Typography>
                  </Box>
                )}
            </CardContent>
          </Card>

          {/* System Metrics */}
          <Card sx={{ mt: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                System Metrics
              </Typography>
              <Stack spacing={2}>
                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Conflicts Prevented</Typography>
                  <Typography variant="body2" color="primary" fontWeight={500}>
                    {metrics?.conflictsPrevented || 0}
                  </Typography>
                </Box>
                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Avg Task Time</Typography>
                  <Typography variant="body2" color="primary" fontWeight={500}>
                    {(metrics?.averageTaskCompletionTime || 0).toFixed(1)}s
                  </Typography>
                </Box>
                <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                  <Typography variant="body2">Success Rate</Typography>
                  <Typography
                    variant="body2"
                    color="success.main"
                    fontWeight={500}
                  >
                    {((completedTasks /
                          (completedTasks +
                            tasks.filter((t) => t.status === "failed")
                              .length)) * 100 || 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Agent Spawn Dialog */}
      <Dialog
        open={spawnDialogOpen}
        onClose={() => setSpawnDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            Spawn New Agent
            <IconButton onClick={() => setSpawnDialogOpen(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <FormProvider {...form}>
          <form onSubmit={form.handleSubmit(onSpawnAgent)}>
            <DialogContent>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <Form.SelectField
                    name="role"
                    label="Agent Role"
                    required
                    options={(roles || []).map((role) => ({
                      value: role.name,
                      label: role.display_name || role.name,
                    }))}
                    helperText="The behavioral archetype for the agent"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Form.SelectField
                    name="domain"
                    label="Domain"
                    required
                    options={(domains || []).map((domain) => ({
                      value: domain.name,
                      label: domain.display_name || domain.name,
                    }))}
                    helperText="Specialized knowledge area"
                  />
                </Grid>
                <Grid item xs={12}>
                  <Form.TextField
                    name="taskDescription"
                    label="Task Description"
                    required
                    multiline
                    rows={3}
                    placeholder="Describe the task you want the agent to perform..."
                    helperText="Clear, specific description of what needs to be done"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Form.SelectField
                    name="priority"
                    label="Priority"
                    options={[
                      { value: "low", label: "Low" },
                      { value: "medium", label: "Medium" },
                      { value: "high", label: "High" },
                      { value: "critical", label: "Critical" },
                    ]}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Form.TextField
                    name="maxAgents"
                    label="Max Agents"
                    type="number"
                    helperText="Maximum number of agents for this orchestration"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Form.SelectField
                    name="coordinationStrategy"
                    label="Coordination Strategy"
                    options={[
                      {
                        value: "fan_out_synthesize",
                        label: "Fan-out & Synthesize",
                      },
                      {
                        value: "parallel_discovery",
                        label: "Parallel Discovery",
                      },
                      {
                        value: "hierarchical_delegation",
                        label: "Hierarchical Delegation",
                      },
                    ]}
                    helperText="How agents will coordinate their work"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Form.SelectField
                    name="qualityGate"
                    label="Quality Gate"
                    options={[
                      { value: "basic", label: "Basic" },
                      { value: "thorough", label: "Thorough" },
                      { value: "critical", label: "Critical" },
                    ]}
                    helperText="Level of quality validation required"
                  />
                </Grid>
              </Grid>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 3 }}>
              <Button onClick={() => setSpawnDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={isCreatingSession}
                startIcon={<AgentIcon />}
              >
                {isCreatingSession ? "Spawning..." : "Spawn Agent"}
              </Button>
            </DialogActions>
          </form>
        </FormProvider>
      </Dialog>
    </Box>
  );
}
