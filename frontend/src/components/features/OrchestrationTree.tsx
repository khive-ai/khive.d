"use client";

import { Box, Typography, Paper } from '@mui/material';
import { OrchestrationSession } from '@/lib/types/khive';

interface OrchestrationTreeProps {
  focused?: boolean;
  sessions?: OrchestrationSession[];
  onSessionSelect?: (sessionId: string) => void;
}

export function OrchestrationTree({ focused: _focused, sessions: _sessions, onSessionSelect: _onSessionSelect }: OrchestrationTreeProps) {
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 1 }}>
      <Paper sx={{ p: 2, flex: 1, textAlign: 'center' }}>
        <Typography variant="h6" gutterBottom>
          Orchestration Tree
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Phase 3 will integrate KHIVE orchestration visualization
        </Typography>
      </Paper>
    </Box>
  );
}