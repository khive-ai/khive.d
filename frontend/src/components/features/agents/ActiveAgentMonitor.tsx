"use client";

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  IconButton,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
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
  Divider
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
  TrendingUp
} from '@mui/icons-material';
import { useAgentStatus } from '../../../lib/services/agent-composition';
import { AgentRealTimeStatus } from '../../../lib/types/agent-composition';

interface ActiveAgentMonitorProps {
  agentIds: string[];
  onAgentAction?: (agentId: string, action: 'pause' | 'resume' | 'terminate') => void;
}

interface AgentActionMenuProps {
  agentId: string;
  anchorEl: HTMLElement | null;
  onClose: () => void;
  onAction: (action: 'pause' | 'resume' | 'terminate' | 'details') => void;
}

function AgentActionMenu({ agentId: _agentId, anchorEl, onClose, onAction }: AgentActionMenuProps) {
  return (
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
  );
}

export function ActiveAgentMonitor({ agentIds, onAgentAction }: ActiveAgentMonitorProps) {
  const [actionMenuState, setActionMenuState] = useState<{
    agentId: string;
    anchorEl: HTMLElement | null;
  } | null>(null);
  const [detailDialog, setDetailDialog] = useState<{
    agentId: string;
    status: AgentRealTimeStatus;
  } | null>(null);

  // Get status for all agents - in real implementation, this would be optimized
  const agentStatuses = agentIds.map(agentId => {
    const status = useAgentStatus(agentId);
    return {
      agentId,
      data: status.data,
      isLoading: status.isLoading,
      error: status.error
    };
  });

  const handleActionMenuClick = (event: React.MouseEvent<HTMLElement>, agentId: string) => {
    setActionMenuState({
      agentId,
      anchorEl: event.currentTarget
    });
  };

  const handleActionMenuClose = () => {
    setActionMenuState(null);
  };

  const handleAgentAction = (action: 'pause' | 'resume' | 'terminate' | 'details') => {
    if (!actionMenuState) return;

    if (action === 'details') {
      const agentData = agentStatuses.find(a => a.agentId === actionMenuState.agentId);
      if (agentData?.data) {
        setDetailDialog({
          agentId: actionMenuState.agentId,
          status: agentData.data
        });
      }
    } else {
      onAgentAction?.(actionMenuState.agentId, action);
    }
  };

  const getStatusColor = (status: AgentRealTimeStatus['status']) => {
    switch (status) {
      case 'active':
      case 'working': return 'success';
      case 'spawning': return 'info';
      case 'idle': return 'warning';
      case 'blocked': return 'error';
      case 'failed': return 'error';
      case 'completed': return 'success';
      default: return 'primary';
    }
  };

  const getStatusIcon = (status: AgentRealTimeStatus['status']) => {
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
  };

  const formatDuration = (lastActivity: number) => {
    const minutes = Math.floor((Date.now() - lastActivity) / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  const renderAgentCard = (agentData: { agentId: string; data?: AgentRealTimeStatus | undefined; isLoading: boolean; error: any }) => {
    if (agentData.isLoading) {
      return (
        <Card key={agentData.agentId}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', p: 2 }}>
              <CircularProgress size={24} />
              <Typography sx={{ ml: 2 }}>Loading {agentData.agentId}...</Typography>
            </Box>
          </CardContent>
        </Card>
      );
    }

    if (agentData.error || !agentData.data) {
      return (
        <Card key={agentData.agentId}>
          <CardContent>
            <Alert severity="error">
              Failed to load agent {agentData.agentId}
            </Alert>
          </CardContent>
        </Card>
      );
    }

    const agent = agentData.data;

    return (
      <Card key={agent.agent_id} sx={{ border: 1, borderColor: `${getStatusColor(agent.status)}.main` }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              {getStatusIcon(agent.status)}
              <Typography variant="h6" sx={{ ml: 1 }}>
                {agent.agent_id}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip 
                label={agent.status} 
                color={getStatusColor(agent.status)}
                size="small"
              />
              <IconButton
                size="small"
                onClick={(e) => handleActionMenuClick(e, agent.agent_id)}
              >
                <MoreVert />
              </IconButton>
            </Box>
          </Box>

          <Typography variant="body2" color="text.secondary" gutterBottom>
            {agent.current_task}
          </Typography>

          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2">Progress</Typography>
              <Typography variant="body2">{Math.round(agent.progress * 100)}%</Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={agent.progress * 100}
              color={getStatusColor(agent.status)}
            />
          </Box>

          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
              <Memory sx={{ mr: 1, fontSize: 16 }} />
              <Typography variant="caption">
                {agent.resource_usage.memory}MB
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
              <Speed sx={{ mr: 1, fontSize: 16 }} />
              <Typography variant="caption">
                {agent.resource_usage.cpu}% CPU
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
              <AttachMoney sx={{ mr: 1, fontSize: 16 }} />
              <Typography variant="caption">
                ${agent.performance_metrics.cost.toFixed(2)}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', flex: 1 }}>
              <TrendingUp sx={{ mr: 1, fontSize: 16 }} />
              <Typography variant="caption">
                {(agent.performance_metrics.success_rate * 100).toFixed(0)}% success
              </Typography>
            </Box>
          </Box>

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
        </CardContent>
      </Card>
    );
  };

  const renderDetailDialog = () => {
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
          <Box sx={{ display: 'flex', gap: 2, flexDirection: { xs: 'column', md: 'row' } }}>
            <Box sx={{ flex: 1 }}>
              <Paper sx={{ p: 2, mb: 2 }}>
                <Typography variant="h6" gutterBottom>Status</Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  {getStatusIcon(status.status)}
                  <Chip 
                    label={status.status} 
                    color={getStatusColor(status.status)}
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
            </Box>

            <Box sx={{ flex: 1 }}>
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
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialog(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  };

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
        <Typography variant="h6">
          Active Agents ({agentIds.length})
        </Typography>
        <Button
          startIcon={<Refresh />}
          onClick={() => window.location.reload()} // Simple refresh - in real app would refresh queries
        >
          Refresh All
        </Button>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 2 }}>
        {agentStatuses.map(agentData => (
          <Box key={agentData.agentId}>
            {renderAgentCard(agentData)}
          </Box>
        ))}
      </Box>

      <AgentActionMenu
        agentId={actionMenuState?.agentId || ''}
        anchorEl={actionMenuState?.anchorEl || null}
        onClose={handleActionMenuClose}
        onAction={handleAgentAction}
      />

      {renderDetailDialog()}
    </Box>
  );
}