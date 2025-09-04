import { useEffect, useCallback, useRef } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  action: () => void;
  description: string;
  category?: 'navigation' | 'workspace' | 'agents' | 'system';
  scope?: 'global' | 'workspace' | 'modal';
}

interface UseKeyboardShortcutsOptions {
  enabled?: boolean;
  scope?: 'global' | 'workspace' | 'modal';
}

export function useKeyboardShortcuts(
  shortcuts: KeyboardShortcut[], 
  options: UseKeyboardShortcutsOptions = {}
) {
  const { enabled = true, scope = 'global' } = options;
  const shortcutsRef = useRef(shortcuts);
  const sequenceRef = useRef<string[]>([]);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Update shortcuts ref when shortcuts change
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts]);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;
    
    // Skip if user is typing in an input
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      (event.target as any)?.contentEditable === 'true'
    ) {
      return;
    }

    const key = event.key.toLowerCase();
    const ctrl = event.ctrlKey;
    const meta = event.metaKey;
    const shift = event.shiftKey;
    const alt = event.altKey;

    // Handle sequence shortcuts (like vim navigation)
    if (!ctrl && !meta && !shift && !alt) {
      // Add to sequence
      sequenceRef.current.push(key);
      
      // Clear sequence after timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        sequenceRef.current = [];
      }, 1500);

      // Check for sequence matches
      const sequence = sequenceRef.current.join(' ');
      const sequenceShortcut = shortcutsRef.current.find(s => 
        s.key === sequence && 
        !s.ctrlKey && !s.metaKey && !s.shiftKey && !s.altKey
      );
      
      if (sequenceShortcut) {
        event.preventDefault();
        event.stopPropagation();
        sequenceShortcut.action();
        sequenceRef.current = [];
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        return;
      }
    } else {
      // Clear sequence for modifier shortcuts
      sequenceRef.current = [];
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    }

    // Handle regular shortcuts
    const shortcut = shortcutsRef.current.find(s => 
      s.key === key &&
      !!s.ctrlKey === ctrl &&
      !!s.metaKey === meta &&
      !!s.shiftKey === shift &&
      !!s.altKey === alt &&
      (s.scope || 'global') === scope
    );

    if (shortcut) {
      event.preventDefault();
      event.stopPropagation();
      shortcut.action();
    }
  }, [enabled, scope]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [handleKeyDown]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const getShortcutString = useCallback((shortcut: KeyboardShortcut) => {
    const parts: string[] = [];
    if (shortcut.metaKey) parts.push('⌘');
    if (shortcut.ctrlKey) parts.push('Ctrl');
    if (shortcut.altKey) parts.push('⌥');
    if (shortcut.shiftKey) parts.push('⇧');
    parts.push(shortcut.key.toUpperCase());
    return parts.join('+');
  }, []);

  return { getShortcutString };
}

// Predefined workspace shortcuts based on KHIVE config
export const createWorkspaceShortcuts = (actions: {
  onViewChange: (view: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings') => void;
  onToggleFullscreen: () => void;
  onOpenCommandPalette: () => void;
  onQuickPlanning: () => void;
  onNewOrchestration: () => void;
  onAgentCompose?: () => void;
  onToggleFocus?: () => void;
}): KeyboardShortcut[] => [
  // Global shortcuts
  {
    key: 'k',
    metaKey: true,
    action: actions.onOpenCommandPalette,
    description: 'Open command palette',
    category: 'system',
    scope: 'global'
  },
  {
    key: 'p',
    metaKey: true,
    action: actions.onQuickPlanning,
    description: 'Quick planning',
    category: 'workspace',
    scope: 'workspace'
  },
  {
    key: 'n',
    metaKey: true,
    action: actions.onNewOrchestration,
    description: 'New orchestration',
    category: 'workspace',
    scope: 'workspace'
  },
  {
    key: 'f',
    metaKey: true,
    action: actions.onToggleFullscreen,
    description: 'Toggle fullscreen',
    category: 'workspace',
    scope: 'workspace'
  },

  // Navigation shortcuts (vim-style)
  {
    key: 'g m',
    action: () => actions.onViewChange('monitoring'),
    description: 'Go to monitoring',
    category: 'navigation',
    scope: 'workspace'
  },
  {
    key: 'g p',
    action: () => actions.onViewChange('planning'),
    description: 'Go to planning',
    category: 'navigation',
    scope: 'workspace'
  },
  {
    key: 'g a',
    action: () => actions.onViewChange('agents'),
    description: 'Go to agents',
    category: 'navigation',
    scope: 'workspace'
  },
  {
    key: 'g n',
    action: () => actions.onViewChange('analytics'),
    description: 'Go to analytics',
    category: 'navigation',
    scope: 'workspace'
  },
  {
    key: 'g s',
    action: () => actions.onViewChange('settings'),
    description: 'Go to settings',
    category: 'navigation',
    scope: 'workspace'
  },

  // Tab shortcuts (like browser tabs)
  {
    key: '1',
    metaKey: true,
    action: () => actions.onViewChange('monitoring'),
    description: 'Switch to monitoring',
    category: 'navigation',
    scope: 'workspace'
  },
  {
    key: '2',
    metaKey: true,
    action: () => actions.onViewChange('planning'),
    description: 'Switch to planning',
    category: 'navigation',
    scope: 'workspace'
  },
  {
    key: '3',
    metaKey: true,
    action: () => actions.onViewChange('agents'),
    description: 'Switch to agents',
    category: 'navigation',
    scope: 'workspace'
  },
  {
    key: '4',
    metaKey: true,
    action: () => actions.onViewChange('analytics'),
    description: 'Switch to analytics',
    category: 'navigation',
    scope: 'workspace'
  },
  {
    key: '5',
    metaKey: true,
    action: () => actions.onViewChange('settings'),
    description: 'Switch to settings',
    category: 'navigation',
    scope: 'workspace'
  },

  // Contextual shortcuts
  ...(actions.onAgentCompose ? [{
    key: 'c',
    action: actions.onAgentCompose,
    description: 'Compose agent',
    category: 'agents' as const,
    scope: 'workspace' as const
  }] : []),

  ...(actions.onToggleFocus ? [{
    key: 'enter',
    action: actions.onToggleFocus,
    description: 'Toggle workspace focus',
    category: 'workspace' as const,
    scope: 'workspace' as const
  }] : [])
];