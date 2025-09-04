// @ts-nocheck
"use client";

import React, { memo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Button,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  Chip,
  Divider
} from '@mui/material';
import { PlayArrow, ExpandMore, Assessment, Schedule, AttachMoney } from '@mui/icons-material';
import { PlanningResponse } from '@/lib/types/khive';

export interface ResultsReviewStepProps {
  response: PlanningResponse;
  onExecute: () => void;
  isExecuting: boolean;
}

/**
 * Component Architecture: Results Review Step
 * 
 * Responsibility: Displays planning results for review before execution
 * Principles:
 * - Presentation Component: Pure UI component with no side effects
 * - Memoization: Optimized with React.memo to prevent unnecessary re-renders
 * - Accessibility: Proper ARIA labels and semantic HTML
 * - Information Architecture: Organized information hierarchy
 */
export const ResultsReviewStep = memo<ResultsReviewStepProps>(({
  response,
  onExecute,
  isExecuting
}) => {
  const getComplexityColor = (score: number) => {
    if (score < 0.3) return 'success';
    if (score < 0.6) return 'warning';
    return 'error';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return 'success';
    if (confidence > 0.6) return 'warning';
    return 'error';
  };

  return (
    <Box>
      {/* Planning Summary Card */}
      <Card sx={{ mb: 2 }} elevation={2}>
        <CardContent>
          <Typography variant="h6" gutterBottom display="flex" alignItems="center" gap={1}>
            <Assessment /> Planning Summary
          </Typography>
          
          <Typography variant="body2" paragraph color="text.secondary">
            {response.summary}
          </Typography>
          
          <Grid container spacing={3}>
            <Grid item xs={6} md={3}>
              <Box textAlign="center">
                <Typography variant="h4" color={getComplexityColor(response.complexity_score)}>
                  {response.complexity_score.toFixed(2)}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  Complexity Score
                </Typography>
                <Chip 
                  label={response.complexity_score < 0.3 ? 'Simple' : 
                        response.complexity_score < 0.6 ? 'Moderate' : 'Complex'}
                  color={getComplexityColor(response.complexity_score)}
                  size="small"
                  sx={{ mt: 0.5 }}
                />
              </Box>
            </Grid>

            <Grid item xs={6} md={3}>
              <Box textAlign="center">
                <Typography variant="h4" color="primary.main">
                  {response.pattern}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  Orchestration Pattern
                </Typography>
                <Typography variant="caption" color="primary.main">
                  {response.phases.length} phases
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={6} md={3}>
              <Box textAlign="center">
                <Typography variant="h4" color="info.main">
                  {response.recommended_agents}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  Recommended Agents
                </Typography>
                <Typography variant="caption" color="info.main">
                  {response.phases.reduce((sum, p) => sum + p.agents.length, 0)} total agents
                </Typography>
              </Box>
            </Grid>

            <Grid item xs={6} md={3}>
              <Box textAlign="center">
                <Typography variant="h4" color={getConfidenceColor(response.confidence)}>
                  {Math.round(response.confidence * 100)}%
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  Plan Confidence
                </Typography>
                <Chip 
                  label={response.confidence > 0.8 ? 'High' : 
                        response.confidence > 0.6 ? 'Medium' : 'Low'}
                  color={getConfidenceColor(response.confidence)}
                  size="small"
                  sx={{ mt: 0.5 }}
                />
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Execution Phases */}
      <Accordion defaultExpanded>
        <AccordionSummary 
          expandIcon={<ExpandMore />}
          aria-controls="phases-content"
          id="phases-header"
        >
          <Typography variant="h6" display="flex" alignItems="center" gap={1}>
            <Schedule /> Execution Phases ({response.phases.length})
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {response.phases.map((phase, idx) => (
              <Card key={idx} variant="outlined">
                <CardContent>
                  <Box display="flex" justifyContent="between" alignItems="start" mb={2}>
                    <Box>
                      <Typography variant="h6" color="primary.main">
                        Phase {idx + 1}: {phase.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" paragraph>
                        {phase.description}
                      </Typography>
                    </Box>
                    <Chip 
                      label={`${phase.agents.length} agents`} 
                      color="primary" 
                      size="small" 
                    />
                  </Box>
                  
                  <Box mb={2}>
                    <Typography variant="subtitle2" gutterBottom>
                      Agent Composition:
                    </Typography>
                    <Box display="flex" flexWrap="wrap" gap={1}>
                      {phase.agents.map((agent, agentIdx) => (
                        <Chip 
                          key={agentIdx}
                          label={`${agent.role}+${agent.domain}`}
                          variant="outlined"
                          size="small"
                          color="primary"
                        />
                      ))}
                    </Box>
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  <Box display="flex" justifyContent="between" alignItems="center">
                    <Typography variant="body2" color="text.secondary">
                      <strong>Quality Gate:</strong> {phase.quality_gate}
                    </Typography>
                    {phase.estimated_duration && (
                      <Typography variant="body2" color="text.secondary">
                        <strong>Est. Duration:</strong> {phase.estimated_duration}
                      </Typography>
                    )}
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        </AccordionDetails>
      </Accordion>

      {/* Cost Estimation */}
      {response.cost && (
        <Alert 
          severity="info" 
          sx={{ mt: 2, mb: 2 }}
          icon={<AttachMoney />}
        >
          <Typography variant="body2">
            <strong>Estimated Cost:</strong> ${response.cost.toFixed(4)}
            {response.tokens && (
              <span style={{ marginLeft: 16 }}>
                <strong>Tokens:</strong> {response.tokens.input} input + {response.tokens.output} output
              </span>
            )}
          </Typography>
        </Alert>
      )}

      {/* Execution Warnings */}
      {response.complexity_score > 0.7 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <Typography variant="body2">
            <strong>High Complexity:</strong> This plan involves complex orchestration patterns. 
            Monitor execution closely and be prepared for potential coordination challenges.
          </Typography>
        </Alert>
      )}

      {response.confidence < 0.6 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <Typography variant="body2">
            <strong>Low Confidence:</strong> The planning system has low confidence in this plan. 
            Consider refining the task description or adjusting parameters.
          </Typography>
        </Alert>
      )}

      {/* Execution Button */}
      <Paper sx={{ p: 2, mt: 2, backgroundColor: 'background.default' }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="subtitle1">
              Ready to Execute Plan
            </Typography>
            <Typography variant="body2" color="text.secondary">
              This will spawn {response.recommended_agents} agents and begin orchestration
            </Typography>
          </Box>
          
          <Button
            variant="contained"
            size="large"
            onClick={onExecute}
            disabled={isExecuting}
            startIcon={<PlayArrow />}
          >
            {isExecuting ? 'Executing...' : 'Execute Plan'}
          </Button>
        </Box>
      </Paper>
    </Box>
  );
});

ResultsReviewStep.displayName = 'ResultsReviewStep';