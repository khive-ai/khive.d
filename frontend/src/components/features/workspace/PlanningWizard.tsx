"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Paper,
  Stepper,
  Step,
  StepLabel,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  LinearProgress,
  Card,
  CardContent,
  IconButton,
  Tooltip,
  Badge,
  Collapse,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Divider
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Refresh,
  ExpandMore,
  Psychology,
  Groups,
  Timeline,
  Assessment,
  CheckCircle,
  Error,
  Warning,
  Info
} from '@mui/icons-material';

import { KhiveApiService, KhiveApiError } from '@/lib/services/khiveApiService';
import { khiveWebSocketService } from '@/lib/services/khiveWebSocketService';
import { 
  PlanningRequest, 
  PlanningResponse, 
  CoordinationEvent,
  OrchestrationSession,
  Agent 
} from '@/lib/types/khive';

// Enhanced types for ConsensusPlannerV3 integration
interface PlanningState {
  currentStep: number;
  request: Partial<PlanningRequest>;
  response: PlanningResponse | null;
  consensusRounds: ConsensusRound[];
  activeCoordination: string | null;
  status: 'idle' | 'planning' | 'consensus' | 'executing' | 'completed' | 'failed';
  error: string | null;
}

interface ConsensusRound {
  round: number;
  agents: AgentConsensus[];
  convergence: number; // 0-1 scale
  timeoutMs: number;
  status: 'active' | 'completed' | 'timeout';
  strategies: string[];
  votes: Record<string, number>; // strategy -> vote count
}

interface AgentConsensus {
  agentId: string;
  role: string;
  domain: string;
  vote: string | null;
  confidence: number; // 0-1 scale
  reasoning: string;
  status: 'thinking' | 'voted' | 'timeout';
}

interface CoordinationLock {
  filePath: string;
  agentId: string;
  lockType: 'read' | 'write' | 'exclusive';
  ttlMs: number;
  acquired: number;
}

const planningSteps = [
  'Define Task',
  'Consensus Planning',
  'Review Results',
  'Execute Plan'
];

export function PlanningWizard() {
  const [state, setState] = useState<PlanningState>({
    currentStep: 0,
    request: { complexity: 'medium', pattern: 'P∥', max_agents: 5 },
    response: null,
    consensusRounds: [],
    activeCoordination: null,
    status: 'idle',
    error: null
  });

  const [coordinationEvents, setCoordinationEvents] = useState<CoordinationEvent[]>([]);
  const [coordinationLocks, setCoordinationLocks] = useState<CoordinationLock[]>([]);
  const [activeSessions, setActiveSessions] = useState<OrchestrationSession[]>([]);
  const [planningAgents, setPlanningAgents] = useState<Agent[]>([]);

  // WebSocket setup for real-time updates
  useEffect(() => {
    const handleCoordinationEvent = (event: CoordinationEvent) => {
      setCoordinationEvents(prev => [event, ...prev.slice(0, 99)]); // Keep last 100 events
      
      // Update consensus rounds based on planning events
      if (event.type === 'agent_spawn' && state.activeCoordination === event.coordination_id) {
        updateConsensusRounds(event);
      }
    };

    const handleSessionUpdated = (session: OrchestrationSession) => {
      setActiveSessions(prev => 
        prev.map(s => s.sessionId === session.sessionId ? session : s)
      );
    };

    const handleAgentUpdated = (agent: Agent) => {
      if (agent.coordination_id === state.activeCoordination) {
        setPlanningAgents(prev => 
          prev.map(a => a.id === agent.id ? agent : a)
        );
        updateAgentConsensus(agent);
      }
    };

    khiveWebSocketService.on('coordination_event', handleCoordinationEvent);
    khiveWebSocketService.on('session_updated', handleSessionUpdated);
    khiveWebSocketService.on('agent_updated', handleAgentUpdated);

    // Join coordination if active
    if (state.activeCoordination) {
      khiveWebSocketService.joinCoordination(state.activeCoordination);
    }

    return () => {
      khiveWebSocketService.off('coordination_event', handleCoordinationEvent);
      khiveWebSocketService.off('session_updated', handleSessionUpdated);
      khiveWebSocketService.off('agent_updated', handleAgentUpdated);
      
      if (state.activeCoordination) {
        khiveWebSocketService.leaveCoordination(state.activeCoordination);
      }
    };
  }, [state.activeCoordination]);

  const updateConsensusRounds = useCallback((event: CoordinationEvent) => {
    // Implementation for updating consensus rounds based on coordination events
    // This would parse planning-specific events and update consensus state
  }, []);

  const updateAgentConsensus = useCallback((agent: Agent) => {
    // Update agent consensus data based on agent updates
    setState(prev => ({
      ...prev,
      consensusRounds: prev.consensusRounds.map(round => ({
        ...round,
        agents: round.agents.map(a => 
          a.agentId === agent.id 
            ? { ...a, status: agent.status === 'working' ? 'thinking' : 'voted' }
            : a
        )
      }))
    }));
  }, []);

  const handlePlanningSubmit = async () => {
    if (!state.request.task_description) {
      setState(prev => ({ ...prev, error: 'Task description is required' }));
      return;
    }

    setState(prev => ({ ...prev, status: 'planning', error: null }));

    try {
      const response = await KhiveApiService.submitPlan(state.request as PlanningRequest);
      
      setState(prev => ({
        ...prev,
        response,
        activeCoordination: response.coordination_id,
        status: 'consensus',
        currentStep: 1
      }));

      // Initialize consensus rounds
      initializeConsensusRounds(response);

      // Join coordination for real-time updates
      khiveWebSocketService.joinCoordination(response.coordination_id);

    } catch (error) {
      const errorMsg = error instanceof KhiveApiError 
        ? error.message 
        : 'Failed to submit planning request';
      
      setState(prev => ({ 
        ...prev, 
        status: 'failed', 
        error: errorMsg 
      }));
    }
  };

  const initializeConsensusRounds = (response: PlanningResponse) => {
    // Create initial consensus round with recommended agents
    const initialRound: ConsensusRound = {
      round: 1,
      agents: response.phases[0]?.agents.map(agent => ({
        agentId: agent.id,
        role: agent.role,
        domain: agent.domain,
        vote: null,
        confidence: 0,
        reasoning: '',
        status: 'thinking'
      })) || [],
      convergence: 0,
      timeoutMs: 30000, // 30 second timeout for consensus
      status: 'active',
      strategies: [], // Will be populated from agent proposals
      votes: {}
    };

    setState(prev => ({
      ...prev,
      consensusRounds: [initialRound]
    }));
  };

  const handleExecutePlan = async () => {
    if (!state.response || !state.activeCoordination) return;

    setState(prev => ({ ...prev, status: 'executing' }));

    try {
      // Execute the spawn commands from the planning response
      const spawnPromises = state.response.spawn_commands.map(async (command) => {
        // Parse spawn command and execute via API
        const [, role, domain] = command.match(/spawn (\w+) (\w+)/) || [];
        if (role && domain) {
          return KhiveApiService.spawnAgent(role, domain, state.activeCoordination!);
        }
      });

      await Promise.all(spawnPromises);

      setState(prev => ({ 
        ...prev, 
        status: 'completed',
        currentStep: 3 
      }));

    } catch (error) {
      const errorMsg = error instanceof KhiveApiError 
        ? error.message 
        : 'Failed to execute plan';
      
      setState(prev => ({ 
        ...prev, 
        status: 'failed', 
        error: errorMsg 
      }));
    }
  };

  const renderTaskDefinitionStep = () => (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Define Planning Task
      </Typography>
      
      <TextField
        fullWidth
        multiline
        rows={4}
        label="Task Description"
        value={state.request.task_description || ''}
        onChange={(e) => setState(prev => ({
          ...prev,
          request: { ...prev.request, task_description: e.target.value }
        }))}
        placeholder="Describe the task you want to orchestrate with multiple agents..."
        sx={{ mb: 3 }}
      />

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth>
            <InputLabel>Complexity</InputLabel>
            <Select
              value={state.request.complexity || 'medium'}
              onChange={(e) => setState(prev => ({
                ...prev,
                request: { ...prev.request, complexity: e.target.value as any }
              }))}
            >
              <MenuItem value="simple">Simple</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="complex">Complex</MenuItem>
              <MenuItem value="very_complex">Very Complex</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} md={4}>
          <FormControl fullWidth>
            <InputLabel>Pattern</InputLabel>
            <Select
              value={state.request.pattern || 'P∥'}
              onChange={(e) => setState(prev => ({
                ...prev,
                request: { ...prev.request, pattern: e.target.value as any }
              }))}
            >
              <MenuItem value="Expert">Expert (Single Agent)</MenuItem>
              <MenuItem value="P∥">Parallel Independent</MenuItem>
              <MenuItem value="P→">Sequential Pipeline</MenuItem>
              <MenuItem value="P⊕">Tournament Quality</MenuItem>
              <MenuItem value="Pⓕ">LionAGI Flow</MenuItem>
              <MenuItem value="P⊗">Multi-phase Hybrid</MenuItem>
            </Select>
          </FormControl>
        </Grid>

        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            type="number"
            label="Max Agents"
            value={state.request.max_agents || 5}
            onChange={(e) => setState(prev => ({
              ...prev,
              request: { ...prev.request, max_agents: parseInt(e.target.value) }
            }))}
            inputProps={{ min: 1, max: 20 }}
          />
        </Grid>
      </Grid>

      <Box sx={{ mt: 3, textAlign: 'right' }}>
        <Button
          variant="contained"
          onClick={handlePlanningSubmit}
          disabled={state.status === 'planning'}
          startIcon={state.status === 'planning' ? <LinearProgress /> : <Psychology />}
        >
          {state.status === 'planning' ? 'Planning...' : 'Start Consensus Planning'}
        </Button>
      </Box>
    </Paper>
  );

  const renderConsensusStep = () => (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Consensus Planning Progress
      </Typography>

      {state.consensusRounds.map((round) => (
        <Card key={round.round} sx={{ mb: 2 }}>
          <CardContent>
            <Box display="flex" alignItems="center" justifyContent="between" mb={2}>
              <Typography variant="subtitle1">
                Round {round.round} - Convergence: {Math.round(round.convergence * 100)}%
              </Typography>
              <Chip 
                label={round.status}
                color={round.status === 'completed' ? 'success' : 'primary'}
                size="small"
              />
            </Box>

            <LinearProgress 
              variant="determinate" 
              value={round.convergence * 100} 
              sx={{ mb: 2 }}
            />

            <Typography variant="subtitle2" gutterBottom>
              Agent Consensus:
            </Typography>
            
            <List dense>
              {round.agents.map((agent) => (
                <ListItem key={agent.agentId}>
                  <ListItemIcon>
                    {agent.status === 'voted' ? <CheckCircle color="success" /> : 
                     agent.status === 'timeout' ? <Error color="error" /> : 
                     <Psychology color="primary" />}
                  </ListItemIcon>
                  <ListItemText
                    primary={`${agent.role}+${agent.domain}`}
                    secondary={`Vote: ${agent.vote || 'Thinking...'} (${Math.round(agent.confidence * 100)}% confidence)`}
                  />
                </ListItem>
              ))}
            </List>

            {round.strategies.length > 0 && (
              <Box mt={2}>
                <Typography variant="subtitle2" gutterBottom>
                  Proposed Strategies:
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {round.strategies.map((strategy, idx) => (
                    <Chip 
                      key={idx}
                      label={strategy}
                      variant="outlined"
                      size="small"
                    />
                  ))}
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      ))}

      {state.response && (
        <Box sx={{ mt: 3, textAlign: 'right' }}>
          <Button
            variant="contained"
            onClick={() => setState(prev => ({ ...prev, currentStep: 2 }))}
            disabled={state.status !== 'consensus' || state.consensusRounds.some(r => r.status === 'active')}
          >
            Review Planning Results
          </Button>
        </Box>
      )}
    </Paper>
  );

  const renderResultsStep = () => (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Planning Results
      </Typography>

      {state.response && (
        <>
          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>
                Planning Summary
              </Typography>
              <Typography variant="body2" paragraph>
                {state.response.summary}
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Complexity Score
                  </Typography>
                  <Typography variant="h6">
                    {state.response.complexity_score.toFixed(2)}
                  </Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Pattern
                  </Typography>
                  <Typography variant="h6">
                    {state.response.pattern}
                  </Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Recommended Agents
                  </Typography>
                  <Typography variant="h6">
                    {state.response.recommended_agents}
                  </Typography>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Typography variant="caption" color="text.secondary">
                    Confidence
                  </Typography>
                  <Typography variant="h6">
                    {Math.round(state.response.confidence * 100)}%
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Accordion>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography variant="subtitle1">Execution Phases</Typography>
            </AccordionSummary>
            <AccordionDetails>
              {state.response.phases.map((phase, idx) => (
                <Card key={idx} sx={{ mb: 1 }}>
                  <CardContent>
                    <Typography variant="subtitle2">{phase.name}</Typography>
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {phase.description}
                    </Typography>
                    
                    <Typography variant="caption" display="block">
                      Agents: {phase.agents.map(a => `${a.role}+${a.domain}`).join(', ')}
                    </Typography>
                    <Typography variant="caption" display="block">
                      Quality Gate: {phase.quality_gate}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </AccordionDetails>
          </Accordion>

          {state.response.cost && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Estimated Cost: ${state.response.cost.toFixed(4)} 
              ({state.response.tokens?.input || 0} input + {state.response.tokens?.output || 0} output tokens)
            </Alert>
          )}

          <Box sx={{ mt: 3, textAlign: 'right' }}>
            <Button
              variant="contained"
              onClick={handleExecutePlan}
              disabled={state.status === 'executing'}
              startIcon={<PlayArrow />}
            >
              Execute Plan
            </Button>
          </Box>
        </>
      )}
    </Paper>
  );

  const renderExecutionStep = () => (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Plan Execution Monitor
      </Typography>

      {state.status === 'executing' && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Spawning agents and executing plan...
        </Alert>
      )}

      {state.status === 'completed' && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Plan execution completed successfully!
        </Alert>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Typography variant="subtitle2" gutterBottom>
            Active Agents ({planningAgents.length})
          </Typography>
          <List dense>
            {planningAgents.map((agent) => (
              <ListItem key={agent.id}>
                <ListItemIcon>
                  <Badge 
                    color={agent.status === 'active' ? 'success' : 'default'}
                    variant="dot"
                  >
                    <Groups />
                  </Badge>
                </ListItemIcon>
                <ListItemText
                  primary={`${agent.role}+${agent.domain}`}
                  secondary={`Status: ${agent.status} | Task: ${agent.currentTask || 'None'}`}
                />
              </ListItem>
            ))}
          </List>
        </Grid>

        <Grid item xs={12} md={6}>
          <Typography variant="subtitle2" gutterBottom>
            Coordination Events
          </Typography>
          <List dense sx={{ maxHeight: 300, overflow: 'auto' }}>
            {coordinationEvents.slice(0, 10).map((event, idx) => (
              <ListItem key={idx}>
                <ListItemIcon>
                  {event.type === 'conflict' ? <Warning color="warning" /> :
                   event.type === 'task_complete' ? <CheckCircle color="success" /> :
                   <Info color="info" />}
                </ListItemIcon>
                <ListItemText
                  primary={event.message}
                  secondary={new Date(event.timestamp).toLocaleTimeString()}
                />
              </ListItem>
            ))}
          </List>
        </Grid>
      </Grid>
    </Paper>
  );

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        ConsensusPlannerV3 - Multi-Agent Orchestration
      </Typography>

      {state.error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setState(prev => ({ ...prev, error: null }))}>
          {state.error}
        </Alert>
      )}

      <Paper sx={{ mb: 3 }}>
        <Stepper activeStep={state.currentStep} alternativeLabel sx={{ p: 2 }}>
          {planningSteps.map((label, index) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Paper>

      {state.currentStep === 0 && renderTaskDefinitionStep()}
      {state.currentStep === 1 && renderConsensusStep()}
      {state.currentStep === 2 && renderResultsStep()}
      {state.currentStep === 3 && renderExecutionStep()}

      {/* Coordination Status */}
      {state.activeCoordination && (
        <Paper sx={{ mt: 3, p: 2, backgroundColor: 'background.paper' }}>
          <Typography variant="subtitle2" gutterBottom>
            Active Coordination: {state.activeCoordination}
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip 
              label={state.status} 
              color={state.status === 'completed' ? 'success' : 'primary'} 
              size="small" 
            />
            {coordinationLocks.length > 0 && (
              <Chip 
                label={`${coordinationLocks.length} active locks`}
                variant="outlined"
                size="small"
              />
            )}
          </Box>
        </Paper>
      )}
    </Box>
  );
}