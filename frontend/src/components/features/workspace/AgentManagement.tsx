"use client";

import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Button, 
  Tabs, 
  Tab, 
  Grid, 
  Alert,
  Drawer,
  IconButton
} from '@mui/material';
import { 
  Add as AddIcon, 
  Psychology, 
  Analytics, 
  Timeline, 
  Close,
  Explore
} from '@mui/icons-material';
import { AgentComposer } from '../agents/AgentComposer';
import { RoleDomainBrowser } from '../agents/RoleDomainBrowser';
import { ActiveAgentMonitor } from '../agents/ActiveAgentMonitor';
import { AgentPerformanceAnalytics } from '../agents/AgentPerformanceAnalytics';
import { DataFlowOptimizer } from '../agents/DataFlowOptimizer';

export function AgentManagement() {
  const [activeTab, setActiveTab] = useState(0);
  const [composerOpen, setComposerOpen] = useState(false);
  const [browserOpen, setBrowserOpen] = useState(false);
  const [activeAgents, setActiveAgents] = useState<string[]>([]);
  const [coordinationId, setCoordinationId] = useState<string>('');

  // Mock coordination ID - in real implementation, this would come from session
  useEffect(() => {
    setCoordinationId(`coord_${Date.now()}`);
  }, []);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleAgentSpawned = (agentId: string, coordId: string) => {
    setActiveAgents(prev => [...prev, agentId]);
    setComposerOpen(false);
    setActiveTab(1); // Switch to Active Agents tab
  };

  const handleAgentAction = (agentId: string, action: 'pause' | 'resume' | 'terminate') => {
    if (action === 'terminate') {
      setActiveAgents(prev => prev.filter(id => id !== agentId));
    }
    // In real implementation, would call API to perform action
    console.log(`${action} agent ${agentId}`);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 0:
        return (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Psychology sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              Agent Composition Center
            </Typography>
            <Typography variant="body1" color="text.secondary" paragraph>
              Compose intelligent agents using Ocean's role+domain methodology
            </Typography>
            <Grid container spacing={2} justifyContent="center">
              <Grid item>
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<AddIcon />}
                  onClick={() => setComposerOpen(true)}
                >
                  Compose New Agent
                </Button>
              </Grid>
              <Grid item>
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<Explore />}
                  onClick={() => setBrowserOpen(true)}
                >
                  Browse Roles & Domains
                </Button>
              </Grid>
            </Grid>
            {coordinationId && (
              <Alert severity="info" sx={{ mt: 3, maxWidth: 500, mx: 'auto' }}>
                Coordination ID: {coordinationId}
              </Alert>
            )}
          </Box>
        );
      
      case 1:
        return (
          <ActiveAgentMonitor 
            agentIds={activeAgents}
            onAgentAction={handleAgentAction}
          />
        );
      
      case 2:
        return (
          <AgentPerformanceAnalytics 
            agentIds={activeAgents}
            coordinationId={coordinationId}
          />
        );
      
      case 3:
        return (
          <DataFlowOptimizer 
            agentIds={activeAgents}
            coordinationId={coordinationId}
          />
        );
      
      default:
        return null;
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2 }}>
        <Typography variant="h5">
          Agent Management
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<Explore />}
            onClick={() => setBrowserOpen(true)}
          >
            Browse
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setComposerOpen(true)}
          >
            Compose Agent
          </Button>
        </Box>
      </Box>
      
      <Paper sx={{ borderRadius: 0 }}>
        <Tabs value={activeTab} onChange={handleTabChange} centered>
          <Tab 
            label="Composition"
            icon={<Psychology />}
          />
          <Tab 
            label={`Active Agents (${activeAgents.length})`}
            icon={<Psychology />}
          />
          <Tab 
            label="Analytics"
            icon={<Analytics />}
          />
          <Tab 
            label="Data Flow"
            icon={<Timeline />}
          />
        </Tabs>
      </Paper>

      <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
        {renderTabContent()}
      </Box>

      {/* Agent Composer Drawer */}
      <Drawer
        anchor="right"
        open={composerOpen}
        onClose={() => setComposerOpen(false)}
        PaperProps={{
          sx: { width: { xs: '100%', md: '60%', lg: '50%' } }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Agent Composer
          </Typography>
          <IconButton onClick={() => setComposerOpen(false)}>
            <Close />
          </IconButton>
        </Box>
        <AgentComposer 
          onAgentSpawned={handleAgentSpawned}
          coordinationId={coordinationId}
        />
      </Drawer>

      {/* Role Domain Browser Drawer */}
      <Drawer
        anchor="right"
        open={browserOpen}
        onClose={() => setBrowserOpen(false)}
        PaperProps={{
          sx: { width: { xs: '100%', md: '70%', lg: '60%' } }
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Role & Domain Browser
          </Typography>
          <IconButton onClick={() => setBrowserOpen(false)}>
            <Close />
          </IconButton>
        </Box>
        <RoleDomainBrowser />
      </Drawer>
    </Box>
  );
}