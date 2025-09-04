// @ts-nocheck
"use client";

import React, { memo } from 'react';
import {
  Box,
  Typography,
  Paper,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Grid,
  LinearProgress
} from '@mui/material';
import { Psychology } from '@mui/icons-material';
import { PlanningRequest } from '@/lib/types/khive';

export interface TaskDefinitionStepProps {
  request: Partial<PlanningRequest>;
  onRequestChange: (updates: Partial<PlanningRequest>) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  errors?: Record<string, string>;
}

/**
 * Component Architecture: Task Definition Step
 * 
 * Responsibility: Handles the first step of the planning wizard - task definition
 * Principles:
 * - Single Responsibility: Only handles task definition UI
 * - Composition: Receives data and callbacks as props
 * - Memoization: Optimized for performance with React.memo
 * - Error Handling: Displays validation errors from parent
 */
export const TaskDefinitionStep = memo<TaskDefinitionStepProps>(({
  request,
  onRequestChange,
  onSubmit,
  isSubmitting,
  errors = {}
}) => {
  const handleFieldChange = (field: keyof PlanningRequest) => (
    event: React.ChangeEvent<HTMLInputElement | { value: unknown }>
  ) => {
    const value = event.target.value;
    onRequestChange({ [field]: value });
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  const complexityOptions = [
    { value: 'simple', label: 'Simple', description: 'Basic tasks, single domain' },
    { value: 'medium', label: 'Medium', description: 'Multi-step tasks, some coordination' },
    { value: 'complex', label: 'Complex', description: 'Multi-domain, complex workflows' },
    { value: 'very_complex', label: 'Very Complex', description: 'Enterprise-level orchestration' }
  ];

  const patternOptions = [
    { value: 'Expert', label: 'Expert (Single Agent)', description: 'One specialized agent' },
    { value: 'P∥', label: 'Parallel Independent', description: 'Multiple agents, no dependencies' },
    { value: 'P→', label: 'Sequential Pipeline', description: 'Sequential processing chain' },
    { value: 'P⊕', label: 'Tournament Quality', description: 'Multiple agents, best result wins' },
    { value: 'Pⓕ', label: 'LionAGI Flow', description: 'Complex workflow orchestration' },
    { value: 'P⊗', label: 'Multi-phase Hybrid', description: 'Combined orchestration patterns' }
  ];

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Define Planning Task
      </Typography>
      
      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          fullWidth
          multiline
          rows={4}
          label="Task Description"
          value={request.task_description || ''}
          onChange={handleFieldChange('task_description')}
          placeholder="Describe the task you want to orchestrate with multiple agents..."
          error={!!errors.task_description}
          helperText={errors.task_description}
          sx={{ mb: 3 }}
          required
        />

        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth error={!!errors.complexity}>
              <InputLabel>Complexity</InputLabel>
              <Select
                value={request.complexity || 'medium'}
                onChange={handleFieldChange('complexity')}
                label="Complexity"
              >
                {complexityOptions.map(option => (
                  <MenuItem key={option.value} value={option.value}>
                    <Box>
                      <Typography variant="body2">{option.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {option.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={4}>
            <FormControl fullWidth error={!!errors.pattern}>
              <InputLabel>Orchestration Pattern</InputLabel>
              <Select
                value={request.pattern || 'P∥'}
                onChange={handleFieldChange('pattern')}
                label="Orchestration Pattern"
              >
                {patternOptions.map(option => (
                  <MenuItem key={option.value} value={option.value}>
                    <Box>
                      <Typography variant="body2">{option.label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {option.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              type="number"
              label="Maximum Agents"
              value={request.max_agents || 5}
              onChange={handleFieldChange('max_agents')}
              inputProps={{ min: 1, max: 20 }}
              error={!!errors.max_agents}
              helperText={errors.max_agents || 'Recommended: 3-8 agents'}
            />
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            type="submit"
            variant="contained"
            disabled={isSubmitting || !request.task_description?.trim()}
            startIcon={isSubmitting ? <LinearProgress size="small" /> : <Psychology />}
            size="large"
          >
            {isSubmitting ? 'Planning...' : 'Start Consensus Planning'}
          </Button>
        </Box>
      </Box>
    </Paper>
  );
});

TaskDefinitionStep.displayName = 'TaskDefinitionStep';