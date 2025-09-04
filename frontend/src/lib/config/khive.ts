// KHIVE backend integration configuration

export const KHIVE_CONFIG = {
  // WebSocket connection for real-time orchestration updates
  WEBSOCKET_URL: process.env.NEXT_PUBLIC_KHIVE_WS_URL || 'ws://localhost:8767',
  
  // API endpoints for KHIVE backend integration
  API_BASE: process.env.NEXT_PUBLIC_KHIVE_API_URL || 'http://localhost:8000',
  
  // Command Center UI Configuration
  UI: {
    // Performance targets Ocean expects
    COMMAND_RESPONSE_TIME_MS: 100,
    CONTEXT_SWITCH_TIME_MS: 50,
    WEBSOCKET_RECONNECT_INTERVAL_MS: 1000,
    
    // Information density preferences
    MAX_ACTIVITY_STREAM_ITEMS: 1000,
    ORCHESTRATION_TREE_MAX_DEPTH: 10,
    
    // Keyboard shortcuts (thinking like Ocean - CLI-first)
    SHORTCUTS: {
      GLOBAL_COMMAND_PALETTE: 'cmd+k',
      QUICK_PLANNING: 'cmd+p',
      NEW_ORCHESTRATION: 'cmd+n',
      TOGGLE_ACTIVITY_STREAM: 'cmd+a',
      FOCUS_ORCHESTRATION_TREE: 'cmd+1',
      FOCUS_WORKSPACE: 'cmd+2',
      FOCUS_ACTIVITY_STREAM: 'cmd+3',
      
      // Contextual shortcuts
      AGENT_COMPOSE: 'c',
      SESSION_SWITCH: 's',
      FILE_SEARCH: 'f',
      DAEMON_STATUS: 'd',
      
      // Navigation (like vim/terminal)
      GO_AGENTS: 'g a',
      GO_PLANNING: 'g p',
      GO_MONITORING: 'g m',
      GO_ANALYTICS: 'g n',
    }
  },
  
  // Real-time update intervals
  POLLING: {
    DAEMON_STATUS_INTERVAL_MS: 5000,
    SESSION_UPDATE_INTERVAL_MS: 1000,
    COST_TRACKING_INTERVAL_MS: 10000,
  },
  
  // CLI command mappings to UI actions
  CLI_MAPPINGS: {
    'khive plan': { action: 'openPlanningWizard', component: 'PlanningWizard' },
    'khive compose': { action: 'openAgentComposer', component: 'AgentComposer' },
    'khive coordinate': { action: 'showCoordinationMonitor', component: 'CoordinationMonitor' },
    'khive session': { action: 'openSessionManager', component: 'SessionManager' },
    'khive daemon': { action: 'showDaemonStatus', component: 'DaemonStatus' },
  },
  
  // Theme configuration (terminal-inspired)
  THEME: {
    TERMINAL_FONT: 'SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace',
    DENSITY: 'high', // Ocean prefers information density
    DEFAULT_MODE: 'dark', // CLI-first users typically prefer dark
  }
} as const;

export const ORCHESTRATION_PATTERNS = {
  'P∥': { name: 'Parallel Discovery', color: '#10b981', description: 'Independent analysis' },
  'P→': { name: 'Sequential Pipeline', color: '#3b82f6', description: 'Dependent handoffs' },
  'P⊕': { name: 'Tournament Validation', color: '#f59e0b', description: 'Quality competition' },
  'Pⓕ': { name: 'LionAGI Flow', color: '#8b5cf6', description: 'Complex dependencies' },
  'P⊗': { name: 'Hybrid Orchestra', color: '#ef4444', description: 'Multi-phase coordination' },
  'Expert': { name: 'Expert Assignment', color: '#06b6d4', description: 'Single specialist' }
} as const;

export const COMPLEXITY_LEVELS = {
  simple: { color: '#10b981', threshold: 0.3 },
  medium: { color: '#f59e0b', threshold: 0.5 },
  complex: { color: '#ef4444', threshold: 0.7 },
  very_complex: { color: '#8b5cf6', threshold: 1.0 }
} as const;