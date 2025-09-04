// @ts-nocheck
"use client";

import React, { memo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  Badge,
  Card,
  CardContent,
  LinearProgress,
  Chip
} from '@mui/material';
import { 
  Groups, 
  CheckCircle, 
  Warning, 
  Info, 
  Schedule,
  TrendingUp,
  Speed,
  Assessment
} from '@mui/icons-material';
import { AgentCoordinationPanel } from '../AgentCoordinationPanel';
import { Agent, CoordinationEvent } from '@/lib/types/khive';

export interface ExecutionMonitorStepProps {
  status: 'executing' | 'completed' | 'failed';
  agents: Agent[];
  coordinationEvents: CoordinationEvent[];
  coordinationId?: string;
  executionMetrics?: {
    startTime: number;
    completionRate: number;
    averageAgentUtilization: number;
    conflictsResolved: number;
  };
}

/**
 * Component Architecture: Execution Monitor Step
 * 
 * Responsibility: Monitors and displays plan execution progress
 * Principles:
 * - Composition: Integrates AgentCoordinationPanel for detailed monitoring
 * - Real-time Updates: Handles live data updates efficiently
 * - Status Management: Clear status indication and progress tracking
 * - Information Architecture: Organized dashboard layout
 */
export const ExecutionMonitorStep = memo<ExecutionMonitorStepProps>(({
  status,
  agents,
  coordinationEvents,
  coordinationId,
  executionMetrics
}) => {
  const getStatusAlert = () => {
    switch (status) {
      case 'executing':
        return {
          severity: 'info' as const,
          icon: <Schedule />,
          title: 'Plan Execution in Progress',
          message: 'Agents are being spawned and tasks are being coordinated. Monitor progress below.'
        };
      case 'completed':
        return {
          severity: 'success' as const,
          icon: <CheckCircle />,
          title: 'Plan Execution Completed Successfully!',
          message: 'All agents have completed their tasks and coordination is finished.'
        };
      case 'failed':
        return {
          severity: 'error' as const,
          icon: <Warning />,
          title: 'Plan Execution Failed',
          message: 'Execution encountered critical errors. Review the coordination events for details.'
        };
      default:
        return null;
    }
  };

  const statusAlert = getStatusAlert();

  const getAgentStatusCounts = () => {
    const statusCounts = agents.reduce((acc, agent) => {
      acc[agent.status] = (acc[agent.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      active: statusCounts.active || statusCounts.working || 0,
      completed: statusCounts.completed || statusCounts.finished || 0,
      failed: statusCounts.failed || statusCounts.error || 0,
      idle: statusCounts.idle || statusCounts.waiting || 0,
      total: agents.length
    };
  };

  const agentCounts = getAgentStatusCounts();

  const getRecentEvents = () => {
    return coordinationEvents
      .slice(0, 10)
      .map(event => ({
        ...event,
        icon: event.type === 'conflict' ? <Warning color="warning" /> :
              event.type === 'task_complete' ? <CheckCircle color="success" /> :
              event.type === 'agent_spawn' ? <Groups color="info" /> :
              <Info color="primary" />
      }));
  };

  const recentEvents = getRecentEvents();

  return (
    <Box>
      {/* Status Alert */}
      {statusAlert && (
        <Alert 
          severity={statusAlert.severity} 
          sx={{ mb: 2 }}
          icon={statusAlert.icon}
        >
          <Typography variant="subtitle1" fontWeight="bold">
            {statusAlert.title}
          </Typography>
          <Typography variant="body2">
            {statusAlert.message}
          </Typography>
        </Alert>
      )}

      {/* Execution Overview Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Badge 
                badgeContent={agentCounts.active}
                color="primary"
                anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
              >
                <Groups color="primary" sx={{ fontSize: 40 }} />
              </Badge>
              <Typography variant="h6" sx={{ mt: 1 }}>
                {agentCounts.total}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Total Agents
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <TrendingUp color="success" sx={{ fontSize: 40 }} />
              <Typography variant="h6" sx={{ mt: 1 }}>
                {Math.round((agentCounts.completed / Math.max(agentCounts.total, 1)) * 100)}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Completion Rate
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={(agentCounts.completed / Math.max(agentCounts.total, 1)) * 100}
                sx={{ mt: 1 }}
                color="success"
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Speed color="info" sx={{ fontSize: 40 }} />
              <Typography variant="h6" sx={{ mt: 1 }}>
                {executionMetrics?.averageAgentUtilization ? 
                  Math.round(executionMetrics.averageAgentUtilization * 100) : 0}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Agent Utilization
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Assessment color="warning" sx={{ fontSize: 40 }} />
              <Typography variant="h6" sx={{ mt: 1 }}>
                {coordinationEvents.filter(e => e.type === 'conflict').length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Coordination Events
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Detailed Monitoring */}
      <Grid container spacing={2}>
        {/* Agent Status List */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '400px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
              <Groups /> Active Agents ({agents.length})
            </Typography>
            
            <Box sx={{ flex: 1, overflow: 'auto' }}>
              <List dense>
                {agents.map((agent) => (
                  <ListItem key={agent.id}>
                    <ListItemIcon>
                      <Badge 
                        color={
                          agent.status === 'active' || agent.status === 'working' ? 'success' :
                          agent.status === 'completed' ? 'primary' :
                          agent.status === 'failed' ? 'error' : 'default'
                        }
                        variant="dot"
                      >
                        <Groups />
                      </Badge>
                    </ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body2" fontWeight="medium">
                            {agent.role}+{agent.domain}
                          </Typography>
                          <Chip 
                            label={agent.status}
                            size="small"
                            color={
                              agent.status === 'active' || agent.status === 'working' ? 'success' :
                              agent.status === 'completed' ? 'primary' :
                              agent.status === 'failed' ? 'error' : 'default'
                            }
                          />
                        </Box>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary">
                          {agent.currentTask || 'No active task'} 
                          {agent.progress !== undefined && ` • ${Math.round(agent.progress * 100)}% complete`}
                        </Typography>
                      }
                    />
                  </ListItem>
                ))}
              </List>
              
              {agents.length === 0 && (
                <Box 
                  display="flex" 
                  alignItems="center" 
                  justifyContent="center" 
                  height="100%"
                  color="text.secondary"
                >
                  <Typography variant="body2">
                    No agents spawned yet...
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* Recent Events */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '400px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
              <Info /> Recent Events
            </Typography>
            
            <Box sx={{ flex: 1, overflow: 'auto' }}>
              <List dense>
                {recentEvents.map((event, index) => (
                  <ListItem key={index}>
                    <ListItemIcon>
                      {event.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={event.message}
                      secondary={
                        <Box>
                          {event.agent_id && (
                            <Typography variant="caption" display="block">
                              Agent: {event.agent_id}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary">
                            {new Date(event.timestamp).toLocaleTimeString()}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
              
              {recentEvents.length === 0 && (
                <Box 
                  display="flex" 
                  alignItems="center" 
                  justifyContent="center" 
                  height="100%"
                  color="text.secondary"
                >
                  <Typography variant="body2">
                    No coordination events yet...
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Advanced Coordination Panel */}
      {coordinationId && (
        <Box sx={{ mt: 3 }}>
          <AgentCoordinationPanel
            coordinationId={coordinationId}
            realTimeUpdates={true}
            showConflictResolution={true}
          />
        </Box>
      )}
    </Box>
  );
});

ExecutionMonitorStep.displayName = 'ExecutionMonitorStep';