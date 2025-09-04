"use client";

import { useState, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Card,
  CardContent,
  IconButton,
  Fab,
  useTheme,
  alpha
} from '@mui/material';
import {
  AutoAwesome as AIIcon,
  TrendingUp as AnalyticsIcon,
  Visibility as MonitorIcon,
  Construction as BuildIcon,
  Settings as SettingsIcon,
  Close as CloseIcon
} from '@mui/icons-material';
import { ConversationalInterface } from '@/components/ui/ConversationalInterface';
import { ProjectDashboard } from './ProjectDashboard';
import { ProgressNarrative } from './ProgressNarrative';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';

interface AIWorkspaceProps {
  initialView?: 'welcome' | 'project' | 'progress' | 'analytics' | 'settings';
}

type WorkspaceView = 'welcome' | 'project' | 'progress' | 'analytics' | 'settings';

interface QuickAction {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  action: () => void;
  color: string;
}

/**
 * AIWorkspace - Revolutionary Simplified Interface
 * 
 * Replaces the complex 3-pane CommandCenter with a focused, 
 * single-purpose workspace that adapts to user needs.
 * 
 * Key Features:
 * - Single-focus design instead of overwhelming 3-pane layout
 * - Context-aware content based on user activity
 * - Natural integration with conversational AI
 * - Progressive disclosure of advanced features
 * - User-centric language and workflows
 */
export function AIWorkspace({ initialView = 'welcome' }: AIWorkspaceProps) {
  const theme = useTheme();
  const [currentView, setCurrentView] = useState<WorkspaceView>(initialView);
  const [conversationOpen, setConversationOpen] = useState(false);
  const [activeWorkflow, setActiveWorkflow] = useState<string | null>(null);
  
  const { 
    connected, 
    sessions, 
    events, 
    sendCommand, 
    daemonStatus 
  } = useKhiveWebSocket();

  // Handle AI intent execution
  const handleExecuteIntent = useCallback(async (intent: string, originalText: string) => {
    console.log('Executing intent:', intent, 'from text:', originalText);
    
    // Map intents to specific actions and views
    switch (intent) {
      case 'analyze_project':
        setCurrentView('analytics');
        setActiveWorkflow('project-analysis');
        await sendCommand('khive plan "Analyze current project performance and metrics"');
        break;
        
      case 'create_workflow':
        setCurrentView('project');
        setActiveWorkflow('workflow-creation');
        await sendCommand('khive plan "Create new workflow based on user requirements"');
        break;
        
      case 'setup_monitoring':
        setCurrentView('progress');
        setActiveWorkflow('monitoring-setup');
        await sendCommand('khive plan "Set up comprehensive system monitoring"');
        break;
        
      case 'optimize_system':
        setCurrentView('analytics');
        setActiveWorkflow('system-optimization');
        await sendCommand('khive plan "Optimize system performance and efficiency"');
        break;
        
      case 'get_help':
        setCurrentView('welcome');
        break;
        
      case 'manage_resources':
        setCurrentView('settings');
        break;
        
      default:
        // General assistance - create custom workflow
        setCurrentView('progress');
        setActiveWorkflow('custom-assistance');
        await sendCommand(`khive plan "${originalText}"`);
        break;
    }
  }, [sendCommand]);

  // Quick actions for the welcome view
  const quickActions: QuickAction[] = [
    {
      id: 'analyze',
      label: 'Analyze My Project',
      description: 'Get insights into performance, dependencies, and optimization opportunities',
      icon: <AnalyticsIcon />,
      action: () => setConversationOpen(true),
      color: theme.palette.info.main
    },
    {
      id: 'create',
      label: 'Create New Workflow',
      description: 'Build automated processes tailored to your specific needs',
      icon: <BuildIcon />,
      action: () => setConversationOpen(true),
      color: theme.palette.success.main
    },
    {
      id: 'monitor',
      label: 'Monitor Progress', 
      description: 'Track your ongoing work and system health in real-time',
      icon: <MonitorIcon />,
      action: () => setCurrentView('progress'),
      color: theme.palette.warning.main
    },
    {
      id: 'manage',
      label: 'Manage Settings',
      description: 'Configure your workspace and system preferences',
      icon: <SettingsIcon />,
      action: () => setCurrentView('settings'),
      color: theme.palette.secondary.main
    }
  ];

  // Render current view content
  const renderViewContent = () => {
    switch (currentView) {
      case 'project':
        return <ProjectDashboard activeWorkflow={activeWorkflow} />;
      
      case 'progress':
        return <ProgressNarrative activeWorkflow={activeWorkflow} />;
        
      case 'analytics':
        return (
          <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>
              Project Analytics
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              AI-powered insights into your project performance, resource usage, and optimization opportunities.
            </Typography>
            {/* Analytics dashboard would be implemented here */}
            <Card sx={{ mt: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance Overview
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {sessions.length} active sessions • {events.length} recent events
                </Typography>
              </CardContent>
            </Card>
          </Box>
        );
        
      case 'settings':
        return (
          <Box sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>
              Workspace Settings
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              Configure your AI assistant and workspace preferences.
            </Typography>
            {/* Settings interface would be implemented here */}
            <Card sx={{ mt: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  System Status
                </Typography>
                <Typography variant="body2" color={connected ? 'success.main' : 'error.main'}>
                  {connected ? '✅ Connected to KHIVE' : '❌ Disconnected'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Daemon: {daemonStatus.running ? 'Running' : 'Stopped'}
                </Typography>
              </CardContent>
            </Card>
          </Box>
        );
        
      default: // welcome
        return (
          <Box sx={{ 
            flex: 1, 
            display: 'flex', 
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            p: 4,
            textAlign: 'center'
          }}>
            {/* Hero Section */}
            <Box sx={{ mb: 6, maxWidth: 600 }}>
              <AIIcon sx={{ 
                fontSize: 64, 
                color: theme.palette.primary.main,
                mb: 2 
              }} />
              <Typography variant="h3" gutterBottom sx={{ fontWeight: 600 }}>
                Welcome to KHIVE AI
              </Typography>
              <Typography variant="h6" color="text.secondary" paragraph>
                Your intelligent project assistant. Just tell me what you want to accomplish,
                and I'll orchestrate the right actions for you.
              </Typography>
            </Box>

            {/* Quick Actions Grid */}
            <Box sx={{ 
              display: 'grid', 
              gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
              gap: 3,
              maxWidth: 800,
              width: '100%',
              mb: 4
            }}>
              {quickActions.map((action) => (
                <Card 
                  key={action.id}
                  sx={{ 
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    borderLeft: `4px solid ${action.color}`,
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: theme.shadows[8]
                    }
                  }}
                  onClick={action.action}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Box sx={{ 
                        p: 1, 
                        borderRadius: 2, 
                        bgcolor: alpha(action.color, 0.1),
                        color: action.color,
                        mr: 2
                      }}>
                        {action.icon}
                      </Box>
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {action.label}
                      </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {action.description}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Box>

            {/* Current Status */}
            {(sessions.length > 0 || events.length > 0) && (
              <Paper sx={{ 
                p: 3, 
                maxWidth: 600, 
                width: '100%',
                bgcolor: alpha(theme.palette.primary.main, 0.05),
                border: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`
              }}>
                <Typography variant="h6" gutterBottom sx={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 1 
                }}>
                  <MonitorIcon />
                  Current Activity
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {sessions.length} active workflows • {events.length} recent updates
                </Typography>
                <Button 
                  variant="contained" 
                  sx={{ mt: 2 }}
                  onClick={() => setCurrentView('progress')}
                >
                  View Progress
                </Button>
              </Paper>
            )}
          </Box>
        );
    }
  };

  return (
    <Box sx={{ 
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      bgcolor: 'background.default'
    }}>
      {/* Simple Top Bar */}
      {currentView !== 'welcome' && (
        <Paper sx={{ 
          p: 2, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          borderRadius: 0,
          boxShadow: 1
        }}>
          <Typography variant="h6" sx={{ 
            textTransform: 'capitalize',
            fontWeight: 500
          }}>
            {currentView === 'progress' ? 'Activity Monitor' : 
             currentView === 'project' ? 'Project Dashboard' :
             currentView === 'analytics' ? 'Analytics' : 'Settings'}
          </Typography>
          
          <IconButton 
            onClick={() => setCurrentView('welcome')}
            size="small"
          >
            <CloseIcon />
          </IconButton>
        </Paper>
      )}

      {/* Main Content Area */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {renderViewContent()}
      </Box>

      {/* Floating AI Assistant Button */}
      <Fab
        data-testid="ai-assistant-fab"
        color="primary"
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          zIndex: 1000
        }}
        onClick={() => setConversationOpen(true)}
      >
        <AIIcon />
      </Fab>

      {/* Conversational Interface */}
      <ConversationalInterface
        open={conversationOpen}
        onClose={() => setConversationOpen(false)}
        onExecuteIntent={handleExecuteIntent}
        onNavigate={(view) => {
          // Map old navigation to new simplified views
          switch (view) {
            case 'planning':
              setCurrentView('project');
              break;
            case 'monitoring':
              setCurrentView('progress');
              break;
            case 'analytics':
              setCurrentView('analytics');
              break;
            case 'settings':
              setCurrentView('settings');
              break;
            default:
              setCurrentView('welcome');
          }
        }}
      />
    </Box>
  );
}