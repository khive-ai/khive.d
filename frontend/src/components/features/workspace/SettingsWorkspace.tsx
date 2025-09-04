"use client";

import { Box, Typography, Paper } from '@mui/material';

export function SettingsWorkspace() {
  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      <Typography variant="h5" gutterBottom>
        Settings
      </Typography>
      
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          Configuration Interface
        </Typography>
        <Typography variant="body2" color="text.secondary">
          System settings and preferences will be integrated in Phase 3
        </Typography>
      </Paper>
    </Box>
  );
}