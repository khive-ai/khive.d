"use client";

import { useState, useCallback } from 'react';
import { Box, useTheme } from '@mui/material';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { CommandPaletteHelp } from '@/components/ui/CommandPaletteHelp';
import { ContextAwareShortcuts } from '@/components/ui/ContextAwareShortcuts';
import { PerformanceMonitor } from '@/components/performance/PerformanceMonitor';
import { IntegrationValidator } from '@/components/testing/IntegrationValidator';
import { OrchestrationTree } from '@/components/features/OrchestrationTree';
import { Workspace } from '@/components/features/Workspace';
import { ActivityStream } from '@/components/features/ActivityStream';
import { useKeyboardShortcuts } from '@/lib/hooks/useKeyboardShortcuts';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';
import { KHIVE_CONFIG } from '@/lib/config/khive';

interface CommandCenterProps {
  children?: React.ReactNode;
}

export function CommandCenter({ children }: CommandCenterProps) {
  const theme = useTheme();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [helpDialogOpen, setHelpDialogOpen] = useState(false);
  const [validationDialogOpen, setValidationDialogOpen] = useState(false);
  const [activeView, setActiveView] = useState<'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings'>('monitoring');
  const [focusedPane, setFocusedPane] = useState<'tree' | 'workspace' | 'activity'>('workspace');

  // Real-time connection to KHIVE backend
  const { connected, sessions, events, sendCommand, reconnect, connectionHealth } = useKhiveWebSocket();

  // Enhanced keyboard shortcuts with comprehensive Ocean-friendly CLI patterns
  const shortcuts = [
    // Global Command Palette (Primary interface)
    {
      key: 'cmd+k',
      action: useCallback(() => setCommandPaletteOpen(true), []),
      description: 'Open command palette',
      category: 'system'
    },
    
    // Quick Navigation (Like browser tabs)
    {
      key: 'cmd+1',
      action: useCallback(() => setFocusedPane('tree'), []),
      description: 'Focus orchestration tree',
      category: 'navigation'
    },
    {
      key: 'cmd+2', 
      action: useCallback(() => setFocusedPane('workspace'), []),
      description: 'Focus workspace',
      category: 'navigation'
    },
    {
      key: 'cmd+3',
      action: useCallback(() => setFocusedPane('activity'), []),
      description: 'Focus activity stream',
      category: 'navigation'
    },

    // Vim-style Navigation (Ocean's terminal preference)
    {
      key: 'g p',
      action: useCallback(() => setActiveView('planning'), []),
      description: 'Go to planning',
      category: 'navigation'
    },
    {
      key: 'g m',
      action: useCallback(() => setActiveView('monitoring'), []),
      description: 'Go to monitoring',
      category: 'navigation'
    },
    {
      key: 'g a',
      action: useCallback(() => setActiveView('agents'), []),
      description: 'Go to agents',
      category: 'navigation'
    },
    {
      key: 'g n',
      action: useCallback(() => setActiveView('analytics'), []),
      description: 'Go to analytics',
      category: 'navigation'
    },
    {
      key: 'g s',
      action: useCallback(() => setActiveView('settings'), []),
      description: 'Go to settings',
      category: 'navigation'
    },

    // Direct Action Shortcuts (Power user efficiency)
    {
      key: 'cmd+p', 
      action: useCallback(() => {
        setActiveView('planning');
        setFocusedPane('workspace');
      }, []),
      description: 'Quick planning',
      category: 'orchestration'
    },
    {
      key: 'cmd+n',
      action: useCallback(() => sendCommand('new_orchestration'), [sendCommand]),
      description: 'New orchestration',
      category: 'orchestration'
    },
    {
      key: 'c',
      action: useCallback(() => sendCommand('khive compose'), [sendCommand]),
      description: 'Compose agent',
      category: 'agents'
    },
    {
      key: 'd',
      action: useCallback(() => sendCommand('khive daemon status'), [sendCommand]),
      description: 'Daemon status',
      category: 'system'
    },
    
    // System Control
    {
      key: 'escape',
      action: useCallback(() => {
        setCommandPaletteOpen(false);
        // Additional escape actions for Ocean's workflow
      }, []),
      description: 'Close command palette / Cancel',
      category: 'system'
    },
    {
      key: 'cmd+r',
      action: useCallback(async () => {
        try {
          await reconnect();
        } catch (error) {
          console.error('Manual reconnection failed:', error);
        }
      }, [reconnect]),
      description: 'Reconnect to KHIVE daemon',
      category: 'system'
    },
    {
      key: 'cmd+shift+k',
      action: useCallback(() => setHelpDialogOpen(true), []),
      description: 'Show keyboard shortcuts and command reference',
      category: 'system'
    },
    {
      key: 'cmd+shift+t',
      action: useCallback(() => setValidationDialogOpen(true), []),
      description: 'Run integration validation tests',
      category: 'system'
    }
  ];

  useKeyboardShortcuts(shortcuts);

  return (
    <Box 
      data-testid="command-center"
      sx={{ 
        height: '100vh',
        width: '100vw',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.default',
        fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT,
        overflow: 'hidden'
      }}>
      {/* Enhanced Status Bar - Terminal-style with Ocean's productivity info */}
      <Box 
        data-testid="status-bar"
        sx={{
          height: 32,
          bgcolor: theme.palette.mode === 'dark' ? '#1e1e1e' : '#f5f5f5',
          borderBottom: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          alignItems: 'center',
          px: 2,
          fontSize: '12px',
          color: 'text.secondary',
          fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT
        }}>
        <Box sx={{ display: 'flex', gap: 3, alignItems: 'center', width: '100%' }}>
          {/* Connection Status */}
          <Box 
            data-testid="connection-status"
            sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 1,
              color: connected ? '#10b981' : '#ef4444'
            }}>
            ● KHIVE {connected ? 'ONLINE' : 'OFFLINE'}
            {connectionHealth.latency > 0 && (
              <Box sx={{ color: 'text.secondary' }}>
                ({connectionHealth.latency}ms)
              </Box>
            )}
          </Box>

          {/* Session Information */}
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Box>Sessions: {sessions.length}</Box>
            <Box>Running: {sessions.filter(s => s.status === 'executing').length}</Box>
            <Box>Queued: {sessions.filter(s => s.status === 'pending').length}</Box>
          </Box>

          {/* Connection Health */}
          {connectionHealth.consecutiveFailures > 0 && (
            <Box sx={{ color: '#f59e0b' }}>
              ⚠ Retries: {connectionHealth.consecutiveFailures}
            </Box>
          )}

          <Box sx={{ ml: 'auto', display: 'flex', gap: 3, alignItems: 'center' }}>
            {/* Current Focus */}
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Box>Focus: {focusedPane.toUpperCase()}</Box>
              <Box>View: {activeView.toUpperCase()}</Box>
            </Box>

            {/* Quick Help */}
            <Box sx={{ 
              fontSize: '11px',
              color: 'text.disabled',
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}>
              <Box sx={{ 
                px: 1, 
                py: 0.25, 
                bgcolor: theme.palette.mode === 'dark' ? '#2d3748' : '#e2e8f0',
                borderRadius: 0.5
              }}>
                ⌘K
              </Box>
              for commands
            </Box>
          </Box>
        </Box>
      </Box>

      {/* Main 3-Pane Layout (ERP-style) */}
      <Box sx={{ 
        flex: 1,
        display: 'flex',
        overflow: 'hidden'
      }}>
        {/* Left Pane: Orchestration Tree */}
        <Box 
          data-testid="orchestration-tree"
          sx={{
            width: 280,
            borderRight: `1px solid ${theme.palette.divider}`,
            bgcolor: theme.palette.mode === 'dark' ? '#0d1117' : '#fafbfc',
            display: 'flex',
            flexDirection: 'column',
            outline: focusedPane === 'tree' ? `2px solid ${theme.palette.primary.main}` : 'none',
            transition: 'outline 0.1s ease'
          }}>
          <OrchestrationTree 
            sessions={sessions}
            onSessionSelect={(_sessionId) => setActiveView('monitoring')}
            focused={focusedPane === 'tree'}
          />
        </Box>

        {/* Center Pane: Workspace */}
        <Box 
          data-testid="workspace"
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            outline: focusedPane === 'workspace' ? `2px solid ${theme.palette.primary.main}` : 'none',
            transition: 'outline 0.1s ease'
          }}>
          <Workspace 
            activeView={activeView}
            onViewChange={setActiveView}
            focused={focusedPane === 'workspace'}
          />
          {children}
        </Box>

        {/* Right Pane: Activity Stream */}
        <Box 
          data-testid="activity-stream"
          sx={{
            width: 360,
            borderLeft: `1px solid ${theme.palette.divider}`,
            bgcolor: theme.palette.mode === 'dark' ? '#0d1117' : '#fafbfc',
            display: 'flex',
            flexDirection: 'column',
            outline: focusedPane === 'activity' ? `2px solid ${theme.palette.primary.main}` : 'none',
            transition: 'outline 0.1s ease'
          }}>
          <ActivityStream 
            events={events}
            focused={focusedPane === 'activity'}
          />
        </Box>
      </Box>

      {/* Enhanced Command Palette - Ocean's CLI-first interface */}
      <CommandPalette
        open={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onCommand={(command) => {
          // Handle system commands directly
          if (command === 'system_reconnect') {
            reconnect().catch(console.error);
          } else if (command === 'system_clear_events') {
            // Clear events locally (would need to implement in useKhiveWebSocket)
            console.log('Clearing activity stream...');
          } else {
            // Send to KHIVE backend
            sendCommand(command);
          }
        }}
        onNavigate={(view) => {
          setActiveView(view);
          setFocusedPane('workspace'); // Auto-focus workspace when navigating
        }}
        onFocusPane={(pane) => {
          setFocusedPane(pane);
        }}
        onShowHelp={() => setHelpDialogOpen(true)}
      />

      {/* Command Reference Help Dialog */}
      <CommandPaletteHelp
        open={helpDialogOpen}
        onClose={() => setHelpDialogOpen(false)}
      />

      {/* Ocean's CLI-First UX Enhancements */}
      <ContextAwareShortcuts
        activeView={activeView}
        focusedPane={focusedPane}
        isCommandPaletteOpen={commandPaletteOpen}
        isHelpOpen={helpDialogOpen}
      />

      {/* Performance Monitoring for CLI Response Times */}
      <PerformanceMonitor />

      {/* Integration Validation Testing */}
      <IntegrationValidator
        open={validationDialogOpen}
        onClose={() => setValidationDialogOpen(false)}
      />
    </Box>
  );
}