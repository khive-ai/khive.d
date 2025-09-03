/**
 * Agent Status Component
 * Displays individual agent information and current status
 */

import React from "react";
import {
  Avatar,
  Box,
  Chip,
  IconButton,
  LinearProgress,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Info as InfoIcon,
  Person as PersonIcon,
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  Stop as StopIcon,
} from "@mui/icons-material";
import { Card, CardContent, CardHeader, StatusBadge } from "@/ui";
import { Agent } from "@/types";
import { camelCaseToReadable, capitalize, formatDuration } from "@/lib/utils";

export interface AgentStatusProps {
  agent: Agent;
  onStop?: (agentId: string) => void;
  onRestart?: (agentId: string) => void;
  onViewDetails?: (agentId: string) => void;
  className?: string;
}

export const AgentStatus: React.FC<AgentStatusProps> = ({
  agent,
  onStop,
  onRestart,
  onViewDetails,
  className,
}) => {
  const getAvatarColor = (role: string) => {
    // Generate consistent colors based on role
    const colors = [
      "#1976d2",
      "#dc004e",
      "#2e7d32",
      "#ed6c02",
      "#9c27b0",
      "#00acc1",
      "#f57c00",
      "#5d4037",
    ];
    const index = role.charCodeAt(0) % colors.length;
    return colors[index];
  };

  const getStatusIcon = (status: Agent["status"]) => {
    switch (status) {
      case "active":
        return "🟢";
      case "idle":
        return "🟡";
      case "error":
        return "🔴";
      default:
        return "⚪";
    }
  };

  const getTaskProgress = () => {
    if (!agent.duration || !agent.currentTask) return 0;
    // Mock progress calculation based on duration
    // In reality, this would come from the agent's actual progress
    return Math.min((agent.duration / 60000) * 10, 90); // Assume task takes ~6 minutes
  };

  const actions = (
    <Box display="flex" alignItems="center" gap={1}>
      <Tooltip title="View Details">
        <IconButton
          size="small"
          onClick={() => onViewDetails?.(agent.id)}
        >
          <InfoIcon />
        </IconButton>
      </Tooltip>

      {agent.status === "active" && (
        <Tooltip title="Stop Agent">
          <IconButton
            size="small"
            onClick={() => onStop?.(agent.id)}
            color="error"
          >
            <StopIcon />
          </IconButton>
        </Tooltip>
      )}

      {(agent.status === "idle" || agent.status === "error") && (
        <Tooltip title="Restart Agent">
          <IconButton
            size="small"
            onClick={() => onRestart?.(agent.id)}
            color="primary"
          >
            <PlayIcon />
          </IconButton>
        </Tooltip>
      )}

      <Tooltip title="Refresh">
        <IconButton size="small">
          <RefreshIcon />
        </IconButton>
      </Tooltip>
    </Box>
  );

  return (
    <Card className={className} variant="outlined">
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={2}>
            <Avatar
              sx={{
                width: 32,
                height: 32,
                bgcolor: getAvatarColor(agent.role),
                fontSize: "0.875rem",
                fontWeight: 600,
              }}
            >
              {agent.role.charAt(0).toUpperCase()}
            </Avatar>
            <Box>
              <Typography variant="subtitle1" fontWeight={600}>
                {camelCaseToReadable(agent.role)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {agent.domain}
              </Typography>
            </Box>
            <StatusBadge status={agent.status} />
          </Box>
        }
        subtitle={
          <Typography variant="caption" color="text.secondary">
            ID: {agent.id.slice(-8)}
          </Typography>
        }
        action={actions}
      />

      <CardContent>
        <Box display="flex" flexDirection="column" gap={2}>
          {/* Current Task */}
          {agent.currentTask && (
            <Box>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                gutterBottom
              >
                Current Task
              </Typography>
              <Typography variant="body2" mb={1}>
                {agent.currentTask}
              </Typography>

              {agent.status === "active" && (
                <Box>
                  <Box
                    display="flex"
                    justifyContent="between"
                    alignItems="center"
                    mb={0.5}
                  >
                    <Typography variant="caption" color="text.secondary">
                      Progress
                    </Typography>
                    <Typography variant="caption">
                      {getTaskProgress().toFixed(0)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={getTaskProgress()}
                    sx={{ height: 6, borderRadius: 3 }}
                  />
                </Box>
              )}
            </Box>
          )}

          {/* Agent Metrics */}
          <Box display="flex" flexWrap="wrap" gap={1} alignItems="center">
            {agent.duration && (
              <Chip
                label={`Active: ${formatDuration(agent.duration)}`}
                size="small"
                variant="outlined"
              />
            )}

            <Chip
              label={`Session: ${agent.sessionId.slice(-6)}`}
              size="small"
              variant="outlined"
            />

            <Box display="flex" alignItems="center" gap={0.5}>
              <Typography variant="caption">
                {getStatusIcon(agent.status)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {capitalize(agent.status)}
              </Typography>
            </Box>
          </Box>

          {/* Error State */}
          {agent.status === "error" && (
            <Box
              sx={{
                backgroundColor: "error.light",
                p: 1.5,
                borderRadius: 1,
                border: "1px solid",
                borderColor: "error.main",
              }}
            >
              <Typography variant="body2" color="error.dark">
                ⚠️ Agent encountered an error and requires attention
              </Typography>
            </Box>
          )}

          {/* Idle State */}
          {agent.status === "idle" && !agent.currentTask && (
            <Box
              sx={{
                backgroundColor: "warning.light",
                p: 1.5,
                borderRadius: 1,
                border: "1px solid",
                borderColor: "warning.main",
              }}
            >
              <Typography variant="body2" color="warning.dark">
                💤 Agent is idle and waiting for tasks
              </Typography>
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};
