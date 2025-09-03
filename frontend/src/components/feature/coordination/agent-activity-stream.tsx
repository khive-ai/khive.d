/**
 * Agent Activity Stream Component
 * Real-time feed of agent events and actions for coordination monitoring
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  alpha,
  Avatar,
  Badge,
  Box,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Stack,
  Switch,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as CompleteIcon,
  Edit as EditIcon,
  Error as ErrorIcon,
  FilterList as FilterIcon,
  Info as InfoIcon,
  MoreVert as MoreIcon,
  PlayArrow as StartIcon,
  Psychology as AgentIcon,
  Task as TaskIcon,
  Timeline as ActivityIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import { formatDistanceToNow } from "date-fns";
import { Agent, HookEvent } from "@/lib/types";

export interface AgentActivityStreamProps {
  events: HookEvent[];
  agents: Agent[];
  isLoading?: boolean;
  isRealTime?: boolean;
  maxItems?: number;
  showFilters?: boolean;
}

interface ActivityItem {
  id: string;
  agentId: string;
  agentRole?: string;
  eventType: string;
  timestamp: string;
  description: string;
  filePath?: string;
  command?: string;
  priority: "low" | "medium" | "high";
  status: "success" | "warning" | "error" | "info";
}

const EVENT_TYPE_CONFIG = {
  pre_command: {
    icon: StartIcon,
    color: "primary",
    priority: "medium" as const,
    status: "info" as const,
    description: (metadata: any) =>
      `Starting command: ${metadata.command || "unknown"}`,
  },
  post_command: {
    icon: CompleteIcon,
    color: "success",
    priority: "low" as const,
    status: "success" as const,
    description: (metadata: any) =>
      `Completed command: ${metadata.command || "unknown"}`,
  },
  pre_edit: {
    icon: EditIcon,
    color: "warning",
    priority: "high" as const,
    status: "warning" as const,
    description: (metadata: any, filePath?: string) =>
      `Editing file: ${filePath ? filePath.split("/").pop() : "unknown"}`,
  },
  post_edit: {
    icon: EditIcon,
    color: "success",
    priority: "medium" as const,
    status: "success" as const,
    description: (metadata: any, filePath?: string) =>
      `Saved file: ${filePath ? filePath.split("/").pop() : "unknown"}`,
  },
  pre_agent_spawn: {
    icon: AgentIcon,
    color: "secondary",
    priority: "high" as const,
    status: "info" as const,
    description: (metadata: any) =>
      `Spawning new agent: ${metadata.role || "unknown"}`,
  },
  post_agent_spawn: {
    icon: AgentIcon,
    color: "success",
    priority: "medium" as const,
    status: "success" as const,
    description: (metadata: any) =>
      `Agent spawned: ${metadata.role || "unknown"}`,
  },
} as const;

export const AgentActivityStream: React.FC<AgentActivityStreamProps> = ({
  events,
  agents,
  isLoading = false,
  isRealTime = true,
  maxItems = 50,
  showFilters = true,
}) => {
  const theme = useTheme();
  const [filterMenuAnchor, setFilterMenuAnchor] = useState<null | HTMLElement>(
    null,
  );
  const [eventTypeFilter, setEventTypeFilter] = useState<string[]>([]);
  const [agentFilter, setAgentFilter] = useState<string[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);

  // Transform events into activity items
  const activityItems = useMemo((): ActivityItem[] => {
    const items = events
      .map((event): ActivityItem => {
        const config = EVENT_TYPE_CONFIG[event.eventType] || {
          icon: InfoIcon,
          color: "default",
          priority: "low" as const,
          status: "info" as const,
          description: () => `Event: ${event.eventType}`,
        };

        const agent = agents.find((a) => a.id === event.agentId);

        return {
          id: event.id,
          agentId: event.agentId,
          agentRole: agent ? `${agent.role}+${agent.domain}` : "unknown",
          eventType: event.eventType,
          timestamp: event.timestamp,
          description: config.description(event.metadata, event.filePath),
          filePath: event.filePath,
          command: event.command,
          priority: config.priority,
          status: config.status,
        };
      })
      .filter((item) => {
        if (
          eventTypeFilter.length > 0 &&
          !eventTypeFilter.includes(item.eventType)
        ) {
          return false;
        }
        if (agentFilter.length > 0 && !agentFilter.includes(item.agentId)) {
          return false;
        }
        return true;
      })
      .sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )
      .slice(0, maxItems);

    return items;
  }, [events, agents, eventTypeFilter, agentFilter, maxItems]);

  const getEventIcon = (eventType: string) => {
    const config =
      EVENT_TYPE_CONFIG[eventType as keyof typeof EVENT_TYPE_CONFIG];
    return config?.icon || InfoIcon;
  };

  const getEventColor = (eventType: string) => {
    const config =
      EVENT_TYPE_CONFIG[eventType as keyof typeof EVENT_TYPE_CONFIG];
    return config?.color || "default";
  };

  const getAgentAvatarColor = (agentId: string) => {
    // Generate consistent color based on agent ID
    const colors = ["primary", "secondary", "success", "warning", "info"];
    const hash = agentId.split("").reduce(
      (acc, char) => acc + char.charCodeAt(0),
      0,
    );
    return colors[hash % colors.length];
  };

  const getPriorityBadgeColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "error";
      case "medium":
        return "warning";
      case "low":
        return "success";
      default:
        return "default";
    }
  };

  const handleFilterClick = (event: React.MouseEvent<HTMLElement>) => {
    setFilterMenuAnchor(event.currentTarget);
  };

  const handleFilterClose = () => {
    setFilterMenuAnchor(null);
  };

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        height={400}
      >
        <Stack spacing={2} alignItems="center">
          <CircularProgress />
          <Typography variant="body2" color="text.secondary">
            Loading activity stream...
          </Typography>
        </Stack>
      </Box>
    );
  }

  if (activityItems.length === 0) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        height={400}
        color="text.secondary"
      >
        <ActivityIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
        <Typography variant="h6" gutterBottom>
          No activity detected
        </Typography>
        <Typography variant="body2" textAlign="center">
          {isRealTime
            ? "Monitoring for agent coordination events..."
            : "Enable real-time monitoring to see live activity"}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Activity Stream Header Controls */}
      {showFilters && (
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
        >
          <Stack direction="row" spacing={1}>
            <Badge badgeContent={activityItems.length} color="primary">
              <Chip
                label="Live Activity"
                color={isRealTime ? "success" : "default"}
                size="small"
              />
            </Badge>
          </Stack>

          <Stack direction="row" spacing={1} alignItems="center">
            <FormControlLabel
              control={
                <Switch
                  size="small"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                />
              }
              label="Auto-scroll"
              sx={{
                m: 0,
                "& .MuiFormControlLabel-label": { fontSize: "0.875rem" },
              }}
            />
            <Tooltip title="Filter Events">
              <IconButton size="small" onClick={handleFilterClick}>
                <FilterIcon />
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>
      )}

      {/* Activity List */}
      <Box
        sx={{
          maxHeight: 480,
          overflowY: "auto",
          "&::-webkit-scrollbar": {
            width: 6,
          },
          "&::-webkit-scrollbar-track": {
            backgroundColor: alpha(theme.palette.grey[300], 0.3),
            borderRadius: 3,
          },
          "&::-webkit-scrollbar-thumb": {
            backgroundColor: alpha(theme.palette.grey[500], 0.5),
            borderRadius: 3,
          },
        }}
      >
        <List dense>
          {activityItems.map((item, index) => {
            const EventIcon = getEventIcon(item.eventType);
            const eventColor = getEventColor(item.eventType);
            const agentColor = getAgentAvatarColor(item.agentId);

            return (
              <React.Fragment key={item.id}>
                <ListItem
                  sx={{
                    py: 1,
                    px: 2,
                    "&:hover": {
                      backgroundColor: alpha(theme.palette.primary.main, 0.04),
                    },
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 40 }}>
                    <Avatar
                      sx={{
                        width: 32,
                        height: 32,
                        bgcolor: `${agentColor}.main`,
                        fontSize: "0.875rem",
                      }}
                    >
                      {item.agentRole?.charAt(0).toUpperCase() || "A"}
                    </Avatar>
                  </ListItemIcon>

                  <ListItemText
                    primary={
                      <Box
                        display="flex"
                        justifyContent="space-between"
                        alignItems="center"
                      >
                        <Box display="flex" alignItems="center" gap={1}>
                          <EventIcon
                            sx={{
                              fontSize: 16,
                              color: `${eventColor}.main`,
                            }}
                          />
                          <Typography variant="body2" fontWeight="medium">
                            {item.description}
                          </Typography>
                          <Chip
                            size="small"
                            label={item.priority}
                            color={getPriorityBadgeColor(item.priority) as any}
                            sx={{ height: 18, fontSize: "0.75rem" }}
                          />
                        </Box>

                        <Typography variant="caption" color="text.secondary">
                          {formatDistanceToNow(new Date(item.timestamp), {
                            addSuffix: true,
                          })}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <Stack
                        direction="row"
                        spacing={1}
                        alignItems="center"
                        mt={0.5}
                      >
                        <Chip
                          size="small"
                          label={item.agentRole || "unknown agent"}
                          variant="outlined"
                          sx={{ height: 16, fontSize: "0.7rem" }}
                        />
                        {item.filePath && (
                          <Typography variant="caption" color="text.secondary">
                            📄 {item.filePath.split("/").slice(-2).join("/")}
                          </Typography>
                        )}
                      </Stack>
                    }
                  />
                </ListItem>
                {index < activityItems.length - 1 && (
                  <Divider variant="inset" component="li" sx={{ ml: 6 }} />
                )}
              </React.Fragment>
            );
          })}
        </List>
      </Box>

      {/* Filter Menu */}
      <Menu
        anchorEl={filterMenuAnchor}
        open={Boolean(filterMenuAnchor)}
        onClose={handleFilterClose}
      >
        <MenuItem onClick={handleFilterClose}>
          <Typography variant="body2">Filter by Event Type</Typography>
        </MenuItem>
        <MenuItem onClick={handleFilterClose}>
          <Typography variant="body2">Filter by Agent</Typography>
        </MenuItem>
        <MenuItem
          onClick={() => {
            setEventTypeFilter([]);
            setAgentFilter([]);
            handleFilterClose();
          }}
        >
          <Typography variant="body2">Clear Filters</Typography>
        </MenuItem>
      </Menu>
    </Box>
  );
};
