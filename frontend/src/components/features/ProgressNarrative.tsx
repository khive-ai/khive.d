"use client";

import { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Avatar,
  Chip,
  IconButton,
  Collapse,
  Button,
  useTheme,
  alpha,
  LinearProgress,
  Paper,
  Divider
} from '@mui/material';
import {
  ExpandMore as ExpandIcon,
  CheckCircle as CompleteIcon,
  PlayArrow as ActiveIcon,
  Schedule as PendingIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  AutoAwesome as AIIcon,
  Group as TeamIcon,
  Insights as InsightsIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';

interface ProgressNarrativeProps {
  activeWorkflow?: string | null;
}

interface NarrativeEvent {
  id: string;
  timestamp: Date;
  type: 'milestone' | 'update' | 'insight' | 'error' | 'completion';
  title: string;
  description: string;
  details?: string;
  agent?: {
    name: string;
    role: string;
    avatar: string;
  };
  progress?: number;
  importance: 'low' | 'medium' | 'high';
  relatedWorkflow?: string;
}

/**
 * ProgressNarrative - Human-Friendly Orchestration Updates
 * 
 * Transforms technical system events into a readable narrative
 * that users can understand and follow.
 * 
 * Key Features:
 * - Human-readable event descriptions
 * - Story-like progress flow
 * - Visual timeline with context
 * - Agent actions explained in plain language
 * - Meaningful progress indicators
 */
export function ProgressNarrative({ activeWorkflow }: ProgressNarrativeProps) {
  const theme = useTheme();
  const { events, sessions, agents } = useKhiveWebSocket();
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [narrativeEvents, setNarrativeEvents] = useState<NarrativeEvent[]>([]);

  // Transform system events into user-friendly narrative
  const transformEventsToNarrative = useMemo(() => {
    const narratives: NarrativeEvent[] = [];

    // Process coordination events into human-readable stories
    events.forEach((event, index) => {
      const narrative = createNarrativeFromEvent(event, agents);
      if (narrative) {
        narratives.push(narrative);
      }
    });

    // Add session milestones
    sessions.forEach(session => {
      const sessionNarrative = createSessionNarrative(session, agents);
      if (sessionNarrative) {
        narratives.push(sessionNarrative);
      }
    });

    // Sort by timestamp, most recent first
    return narratives.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  }, [events, sessions, agents]);

  useEffect(() => {
    setNarrativeEvents(transformEventsToNarrative);
  }, [transformEventsToNarrative]);

  // Create human-readable narrative from system events
  const createNarrativeFromEvent = (event: any, agents: any[]): NarrativeEvent | null => {
    const agent = agents.find(a => a.id === event.agent_id);
    const timestamp = new Date(event.timestamp || Date.now());

    switch (event.type) {
      case 'agent_spawn':
        return {
          id: `narrative_${event.id || Math.random()}`,
          timestamp,
          type: 'milestone',
          title: `${getAgentFriendlyName(agent)} joined the team`,
          description: `A ${agent?.role || 'specialist'} agent has been activated to help with your project`,
          details: `This agent specializes in ${getAgentExpertise(agent?.role)} and will work on specific tasks as needed.`,
          agent: agent ? {
            name: getAgentFriendlyName(agent),
            role: capitalizeRole(agent.role),
            avatar: getAgentAvatar(agent.role)
          } : undefined,
          importance: 'medium',
          relatedWorkflow: event.session_id
        };

      case 'task_start':
        return {
          id: `narrative_${event.id || Math.random()}`,
          timestamp,
          type: 'update',
          title: `Started working on: ${humanizeTaskName(event.task_name || 'New Task')}`,
          description: `Your AI team has begun processing this task with dedicated focus`,
          details: `The system is allocating resources and coordinating multiple agents to ensure efficient completion.`,
          agent: agent ? {
            name: getAgentFriendlyName(agent),
            role: capitalizeRole(agent.role),
            avatar: getAgentAvatar(agent.role)
          } : undefined,
          importance: 'high',
          relatedWorkflow: event.session_id
        };

      case 'task_complete':
        return {
          id: `narrative_${event.id || Math.random()}`,
          timestamp,
          type: 'completion',
          title: `Completed: ${humanizeTaskName(event.task_name || 'Task')}`,
          description: `Successfully finished processing with high-quality results`,
          details: `All objectives have been met and the output is ready for your review.`,
          agent: agent ? {
            name: getAgentFriendlyName(agent),
            role: capitalizeRole(agent.role),
            avatar: getAgentAvatar(agent.role)
          } : undefined,
          progress: 100,
          importance: 'high',
          relatedWorkflow: event.session_id
        };

      case 'coordination_update':
        return {
          id: `narrative_${event.id || Math.random()}`,
          timestamp,
          type: 'insight',
          title: `Team coordination update`,
          description: `Agents are collaborating efficiently and sharing insights`,
          details: `The AI team is working together seamlessly, with each agent contributing their specialized expertise.`,
          importance: 'low',
          relatedWorkflow: event.session_id
        };

      default:
        return null;
    }
  };

  const createSessionNarrative = (session: any, agents: any[]): NarrativeEvent | null => {
    if (!session.created_at) return null;

    const timestamp = new Date(session.created_at);
    const sessionAgents = agents.filter(a => session.active_agents?.includes(a.id));

    return {
      id: `session_${session.sessionId}`,
      timestamp,
      type: 'milestone',
      title: `Workflow "${humanizeSessionName(session.sessionId)}" initiated`,
      description: `Started a new workflow with ${sessionAgents.length || 'multiple'} specialized agents`,
      details: `This workflow will coordinate various AI agents to accomplish your objectives efficiently and accurately.`,
      agent: sessionAgents.length > 0 ? {
        name: `Team of ${sessionAgents.length}`,
        role: 'Coordination Team',
        avatar: '👥'
      } : undefined,
      importance: 'high',
      relatedWorkflow: session.sessionId
    };
  };

  // Helper functions for humanizing system data
  const getAgentFriendlyName = (agent: any): string => {
    if (!agent) return 'AI Assistant';
    const roleNames = {
      analyst: 'Data Analyst',
      researcher: 'Research Specialist', 
      architect: 'System Designer',
      implementer: 'Implementation Expert',
      reviewer: 'Quality Reviewer',
      tester: 'Quality Tester',
      orchestrator: 'Project Coordinator'
    };
    return roleNames[agent.role as keyof typeof roleNames] || 'AI Specialist';
  };

  const getAgentExpertise = (role: string): string => {
    const expertise = {
      analyst: 'data analysis and pattern recognition',
      researcher: 'information gathering and research',
      architect: 'system design and planning',
      implementer: 'building and executing solutions',
      reviewer: 'quality assurance and validation',
      tester: 'testing and verification',
      orchestrator: 'coordination and management'
    };
    return expertise[role as keyof typeof expertise] || 'specialized tasks';
  };

  const getAgentAvatar = (role: string): string => {
    const avatars = {
      analyst: '📊',
      researcher: '🔍',
      architect: '🏗️',
      implementer: '⚒️',
      reviewer: '👁️',
      tester: '🧪',
      orchestrator: '🎭'
    };
    return avatars[role as keyof typeof avatars] || '🤖';
  };

  const capitalizeRole = (role: string): string => {
    return role.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  const humanizeTaskName = (taskName: string): string => {
    return taskName
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .replace(/\b\w/g, l => l.toUpperCase())
      .trim();
  };

  const humanizeSessionName = (sessionId: string): string => {
    // Extract meaningful parts from session ID
    const parts = sessionId.split('_');
    if (parts.length > 1) {
      return `${parts[0].toUpperCase()} Project`;
    }
    return `Project ${sessionId.substring(0, 8)}`;
  };

  const getEventIcon = (type: NarrativeEvent['type']) => {
    switch (type) {
      case 'completion': return <CompleteIcon />;
      case 'milestone': return <AIIcon />;
      case 'update': return <ActiveIcon />;
      case 'insight': return <InsightsIcon />;
      case 'error': return <ErrorIcon />;
      default: return <InfoIcon />;
    }
  };

  const getEventColor = (type: NarrativeEvent['type']) => {
    switch (type) {
      case 'completion': return theme.palette.success.main;
      case 'milestone': return theme.palette.primary.main;
      case 'update': return theme.palette.info.main;
      case 'insight': return theme.palette.secondary.main;
      case 'error': return theme.palette.error.main;
      default: return theme.palette.grey[500];
    }
  };

  const getImportanceColor = (importance: NarrativeEvent['importance']) => {
    switch (importance) {
      case 'high': return theme.palette.error.main;
      case 'medium': return theme.palette.warning.main;
      case 'low': return theme.palette.success.main;
      default: return theme.palette.grey[500];
    }
  };

  const toggleEventDetails = (eventId: string) => {
    setExpandedEvents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(eventId)) {
        newSet.delete(eventId);
      } else {
        newSet.add(eventId);
      }
      return newSet;
    });
  };

  const filteredEvents = activeWorkflow 
    ? narrativeEvents.filter(event => event.relatedWorkflow === activeWorkflow)
    : narrativeEvents;

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Progress Story
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Follow along as your AI team works on your project
          </Typography>
          {activeWorkflow && (
            <Chip 
              label={`Workflow: ${humanizeSessionName(activeWorkflow)}`}
              sx={{ mt: 1 }}
              color="primary"
              variant="outlined"
            />
          )}
        </Box>
        <IconButton onClick={() => window.location.reload()}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {/* Progress Summary */}
      {narrativeEvents.length > 0 && (
        <Card sx={{ mb: 4, bgcolor: alpha(theme.palette.primary.main, 0.05) }}>
          <CardContent>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <InsightsIcon />
              Activity Summary
            </Typography>
            <Box sx={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              <Box>
                <Typography variant="h4" color="primary.main">
                  {narrativeEvents.filter(e => e.type === 'completion').length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Tasks Completed
                </Typography>
              </Box>
              <Box>
                <Typography variant="h4" color="info.main">
                  {narrativeEvents.filter(e => e.type === 'update').length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Active Tasks
                </Typography>
              </Box>
              <Box>
                <Typography variant="h4" color="secondary.main">
                  {narrativeEvents.filter(e => e.type === 'insight').length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Insights Generated
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Progress Timeline */}
      {filteredEvents.length === 0 ? (
        <Card sx={{ textAlign: 'center', py: 6 }}>
          <CardContent>
            <AIIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              {activeWorkflow ? 'No activity for this workflow yet' : 'No activity to show'}
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              {activeWorkflow 
                ? 'This workflow is getting started. Activity will appear here as work progresses.'
                : 'Start a conversation with the AI assistant to begin seeing progress updates.'
              }
            </Typography>
            <Button variant="contained" onClick={() => {/* Open conversational interface */}}>
              Start New Workflow
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Box sx={{ position: 'relative' }}>
          {/* Timeline Line */}
          <Box sx={{
            position: 'absolute',
            left: 24,
            top: 0,
            bottom: 0,
            width: 2,
            bgcolor: theme.palette.divider,
            zIndex: 0
          }} />
          
          {filteredEvents.map((event, index) => (
            <Box key={event.id} sx={{ position: 'relative', pb: 3 }}>
              {/* Timeline Dot */}
              <Box sx={{
                position: 'absolute',
                left: 16,
                top: 8,
                width: 16,
                height: 16,
                borderRadius: '50%',
                bgcolor: getEventColor(event.type),
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1,
                fontSize: '12px'
              }}>
                {getEventIcon(event.type)}
              </Box>
              
              {/* Event Card */}
              <Box sx={{ ml: 6 }}>
                <Card sx={{ 
                  bgcolor: event.importance === 'high' 
                    ? alpha(getEventColor(event.type), 0.05)
                    : 'background.paper',
                  border: event.importance === 'high' 
                    ? `1px solid ${alpha(getEventColor(event.type), 0.3)}`
                    : 'none'
                }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Typography variant="h6" gutterBottom>
                        {event.title}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip
                          label={event.importance}
                          size="small"
                          sx={{ 
                            bgcolor: alpha(getImportanceColor(event.importance), 0.1),
                            color: getImportanceColor(event.importance),
                            fontSize: '0.75rem'
                          }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {event.timestamp.toLocaleTimeString()}
                        </Typography>
                      </Box>
                    </Box>

                    <Typography variant="body1" color="text.secondary" paragraph>
                      {event.description}
                    </Typography>

                    {/* Agent Information */}
                    {event.agent && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                        <Avatar sx={{ bgcolor: 'transparent', color: 'text.primary' }}>
                          {event.agent.avatar}
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle2">
                            {event.agent.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {event.agent.role}
                          </Typography>
                        </Box>
                      </Box>
                    )}

                    {/* Progress Bar */}
                    {event.progress !== undefined && (
                      <Box sx={{ mb: 2 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                          <Typography variant="body2" color="text.secondary">
                            Progress
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {event.progress}%
                          </Typography>
                        </Box>
                        <LinearProgress 
                          variant="determinate" 
                          value={event.progress}
                          sx={{ height: 6, borderRadius: 3 }}
                        />
                      </Box>
                    )}

                    {/* Expandable Details */}
                    {event.details && (
                      <>
                        <Button
                          size="small"
                          onClick={() => toggleEventDetails(event.id)}
                          endIcon={<ExpandIcon sx={{ 
                            transform: expandedEvents.has(event.id) ? 'rotate(180deg)' : 'rotate(0deg)',
                            transition: 'transform 0.2s'
                          }} />}
                        >
                          {expandedEvents.has(event.id) ? 'Less Details' : 'More Details'}
                        </Button>
                        
                        <Collapse in={expandedEvents.has(event.id)}>
                          <Box sx={{ mt: 2, p: 2, bgcolor: alpha(theme.palette.primary.main, 0.05), borderRadius: 1 }}>
                            <Typography variant="body2" color="text.secondary">
                              {event.details}
                            </Typography>
                          </Box>
                        </Collapse>
                      </>
                    )}
                  </CardContent>
                </Card>
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
}