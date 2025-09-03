/**
 * Task Node - Custom ReactFlow node for individual tasks
 * Shows task details, progress, and assigned agent
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
  Person as PersonIcon,
  PlayArrow as RunningIcon,
  Schedule as PendingIcon,
  Task as TaskIcon,
} from "@mui/icons-material";

export interface TaskNodeData {
  taskName: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  progress: number;
  assignedAgent?: string;
  agentRole?: string;
  priority: "low" | "medium" | "high" | "critical";
  estimatedDuration?: string;
  artifacts?: string[];
  description?: string;
}

export const TaskNode: React.FC<NodeProps<TaskNodeData>> = ({
  data,
  selected,
}) => {
  const {
    taskName,
    status,
    progress,
    assignedAgent,
    agentRole,
    priority,
    estimatedDuration,
    artifacts = [],
    description,
  } = data;

  // Get status configuration
  const getStatusConfig = (status: string) => {
    switch (status) {
      case "completed":
        return {
          color: "#4caf50",
          bgColor: "#e8f5e8",
          icon: <CompleteIcon sx={{ fontSize: 14, color: "#4caf50" }} />,
          label: "Done",
        };
      case "in_progress":
        return {
          color: "#2196f3",
          bgColor: "#e3f2fd",
          icon: <RunningIcon sx={{ fontSize: 14, color: "#2196f3" }} />,
          label: "In Progress",
        };
      case "failed":
        return {
          color: "#f44336",
          bgColor: "#ffebee",
          icon: <ErrorIcon sx={{ fontSize: 14, color: "#f44336" }} />,
          label: "Failed",
        };
      case "pending":
      default:
        return {
          color: "#ff9800",
          bgColor: "#fff3e0",
          icon: <PendingIcon sx={{ fontSize: 14, color: "#ff9800" }} />,
          label: "Pending",
        };
    }
  };

  // Get priority configuration
  const getPriorityConfig = (priority: string) => {
    switch (priority) {
      case "critical":
        return { color: "error" as const, label: "Critical" };
      case "high":
        return { color: "warning" as const, label: "High" };
      case "medium":
        return { color: "primary" as const, label: "Medium" };
      case "low":
      default:
        return { color: "default" as const, label: "Low" };
    }
  };

  // Get role-based avatar color
  const getRoleColor = (role?: string) => {
    if (!role) return "#9e9e9e";

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

  const statusConfig = getStatusConfig(status);
  const priorityConfig = getPriorityConfig(priority);
  const roleColor = getRoleColor(agentRole);

  return (
    <Card
      sx={{
        minWidth: 160,
        minHeight: 80,
        border: selected ? "2px solid #1976d2" : "1px solid #e0e0e0",
        borderRadius: 1.5,
        backgroundColor: statusConfig.bgColor,
        transition: "all 0.2s ease-in-out",
        position: "relative",
        "&:hover": {
          transform: "translateY(-1px)",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        },
      }}
    >
      <CardContent sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}>
        {/* Header with task name and status */}
        <Box display="flex" alignItems="flex-start" gap={1} mb={1}>
          <TaskIcon sx={{ fontSize: 14, color: "text.secondary", mt: 0.25 }} />

          <Box flex={1} minWidth={0}>
            <Typography
              variant="body2"
              fontWeight={500}
              sx={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                lineHeight: 1.2,
              }}
            >
              {taskName}
            </Typography>

            {description && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  display: "block",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                  mt: 0.25,
                }}
              >
                {description}
              </Typography>
            )}
          </Box>

          {statusConfig.icon}
        </Box>

        {/* Progress bar */}
        {status === "in_progress" && progress > 0 && (
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 3,
              borderRadius: 2,
              mb: 1,
              backgroundColor: "rgba(0,0,0,0.1)",
              "& .MuiLinearProgress-bar": {
                backgroundColor: statusConfig.color,
              },
            }}
          />
        )}

        {/* Bottom row with priority, agent, and metadata */}
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={0.5}>
            {/* Priority */}
            <Chip
              label={priorityConfig.label}
              size="small"
              color={priorityConfig.color}
              variant="outlined"
              sx={{
                height: 16,
                fontSize: "0.6rem",
                "& .MuiChip-label": { px: 0.5 },
              }}
            />

            {/* Assigned agent */}
            {assignedAgent && agentRole && (
              <Avatar
                sx={{
                  width: 16,
                  height: 16,
                  bgcolor: roleColor,
                  fontSize: "0.6rem",
                  fontWeight: 600,
                }}
              >
                {agentRole.charAt(0).toUpperCase()}
              </Avatar>
            )}
          </Box>

          {/* Progress percentage for active tasks */}
          {status === "in_progress" && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ fontSize: "0.65rem" }}
            >
              {progress}%
            </Typography>
          )}

          {/* Artifact count */}
          {artifacts.length > 0 && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ fontSize: "0.65rem" }}
            >
              {artifacts.length} file{artifacts.length !== 1 ? "s" : ""}
            </Typography>
          )}
        </Box>

        {/* Estimated duration */}
        {estimatedDuration && status !== "completed" && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              position: "absolute",
              bottom: 2,
              right: 6,
              fontSize: "0.6rem",
            }}
          >
            ~{estimatedDuration}
          </Typography>
        )}

        {/* High priority indicator */}
        {(priority === "critical" || priority === "high") && (
          <Box
            sx={{
              position: "absolute",
              top: 2,
              right: 2,
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: priority === "critical" ? "#f44336" : "#ff9800",
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
          width: 6,
          height: 6,
          border: "1px solid white",
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: statusConfig.color,
          width: 6,
          height: 6,
          border: "1px solid white",
        }}
      />
    </Card>
  );
};
