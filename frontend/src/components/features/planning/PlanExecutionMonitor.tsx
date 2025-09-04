// @ts-nocheck
"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  IconButton,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  LinearProgress,
  CircularProgress,
  Alert,
  Tooltip,
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import {
  PlayArrow,
  Pause,
  Stop,
  Refresh,
  ExpandMore,
  Timeline,
  Groups,
  Assessment,
  Warning,
  CheckCircle,
  Error,
  Speed,
  MonitorHeart,
  NetworkCheck,
  Memory,
  Storage,
  TrendingUp,
  Person,
  Psychology,
  Sync,
  Schedule,
  AttachMoney,
  DataUsage
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';

import { KhiveApiService, KhiveApiError } from '@/lib/services/khiveApiService';
import { khiveWebSocketService } from '@/lib/services/khiveWebSocketService';
import { 
  PlanningResponse, 
  TaskPhase,
  CoordinationEvent,
  OrchestrationSession,
  Agent,
  SessionMetrics 
} from '@/lib/types/khive';
import { ConsensusVisualization } from './ConsensusVisualization';
import { AgentCoordinationPanel } from './AgentCoordinationPanel';

// Enhanced execution monitoring types
export interface ExecutionPhase {
  phase: TaskPhase;
  status: 'pending' | 'active' | 'completed' | 'failed' | 'blocked';
  startTime?: number;
  endTime?: number;
  duration?: number;
  progress: number; // 0-100
  agents: Agent[];
  artifacts: ExecutionArtifact[];
  metrics: PhaseMetrics;
  dependencies: string[];
  blockers: string[];
}

export interface ExecutionArtifact {
  id: string;
  name: string;
  type: 'file' | 'report' | 'data' | 'config';
  path: string;
  size: number;
  createdBy: string;
  createdAt: number;
  status: 'creating' | 'ready' | 'validated' | 'failed';
}

export interface PhaseMetrics {
  tokensUsed: number;
  apiCalls: number;
  cost: number;
  averageResponseTime: number;
  errorRate: number;
  throughput: number;
}

export interface ExecutionMetrics {
  totalCost: number;
  totalTokens: { input: number; output: number };
  totalApiCalls: number;
  executionTime: number;
  successRate: number;
  agentUtilization: number;
  resourceUsage: {
    cpu: number;
    memory: number;
    network: number;
  };
}

interface PlanExecutionMonitorProps {
  coordinationId: string;
  planningResponse: PlanningResponse;
  onPhaseComplete?: (phaseIndex: number) => void;
  onExecutionComplete?: (metrics: ExecutionMetrics) => void;
  onExecutionFailed?: (error: string) => void;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index, ...other }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`execution-tabpanel-${index}`}
      aria-labelledby={`execution-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

export function PlanExecutionMonitor({
  coordinationId,
  planningResponse,
  onPhaseComplete,
  onExecutionComplete,
  onExecutionFailed
}: PlanExecutionMonitorProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [executionPhases, setExecutionPhases] = useState<ExecutionPhase[]>([]);
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0);
  const [executionStatus, setExecutionStatus] = useState<'idle' | 'running' | 'paused' | 'completed' | 'failed'>('idle');
  const [sessions, setSessions] = useState<OrchestrationSession[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [coordinationEvents, setCoordinationEvents] = useState<CoordinationEvent[]>([]);
  const [executionMetrics, setExecutionMetrics] = useState<ExecutionMetrics | null>(null);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);

  // Initialize execution phases from planning response
  useEffect(() => {
    const phases: ExecutionPhase[] = planningResponse.phases.map((phase, index) => ({
      phase,
      status: index === 0 ? 'active' : 'pending',
      progress: 0,
      agents: phase.agents,
      artifacts: [],
      metrics: {
        tokensUsed: 0,
        apiCalls: 0,
        cost: 0,
        averageResponseTime: 0,
        errorRate: 0,
        throughput: 0
      },
      dependencies: phase.dependencies,
      blockers: []
    }));

    setExecutionPhases(phases);
  }, [planningResponse]);

  // WebSocket setup for real-time updates
  useEffect(() => {
    const handleCoordinationEvent = (event: CoordinationEvent) => {
      setCoordinationEvents(prev => [event, ...prev.slice(0, 99)]);
      updateExecutionProgress(event);
    };

    const handleSessionUpdated = (session: OrchestrationSession) => {
      setSessions(prev => {
        const existing = prev.find(s => s.sessionId === session.sessionId);
        if (existing) {
          return prev.map(s => s.sessionId === session.sessionId ? session : s);
        }
        return [...prev, session];
      });
    };

    const handleAgentUpdated = (agent: Agent) => {
      if (agent.coordination_id === coordinationId) {
        setAgents(prev => {
          const existing = prev.find(a => a.id === agent.id);
          if (existing) {
            return prev.map(a => a.id === agent.id ? agent : a);
          }
          return [...prev, agent];
        });
      }
    };

    khiveWebSocketService.on('coordination_event', handleCoordinationEvent);
    khiveWebSocketService.on('session_updated', handleSessionUpdated);
    khiveWebSocketService.on('agent_updated', handleAgentUpdated);
    khiveWebSocketService.joinCoordination(coordinationId);

    return () => {
      khiveWebSocketService.off('coordination_event', handleCoordinationEvent);
      khiveWebSocketService.off('session_updated', handleSessionUpdated);
      khiveWebSocketService.off('agent_updated', handleAgentUpdated);
      khiveWebSocketService.leaveCoordination(coordinationId);
    };
  }, [coordinationId]);

  // Periodic data refresh
  useEffect(() => {
    if (executionStatus === 'running') {
      const interval = setInterval(() => {
        refreshExecutionData();
      }, 5000);
      setRefreshInterval(interval);
      
      return () => {
        if (interval) clearInterval(interval);
      };
    } else {
      if (refreshInterval) {
        clearInterval(refreshInterval);
        setRefreshInterval(null);
      }
    }
  }, [executionStatus]);

  const updateExecutionProgress = (event: CoordinationEvent) => {
    setExecutionPhases(prev => prev.map((phase, index) => {
      if (event.type === 'task_complete' && index === currentPhaseIndex) {
        const updatedPhase = { ...phase, progress: Math.min(phase.progress + 10, 100) };
        
        // Check if phase is complete
        if (updatedPhase.progress >= 100) {
          updatedPhase.status = 'completed';
          updatedPhase.endTime = Date.now();
          updatedPhase.duration = (updatedPhase.endTime - (updatedPhase.startTime || Date.now())) / 1000;
          
          // Advance to next phase
          if (index < prev.length - 1) {
            setCurrentPhaseIndex(index + 1);
            onPhaseComplete?.(index);
          } else {
            setExecutionStatus('completed');
            onExecutionComplete?.(executionMetrics || {
              totalCost: 0,
              totalTokens: { input: 0, output: 0 },
              totalApiCalls: 0,
              executionTime: 0,
              successRate: 0,
              agentUtilization: 0,
              resourceUsage: { cpu: 0, memory: 0, network: 0 }
            });
          }
        }
        
        return updatedPhase;
      }
      return phase;
    }));
  };

  const refreshExecutionData = async () => {
    try {
      // Load sessions and agents
      const [sessionData, agentData, eventData] = await Promise.all([
        KhiveApiService.getSessionsByCoordination(coordinationId),
        KhiveApiService.getAgentsByCoordination(coordinationId),
        KhiveApiService.getCoordinationEvents(coordinationId, 50)
      ]);

      setSessions(sessionData);
      setAgents(agentData);
      setCoordinationEvents(eventData);

      // Calculate execution metrics
      const totalCost = sessionData.reduce((sum, session) => sum + (session.metrics?.cost || 0), 0);
      const totalTokens = sessionData.reduce(
        (acc, session) => ({
          input: acc.input + (session.metrics?.tokensUsed || 0),
          output: acc.output + (session.metrics?.tokensUsed || 0) // Simplified
        }),
        { input: 0, output: 0 }
      );

      const metrics: ExecutionMetrics = {
        totalCost,
        totalTokens,
        totalApiCalls: sessionData.reduce((sum, session) => sum + (session.metrics?.apiCalls || 0), 0),
        executionTime: (Date.now() - (sessions[0]?.startTime || Date.now())) / 1000,
        successRate: agentData.length > 0 ? agentData.filter(a => a.status === 'completed').length / agentData.length : 0,
        agentUtilization: agentData.filter(a => a.status === 'working' || a.status === 'active').length / Math.max(agentData.length, 1),
        resourceUsage: {
          cpu: Math.random() * 100, // Mock data - would come from system metrics
          memory: Math.random() * 100,
          network: Math.random() * 100
        }
      };

      setExecutionMetrics(metrics);
    } catch (error) {
      console.error('Failed to refresh execution data:', error);
    }
  };

  const handleExecutionControl = async (action: 'start' | 'pause' | 'stop') => {
    try {
      switch (action) {
        case 'start':
          setExecutionStatus('running');
          // Start the first phase if not already started
          if (executionPhases[0]?.status === 'pending') {
            setExecutionPhases(prev => prev.map((phase, index) => 
              index === 0 ? { ...phase, status: 'active', startTime: Date.now() } : phase
            ));
          }
          break;
        case 'pause':
          setExecutionStatus('paused');
          break;
        case 'stop':
          setExecutionStatus('idle');
          // Reset all phases
          setExecutionPhases(prev => prev.map(phase => ({
            ...phase,
            status: 'pending',
            progress: 0,
            startTime: undefined,
            endTime: undefined
          })));
          setCurrentPhaseIndex(0);
          break;
      }
    } catch (error) {
      onExecutionFailed?.(`Failed to ${action} execution: ${error}`);
    }
  };

  // Memoized calculations
  const overallProgress = useMemo(() => {
    const totalPhases = executionPhases.length;
    const completedPhases = executionPhases.filter(p => p.status === 'completed').length;
    const currentPhaseProgress = executionPhases[currentPhaseIndex]?.progress || 0;
    
    return totalPhases > 0 ? ((completedPhases + currentPhaseProgress / 100) / totalPhases) * 100 : 0;
  }, [executionPhases, currentPhaseIndex]);

  const phaseProgressData = useMemo(() => {
    return executionPhases.map((phase, index) => ({
      phase: `Phase ${index + 1}`,
      progress: phase.progress,
      status: phase.status,
      cost: phase.metrics.cost,
      tokens: phase.metrics.tokensUsed
    }));
  }, [executionPhases]);

  const renderExecutionOverview = () => (
    <Grid container spacing={2}>
      <Grid item xs={12} md={8}>
        <Card>
          <CardContent>
            <Box display="flex" justifyContent="between" alignItems="center" mb={2}>
              <Typography variant="h6" display="flex" alignItems="center" gap={1}>
                <Timeline /> Execution Progress
              </Typography>
              <Box display="flex" gap={1}>
                <Button
                  size="small"
                  variant={executionStatus === 'running' ? 'contained' : 'outlined'}
                  color="success"
                  startIcon={<PlayArrow />}
                  onClick={() => handleExecutionControl('start')}
                  disabled={executionStatus === 'completed'}
                >
                  Start
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<Pause />}
                  onClick={() => handleExecutionControl('pause')}
                  disabled={executionStatus !== 'running'}
                >
                  Pause
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  color="error"
                  startIcon={<Stop />}
                  onClick={() => handleExecutionControl('stop')}
                >
                  Stop
                </Button>
              </Box>
            </Box>

            <Typography variant="body2" color="text.secondary" gutterBottom>
              Overall Progress: {Math.round(overallProgress)}%
            </Typography>
            <LinearProgress
              variant="determinate"
              value={overallProgress}
              sx={{ height: 8, borderRadius: 4, mb: 2 }}
              color={executionStatus === 'completed' ? 'success' : 'primary'}
            />

            <Typography variant="body2" color="text.secondary">
              Phase {currentPhaseIndex + 1} of {executionPhases.length}: {executionPhases[currentPhaseIndex]?.phase.name || 'Unknown'}
            </Typography>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={4}>
        <Card>
          <CardContent>
            <Typography variant="h6" display="flex" alignItems="center" gap={1} gutterBottom>
              <Assessment /> Key Metrics
            </Typography>
            
            {executionMetrics && (
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Total Cost
                  </Typography>
                  <Typography variant="h6" display="flex" alignItems="center" gap={0.5}>
                    <AttachMoney fontSize="small" />
                    {executionMetrics.totalCost.toFixed(4)}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Success Rate
                  </Typography>
                  <Typography variant="h6">
                    {Math.round(executionMetrics.successRate * 100)}%
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Active Agents
                  </Typography>
                  <Typography variant="h6" display="flex" alignItems="center" gap={0.5}>
                    <Groups fontSize="small" />
                    {agents.filter(a => a.status === 'active' || a.status === 'working').length}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="caption" color="text.secondary">
                    Execution Time
                  </Typography>
                  <Typography variant="h6">
                    {Math.round(executionMetrics.executionTime)}s
                  </Typography>
                </Grid>
              </Grid>
            )}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );

  const renderPhaseDetails = () => (
    <Box>
      {executionPhases.map((phase, index) => (
        <Accordion key={index} expanded={index === currentPhaseIndex}>
          <AccordionSummary
            expandIcon={<ExpandMore />}
            sx={{
              backgroundColor: phase.status === 'completed' ? 'success.light' :
                             phase.status === 'active' ? 'primary.light' :
                             phase.status === 'failed' ? 'error.light' : 'grey.100',
              '&:hover': { backgroundColor: 'action.hover' }
            }}
          >
            <Box display="flex" alignItems="center" gap={2} width="100%">
              <Badge
                badgeContent={index + 1}
                color="primary"
                anchorOrigin={{ vertical: 'top', horizontal: 'left' }}
              >
                <Box width={24} />
              </Badge>
              
              <Box flexGrow={1}>
                <Typography variant="subtitle1" fontWeight="medium">
                  {phase.phase.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {phase.phase.description}
                </Typography>
              </Box>

              <Box display="flex" alignItems="center" gap={2} minWidth={200}>
                <Box flexGrow={1}>
                  <LinearProgress
                    variant="determinate"
                    value={phase.progress}
                    sx={{ height: 6, borderRadius: 3 }}
                    color={phase.status === 'completed' ? 'success' : 'primary'}
                  />
                  <Typography variant="caption">
                    {phase.progress}%
                  </Typography>
                </Box>
                
                <Chip
                  label={phase.status}
                  color={phase.status === 'completed' ? 'success' :
                         phase.status === 'active' ? 'primary' :
                         phase.status === 'failed' ? 'error' : 'default'}
                  size="small"
                  icon={phase.status === 'completed' ? <CheckCircle /> :
                        phase.status === 'failed' ? <Error /> : <Schedule />}
                />
              </Box>
            </Box>
          </AccordionSummary>

          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Agents ({phase.agents.length})
                </Typography>
                <List dense>
                  {phase.agents.map((agent) => (
                    <ListItem key={agent.id}>
                      <ListItemIcon>
                        <Person />
                      </ListItemIcon>
                      <ListItemText
                        primary={`${agent.role}+${agent.domain}`}
                        secondary={`Status: ${agent.status} | Priority: ${agent.priority}`}
                      />
                      <ListItemSecondaryAction>
                        <Chip
                          label={agent.status}
                          size="small"
                          color={agent.status === 'completed' ? 'success' :
                                 agent.status === 'failed' ? 'error' : 'default'}
                        />
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              </Grid>

              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Phase Metrics
                </Typography>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell>Tokens Used</TableCell>
                      <TableCell>{phase.metrics.tokensUsed.toLocaleString()}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>API Calls</TableCell>
                      <TableCell>{phase.metrics.apiCalls}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Cost</TableCell>
                      <TableCell>${phase.metrics.cost.toFixed(4)}</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Avg Response Time</TableCell>
                      <TableCell>{phase.metrics.averageResponseTime}ms</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Error Rate</TableCell>
                      <TableCell>{Math.round(phase.metrics.errorRate * 100)}%</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );

  const renderMetricsCharts = () => (
    <Grid container spacing={2}>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Phase Progress Overview
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={phaseProgressData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="phase" />
              <YAxis />
              <RechartsTooltip />
              <Bar dataKey="progress" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      </Grid>

      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Resource Utilization
          </Typography>
          {executionMetrics && (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={[
                    { name: 'CPU', value: executionMetrics.resourceUsage.cpu },
                    { name: 'Memory', value: executionMetrics.resourceUsage.memory },
                    { name: 'Network', value: executionMetrics.resourceUsage.network }
                  ]}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${Math.round(value)}%`}
                >
                  {COLORS.map((color, index) => (
                    <Cell key={`cell-${index}`} fill={color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Paper>
      </Grid>
    </Grid>
  );

  return (
    <Box>
      {/* Execution Overview */}
      {renderExecutionOverview()}

      {/* Status Alert */}
      {executionStatus === 'completed' && (
        <Alert severity="success" sx={{ mt: 2 }}>
          Plan execution completed successfully! All phases finished with {Math.round((executionMetrics?.successRate || 0) * 100)}% success rate.
        </Alert>
      )}

      {executionStatus === 'failed' && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Plan execution failed. Check the coordination panel for conflict details.
        </Alert>
      )}

      {/* Main Content Tabs */}
      <Paper sx={{ mt: 3 }}>
        <Tabs value={activeTab} onChange={(e, newValue) => setActiveTab(newValue)}>
          <Tab label="Phase Details" />
          <Tab label="Coordination Monitor" />
          <Tab label="Metrics & Charts" />
          <Tab label="Event Stream" />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          {renderPhaseDetails()}
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <AgentCoordinationPanel
            coordinationId={coordinationId}
            realTimeUpdates={true}
            showConflictResolution={true}
          />
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          {renderMetricsCharts()}
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          <List sx={{ maxHeight: 500, overflow: 'auto' }}>
            {coordinationEvents.slice(0, 50).map((event, index) => (
              <ListItem key={index} divider>
                <ListItemIcon>
                  {event.type === 'conflict' ? <Warning color="warning" /> :
                   event.type === 'task_complete' ? <CheckCircle color="success" /> :
                   event.type === 'agent_spawn' ? <Person color="primary" /> :
                   <Sync color="info" />}
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
                        {new Date(event.timestamp).toLocaleString()}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        </TabPanel>
      </Paper>
    </Box>
  );
}