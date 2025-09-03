/**
 * Task Flow Visualizer MVP
 * Interactive workflow diagrams for multi-agent tasks with agent activity highlighting
 */

"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  alpha,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputLabel,
  Menu,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  AccountTree as FlowIcon,
  CenterFocusStrong as CenterIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  FilterList as FilterIcon,
  Pause as PauseIcon,
  PlayArrow as PlayIcon,
  Psychology as AgentIcon,
  Refresh as RefreshIcon,
  Schedule as PendingIcon,
  Timeline as TimelineIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
} from "@mui/icons-material";

import {
  useAgents,
  useCoordinationMetrics,
  useEvents,
  useInvalidateQueries,
  useSessions,
} from "@/lib/api/hooks";
import type { Agent, HookEvent, Session } from "@/lib/types";

// Flow diagram types
interface FlowNode {
  id: string;
  type: "agent" | "task" | "decision";
  position: { x: number; y: number };
  data: {
    label: string;
    role?: string;
    domain?: string;
    status: "active" | "idle" | "completed" | "error";
    progress?: number;
    agentId?: string;
    taskDescription?: string;
  };
}

interface FlowEdge {
  id: string;
  source: string;
  target: string;
  type: "task_flow" | "data_flow" | "coordination";
  animated?: boolean;
  status: "active" | "completed" | "pending";
}

interface WorkflowDiagram {
  id: string;
  name: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  coordinationStrategy: string;
  status: "running" | "paused" | "completed" | "error";
}

export default function TaskFlowVisualizerPage() {
  const theme = useTheme();
  const [isRealTime, setIsRealTime] = useState(true);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>("");
  const [zoomLevel, setZoomLevel] = useState(1);
  const [autoCenter, setAutoCenter] = useState(true);
  const [filterMenuAnchor, setFilterMenuAnchor] = useState<null | HTMLElement>(
    null,
  );
  const [activityFilter, setActivityFilter] = useState<string>("all");
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());

  const { invalidateAll } = useInvalidateQueries();

  // API data
  const { data: events, refetch: refetchEvents } = useEvents(undefined, {
    refetchInterval: isRealTime ? 3000 : false,
    onSuccess: () => setLastUpdateTime(new Date()),
  });

  const { data: agents, refetch: refetchAgents } = useAgents({
    refetchInterval: isRealTime ? 5000 : false,
  });

  const { data: sessions } = useSessions({
    refetchInterval: isRealTime ? 10000 : false,
  });

  const { data: metrics } = useCoordinationMetrics({
    refetchInterval: isRealTime ? 10000 : false,
  });

  // Generate workflow diagrams from session and agent data
  const workflowDiagrams = useMemo((): WorkflowDiagram[] => {
    if (!sessions || !agents || !events) return [];

    return sessions
      .filter((session) =>
        session.status === "running" || session.status === "completed"
      )
      .map((session, sessionIndex): WorkflowDiagram => {
        const sessionAgents = agents.filter((agent) =>
          session.agents?.some((sa) => sa.role === agent.role)
        );

        // Create nodes for each agent
        const nodes: FlowNode[] = sessionAgents.map((agent, index) => {
          const recentEvents = events
            .filter((event) => event.agentId === agent.id)
            .slice(0, 5);

          const isActive = recentEvents.some((event) =>
            new Date(event.timestamp).getTime() > Date.now() - 60000
          );

          const hasErrors = recentEvents.some((event) =>
            event.eventType.includes("error") ||
            event.eventType.includes("fail")
          );

          let status: FlowNode["data"]["status"] = "idle";
          if (hasErrors) status = "error";
          else if (isActive) status = "active";
          else if (session.status === "completed") status = "completed";

          return {
            id: `agent-${agent.id}`,
            type: "agent",
            position: {
              x: 150 + (index % 3) * 300,
              y: 100 + Math.floor(index / 3) * 200,
            },
            data: {
              label: `${agent.role}+${agent.domain}`,
              role: agent.role,
              domain: agent.domain,
              status,
              agentId: agent.id,
              progress: status === "completed"
                ? 100
                : (status === "active" ? 65 : 0),
            },
          };
        });

        // Create task flow nodes
        const taskNodes: FlowNode[] =
          session.agents?.map((sessionAgent, index) => ({
            id: `task-${session.id}-${index}`,
            type: "task",
            position: {
              x: 150 + (index % 3) * 300,
              y: 50,
            },
            data: {
              label: sessionAgent.task?.substring(0, 30) + "..." || "Task",
              status: session.status === "completed" ? "completed" : "active",
              taskDescription: sessionAgent.task,
              progress: session.status === "completed" ? 100 : 45,
            },
          })) || [];

        // Create edges showing task flows
        const edges: FlowEdge[] = [];

        // Connect tasks to agents
        taskNodes.forEach((taskNode, index) => {
          if (nodes[index]) {
            edges.push({
              id: `edge-${taskNode.id}-${nodes[index].id}`,
              source: taskNode.id,
              target: nodes[index].id,
              type: "task_flow",
              animated: nodes[index].data.status === "active",
              status: nodes[index].data.status === "active"
                ? "active"
                : "completed",
            });
          }
        });

        // Add coordination edges between agents
        for (let i = 0; i < nodes.length - 1; i++) {
          edges.push({
            id: `coord-${nodes[i].id}-${nodes[i + 1].id}`,
            source: nodes[i].id,
            target: nodes[i + 1].id,
            type: "coordination",
            animated: false,
            status: "pending",
          });
        }

        return {
          id: session.id,
          name: session.name || `Session ${sessionIndex + 1}`,
          nodes: [...taskNodes, ...nodes],
          edges,
          coordinationStrategy: session.coordinationStrategy ||
            "fan_out_synthesize",
          status: session.status as WorkflowDiagram["status"],
        };
      });
  }, [sessions, agents, events]);

  // Handle workflow selection
  const selectedWorkflowData =
    workflowDiagrams.find((w) => w.id === selectedWorkflow) ||
    workflowDiagrams[0];

  const handleManualRefresh = () => {
    invalidateAll();
    setLastUpdateTime(new Date());
  };

  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 0.2, 2));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 0.2, 0.5));
  const handleCenterView = () => setAutoCenter(!autoCenter);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return theme.palette.warning.main;
      case "completed":
        return theme.palette.success.main;
      case "error":
        return theme.palette.error.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return PlayIcon;
      case "completed":
        return CompleteIcon;
      case "error":
        return ErrorIcon;
      default:
        return PendingIcon;
    }
  };

  return (
    <Box
      sx={{ p: 3, height: "100vh", display: "flex", flexDirection: "column" }}
    >
      {/* Header */}
      <Box sx={{ mb: 3 }}>
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
              Task Flow Visualizer
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Interactive workflow diagrams showing multi-agent task
              coordination and real-time activity
            </Typography>
          </Box>

          <Box display="flex" alignItems="center" gap={2}>
            {/* Workflow Selector */}
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Active Workflow</InputLabel>
              <Select
                value={selectedWorkflow || (workflowDiagrams[0]?.id || "")}
                onChange={(e) => setSelectedWorkflow(e.target.value)}
                label="Active Workflow"
                size="small"
              >
                {workflowDiagrams.map((workflow) => (
                  <MenuItem key={workflow.id} value={workflow.id}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Box
                        sx={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          backgroundColor: getStatusColor(workflow.status),
                        }}
                      />
                      {workflow.name}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Controls */}
            <Stack direction="row" spacing={1} alignItems="center">
              <FormControlLabel
                control={
                  <Switch
                    checked={isRealTime}
                    onChange={(e) => setIsRealTime(e.target.checked)}
                    color="primary"
                  />
                }
                label="Real-time"
                sx={{ m: 0 }}
              />

              <Tooltip title="Refresh">
                <IconButton onClick={handleManualRefresh} color="primary">
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
            </Stack>
          </Box>
        </Box>

        {/* Workflow Status Bar */}
        {selectedWorkflowData && (
          <Paper
            sx={{
              p: 2,
              mt: 2,
              bgcolor: alpha(theme.palette.primary.main, 0.04),
            }}
          >
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="center"
            >
              <Stack direction="row" spacing={2} alignItems="center">
                <Box display="flex" alignItems="center" gap={1}>
                  <FlowIcon color="primary" />
                  <Typography variant="h6">
                    {selectedWorkflowData.name}
                  </Typography>
                  <Chip
                    label={selectedWorkflowData.status}
                    color={selectedWorkflowData.status === "running"
                      ? "success"
                      : "default"}
                    size="small"
                  />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Strategy: {selectedWorkflowData.coordinationStrategy}{" "}
                  • Agents:{" "}
                  {selectedWorkflowData.nodes.filter((n) => n.type === "agent")
                    .length} • Tasks:{" "}
                  {selectedWorkflowData.nodes.filter((n) => n.type === "task")
                    .length}
                </Typography>
              </Stack>

              <Typography variant="caption" color="text.secondary">
                Last updated: {lastUpdateTime.toLocaleTimeString()}
              </Typography>
            </Stack>
          </Paper>
        )}
      </Box>

      {/* Main Content */}
      <Grid container spacing={3} sx={{ flex: 1, height: 0 }}>
        {/* Workflow Diagram */}
        <Grid item xs={12} lg={9}>
          <Card
            sx={{ height: "100%", display: "flex", flexDirection: "column" }}
          >
            <CardContent sx={{ pb: 1 }}>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography variant="h6">Workflow Diagram</Typography>

                <Stack direction="row" spacing={1}>
                  <Tooltip title="Zoom In">
                    <IconButton size="small" onClick={handleZoomIn}>
                      <ZoomInIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Zoom Out">
                    <IconButton size="small" onClick={handleZoomOut}>
                      <ZoomOutIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Center View">
                    <IconButton size="small" onClick={handleCenterView}>
                      <CenterIcon />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Box>
            </CardContent>

            {/* Diagram Canvas */}
            <Box
              sx={{
                flex: 1,
                position: "relative",
                overflow: "hidden",
                backgroundColor: alpha(theme.palette.grey[100], 0.3),
                backgroundImage:
                  "radial-gradient(circle, #ccc 1px, transparent 1px)",
                backgroundSize: "20px 20px",
              }}
            >
              {selectedWorkflowData
                ? (
                  <Box
                    sx={{
                      transform: `scale(${zoomLevel})`,
                      transformOrigin: autoCenter ? "center" : "top left",
                      transition: "transform 0.2s",
                      width: "100%",
                      height: "100%",
                      position: "relative",
                    }}
                  >
                    {/* Render Nodes */}
                    {selectedWorkflowData.nodes.map((node) => {
                      const StatusIcon = getStatusIcon(node.data.status);
                      const isAgent = node.type === "agent";

                      return (
                        <Paper
                          key={node.id}
                          sx={{
                            position: "absolute",
                            left: node.position.x,
                            top: node.position.y,
                            width: isAgent ? 160 : 200,
                            p: 2,
                            cursor: "pointer",
                            border: `2px solid ${
                              getStatusColor(node.data.status)
                            }`,
                            backgroundColor: node.data.status === "active"
                              ? alpha(theme.palette.warning.main, 0.1)
                              : "white",
                            "&:hover": {
                              boxShadow: theme.shadows[4],
                              transform: "translateY(-2px)",
                            },
                            transition: "all 0.2s",
                          }}
                        >
                          <Stack spacing={1}>
                            <Box display="flex" alignItems="center" gap={1}>
                              {isAgent
                                ? (
                                  <Avatar
                                    sx={{
                                      width: 24,
                                      height: 24,
                                      bgcolor: getStatusColor(node.data.status),
                                    }}
                                  >
                                    <AgentIcon sx={{ fontSize: 14 }} />
                                  </Avatar>
                                )
                                : (
                                  <StatusIcon
                                    sx={{
                                      color: getStatusColor(node.data.status),
                                      fontSize: 20,
                                    }}
                                  />
                                )}
                              <Typography variant="subtitle2" fontWeight={600}>
                                {node.data.label}
                              </Typography>
                            </Box>

                            {node.data.progress !== undefined && (
                              <Box>
                                <Box
                                  display="flex"
                                  justifyContent="space-between"
                                  alignItems="center"
                                >
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                  >
                                    Progress
                                  </Typography>
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                  >
                                    {node.data.progress}%
                                  </Typography>
                                </Box>
                                <Box
                                  sx={{
                                    width: "100%",
                                    height: 4,
                                    backgroundColor: alpha(
                                      theme.palette.grey[400],
                                      0.3,
                                    ),
                                    borderRadius: 2,
                                    overflow: "hidden",
                                  }}
                                >
                                  <Box
                                    sx={{
                                      width: `${node.data.progress}%`,
                                      height: "100%",
                                      backgroundColor: getStatusColor(
                                        node.data.status,
                                      ),
                                      transition: "width 0.3s",
                                    }}
                                  />
                                </Box>
                              </Box>
                            )}

                            <Chip
                              size="small"
                              label={node.data.status}
                              color={node.data.status === "active"
                                ? "warning"
                                : node.data.status === "completed"
                                ? "success"
                                : node.data.status === "error"
                                ? "error"
                                : "default"}
                              sx={{ height: 20, fontSize: "0.7rem" }}
                            />
                          </Stack>
                        </Paper>
                      );
                    })}

                    {/* Render Edges (simple lines for MVP) */}
                    <svg
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: "100%",
                        pointerEvents: "none",
                        zIndex: 0,
                      }}
                    >
                      {selectedWorkflowData.edges.map((edge) => {
                        const sourceNode = selectedWorkflowData.nodes.find(
                          (n) => n.id === edge.source,
                        );
                        const targetNode = selectedWorkflowData.nodes.find(
                          (n) => n.id === edge.target,
                        );

                        if (!sourceNode || !targetNode) return null;

                        const strokeColor = edge.status === "active"
                          ? theme.palette.warning.main
                          : edge.status === "completed"
                          ? theme.palette.success.main
                          : theme.palette.grey[400];

                        return (
                          <line
                            key={edge.id}
                            x1={sourceNode.position.x + 80}
                            y1={sourceNode.position.y + 40}
                            x2={targetNode.position.x + 80}
                            y2={targetNode.position.y + 40}
                            stroke={strokeColor}
                            strokeWidth={edge.status === "active" ? 3 : 2}
                            strokeDasharray={edge.type === "coordination"
                              ? "5,5"
                              : "0"}
                            opacity={0.7}
                          />
                        );
                      })}
                    </svg>
                  </Box>
                )
                : (
                  <Box
                    display="flex"
                    flexDirection="column"
                    alignItems="center"
                    justifyContent="center"
                    height="100%"
                    color="text.secondary"
                  >
                    <FlowIcon sx={{ fontSize: 64, mb: 2, opacity: 0.3 }} />
                    <Typography variant="h6">No Active Workflows</Typography>
                    <Typography variant="body2">
                      Start an orchestration to see workflow diagrams
                    </Typography>
                  </Box>
                )}
            </Box>
          </Card>
        </Grid>

        {/* Agent Activity Panel */}
        <Grid item xs={12} lg={3}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
                <Typography variant="h6">Agent Activity</Typography>
                <IconButton
                  size="small"
                  onClick={(e) => setFilterMenuAnchor(e.currentTarget)}
                >
                  <FilterIcon />
                </IconButton>
              </Box>

              <Stack spacing={2} sx={{ maxHeight: 400, overflowY: "auto" }}>
                {agents?.map((agent) => {
                  const recentEvents = events?.filter((e) =>
                    e.agentId === agent.id
                  ).slice(0, 3) || [];
                  const isActive = recentEvents.some((e) =>
                    new Date(e.timestamp).getTime() > Date.now() - 60000
                  );

                  return (
                    <Paper
                      key={agent.id}
                      sx={{
                        p: 2,
                        bgcolor: alpha(theme.palette.grey[100], 0.3),
                      }}
                    >
                      <Stack direction="row" spacing={2} alignItems="center">
                        <Avatar
                          sx={{
                            bgcolor: isActive ? "warning.main" : "grey.400",
                            width: 32,
                            height: 32,
                          }}
                        >
                          <AgentIcon sx={{ fontSize: 16 }} />
                        </Avatar>

                        <Box flex={1}>
                          <Typography variant="subtitle2" fontWeight={600}>
                            {agent.role}+{agent.domain}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {isActive ? "Active" : "Idle"} •{" "}
                            {recentEvents.length} events
                          </Typography>
                        </Box>

                        <Box
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            backgroundColor: isActive
                              ? "warning.main"
                              : "grey.400",
                          }}
                        />
                      </Stack>
                    </Paper>
                  );
                }) || (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    textAlign="center"
                  >
                    No active agents
                  </Typography>
                )}
              </Stack>
            </CardContent>
          </Card>

          {/* Quick Metrics */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Quick Metrics</Typography>
              <Stack spacing={1}>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2">Active Workflows</Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {workflowDiagrams.filter((w) => w.status === "running")
                      .length}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2">Total Agents</Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {agents?.length || 0}
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2">Avg. Progress</Typography>
                  <Typography variant="body2" fontWeight={600}>
                    {selectedWorkflowData
                      ? Math.round(
                        selectedWorkflowData.nodes.reduce((acc, node) =>
                          acc + (node.data.progress || 0), 0) /
                          selectedWorkflowData.nodes.length,
                      ) + "%"
                      : "0%"}
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filter Menu */}
      <Menu
        anchorEl={filterMenuAnchor}
        open={Boolean(filterMenuAnchor)}
        onClose={() =>
          setFilterMenuAnchor(null)}
      >
        <MenuItem
          onClick={() => {
            setActivityFilter("all");
            setFilterMenuAnchor(null);
          }}
        >
          All Agents
        </MenuItem>
        <MenuItem
          onClick={() => {
            setActivityFilter("active");
            setFilterMenuAnchor(null);
          }}
        >
          Active Only
        </MenuItem>
        <MenuItem
          onClick={() => {
            setActivityFilter("idle");
            setFilterMenuAnchor(null);
          }}
        >
          Idle Only
        </MenuItem>
      </Menu>
    </Box>
  );
}
