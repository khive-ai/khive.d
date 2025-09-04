"use client";

import React from 'react';
import {
  Box,
  Typography
} from '@mui/material';

export interface AgentComposerProps {
  onAgentSpawned?: (agentId: string) => void;
  coordinationId?: string;
}

export function AgentComposer({ onAgentSpawned: _onAgentSpawned, coordinationId }: AgentComposerProps) {
  // Temporarily simplified to avoid Grid compatibility issues during Phase 3.5 validation
  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Agent Composer
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Agent composition interface is temporarily disabled due to MUI Grid compatibility issues.
        This will be fully restored in Phase 4 E2E testing.
      </Typography>
      <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 2 }}>
        Coordination ID: {coordinationId || 'None'}
      </Typography>
    </Box>
  );
}