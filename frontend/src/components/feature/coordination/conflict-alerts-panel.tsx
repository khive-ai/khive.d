/**
 * Conflict Alerts Panel Component
 * Basic conflict alert system with notifications for file conflicts and duplicate work
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  AlertTitle,
  alpha,
  Badge,
  Box,
  Button,
  Chip,
  Collapse,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as ResolvedIcon,
  Close as CloseIcon,
  Error as ErrorIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  Group as GroupIcon,
  Info as InfoIcon,
  Lock as LockIcon,
  Notifications as NotificationsIcon,
  Schedule as TimeIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import { formatDistanceToNow } from "date-fns";
import { FileLock, HookEvent } from "@/lib/types";

export interface ConflictAlertsPanelProps {
  fileLocks: FileLock[];
  events: HookEvent[];
  isRealTime?: boolean;
  maxAlerts?: number;
}

interface ConflictAlert {
  id: string;
  type:
    | "file_conflict"
    | "duplicate_work"
    | "stale_lock"
    | "coordination_issue";
  severity: "error" | "warning" | "info";
  title: string;
  description: string;
  timestamp: string;
  metadata: {
    filePath?: string;
    agentIds?: string[];
    lockExpiration?: string;
    isStale?: boolean;
  };
  resolved?: boolean;
}

const CONFLICT_TYPE_CONFIG = {
  file_conflict: {
    icon: LockIcon,
    color: "error" as const,
    severity: "error" as const,
  },
  duplicate_work: {
    icon: GroupIcon,
    color: "warning" as const,
    severity: "warning" as const,
  },
  stale_lock: {
    icon: TimeIcon,
    color: "warning" as const,
    severity: "warning" as const,
  },
  coordination_issue: {
    icon: WarningIcon,
    color: "info" as const,
    severity: "info" as const,
  },
};

export const ConflictAlertsPanel: React.FC<ConflictAlertsPanelProps> = ({
  fileLocks,
  events,
  isRealTime = true,
  maxAlerts = 20,
}) => {
  const theme = useTheme();
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(
    new Set(),
  );
  const [expandedAlert, setExpandedAlert] = useState<string | null>(null);

  // Generate conflict alerts from file locks and events
  const conflictAlerts = useMemo((): ConflictAlert[] => {
    const alerts: ConflictAlert[] = [];

    // File lock conflicts
    fileLocks.forEach((lock) => {
      if (lock.isStale) {
        alerts.push({
          id: `stale-lock-${lock.filePath}`,
          type: "stale_lock",
          severity: "warning",
          title: "Stale File Lock Detected",
          description: `File lock has expired but was not released: ${
            lock.filePath.split("/").pop()
          }`,
          timestamp: lock.expiration,
          metadata: {
            filePath: lock.filePath,
            agentIds: [lock.agentId],
            lockExpiration: lock.expiration,
            isStale: lock.isStale,
          },
        });
      }
    });

    // Detect potential duplicate work from events
    const recentEditEvents = events
      .filter((e) => e.eventType === "pre_edit" || e.eventType === "post_edit")
      .filter((e) => Date.now() - new Date(e.timestamp).getTime() < 300000) // Last 5 minutes
      .sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );

    // Group by file path to detect multiple agents editing same file
    const fileEditMap = new Map<string, HookEvent[]>();
    recentEditEvents.forEach((event) => {
      if (event.filePath) {
        if (!fileEditMap.has(event.filePath)) {
          fileEditMap.set(event.filePath, []);
        }
        fileEditMap.get(event.filePath)!.push(event);
      }
    });

    fileEditMap.forEach((fileEvents, filePath) => {
      const uniqueAgents = new Set(fileEvents.map((e) => e.agentId));
      if (uniqueAgents.size > 1) {
        alerts.push({
          id: `duplicate-work-${filePath}`,
          type: "duplicate_work",
          severity: "warning",
          title: "Multiple Agents on Same File",
          description: `${uniqueAgents.size} agents recently edited: ${
            filePath.split("/").pop()
          }`,
          timestamp: fileEvents[0].timestamp,
          metadata: {
            filePath,
            agentIds: Array.from(uniqueAgents),
          },
        });
      }
    });

    // General coordination issues
    const failedEvents = events
      .filter((e) => e.metadata.status === "error" || e.metadata.error)
      .slice(0, 5);

    failedEvents.forEach((event, index) => {
      alerts.push({
        id: `coordination-error-${event.id}`,
        type: "coordination_issue",
        severity: "info",
        title: "Coordination Event Error",
        description: `Agent ${
          event.agentId.slice(-8)
        } encountered an error during ${event.eventType}`,
        timestamp: event.timestamp,
        metadata: {
          agentIds: [event.agentId],
        },
      });
    });

    return alerts
      .filter((alert) => !dismissedAlerts.has(alert.id))
      .sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      )
      .slice(0, maxAlerts);
  }, [fileLocks, events, dismissedAlerts, maxAlerts]);

  const handleDismissAlert = (alertId: string) => {
    setDismissedAlerts((prev) => new Set([...prev, alertId]));
  };

  const handleExpandAlert = (alertId: string) => {
    setExpandedAlert(expandedAlert === alertId ? null : alertId);
  };

  const getAlertIcon = (type: string) => {
    const config =
      CONFLICT_TYPE_CONFIG[type as keyof typeof CONFLICT_TYPE_CONFIG];
    return config?.icon || InfoIcon;
  };

  const getAlertColor = (type: string) => {
    const config =
      CONFLICT_TYPE_CONFIG[type as keyof typeof CONFLICT_TYPE_CONFIG];
    return config?.color || "info";
  };

  const activeAlerts =
    conflictAlerts.filter((a) => a.severity === "error").length;
  const warningAlerts =
    conflictAlerts.filter((a) => a.severity === "warning").length;

  if (conflictAlerts.length === 0) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        height={400}
        color="text.secondary"
      >
        <ResolvedIcon
          sx={{ fontSize: 48, mb: 2, opacity: 0.5, color: "success.main" }}
        />
        <Typography variant="h6" gutterBottom>
          No Conflicts Detected
        </Typography>
        <Typography variant="body2" textAlign="center">
          All coordination is running smoothly.
          {isRealTime && " Monitoring for conflicts in real-time."}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Alert Summary */}
      <Box mb={2}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Badge badgeContent={activeAlerts} color="error">
            <Chip
              icon={<ErrorIcon />}
              label="Critical"
              color="error"
              size="small"
              variant={activeAlerts > 0 ? "filled" : "outlined"}
            />
          </Badge>
          <Badge badgeContent={warningAlerts} color="warning">
            <Chip
              icon={<WarningIcon />}
              label="Warnings"
              color="warning"
              size="small"
              variant={warningAlerts > 0 ? "filled" : "outlined"}
            />
          </Badge>
          {isRealTime && (
            <Chip
              icon={<NotificationsIcon />}
              label="Live"
              color="success"
              size="small"
              variant="outlined"
            />
          )}
        </Stack>
      </Box>

      {/* Alerts List */}
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
          {conflictAlerts.map((alert, index) => {
            const AlertIcon = getAlertIcon(alert.type);
            const alertColor = getAlertColor(alert.type);
            const isExpanded = expandedAlert === alert.id;

            return (
              <React.Fragment key={alert.id}>
                <ListItem
                  sx={{
                    py: 1,
                    px: 1,
                    borderRadius: 1,
                    mb: 1,
                    backgroundColor: alpha(
                      theme.palette[alertColor].main,
                      0.05,
                    ),
                    border: `1px solid ${
                      alpha(theme.palette[alertColor].main, 0.2)
                    }`,
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    <AlertIcon
                      sx={{
                        fontSize: 20,
                        color: `${alertColor}.main`,
                      }}
                    />
                  </ListItemIcon>

                  <ListItemText
                    primary={
                      <Box
                        display="flex"
                        justifyContent="space-between"
                        alignItems="center"
                      >
                        <Typography variant="body2" fontWeight="medium">
                          {alert.title}
                        </Typography>
                        <Box display="flex" alignItems="center" gap={0.5}>
                          <Typography variant="caption" color="text.secondary">
                            {formatDistanceToNow(new Date(alert.timestamp), {
                              addSuffix: true,
                            })}
                          </Typography>
                          <Tooltip title={isExpanded ? "Collapse" : "Expand"}>
                            <IconButton
                              size="small"
                              onClick={() => handleExpandAlert(alert.id)}
                            >
                              {isExpanded
                                ? <ExpandLessIcon />
                                : <ExpandMoreIcon />}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Dismiss Alert">
                            <IconButton
                              size="small"
                              onClick={() => handleDismissAlert(alert.id)}
                            >
                              <CloseIcon />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </Box>
                    }
                    secondary={
                      <Typography variant="caption" color="text.secondary">
                        {alert.description}
                      </Typography>
                    }
                  />
                </ListItem>

                {/* Expanded Alert Details */}
                <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                  <Box sx={{ px: 2, py: 1, mb: 1 }}>
                    <Alert severity={alert.severity} variant="outlined">
                      <AlertTitle>{alert.title}</AlertTitle>
                      <Typography variant="body2" mb={1}>
                        {alert.description}
                      </Typography>

                      {/* Alert Metadata */}
                      <Stack spacing={1}>
                        {alert.metadata.filePath && (
                          <Box>
                            <Typography variant="caption" fontWeight="bold">
                              File:
                            </Typography>
                            <Typography variant="caption" sx={{ ml: 1 }}>
                              {alert.metadata.filePath}
                            </Typography>
                          </Box>
                        )}

                        {alert.metadata.agentIds &&
                          alert.metadata.agentIds.length > 0 && (
                          <Box>
                            <Typography variant="caption" fontWeight="bold">
                              Agents:
                            </Typography>
                            <Box display="flex" gap={0.5} mt={0.5}>
                              {alert.metadata.agentIds.map((agentId) => (
                                <Chip
                                  key={agentId}
                                  label={agentId.slice(-8)}
                                  size="small"
                                  variant="outlined"
                                  sx={{ height: 20, fontSize: "0.7rem" }}
                                />
                              ))}
                            </Box>
                          </Box>
                        )}

                        {alert.metadata.lockExpiration && (
                          <Box>
                            <Typography variant="caption" fontWeight="bold">
                              Lock Expired:
                            </Typography>
                            <Typography variant="caption" sx={{ ml: 1 }}>
                              {formatDistanceToNow(
                                new Date(alert.metadata.lockExpiration),
                                { addSuffix: true },
                              )}
                            </Typography>
                          </Box>
                        )}
                      </Stack>
                    </Alert>
                  </Box>
                </Collapse>
              </React.Fragment>
            );
          })}
        </List>
      </Box>

      {/* Footer Actions */}
      {conflictAlerts.length > 0 && (
        <Box
          sx={{ mt: 2, pt: 2, borderTop: `1px solid ${theme.palette.divider}` }}
        >
          <Stack direction="row" spacing={1} justifyContent="space-between">
            <Typography variant="caption" color="text.secondary">
              {conflictAlerts.length} active alerts
            </Typography>
            <Button
              size="small"
              variant="outlined"
              onClick={() =>
                setDismissedAlerts(new Set(conflictAlerts.map((a) => a.id)))}
            >
              Dismiss All
            </Button>
          </Stack>
        </Box>
      )}
    </Box>
  );
};
