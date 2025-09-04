"use client";

import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Chip,
  Divider,
  useTheme,
  alpha
} from '@mui/material';
import {
  PlayArrow as PlanIcon,
  Construction as ComposeIcon,
  Hub as CoordinateIcon,
  Visibility as MonitorIcon,
  Add as AddIcon,
  Settings as SettingsIcon,
  Refresh as RefreshIcon,
  FolderOpen as ProjectIcon,
  CheckCircle as CompletedIcon,
  RadioButtonUnchecked as PendingIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';

interface Session {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed' | 'pending';
  createdAt: string;
  agents: number;
  progress?: number;
}

interface ProfessionalWorkspaceProps {
  className?: string;
}

/**
 * Professional KHIVE Workspace
 * 
 * Clean 3-panel layout inspired by Ocean's document processing app:
 * - Left Panel: Session/Project Management
 * - Center Panel: Main work area for orchestration and results
 * - Right Panel: Direct action controls
 * 
 * Professional design with direct access to KHIVE functionality.
 * No modals or conversational interfaces - just efficient workflow tools.
 */
export function ProfessionalWorkspace({ className }: ProfessionalWorkspaceProps) {
  const theme = useTheme();
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<'overview' | 'orchestration' | 'results' | 'logs'>('overview');
  
  const { 
    connected, 
    sessions, 
    events, 
    sendCommand, 
    daemonStatus 
  } = useKhiveWebSocket();

  // Mock sessions for demo - replace with real data
  const mockSessions: Session[] = [
    {
      id: '1',
      name: 'Project Analysis',
      status: 'running',
      createdAt: '2025-09-04T10:30:00Z',
      agents: 3,
      progress: 65
    },
    {
      id: '2', 
      name: 'System Architecture Review',
      status: 'completed',
      createdAt: '2025-09-04T09:15:00Z',
      agents: 5,
      progress: 100
    },
    {
      id: '3',
      name: 'Performance Optimization',
      status: 'pending',
      createdAt: '2025-09-04T11:00:00Z',
      agents: 2,
      progress: 0
    }
  ];

  const getStatusIcon = (status: Session['status']) => {
    switch (status) {
      case 'completed':
        return <CompletedIcon sx={{ color: theme.palette.success.main, fontSize: 16 }} />;
      case 'running':
        return <RefreshIcon sx={{ color: theme.palette.primary.main, fontSize: 16 }} />;
      case 'failed':
        return <ErrorIcon sx={{ color: theme.palette.error.main, fontSize: 16 }} />;
      default:
        return <PendingIcon sx={{ color: theme.palette.grey[400], fontSize: 16 }} />;
    }
  };

  const getStatusChip = (status: Session['status']) => {
    const colors = {
      completed: 'success' as const,
      running: 'primary' as const,
      failed: 'error' as const,
      pending: 'default' as const
    };

    return (
      <Chip
        label={status.charAt(0).toUpperCase() + status.slice(1)}
        size="small"
        color={colors[status]}
        variant="filled"
      />
    );
  };

  // Direct action handlers
  const handlePlanOrchestration = () => {
    console.log('Planning new orchestration...');
    sendCommand('khive plan "New orchestration task"');
  };

  const handleComposeAgent = () => {
    console.log('Composing new agent...');
    sendCommand('khive compose researcher -d software-architecture');
  };

  const handleCoordinate = () => {
    console.log('Opening coordination interface...');
    setActiveView('orchestration');
  };

  const handleMonitor = () => {
    console.log('Opening monitoring dashboard...');
    setActiveView('logs');
  };

  return (
    <Box 
      className={className}
      data-testid="professional-workspace"
      sx={{ 
        height: '100vh',
        display: 'flex',
        backgroundColor: theme.palette.grey[50]
      }}
    >
      {/* Left Panel - Session Management */}
      <Paper
        data-testid="left-panel-sessions"
        elevation={1}
        sx={{
          width: 320,
          borderRadius: 0,
          borderRight: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Header */}
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, color: theme.palette.text.primary }}>
              Sessions
            </Typography>
            <IconButton size="small" onClick={() => console.log('Add session')}>
              <AddIcon />
            </IconButton>
          </Box>
          <Typography variant="body2" color="text.secondary">
            Manage your KHIVE orchestration sessions
          </Typography>
        </Box>

        {/* Session List */}
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          <List sx={{ p: 0 }}>
            {mockSessions.map((session) => (
              <ListItem
                key={session.id}
                button
                selected={selectedSession === session.id}
                onClick={() => setSelectedSession(session.id)}
                sx={{
                  borderBottom: `1px solid ${alpha(theme.palette.divider, 0.5)}`,
                  '&:hover': {
                    backgroundColor: alpha(theme.palette.primary.main, 0.04)
                  },
                  '&.Mui-selected': {
                    backgroundColor: alpha(theme.palette.primary.main, 0.08),
                    '&:hover': {
                      backgroundColor: alpha(theme.palette.primary.main, 0.12)
                    }
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  {getStatusIcon(session.status)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {session.name}
                    </Typography>
                  }
                  secondary={
                    <Box sx={{ mt: 0.5 }}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {session.agents} agents • {new Date(session.createdAt).toLocaleDateString()}
                      </Typography>
                      <Box sx={{ mt: 0.5 }}>
                        {getStatusChip(session.status)}
                      </Box>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        </Box>

        {/* Status Footer */}
        <Box sx={{ p: 2, borderTop: `1px solid ${theme.palette.divider}`, backgroundColor: theme.palette.grey[25] }}>
          <Typography variant="caption" color="text.secondary" display="block">
            KHIVE Daemon: {connected ? 'Connected' : 'Disconnected'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Status: {daemonStatus?.health || 'Unknown'}
          </Typography>
        </Box>
      </Paper>

      {/* Center Panel - Main Work Area */}
      <Box data-testid="center-panel-workspace" sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Main Content Header */}
        <Paper
          elevation={0}
          sx={{
            p: 2,
            borderBottom: `1px solid ${theme.palette.divider}`,
            backgroundColor: 'white'
          }}
        >
          <Typography variant="h5" sx={{ fontWeight: 600, color: theme.palette.text.primary }}>
            {selectedSession 
              ? mockSessions.find(s => s.id === selectedSession)?.name || 'Orchestration Workspace'
              : 'KHIVE Orchestration Workspace'
            }
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {selectedSession 
              ? 'View and manage your orchestration session'
              : 'Select a session to view orchestration details and results'
            }
          </Typography>
        </Paper>

        {/* Main Content Area */}
        <Box sx={{ flex: 1, p: 3, overflow: 'auto' }}>
          {selectedSession ? (
            <Box>
              <Typography variant="h6" gutterBottom>
                Session Details
              </Typography>
              <Paper elevation={1} sx={{ p: 3, mb: 3 }}>
                <Typography variant="body1">
                  Orchestration session content will be displayed here.
                  This includes agent coordination, progress tracking, and results visualization.
                </Typography>
              </Paper>
              
              {/* Placeholder for orchestration visualization */}
              <Paper elevation={1} sx={{ p: 3, minHeight: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography variant="body2" color="text.secondary" align="center">
                  Orchestration Visualization
                  <br />
                  Agent coordination, progress, and results will be displayed here
                </Typography>
              </Paper>
            </Box>
          ) : (
            <Box sx={{ 
              height: '100%', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              flexDirection: 'column'
            }}>
              <ProjectIcon sx={{ fontSize: 64, color: theme.palette.grey[300], mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No Session Selected
              </Typography>
              <Typography variant="body2" color="text.secondary" align="center" sx={{ maxWidth: 300 }}>
                Select a session from the left panel to view orchestration details, 
                or create a new session using the action controls.
              </Typography>
            </Box>
          )}
        </Box>
      </Box>

      {/* Right Panel - Action Controls */}
      <Paper
        data-testid="right-panel-actions"
        elevation={1}
        sx={{
          width: 280,
          borderRadius: 0,
          borderLeft: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Actions Header */}
        <Box sx={{ p: 2, borderBottom: `1px solid ${theme.palette.divider}` }}>
          <Typography variant="h6" sx={{ fontWeight: 600, color: theme.palette.text.primary }}>
            Actions
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Direct access to KHIVE commands
          </Typography>
        </Box>

        {/* Primary Actions */}
        <Box sx={{ p: 2 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, fontWeight: 500 }}>
            Orchestration
          </Typography>
          
          <Button
            fullWidth
            variant="contained"
            startIcon={<PlanIcon />}
            onClick={handlePlanOrchestration}
            sx={{ mb: 1.5, justifyContent: 'flex-start', textTransform: 'none', py: 1 }}
          >
            Plan Orchestration
          </Button>
          
          <Button
            fullWidth
            variant="outlined"
            startIcon={<ComposeIcon />}
            onClick={handleComposeAgent}
            sx={{ mb: 1.5, justifyContent: 'flex-start', textTransform: 'none', py: 1 }}
          >
            Compose Agent
          </Button>
          
          <Button
            fullWidth
            variant="outlined"
            startIcon={<CoordinateIcon />}
            onClick={handleCoordinate}
            sx={{ mb: 1.5, justifyContent: 'flex-start', textTransform: 'none', py: 1 }}
          >
            Coordinate
          </Button>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, fontWeight: 500 }}>
            Monitoring
          </Typography>

          <Button
            fullWidth
            variant="outlined"
            startIcon={<MonitorIcon />}
            onClick={handleMonitor}
            sx={{ mb: 1.5, justifyContent: 'flex-start', textTransform: 'none', py: 1 }}
          >
            Monitor Sessions
          </Button>

          <Button
            fullWidth
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => console.log('Open settings')}
            sx={{ justifyContent: 'flex-start', textTransform: 'none', py: 1 }}
          >
            Settings
          </Button>
        </Box>

        {/* Status Section */}
        <Box sx={{ mt: 'auto', p: 2, borderTop: `1px solid ${theme.palette.divider}`, backgroundColor: theme.palette.grey[25] }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1.5, fontWeight: 500 }}>
            System Status
          </Typography>
          
          <Box sx={{ mb: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Connection Status
            </Typography>
            <Chip
              label={connected ? 'Connected' : 'Disconnected'}
              size="small"
              color={connected ? 'success' : 'error'}
              variant="filled"
              sx={{ ml: 1 }}
            />
          </Box>
          
          <Typography variant="caption" color="text.secondary" display="block">
            Active Sessions: {mockSessions.filter(s => s.status === 'running').length}
          </Typography>
          
          <Typography variant="caption" color="text.secondary" display="block">
            Total Agents: {mockSessions.reduce((sum, s) => sum + s.agents, 0)}
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
}