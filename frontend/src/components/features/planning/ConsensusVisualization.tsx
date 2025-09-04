// @ts-nocheck
"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  LinearProgress,
  CircularProgress,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Grid,
  Badge,
  Tooltip,
  IconButton,
  Collapse,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert
} from '@mui/material';
import {
  ExpandMore,
  Psychology,
  HowToVote,
  Timer,
  CheckCircle,
  Error,
  Warning,
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Groups,
  AccountTree,
  Speed,
  Timeline,
  VisibilityOff
} from '@mui/icons-material';
import { 
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  Legend
} from 'recharts';

// Enhanced consensus types for visualization
export interface ConsensusRound {
  round: number;
  agents: AgentConsensus[];
  convergence: number; // 0-1 scale
  timeoutMs: number;
  timeRemaining: number;
  status: 'active' | 'completed' | 'timeout';
  strategies: ConsensusStrategy[];
  votes: Record<string, number>;
  startTime: number;
  endTime?: number;
  byzantineFaultTolerance: boolean;
  quorumThreshold: number;
}

export interface AgentConsensus {
  agentId: string;
  role: string;
  domain: string;
  vote: string | null;
  confidence: number; // 0-1 scale
  reasoning: string;
  status: 'thinking' | 'voted' | 'timeout' | 'conflict';
  priority: number;
  reputation: number; // Historical voting accuracy
  lastVoteTime?: number;
  voteHistory: VoteHistoryEntry[];
}

export interface ConsensusStrategy {
  id: string;
  name: string;
  description: string;
  votes: number;
  proposedBy: string;
  complexity: number;
  feasibility: number;
  cost: number;
  timeEstimate: number;
}

export interface VoteHistoryEntry {
  round: number;
  vote: string;
  confidence: number;
  timestamp: number;
  outcome: 'correct' | 'incorrect' | 'partial';
}

interface ConsensusVisualizationProps {
  rounds: ConsensusRound[];
  currentRound?: number;
  onAgentClick?: (agentId: string) => void;
  onStrategyClick?: (strategyId: string) => void;
  showHistoricalData?: boolean;
  compactView?: boolean;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

export function ConsensusVisualization({
  rounds,
  currentRound = 0,
  onAgentClick,
  onStrategyClick,
  showHistoricalData = true,
  compactView = false
}: ConsensusVisualizationProps) {
  const [selectedRound, setSelectedRound] = useState(currentRound);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    overview: true,
    agents: true,
    strategies: false,
    timeline: false
  });

  const activeRound = rounds[selectedRound] || rounds[0];
  
  // Real-time consensus metrics calculation
  const consensusMetrics = useMemo(() => {
    if (!activeRound) return null;

    const totalAgents = activeRound.agents.length;
    const votedAgents = activeRound.agents.filter(a => a.vote !== null).length;
    const averageConfidence = activeRound.agents
      .filter(a => a.vote !== null)
      .reduce((sum, a) => sum + a.confidence, 0) / Math.max(votedAgents, 1);
    
    const strategyDistribution = activeRound.strategies.reduce((acc, strategy) => {
      acc[strategy.name] = strategy.votes;
      return acc;
    }, {} as Record<string, number>);

    const leadingStrategy = activeRound.strategies.reduce((prev, current) => 
      current.votes > prev.votes ? current : prev, activeRound.strategies[0]
    );

    const consensusLevel = leadingStrategy 
      ? leadingStrategy.votes / totalAgents 
      : 0;

    const byzantineToleranceActual = Math.floor((totalAgents - 1) / 3);
    const quorumMet = votedAgents >= activeRound.quorumThreshold;

    return {
      totalAgents,
      votedAgents,
      averageConfidence,
      strategyDistribution,
      leadingStrategy,
      consensusLevel,
      byzantineToleranceActual,
      quorumMet,
      participationRate: votedAgents / totalAgents,
      timeElapsed: Date.now() - activeRound.startTime,
      expectedCompletion: activeRound.startTime + activeRound.timeoutMs
    };
  }, [activeRound]);

  // Historical convergence data for timeline
  const convergenceHistory = useMemo(() => {
    return rounds.slice(0, selectedRound + 1).map((round, index) => ({
      round: index + 1,
      convergence: round.convergence * 100,
      participants: round.agents.filter(a => a.vote !== null).length,
      strategies: round.strategies.length,
      avgConfidence: round.agents
        .filter(a => a.vote !== null)
        .reduce((sum, a) => sum + a.confidence, 0) / 
        Math.max(round.agents.filter(a => a.vote !== null).length, 1) * 100
    }));
  }, [rounds, selectedRound]);

  const handleSectionToggle = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const getAgentStatusIcon = (agent: AgentConsensus) => {
    switch (agent.status) {
      case 'voted': return <CheckCircle color="success" />;
      case 'timeout': return <Error color="error" />;
      case 'conflict': return <Warning color="warning" />;
      default: return <Psychology color="primary" />;
    }
  };

  const getAgentStatusColor = (agent: AgentConsensus): 'success' | 'error' | 'warning' | 'primary' => {
    switch (agent.status) {
      case 'voted': return 'success';
      case 'timeout': return 'error';
      case 'conflict': return 'warning';
      default: return 'primary';
    }
  };

  const renderOverviewMetrics = () => (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
          <Speed /> Consensus Overview - Round {activeRound.round}
        </Typography>
        
        <Grid container spacing={2}>
          <Grid item xs={6} md={3}>
            <Box textAlign="center">
              <CircularProgress 
                variant="determinate" 
                value={consensusMetrics?.consensusLevel ? consensusMetrics.consensusLevel * 100 : 0}
                size={60}
                thickness={4}
              />
              <Typography variant="caption" display="block" mt={1}>
                Consensus Level
              </Typography>
              <Typography variant="h6">
                {consensusMetrics?.consensusLevel ? Math.round(consensusMetrics.consensusLevel * 100) : 0}%
              </Typography>
            </Box>
          </Grid>

          <Grid item xs={6} md={3}>
            <Box textAlign="center">
              <Typography variant="h4" color={consensusMetrics?.quorumMet ? 'success.main' : 'warning.main'}>
                {consensusMetrics?.votedAgents || 0}/{consensusMetrics?.totalAgents || 0}
              </Typography>
              <Typography variant="caption" display="block">
                Agent Participation
              </Typography>
              <Chip 
                label={consensusMetrics?.quorumMet ? 'Quorum Met' : 'Below Quorum'}
                color={consensusMetrics?.quorumMet ? 'success' : 'warning'}
                size="small"
              />
            </Box>
          </Grid>

          <Grid item xs={6} md={3}>
            <Box textAlign="center">
              <Typography variant="h4">
                {consensusMetrics?.averageConfidence ? Math.round(consensusMetrics.averageConfidence * 100) : 0}%
              </Typography>
              <Typography variant="caption" display="block">
                Avg Confidence
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={consensusMetrics?.averageConfidence ? consensusMetrics.averageConfidence * 100 : 0}
                color={consensusMetrics?.averageConfidence && consensusMetrics.averageConfidence > 0.7 ? 'success' : 'warning'}
              />
            </Box>
          </Grid>

          <Grid item xs={6} md={3}>
            <Box textAlign="center">
              <Typography variant="h4" color={activeRound.status === 'active' ? 'primary.main' : 'text.secondary'}>
                {Math.ceil((consensusMetrics?.expectedCompletion || 0) - Date.now()) / 1000}s
              </Typography>
              <Typography variant="caption" display="block">
                Time Remaining
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={((activeRound.timeoutMs - (consensusMetrics?.timeElapsed || 0)) / activeRound.timeoutMs) * 100}
                color="primary"
              />
            </Box>
          </Grid>
        </Grid>

        {activeRound.byzantineFaultTolerance && (
          <Alert severity="info" sx={{ mt: 2 }}>
            Byzantine Fault Tolerance: Can handle up to {consensusMetrics?.byzantineToleranceActual} malicious agents
          </Alert>
        )}
      </CardContent>
    </Card>
  );

  const renderAgentConsensus = () => (
    <Accordion 
      expanded={expandedSections.agents} 
      onChange={() => handleSectionToggle('agents')}
    >
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Typography variant="h6" display="flex" alignItems="center" gap={1}>
          <Groups /> Agent Consensus Status
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Agent</TableCell>
                <TableCell>Vote</TableCell>
                <TableCell>Confidence</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Reputation</TableCell>
                <TableCell>Reasoning</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {activeRound.agents
                .sort((a, b) => b.priority - a.priority) // Sort by priority
                .map((agent) => (
                <TableRow 
                  key={agent.agentId}
                  hover
                  onClick={() => onAgentClick?.(agent.agentId)}
                  sx={{ cursor: onAgentClick ? 'pointer' : 'default' }}
                >
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Avatar sx={{ width: 24, height: 24 }}>
                        {agent.role.charAt(0).toUpperCase()}
                      </Avatar>
                      <Box>
                        <Typography variant="body2" fontWeight="medium">
                          {agent.role}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {agent.domain}
                        </Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  
                  <TableCell>
                    {agent.vote ? (
                      <Chip 
                        label={agent.vote} 
                        color="primary" 
                        size="small" 
                        variant="outlined"
                      />
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        Thinking...
                      </Typography>
                    )}
                  </TableCell>
                  
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      <LinearProgress
                        variant="determinate"
                        value={agent.confidence * 100}
                        sx={{ width: 60, height: 4 }}
                        color={agent.confidence > 0.7 ? 'success' : agent.confidence > 0.4 ? 'warning' : 'error'}
                      />
                      <Typography variant="caption">
                        {Math.round(agent.confidence * 100)}%
                      </Typography>
                    </Box>
                  </TableCell>
                  
                  <TableCell>
                    <Chip
                      icon={getAgentStatusIcon(agent)}
                      label={agent.status}
                      color={getAgentStatusColor(agent)}
                      size="small"
                    />
                  </TableCell>
                  
                  <TableCell>
                    <Tooltip title={`Historical accuracy: ${Math.round(agent.reputation * 100)}%`}>
                      <Badge
                        badgeContent={agent.priority}
                        color="primary"
                        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
                      >
                        <Box display="flex" alignItems="center" gap={1}>
                          {agent.reputation > 0.8 ? <TrendingUp color="success" /> :
                           agent.reputation > 0.6 ? <TrendingFlat color="warning" /> :
                           <TrendingDown color="error" />}
                          <Typography variant="caption">
                            {Math.round(agent.reputation * 100)}%
                          </Typography>
                        </Box>
                      </Badge>
                    </Tooltip>
                  </TableCell>
                  
                  <TableCell>
                    <Typography variant="caption" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {agent.reasoning || 'No reasoning provided'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </AccordionDetails>
    </Accordion>
  );

  const renderStrategyBreakdown = () => (
    <Accordion 
      expanded={expandedSections.strategies} 
      onChange={() => handleSectionToggle('strategies')}
    >
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Typography variant="h6" display="flex" alignItems="center" gap={1}>
          <AccountTree /> Strategy Breakdown
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              Vote Distribution
            </Typography>
            {consensusMetrics?.strategyDistribution && Object.keys(consensusMetrics.strategyDistribution).length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={Object.entries(consensusMetrics.strategyDistribution).map(([name, value]) => ({ name, value }))}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {Object.entries(consensusMetrics.strategyDistribution).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Typography variant="body2" color="text.secondary">
                No votes cast yet
              </Typography>
            )}
          </Grid>

          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              Strategy Details
            </Typography>
            <List dense>
              {activeRound.strategies.map((strategy) => (
                <ListItem 
                  key={strategy.id}
                  button={!!onStrategyClick}
                  onClick={() => onStrategyClick?.(strategy.id)}
                >
                  <ListItemText
                    primary={
                      <Box display="flex" justifyContent="between" alignItems="center">
                        <Typography variant="body2" fontWeight="medium">
                          {strategy.name}
                        </Typography>
                        <Chip 
                          label={`${strategy.votes} votes`}
                          size="small"
                          color={strategy.votes > 0 ? 'primary' : 'default'}
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="caption" display="block">
                          {strategy.description}
                        </Typography>
                        <Box display="flex" gap={1} mt={0.5}>
                          <Chip label={`Complexity: ${strategy.complexity}/5`} size="tiny" variant="outlined" />
                          <Chip label={`Cost: $${strategy.cost}`} size="tiny" variant="outlined" />
                          <Chip label={`Time: ${strategy.timeEstimate}h`} size="tiny" variant="outlined" />
                        </Box>
                      </Box>
                    }
                  />
                </ListItem>
              ))}
            </List>
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );

  const renderConsensusTimeline = () => (
    <Accordion 
      expanded={expandedSections.timeline} 
      onChange={() => handleSectionToggle('timeline')}
    >
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Typography variant="h6" display="flex" alignItems="center" gap={1}>
          <Timeline /> Consensus Timeline
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={convergenceHistory}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="round" />
            <YAxis />
            <RechartsTooltip />
            <Legend />
            <Line type="monotone" dataKey="convergence" stroke="#8884d8" name="Convergence %" />
            <Line type="monotone" dataKey="participants" stroke="#82ca9d" name="Participants" />
            <Line type="monotone" dataKey="avgConfidence" stroke="#ffc658" name="Avg Confidence %" />
          </LineChart>
        </ResponsiveContainer>
      </AccordionDetails>
    </Accordion>
  );

  if (!activeRound) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          No consensus data available
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Round Selection */}
      {rounds.length > 1 && (
        <Box display="flex" gap={1} mb={2}>
          {rounds.map((round, index) => (
            <Chip
              key={round.round}
              label={`Round ${round.round}`}
              onClick={() => setSelectedRound(index)}
              color={index === selectedRound ? 'primary' : 'default'}
              variant={index === selectedRound ? 'filled' : 'outlined'}
              icon={round.status === 'completed' ? <CheckCircle /> : 
                    round.status === 'timeout' ? <Error /> : 
                    <Timer />}
            />
          ))}
        </Box>
      )}

      {/* Overview Metrics */}
      {consensusMetrics && renderOverviewMetrics()}

      {/* Agent Consensus */}
      {!compactView && renderAgentConsensus()}

      {/* Strategy Breakdown */}
      {!compactView && renderStrategyBreakdown()}

      {/* Timeline */}
      {!compactView && showHistoricalData && renderConsensusTimeline()}
    </Box>
  );
}