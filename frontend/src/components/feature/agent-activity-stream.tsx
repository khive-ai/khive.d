/**
 * Agent Activity Stream Component
 * Real-time display of agent coordination activities and events
 */

import React, { useEffect, useState } from "react";
import {
  Avatar,
  Box,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  Typography,
} from "@mui/material";
import {
  Cancel as CancelIcon,
  CheckCircle as CheckCircleIcon,
  Edit as EditIcon,
  Person as PersonIcon,
  Task as TaskIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import { Card, CardContent, CardHeader } from "@/components/ui";
import { Agent, HookEvent } from "@/lib/types";

export interface AgentActivityStreamProps {
  events: HookEvent[];
  agents: Agent[];
  maxEvents?: number;
  autoRefresh?: boolean;
  className?: string;
}

export const AgentActivityStream: React.FC<AgentActivityStreamProps> = ({
  events,
  agents,
  maxEvents = 50,
  autoRefresh = true,
  className,
}) => {
  const [displayEvents, setDisplayEvents] = useState<HookEvent[]>([]);

  useEffect(() => {
    // Sort events by timestamp (most recent first) and limit display count
    const sortedEvents = [...events]
      .sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )
      .slice(0, maxEvents);

    setDisplayEvents(sortedEvents);
  }, [events, maxEvents]);

  const getAgentInfo = (agentId: string) => {
    return agents.find((agent) => agent.id === agentId);
  };

  const getEventIcon = (eventType: HookEvent["eventType"]) => {
    switch (eventType) {
      case "pre_command":
      case "post_command":
        return <TaskIcon color="primary" />;
      case "pre_edit":
      case "post_edit":
        return <EditIcon color="secondary" />;
      case "pre_agent_spawn":
      case "post_agent_spawn":
        return <PersonIcon color="success" />;
      default:
        return <CheckCircleIcon color="action" />;
    }
  };

  const getEventColor = (eventType: HookEvent["eventType"]) => {
    switch (eventType) {
      case "pre_command":
        return "info";
      case "post_command":
        return "success";
      case "pre_edit":
        return "warning";
      case "post_edit":
        return "success";
      case "pre_agent_spawn":
        return "info";
      case "post_agent_spawn":
        return "success";
      default:
        return "default";
    }
  };

  const formatEventDescription = (event: HookEvent) => {
    const agent = getAgentInfo(event.agentId);
    const agentName = agent
      ? `${agent.role}+${agent.domain}`
      : event.agentId.slice(-8);

    switch (event.eventType) {
      case "pre_command":
        return `${agentName} starting command: ${
          event.command?.slice(0, 60) || "Unknown"
        }${event.command && event.command.length > 60 ? "..." : ""}`;
      case "post_command":
        return `${agentName} completed command: ${
          event.command?.slice(0, 60) || "Unknown"
        }${event.command && event.command.length > 60 ? "..." : ""}`;
      case "pre_edit":
        return `${agentName} acquiring lock on: ${
          event.filePath?.split("/").pop() || "file"
        }`;
      case "post_edit":
        return `${agentName} released lock on: ${
          event.filePath?.split("/").pop() || "file"
        }`;
      case "pre_agent_spawn":
        return `${agentName} spawning new agent`;
      case "post_agent_spawn":
        return `${agentName} successfully spawned agent`;
      default:
        return `${agentName} performed ${event.eventType}`;
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) return "just now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}h ago`;
    return date.toLocaleDateString();
  };

  const getAvatarProps = (agentId: string) => {
    const agent = getAgentInfo(agentId);
    if (!agent) {
      return {
        sx: { width: 32, height: 32, bgcolor: "#666", fontSize: "0.75rem" },
        children: agentId.slice(-2).toUpperCase(),
      };
    }

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
    const colorIndex = agent.role.charCodeAt(0) % colors.length;

    return {
      sx: {
        width: 32,
        height: 32,
        bgcolor: colors[colorIndex],
        fontSize: "0.75rem",
        fontWeight: 600,
      },
      children: agent.role.charAt(0).toUpperCase(),
    };
  };

  return (
    <Card className={className} variant="outlined">
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="h6" component="h3">
              Agent Activity Stream
            </Typography>
            <Chip
              label={`${displayEvents.length} events`}
              size="small"
              color="primary"
              variant="outlined"
            />
            {autoRefresh && (
              <Chip
                label="Live"
                size="small"
                color="success"
                variant="filled"
              />
            )}
          </Box>
        }
        subtitle={
          <Typography variant="body2" color="text.secondary">
            Real-time coordination activity from all agents
          </Typography>
        }
      />

      <CardContent sx={{ p: 0, maxHeight: 600, overflow: "auto" }}>
        {displayEvents.length === 0
          ? (
            <Box p={3} textAlign="center">
              <Typography variant="body2" color="text.secondary">
                No recent activity to display
              </Typography>
            </Box>
          )
          : (
            <List dense>
              {displayEvents.map((event, index) => (
                <React.Fragment key={event.id}>
                  <ListItem sx={{ py: 1.5, px: 2 }}>
                    <Box
                      display="flex"
                      alignItems="flex-start"
                      gap={2}
                      width="100%"
                    >
                      <Avatar {...getAvatarProps(event.agentId)} />

                      <Box flex={1} minWidth={0}>
                        <Box
                          display="flex"
                          alignItems="center"
                          gap={1}
                          mb={0.5}
                        >
                          {getEventIcon(event.eventType)}
                          <Chip
                            label={event.eventType.replace("_", " ")}
                            size="small"
                            color={getEventColor(event.eventType) as any}
                            variant="outlined"
                            sx={{ textTransform: "capitalize" }}
                          />
                          <Typography variant="caption" color="text.secondary">
                            {formatTimestamp(event.timestamp)}
                          </Typography>
                        </Box>

                        <Typography
                          variant="body2"
                          sx={{ wordBreak: "break-word" }}
                        >
                          {formatEventDescription(event)}
                        </Typography>

                        {event.filePath && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{
                              display: "block",
                              mt: 0.5,
                              fontFamily: "monospace",
                              backgroundColor: "grey.50",
                              px: 1,
                              py: 0.5,
                              borderRadius: 0.5,
                              wordBreak: "break-all",
                            }}
                          >
                            {event.filePath}
                          </Typography>
                        )}

                        {event.metadata &&
                          Object.keys(event.metadata).length > 0 && (
                          <Box
                            display="flex"
                            flexWrap="wrap"
                            gap={0.5}
                            mt={0.5}
                          >
                            {Object.entries(event.metadata).slice(0, 3).map((
                              [key, value],
                            ) => (
                              <Chip
                                key={key}
                                label={`${key}: ${String(value).slice(0, 20)}`}
                                size="small"
                                variant="outlined"
                                sx={{ height: 20, fontSize: "0.65rem" }}
                              />
                            ))}
                          </Box>
                        )}
                      </Box>
                    </Box>
                  </ListItem>

                  {index < displayEvents.length - 1 && (
                    <Divider variant="inset" component="li" />
                  )}
                </React.Fragment>
              ))}
            </List>
          )}
      </CardContent>
    </Card>
  );
};
