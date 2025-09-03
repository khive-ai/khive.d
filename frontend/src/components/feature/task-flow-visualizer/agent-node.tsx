/**
 * Agent Node - Custom ReactFlow node for individual agents
 * Shows agent status, current task, and recent activity
 */

import React from "react";
import { Handle, NodeProps, Position } from "reactflow";
import {
  Avatar,
  Box,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Typography,
} from "@mui/material";
import {
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  Pause as IdleIcon,
  Person as PersonIcon,
  PlayArrow as ActiveIcon,
  Psychology as BrainIcon,
  Schedule as ClockIcon,
} from "@mui/icons-material";
import { Agent, HookEvent } from "@/lib/types";

export interface AgentNodeData {
  agent: Agent;
  recentEvents?: HookEvent[];
  taskProgress?: number;
  estimatedCompletion?: string;
}

export const AgentNode: React.FC<NodeProps<AgentNodeData>> = ({
  data,
  selected,
}) => {
  const { agent, recentEvents = [], taskProgress = 0, estimatedCompletion } =
    data;

  // Get agent status configuration
  const getStatusConfig = (status: string) => {
    switch (status) {
      case "active":
        return {
          color: "#4caf50",
          bgColor: "#e8f5e8",
          icon: <ActiveIcon sx={{ fontSize: 14, color: "#4caf50" }} />,
          label: "Active",
        };
      case "idle":
        return {
          color: "#ff9800",
          bgColor: "#fff3e0",
          icon: <IdleIcon sx={{ fontSize: 14, color: "#ff9800" }} />,
          label: "Idle",
        };
      case "error":
        return {
          color: "#f44336",
          bgColor: "#ffebee",
          icon: <ErrorIcon sx={{ fontSize: 14, color: "#f44336" }} />,
          label: "Error",
        };
      default:
        return {
          color: "#9e9e9e",
          bgColor: "#f5f5f5",
          icon: <IdleIcon sx={{ fontSize: 14, color: "#9e9e9e" }} />,
          label: "Unknown",
        };
    }
  };

  // Get role-based avatar color
  const getRoleColor = (role: string) => {
    const roleColors = {
      researcher: "#1976d2",
      analyst: "#dc004e",
      architect: "#2e7d32",
      implementer: "#ed6c02",
      tester: "#9c27b0",
      reviewer: "#00acc1",
      critic: "#f57c00",
      commentator: "#5d4037",
    };

    return roleColors[role.toLowerCase() as keyof typeof roleColors] ||
      "#666666";
  };

  // Format task duration
  const formatDuration = (duration?: number) => {
    if (!duration) return "N/A";

    const minutes = Math.floor(duration / 60000);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    }
    return `${minutes}m`;
  };

  // Count recent activity (last 5 minutes)
  const getRecentActivityCount = () => {
    const fiveMinutesAgo = Date.now() - 300000;
    return recentEvents.filter(
      (event) => new Date(event.timestamp).getTime() > fiveMinutesAgo,
    ).length;
  };

  // Get the most recent event type
  const getLastActivity = () => {
    if (recentEvents.length === 0) return null;

    const lastEvent = recentEvents.sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    )[0];

    return {
      type: lastEvent.eventType,
      timestamp: lastEvent.timestamp,
    };
  };

  const statusConfig = getStatusConfig(agent.status);
  const roleColor = getRoleColor(agent.role);
  const recentActivityCount = getRecentActivityCount();
  const lastActivity = getLastActivity();

  return (
    <Card
      sx={{
        minWidth: 180,
        minHeight: 100,
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
      <CardContent sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}>
        {/* Header with agent info */}
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <Avatar
            sx={{
              width: 32,
              height: 32,
              bgcolor: roleColor,
              fontSize: "0.75rem",
              fontWeight: 600,
            }}
          >
            {agent.role.charAt(0).toUpperCase()}
          </Avatar>

          <Box flex={1} minWidth={0}>
            <Typography
              variant="body2"
              fontWeight={600}
              sx={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {agent.role}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                display: "block",
              }}
            >
              {agent.domain}
            </Typography>
          </Box>

          {statusConfig.icon}
        </Box>

        {/* Current task */}
        {agent.currentTask && (
          <Box mb={1}>
            <Typography
              variant="caption"
              sx={{
                display: "block",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: "100%",
                fontStyle: "italic",
                color: "text.secondary",
              }}
            >
              {agent.currentTask}
            </Typography>

            {/* Task progress for active agents */}
            {agent.status === "active" && taskProgress > 0 && (
              <LinearProgress
                variant="determinate"
                value={taskProgress}
                sx={{
                  height: 3,
                  borderRadius: 2,
                  mt: 0.5,
                  backgroundColor: "rgba(0,0,0,0.1)",
                  "& .MuiLinearProgress-bar": {
                    backgroundColor: statusConfig.color,
                  },
                }}
              />
            )}
          </Box>
        )}

        {/* Status and metadata */}
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Chip
            label={statusConfig.label}
            size="small"
            sx={{
              height: 18,
              fontSize: "0.65rem",
              backgroundColor: statusConfig.color,
              color: "white",
              "& .MuiChip-label": { px: 0.5 },
            }}
          />

          <Box display="flex" alignItems="center" gap={0.5}>
            {/* Duration */}
            {agent.duration && (
              <Box display="flex" alignItems="center" gap={0.25}>
                <ClockIcon sx={{ fontSize: 10, color: "text.secondary" }} />
                <Typography variant="caption" color="text.secondary">
                  {formatDuration(agent.duration)}
                </Typography>
              </Box>
            )}
          </Box>
        </Box>

        {/* Recent activity indicator */}
        {recentActivityCount > 0 && (
          <Box
            sx={{
              position: "absolute",
              top: 4,
              right: 4,
              minWidth: 16,
              height: 16,
              borderRadius: "50%",
              backgroundColor: "#ff5722",
              color: "white",
              fontSize: "0.6rem",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {recentActivityCount > 9 ? "9+" : recentActivityCount}
          </Box>
        )}

        {/* Last activity timestamp */}
        {lastActivity && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              position: "absolute",
              bottom: 4,
              right: 8,
              fontSize: "0.6rem",
            }}
          >
            {new Date(lastActivity.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </Typography>
        )}
      </CardContent>

      {/* ReactFlow handles */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: roleColor,
          width: 8,
          height: 8,
          border: "2px solid white",
        }}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: roleColor,
          width: 8,
          height: 8,
          border: "2px solid white",
        }}
      />
    </Card>
  );
};
