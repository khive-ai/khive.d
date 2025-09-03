/**
 * Task List Display Component
 * Advanced task management interface with orchestration flow visualization
 * Implements agentic-systems patterns for multi-agent coordination tracking
 */

import React, { useMemo, useState } from "react";
import {
  Avatar,
  AvatarGroup,
  Badge,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  IconButton,
  LinearProgress,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  AccountTree as DependencyIcon,
  CheckCircle as CompleteIcon,
  Error as ErrorIcon,
  FilterList as FilterIcon,
  Group as AgentIcon,
  Pause as PauseIcon,
  PlayArrow as StartIcon,
  Refresh as RefreshIcon,
  Schedule as PendingIcon,
  Sort as SortIcon,
  Stop as StopIcon,
  Task as TaskIcon,
  Timeline as TimelineIcon,
} from "@mui/icons-material";
import { DataTable } from "@/components/ui/table";
import { useEvents, usePlans } from "@/lib/api/hooks";
import type { ColumnDef } from "@/components/ui/table";

export interface TaskListDisplayProps {
  coordinationId?: string;
  onTaskSelect?: (task: TaskItem) => void;
  onTaskAction?: (taskId: string, action: "start" | "pause" | "stop") => void;
  className?: string;
}

export interface TaskItem {
  id: string;
  name: string;
  description: string;
  status: "pending" | "running" | "completed" | "failed" | "paused";
  priority: "low" | "normal" | "high" | "critical";
  progress: number;
  assignedAgents: Array<{
    id: string;
    role: string;
    domain: string;
    status: "active" | "idle" | "error";
  }>;
  dependencies: string[];
  coordinationStrategy: "FAN_OUT_SYNTHESIZE" | "PIPELINE" | "PARALLEL";
  expectedArtifacts: string[];
  startTime?: string;
  endTime?: string;
  duration?: number;
  phase: string;
  sessionId: string;
}

type TaskFilterType = "all" | "running" | "pending" | "completed" | "failed";
type TaskSortType = "priority" | "status" | "progress" | "startTime";

export const TaskListDisplay: React.FC<TaskListDisplayProps> = ({
  coordinationId,
  onTaskSelect,
  onTaskAction,
  className,
}) => {
  const [filterType, setFilterType] = useState<TaskFilterType>("all");
  const [sortType, setSortType] = useState<TaskSortType>("priority");
  const [filterAnchorEl, setFilterAnchorEl] = useState<null | HTMLElement>(
    null,
  );
  const [sortAnchorEl, setSortAnchorEl] = useState<null | HTMLElement>(null);

  // Fetch real-time events and plans
  const { data: events, refetch: refetchEvents } = useEvents(coordinationId);
  const { data: plans, refetch: refetchPlans } = usePlans();

  // Transform events and plans into task items
  const tasks: TaskItem[] = useMemo(() => {
    if (!events || !plans) return [];

    // Mock implementation - in real app, this would combine events and plans
    // to create comprehensive task tracking
    const mockTasks: TaskItem[] = [
      {
        id: "task-001",
        name: "Research Memory Systems Architecture",
        description:
          "Analyze current memory management patterns and identify optimization opportunities",
        status: "running",
        priority: "high",
        progress: 65,
        assignedAgents: [
          {
            id: "agent-001",
            role: "researcher",
            domain: "memory-systems",
            status: "active",
          },
          {
            id: "agent-002",
            role: "analyst",
            domain: "memory-systems",
            status: "active",
          },
        ],
        dependencies: [],
        coordinationStrategy: "FAN_OUT_SYNTHESIZE",
        expectedArtifacts: [
          "Memory Analysis Report",
          "Optimization Recommendations",
        ],
        startTime: new Date(Date.now() - 3600000).toISOString(),
        phase: "Discovery",
        sessionId: "session-001",
      },
      {
        id: "task-002",
        name: "Implement Coordination Protocol",
        description: "Develop and test multi-agent coordination mechanisms",
        status: "pending",
        priority: "critical",
        progress: 0,
        assignedAgents: [
          {
            id: "agent-003",
            role: "architect",
            domain: "distributed-systems",
            status: "idle",
          },
          {
            id: "agent-004",
            role: "implementer",
            domain: "async-programming",
            status: "idle",
          },
        ],
        dependencies: ["task-001"],
        coordinationStrategy: "PIPELINE",
        expectedArtifacts: [
          "Protocol Implementation",
          "Test Suite",
          "Documentation",
        ],
        phase: "Implementation",
        sessionId: "session-001",
      },
      {
        id: "task-003",
        name: "Performance Optimization Review",
        description:
          "Comprehensive performance analysis and optimization implementation",
        status: "completed",
        priority: "normal",
        progress: 100,
        assignedAgents: [
          {
            id: "agent-005",
            role: "critic",
            domain: "rust-performance",
            status: "idle",
          },
        ],
        dependencies: [],
        coordinationStrategy: "PARALLEL",
        expectedArtifacts: ["Performance Report", "Optimization Patches"],
        startTime: new Date(Date.now() - 7200000).toISOString(),
        endTime: new Date(Date.now() - 1800000).toISOString(),
        duration: 5400000,
        phase: "Validation",
        sessionId: "session-002",
      },
      {
        id: "task-004",
        name: "Error Handling Implementation",
        description:
          "Implement comprehensive error handling across all agent interactions",
        status: "failed",
        priority: "high",
        progress: 45,
        assignedAgents: [
          {
            id: "agent-006",
            role: "implementer",
            domain: "software-architecture",
            status: "error",
          },
        ],
        dependencies: ["task-002"],
        coordinationStrategy: "PIPELINE",
        expectedArtifacts: ["Error Handling Framework", "Recovery Mechanisms"],
        startTime: new Date(Date.now() - 5400000).toISOString(),
        phase: "Implementation",
        sessionId: "session-001",
      },
    ];

    return mockTasks;
  }, [events, plans]);

  // Filter tasks based on selected filter
  const filteredTasks = useMemo(() => {
    if (filterType === "all") return tasks;
    return tasks.filter((task) => task.status === filterType);
  }, [tasks, filterType]);

  // Sort tasks based on selected sort type
  const sortedTasks = useMemo(() => {
    return [...filteredTasks].sort((a, b) => {
      switch (sortType) {
        case "priority":
          const priorityOrder = { critical: 4, high: 3, normal: 2, low: 1 };
          return priorityOrder[b.priority] - priorityOrder[a.priority];
        case "status":
          return a.status.localeCompare(b.status);
        case "progress":
          return b.progress - a.progress;
        case "startTime":
          if (!a.startTime || !b.startTime) return 0;
          return new Date(b.startTime).getTime() -
            new Date(a.startTime).getTime();
        default:
          return 0;
      }
    });
  }, [filteredTasks, sortType]);

  // Column definitions for the data table
  const columns: ColumnDef<TaskItem>[] = [
    {
      accessorKey: "name",
      header: "Task Name",
      cell: ({ row }) => (
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            {row.original.name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {row.original.description}
          </Typography>
        </Box>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      cell: ({ row }) => {
        const getStatusIcon = (status: string) => {
          switch (status) {
            case "running":
              return <StartIcon fontSize="small" />;
            case "pending":
              return <PendingIcon fontSize="small" />;
            case "completed":
              return <CompleteIcon fontSize="small" />;
            case "failed":
              return <ErrorIcon fontSize="small" />;
            case "paused":
              return <PauseIcon fontSize="small" />;
            default:
              return <PendingIcon fontSize="small" />;
          }
        };

        const getStatusColor = (status: string) => {
          switch (status) {
            case "running":
              return "success";
            case "pending":
              return "warning";
            case "completed":
              return "primary";
            case "failed":
              return "error";
            case "paused":
              return "default";
            default:
              return "default";
          }
        };

        return (
          <Chip
            icon={getStatusIcon(row.original.status)}
            label={row.original.status.charAt(0).toUpperCase() +
              row.original.status.slice(1)}
            size="small"
            color={getStatusColor(row.original.status) as any}
            variant="outlined"
          />
        );
      },
    },
    {
      accessorKey: "priority",
      header: "Priority",
      cell: ({ row }) => {
        const getPriorityColor = (priority: string) => {
          switch (priority) {
            case "critical":
              return "error";
            case "high":
              return "warning";
            case "normal":
              return "info";
            case "low":
              return "default";
            default:
              return "default";
          }
        };

        return (
          <Chip
            label={row.original.priority.toUpperCase()}
            size="small"
            color={getPriorityColor(row.original.priority) as any}
          />
        );
      },
    },
    {
      accessorKey: "progress",
      header: "Progress",
      cell: ({ row }) => (
        <Box
          sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 120 }}
        >
          <LinearProgress
            variant="determinate"
            value={row.original.progress}
            sx={{ flex: 1, height: 6, borderRadius: 3 }}
            color={row.original.status === "failed"
              ? "error"
              : row.original.status === "completed"
              ? "success"
              : "primary"}
          />
          <Typography variant="caption" color="text.secondary">
            {row.original.progress}%
          </Typography>
        </Box>
      ),
    },
    {
      accessorKey: "assignedAgents",
      header: "Agents",
      cell: ({ row }) => (
        <Box>
          <AvatarGroup max={3} sx={{ justifyContent: "flex-start" }}>
            {row.original.assignedAgents.map((agent) => (
              <Tooltip
                key={agent.id}
                title={`${agent.role}+${agent.domain} (${agent.status})`}
              >
                <Badge
                  badgeContent=""
                  color={agent.status === "active"
                    ? "success"
                    : agent.status === "error"
                    ? "error"
                    : "default"}
                  variant="dot"
                  anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                >
                  <Avatar sx={{ width: 24, height: 24, fontSize: "0.75rem" }}>
                    {agent.role.charAt(0).toUpperCase()}
                  </Avatar>
                </Badge>
              </Tooltip>
            ))}
          </AvatarGroup>
          <Typography variant="caption" color="text.secondary">
            {row.original.assignedAgents.length}{" "}
            agent{row.original.assignedAgents.length !== 1 ? "s" : ""}
          </Typography>
        </Box>
      ),
    },
    {
      accessorKey: "coordinationStrategy",
      header: "Strategy",
      cell: ({ row }) => {
        const getStrategyInfo = (strategy: string) => {
          switch (strategy) {
            case "FAN_OUT_SYNTHESIZE":
              return {
                label: "Fan-Out",
                icon: <DependencyIcon fontSize="small" />,
                color: "primary",
              };
            case "PIPELINE":
              return {
                label: "Pipeline",
                icon: <TimelineIcon fontSize="small" />,
                color: "secondary",
              };
            case "PARALLEL":
              return {
                label: "Parallel",
                icon: <AgentIcon fontSize="small" />,
                color: "success",
              };
            default:
              return {
                label: "Unknown",
                icon: <TaskIcon fontSize="small" />,
                color: "default",
              };
          }
        };

        const strategyInfo = getStrategyInfo(row.original.coordinationStrategy);

        return (
          <Chip
            icon={strategyInfo.icon}
            label={strategyInfo.label}
            size="small"
            variant="outlined"
            color={strategyInfo.color as any}
          />
        );
      },
    },
    {
      accessorKey: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <Stack direction="row" spacing={0.5}>
          {row.original.status === "pending" && (
            <Tooltip title="Start Task">
              <IconButton
                size="small"
                onClick={() => onTaskAction?.(row.original.id, "start")}
              >
                <StartIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          {row.original.status === "running" && (
            <>
              <Tooltip title="Pause Task">
                <IconButton
                  size="small"
                  onClick={() => onTaskAction?.(row.original.id, "pause")}
                >
                  <PauseIcon fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="Stop Task">
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => onTaskAction?.(row.original.id, "stop")}
                >
                  <StopIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </>
          )}
          {row.original.status === "paused" && (
            <Tooltip title="Resume Task">
              <IconButton
                size="small"
                onClick={() => onTaskAction?.(row.original.id, "start")}
              >
                <StartIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      ),
    },
  ];

  const handleRefresh = () => {
    refetchEvents();
    refetchPlans();
  };

  const handleFilterClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setFilterAnchorEl(event.currentTarget);
  };

  const handleSortClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setSortAnchorEl(event.currentTarget);
  };

  const handleFilterClose = () => {
    setFilterAnchorEl(null);
  };

  const handleSortClose = () => {
    setSortAnchorEl(null);
  };

  const handleFilterSelect = (filter: TaskFilterType) => {
    setFilterType(filter);
    handleFilterClose();
  };

  const handleSortSelect = (sort: TaskSortType) => {
    setSortType(sort);
    handleSortClose();
  };

  return (
    <Card className={className} variant="outlined">
      <CardHeader
        avatar={<TaskIcon color="primary" />}
        title="Task Orchestration"
        subheader={`${sortedTasks.length} tasks • ${
          sortedTasks.filter((t) => t.status === "running").length
        } running`}
        action={
          <Stack direction="row" spacing={1}>
            <Button
              startIcon={<FilterIcon />}
              size="small"
              onClick={handleFilterClick}
              variant="outlined"
            >
              Filter: {filterType}
            </Button>
            <Button
              startIcon={<SortIcon />}
              size="small"
              onClick={handleSortClick}
              variant="outlined"
            >
              Sort: {sortType}
            </Button>
            <Tooltip title="Refresh Tasks">
              <IconButton size="small" onClick={handleRefresh}>
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          </Stack>
        }
      />

      <CardContent sx={{ p: 0 }}>
        <DataTable
          data={sortedTasks}
          columns={columns}
          searchable
          searchPlaceholder="Search tasks..."
          emptyStateMessage="No tasks available"
          emptyStateDescription="Tasks will appear here when orchestration sessions are active"
          pageSize={10}
          onRowClick={(row) => onTaskSelect?.(row)}
        />
      </CardContent>

      {/* Filter Menu */}
      <Menu
        anchorEl={filterAnchorEl}
        open={Boolean(filterAnchorEl)}
        onClose={handleFilterClose}
      >
        <MenuItem onClick={() => handleFilterSelect("all")}>
          <ListItemText>All Tasks</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleFilterSelect("running")}>
          <ListItemIcon>
            <StartIcon />
          </ListItemIcon>
          <ListItemText>Running</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleFilterSelect("pending")}>
          <ListItemIcon>
            <PendingIcon />
          </ListItemIcon>
          <ListItemText>Pending</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleFilterSelect("completed")}>
          <ListItemIcon>
            <CompleteIcon />
          </ListItemIcon>
          <ListItemText>Completed</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleFilterSelect("failed")}>
          <ListItemIcon>
            <ErrorIcon />
          </ListItemIcon>
          <ListItemText>Failed</ListItemText>
        </MenuItem>
      </Menu>

      {/* Sort Menu */}
      <Menu
        anchorEl={sortAnchorEl}
        open={Boolean(sortAnchorEl)}
        onClose={handleSortClose}
      >
        <MenuItem onClick={() => handleSortSelect("priority")}>
          <ListItemText>Priority</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleSortSelect("status")}>
          <ListItemText>Status</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleSortSelect("progress")}>
          <ListItemText>Progress</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleSortSelect("startTime")}>
          <ListItemText>Start Time</ListItemText>
        </MenuItem>
      </Menu>
    </Card>
  );
};
