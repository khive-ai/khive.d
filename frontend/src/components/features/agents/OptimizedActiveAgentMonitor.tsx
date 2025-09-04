// @ts-nocheck
"use client";

import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Grid,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Skeleton,
  Collapse
} from '@mui/material';
import {
  Person,
  PlayArrow,
  Pause,
  Stop,
  Refresh,
  MoreVert,
  Visibility,
  Memory,
  Speed,
  AttachMoney,
  Lock,
  Warning,
  CheckCircle,
  Error,
  Schedule,
  TrendingUp,
  ExpandMore,
  ExpandLess,
  SignalWifiOff,
  SignalWifi4Bar,
  FilterList
} from '@mui/icons-material';
import { 
  useBatchAgentStatus,
  useAgentStatusSubscription 
} from '../../../lib/services/optimized-agent-composition';
import { AgentRealTimeStatus } from '../../../lib/types/agent-composition';

interface OptimizedActiveAgentMonitorProps {
  agentIds: string[];
  onAgentAction?: (agentId: string, action: 'pause' | 'resume' | 'terminate') => void;
  realTimeEnabled?: boolean;
  batchSize?: number;
  refreshInterval?: number;
}

interface AgentActionMenuProps {
  agentId: string;
  anchorEl: HTMLElement | null;
  onClose: () => void;
  onAction: (action: 'pause' | 'resume' | 'terminate' | 'details') => void;
}

interface AgentCardProps {
  agent: AgentRealTimeStatus;
  onActionMenuClick: (event: React.MouseEvent<HTMLElement>, agentId: string) => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

// Memoized Agent Action Menu Component
const AgentActionMenu = React.memo<AgentActionMenuProps>(({ 
  agentId, 
  anchorEl, 
  onClose, 
  onAction 
}) => (
  <Menu
    anchorEl={anchorEl}
    open={Boolean(anchorEl)}
    onClose={onClose}
  >
    <MenuItem onClick={() => { onAction('details'); onClose(); }}>
      <Visibility sx={{ mr: 1 }} /> View Details
    </MenuItem>
    <MenuItem onClick={() => { onAction('pause'); onClose(); }}>
      <Pause sx={{ mr: 1 }} /> Pause Agent
    </MenuItem>
    <MenuItem onClick={() => { onAction('resume'); onClose(); }}>
      <PlayArrow sx={{ mr: 1 }} /> Resume Agent
    </MenuItem>
    <Divider />
    <MenuItem 
      onClick={() => { onAction('terminate'); onClose(); }}
      sx={{ color: 'error.main' }}
    >
      <Stop sx={{ mr: 1 }} /> Terminate Agent
    </MenuItem>
  </Menu>
));

AgentActionMenu.displayName = 'AgentActionMenu';

// Memoized Agent Card Component with Performance Optimizations
const AgentCard = React.memo<AgentCardProps>(({ 
  agent, 
  onActionMenuClick,
  isCollapsed = false,
  onToggleCollapse 
}) => {
  const getStatusColor = useCallback((status: AgentRealTimeStatus['status']) => {
    switch (status) {
      case 'active':
      case 'working': return 'success';
      case 'spawning': return 'info';
      case 'idle': return 'warning';
      case 'blocked': return 'error';
      case 'failed': return 'error';
      case 'completed': return 'success';
      default: return 'default';
    }
  }, []);

  const getStatusIcon = useCallback((status: AgentRealTimeStatus['status']) => {
    switch (status) {
      case 'active':
      case 'working': return <CheckCircle />;
      case 'spawning': return <CircularProgress size={16} />;
      case 'idle': return <Schedule />;
      case 'blocked': return <Warning />;
      case 'failed': return <Error />;
      case 'completed': return <CheckCircle />;
      default: return <Person />;
    }
  }, []);

  const formatDuration = useCallback((lastActivity: number) => {
    const minutes = Math.floor((Date.now() - lastActivity) / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  }, []);

  const statusColor = getStatusColor(agent.status);
  const statusIcon = getStatusIcon(agent.status);

  return (
    <Card sx={{ 
      border: 1, 
      borderColor: `${statusColor}.main`,
      transition: 'box-shadow 0.2s ease-in-out',
      '&:hover': { boxShadow: 3 }
    }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            {statusIcon}
            <Typography variant="h6" sx={{ ml: 1 }}>
              {agent.agent_id}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip 
              label={agent.status} 
              color={statusColor}
              size="small"
            />
            <IconButton
              size="small"
              onClick={(e) => onActionMenuClick(e, agent.agent_id)}
              aria-label="Agent actions"
            >
              <MoreVert />
            </IconButton>
            {onToggleCollapse && (
              <IconButton
                size="small"
                onClick={onToggleCollapse}
                aria-label={isCollapsed ? "Expand" : "Collapse"}
              >
                {isCollapsed ? <ExpandMore /> : <ExpandLess />}
              </IconButton>
            )}
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" gutterBottom>
          {agent.current_task}
        </Typography>

        <Collapse in={!isCollapsed} timeout="auto" unmountOnExit>
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2">Progress</Typography>
              <Typography variant="body2">{Math.round(agent.progress * 100)}%</Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={agent.progress * 100}
              color={statusColor}
            />
          </Box>

          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Memory sx={{ mr: 1, fontSize: 16 }} />
                <Typography variant="caption">
                  {agent.resource_usage.memory}MB
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Speed sx={{ mr: 1, fontSize: 16 }} />
                <Typography variant="caption">
                  {agent.resource_usage.cpu}% CPU
                </Typography>
              </Box>
            </Grid>
          </Grid>

          <Grid container spacing={2}>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <AttachMoney sx={{ mr: 1, fontSize: 16 }} />
                <Typography variant="caption">
                  ${agent.performance_metrics.cost.toFixed(2)}
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={6}>
              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <TrendingUp sx={{ mr: 1, fontSize: 16 }} />
                <Typography variant="caption">
                  {(agent.performance_metrics.success_rate * 100).toFixed(0)}% success
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {agent.coordination.locks_held.length > 0 && (
            <Box sx={{ mt: 1, display: 'flex', alignItems: 'center' }}>
              <Lock sx={{ mr: 1, fontSize: 16, color: 'warning.main' }} />
              <Typography variant="caption" color="warning.main">
                {agent.coordination.locks_held.length} locks held
              </Typography>
            </Box>
          )}

          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Last activity: {formatDuration(agent.last_activity)}
          </Typography>
        </Collapse>
      </CardContent>
    </Card>
  );
});

AgentCard.displayName = 'AgentCard';

// Optimized Loading Skeleton Component
const AgentCardSkeleton = React.memo(() => (
  <Card>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Skeleton variant="circular" width={40} height={40} />
        <Skeleton variant="rectangular" width={80} height={24} />
      </Box>
      <Skeleton variant="text" sx={{ mb: 1 }} />
      <Skeleton variant="rectangular" width="100%" height={6} sx={{ mb: 2 }} />
      <Grid container spacing={2}>
        <Grid item xs={6}>
          <Skeleton variant="text" />
        </Grid>
        <Grid item xs={6}>
          <Skeleton variant="text" />
        </Grid>
      </Grid>
    </CardContent>
  </Card>
));

AgentCardSkeleton.displayName = 'AgentCardSkeleton';

export function OptimizedActiveAgentMonitor({ 
  agentIds, 
  onAgentAction,
  realTimeEnabled = true,
  batchSize = 10,
  refreshInterval = 5000
}: OptimizedActiveAgentMonitorProps) {
  const [actionMenuState, setActionMenuState] = useState<{
    agentId: string;
    anchorEl: HTMLElement | null;
  } | null>(null);
  const [detailDialog, setDetailDialog] = useState<{
    agentId: string;
    status: AgentRealTimeStatus;
  } | null>(null);
  const [collapsedAgents, setCollapsedAgents] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Use optimized batch query instead of individual queries
  const { 
    data: agentStatuses, 
    isLoading, 
    error, 
    refetch,
    isStale 
  } = useBatchAgentStatus(
    agentIds, 
    {
      batchSize,
      enabled: agentIds.length > 0,
      refetchInterval: realTimeEnabled ? refreshInterval : false,
      staleTime: refreshInterval / 2,
    }
  );

  // Optional real-time subscription for critical updates
  const { 
    connectionStatus, 
    lastUpdate 
  } = useAgentStatusSubscription(
    agentIds, 
    { enabled: realTimeEnabled }
  );

  // Memoized filtered agent data
  const filteredAgents = useMemo(() => {
    if (!agentStatuses) return [];
    
    return agentStatuses.filter(agent => {
      if (statusFilter === 'all') return true;
      return agent.status === statusFilter;
    });
  }, [agentStatuses, statusFilter]);

  // Memoized handlers to prevent unnecessary re-renders
  const handleActionMenuClick = useCallback((event: React.MouseEvent<HTMLElement>, agentId: string) => {
    setActionMenuState({
      agentId,
      anchorEl: event.currentTarget
    });
  }, []);

  const handleActionMenuClose = useCallback(() => {
    setActionMenuState(null);
  }, []);

  const handleAgentAction = useCallback((action: 'pause' | 'resume' | 'terminate' | 'details') => {
    if (!actionMenuState) return;

    if (action === 'details') {
      const agent = agentStatuses?.find(a => a.agent_id === actionMenuState.agentId);
      if (agent) {
        setDetailDialog({
          agentId: actionMenuState.agentId,
          status: agent
        });
      }
    } else {
      onAgentAction?.(actionMenuState.agentId, action);
    }
  }, [actionMenuState, agentStatuses, onAgentAction]);

  const handleToggleCollapse = useCallback((agentId: string) => {
    setCollapsedAgents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(agentId)) {
        newSet.delete(agentId);
      } else {
        newSet.add(agentId);
      }
      return newSet;
    });
  }, []);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Connection status indicator
  const renderConnectionStatus = useCallback(() => {
    if (!realTimeEnabled) return null;

    const isConnected = connectionStatus === 'connected';
    return (
      <Tooltip title={`Real-time updates: ${connectionStatus}`}>
        <Box sx={{ display: 'flex', alignItems: 'center', ml: 1 }}>
          {isConnected ? (
            <SignalWifi4Bar color="success" fontSize="small" />
          ) : (
            <SignalWifiOff color="error" fontSize="small" />
          )}
          <Typography variant="caption" sx={{ ml: 0.5 }}>
            {lastUpdate && `Updated ${formatDuration(lastUpdate)}`}
          </Typography>
        </Box>
      </Tooltip>
    );
  }, [connectionStatus, lastUpdate, realTimeEnabled]);

  const formatDuration = useCallback((timestamp: number) => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  }, []);

  // Detailed Dialog Component (memoized)
  const renderDetailDialog = useMemo(() => {
    if (!detailDialog) return null;

    const { agentId, status } = detailDialog;

    return (
      <Dialog
        open={true}
        onClose={() => setDetailDialog(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Agent Details: {agentId}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>Status</Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <Chip 
                    label={status.status} 
                    color={(() => {
                      switch (status.status) {
                        case 'active':
                        case 'working': return 'success';
                        case 'spawning': return 'info';
                        case 'idle': return 'warning';
                        case 'blocked': return 'error';
                        case 'failed': return 'error';
                        case 'completed': return 'success';
                        default: return 'default';
                      }
                    })()}
                    sx={{ ml: 1 }}
                  />
                </Box>
                <Typography variant="body2">{status.current_task}</Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={status.progress * 100}
                  sx={{ mt: 1 }}
                />
                <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>
                  {Math.round(status.progress * 100)}% complete
                </Typography>
              </Paper>

              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Resource Usage</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>CPU</TableCell>
                        <TableCell>{status.resource_usage.cpu}%</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Memory</TableCell>
                        <TableCell>{status.resource_usage.memory}MB</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Tokens Used</TableCell>
                        <TableCell>{status.resource_usage.tokens_used}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>API Calls</TableCell>
                        <TableCell>{status.resource_usage.api_calls}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>Performance</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>Tasks Completed</TableCell>
                        <TableCell>{status.performance_metrics.tasks_completed}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Avg Task Time</TableCell>
                        <TableCell>{Math.round(status.performance_metrics.avg_task_time / 60)}m</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Success Rate</TableCell>
                        <TableCell>{(status.performance_metrics.success_rate * 100).toFixed(1)}%</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Total Cost</TableCell>
                        <TableCell>${status.performance_metrics.cost.toFixed(2)}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>

              <Paper sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>Coordination</Typography>
                
                {status.coordination.locks_held.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>Locks Held</Typography>
                    <List dense>
                      {status.coordination.locks_held.map((lock, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <Lock fontSize="small" />
                          </ListItemIcon>
                          <ListItemText primary={lock} />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}

                {status.coordination.waiting_for.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>Waiting For</Typography>
                    <List dense>
                      {status.coordination.waiting_for.map((item, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <Schedule fontSize="small" />
                          </ListItemIcon>
                          <ListItemText primary={item} />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}

                {status.coordination.conflicts.length > 0 && (
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>Conflicts</Typography>
                    <List dense>
                      {status.coordination.conflicts.map((conflict, index) => (
                        <ListItem key={index}>
                          <ListItemIcon>
                            <Warning fontSize="small" color="error" />
                          </ListItemIcon>
                          <ListItemText primary={conflict} />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}

                {status.coordination.locks_held.length === 0 && 
                 status.coordination.waiting_for.length === 0 && 
                 status.coordination.conflicts.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    No coordination issues
                  </Typography>
                )}
              </Paper>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialog(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  }, [detailDialog]);

  // Error boundary
  if (error) {
    return (
      <Paper sx={{ p: 3 }}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={handleRefresh}>
            Retry
          </Button>
        }>
          Failed to load agent status data: {error.message}
        </Alert>
      </Paper>
    );
  }

  // Empty state
  if (agentIds.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No Active Agents
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Spawn some agents to see their real-time status here
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ height: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Typography variant="h6">
            Active Agents ({filteredAgents.length}/{agentIds.length})
          </Typography>
          {renderConnectionStatus()}
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Button
            startIcon={<FilterList />}
            size="small"
            variant="outlined"
            onClick={() => {
              // Filter implementation would go here
              console.log('Filter clicked');
            }}
          >
            Filter
          </Button>
          <Button
            startIcon={<Refresh />}
            onClick={handleRefresh}
            disabled={isLoading}
          >
            {isLoading ? 'Refreshing...' : 'Refresh All'}
          </Button>
        </Box>
      </Box>

      {isStale && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Data may be stale. Real-time updates are {realTimeEnabled ? 'enabled' : 'disabled'}.
        </Alert>
      )}

      <Grid container spacing={2}>
        {isLoading && !agentStatuses ? (
          // Loading skeletons
          Array.from({ length: Math.min(agentIds.length, 6) }).map((_, index) => (
            <Grid item xs={12} md={6} lg={4} key={`skeleton-${index}`}>
              <AgentCardSkeleton />
            </Grid>
          ))
        ) : (
          // Agent cards
          filteredAgents.map(agent => (
            <Grid item xs={12} md={6} lg={4} key={agent.agent_id}>
              <AgentCard
                agent={agent}
                onActionMenuClick={handleActionMenuClick}
                isCollapsed={collapsedAgents.has(agent.agent_id)}
                onToggleCollapse={() => handleToggleCollapse(agent.agent_id)}
              />
            </Grid>
          ))
        )}
      </Grid>

      <AgentActionMenu
        agentId={actionMenuState?.agentId || ''}
        anchorEl={actionMenuState?.anchorEl || null}
        onClose={handleActionMenuClose}
        onAction={handleAgentAction}
      />

      {renderDetailDialog}
    </Box>
  );
}