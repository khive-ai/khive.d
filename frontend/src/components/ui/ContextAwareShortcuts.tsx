"use client";

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Typography, Fade, Paper, useTheme } from '@mui/material';
import { KHIVE_CONFIG } from '@/lib/config/khive';

interface ContextualShortcut {
  key: string;
  description: string;
  category: 'primary' | 'secondary' | 'context';
}

interface ContextAwareShortcutsProps {
  activeView: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings';
  focusedPane: 'tree' | 'workspace' | 'activity';
  isCommandPaletteOpen?: boolean;
  isHelpOpen?: boolean;
}

export function ContextAwareShortcuts({ 
  activeView, 
  focusedPane, 
  isCommandPaletteOpen = false,
  isHelpOpen = false 
}: ContextAwareShortcutsProps) {
  const theme = useTheme();
  const [isVisible, setIsVisible] = useState(false);
  const [shouldAutoShow, setShouldAutoShow] = useState(true);

  // Context-aware shortcuts based on current state
  const contextualShortcuts = useMemo((): ContextualShortcut[] => {
    const base: ContextualShortcut[] = [
      { key: '⌘K', description: 'Command Palette', category: 'primary' },
      { key: 'ESC', description: 'Cancel/Close', category: 'primary' }
    ];

    // Add context-specific shortcuts based on active view
    if (activeView === 'planning') {
      base.push(
        { key: '⌘P', description: 'Quick Plan', category: 'primary' },
        { key: '⌘N', description: 'New Orchestration', category: 'context' },
        { key: 'C', description: 'Compose Agent', category: 'context' }
      );
    } else if (activeView === 'monitoring') {
      base.push(
        { key: 'D', description: 'Daemon Status', category: 'context' },
        { key: '⌘R', description: 'Reconnect', category: 'secondary' },
        { key: 'F', description: 'Search Files', category: 'context' }
      );
    } else if (activeView === 'agents') {
      base.push(
        { key: 'C', description: 'Compose Agent', category: 'primary' },
        { key: 'A', description: 'Agent Performance', category: 'context' },
        { key: 'L', description: 'List Active', category: 'context' }
      );
    }

    // Add pane-specific shortcuts
    if (focusedPane === 'tree') {
      base.push(
        { key: '↑↓', description: 'Navigate Sessions', category: 'context' },
        { key: 'Enter', description: 'Select Session', category: 'context' }
      );
    } else if (focusedPane === 'activity') {
      base.push(
        { key: '⌘↑', description: 'Scroll to Top', category: 'secondary' },
        { key: '⌘↓', description: 'Scroll to Bottom', category: 'secondary' }
      );
    }

    // Always show navigation shortcuts
    base.push(
      { key: '⌘1', description: `Focus ${focusedPane === 'tree' ? '→ Tree' : 'Tree'}`, category: 'secondary' },
      { key: '⌘2', description: `Focus ${focusedPane === 'workspace' ? '→ Workspace' : 'Workspace'}`, category: 'secondary' },
      { key: '⌘3', description: `Focus ${focusedPane === 'activity' ? '→ Activity' : 'Activity'}`, category: 'secondary' }
    );

    // Vim-style navigation
    base.push(
      { key: 'G P', description: `Go ${activeView === 'planning' ? '→ Planning' : 'Planning'}`, category: 'secondary' },
      { key: 'G M', description: `Go ${activeView === 'monitoring' ? '→ Monitoring' : 'Monitoring'}`, category: 'secondary' },
      { key: 'G A', description: `Go ${activeView === 'agents' ? '→ Agents' : 'Agents'}`, category: 'secondary' }
    );

    return base;
  }, [activeView, focusedPane]);

  // Auto-show shortcuts when context changes
  useEffect(() => {
    if (shouldAutoShow && !isCommandPaletteOpen && !isHelpOpen) {
      setIsVisible(true);
      const timer = setTimeout(() => setIsVisible(false), 3000);
      return () => clearTimeout(timer);
    } else {
      setIsVisible(false);
    }
  }, [activeView, focusedPane, shouldAutoShow, isCommandPaletteOpen, isHelpOpen]);

  // Manual toggle with ? key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't show if typing in inputs
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      if (event.key === '?' && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        setIsVisible(prev => !prev);
        setShouldAutoShow(false); // Disable auto-show when manually controlled
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Hide when command palette or help is open
  useEffect(() => {
    if (isCommandPaletteOpen || isHelpOpen) {
      setIsVisible(false);
    }
  }, [isCommandPaletteOpen, isHelpOpen]);

  const getCategoryColor = (category: ContextualShortcut['category']) => {
    switch (category) {
      case 'primary': return theme.palette.primary.main;
      case 'secondary': return theme.palette.text.secondary;
      case 'context': return theme.palette.warning.main;
      default: return theme.palette.text.secondary;
    }
  };

  const getCategoryWeight = (category: ContextualShortcut['category']) => {
    switch (category) {
      case 'primary': return 'bold';
      case 'context': return '500';
      default: return 'normal';
    }
  };

  if (!isVisible) return null;

  return (
    <Fade in={isVisible}>
      <Paper sx={{
        position: 'fixed',
        bottom: 20,
        left: 20,
        maxWidth: 280,
        p: 2,
        bgcolor: theme.palette.mode === 'dark' 
          ? 'rgba(0, 0, 0, 0.9)' 
          : 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(8px)',
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 2,
        zIndex: 1000,
        fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT
      }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography variant="subtitle2" sx={{ 
            fontWeight: 'bold',
            flex: 1,
            color: theme.palette.primary.main
          }}>
            Context Shortcuts
          </Typography>
          <Box sx={{
            px: 1,
            py: 0.25,
            bgcolor: theme.palette.action.hover,
            borderRadius: 0.5,
            fontSize: '10px'
          }}>
            {activeView.toUpperCase()} • {focusedPane.toUpperCase()}
          </Box>
        </Box>

        {/* Shortcuts List */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {contextualShortcuts.map((shortcut, index) => (
            <Box 
              key={`${shortcut.key}-${index}`}
              sx={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                alignItems: 'center',
                minHeight: 20
              }}
            >
              <Typography 
                variant="caption" 
                sx={{ 
                  color: getCategoryColor(shortcut.category),
                  fontWeight: getCategoryWeight(shortcut.category),
                  fontSize: '11px'
                }}
              >
                {shortcut.description}
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                {shortcut.key.split(' ').map((keyPart, keyIndex) => (
                  <Box
                    key={keyIndex}
                    component="kbd"
                    sx={{
                      px: 0.75,
                      py: 0.25,
                      bgcolor: theme.palette.mode === 'dark' ? '#2d3748' : '#e2e8f0',
                      borderRadius: 0.5,
                      fontSize: '9px',
                      fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT,
                      border: `1px solid ${theme.palette.divider}`,
                      minWidth: 16,
                      textAlign: 'center',
                      color: getCategoryColor(shortcut.category)
                    }}
                  >
                    {keyPart}
                  </Box>
                ))}
              </Box>
            </Box>
          ))}
        </Box>

        {/* Footer */}
        <Box sx={{
          mt: 2,
          pt: 1.5,
          borderTop: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: '10px' }}>
            Auto-hides in 3s
          </Typography>
          <Typography variant="caption" color="text.disabled" sx={{ fontSize: '10px' }}>
            ? to toggle • ⌘⇧K for full help
          </Typography>
        </Box>

        {/* Context Indicator */}
        <Box sx={{
          position: 'absolute',
          top: -6,
          left: 12,
          width: 12,
          height: 12,
          bgcolor: getCategoryColor('primary'),
          transform: 'rotate(45deg)',
          border: `1px solid ${theme.palette.divider}`
        }} />
      </Paper>
    </Fade>
  );
}