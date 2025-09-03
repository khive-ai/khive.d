/**
 * Workflow Diagram Display Component - Task Flow Visualizer MVP
 * Interactive workflow diagrams for multi-agent tasks with activity highlighting
 */

"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  alpha,
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  FormControlLabel,
  IconButton,
  Paper,
  Stack,
  Switch,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CenterFocusStrong as CenterIcon,
  Fullscreen as FullscreenIcon,
  Refresh as RefreshIcon,
  Timeline as WorkflowIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
} from "@mui/icons-material";
import ReactFlow, {
  Background,
  ConnectionMode,
  Controls,
  Edge,
  EdgeTypes,
  Node,
  NodeTypes,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

// Import types
import type { Agent, CoordinationEvent, Session } from "@/types";

// Agent Node Component with Activity Highlighting
const AgentNode = ({ data }: { data: any }) => {
  const theme = useTheme();
  const { agent, isActive, currentTask, status, progress } = data;

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return theme.palette.success.main;
      case "idle":
        return theme.palette.info.main;
      case "error":
        return theme.palette.error.main;
      case "terminated":
        return theme.palette.grey[400];
      default:
        return theme.palette.grey[400];
    }
  };

  const getNodeStyle = () => {
    const baseStyle = {
      background: isActive
        ? `linear-gradient(135deg, ${alpha(getStatusColor(status), 0.2)}, ${
          alpha(getStatusColor(status), 0.1)
        })`
        : alpha(theme.palette.grey[100], 0.8),
      border: `2px solid ${getStatusColor(status)}`,
      borderRadius: "12px",
      padding: "12px",
      minWidth: "180px",
      boxShadow: isActive
        ? `0 4px 20px ${alpha(getStatusColor(status), 0.3)}`
        : `0 2px 8px ${alpha(theme.palette.grey[400], 0.2)}`,
      transform: isActive ? "scale(1.05)" : "scale(1)",
      transition: "all 0.3s ease-in-out",
    };

    // Pulsing effect for active agents
    if (isActive && status === "active") {
      return {
        ...baseStyle,
        animation: "pulse 2s infinite",
        "@keyframes pulse": {
          "0%": {
            boxShadow: `0 4px 20px ${alpha(getStatusColor(status), 0.3)}`,
          },
          "50%": {
            boxShadow: `0 6px 25px ${alpha(getStatusColor(status), 0.5)}`,
          },
          "100%": {
            boxShadow: `0 4px 20px ${alpha(getStatusColor(status), 0.3)}`,
          },
        },
      };
    }

    return baseStyle;
  };

  return (
    <Box sx={getNodeStyle()}>
      <Stack spacing={1} alignItems="center">
        {/* Agent Role & Domain */}
        <Typography variant="subtitle2" fontWeight={600} textAlign="center">
          {agent.role}
        </Typography>
        <Chip
          label={agent.domain}
          size="small"
          variant="outlined"
          sx={{ fontSize: "0.75rem", height: "20px" }}
        />

        {/* Status Indicator */}
        <Stack direction="row" alignItems="center" spacing={1}>
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: getStatusColor(status),
              boxShadow: isActive
                ? `0 0 8px ${alpha(getStatusColor(status), 0.6)}`
                : "none",
            }}
          />
          <Typography variant="caption" color="text.secondary">
            {status}
          </Typography>
        </Stack>

        {/* Current Task (if active) */}
        {currentTask && isActive && (
          <Typography
            variant="caption"
            sx={{
              textAlign: "center",
              color: "primary.main",
              fontStyle: "italic",
              maxWidth: "160px",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {currentTask}
          </Typography>
        )}

        {/* Progress indicator (if available) */}
        {progress !== undefined && isActive && (
          <Box
            sx={{
              width: "100%",
              height: 4,
              backgroundColor: "grey.200",
              borderRadius: 2,
            }}
          >
            <Box
              sx={{
                width: `${progress}%`,
                height: "100%",
                backgroundColor: getStatusColor(status),
                borderRadius: 2,
                transition: "width 0.3s ease",
              }}
            />
          </Box>
        )}
      </Stack>
    </Box>
  );
};

// Orchestrator Node Component
const OrchestratorNode = ({ data }: { data: any }) => {
  const theme = useTheme();
  const { name, strategy, activeAgents, totalTasks } = data;

  return (
    <Box
      sx={{
        background: `linear-gradient(135deg, ${
          alpha(theme.palette.primary.main, 0.2)
        }, ${alpha(theme.palette.primary.main, 0.1)})`,
        border: `3px solid ${theme.palette.primary.main}`,
        borderRadius: "16px",
        padding: "16px",
        minWidth: "200px",
        boxShadow: `0 6px 24px ${alpha(theme.palette.primary.main, 0.2)}`,
      }}
    >
      <Stack spacing={2} alignItems="center">
        <WorkflowIcon sx={{ fontSize: 32, color: "primary.main" }} />
        <Typography
          variant="h6"
          fontWeight={700}
          color="primary.main"
          textAlign="center"
        >
          {name || "Orchestrator"}
        </Typography>
        <Chip
          label={strategy}
          color="primary"
          variant="filled"
          sx={{ fontWeight: 600 }}
        />
        <Stack direction="row" spacing={2}>
          <Box textAlign="center">
            <Typography variant="h6" color="primary.main">
              {activeAgents}
            </Typography>
            <Typography variant="caption">Active Agents</Typography>
          </Box>
          <Box textAlign="center">
            <Typography variant="h6" color="secondary.main">
              {totalTasks}
            </Typography>
            <Typography variant="caption">Tasks</Typography>
          </Box>
        </Stack>
      </Stack>
    </Box>
  );
};

// Custom Edge Component
const AnimatedEdge = (
  { id, sourceX, sourceY, targetX, targetY, style = {} }: any,
) => {
  const theme = useTheme();

  return (
    <>
      <path
        id={id}
        className="react-flow__edge-path"
        d={`M${sourceX},${sourceY} L${targetX},${targetY}`}
        stroke={alpha(theme.palette.primary.main, 0.6)}
        strokeWidth={2}
        fill="none"
        strokeDasharray="5,5"
        style={{
          ...style,
          animation: "dash 1s linear infinite",
        }}
      />
      <style jsx>
        {`
        @keyframes dash {
          to {
            stroke-dashoffset: -10;
          }
        }
      `}
      </style>
    </>
  );
};

// Node Types
const nodeTypes: NodeTypes = {
  agent: AgentNode,
  orchestrator: OrchestratorNode,
};

// Edge Types
const edgeTypes: EdgeTypes = {
  animated: AnimatedEdge,
};

// Main Props Interface
interface WorkflowDiagramDisplayProps {
  session?: Session;
  agents?: Agent[];
  coordinationStrategy?:
    | "fan_out_synthesize"
    | "parallel_discovery"
    | "hierarchical_delegation";
  recentEvents?: CoordinationEvent[];
  onNodeClick?: (agent: Agent) => void;
  className?: string;
}

export const WorkflowDiagramDisplay: React.FC<WorkflowDiagramDisplayProps> = ({
  session,
  agents = [],
  coordinationStrategy = "fan_out_synthesize",
  recentEvents = [],
  onNodeClick,
  className,
}) => {
  const theme = useTheme();

  // State
  const [showLabels, setShowLabels] = useState(true);
  const [highlightActive, setHighlightActive] = useState(true);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Generate workflow layout based on coordination strategy
  const generateWorkflowLayout = useCallback(() => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];

    // Central orchestrator node
    newNodes.push({
      id: "orchestrator",
      type: "orchestrator",
      position: { x: 400, y: 200 },
      data: {
        name: "Lion Orchestrator",
        strategy: coordinationStrategy.replace(/_/g, " "),
        activeAgents: agents.filter((a) => a.status === "active").length,
        totalTasks: session?.metrics?.totalTasks || agents.length,
      },
    });

    // Position agents based on coordination strategy
    agents.forEach((agent, index) => {
      let position = { x: 0, y: 0 };

      switch (coordinationStrategy) {
        case "fan_out_synthesize":
          // Radial layout around orchestrator
          const angle = (index / agents.length) * 2 * Math.PI;
          const radius = 250;
          position = {
            x: 400 + radius * Math.cos(angle),
            y: 200 + radius * Math.sin(angle),
          };
          break;

        case "parallel_discovery":
          // Horizontal line layout
          position = {
            x: 100 + index * 200,
            y: 100,
          };
          break;

        case "hierarchical_delegation":
          // Hierarchical tree layout
          const cols = Math.ceil(Math.sqrt(agents.length));
          const row = Math.floor(index / cols);
          const col = index % cols;
          position = {
            x: 200 + col * 180,
            y: 350 + row * 120,
          };
          break;
      }

      const isActive = highlightActive &&
        (agent.status === "active" ||
          recentEvents.some((e) => e.agentId === agent.id));

      newNodes.push({
        id: agent.id,
        type: "agent",
        position,
        data: {
          agent,
          isActive,
          currentTask: agent.currentTask,
          status: agent.status,
          progress: Math.random() * 100, // Mock progress for MVP
        },
      });

      // Connect agents to orchestrator
      newEdges.push({
        id: `orchestrator-${agent.id}`,
        source: "orchestrator",
        target: agent.id,
        type: isActive ? "animated" : "default",
        animated: isActive,
        style: {
          stroke: isActive
            ? theme.palette.success.main
            : alpha(theme.palette.grey[400], 0.6),
          strokeWidth: isActive ? 3 : 1,
        },
      });
    });

    // Add inter-agent connections for certain strategies
    if (coordinationStrategy === "parallel_discovery") {
      for (let i = 0; i < agents.length - 1; i++) {
        newEdges.push({
          id: `agent-${agents[i].id}-${agents[i + 1].id}`,
          source: agents[i].id,
          target: agents[i + 1].id,
          style: {
            stroke: alpha(theme.palette.secondary.main, 0.4),
            strokeWidth: 1,
            strokeDasharray: "3,3",
          },
        });
      }
    }

    return { nodes: newNodes, edges: newEdges };
  }, [
    agents,
    coordinationStrategy,
    highlightActive,
    recentEvents,
    theme,
    session,
  ]);

  // Update layout when data changes
  useEffect(() => {
    const layout = generateWorkflowLayout();
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [generateWorkflowLayout, setNodes, setEdges]);

  // Handle node clicks
  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.type === "agent" && node.data.agent && onNodeClick) {
      onNodeClick(node.data.agent);
    }
  }, [onNodeClick]);

  const refreshLayout = useCallback(() => {
    const layout = generateWorkflowLayout();
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [generateWorkflowLayout, setNodes, setEdges]);

  return (
    <Card className={className} sx={{ height: 600 }}>
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={1}>
            <WorkflowIcon color="primary" />
            <Typography variant="h6">Task Flow Visualizer</Typography>
            <Chip
              label={coordinationStrategy.replace(/_/g, " ")}
              size="small"
              color="primary"
              variant="outlined"
            />
          </Box>
        }
        action={
          <Stack direction="row" spacing={1} alignItems="center">
            <FormControlLabel
              control={
                <Switch
                  checked={highlightActive}
                  onChange={(e) => setHighlightActive(e.target.checked)}
                  size="small"
                />
              }
              label="Highlight Active"
              sx={{ "& .MuiFormControlLabel-label": { fontSize: "0.875rem" } }}
            />
            <Tooltip title="Refresh Layout">
              <IconButton size="small" onClick={refreshLayout}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Stack>
        }
      />

      <CardContent sx={{ height: "calc(100% - 80px)", p: 0 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          connectionMode={ConnectionMode.Loose}
          fitView
          attributionPosition="bottom-left"
          proOptions={{ hideAttribution: true }}
        >
          <Background color={alpha(theme.palette.primary.main, 0.1)} gap={20} />
          <Controls showInteractive={false} />
        </ReactFlow>

        {/* Status Summary */}
        <Paper
          sx={{
            position: "absolute",
            top: 16,
            left: 16,
            p: 2,
            bgcolor: alpha(theme.palette.background.paper, 0.9),
            backdropFilter: "blur(8px)",
            minWidth: 200,
          }}
        >
          <Typography variant="subtitle2" gutterBottom>
            Workflow Status
          </Typography>
          <Stack spacing={1}>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="body2">Total Agents:</Typography>
              <Typography variant="body2" fontWeight={600}>
                {agents.length}
              </Typography>
            </Box>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="body2">Active:</Typography>
              <Typography variant="body2" fontWeight={600} color="success.main">
                {agents.filter((a) => a.status === "active").length}
              </Typography>
            </Box>
            <Box display="flex" justifyContent="space-between">
              <Typography variant="body2">Strategy:</Typography>
              <Typography variant="body2" fontWeight={600} color="primary.main">
                {coordinationStrategy.split("_").map((word) =>
                  word.charAt(0).toUpperCase() + word.slice(1)
                ).join(" ")}
              </Typography>
            </Box>
          </Stack>
        </Paper>
      </CardContent>
    </Card>
  );
};

export default WorkflowDiagramDisplay;
