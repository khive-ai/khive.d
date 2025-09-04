"use client";

import { useState, useMemo, useEffect } from 'react';
import {
  Dialog,
  Box,
  InputBase,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
  Chip,
  useTheme
} from '@mui/material';
import { KHIVE_CONFIG, ORCHESTRATION_PATTERNS } from '@/lib/config/khive';

interface Command {
  id: string;
  label: string;
  description: string;
  category: 'navigation' | 'orchestration' | 'agents' | 'sessions' | 'system' | 'workspace';
  keywords?: string[];
  shortcut?: string;
  action?: string;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  onCommand: (command: string) => void;
  onNavigate?: (view: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings') => void;
  onFocusPane?: (pane: 'tree' | 'workspace' | 'activity') => void;
  onShowHelp?: () => void;
}

export function CommandPalette({ open, onClose, onCommand, onNavigate, onFocusPane, onShowHelp }: CommandPaletteProps) {
  const theme = useTheme();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Comprehensive command set based on KHIVE CLI operations and Ocean's workflow preferences
  const commands: Command[] = useMemo(() => [
    // Orchestration Commands (Core KHIVE functionality)
    { 
      id: 'khive_plan', 
      label: 'Plan Orchestration', 
      description: 'Create a new orchestration plan using ConsensusPlannerV3',
      category: 'orchestration',
      keywords: ['plan', 'orchestrate', 'consensus', 'task'],
      shortcut: '⌘P',
      action: 'khive plan'
    },
    { 
      id: 'khive_compose', 
      label: 'Compose Agent', 
      description: 'Compose a new agent with role and domain specialization',
      category: 'agents',
      keywords: ['agent', 'compose', 'create', 'role', 'domain'],
      shortcut: 'C',
      action: 'khive compose'
    },
    { 
      id: 'khive_coordinate', 
      label: 'Coordination Monitor', 
      description: 'Monitor agent coordination and task dependencies',
      category: 'orchestration',
      keywords: ['coordinate', 'monitor', 'sync', 'dependencies'],
      action: 'khive coordinate'
    },
    { 
      id: 'khive_session_list', 
      label: 'List Sessions', 
      description: 'Show all active orchestration sessions',
      category: 'sessions',
      keywords: ['sessions', 'list', 'active', 'running'],
      action: 'khive session list'
    },
    { 
      id: 'khive_session_init', 
      label: 'Initialize Session', 
      description: 'Start a new orchestration session',
      category: 'sessions',
      keywords: ['init', 'start', 'new', 'session'],
      action: 'khive session init'
    },
    { 
      id: 'khive_daemon_status', 
      label: 'Daemon Status', 
      description: 'Check KHIVE daemon health and performance metrics',
      category: 'system',
      keywords: ['daemon', 'status', 'health', 'performance'],
      shortcut: 'D',
      action: 'khive daemon status'
    },

    // Navigation Commands (CLI-first workflow)
    { 
      id: 'nav_planning', 
      label: 'Go to Planning', 
      description: 'Switch to planning workspace for task orchestration',
      category: 'navigation',
      keywords: ['planning', 'plan', 'orchestrate', 'gp'],
      shortcut: 'G P'
    },
    { 
      id: 'nav_monitoring', 
      label: 'Go to Monitoring', 
      description: 'Switch to monitoring dashboard for real-time oversight',
      category: 'navigation',
      keywords: ['monitoring', 'monitor', 'dashboard', 'gm'],
      shortcut: 'G M'
    },
    { 
      id: 'nav_analytics', 
      label: 'Go to Analytics', 
      description: 'Switch to analytics for performance insights and metrics',
      category: 'navigation',
      keywords: ['analytics', 'metrics', 'insights', 'ga', 'gn'],
      shortcut: 'G A'
    },
    { 
      id: 'nav_agents', 
      label: 'Go to Agents', 
      description: 'Switch to agent management and composition interface',
      category: 'navigation',
      keywords: ['agents', 'management', 'compose', 'ga'],
      shortcut: 'G A'
    },
    { 
      id: 'nav_settings', 
      label: 'Go to Settings', 
      description: 'Switch to system configuration and preferences',
      category: 'navigation',
      keywords: ['settings', 'config', 'preferences', 'gs'],
      shortcut: 'G S'
    },

    // Focus Pane Commands (Terminal-like productivity)
    { 
      id: 'focus_tree', 
      label: 'Focus Orchestration Tree', 
      description: 'Focus on the orchestration hierarchy and session tree',
      category: 'workspace',
      keywords: ['tree', 'focus', 'orchestration', 'sessions'],
      shortcut: '⌘1'
    },
    { 
      id: 'focus_workspace', 
      label: 'Focus Main Workspace', 
      description: 'Focus on the central workspace content area',
      category: 'workspace',
      keywords: ['workspace', 'focus', 'main', 'center'],
      shortcut: '⌘2'
    },
    { 
      id: 'focus_activity', 
      label: 'Focus Activity Stream', 
      description: 'Focus on real-time activity and coordination events',
      category: 'workspace',
      keywords: ['activity', 'focus', 'stream', 'events'],
      shortcut: '⌘3'
    },

    // System Commands (Power user functionality)
    { 
      id: 'system_reconnect', 
      label: 'Reconnect WebSocket', 
      description: 'Reconnect to KHIVE daemon WebSocket connection',
      category: 'system',
      keywords: ['reconnect', 'websocket', 'connection', 'daemon'],
      action: 'system_reconnect'
    },
    { 
      id: 'system_clear_events', 
      label: 'Clear Activity Stream', 
      description: 'Clear all events from the activity stream',
      category: 'system',
      keywords: ['clear', 'events', 'activity', 'stream'],
      action: 'system_clear_events'
    },
    { 
      id: 'system_export_session', 
      label: 'Export Session Data', 
      description: 'Export current session data and coordination logs',
      category: 'system',
      keywords: ['export', 'session', 'data', 'logs'],
      action: 'system_export_session'
    },

    // Agent Management Commands
    { 
      id: 'agents_list_active', 
      label: 'List Active Agents', 
      description: 'Show all currently active agents and their status',
      category: 'agents',
      keywords: ['agents', 'active', 'list', 'running'],
      action: 'agents_list_active'
    },
    { 
      id: 'agents_performance', 
      label: 'Agent Performance', 
      description: 'View agent performance metrics and analytics',
      category: 'agents',
      keywords: ['agents', 'performance', 'metrics', 'analytics'],
      action: 'agents_performance'
    },

    // Orchestration Pattern Commands
    ...Object.entries(ORCHESTRATION_PATTERNS).map(([key, pattern]) => ({
      id: `pattern_${key.toLowerCase()}`,
      label: `Pattern: ${pattern.name}`,
      description: pattern.description,
      category: 'orchestration' as const,
      keywords: [pattern.name.toLowerCase(), key.toLowerCase(), 'pattern'],
      action: `orchestration_pattern_${key}`
    })),

    // Quick Actions (Ocean's productivity preferences)
    { 
      id: 'quick_new_orchestration', 
      label: 'New Orchestration', 
      description: 'Quickly start a new orchestration workflow',
      category: 'orchestration',
      keywords: ['new', 'quick', 'start', 'orchestration'],
      shortcut: '⌘N',
      action: 'new_orchestration'
    },
    { 
      id: 'quick_file_search', 
      label: 'Search Files', 
      description: 'Search through session files and artifacts',
      category: 'workspace',
      keywords: ['search', 'files', 'artifacts', 'find'],
      shortcut: 'F',
      action: 'file_search'
    },

    // Help and Documentation
    { 
      id: 'show_help', 
      label: 'Show Help', 
      description: 'Open keyboard shortcuts and command reference',
      category: 'system',
      keywords: ['help', 'shortcuts', 'commands', 'reference', 'guide'],
      shortcut: '⌘⇧K',
      action: 'show_help'
    }
  ], []);

  // Filter commands based on query
  const filteredCommands = useMemo(() => {
    if (!query.trim()) return commands;
    
    const lowerQuery = query.toLowerCase();
    return commands.filter(cmd => 
      cmd.label.toLowerCase().includes(lowerQuery) ||
      cmd.description.toLowerCase().includes(lowerQuery) ||
      cmd.keywords?.some(keyword => keyword.includes(lowerQuery)) ||
      cmd.shortcut?.toLowerCase().includes(lowerQuery) ||
      cmd.action?.includes(lowerQuery)
    ).sort((a, b) => {
      // Prioritize exact matches and shorter labels
      const aExact = a.label.toLowerCase().startsWith(lowerQuery) ? 1 : 0;
      const bExact = b.label.toLowerCase().startsWith(lowerQuery) ? 1 : 0;
      if (aExact !== bExact) return bExact - aExact;
      return a.label.length - b.label.length;
    });
  }, [query, commands]);

  // Reset selected index when query changes
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev => Math.min(prev + 1, filteredCommands.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (filteredCommands[selectedIndex]) {
            handleCommand(filteredCommands[selectedIndex]);
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, filteredCommands, selectedIndex]);

  const getCategoryColor = (category: Command['category']) => {
    switch (category) {
      case 'navigation': return '#10b981';
      case 'orchestration': return '#3b82f6';
      case 'agents': return '#f59e0b';
      case 'sessions': return '#8b5cf6';
      case 'system': return '#ef4444';
      case 'workspace': return '#06b6d4';
      default: return theme.palette.text.secondary;
    }
  };

  const handleCommand = (command: Command) => {
    // Handle navigation commands
    if (command.id.startsWith('nav_') && onNavigate) {
      const view = command.id.replace('nav_', '') as 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings';
      onNavigate(view);
    }
    // Handle focus pane commands
    else if (command.id.startsWith('focus_') && onFocusPane) {
      const pane = command.id.replace('focus_', '') as 'tree' | 'workspace' | 'activity';
      onFocusPane(pane);
    }
    // Handle help command
    else if (command.id === 'show_help' && onShowHelp) {
      onShowHelp();
    }
    // Handle system commands or send to backend
    else {
      onCommand(command.action || command.id);
    }
    
    setQuery('');
    onClose();
  };

  return (
    <Dialog
      data-testid="command-palette"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          bgcolor: theme.palette.background.paper,
          width: '700px',
          maxWidth: '90vw',
          borderRadius: 2,
          fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT
        }
      }}
    >
      <Box sx={{ p: 2 }}>
        {/* Terminal-style input */}
        <InputBase
          data-testid="command-input"
          placeholder="Type a command... (use ↑↓ to navigate, Enter to execute)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          sx={{ 
            width: '100%',
            fontSize: '16px',
            p: 2,
            border: `2px solid ${theme.palette.divider}`,
            borderRadius: 1,
            fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT,
            bgcolor: theme.palette.mode === 'dark' ? '#0d1117' : '#f6f8fa',
            '&::before': {
              content: '">"',
              color: theme.palette.primary.main,
              marginRight: 1,
              fontWeight: 'bold'
            }
          }}
          autoFocus
        />
        
        {/* Command list */}
        <List sx={{ 
          mt: 1, 
          maxHeight: 400, 
          overflow: 'auto',
          '& .MuiListItem-root': {
            borderRadius: 1,
            mb: 0.5
          }
        }}>
          {filteredCommands.map((command, index) => (
            <ListItem 
              key={command.id} 
              disablePadding
              sx={{
                bgcolor: index === selectedIndex ? `${theme.palette.primary.main}20` : 'transparent',
                border: index === selectedIndex ? `1px solid ${theme.palette.primary.main}` : '1px solid transparent',
                transition: 'all 0.1s ease'
              }}
            >
              <ListItemButton
                onClick={() => handleCommand(command)}
                sx={{ 
                  borderRadius: 1,
                  p: 2,
                  '&:hover': {
                    bgcolor: index === selectedIndex ? `${theme.palette.primary.main}30` : `${theme.palette.action.hover}`
                  }
                }}
              >
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Typography variant="subtitle1" sx={{ 
                      fontWeight: 500,
                      fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT
                    }}>
                      {command.label}
                    </Typography>
                    
                    {/* Category chip */}
                    <Chip 
                      label={command.category}
                      size="small"
                      sx={{ 
                        height: 20,
                        fontSize: '0.75rem',
                        bgcolor: getCategoryColor(command.category),
                        color: 'white',
                        fontWeight: 'bold'
                      }}
                    />
                    
                    {/* Keyboard shortcut */}
                    {command.shortcut && (
                      <Box sx={{
                        ml: 'auto',
                        px: 1,
                        py: 0.25,
                        bgcolor: theme.palette.mode === 'dark' ? '#2d3748' : '#e2e8f0',
                        borderRadius: 0.5,
                        fontSize: '0.75rem',
                        fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT,
                        color: 'text.secondary'
                      }}>
                        {command.shortcut}
                      </Box>
                    )}
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ 
                    mt: 0.5,
                    fontSize: '0.875rem'
                  }}>
                    {command.description}
                  </Typography>
                </Box>
              </ListItemButton>
            </ListItem>
          ))}
          
          {filteredCommands.length === 0 && (
            <ListItem>
              <ListItemText
                primary={
                  <Typography color="text.secondary" sx={{ 
                    textAlign: 'center',
                    py: 4,
                    fontStyle: 'italic'
                  }}>
                    No commands found. Try searching for "plan", "agent", or "monitor"
                  </Typography>
                }
              />
            </ListItem>
          )}
        </List>
        
        {/* Footer with command count and shortcuts reminder */}
        <Box sx={{ 
          mt: 2, 
          pt: 2, 
          borderTop: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <Typography variant="caption" color="text.secondary">
            {filteredCommands.length} command{filteredCommands.length !== 1 ? 's' : ''} available
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ 
            fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT
          }}>
            ESC to close • ↑↓ navigate • Enter execute
          </Typography>
        </Box>
      </Box>
    </Dialog>
  );
}