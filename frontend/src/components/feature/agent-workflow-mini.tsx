/**
 * Agent Workflow Mini Component - Compact Task Flow Visualizer
 * Compact workflow visualization for integration with coordination monitoring
 */

"use client";

import React, { useCallback, useMemo } from "react";
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  IconButton,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Psychology as AgentIcon,
  Refresh as RefreshIcon,
  Timeline as WorkflowIcon,
  ZoomIn as ZoomInIcon,
} from "@mui/icons-material";

// Import types
import type { Agent, CoordinationEvent } from "@/types";

// Compact Agent Node
const CompactAgentNode = ({
  agent,
  isActive,
  position,
}: {
  agent: Agent;
  isActive: boolean;
  position: { x: number; y: number };
}) => {
  const theme = useTheme();

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

  return (
    <Box
      sx={{
        position: "absolute",
        left: position.x,
        top: position.y,
        transform: "translate(-50%, -50%)",
        zIndex: 2,
      }}
    >
      <Tooltip
        title={`${agent.role} (${agent.domain})\nStatus: ${agent.status}\n${
          agent.currentTask || "No active task"
        }`}
      >
        <Box
          sx={{
            width: 40,
            height: 40,
            borderRadius: "50%",
            background: isActive
              ? `radial-gradient(circle, ${
                alpha(getStatusColor(agent.status), 0.3)
              }, ${alpha(getStatusColor(agent.status), 0.1)})`
              : alpha(theme.palette.grey[200], 0.8),
            border: `2px solid ${getStatusColor(agent.status)}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            transition: "all 0.3s ease-in-out",
            boxShadow: isActive
              ? `0 0 12px ${alpha(getStatusColor(agent.status), 0.4)}`
              : "0 2px 4px rgba(0,0,0,0.1)",
            animation: isActive && agent.status === "active"
              ? "pulse 2s infinite"
              : "none",
            "&:hover": {
              transform: "scale(1.1)",
              boxShadow: `0 0 16px ${alpha(getStatusColor(agent.status), 0.6)}`,
            },
            "@keyframes pulse": {
              "0%": {
                boxShadow: `0 0 8px ${
                  alpha(getStatusColor(agent.status), 0.3)
                }`,
              },
              "50%": {
                boxShadow: `0 0 16px ${
                  alpha(getStatusColor(agent.status), 0.6)
                }`,
              },
              "100%": {
                boxShadow: `0 0 8px ${
                  alpha(getStatusColor(agent.status), 0.3)
                }`,
              },
            },
          }}
        >
          <AgentIcon
            sx={{
              fontSize: 20,
              color: isActive ? getStatusColor(agent.status) : "grey.500",
            }}
          />
        </Box>
      </Tooltip>
    </Box>
  );
};

// Connection Line Component
const ConnectionLine = ({
  from,
  to,
  isActive,
}: {
  from: { x: number; y: number };
  to: { x: number; y: number };
  isActive: boolean;
}) => {
  const theme = useTheme();

  return (
    <svg
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 1,
      }}
    >
      <line
        x1={from.x}
        y1={from.y}
        x2={to.x}
        y2={to.y}
        stroke={isActive
          ? alpha(theme.palette.primary.main, 0.8)
          : alpha(theme.palette.grey[400], 0.4)}
        strokeWidth={isActive ? 2 : 1}
        strokeDasharray={isActive ? "4,2" : "none"}
        style={{
          animation: isActive ? "dash 1s linear infinite" : "none",
        }}
      />
      <defs>
        <style>
          {`
          @keyframes dash {
            to {
              stroke-dashoffset: -6;
            }
          }
        `}
        </style>
      </defs>
    </svg>
  );
};

// Main Props Interface
interface AgentWorkflowMiniProps {
  agents?: Agent[];
  coordinationStrategy?:
    | "fan_out_synthesize"
    | "parallel_discovery"
    | "hierarchical_delegation";
  recentEvents?: CoordinationEvent[];
  onAgentClick?: (agent: Agent) => void;
  onExpandClick?: () => void;
  height?: number;
  className?: string;
}

export const AgentWorkflowMini: React.FC<AgentWorkflowMiniProps> = ({
  agents = [],
  coordinationStrategy = "fan_out_synthesize",
  recentEvents = [],
  onAgentClick,
  onExpandClick,
  height = 200,
  className,
}) => {
  const theme = useTheme();

  // Generate compact layout positions
  const generateCompactLayout = useCallback(() => {
    const centerX = 120;
    const centerY = height / 2;
    const agentPositions: Array<
      { agent: Agent; position: { x: number; y: number }; isActive: boolean }
    > = [];
    const connections: Array<
      {
        from: { x: number; y: number };
        to: { x: number; y: number };
        isActive: boolean;
      }
    > = [];

    // Orchestrator position (center)
    const orchestratorPos = { x: centerX, y: centerY };

    agents.forEach((agent, index) => {
      let position = { x: 0, y: 0 };
      const isActive = agent.status === "active" ||
        recentEvents.some((e) => e.agentId === agent.id);

      switch (coordinationStrategy) {
        case "fan_out_synthesize":
          // Radial layout (compact)
          const angle = (index / agents.length) * 2 * Math.PI;
          const radius = Math.min(80, height * 0.3);
          position = {
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle),
          };
          break;

        case "parallel_discovery":
          // Horizontal line
          const spacing = Math.min(40, 200 / Math.max(agents.length, 1));
          position = {
            x: 40 + index * spacing,
            y: centerY,
          };
          break;

        case "hierarchical_delegation":
          // Simple grid
          const cols = Math.ceil(Math.sqrt(agents.length));
          const row = Math.floor(index / cols);
          const col = index % cols;
          position = {
            x: 60 + col * 60,
            y: 60 + row * 50,
          };
          break;
      }

      agentPositions.push({ agent, position, isActive });

      // Add connection to orchestrator for fan_out_synthesize
      if (coordinationStrategy === "fan_out_synthesize") {
        connections.push({
          from: orchestratorPos,
          to: position,
          isActive,
        });
      }
    });

    return { agentPositions, connections, orchestratorPos };
  }, [agents, coordinationStrategy, recentEvents, height]);

  const layout = useMemo(() => generateCompactLayout(), [
    generateCompactLayout,
  ]);

  const activeCount = agents.filter((a) => a.status === "active").length;

  return (
    <Card className={className} sx={{ height }}>
      <CardContent
        sx={{ height: "100%", position: "relative", overflow: "hidden" }}
      >
        {/* Header */}
        <Box
          sx={{
            position: "absolute",
            top: 8,
            left: 16,
            right: 16,
            zIndex: 3,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <WorkflowIcon sx={{ fontSize: 18, color: "primary.main" }} />
            <Typography variant="subtitle2" fontWeight={600}>
              Workflow
            </Typography>
            <Chip
              label={`${activeCount}/${agents.length}`}
              size="small"
              color={activeCount > 0 ? "success" : "default"}
              sx={{ fontSize: "0.7rem", height: 20 }}
            />
          </Box>

          <Stack direction="row" spacing={0.5}>
            <Tooltip title="Refresh">
              <IconButton size="small" onClick={() => window.location.reload()}>
                <RefreshIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
            {onExpandClick && (
              <Tooltip title="Expand View">
                <IconButton size="small" onClick={onExpandClick}>
                  <ZoomInIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            )}
          </Stack>
        </Box>

        {/* Strategy indicator */}
        <Box sx={{ position: "absolute", bottom: 8, left: 16, zIndex: 3 }}>
          <Chip
            label={coordinationStrategy.replace(/_/g, " ")}
            size="small"
            variant="outlined"
            sx={{ fontSize: "0.7rem", height: 20 }}
          />
        </Box>

        {/* Render connections */}
        {layout.connections.map((conn, index) => (
          <ConnectionLine
            key={index}
            from={conn.from}
            to={conn.to}
            isActive={conn.isActive}
          />
        ))}

        {/* Orchestrator node (only for fan_out_synthesize) */}
        {coordinationStrategy === "fan_out_synthesize" && (
          <Box
            sx={{
              position: "absolute",
              left: layout.orchestratorPos.x,
              top: layout.orchestratorPos.y,
              transform: "translate(-50%, -50%)",
              zIndex: 2,
            }}
          >
            <Tooltip title="Lion Orchestrator">
              <Box
                sx={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: `radial-gradient(circle, ${
                    alpha(theme.palette.primary.main, 0.3)
                  }, ${alpha(theme.palette.primary.main, 0.1)})`,
                  border: `2px solid ${theme.palette.primary.main}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: `0 0 8px ${
                    alpha(theme.palette.primary.main, 0.3)
                  }`,
                }}
              >
                <WorkflowIcon sx={{ fontSize: 16, color: "primary.main" }} />
              </Box>
            </Tooltip>
          </Box>
        )}

        {/* Render agents */}
        {layout.agentPositions.map(({ agent, position, isActive }) => (
          <CompactAgentNode
            key={agent.id}
            agent={agent}
            isActive={isActive}
            position={position}
          />
        ))}

        {/* No agents message */}
        {agents.length === 0 && (
          <Box
            sx={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              textAlign: "center",
              color: "text.secondary",
            }}
          >
            <AgentIcon sx={{ fontSize: 32, opacity: 0.3, mb: 1 }} />
            <Typography variant="body2" fontSize="0.8rem">
              No agents active
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default AgentWorkflowMini;
