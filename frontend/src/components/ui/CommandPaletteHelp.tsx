"use client";

import { useState, useMemo } from 'react';
import {
  Dialog,
  Box,
  Typography,
  Tabs,
  Tab,
  Card,
  CardContent,
  Grid,
  Chip,
  Divider,
  useTheme
} from '@mui/material';
import { KHIVE_CONFIG, ORCHESTRATION_PATTERNS } from '@/lib/config/khive';

interface CommandPaletteHelpProps {
  open: boolean;
  onClose: () => void;
}

interface ShortcutGroup {
  category: string;
  shortcuts: Array<{
    key: string;
    description: string;
    context?: string;
  }>;
}

export function CommandPaletteHelp({ open, onClose }: CommandPaletteHelpProps) {
  const theme = useTheme();
  const [activeTab, setActiveTab] = useState(0);

  // Ocean's keyboard shortcuts organized by category
  const shortcutGroups: ShortcutGroup[] = useMemo(() => [
    {
      category: 'Global Navigation',
      shortcuts: [
        { key: '⌘K', description: 'Open command palette', context: 'Primary interface' },
        { key: '⌘1', description: 'Focus orchestration tree', context: 'Left pane' },
        { key: '⌘2', description: 'Focus main workspace', context: 'Center pane' },
        { key: '⌘3', description: 'Focus activity stream', context: 'Right pane' },
        { key: 'ESC', description: 'Close dialogs / Cancel actions' },
      ]
    },
    {
      category: 'Vim-Style Navigation',
      shortcuts: [
        { key: 'G P', description: 'Go to Planning workspace' },
        { key: 'G M', description: 'Go to Monitoring dashboard' },
        { key: 'G A', description: 'Go to Agent management' },
        { key: 'G N', description: 'Go to Analytics & metrics' },
        { key: 'G S', description: 'Go to Settings & configuration' },
      ]
    },
    {
      category: 'Orchestration Actions',
      shortcuts: [
        { key: '⌘P', description: 'Quick planning mode', context: 'ConsensusPlannerV3' },
        { key: '⌘N', description: 'New orchestration session' },
        { key: 'C', description: 'Compose new agent', context: 'When focused' },
        { key: 'S', description: 'Switch between sessions' },
        { key: 'F', description: 'Search files and artifacts' },
      ]
    },
    {
      category: 'System Control',
      shortcuts: [
        { key: 'D', description: 'Check daemon status', context: 'KHIVE health' },
        { key: '⌘R', description: 'Reconnect WebSocket connection' },
        { key: '⌘⇧K', description: 'Show this help dialog' },
      ]
    }
  ], []);

  // KHIVE CLI commands reference
  const cliCommands = useMemo(() => [
    {
      command: 'khive plan',
      description: 'Create orchestration plan using ConsensusPlannerV3',
      example: 'khive plan "Build user authentication system"',
      category: 'Orchestration'
    },
    {
      command: 'khive compose',
      description: 'Compose agent with role and domain expertise',
      example: 'khive compose implementer -d software-architecture',
      category: 'Agents'
    },
    {
      command: 'khive coordinate',
      description: 'Monitor agent coordination and dependencies',
      example: 'khive coordinate status --coordination-id abc123',
      category: 'Coordination'
    },
    {
      command: 'khive session',
      description: 'Manage orchestration sessions',
      example: 'khive session list --active',
      category: 'Sessions'
    },
    {
      command: 'khive daemon',
      description: 'Control and monitor KHIVE daemon',
      example: 'khive daemon status --verbose',
      category: 'System'
    }
  ], []);

  // Available orchestration patterns
  const patterns = useMemo(() => 
    Object.entries(ORCHESTRATION_PATTERNS).map(([key, pattern]) => ({
      key,
      name: pattern.name,
      description: pattern.description,
      color: pattern.color,
      usage: `Best for ${pattern.description.toLowerCase()}`
    })), []
  );

  const getCategoryColor = (category: string) => {
    switch (category.toLowerCase()) {
      case 'orchestration': return '#3b82f6';
      case 'agents': return '#f59e0b';
      case 'coordination': return '#8b5cf6';
      case 'sessions': return '#06b6d4';
      case 'system': return '#ef4444';
      default: return theme.palette.text.secondary;
    }
  };

  const formatKey = (key: string) => {
    return key.split(' ').map((part, index) => (
      <Box
        key={index}
        component="kbd"
        sx={{
          px: 1,
          py: 0.25,
          mx: index > 0 ? 0.5 : 0,
          bgcolor: theme.palette.mode === 'dark' ? '#2d3748' : '#e2e8f0',
          borderRadius: 0.5,
          fontSize: '0.75rem',
          fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT,
          border: `1px solid ${theme.palette.divider}`
        }}
      >
        {part}
      </Box>
    ));
  };

  return (
    <Dialog
      data-testid="help-dialog"
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          height: '80vh',
          bgcolor: theme.palette.background.paper,
          fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT
        }
      }}
    >
      <Box sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h4" sx={{ 
            fontWeight: 'bold',
            fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT,
            color: theme.palette.primary.main
          }}>
            KHIVE Command Reference
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Ocean's CLI-first workflow shortcuts and commands for maximum productivity
          </Typography>
        </Box>

        {/* Tabs */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs 
            value={activeTab} 
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="scrollable"
          >
            <Tab label="Keyboard Shortcuts" />
            <Tab label="CLI Commands" />
            <Tab label="Orchestration Patterns" />
          </Tabs>
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          {/* Keyboard Shortcuts Tab */}
          {activeTab === 0 && (
            <Grid container spacing={3}>
              {shortcutGroups.map((group, index) => (
                <Grid item xs={12} md={6} key={index}>
                  <Card sx={{ height: '100%' }}>
                    <CardContent>
                      <Typography variant="h6" sx={{ 
                        mb: 2,
                        color: theme.palette.primary.main,
                        fontWeight: 'bold'
                      }}>
                        {group.category}
                      </Typography>
                      
                      {group.shortcuts.map((shortcut, shortcutIndex) => (
                        <Box key={shortcutIndex} sx={{ mb: 2 }}>
                          <Box sx={{ 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'space-between',
                            mb: 0.5
                          }}>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {shortcut.description}
                            </Typography>
                            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                              {formatKey(shortcut.key)}
                            </Box>
                          </Box>
                          
                          {shortcut.context && (
                            <Typography variant="caption" color="text.secondary">
                              {shortcut.context}
                            </Typography>
                          )}
                          
                          {shortcutIndex < group.shortcuts.length - 1 && (
                            <Divider sx={{ mt: 1 }} />
                          )}
                        </Box>
                      ))}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}

          {/* CLI Commands Tab */}
          {activeTab === 1 && (
            <Grid container spacing={2}>
              {cliCommands.map((cmd, index) => (
                <Grid item xs={12} key={index}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Typography variant="h6" sx={{ 
                          fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT,
                          color: theme.palette.primary.main
                        }}>
                          {cmd.command}
                        </Typography>
                        <Chip 
                          label={cmd.category}
                          size="small"
                          sx={{ 
                            ml: 2,
                            bgcolor: getCategoryColor(cmd.category),
                            color: 'white',
                            fontWeight: 'bold'
                          }}
                        />
                      </Box>
                      
                      <Typography variant="body2" sx={{ mb: 2 }}>
                        {cmd.description}
                      </Typography>
                      
                      <Box sx={{ 
                        p: 2,
                        bgcolor: theme.palette.mode === 'dark' ? '#0d1117' : '#f6f8fa',
                        borderRadius: 1,
                        border: `1px solid ${theme.palette.divider}`
                      }}>
                        <Typography variant="body2" sx={{ 
                          fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT,
                          color: theme.palette.text.secondary
                        }}>
                          $ {cmd.example}
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}

          {/* Orchestration Patterns Tab */}
          {activeTab === 2 && (
            <Grid container spacing={2}>
              {patterns.map((pattern, index) => (
                <Grid item xs={12} md={6} key={index}>
                  <Card>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Box sx={{ 
                          width: 16,
                          height: 16,
                          bgcolor: pattern.color,
                          borderRadius: '50%',
                          mr: 2
                        }} />
                        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                          {pattern.key}
                        </Typography>
                        <Typography variant="body2" sx={{ ml: 1, color: 'text.secondary' }}>
                          {pattern.name}
                        </Typography>
                      </Box>
                      
                      <Typography variant="body2" sx={{ mb: 2 }}>
                        {pattern.description}
                      </Typography>
                      
                      <Typography variant="caption" color="text.secondary" sx={{ 
                        fontStyle: 'italic'
                      }}>
                        {pattern.usage}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </Box>

        {/* Footer */}
        <Box sx={{ 
          mt: 2, 
          pt: 2, 
          borderTop: `1px solid ${theme.palette.divider}`,
          textAlign: 'center'
        }}>
          <Typography variant="caption" color="text.secondary">
            Press ESC to close • Access this help anytime with ⌘⇧K
          </Typography>
        </Box>
      </Box>
    </Dialog>
  );
}