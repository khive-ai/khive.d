/**
 * Agent Activity Highlight - Real-time Agent Status Visualization
 *
 * Part of the Task Flow Visualizer MVP - provides visual highlighting and status
 * indicators for agent activities within workflow diagrams.
 *
 * @author commentator_agentic-systems
 * @version MVP
 */

"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  alpha,
  Avatar,
  Badge,
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  Menu,
  MenuItem,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useTheme,
  Zoom,
} from "@mui/material";
import {
  CheckCircle as CompleteIcon,
  Error as BlockedIcon,
  History as HistoryIcon,
  MoreVert as MoreIcon,
  Pause as IdleIcon,
  PlayArrow as ActiveIcon,
  Psychology as AgentIcon,
  Refresh as RefreshIcon,
  Schedule as PendingIcon,
  Speed as PerformanceIcon,
  Visibility as ViewIcon,
} from "@mui/icons-material";

import { useAgents, useCoordinationMetrics } from "@/lib/api/hooks";
import type { Agent, HookEvent } from "@/lib/types";

// Enhanced agent data for visualization
interface AgentActivityData extends Agent {
  progress?: number;
  lastActivity?: string;
  artifactsCreated?: number;
  timeActive?: number;
  efficiency?: number;
  recentEvents?: HookEvent[];
}

interface AgentActivityHighlightProps {
  className?: string;
  sessionId?: string;
  compact?: boolean;
  onAgentClick?: (agent: AgentActivityData) => void;
  highlightedAgents?: string[];
}

// Activity state configurations
const ACTIVITY_STATES = {
  active: {
    color: "#4caf50",
    icon: ActiveIcon,
    label: "Active",
    description: "Currently executing tasks",
    pulse: true,
  },
  idle: {
    color: "#ff9800",
    icon: IdleIcon,
    label: "Idle",
    description: "Waiting for task assignment",
    pulse: false,
  },
  blocked: {
    color: "#f44336",
    icon: BlockedIcon,
    label: "Blocked",
    description: "Blocked by dependencies",
    pulse: true,
  },
  completed: {
    color: "#2196f3",
    icon: CompleteIcon,
    label: "Completed",
    description: "Task completed successfully",
    pulse: false,
  },
} as const;

// Role-based color schemes
const ROLE_COLORS = {
  researcher: "#1976d2",
  analyst: "#388e3c",
  architect: "#7b1fa2",
  implementer: "#f57c00",
  reviewer: "#c2185b",
  tester: "#0097a7",
  critic: "#d32f2f",
  commentator: "#5e35b1",
  orchestrator: "#424242",
} as const;

export function AgentActivityHighlight({
  className,
  sessionId,
  compact = false,
  onAgentClick,
  highlightedAgents = [],
}: AgentActivityHighlightProps) {
  const theme = useTheme();
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [selectedAgent, setSelectedAgent] = useState<AgentActivityData | null>(
    null,
  );
  const [refreshing, setRefreshing] = useState(false);

  // API data
  const { data: agents, refetch: refetchAgents } = useAgents(sessionId);
  const { data: metrics } = useCoordinationMetrics();

  // Enhance agents with activity data (mock data for MVP)
  const enhancedAgents: AgentActivityData[] = useMemo(() => {
    if (!agents) return [];

    return agents.map((agent) => ({
      ...agent,
      progress: Math.floor(Math.random() * 100),
      lastActivity: new Date(Date.now() - Math.random() * 3600000)
        .toISOString(),
      artifactsCreated: Math.floor(Math.random() * 8),
      timeActive: Math.floor(Math.random() * 120), // minutes
      efficiency: 75 + Math.random() * 25, // 75-100%
      recentEvents: [], // Would be populated from real event data
    }));
  }, [agents]);

  // Auto-refresh functionality
  useEffect(() => {
    const interval = setInterval(() => {
      if (!refreshing) {
        setRefreshing(true);
        refetchAgents().finally(() => setRefreshing(false));
      }
    }, 15000); // Refresh every 15 seconds

    return () => clearInterval(interval);
  }, [refetchAgents, refreshing]);

  const handleAgentMenuClick = (
    event: React.MouseEvent<HTMLElement>,
    agent: AgentActivityData,
  ) => {
    event.stopPropagation();
    setSelectedAgent(agent);
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
    setSelectedAgent(null);
  };

  const handleAgentClick = (agent: AgentActivityData) => {
    if (onAgentClick) {
      onAgentClick(agent);
    }
  };

  const getActivityState = (status: Agent["status"]) => {
    switch (status) {
      case "active":
        return ACTIVITY_STATES.active;
      case "idle":
        return ACTIVITY_STATES.idle;
      case "error":
        return ACTIVITY_STATES.blocked;
      default:
        return ACTIVITY_STATES.idle;
    }
  };

  const getRoleColor = (role: string): string => {
    return ROLE_COLORS[role as keyof typeof ROLE_COLORS] ||
      theme.palette.primary.main;
  };

  const formatDuration = (minutes: number): string => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  // Pulse animation keyframes
  const pulseAnimation = `
    @keyframes pulse {
      0% { opacity: 1; }
      50% { opacity: 0.5; }
      100% { opacity: 1; }
    }
  `;

  if (compact) {
    return (
      <Card className={className}>
        <CardContent sx={{ pb: 2 }}>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              mb: 2,
            }}
          >
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Active Agents ({enhancedAgents.filter((a) =>
                a.status === "active"
              ).length})
            </Typography>
            <IconButton
              size="small"
              onClick={() => refetchAgents()}
              disabled={refreshing}
            >
              <RefreshIcon />
            </IconButton>
          </Box>

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {enhancedAgents.slice(0, 8).map((agent) => {
              const activityState = getActivityState(agent.status);
              const isHighlighted = highlightedAgents.includes(agent.id);

              return (
                <Tooltip
                  key={agent.id}
                  title={`${agent.role} - ${activityState.label}: ${
                    agent.currentTask || "No active task"
                  }`}
                  arrow
                  placement="top"
                >
                  <Badge
                    badgeContent={agent.artifactsCreated}
                    color="primary"
                    sx={{
                      "& .MuiBadge-badge": {
                        fontSize: "0.6rem",
                        minWidth: 16,
                        height: 16,
                      },
                    }}
                  >
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        bgcolor: getRoleColor(agent.role),
                        border: isHighlighted
                          ? `2px solid ${theme.palette.warning.main}`
                          : "none",
                        boxShadow: isHighlighted
                          ? theme.shadows[4]
                          : theme.shadows[1],
                        cursor: "pointer",
                        "&::after": activityState.pulse
                          ? {
                            content: '""',
                            position: "absolute",
                            top: -2,
                            right: -2,
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            backgroundColor: activityState.color,
                            animation: "pulse 2s infinite",
                          }
                          : {},
                      }}
                      onClick={() => handleAgentClick(agent)}
                    >
                      <style>{pulseAnimation}</style>
                      {agent.role.charAt(0).toUpperCase()}
                    </Avatar>
                  </Badge>
                </Tooltip>
              );
            })}
          </Stack>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box className={className}>
      {/* Header */}
      <Box
        sx={{
          mb: 3,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box>
          <Typography variant="h5" gutterBottom sx={{ fontWeight: 700 }}>
            Agent Activity Monitor
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Real-time status and performance tracking for all active agents
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Chip
            label={`${
              enhancedAgents.filter((a) => a.status === "active").length
            } Active`}
            color="success"
            size="small"
          />
          <Chip
            label={`${
              enhancedAgents.filter((a) => a.status === "idle").length
            } Idle`}
            color="warning"
            size="small"
          />
          <IconButton onClick={() => refetchAgents()} disabled={refreshing}>
            <RefreshIcon />
          </IconButton>
        </Stack>
      </Box>

      {/* Agent Activity Grid */}
      <Grid container spacing={2}>
        {enhancedAgents.map((agent) => {
          const activityState = getActivityState(agent.status);
          const isHighlighted = highlightedAgents.includes(agent.id);
          const roleColor = getRoleColor(agent.role);

          return (
            <Grid item xs={12} sm={6} md={4} lg={3} key={agent.id}>
              <Zoom in timeout={300}>
                <Card
                  sx={{
                    cursor: "pointer",
                    position: "relative",
                    border: isHighlighted
                      ? `2px solid ${theme.palette.warning.main}`
                      : `1px solid ${theme.palette.divider}`,
                    boxShadow: isHighlighted
                      ? theme.shadows[8]
                      : theme.shadows[1],
                    "&:hover": {
                      boxShadow: theme.shadows[4],
                      transform: "translateY(-2px)",
                    },
                    transition: theme.transitions.create([
                      "box-shadow",
                      "transform",
                    ], {
                      duration: theme.transitions.duration.short,
                    }),
                  }}
                  onClick={() => handleAgentClick(agent)}
                >
                  {/* Activity Status Indicator */}
                  <Box
                    sx={{
                      position: "absolute",
                      top: 8,
                      right: 8,
                      width: 12,
                      height: 12,
                      borderRadius: "50%",
                      bgcolor: activityState.color,
                      animation: activityState.pulse
                        ? "pulse 2s infinite"
                        : "none",
                    }}
                  />
                  <style>{pulseAnimation}</style>

                  <CardContent sx={{ pb: 2 }}>
                    {/* Agent Header */}
                    <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                      <Avatar
                        sx={{
                          width: 40,
                          height: 40,
                          bgcolor: roleColor,
                          mr: 2,
                        }}
                      >
                        {agent.role.charAt(0).toUpperCase()}
                      </Avatar>
                      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                        <Typography
                          variant="subtitle1"
                          sx={{ fontWeight: 600 }}
                          noWrap
                        >
                          {agent.role}
                        </Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          noWrap
                        >
                          {agent.domain}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={(e) => handleAgentMenuClick(e, agent)}
                      >
                        <MoreIcon />
                      </IconButton>
                    </Box>

                    {/* Status and Current Task */}
                    <Box sx={{ mb: 2 }}>
                      <Box
                        sx={{ display: "flex", alignItems: "center", mb: 1 }}
                      >
                        {React.createElement(activityState.icon, {
                          sx: {
                            color: activityState.color,
                            fontSize: 16,
                            mr: 1,
                          },
                        })}
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {activityState.label}
                        </Typography>
                      </Box>
                      {agent.currentTask && (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{
                            fontSize: "0.8rem",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                          }}
                        >
                          {agent.currentTask}
                        </Typography>
                      )}
                    </Box>

                    {/* Progress Bar (for active agents) */}
                    {agent.status === "active" &&
                      agent.progress !== undefined && (
                      <Box sx={{ mb: 2 }}>
                        <Box
                          sx={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            mb: 0.5,
                          }}
                        >
                          <Typography variant="caption" color="text.secondary">
                            Progress
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {agent.progress}%
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={agent.progress}
                          sx={{
                            height: 4,
                            borderRadius: 2,
                            bgcolor: alpha(roleColor, 0.1),
                            "& .MuiLinearProgress-bar": {
                              bgcolor: roleColor,
                            },
                          }}
                        />
                      </Box>
                    )}

                    {/* Performance Metrics */}
                    <Grid container spacing={1}>
                      <Grid item xs={4}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                        >
                          Artifacts
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {agent.artifactsCreated || 0}
                        </Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                        >
                          Active
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {formatDuration(agent.timeActive || 0)}
                        </Typography>
                      </Grid>
                      <Grid item xs={4}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                        >
                          Efficiency
                        </Typography>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 600,
                            color: theme.palette.success.main,
                          }}
                        >
                          {Math.round(agent.efficiency || 0)}%
                        </Typography>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Zoom>
            </Grid>
          );
        })}
      </Grid>

      {/* Agent Context Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={handleMenuClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
      >
        <MenuItem onClick={handleMenuClose}>
          <ViewIcon sx={{ mr: 1 }} />
          View Details
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <HistoryIcon sx={{ mr: 1 }} />
          View History
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <PerformanceIcon sx={{ mr: 1 }} />
          Performance Metrics
        </MenuItem>
      </Menu>

      {/* Empty State */}
      {enhancedAgents.length === 0 && (
        <Paper
          sx={{
            p: 4,
            textAlign: "center",
            bgcolor: alpha(theme.palette.primary.main, 0.05),
          }}
        >
          <AgentIcon
            sx={{ fontSize: 48, color: theme.palette.primary.main, mb: 2 }}
          />
          <Typography variant="h6" gutterBottom>
            No Active Agents
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Spawn agents from the Orchestration Center to see them here
          </Typography>
        </Paper>
      )}
    </Box>
  );
}

// Utility functions for external use
export function getAgentActivityColor(status: Agent["status"]): string {
  return ACTIVITY_STATES[status === "error" ? "blocked" : status]?.color ||
    ACTIVITY_STATES.idle.color;
}

export function getAgentRoleColor(role: string): string {
  return ROLE_COLORS[role as keyof typeof ROLE_COLORS] || "#1976d2";
}

export function formatAgentDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}
