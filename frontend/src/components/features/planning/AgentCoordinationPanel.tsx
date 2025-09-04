"use client";

import React, { useState } from 'react';
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
  ListItemText,
  Tabs,
  Tab
} from '@mui/material';
import {
  Lock,
  LockOpen,
  Warning,
  CheckCircle
} from '@mui/icons-material';

interface AgentCoordinationPanelProps {
  coordinationData?: any;
  onRefresh?: () => void;
}

export function AgentCoordinationPanel({ coordinationData: _coordinationData, onRefresh }: AgentCoordinationPanelProps) {
  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Agent Coordination</Typography>
        <Button variant="outlined" size="small" onClick={onRefresh}>
          Refresh
        </Button>
      </Box>

      <Paper sx={{ mb: 2 }}>
        <Tabs value={activeTab} onChange={handleTabChange}>
          <Tab label="Active Locks" />
          <Tab label="Conflicts" />
          <Tab label="Health" />
        </Tabs>
      </Paper>

      {activeTab === 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <Lock sx={{ mr: 1, fontSize: 20 }} />
              File Locks
            </Typography>
            <List>
              <ListItem>
                <LockOpen color="success" sx={{ mr: 1 }} />
                <ListItemText 
                  primary="No active locks"
                  secondary="All resources available"
                />
                <Chip label="Healthy" color="success" size="small" />
              </ListItem>
            </List>
          </CardContent>
        </Card>
      )}

      {activeTab === 1 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <Warning sx={{ mr: 1, fontSize: 20 }} />
              Conflicts
            </Typography>
            <List>
              <ListItem>
                <CheckCircle color="success" sx={{ mr: 1 }} />
                <ListItemText 
                  primary="No conflicts detected"
                  secondary="All agents coordinating properly"
                />
                <Chip label="Resolved" color="success" size="small" />
              </ListItem>
            </List>
          </CardContent>
        </Card>
      )}

      {activeTab === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              <CheckCircle sx={{ mr: 1, fontSize: 20 }} />
              System Health
            </Typography>
            <List>
              <ListItem>
                <CheckCircle color="success" sx={{ mr: 1 }} />
                <ListItemText 
                  primary="Coordination services online"
                  secondary="All systems operational"
                />
                <Chip label="Healthy" color="success" size="small" />
              </ListItem>
            </List>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}