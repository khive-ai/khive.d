/**
 * Task Flow Visualizer MVP - Interactive workflow diagrams for multi-agent tasks
 * Core functionality: basic workflow diagram display, agent activity highlighting
 */

"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  ConnectionMode,
  Controls,
  Edge,
  MarkerType,
  MiniMap,
  Node,
  Panel,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "reactflow";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Drawer,
  FormControlLabel,
  IconButton,
  Switch,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  AccountTree as FlowIcon,
  CenterFocusStrong as CenterIcon,
  Close as CloseIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
} from "@mui/icons-material";
import { Agent, HookEvent, Plan, PlanNode } from "@/lib/types";

// Import ReactFlow styles
import "reactflow/dist/style.css";

// Custom node types
import { WorkflowNode } from "./task-flow-visualizer/workflow-node";
import { AgentNode } from "./task-flow-visualizer/agent-node";
import { TaskNode } from "./task-flow-visualizer/task-node";

export interface TaskFlowVisualizerProps {
  plan?: Plan;
  agents?: Agent[];
  events?: HookEvent[];
  className?: string;
  autoLayout?: boolean;
  showMiniMap?: boolean;
  showControls?: boolean;
  onNodeClick?: (nodeId: string, nodeData: any) => void;
  onNodeSelect?: (node: Node | null) => void;
}

// Define custom node types
const nodeTypes = {
  workflow: WorkflowNode,
  agent: AgentNode,
  task: TaskNode,
};

// Layout constants
const LAYOUT_CONFIG = {
  nodeWidth: 200,
  nodeHeight: 80,
  verticalSpacing: 150,
  horizontalSpacing: 250,
  miniMapNodeColor: "#1976d2",
  miniMapMaskColor: "rgba(25, 118, 210, 0.1)",
};

export const TaskFlowVisualizer: React.FC<TaskFlowVisualizerProps> = ({
  plan,
  agents = [],
  events = [],
  className,
  autoLayout = true,
  showMiniMap = true,
  showControls = true,
  onNodeClick,
  onNodeSelect,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [showAgentActivity, setShowAgentActivity] = useState(true);
  const [showNodeDetails, setShowNodeDetails] = useState(false);
  const [layoutDirection, setLayoutDirection] = useState<"TB" | "LR">("TB"); // Top-Bottom or Left-Right

  // Generate layout positions using a simple grid-based algorithm
  const calculateNodePositions = useCallback(
    (planNodes: PlanNode[], edges: Array<{ from: string; to: string }>) => {
      const positions: Record<string, { x: number; y: number }> = {};
      const visited = new Set<string>();
      const levels: string[][] = [];

      // Build dependency graph
      const dependencies = new Map<string, string[]>();
      const dependents = new Map<string, string[]>();

      planNodes.forEach((node) => {
        dependencies.set(node.id, node.dependencies || []);
        dependents.set(node.id, []);
      });

      edges.forEach((edge) => {
        const deps = dependents.get(edge.from) || [];
        deps.push(edge.to);
        dependents.set(edge.from, deps);
      });

      // Topological sort to determine levels
      const queue = planNodes.filter((node) =>
        (node.dependencies || []).length === 0
      );
      let currentLevel = 0;

      while (queue.length > 0) {
        const levelNodes: string[] = [];
        const nextQueue: PlanNode[] = [];

        queue.forEach((node) => {
          if (!visited.has(node.id)) {
            visited.add(node.id);
            levelNodes.push(node.id);

            // Add dependent nodes to next queue
            const deps = dependents.get(node.id) || [];
            deps.forEach((depId) => {
              const depNode = planNodes.find((n) => n.id === depId);
              if (depNode && !visited.has(depId)) {
                const allDepsVisited = (depNode.dependencies || []).every((d) =>
                  visited.has(d)
                );
                if (allDepsVisited) {
                  nextQueue.push(depNode);
                }
              }
            });
          }
        });

        levels[currentLevel] = levelNodes;
        queue.splice(0, queue.length, ...nextQueue);
        currentLevel++;
      }

      // Calculate positions based on levels
      levels.forEach((levelNodes, levelIndex) => {
        const levelY = layoutDirection === "TB"
          ? levelIndex * LAYOUT_CONFIG.verticalSpacing
          : levelIndex * LAYOUT_CONFIG.horizontalSpacing;

        levelNodes.forEach((nodeId, nodeIndex) => {
          const levelX = layoutDirection === "TB"
            ? (nodeIndex - (levelNodes.length - 1) / 2) *
              LAYOUT_CONFIG.horizontalSpacing
            : (nodeIndex - (levelNodes.length - 1) / 2) *
              LAYOUT_CONFIG.verticalSpacing;

          positions[nodeId] = {
            x: layoutDirection === "TB" ? levelX : levelY,
            y: layoutDirection === "TB" ? levelY : levelX,
          };
        });
      });

      return positions;
    },
    [layoutDirection],
  );

  // Convert plan data to React Flow nodes and edges
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!plan) {
      return { flowNodes: [], flowEdges: [] };
    }

    const positions = autoLayout
      ? calculateNodePositions(plan.nodes, plan.edges)
      : {};

    // Create workflow nodes from plan nodes
    const workflowNodes: Node[] = plan.nodes.map((planNode) => {
      const position = positions[planNode.id] ||
        { x: Math.random() * 500, y: Math.random() * 300 };

      return {
        id: planNode.id,
        type: "workflow",
        position,
        data: {
          phase: planNode.phase,
          status: planNode.status,
          agents: planNode.agents,
          tasks: planNode.tasks,
          coordinationStrategy: planNode.coordinationStrategy,
          expectedArtifacts: planNode.expectedArtifacts,
          activeAgents: showAgentActivity
            ? agents.filter((a) => planNode.agents.includes(a.id))
            : [],
          recentEvents: showAgentActivity
            ? events.filter((e) => planNode.agents.includes(e.agentId))
            : [],
        },
        style: {
          width: LAYOUT_CONFIG.nodeWidth,
          height: LAYOUT_CONFIG.nodeHeight,
        },
      };
    });

    // Create edges from plan edges
    const workflowEdges: Edge[] = plan.edges.map((edge, index) => ({
      id: `edge-${edge.from}-${edge.to}`,
      source: edge.from,
      target: edge.to,
      type: "smoothstep",
      animated: false,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: "#1976d2",
        width: 20,
        height: 20,
      },
      style: {
        stroke: "#1976d2",
        strokeWidth: 2,
      },
      label: `Step ${index + 1}`,
      labelStyle: {
        fontSize: 12,
        fontWeight: 500,
        fill: "#666",
      },
      labelBgStyle: {
        fill: "white",
        stroke: "#ccc",
        strokeWidth: 1,
        rx: 4,
      },
    }));

    return { flowNodes: workflowNodes, flowEdges: workflowEdges };
  }, [
    plan,
    agents,
    events,
    showAgentActivity,
    autoLayout,
    calculateNodePositions,
  ]);

  // Update nodes and edges when data changes
  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  // Handle node selection
  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
    setShowNodeDetails(true);
    onNodeClick?.(node.id, node.data);
    onNodeSelect?.(node);
  }, [onNodeClick, onNodeSelect]);

  // Handle node selection change (for external control)
  const handleSelectionChange = useCallback((elements: { nodes: Node[] }) => {
    const selected = elements.nodes[0] || null;
    setSelectedNode(selected);
    onNodeSelect?.(selected);
  }, [onNodeSelect]);

  // Get status color for nodes
  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "#4caf50";
      case "running":
        return "#2196f3";
      case "failed":
        return "#f44336";
      case "pending":
        return "#ff9800";
      default:
        return "#9e9e9e";
    }
  };

  // Mock data for demo when no plan is provided
  const mockPlan: Plan = {
    id: "demo-plan",
    sessionId: "demo-session",
    nodes: [
      {
        id: "phase-1",
        phase: "Research & Analysis",
        status: "completed",
        agents: ["researcher-001", "analyst-001"],
        tasks: ["Market research", "Competitive analysis"],
        coordinationStrategy: "FAN_OUT_SYNTHESIZE",
        expectedArtifacts: ["research_report.md", "analysis_summary.md"],
        dependencies: [],
      },
      {
        id: "phase-2",
        phase: "Architecture Design",
        status: "running",
        agents: ["architect-001"],
        tasks: ["System design", "API specification"],
        coordinationStrategy: "PIPELINE",
        expectedArtifacts: ["architecture_design.md", "api_spec.yaml"],
        dependencies: ["phase-1"],
      },
      {
        id: "phase-3",
        phase: "Implementation",
        status: "pending",
        agents: ["implementer-001", "implementer-002"],
        tasks: ["Frontend development", "Backend development"],
        coordinationStrategy: "PARALLEL",
        expectedArtifacts: ["frontend_code", "backend_code"],
        dependencies: ["phase-2"],
      },
    ],
    edges: [
      { from: "phase-1", to: "phase-2" },
      { from: "phase-2", to: "phase-3" },
    ],
  };

  const displayPlan = plan || mockPlan;

  return (
    <Box className={className}>
      <Card variant="outlined">
        <CardContent sx={{ p: 0, height: 600, position: "relative" }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            onSelectionChange={handleSelectionChange}
            nodeTypes={nodeTypes}
            connectionMode={ConnectionMode.Strict}
            fitView
            attributionPosition="top-right"
          >
            <Background variant="dots" gap={20} size={1} />

            {showControls && <Controls />}

            {showMiniMap && (
              <MiniMap
                nodeColor={LAYOUT_CONFIG.miniMapNodeColor}
                maskColor={LAYOUT_CONFIG.miniMapMaskColor}
                position="bottom-left"
              />
            )}

            {/* Control Panel */}
            <Panel position="top-left">
              <Card sx={{ p: 2, minWidth: 250 }}>
                <Box display="flex" alignItems="center" gap={2} mb={2}>
                  <FlowIcon color="primary" />
                  <Typography variant="h6">Task Flow</Typography>
                  <Chip
                    label={`${displayPlan.nodes.length} phases`}
                    size="small"
                    color="primary"
                    variant="outlined"
                  />
                </Box>

                <Box display="flex" flexDirection="column" gap={1}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={showAgentActivity}
                        onChange={(e) => setShowAgentActivity(e.target.checked)}
                        size="small"
                      />
                    }
                    label="Show Agent Activity"
                  />

                  <Box display="flex" gap={1}>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={() =>
                        setLayoutDirection(
                          layoutDirection === "TB" ? "LR" : "TB",
                        )}
                    >
                      {layoutDirection === "TB" ? "Vertical" : "Horizontal"}
                    </Button>

                    <Tooltip title="Refresh layout">
                      <IconButton size="small">
                        <RefreshIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>
              </Card>
            </Panel>

            {/* Status Panel */}
            <Panel position="top-right">
              <Card sx={{ p: 1.5, minWidth: 200 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  System Status
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={0.5}>
                  <Chip
                    label="3 Active"
                    size="small"
                    color="success"
                    variant="filled"
                  />
                  <Chip
                    label="1 Pending"
                    size="small"
                    color="warning"
                    variant="filled"
                  />
                  <Chip
                    label="Live Updates"
                    size="small"
                    color="info"
                    variant="outlined"
                  />
                </Box>
              </Card>
            </Panel>
          </ReactFlow>
        </CardContent>
      </Card>

      {/* Node Details Drawer */}
      <Drawer
        anchor="right"
        open={showNodeDetails && selectedNode !== null}
        onClose={() => setShowNodeDetails(false)}
        sx={{ "& .MuiDrawer-paper": { width: 400, p: 2 } }}
      >
        {selectedNode && (
          <Box>
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              mb={2}
            >
              <Typography variant="h6">Node Details</Typography>
              <IconButton onClick={() => setShowNodeDetails(false)}>
                <CloseIcon />
              </IconButton>
            </Box>

            <Card variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {selectedNode.data.phase || selectedNode.id}
                </Typography>

                <Chip
                  label={selectedNode.data.status || "Unknown"}
                  color={selectedNode.data.status === "completed"
                    ? "success"
                    : selectedNode.data.status === "running"
                    ? "primary"
                    : selectedNode.data.status === "failed"
                    ? "error"
                    : "default"}
                  sx={{ mb: 2 }}
                />

                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Coordination Strategy
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {selectedNode.data.coordinationStrategy || "N/A"}
                </Typography>

                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Assigned Agents
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={0.5} mb={2}>
                  {(selectedNode.data.agents || []).map((agentId: string) => (
                    <Chip
                      key={agentId}
                      label={agentId.slice(-8)}
                      size="small"
                      variant="outlined"
                    />
                  ))}
                </Box>

                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Tasks
                </Typography>
                <Box component="ul" sx={{ pl: 2, mt: 0 }}>
                  {(selectedNode.data.tasks || []).map((
                    task: string,
                    index: number,
                  ) => (
                    <Typography key={index} component="li" variant="body2">
                      {task}
                    </Typography>
                  ))}
                </Box>
              </CardContent>
            </Card>

            {selectedNode.data.expectedArtifacts &&
              selectedNode.data.expectedArtifacts.length > 0 && (
              <Card variant="outlined">
                <CardContent>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Expected Artifacts
                  </Typography>
                  <Box component="ul" sx={{ pl: 2, mt: 0 }}>
                    {selectedNode.data.expectedArtifacts.map((
                      artifact: string,
                      index: number,
                    ) => (
                      <Typography key={index} component="li" variant="body2">
                        {artifact}
                      </Typography>
                    ))}
                  </Box>
                </CardContent>
              </Card>
            )}
          </Box>
        )}
      </Drawer>
    </Box>
  );
};

export default TaskFlowVisualizer;
