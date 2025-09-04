// @ts-nocheck
"use client";

import React, { memo, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Button,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  LinearProgress,
  Alert
} from '@mui/material';
import { CheckCircle, Error, Psychology, Timeline } from '@mui/icons-material';
import { ConsensusVisualization } from '../ConsensusVisualization';
import type { ConsensusRound } from '@/lib/hooks/usePlanningWorkflow';

export interface ConsensusStepProps {
  consensusRounds: ConsensusRound[];
  isActive: boolean;
  onProceed: () => void;
  coordinationId?: string;
}

/**
 * Component Architecture: Consensus Step
 * 
 * Responsibility: Displays consensus planning progress and allows proceeding to next step
 * Principles:
 * - Composition over Inheritance: Uses ConsensusVisualization component
 * - Memoization: Optimized rendering with useMemo and React.memo
 * - Single Responsibility: Only handles consensus step UI logic
 * - Data Flow: Receives data from parent, delegates visualization to child
 */
export const ConsensusStep = memo<ConsensusStepProps>(({
  consensusRounds,
  isActive,
  onProceed,
  coordinationId
}) => {
  // Memoized consensus metrics to avoid recalculation on every render
  const consensusMetrics = useMemo(() => {
    if (!consensusRounds.length) return null;

    const activeRound = consensusRounds[consensusRounds.length - 1];
    const totalAgents = activeRound.agents.length;
    const votedAgents = activeRound.agents.filter(a => a.vote !== null).length;
    const convergenceLevel = activeRound.convergence;
    const isComplete = activeRound.status === 'completed';
    const hasTimeout = activeRound.status === 'timeout';
    const canProceed = isComplete && convergenceLevel > 0.7;

    return {
      totalAgents,
      votedAgents,
      convergenceLevel,
      isComplete,
      hasTimeout,
      canProceed,
      participationRate: totalAgents > 0 ? votedAgents / totalAgents : 0
    };
  }, [consensusRounds]);

  const getConsensusStatus = () => {
    if (!consensusMetrics) return { severity: 'info', message: 'Initializing consensus...' };
    
    if (consensusMetrics.hasTimeout) {
      return { severity: 'error', message: 'Consensus timed out. Some agents may need manual intervention.' };
    }
    
    if (consensusMetrics.isComplete) {
      return consensusMetrics.canProceed 
        ? { severity: 'success', message: 'Consensus reached! Ready to proceed to execution.' }
        : { severity: 'warning', message: 'Consensus completed but convergence is low. Consider another round.' };
    }
    
    return { severity: 'info', message: 'Consensus in progress...' };
  };

  const statusInfo = getConsensusStatus();

  if (!isActive) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center', opacity: 0.6 }}>
        <Typography variant="h6" color="text.secondary">
          Consensus Planning
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Complete the previous step to begin consensus planning
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Status Alert */}
      <Alert severity={statusInfo.severity as any} sx={{ mb: 2 }}>
        {statusInfo.message}
      </Alert>

      {/* Consensus Progress Overview */}
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
          <Timeline /> Consensus Planning Progress
        </Typography>

        {consensusMetrics && (
          <Box sx={{ mb: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="body2">
                Agent Participation: {consensusMetrics.votedAgents}/{consensusMetrics.totalAgents}
              </Typography>
              <Typography variant="body2">
                Convergence: {Math.round(consensusMetrics.convergenceLevel * 100)}%
              </Typography>
            </Box>
            
            <LinearProgress 
              variant="determinate" 
              value={consensusMetrics.participationRate * 100} 
              sx={{ mb: 1, height: 6, borderRadius: 3 }}
            />
            
            <LinearProgress 
              variant="determinate" 
              value={consensusMetrics.convergenceLevel * 100}
              color={consensusMetrics.convergenceLevel > 0.7 ? 'success' : 'warning'}
              sx={{ height: 6, borderRadius: 3 }}
            />
          </Box>
        )}

        {/* Round Summary */}
        <Box display="flex" gap={1} mb={2}>
          {consensusRounds.map((round, index) => (
            <Chip
              key={round.round}
              label={`Round ${round.round}`}
              color={
                round.status === 'completed' ? 'success' :
                round.status === 'timeout' ? 'error' :
                round.status === 'active' ? 'primary' : 'default'
              }
              variant={index === consensusRounds.length - 1 ? 'filled' : 'outlined'}
              size="small"
            />
          ))}
        </Box>

        {/* Quick Agent Status */}
        {consensusRounds.length > 0 && (
          <Card variant="outlined">
            <CardContent sx={{ p: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Agent Status Overview
              </Typography>
              <List dense sx={{ py: 0 }}>
                {consensusRounds[consensusRounds.length - 1].agents.slice(0, 5).map((agent) => (
                  <ListItem key={agent.agentId} sx={{ py: 0.5 }}>
                    <ListItemIcon sx={{ minWidth: 32 }}>
                      {agent.status === 'voted' ? <CheckCircle color="success" fontSize="small" /> : 
                       agent.status === 'timeout' ? <Error color="error" fontSize="small" /> : 
                       <Psychology color="primary" fontSize="small" />}
                    </ListItemIcon>
                    <ListItemText
                      primary={`${agent.role}+${agent.domain}`}
                      secondary={`${agent.vote || 'Thinking...'} (${Math.round(agent.confidence * 100)}%)`}
                      primaryTypographyProps={{ variant: 'caption' }}
                      secondaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
                    />
                  </ListItem>
                ))}
              </List>
              
              {consensusRounds[consensusRounds.length - 1].agents.length > 5 && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  +{consensusRounds[consensusRounds.length - 1].agents.length - 5} more agents
                </Typography>
              )}
            </CardContent>
          </Card>
        )}
      </Paper>

      {/* Detailed Consensus Visualization */}
      <ConsensusVisualization
        rounds={consensusRounds}
        currentRound={consensusRounds.length - 1}
        showHistoricalData={true}
        compactView={false}
      />

      {/* Action Button */}
      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          onClick={onProceed}
          disabled={!consensusMetrics?.canProceed}
          size="large"
        >
          Review Planning Results
        </Button>
      </Box>
    </Box>
  );
});

ConsensusStep.displayName = 'ConsensusStep';