"use client";

import React, { useState } from 'react';
import { SessionManagerMUI } from '@/components/features/sessions/SessionManagerMUI';
import { CostTrackerMUI } from '@/components/features/analytics/CostTrackerMUI';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';
import { useSessionPersistence } from '@/lib/hooks/useSessionPersistence';
import { OrchestrationSession } from '@/lib/types/khive';
import { Box, Typography, Card, CardContent, Chip, Button, Tabs, Tab, Grid, LinearProgress } from '@mui/material';

export function MonitoringDashboard() {
  const [selectedSession, setSelectedSession] = useState<OrchestrationSession | null>(null);
  const [activeTab, setActiveTab] = useState<0 | 1 | 2>(0); // 0=sessions, 1=costs, 2=health
  
  const { connected, daemonStatus, connectionHealth } = useKhiveWebSocket();
  const { 
    activeSessionId, 
    setActiveSession, 
    costBudgets 
  } = useSessionPersistence();

  const handleSessionSelect = (session: OrchestrationSession) => {
    setSelectedSession(session);
    setActiveSession(session.sessionId);
  };

  const getHealthStatusColor = () => {
    if (!connected) return 'error';
    if (daemonStatus.health === 'healthy') return 'success';
    if (daemonStatus.health === 'degraded') return 'warning';
    return 'error';
  };

  return (
    <Box sx={{ height: '100%', overflow: 'auto', p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Real-time Monitoring Dashboard
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Chip
            label={connected ? 'Connected' : 'Disconnected'}
            color={connected ? 'success' : 'error'}
          />
          <Chip
            label={daemonStatus.health || 'unknown'}
            color={getHealthStatusColor()}
          />
        </Box>
      </Box>

      {/* System Health Overview */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Connection Status
                  </Typography>
                  <Typography 
                    variant="h4" 
                    sx={{ color: connected ? 'success.main' : 'error.main' }}
                  >
                    {connected ? 'Online' : 'Offline'}
                  </Typography>
                </Box>
                <Box 
                  sx={{ 
                    width: 12, 
                    height: 12, 
                    borderRadius: '50%',
                    bgcolor: connected ? 'success.main' : 'error.main',
                    animation: 'pulse 2s infinite'
                  }} 
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Active Sessions
              </Typography>
              <Typography variant="h4" color="primary.main">
                {daemonStatus.active_sessions || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {connectionHealth.latency}ms latency
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                Total Agents
              </Typography>
              <Typography variant="h4" color="secondary.main">
                {daemonStatus.total_agents || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {connectionHealth.reconnectCount} reconnects
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">
                System Uptime
              </Typography>
              <Typography variant="h4" color="warning.main">
                {daemonStatus.uptime ? Math.round(daemonStatus.uptime / 3600) : 0}h
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {Math.round(daemonStatus.cpu_usage || 0)}% CPU
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tab Navigation */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab label="Session Management" />
          <Tab label="Cost Tracking" />
          <Tab label="System Health" />
        </Tabs>
      </Box>

      {/* Tab Content */}
      <Box>
        {activeTab === 0 && (
          <Box>
            <SessionManagerMUI
              showControls={true}
              onSessionSelect={handleSessionSelect}
            />
            
            {selectedSession && (
              <Card sx={{ mt: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Session Details: {selectedSession.flowName}
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6} md={3}>
                      <Typography variant="body2" fontWeight="medium">Status</Typography>
                      <Chip label={selectedSession.status} size="small" />
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="body2" fontWeight="medium">Pattern</Typography>
                      <Typography variant="body2">{selectedSession.pattern || 'Expert'}</Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="body2" fontWeight="medium">Agents</Typography>
                      <Typography variant="body2">{selectedSession.agents?.length || 0}</Typography>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Typography variant="body2" fontWeight="medium">Duration</Typography>
                      <Typography variant="body2">{Math.round(selectedSession.duration)}s</Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            )}
          </Box>
        )}

        {activeTab === 1 && (
          <CostTrackerMUI
            coordinationId={selectedSession?.coordination_id}
            sessionId={activeSessionId}
            showDetails={true}
            autoRefresh={true}
            budgetLimit={
              selectedSession?.coordination_id 
                ? costBudgets[selectedSession.coordination_id] 
                : undefined
            }
            onBudgetExceeded={(current, limit) => {
              console.warn(`Budget exceeded: $${current.toFixed(4)} > $${limit.toFixed(4)}`);
            }}
          />
        )}

        {activeTab === 2 && (
          <Box>
            <Card sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Connection Health</Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Typography variant="body2" fontWeight="medium">Status</Typography>
                    <Typography 
                      variant="body2" 
                      sx={{ color: connectionHealth.status === 'connected' ? 'success.main' : 'error.main' }}
                    >
                      {connectionHealth.status}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="body2" fontWeight="medium">Latency</Typography>
                    <Typography variant="body2">{connectionHealth.latency}ms</Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="body2" fontWeight="medium">Queue Size</Typography>
                    <Typography variant="body2">{connectionHealth.queueSize}</Typography>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Typography variant="body2" fontWeight="medium">Failures</Typography>
                    <Typography variant="body2">{connectionHealth.consecutiveFailures}</Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>System Resources</Typography>
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'between', mb: 1 }}>
                    <Typography variant="body2">Memory Usage</Typography>
                    <Typography variant="body2">{Math.round(daemonStatus.memory_usage || 0)}%</Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={Math.min(daemonStatus.memory_usage || 0, 100)}
                    color={(daemonStatus.memory_usage || 0) > 80 ? 'error' : 
                           (daemonStatus.memory_usage || 0) > 60 ? 'warning' : 'success'}
                  />
                </Box>

                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'between', mb: 1 }}>
                    <Typography variant="body2">CPU Usage</Typography>
                    <Typography variant="body2">{Math.round(daemonStatus.cpu_usage || 0)}%</Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={Math.min(daemonStatus.cpu_usage || 0, 100)}
                    color={(daemonStatus.cpu_usage || 0) > 80 ? 'error' : 
                           (daemonStatus.cpu_usage || 0) > 60 ? 'warning' : 'success'}
                  />
                </Box>
              </CardContent>
            </Card>
          </Box>
        )}
      </Box>
    </Box>
  );
}