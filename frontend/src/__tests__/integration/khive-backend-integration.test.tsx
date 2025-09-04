import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CommandCenter } from '@/components/layout/CommandCenter';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';

// Create a mock WebSocket service
const mockWebSocketService = {
  connect: jest.fn(),
  disconnect: jest.fn(),
  on: jest.fn(),
  off: jest.fn(),
  joinCoordination: jest.fn(),
  leaveCoordination: jest.fn(),
  subscribeToSession: jest.fn(),
  unsubscribeFromSession: jest.fn(),
  getConnectionHealth: jest.fn(() => ({
    status: 'connected',
    latency: 42,
    consecutiveFailures: 0,
    queueSize: 0,
    reconnectCount: 1
  })),
  getStats: jest.fn(() => ({
    messagesReceived: 234,
    messagesSent: 156,
    duplicatesFiltered: 3,
    reconnectCount: 1,
    averageLatency: 42
  }))
};

// Mock KHIVE API Service
const mockApiService = {
  getDaemonStatus: jest.fn(),
  getSessions: jest.fn(),
  executeCommand: jest.fn()
};

// Mock the hooks and services
jest.mock('@/lib/hooks/useKhiveWebSocket');
jest.mock('@/lib/services/khiveApiService', () => ({
  KhiveApiService: mockApiService,
  KhiveApiError: class extends Error {},
  KhiveConnectionError: class extends Error {}
}));
jest.mock('@/lib/services/khiveWebSocketService', () => ({
  khiveWebSocketService: mockWebSocketService
}));

// Mock components for focused testing
jest.mock('@/components/features/OrchestrationTree', () => ({
  OrchestrationTree: ({ sessions, onSessionSelect }: any) => (
    <div data-testid="orchestration-tree">
      {sessions.map((session: any) => (
        <button 
          key={session.sessionId}
          data-testid={`session-${session.sessionId}`}
          onClick={() => onSessionSelect(session.sessionId)}
        >
          {session.sessionId}
        </button>
      ))}
    </div>
  )
}));

jest.mock('@/components/features/Workspace', () => ({
  Workspace: ({ activeView }: any) => (
    <div data-testid="workspace" data-active-view={activeView}>
      Workspace: {activeView}
    </div>
  )
}));

jest.mock('@/components/features/ActivityStream', () => ({
  ActivityStream: ({ events }: any) => (
    <div data-testid="activity-stream">
      {events.map((event: any) => (
        <div key={event.id} data-testid={`event-${event.id}`}>
          {event.type}: {event.data?.message || 'No message'}
        </div>
      ))}
    </div>
  )
}));

describe('KHIVE Backend Integration', () => {
  let queryClient: QueryClient;
  const mockUseKhiveWebSocket = useKhiveWebSocket as jest.MockedFunction<typeof useKhiveWebSocket>;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false }
      }
    });

    // Reset all mocks
    jest.clearAllMocks();

    // Setup default mock return value
    mockUseKhiveWebSocket.mockReturnValue({
      connected: true,
      sessions: [
        {
          sessionId: 'session-1',
          status: 'executing',
          pattern: 'P∥',
          agents: [{ id: 'agent-1', role: 'researcher', status: 'active' }],
          createdAt: new Date(),
          lastActivity: new Date()
        },
        {
          sessionId: 'session-2',
          status: 'pending',
          pattern: 'P→',
          agents: [],
          createdAt: new Date(),
          lastActivity: new Date()
        }
      ],
      events: [
        {
          id: 'event-1',
          type: 'agent_spawn',
          timestamp: Date.now(),
          sessionId: 'session-1',
          data: { agentId: 'agent-1', role: 'researcher' }
        },
        {
          id: 'event-2',
          type: 'task_start',
          timestamp: Date.now(),
          sessionId: 'session-1',
          data: { taskId: 'task-1', description: 'Research market trends' }
        }
      ],
      agents: [
        { id: 'agent-1', role: 'researcher', status: 'active', sessionId: 'session-1' }
      ],
      sendCommand: jest.fn().mockResolvedValue(true),
      reconnect: jest.fn().mockResolvedValue(undefined),
      joinCoordination: jest.fn(),
      leaveCoordination: jest.fn(),
      subscribeToSession: jest.fn(),
      unsubscribeFromSession: jest.fn(),
      daemonStatus: {
        running: true,
        health: 'healthy',
        uptime: 86400,
        active_sessions: 2,
        total_agents: 1,
        memory_usage: 1024,
        cpu_usage: 45
      },
      connectionHealth: {
        status: 'connected',
        latency: 42,
        consecutiveFailures: 0,
        queueSize: 0,
        reconnectCount: 1
      },
      stats: {
        messagesReceived: 234,
        messagesSent: 156,
        duplicatesFiltered: 3,
        reconnectCount: 1,
        averageLatency: 42
      },
      error: null
    });
  });

  const renderCommandCenter = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <CommandCenter />
      </QueryClientProvider>
    );
  };

  describe('WebSocket Connection Management', () => {
    it('should display correct connection status when online', () => {
      renderCommandCenter();
      
      expect(screen.getByText('KHIVE ONLINE')).toBeInTheDocument();
      expect(screen.getByText('(42ms)')).toBeInTheDocument();
    });

    it('should display correct connection status when offline', () => {
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        connected: false,
        connectionHealth: {
          status: 'disconnected',
          latency: 0,
          consecutiveFailures: 3,
          queueSize: 5,
          reconnectCount: 3
        }
      } as any);

      renderCommandCenter();
      
      expect(screen.getByText('KHIVE OFFLINE')).toBeInTheDocument();
      expect(screen.getByText('⚠ Retries: 3')).toBeInTheDocument();
    });

    it('should handle reconnection attempts', async () => {
      const mockReconnect = jest.fn().mockResolvedValue(undefined);
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        reconnect: mockReconnect
      } as any);

      renderCommandCenter();
      
      // Trigger reconnection via keyboard shortcut
      await act(async () => {
        const event = new KeyboardEvent('keydown', {
          key: 'r',
          metaKey: true,
          bubbles: true
        });
        document.dispatchEvent(event);
      });

      expect(mockReconnect).toHaveBeenCalled();
    });

    it('should handle connection errors gracefully', () => {
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        connected: false,
        error: 'Failed to connect to KHIVE daemon'
      } as any);

      renderCommandCenter();
      
      expect(screen.getByText('KHIVE OFFLINE')).toBeInTheDocument();
    });
  });

  describe('Session Management Integration', () => {
    it('should display session information correctly', () => {
      renderCommandCenter();
      
      expect(screen.getByText('Sessions: 2')).toBeInTheDocument();
      expect(screen.getByText('Running: 1')).toBeInTheDocument();
      expect(screen.getByText('Queued: 1')).toBeInTheDocument();
    });

    it('should render sessions in orchestration tree', () => {
      renderCommandCenter();
      
      expect(screen.getByTestId('session-session-1')).toBeInTheDocument();
      expect(screen.getByTestId('session-session-2')).toBeInTheDocument();
    });

    it('should handle session selection', async () => {
      const user = userEvent.setup();
      renderCommandCenter();
      
      const sessionButton = screen.getByTestId('session-session-1');
      await user.click(sessionButton);
      
      // Should switch to monitoring view when session is selected
      const workspace = screen.getByTestId('workspace');
      expect(workspace).toHaveAttribute('data-active-view', 'monitoring');
    });

    it('should update session counts dynamically', () => {
      const { rerender } = renderCommandCenter();
      
      expect(screen.getByText('Running: 1')).toBeInTheDocument();
      
      // Update mock data
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        sessions: [
          {
            sessionId: 'session-1',
            status: 'completed',
            pattern: 'P∥',
            agents: [],
            createdAt: new Date(),
            lastActivity: new Date()
          },
          {
            sessionId: 'session-3',
            status: 'executing',
            pattern: 'P→',
            agents: [],
            createdAt: new Date(),
            lastActivity: new Date()
          }
        ]
      } as any);

      rerender(
        <QueryClientProvider client={queryClient}>
          <CommandCenter />
        </QueryClientProvider>
      );
      
      expect(screen.getByText('Running: 1')).toBeInTheDocument();
      expect(screen.getByText('Queued: 0')).toBeInTheDocument();
    });
  });

  describe('Real-time Event Handling', () => {
    it('should display events in activity stream', () => {
      renderCommandCenter();
      
      expect(screen.getByTestId('event-event-1')).toBeInTheDocument();
      expect(screen.getByTestId('event-event-2')).toBeInTheDocument();
    });

    it('should handle new events dynamically', () => {
      const { rerender } = renderCommandCenter();
      
      // Add new event
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        events: [
          ...mockUseKhiveWebSocket.getMockImplementation()!().events,
          {
            id: 'event-3',
            type: 'task_complete',
            timestamp: Date.now(),
            sessionId: 'session-1',
            data: { taskId: 'task-1', result: 'success' }
          }
        ]
      } as any);

      rerender(
        <QueryClientProvider client={queryClient}>
          <CommandCenter />
        </QueryClientProvider>
      );
      
      expect(screen.getByTestId('event-event-3')).toBeInTheDocument();
    });

    it('should limit event history to prevent memory leaks', () => {
      // Create many events to test the limit
      const manyEvents = Array.from({ length: 1500 }, (_, i) => ({
        id: `event-${i}`,
        type: 'test_event',
        timestamp: Date.now() - (i * 1000),
        sessionId: 'session-1',
        data: { index: i }
      }));

      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        events: manyEvents
      } as any);

      renderCommandCenter();
      
      // Should only display up to MAX_ACTIVITY_STREAM_ITEMS
      const eventElements = screen.getAllByTestId(/event-event-/);
      expect(eventElements.length).toBeLessThanOrEqual(1000); // From KHIVE_CONFIG.UI.MAX_ACTIVITY_STREAM_ITEMS
    });
  });

  describe('Command Execution', () => {
    it('should send commands through WebSocket', async () => {
      const mockSendCommand = jest.fn().mockResolvedValue(true);
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        sendCommand: mockSendCommand
      } as any);

      renderCommandCenter();
      
      // Open command palette and execute a command
      const event = new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: true,
        bubbles: true
      });
      document.dispatchEvent(event);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const user = userEvent.setup();
      const planCommand = screen.getByText('Plan Orchestration');
      await user.click(planCommand);

      expect(mockSendCommand).toHaveBeenCalledWith('khive plan');
    });

    it('should handle command execution failures', async () => {
      const mockSendCommand = jest.fn().mockResolvedValue(false);
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        sendCommand: mockSendCommand,
        error: 'Command execution failed'
      } as any);

      renderCommandCenter();
      
      // The error should be handled gracefully
      expect(screen.getByText('KHIVE ONLINE')).toBeInTheDocument();
    });

    it('should handle system commands locally', async () => {
      const mockReconnect = jest.fn().mockResolvedValue(undefined);
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        reconnect: mockReconnect
      } as any);

      renderCommandCenter();
      
      // Open command palette
      const event = new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: true,
        bubbles: true
      });
      document.dispatchEvent(event);

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });

      const user = userEvent.setup();
      const reconnectCommand = screen.getByText('Reconnect WebSocket');
      await user.click(reconnectCommand);

      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe('Daemon Status Integration', () => {
    it('should display comprehensive daemon status', () => {
      renderCommandCenter();
      
      expect(screen.getByText('Sessions: 2')).toBeInTheDocument();
      expect(screen.getByText('Running: 1')).toBeInTheDocument();
      expect(screen.getByText('Queued: 1')).toBeInTheDocument();
    });

    it('should handle daemon offline state', () => {
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        daemonStatus: {
          running: false,
          health: 'unhealthy',
          uptime: 0,
          active_sessions: 0,
          total_agents: 0,
          memory_usage: 0,
          cpu_usage: 0
        }
      } as any);

      renderCommandCenter();
      
      expect(screen.getByText('Running: 0')).toBeInTheDocument();
      expect(screen.getByText('Queued: 0')).toBeInTheDocument();
    });
  });

  describe('Performance and Error Handling', () => {
    it('should handle rapid WebSocket updates efficiently', async () => {
      const { rerender } = renderCommandCenter();
      
      // Simulate rapid updates
      for (let i = 0; i < 10; i++) {
        mockUseKhiveWebSocket.mockReturnValue({
          ...mockUseKhiveWebSocket.getMockImplementation()!(),
          events: [
            {
              id: `rapid-event-${i}`,
              type: 'rapid_update',
              timestamp: Date.now() + i,
              sessionId: 'session-1',
              data: { iteration: i }
            }
          ]
        } as any);

        rerender(
          <QueryClientProvider client={queryClient}>
            <CommandCenter />
          </QueryClientProvider>
        );
      }

      // Should not crash or cause performance issues
      expect(screen.getByTestId('activity-stream')).toBeInTheDocument();
    });

    it('should handle malformed WebSocket data gracefully', () => {
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        events: [
          {
            id: 'malformed-event',
            type: null as any,
            timestamp: 'invalid-timestamp' as any,
            sessionId: undefined as any,
            data: null
          }
        ]
      } as any);

      // Should render without crashing
      expect(() => renderCommandCenter()).not.toThrow();
    });

    it('should maintain state consistency during connection issues', () => {
      const { rerender } = renderCommandCenter();
      
      expect(screen.getByText('KHIVE ONLINE')).toBeInTheDocument();
      
      // Simulate connection loss
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        connected: false,
        error: 'Connection lost'
      } as any);

      rerender(
        <QueryClientProvider client={queryClient}>
          <CommandCenter />
        </QueryClientProvider>
      );
      
      expect(screen.getByText('KHIVE OFFLINE')).toBeInTheDocument();
      
      // Simulate reconnection
      mockUseKhiveWebSocket.mockReturnValue({
        ...mockUseKhiveWebSocket.getMockImplementation()!(),
        connected: true,
        error: null
      } as any);

      rerender(
        <QueryClientProvider client={queryClient}>
          <CommandCenter />
        </QueryClientProvider>
      );
      
      expect(screen.getByText('KHIVE ONLINE')).toBeInTheDocument();
    });
  });
});