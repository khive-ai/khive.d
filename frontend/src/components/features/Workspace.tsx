"use client";

import { useState } from 'react';
import { Box, Tabs, Tab } from '@mui/material';
import { PlanningWizard } from './workspace/PlanningWizard';
import { MonitoringDashboard } from './workspace/MonitoringDashboard';
import { AnalyticsDashboard } from './workspace/AnalyticsDashboard';
import { AgentManagement } from './workspace/AgentManagement';
import { SettingsWorkspace } from './workspace/SettingsWorkspace';

interface WorkspaceProps {
  activeView?: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings';
  onViewChange?: (view: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings') => void;
  focused?: boolean;
}

export function Workspace({ activeView = 'planning', onViewChange, focused: _focused }: WorkspaceProps) {
  const [currentView, setCurrentView] = useState(activeView);

  const handleViewChange = (_: React.SyntheticEvent, newValue: string) => {
    const view = newValue as 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings';
    setCurrentView(view);
    onViewChange?.(view);
  };

  const renderContent = () => {
    switch (currentView) {
      case 'planning': return <PlanningWizard />;
      case 'monitoring': return <MonitoringDashboard />;
      case 'analytics': return <AnalyticsDashboard />;
      case 'agents': return <AgentManagement />;
      case 'settings': return <SettingsWorkspace />;
      default: return <PlanningWizard />;
    }
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={currentView} onChange={handleViewChange} variant="scrollable">
          <Tab label="Planning" value="planning" />
          <Tab label="Monitoring" value="monitoring" />
          <Tab label="Analytics" value="analytics" />
          <Tab label="Agents" value="agents" />
          <Tab label="Settings" value="settings" />
        </Tabs>
      </Box>
      <Box sx={{ flex: 1, overflow: 'hidden' }}>
        {renderContent()}
      </Box>
    </Box>
  );
}