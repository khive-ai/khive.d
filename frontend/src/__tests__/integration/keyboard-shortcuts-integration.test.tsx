import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CommandCenter } from '@/components/layout/CommandCenter';
import { useKeyboardShortcuts } from '@/lib/hooks/useKeyboardShortcuts';

// Mock the WebSocket hook
jest.mock('@/lib/hooks/useKhiveWebSocket', () => ({
  useKhiveWebSocket: () => ({
    connected: true,
    sessions: [],
    events: [],
    agents: [],
    sendCommand: jest.fn().mockResolvedValue(true),
    reconnect: jest.fn().mockResolvedValue(undefined),
    connectionHealth: {
      status: 'connected',
      latency: 25,
      consecutiveFailures: 0,
      queueSize: 0,
      reconnectCount: 0
    },
    stats: {
      messagesReceived: 50,
      messagesSent: 25,
      duplicatesFiltered: 0,
      reconnectCount: 0,
      averageLatency: 25
    },
    error: null,
    joinCoordination: jest.fn(),
    leaveCoordination: jest.fn(),
    subscribeToSession: jest.fn(),
    unsubscribeFromSession: jest.fn(),
    daemonStatus: {
      running: true,
      health: 'healthy' as const,
      uptime: 3600,
      active_sessions: 0,
      total_agents: 0,
      memory_usage: 256,
      cpu_usage: 15
    }
  })
}));

// Mock components to focus on keyboard functionality
jest.mock('@/components/features/OrchestrationTree', () => ({
  OrchestrationTree: ({ focused }: { focused: boolean }) => (
    <div data-testid="orchestration-tree" data-focused={focused}>
      Tree
    </div>
  )
}));

jest.mock('@/components/features/Workspace', () => ({
  Workspace: ({ activeView, focused }: { activeView: string; focused: boolean }) => (
    <div data-testid="workspace" data-active-view={activeView} data-focused={focused}>
      Workspace
    </div>
  )
}));

jest.mock('@/components/features/ActivityStream', () => ({
  ActivityStream: ({ focused }: { focused: boolean }) => (
    <div data-testid="activity-stream" data-focused={focused}>
      Stream
    </div>
  )
}));

// Test component for isolated keyboard shortcuts testing
function TestKeyboardComponent({ onShortcut }: { onShortcut: (key: string) => void }) {
  const shortcuts = [
    {
      key: 'cmd+k',
      action: () => onShortcut('cmd+k'),
      description: 'Test shortcut'
    },
    {
      key: 'g p',
      action: () => onShortcut('g p'),
      description: 'Vim navigation test'
    },
    {
      key: 'cmd+1',
      action: () => onShortcut('cmd+1'),
      description: 'Number shortcut'
    },
    {
      key: 'escape',
      action: () => onShortcut('escape'),
      description: 'Escape key'
    }
  ];

  useKeyboardShortcuts(shortcuts);

  return (
    <div data-testid="keyboard-test">
      <input data-testid="test-input" placeholder="Test input" />
      <div>Keyboard shortcuts active</div>
    </div>
  );
}

describe('Keyboard Shortcuts Integration', () => {
  let queryClient: QueryClient;

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

  describe('Global Keyboard Shortcuts', () => {
    it('should open command palette with Cmd+K', async () => {
      renderCommandCenter();
      
      // Simulate Cmd+K
      fireEvent.keyDown(document, {
        key: 'k',
        metaKey: true,
        bubbles: true
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
    });

    it('should focus panes with number shortcuts', async () => {
      renderCommandCenter();
      
      // Focus tree pane with Cmd+1
      fireEvent.keyDown(document, {
        key: '1',
        metaKey: true,
        bubbles: true
      });

      await waitFor(() => {
        const tree = screen.getByTestId('orchestration-tree');
        expect(tree).toHaveAttribute('data-focused', 'true');
      });

      // Focus workspace with Cmd+2
      fireEvent.keyDown(document, {
        key: '2',
        metaKey: true,
        bubbles: true
      });

      await waitFor(() => {
        const workspace = screen.getByTestId('workspace');
        expect(workspace).toHaveAttribute('data-focused', 'true');
      });

      // Focus activity stream with Cmd+3
      fireEvent.keyDown(document, {
        key: '3',
        metaKey: true,
        bubbles: true
      });

      await waitFor(() => {
        const stream = screen.getByTestId('activity-stream');
        expect(stream).toHaveAttribute('data-focused', 'true');
      });
    });

    it('should handle vim-style navigation shortcuts', async () => {
      renderCommandCenter();
      
      // Test 'g p' sequence for planning
      fireEvent.keyDown(document, {
        key: 'g',
        bubbles: true
      });

      fireEvent.keyDown(document, {
        key: 'p',
        bubbles: true
      });

      await waitFor(() => {
        const workspace = screen.getByTestId('workspace');
        expect(workspace).toHaveAttribute('data-active-view', 'planning');
      });
    });

    it('should handle escape key correctly', async () => {
      renderCommandCenter();
      
      // Open command palette first
      fireEvent.keyDown(document, {
        key: 'k',
        metaKey: true,
        bubbles: true
      });

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      // Press escape to close
      fireEvent.keyDown(document, {
        key: 'Escape',
        bubbles: true
      });

      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      });
    });

    it('should handle help shortcut Cmd+Shift+K', async () => {
      renderCommandCenter();
      
      fireEvent.keyDown(document, {
        key: 'k',
        metaKey: true,
        shiftKey: true,
        bubbles: true
      });

      await waitFor(() => {
        expect(screen.getByText('KHIVE Command Reference')).toBeInTheDocument();
      });
    });
  });

  describe('Keyboard Shortcuts Hook Behavior', () => {
    it('should register and trigger shortcuts correctly', () => {
      const mockOnShortcut = jest.fn();
      
      render(<TestKeyboardComponent onShortcut={mockOnShortcut} />);
      
      // Test Cmd+K
      fireEvent.keyDown(document, {
        key: 'k',
        metaKey: true,
        bubbles: true
      });
      
      expect(mockOnShortcut).toHaveBeenCalledWith('cmd+k');
    });

    it('should handle sequence shortcuts correctly', () => {
      const mockOnShortcut = jest.fn();
      
      render(<TestKeyboardComponent onShortcut={mockOnShortcut} />);
      
      // Test 'g p' sequence
      fireEvent.keyDown(document, {
        key: 'g',
        bubbles: true
      });
      
      fireEvent.keyDown(document, {
        key: 'p',
        bubbles: true
      });
      
      expect(mockOnShortcut).toHaveBeenCalledWith('g p');
    });

    it('should not trigger shortcuts when typing in inputs', () => {
      const mockOnShortcut = jest.fn();
      
      render(<TestKeyboardComponent onShortcut={mockOnShortcut} />);
      
      const input = screen.getByTestId('test-input');
      input.focus();
      
      // Type in input - should not trigger shortcut
      fireEvent.keyDown(input, {
        key: 'k',
        metaKey: true,
        target: input,
        bubbles: true
      });
      
      expect(mockOnShortcut).not.toHaveBeenCalled();
    });

    it('should handle timeout for sequence shortcuts', async () => {
      const mockOnShortcut = jest.fn();
      
      render(<TestKeyboardComponent onShortcut={mockOnShortcut} />);
      
      // Start sequence but don't complete it
      fireEvent.keyDown(document, {
        key: 'g',
        bubbles: true
      });
      
      // Wait for timeout (1500ms + buffer)
      await new Promise(resolve => setTimeout(resolve, 1600));
      
      // Now press 'p' - should not trigger the sequence
      fireEvent.keyDown(document, {
        key: 'p',
        bubbles: true
      });
      
      expect(mockOnShortcut).not.toHaveBeenCalledWith('g p');
    });
  });

  describe('Command Center Specific Shortcuts', () => {
    it('should handle quick planning shortcut Cmd+P', async () => {
      renderCommandCenter();
      
      fireEvent.keyDown(document, {
        key: 'p',
        metaKey: true,
        bubbles: true
      });

      await waitFor(() => {
        const workspace = screen.getByTestId('workspace');
        expect(workspace).toHaveAttribute('data-active-view', 'planning');
        expect(workspace).toHaveAttribute('data-focused', 'true');
      });
    });

    it('should send commands for orchestration shortcuts', async () => {
      const mockSendCommand = jest.fn();
      
      // Mock the sendCommand function
      jest.mocked(require('@/lib/hooks/useKhiveWebSocket').useKhiveWebSocket).mockReturnValue({
        connected: true,
        sessions: [],
        events: [],
        agents: [],
        sendCommand: mockSendCommand,
        reconnect: jest.fn(),
        connectionHealth: { status: 'connected', latency: 25, consecutiveFailures: 0, queueSize: 0, reconnectCount: 0 },
        stats: { messagesReceived: 50, messagesSent: 25, duplicatesFiltered: 0, reconnectCount: 0, averageLatency: 25 },
        error: null,
        joinCoordination: jest.fn(),
        leaveCoordination: jest.fn(),
        subscribeToSession: jest.fn(),
        unsubscribeFromSession: jest.fn(),
        daemonStatus: { running: true, health: 'healthy' as const, uptime: 3600, active_sessions: 0, total_agents: 0, memory_usage: 256, cpu_usage: 15 }
      });

      renderCommandCenter();
      
      // Test Cmd+N for new orchestration
      fireEvent.keyDown(document, {
        key: 'n',
        metaKey: true,
        bubbles: true
      });

      expect(mockSendCommand).toHaveBeenCalledWith('new_orchestration');
    });

    it('should handle single-key shortcuts in context', async () => {
      renderCommandCenter();
      
      // Test 'c' for compose agent (context-dependent)
      fireEvent.keyDown(document, {
        key: 'c',
        bubbles: true
      });

      // Should trigger the compose command
      expect(require('@/lib/hooks/useKhiveWebSocket').useKhiveWebSocket().sendCommand)
        .toHaveBeenCalledWith('khive compose');
    });
  });

  describe('Shortcut Accessibility and UX', () => {
    it('should prevent default browser behavior for custom shortcuts', () => {
      const mockOnShortcut = jest.fn();
      
      render(<TestKeyboardComponent onShortcut={mockOnShortcut} />);
      
      const keyDownEvent = new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: true,
        bubbles: true,
        cancelable: true
      });
      
      const preventDefaultSpy = jest.spyOn(keyDownEvent, 'preventDefault');
      const stopPropagationSpy = jest.spyOn(keyDownEvent, 'stopPropagation');
      
      document.dispatchEvent(keyDownEvent);
      
      expect(preventDefaultSpy).toHaveBeenCalled();
      expect(stopPropagationSpy).toHaveBeenCalled();
    });

    it('should handle multiple rapid keystrokes gracefully', () => {
      const mockOnShortcut = jest.fn();
      
      render(<TestKeyboardComponent onShortcut={mockOnShortcut} />);
      
      // Rapid fire shortcuts
      for (let i = 0; i < 10; i++) {
        fireEvent.keyDown(document, {
          key: 'k',
          metaKey: true,
          bubbles: true
        });
      }
      
      expect(mockOnShortcut).toHaveBeenCalledTimes(10);
    });

    it('should work consistently across different focus states', async () => {
      renderCommandCenter();
      
      // Test shortcut works when different elements are focused
      const elements = screen.getAllByRole('generic');
      
      for (const element of elements.slice(0, 3)) {
        if (element.tabIndex >= 0) {
          element.focus();
          
          fireEvent.keyDown(document, {
            key: 'k',
            metaKey: true,
            bubbles: true
          });
          
          await waitFor(() => {
            expect(screen.getByRole('dialog')).toBeInTheDocument();
          });
          
          // Close dialog
          fireEvent.keyDown(document, {
            key: 'Escape',
            bubbles: true
          });
          
          await waitFor(() => {
            expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
          });
        }
      }
    });
  });

  describe('Performance and Memory', () => {
    it('should cleanup event listeners on unmount', () => {
      const mockOnShortcut = jest.fn();
      const addEventListenerSpy = jest.spyOn(document, 'addEventListener');
      const removeEventListenerSpy = jest.spyOn(document, 'removeEventListener');
      
      const { unmount } = render(<TestKeyboardComponent onShortcut={mockOnShortcut} />);
      
      expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
      
      unmount();
      
      expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function));
    });

    it('should handle shortcut updates efficiently', () => {
      const mockOnShortcut = jest.fn();
      
      const { rerender } = render(<TestKeyboardComponent onShortcut={mockOnShortcut} />);
      
      // Trigger shortcut
      fireEvent.keyDown(document, {
        key: 'k',
        metaKey: true,
        bubbles: true
      });
      
      expect(mockOnShortcut).toHaveBeenCalledWith('cmd+k');
      
      // Rerender component
      rerender(<TestKeyboardComponent onShortcut={mockOnShortcut} />);
      
      // Shortcut should still work
      fireEvent.keyDown(document, {
        key: 'k',
        metaKey: true,
        bubbles: true
      });
      
      expect(mockOnShortcut).toHaveBeenCalledTimes(2);
    });
  });
});