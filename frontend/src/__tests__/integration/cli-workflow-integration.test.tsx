import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CommandCenter } from '@/components/layout/CommandCenter';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { CommandPaletteHelp } from '@/components/ui/CommandPaletteHelp';
import { KHIVE_CONFIG, ORCHESTRATION_PATTERNS } from '@/lib/config/khive';

// Mock the WebSocket hook
jest.mock('@/lib/hooks/useKhiveWebSocket', () => ({
  useKhiveWebSocket: () => ({
    connected: true,
    sessions: [
      { sessionId: 'test-1', status: 'executing', agents: [] },
      { sessionId: 'test-2', status: 'pending', agents: [] }
    ],
    events: [
      { id: '1', type: 'agent_spawn', timestamp: Date.now(), data: {} },
      { id: '2', type: 'task_complete', timestamp: Date.now(), data: {} }
    ],
    agents: [],
    sendCommand: jest.fn(),
    reconnect: jest.fn(),
    connectionHealth: {
      status: 'connected',
      latency: 50,
      consecutiveFailures: 0,
      queueSize: 0,
      reconnectCount: 0
    },
    stats: {
      messagesReceived: 100,
      messagesSent: 50,
      duplicatesFiltered: 2,
      reconnectCount: 0,
      averageLatency: 50
    },
    error: null,
    joinCoordination: jest.fn(),
    leaveCoordination: jest.fn(),
    subscribeToSession: jest.fn(),
    unsubscribeFromSession: jest.fn(),
    daemonStatus: {
      running: true,
      health: 'healthy' as const,
      uptime: 86400,
      active_sessions: 2,
      total_agents: 5,
      memory_usage: 512,
      cpu_usage: 25
    }
  })
}));

// Mock other components
jest.mock('@/components/features/OrchestrationTree', () => ({
  OrchestrationTree: ({ focused }: { focused: boolean }) => (
    <div data-testid="orchestration-tree" data-focused={focused}>
      Orchestration Tree
    </div>
  )
}));

jest.mock('@/components/features/Workspace', () => ({
  Workspace: ({ activeView, focused }: { activeView: string; focused: boolean }) => (
    <div data-testid="workspace" data-active-view={activeView} data-focused={focused}>
      Workspace - {activeView}
    </div>
  )
}));

jest.mock('@/components/features/ActivityStream', () => ({
  ActivityStream: ({ focused }: { focused: boolean }) => (
    <div data-testid="activity-stream" data-focused={focused}>
      Activity Stream
    </div>
  )
}));

describe('CLI Workflow Integration', () => {
  let queryClient: QueryClient;
  const user = userEvent.setup();

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  const renderCommandCenter = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <CommandCenter />
      </QueryClientProvider>
    );
  };

  describe('Command Center Integration', () => {
    it('should render all three panes correctly', () => {
      renderCommandCenter();
      
      expect(screen.getByTestId('orchestration-tree')).toBeInTheDocument();
      expect(screen.getByTestId('workspace')).toBeInTheDocument();
      expect(screen.getByTestId('activity-stream')).toBeInTheDocument();
    });

    it('should display correct connection status in status bar', () => {
      renderCommandCenter();
      
      expect(screen.getByText('KHIVE ONLINE')).toBeInTheDocument();
      expect(screen.getByText('(50ms)')).toBeInTheDocument();
      expect(screen.getByText('Sessions: 2')).toBeInTheDocument();
      expect(screen.getByText('Running: 1')).toBeInTheDocument();
      expect(screen.getByText('Queued: 1')).toBeInTheDocument();
    });

    it('should show command palette hint in status bar', () => {
      renderCommandCenter();
      
      expect(screen.getByText('⌘K')).toBeInTheDocument();
      expect(screen.getByText('for commands')).toBeInTheDocument();
    });
  });

  describe('Command Palette Functionality', () => {
    const mockProps = {
      open: true,
      onClose: jest.fn(),
      onCommand: jest.fn(),
      onNavigate: jest.fn(),
      onFocusPane: jest.fn(),
      onShowHelp: jest.fn()
    };

    it('should display comprehensive command list', () => {
      render(<CommandPalette {...mockProps} />);
      
      // Check for key commands
      expect(screen.getByText('Plan Orchestration')).toBeInTheDocument();
      expect(screen.getByText('Compose Agent')).toBeInTheDocument();
      expect(screen.getByText('Go to Planning')).toBeInTheDocument();
      expect(screen.getByText('Focus Orchestration Tree')).toBeInTheDocument();
      expect(screen.getByText('Show Help')).toBeInTheDocument();
    });

    it('should filter commands based on search query', async () => {
      render(<CommandPalette {...mockProps} />);
      
      const searchInput = screen.getByPlaceholderText(/Type a command/);
      await user.type(searchInput, 'plan');
      
      expect(screen.getByText('Plan Orchestration')).toBeInTheDocument();
      expect(screen.getByText('Go to Planning')).toBeInTheDocument();
      // Should not show unrelated commands
      expect(screen.queryByText('Compose Agent')).not.toBeInTheDocument();
    });

    it('should support keyboard navigation', async () => {
      render(<CommandPalette {...mockProps} />);
      
      const searchInput = screen.getByPlaceholderText(/Type a command/);
      
      // Press arrow down to select next command
      await user.type(searchInput, '{arrowdown}');
      await user.type(searchInput, '{enter}');
      
      expect(mockProps.onCommand).toHaveBeenCalled();
    });

    it('should display category chips and shortcuts', () => {
      render(<CommandPalette {...mockProps} />);
      
      // Check for category chips
      expect(screen.getByText('orchestration')).toBeInTheDocument();
      expect(screen.getByText('navigation')).toBeInTheDocument();
      expect(screen.getByText('system')).toBeInTheDocument();
      
      // Check for keyboard shortcuts
      expect(screen.getByText('⌘P')).toBeInTheDocument();
      expect(screen.getByText('⌘N')).toBeInTheDocument();
    });

    it('should handle navigation commands correctly', async () => {
      render(<CommandPalette {...mockProps} />);
      
      const planningCommand = screen.getByText('Go to Planning');
      await user.click(planningCommand);
      
      expect(mockProps.onNavigate).toHaveBeenCalledWith('planning');
      expect(mockProps.onClose).toHaveBeenCalled();
    });

    it('should handle focus pane commands correctly', async () => {
      render(<CommandPalette {...mockProps} />);
      
      const focusCommand = screen.getByText('Focus Orchestration Tree');
      await user.click(focusCommand);
      
      expect(mockProps.onFocusPane).toHaveBeenCalledWith('tree');
      expect(mockProps.onClose).toHaveBeenCalled();
    });

    it('should handle help command correctly', async () => {
      render(<CommandPalette {...mockProps} />);
      
      const helpCommand = screen.getByText('Show Help');
      await user.click(helpCommand);
      
      expect(mockProps.onShowHelp).toHaveBeenCalled();
      expect(mockProps.onClose).toHaveBeenCalled();
    });
  });

  describe('Command Palette Help Dialog', () => {
    const mockHelpProps = {
      open: true,
      onClose: jest.fn()
    };

    it('should display keyboard shortcuts reference', () => {
      render(<CommandPaletteHelp {...mockHelpProps} />);
      
      expect(screen.getByText('KHIVE Command Reference')).toBeInTheDocument();
      expect(screen.getByText('Global Navigation')).toBeInTheDocument();
      expect(screen.getByText('Vim-Style Navigation')).toBeInTheDocument();
      expect(screen.getByText('Orchestration Actions')).toBeInTheDocument();
    });

    it('should display CLI commands reference', async () => {
      render(<CommandPaletteHelp {...mockHelpProps} />);
      
      const cliTab = screen.getByText('CLI Commands');
      await user.click(cliTab);
      
      expect(screen.getByText('khive plan')).toBeInTheDocument();
      expect(screen.getByText('khive compose')).toBeInTheDocument();
      expect(screen.getByText('khive coordinate')).toBeInTheDocument();
    });

    it('should display orchestration patterns', async () => {
      render(<CommandPaletteHelp {...mockHelpProps} />);
      
      const patternsTab = screen.getByText('Orchestration Patterns');
      await user.click(patternsTab);
      
      // Check for orchestration patterns from config
      Object.entries(ORCHESTRATION_PATTERNS).forEach(([key, pattern]) => {
        expect(screen.getByText(key)).toBeInTheDocument();
        expect(screen.getByText(pattern.name)).toBeInTheDocument();
      });
    });
  });

  describe('Focus Management', () => {
    it('should highlight focused pane correctly', () => {
      renderCommandCenter();
      
      // Default focus should be on workspace
      const workspace = screen.getByTestId('workspace');
      expect(workspace).toHaveAttribute('data-focused', 'true');
      
      const tree = screen.getByTestId('orchestration-tree');
      expect(tree).toHaveAttribute('data-focused', 'false');
    });

    it('should update focus indicators in status bar', async () => {
      renderCommandCenter();
      
      // Should show default focus
      expect(screen.getByText('Focus: WORKSPACE')).toBeInTheDocument();
      expect(screen.getByText('View: MONITORING')).toBeInTheDocument();
    });
  });

  describe('Real-time Integration', () => {
    it('should display session information correctly', () => {
      renderCommandCenter();
      
      // Check session counts from mocked data
      expect(screen.getByText('Sessions: 2')).toBeInTheDocument();
      expect(screen.getByText('Running: 1')).toBeInTheDocument();
      expect(screen.getByText('Queued: 1')).toBeInTheDocument();
    });

    it('should show connection health status', () => {
      renderCommandCenter();
      
      expect(screen.getByText('KHIVE ONLINE')).toBeInTheDocument();
      expect(screen.getByText('(50ms)')).toBeInTheDocument();
      // Should not show retry indicator when no failures
      expect(screen.queryByText(/Retries:/)).not.toBeInTheDocument();
    });
  });

  describe('Terminal-style UI Elements', () => {
    it('should use terminal font family from config', () => {
      renderCommandCenter();
      
      const statusBar = screen.getByText('KHIVE ONLINE').closest('.MuiBox-root');
      expect(statusBar).toHaveStyle({
        fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT
      });
    });

    it('should display command palette with terminal styling', () => {
      render(<CommandPalette {...{ 
        open: true, 
        onClose: jest.fn(), 
        onCommand: jest.fn() 
      }} />);
      
      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
      
      const input = screen.getByPlaceholderText(/Type a command/);
      expect(input).toHaveStyle({
        fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT
      });
    });
  });

  describe('Performance and Accessibility', () => {
    it('should handle large command lists efficiently', () => {
      const start = performance.now();
      render(<CommandPalette {...{ 
        open: true, 
        onClose: jest.fn(), 
        onCommand: jest.fn() 
      }} />);
      const end = performance.now();
      
      // Should render in under 100ms
      expect(end - start).toBeLessThan(100);
    });

    it('should have proper ARIA labels and roles', () => {
      render(<CommandPalette {...{ 
        open: true, 
        onClose: jest.fn(), 
        onCommand: jest.fn() 
      }} />);
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      expect(screen.getByRole('list')).toBeInTheDocument();
    });

    it('should support keyboard-only navigation', async () => {
      render(<CommandPalette {...{ 
        open: true, 
        onClose: jest.fn(), 
        onCommand: jest.fn() 
      }} />);
      
      const input = screen.getByPlaceholderText(/Type a command/);
      
      // Tab should move focus properly
      await user.tab();
      expect(input).toHaveFocus();
      
      // Arrow keys should work for navigation
      await user.keyboard('{ArrowDown}');
      await user.keyboard('{ArrowUp}');
      await user.keyboard('{Enter}');
    });
  });
});