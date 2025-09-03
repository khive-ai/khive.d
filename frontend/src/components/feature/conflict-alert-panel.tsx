/**
 * Conflict Alert Panel Component
 * Displays file conflicts, duplicate work warnings, and coordination alerts
 */

import React, { useEffect, useState } from "react";
import {
  Alert,
  AlertTitle,
  Badge,
  Box,
  Chip,
  Collapse,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Clear as ClearIcon,
  ContentCopy as DuplicateIcon,
  Error as ErrorIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  Lock as LockIcon,
  Timer as TimerIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";
import { Card, CardContent, CardHeader } from "@/components/ui";
import { Agent, FileLock, HookEvent } from "@/lib/types";

export interface ConflictAlert {
  id: string;
  type:
    | "file_conflict"
    | "duplicate_work"
    | "stale_lock"
    | "coordination_error";
  severity: "low" | "medium" | "high" | "critical";
  title: string;
  description: string;
  timestamp: string;
  agentIds: string[];
  filePath?: string;
  metadata?: Record<string, any>;
}

export interface ConflictAlertPanelProps {
  fileLocks: FileLock[];
  agents: Agent[];
  events: HookEvent[];
  autoGenerateAlerts?: boolean;
  onDismissAlert?: (alertId: string) => void;
  className?: string;
}

export const ConflictAlertPanel: React.FC<ConflictAlertPanelProps> = ({
  fileLocks,
  agents,
  events,
  autoGenerateAlerts = true,
  onDismissAlert,
  className,
}) => {
  const [alerts, setAlerts] = useState<ConflictAlert[]>([]);
  const [expandedAlerts, setExpandedAlerts] = useState<Set<string>>(new Set());
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(
    new Set(),
  );

  useEffect(() => {
    if (autoGenerateAlerts) {
      generateAlerts();
    }
  }, [fileLocks, agents, events, autoGenerateAlerts]);

  const generateAlerts = () => {
    const newAlerts: ConflictAlert[] = [];

    // Check for stale file locks
    fileLocks.forEach((lock) => {
      if (lock.isStale) {
        newAlerts.push({
          id: `stale-lock-${lock.filePath}`,
          type: "stale_lock",
          severity: "medium",
          title: "Stale File Lock Detected",
          description: `File ${
            lock.filePath.split("/").pop()
          } has been locked by ${
            lock.agentId.slice(-8)
          } for an extended period`,
          timestamp: new Date().toISOString(),
          agentIds: [lock.agentId],
          filePath: lock.filePath,
        });
      }
    });

    // Check for potential duplicate work (simplified logic)
    const taskGroups = new Map<string, string[]>();
    events.forEach((event) => {
      if (event.eventType === "pre_command" && event.command) {
        const taskKey = event.command.toLowerCase();
        if (!taskGroups.has(taskKey)) {
          taskGroups.set(taskKey, []);
        }
        taskGroups.get(taskKey)!.push(event.agentId);
      }
    });

    taskGroups.forEach((agentIds, task) => {
      if (agentIds.length > 1) {
        const uniqueAgents = [...new Set(agentIds)];
        if (uniqueAgents.length > 1) {
          newAlerts.push({
            id: `duplicate-work-${task.slice(0, 20)}`,
            type: "duplicate_work",
            severity: "high",
            title: "Potential Duplicate Work",
            description: `Multiple agents may be working on similar tasks: ${
              task.slice(0, 60)
            }...`,
            timestamp: new Date().toISOString(),
            agentIds: uniqueAgents,
            metadata: { taskCommand: task },
          });
        }
      }
    });

    // Check for multiple locks on same file
    const filePathGroups = new Map<string, string[]>();
    fileLocks.forEach((lock) => {
      if (!filePathGroups.has(lock.filePath)) {
        filePathGroups.set(lock.filePath, []);
      }
      filePathGroups.get(lock.filePath)!.push(lock.agentId);
    });

    filePathGroups.forEach((agentIds, filePath) => {
      if (agentIds.length > 1) {
        newAlerts.push({
          id: `file-conflict-${filePath}`,
          type: "file_conflict",
          severity: "critical",
          title: "File Lock Conflict",
          description: `Multiple agents attempting to access: ${
            filePath.split("/").pop()
          }`,
          timestamp: new Date().toISOString(),
          agentIds,
          filePath,
        });
      }
    });

    // Filter out dismissed alerts
    const activeAlerts = newAlerts.filter((alert) =>
      !dismissedAlerts.has(alert.id)
    );
    setAlerts(activeAlerts);
  };

  const getSeverityColor = (severity: ConflictAlert["severity"]) => {
    switch (severity) {
      case "low":
        return "info";
      case "medium":
        return "warning";
      case "high":
        return "error";
      case "critical":
        return "error";
      default:
        return "info";
    }
  };

  const getSeverityIcon = (severity: ConflictAlert["severity"]) => {
    switch (severity) {
      case "low":
        return <TimerIcon />;
      case "medium":
        return <WarningIcon />;
      case "high":
        return <ErrorIcon />;
      case "critical":
        return <ErrorIcon />;
      default:
        return <WarningIcon />;
    }
  };

  const getTypeIcon = (type: ConflictAlert["type"]) => {
    switch (type) {
      case "file_conflict":
        return <LockIcon />;
      case "duplicate_work":
        return <DuplicateIcon />;
      case "stale_lock":
        return <TimerIcon />;
      case "coordination_error":
        return <ErrorIcon />;
      default:
        return <WarningIcon />;
    }
  };

  const handleDismissAlert = (alertId: string) => {
    setDismissedAlerts((prev) => new Set([...prev, alertId]));
    setAlerts((prev) => prev.filter((alert) => alert.id !== alertId));
    onDismissAlert?.(alertId);
  };

  const toggleExpandAlert = (alertId: string) => {
    setExpandedAlerts((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(alertId)) {
        newSet.delete(alertId);
      } else {
        newSet.add(alertId);
      }
      return newSet;
    });
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const getAgentName = (agentId: string) => {
    const agent = agents.find((a) => a.id === agentId);
    return agent ? `${agent.role}+${agent.domain}` : agentId.slice(-8);
  };

  const criticalAlerts = alerts.filter((a) => a.severity === "critical");
  const nonCriticalAlerts = alerts.filter((a) => a.severity !== "critical");

  return (
    <Card className={className} variant="outlined">
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="h6" component="h3">
              Coordination Alerts
            </Typography>
            <Badge badgeContent={alerts.length} color="error">
              <Chip
                label={`${alerts.length} active`}
                size="small"
                color={alerts.length > 0 ? "error" : "success"}
                variant="outlined"
              />
            </Badge>
          </Box>
        }
        subtitle={
          <Typography variant="body2" color="text.secondary">
            File conflicts and coordination issues
          </Typography>
        }
      />

      <CardContent sx={{ p: 0 }}>
        {alerts.length === 0
          ? (
            <Box p={3} textAlign="center">
              <Typography variant="body2" color="text.secondary">
                ✅ No coordination conflicts detected
              </Typography>
            </Box>
          )
          : (
            <Box>
              {/* Critical Alerts */}
              {criticalAlerts.length > 0 && (
                <Box mb={2}>
                  <Typography
                    variant="subtitle2"
                    color="error.main"
                    sx={{ px: 2, py: 1 }}
                  >
                    Critical Issues ({criticalAlerts.length})
                  </Typography>
                  {criticalAlerts.map((alert) => (
                    <Alert
                      key={alert.id}
                      severity="error"
                      sx={{ mx: 2, mb: 1, borderRadius: 1 }}
                      action={
                        <IconButton
                          size="small"
                          onClick={() => handleDismissAlert(alert.id)}
                        >
                          <ClearIcon />
                        </IconButton>
                      }
                    >
                      <AlertTitle>{alert.title}</AlertTitle>
                      {alert.description}
                      <Box display="flex" gap={1} mt={1} flexWrap="wrap">
                        {alert.agentIds.map((agentId) => (
                          <Chip
                            key={agentId}
                            label={getAgentName(agentId)}
                            size="small"
                            variant="outlined"
                          />
                        ))}
                        <Chip
                          label={formatTimestamp(alert.timestamp)}
                          size="small"
                          variant="outlined"
                          color="secondary"
                        />
                      </Box>
                    </Alert>
                  ))}
                </Box>
              )}

              {/* Non-Critical Alerts */}
              {nonCriticalAlerts.length > 0 && (
                <List dense>
                  {nonCriticalAlerts.map((alert) => (
                    <React.Fragment key={alert.id}>
                      <ListItem
                        sx={{
                          borderLeft: `4px solid`,
                          borderLeftColor: `${
                            getSeverityColor(alert.severity)
                          }.main`,
                          backgroundColor: `${
                            getSeverityColor(alert.severity)
                          }.light`,
                          mx: 2,
                          mb: 1,
                          borderRadius: 1,
                        }}
                      >
                        <ListItemIcon>
                          {getTypeIcon(alert.type)}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="subtitle2">
                                {alert.title}
                              </Typography>
                              <Chip
                                label={alert.severity}
                                size="small"
                                color={getSeverityColor(alert.severity) as any}
                                variant="outlined"
                              />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography
                                variant="body2"
                                color="text.secondary"
                              >
                                {alert.description}
                              </Typography>
                              <Box
                                display="flex"
                                gap={0.5}
                                mt={0.5}
                                flexWrap="wrap"
                              >
                                {alert.agentIds.slice(0, 3).map((agentId) => (
                                  <Chip
                                    key={agentId}
                                    label={getAgentName(agentId)}
                                    size="small"
                                    variant="outlined"
                                    sx={{ height: 18, fontSize: "0.65rem" }}
                                  />
                                ))}
                                {alert.agentIds.length > 3 && (
                                  <Chip
                                    label={`+${alert.agentIds.length - 3} more`}
                                    size="small"
                                    variant="outlined"
                                    sx={{ height: 18, fontSize: "0.65rem" }}
                                  />
                                )}
                              </Box>
                            </Box>
                          }
                        />
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="caption" color="text.secondary">
                            {formatTimestamp(alert.timestamp)}
                          </Typography>
                          <IconButton
                            size="small"
                            onClick={() =>
                              toggleExpandAlert(alert.id)}
                          >
                            {expandedAlerts.has(alert.id)
                              ? <ExpandLessIcon />
                              : <ExpandMoreIcon />}
                          </IconButton>
                          <IconButton
                            size="small"
                            onClick={() => handleDismissAlert(alert.id)}
                          >
                            <ClearIcon />
                          </IconButton>
                        </Box>
                      </ListItem>

                      <Collapse in={expandedAlerts.has(alert.id)}>
                        <Box px={4} pb={2}>
                          {alert.filePath && (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{
                                display: "block",
                                fontFamily: "monospace",
                                backgroundColor: "grey.100",
                                px: 1,
                                py: 0.5,
                                borderRadius: 0.5,
                                mb: 1,
                                wordBreak: "break-all",
                              }}
                            >
                              File: {alert.filePath}
                            </Typography>
                          )}
                          {alert.metadata && (
                            <Box>
                              <Typography
                                variant="caption"
                                color="text.secondary"
                              >
                                Metadata:
                              </Typography>
                              <Box
                                display="flex"
                                flexWrap="wrap"
                                gap={0.5}
                                mt={0.5}
                              >
                                {Object.entries(alert.metadata).map((
                                  [key, value],
                                ) => (
                                  <Chip
                                    key={key}
                                    label={`${key}: ${
                                      String(value).slice(0, 30)
                                    }`}
                                    size="small"
                                    variant="outlined"
                                    sx={{ height: 18, fontSize: "0.6rem" }}
                                  />
                                ))}
                              </Box>
                            </Box>
                          )}
                        </Box>
                      </Collapse>
                    </React.Fragment>
                  ))}
                </List>
              )}
            </Box>
          )}
      </CardContent>
    </Card>
  );
};
