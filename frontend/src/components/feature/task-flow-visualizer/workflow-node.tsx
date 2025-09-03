/**
 * Workflow Node - Custom ReactFlow node for plan phases
 * Shows phase details, agent assignments, and activity highlighting
 */

import React from "react";
import { Handle, NodeProps, Position } from "reactflow";
import {
  Avatar,
  AvatarGroup,
  Box,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Typography,
} from "@mui/material";
import {
  AccountTree as PhaseIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  PlayArrow as RunningIcon,
  Schedule as PendingIcon,
} from "@mui/icons-material";
import { Agent, HookEvent } from "@/lib/types";

export interface WorkflowNodeData {
  phase: string;
  status: "pending" | "running" | "completed" | "failed";
  agents: string[];
  tasks: string[];
  coordinationStrategy: "FAN_OUT_SYNTHESIZE" | "PIPELINE" | "PARALLEL";
  expectedArtifacts: string[];
  activeAgents?: Agent[];
  recentEvents?: HookEvent[];
}

export const WorkflowNode: React.FC<NodeProps<WorkflowNodeData>> = ({
  data,
  selected,
}) => {
  const {
    phase,
    status,
    agents,
    tasks,
    coordinationStrategy,
    activeAgents = [],
    recentEvents = [],
  } = data;

  // Get status configuration
  const getStatusConfig = (status: string) => {
    switch (status) {
      case "completed":
        return {
          color: "#4caf50",
          bgColor: "#e8f5e8",
          icon: <CompleteIcon sx={{ fontSize: 16, color: "#4caf50" }} />,
          label: "Completed",
        };
      case "running":
        return {
          color: "#2196f3",
          bgColor: "#e3f2fd",
          icon: <RunningIcon sx={{ fontSize: 16, color: "#2196f3" }} />,
          label: "Running",
        };
      case "failed":
        return {
          color: "#f44336",
          bgColor: "#ffebee",
          icon: <ErrorIcon sx={{ fontSize: 16, color: "#f44336" }} />,
          label: "Failed",
        };
      case "pending":
      default:
        return {
          color: "#ff9800",
          bgColor: "#fff3e0",
          icon: <PendingIcon sx={{ fontSize: 16, color: "#ff9800" }} />,
          label: "Pending",
        };
    }
  };

  // Get coordination strategy configuration
  const getStrategyConfig = (strategy: string) => {
    switch (strategy) {
      case "FAN_OUT_SYNTHESIZE":
        return { label: "Fan-Out", color: "primary" as const };
      case "PIPELINE":
        return { label: "Pipeline", color: "secondary" as const };
      case "PARALLEL":
        return { label: "Parallel", color: "success" as const };
      default:
        return { label: strategy, color: "default" as const };
    }
  };

  // Calculate progress based on status and active events
  const getProgressValue = () => {
    if (status === "completed") return 100;
    if (status === "pending") return 0;
    if (status === "failed") return 0;

    // For running status, estimate progress based on recent activity
    const recentActivityCount = recentEvents.filter(
      (event) => new Date(event.timestamp).getTime() > Date.now() - 300000, // Last 5 minutes
    ).length;

    return Math.min(25 + recentActivityCount * 15, 90); // 25-90% for running tasks
  };

  // Generate agent avatars
  const getAgentAvatars = () => {
    const agentColors = [
      "#1976d2",
      "#dc004e",
      "#2e7d32",
      "#ed6c02",
      "#9c27b0",
      "#00acc1",
      "#f57c00",
      "#5d4037",
    ];

    return agents.map((agentId) => {
      const agent = activeAgents.find((a) => a.id === agentId);
      const colorIndex = agentId.charCodeAt(0) % agentColors.length;
      const isActive = agent?.status === "active";

      return (
        <Avatar
          key={agentId}
          sx={{
            width: 24,
            height: 24,
            fontSize: "0.65rem",
            fontWeight: 600,
            bgcolor: isActive ? agentColors[colorIndex] : "#bdbdbd",
            border: isActive ? "2px solid #4caf50" : "1px solid #e0e0e0",
            transition: "all 0.2s ease-in-out",
          }}
        >
          {(agent?.role?.charAt(0) || agentId.charAt(0)).toUpperCase()}
        </Avatar>
      );
    });
  };

  const statusConfig = getStatusConfig(status);
  const strategyConfig = getStrategyConfig(coordinationStrategy);
  const progressValue = getProgressValue();

  return (
    <Card
      sx={{
        minWidth: 200,
        minHeight: 120,
        border: selected ? "2px solid #1976d2" : "1px solid #e0e0e0",
        borderRadius: 2,
        backgroundColor: statusConfig.bgColor,
        transition: "all 0.2s ease-in-out",
        position: "relative",
        "&:hover": {
          transform: "translateY(-1px)",
          boxShadow: "0 4px 8px rgba(0,0,0,0.12)",
        },
      }}
    >
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
        {/* Header with phase name and status */}
        <Box
          display="flex"
          alignItems="center"
          justifyContent="space-between"
          mb={1.5}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <PhaseIcon sx={{ fontSize: 16, color: "text.secondary" }} />
            <Typography
              variant="body1"
              fontWeight={600}
              sx={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: 120,
              }}
            >
              {phase}
            </Typography>
          </Box>
          {statusConfig.icon}
        </Box>

        {/* Progress bar for running tasks */}
        {status === "running" && (
          <LinearProgress
            variant="determinate"
            value={progressValue}
            sx={{
              height: 4,
              borderRadius: 2,
              mb: 1.5,
              backgroundColor: "rgba(0,0,0,0.1)",
              "& .MuiLinearProgress-bar": {
                backgroundColor: statusConfig.color,
              },
            }}
          />
        )}

        {/* Coordination strategy */}
        <Chip
          label={strategyConfig.label}
          size="small"
          color={strategyConfig.color}
          variant="outlined"
          sx={{ mb: 1.5, fontSize: "0.7rem", height: 20 }}
        />

        {/* Agent avatars */}
        {agents.length > 0 && (
          <Box
            display="flex"
            alignItems="center"
            justifyContent="space-between"
          >
            <AvatarGroup
              max={4}
              sx={{
                "& .MuiAvatar-root": { width: 24, height: 24 },
                "& .MuiAvatarGroup-avatar": { fontSize: "0.65rem" },
              }}
            >
              {getAgentAvatars()}
            </AvatarGroup>

            {/* Task count */}
            <Typography variant="caption" color="text.secondary">
              {tasks.length} task{tasks.length !== 1 ? "s" : ""}
            </Typography>
          </Box>
        )}

        {/* Activity indicator */}
        {recentEvents.length > 0 && (
          <Box
            sx={{
              position: "absolute",
              top: 8,
              right: 8,
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: "#4caf50",
              animation: "pulse 2s infinite",
              "@keyframes pulse": {
                "0%": { opacity: 1 },
                "50%": { opacity: 0.3 },
                "100%": { opacity: 1 },
              },
            }}
          />
        )}
      </CardContent>

      {/* ReactFlow handles */}
      <Handle
        type="target"
        position={Position.Top}
        style={{
          background: statusConfig.color,
          width: 10,
          height: 10,
          border: "2px solid white",
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: statusConfig.color,
          width: 10,
          height: 10,
          border: "2px solid white",
        }}
      />
    </Card>
  );
};
