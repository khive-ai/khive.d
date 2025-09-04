/**
 * ConsensusPlannerV3 Integration Tests
 * 
 * Tests the complete planning workflow including:
 * - Planning request submission
 * - Consensus visualization
 * - Agent coordination monitoring
 * - Plan execution tracking
 * - WebSocket real-time updates
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { jest } from '@jest/globals';

// Mock WebSocket and API services
import { KhiveApiService } from '@/lib/services/khiveApiService';
import { khiveWebSocketService } from '@/lib/services/khiveWebSocketService';
import { PlanningWizard } from '@/components/features/workspace/PlanningWizard';
import { ConsensusVisualization } from '@/components/features/planning/ConsensusVisualization';
import { AgentCoordinationPanel } from '@/components/features/planning/AgentCoordinationPanel';
import { PlanExecutionMonitor } from '@/components/features/planning/PlanExecutionMonitor';

// Mock data
const mockPlanningResponse = {
  success: true,
  summary: 'Multi-agent orchestration plan for test task',
  complexity: 'medium',
  complexity_score: 0.6,
  pattern: 'P∥',
  recommended_agents: 3,
  coordination_id: 'coord_test_123',
  confidence: 0.85,
  spawn_commands: [
    'spawn researcher memory-systems',
    'spawn analyst agentic-systems',
    'spawn implementer software-architecture'
  ],
  phases: [
    {
      name: 'Research Phase',
      description: 'Initial research and analysis',
      agents: [
        {
          id: 'agent_001',
          role: 'researcher',
          domain: 'memory-systems',
          priority: 1,
          status: 'spawning',
          coordination_id: 'coord_test_123',
          reasoning: 'Research expertise needed',
          progress: 0
        }
      ],
      dependencies: [],
      quality_gate: 'thorough',
      coordination_strategy: 'parallel',
      expected_artifacts: ['research_report.md']
    }
  ],
  cost: 0.0123,
  tokens: { input: 150, output: 300 }
};

const mockConsensusRounds = [
  {
    round: 1,
    agents: [
      {
        agentId: 'agent_001',
        role: 'researcher',
        domain: 'memory-systems',
        vote: 'approach_a',
        confidence: 0.8,
        reasoning: 'Memory-first approach is optimal',
        status: 'voted',
        priority: 1,
        reputation: 0.9,
        voteHistory: []
      },
      {
        agentId: 'agent_002',
        role: 'analyst',
        domain: 'agentic-systems',
        vote: null,
        confidence: 0,
        reasoning: '',
        status: 'thinking',
        priority: 2,
        reputation: 0.85,
        voteHistory: []
      }
    ],
    convergence: 0.5,
    timeoutMs: 30000,
    timeRemaining: 25000,
    status: 'active',
    strategies: [
      {
        id: 'strategy_1',
        name: 'approach_a',
        description: 'Memory-first orchestration approach',
        votes: 1,
        proposedBy: 'agent_001',
        complexity: 3,
        feasibility: 4,
        cost: 100,
        timeEstimate: 2
      }
    ],
    votes: { approach_a: 1 },
    startTime: Date.now() - 5000,
    byzantineFaultTolerance: true,
    quorumThreshold: 2
  }
];

const mockCoordinationEvents = [
  {
    timestamp: Date.now() - 1000,
    type: 'agent_spawn',
    agent_id: 'agent_001',
    session_id: 'session_001',
    coordination_id: 'coord_test_123',
    message: 'Agent researcher+memory-systems spawned',
    metadata: { role: 'researcher', domain: 'memory-systems' }
  },
  {
    timestamp: Date.now() - 500,
    type: 'task_start',
    agent_id: 'agent_001',
    session_id: 'session_001',
    coordination_id: 'coord_test_123',
    message: 'Started research task',
    metadata: { task: 'initial_research' }
  }
];

// Mock implementations
jest.mock('@/lib/services/khiveApiService');
jest.mock('@/lib/services/khiveWebSocketService');

const mockKhiveApiService = KhiveApiService as jest.Mocked<typeof KhiveApiService>;
const mockWebSocketService = khiveWebSocketService as jest.Mocked<typeof khiveWebSocketService>;

describe('ConsensusPlannerV3 Integration', () => {
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();

    // Setup API service mocks
    mockKhiveApiService.submitPlan.mockResolvedValue(mockPlanningResponse);
    mockKhiveApiService.getPlanningResult.mockResolvedValue(mockPlanningResponse);
    mockKhiveApiService.getCoordinationEvents.mockResolvedValue(mockCoordinationEvents);
    mockKhiveApiService.getAgentsByCoordination.mockResolvedValue([]);
    mockKhiveApiService.getSessionsByCoordination.mockResolvedValue([]);

    // Setup WebSocket service mocks
    mockWebSocketService.on = jest.fn();
    mockWebSocketService.off = jest.fn();
    mockWebSocketService.joinCoordination = jest.fn();
    mockWebSocketService.leaveCoordination = jest.fn();
    mockWebSocketService.connect = jest.fn().mockResolvedValue(undefined);
    mockWebSocketService.disconnect = jest.fn();
  });

  describe('PlanningWizard Integration', () => {
    test('completes full planning workflow', async () => {
      const user = userEvent.setup();
      render(<PlanningWizard />);

      // Step 1: Define task
      expect(screen.getByText('ConsensusPlannerV3 - Multi-Agent Orchestration')).toBeInTheDocument();
      
      const taskInput = screen.getByLabelText('Task Description');
      await user.type(taskInput, 'Test multi-agent orchestration task');

      const complexitySelect = screen.getByLabelText('Complexity');
      await user.click(complexitySelect);
      await user.click(screen.getByText('Complex'));

      const patternSelect = screen.getByLabelText('Pattern');
      await user.click(patternSelect);
      await user.click(screen.getByText('Parallel Independent'));

      const planButton = screen.getByText('Start Consensus Planning');
      await user.click(planButton);

      // Verify API call
      await waitFor(() => {
        expect(mockKhiveApiService.submitPlan).toHaveBeenCalledWith(
          expect.objectContaining({
            task_description: 'Test multi-agent orchestration task',
            complexity: 'complex',
            pattern: 'P∥'
          })
        );
      });

      // Step 2: Verify consensus step
      await waitFor(() => {
        expect(screen.getByText('Consensus Planning Progress')).toBeInTheDocument();
      });

      // Step 3: Verify WebSocket connection
      expect(mockWebSocketService.joinCoordination).toHaveBeenCalledWith('coord_test_123');
    });

    test('handles planning errors gracefully', async () => {
      const user = userEvent.setup();
      const planningError = new Error('Planning service unavailable');
      mockKhiveApiService.submitPlan.mockRejectedValue(planningError);

      render(<PlanningWizard />);

      const taskInput = screen.getByLabelText('Task Description');
      await user.type(taskInput, 'Test task');

      const planButton = screen.getByText('Start Consensus Planning');
      await user.click(planButton);

      await waitFor(() => {
        expect(screen.getByText('Planning service unavailable')).toBeInTheDocument();
      });
    });

    test('validates required fields', async () => {
      const user = userEvent.setup();
      render(<PlanningWizard />);

      const planButton = screen.getByText('Start Consensus Planning');
      await user.click(planButton);

      await waitFor(() => {
        expect(screen.getByText('Task description is required')).toBeInTheDocument();
      });

      expect(mockKhiveApiService.submitPlan).not.toHaveBeenCalled();
    });
  });

  describe('ConsensusVisualization Integration', () => {
    test('displays consensus rounds with agent voting', async () => {
      render(
        <ConsensusVisualization
          rounds={mockConsensusRounds}
          currentRound={0}
          showHistoricalData={true}
        />
      );

      // Verify consensus overview metrics
      expect(screen.getByText('Consensus Overview - Round 1')).toBeInTheDocument();
      expect(screen.getByText('50%')).toBeInTheDocument(); // Consensus level
      expect(screen.getByText('1/2')).toBeInTheDocument(); // Agent participation

      // Verify agent consensus display
      expect(screen.getByText('researcher+memory-systems')).toBeInTheDocument();
      expect(screen.getByText('Vote: approach_a (80% confidence)')).toBeInTheDocument();
      expect(screen.getByText('analyst+agentic-systems')).toBeInTheDocument();
      expect(screen.getByText('Vote: Thinking... (0% confidence)')).toBeInTheDocument();

      // Verify Byzantine fault tolerance
      expect(screen.getByText(/Byzantine Fault Tolerance/)).toBeInTheDocument();
    });

    test('handles agent clicks and interactions', async () => {
      const user = userEvent.setup();
      const onAgentClick = jest.fn();

      render(
        <ConsensusVisualization
          rounds={mockConsensusRounds}
          currentRound={0}
          onAgentClick={onAgentClick}
        />
      );

      // Click on agent consensus section
      const agentSection = screen.getByText('Agent Consensus Status');
      await user.click(agentSection);

      // Find and click on an agent row
      const agentRow = screen.getByText('researcher+memory-systems').closest('tr');
      expect(agentRow).toBeInTheDocument();

      if (agentRow) {
        await user.click(agentRow);
        expect(onAgentClick).toHaveBeenCalledWith('agent_001');
      }
    });

    test('shows strategy breakdown with voting distribution', async () => {
      render(
        <ConsensusVisualization
          rounds={mockConsensusRounds}
          currentRound={0}
        />
      );

      // Expand strategy breakdown
      const user = userEvent.setup();
      const strategySection = screen.getByText('Strategy Breakdown');
      await user.click(strategySection);

      expect(screen.getByText('approach_a')).toBeInTheDocument();
      expect(screen.getByText('Memory-first orchestration approach')).toBeInTheDocument();
      expect(screen.getByText('1 votes')).toBeInTheDocument();
    });
  });

  describe('AgentCoordinationPanel Integration', () => {
    test('displays coordination overview metrics', async () => {
      render(
        <AgentCoordinationPanel
          coordinationId="coord_test_123"
          realTimeUpdates={true}
        />
      );

      expect(screen.getByText('Agent Coordination Monitor')).toBeInTheDocument();
      expect(screen.getByText('Total Coordinations')).toBeInTheDocument();
      expect(screen.getByText('Active Agents')).toBeInTheDocument();
      expect(screen.getByText('Active Locks')).toBeInTheDocument();
      expect(screen.getByText('Active Conflicts')).toBeInTheDocument();
    });

    test('handles WebSocket events for real-time updates', async () => {
      const { rerender } = render(
        <AgentCoordinationPanel
          coordinationId="coord_test_123"
          realTimeUpdates={true}
        />
      );

      // Verify WebSocket event handler registration
      expect(mockWebSocketService.on).toHaveBeenCalledWith(
        'coordination_event',
        expect.any(Function)
      );

      // Simulate WebSocket event
      const eventHandler = mockWebSocketService.on.mock.calls.find(
        call => call[0] === 'coordination_event'
      )?.[1];

      if (eventHandler) {
        act(() => {
          eventHandler(mockCoordinationEvents[0]);
        });
      }

      rerender(
        <AgentCoordinationPanel
          coordinationId="coord_test_123"
          realTimeUpdates={true}
        />
      );

      // Verify event appears in the UI
      expect(screen.getByText('Agent researcher+memory-systems spawned')).toBeInTheDocument();
    });

    test('displays conflict resolution interface', async () => {
      const mockConflictEvent = {
        ...mockCoordinationEvents[0],
        type: 'conflict' as const,
        message: 'File lock conflict detected'
      };

      render(
        <AgentCoordinationPanel
          coordinationId="coord_test_123"
          realTimeUpdates={true}
          showConflictResolution={true}
        />
      );

      // Switch to conflicts tab
      const user = userEvent.setup();
      const conflictsTab = screen.getByText('Conflicts');
      await user.click(conflictsTab);

      // Simulate conflict event
      const eventHandler = mockWebSocketService.on.mock.calls.find(
        call => call[0] === 'coordination_event'
      )?.[1];

      if (eventHandler) {
        act(() => {
          eventHandler(mockConflictEvent);
        });
      }

      await waitFor(() => {
        expect(screen.getByText('No Active Conflicts')).toBeInTheDocument();
      });
    });
  });

  describe('PlanExecutionMonitor Integration', () => {
    test('monitors plan execution progress', async () => {
      render(
        <PlanExecutionMonitor
          coordinationId="coord_test_123"
          planningResponse={mockPlanningResponse}
        />
      );

      expect(screen.getByText('Execution Progress')).toBeInTheDocument();
      expect(screen.getByText('Phase 1 of 1: Research Phase')).toBeInTheDocument();
      expect(screen.getByText('Key Metrics')).toBeInTheDocument();

      // Verify execution controls
      expect(screen.getByText('Start')).toBeInTheDocument();
      expect(screen.getByText('Pause')).toBeInTheDocument();
      expect(screen.getByText('Stop')).toBeInTheDocument();
    });

    test('handles plan execution lifecycle', async () => {
      const user = userEvent.setup();
      const onPhaseComplete = jest.fn();
      const onExecutionComplete = jest.fn();

      render(
        <PlanExecutionMonitor
          coordinationId="coord_test_123"
          planningResponse={mockPlanningResponse}
          onPhaseComplete={onPhaseComplete}
          onExecutionComplete={onExecutionComplete}
        />
      );

      // Start execution
      const startButton = screen.getByText('Start');
      await user.click(startButton);

      // Verify execution started
      expect(screen.getByText('Start')).toHaveAttribute('aria-pressed', 'true');

      // Simulate phase completion
      const eventHandler = mockWebSocketService.on.mock.calls.find(
        call => call[0] === 'coordination_event'
      )?.[1];

      if (eventHandler) {
        act(() => {
          eventHandler({
            ...mockCoordinationEvents[1],
            type: 'task_complete'
          });
        });
      }

      // Phase completion should be detected
      await waitFor(() => {
        expect(onPhaseComplete).toHaveBeenCalledWith(0);
      });
    });

    test('displays real-time metrics and charts', async () => {
      render(
        <PlanExecutionMonitor
          coordinationId="coord_test_123"
          planningResponse={mockPlanningResponse}
        />
      );

      // Switch to metrics tab
      const user = userEvent.setup();
      const metricsTab = screen.getByText('Metrics & Charts');
      await user.click(metricsTab);

      expect(screen.getByText('Phase Progress Overview')).toBeInTheDocument();
      expect(screen.getByText('Resource Utilization')).toBeInTheDocument();
    });
  });

  describe('WebSocket Integration', () => {
    test('establishes WebSocket connection on component mount', () => {
      render(<PlanningWizard />);

      expect(mockWebSocketService.on).toHaveBeenCalledWith(
        'coordination_event',
        expect.any(Function)
      );
      expect(mockWebSocketService.on).toHaveBeenCalledWith(
        'session_updated',
        expect.any(Function)
      );
      expect(mockWebSocketService.on).toHaveBeenCalledWith(
        'agent_updated',
        expect.any(Function)
      );
    });

    test('cleans up WebSocket listeners on unmount', () => {
      const { unmount } = render(<PlanningWizard />);

      unmount();

      expect(mockWebSocketService.off).toHaveBeenCalledWith(
        'coordination_event',
        expect.any(Function)
      );
      expect(mockWebSocketService.off).toHaveBeenCalledWith(
        'session_updated',
        expect.any(Function)
      );
      expect(mockWebSocketService.off).toHaveBeenCalledWith(
        'agent_updated',
        expect.any(Function)
      );
    });

    test('joins and leaves coordination rooms appropriately', () => {
      const { rerender } = render(
        <AgentCoordinationPanel coordinationId="coord_test_123" />
      );

      expect(mockWebSocketService.joinCoordination).toHaveBeenCalledWith('coord_test_123');

      // Change coordination ID
      rerender(
        <AgentCoordinationPanel coordinationId="coord_test_456" />
      );

      expect(mockWebSocketService.leaveCoordination).toHaveBeenCalledWith('coord_test_123');
      expect(mockWebSocketService.joinCoordination).toHaveBeenCalledWith('coord_test_456');
    });
  });

  describe('Error Handling and Recovery', () => {
    test('handles API errors with retry mechanism', async () => {
      const user = userEvent.setup();
      
      // First call fails, second succeeds
      mockKhiveApiService.submitPlan
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce(mockPlanningResponse);

      render(<PlanningWizard />);

      const taskInput = screen.getByLabelText('Task Description');
      await user.type(taskInput, 'Test task');

      const planButton = screen.getByText('Start Consensus Planning');
      await user.click(planButton);

      // Should show error initially
      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });

      // Retry should succeed
      await user.click(planButton);
      
      await waitFor(() => {
        expect(screen.getByText('Consensus Planning Progress')).toBeInTheDocument();
      });
    });

    test('handles WebSocket connection failures gracefully', async () => {
      mockWebSocketService.connect.mockRejectedValue(new Error('Connection failed'));

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      render(
        <AgentCoordinationPanel
          coordinationId="coord_test_123"
          realTimeUpdates={true}
        />
      );

      // Should not crash the component
      expect(screen.getByText('Agent Coordination Monitor')).toBeInTheDocument();

      consoleSpy.mockRestore();
    });
  });

  describe('Performance and Optimization', () => {
    test('limits event history to prevent memory leaks', async () => {
      render(
        <AgentCoordinationPanel
          coordinationId="coord_test_123"
          realTimeUpdates={true}
        />
      );

      const eventHandler = mockWebSocketService.on.mock.calls.find(
        call => call[0] === 'coordination_event'
      )?.[1];

      if (eventHandler) {
        // Send 150 events (more than the 100 limit)
        for (let i = 0; i < 150; i++) {
          act(() => {
            eventHandler({
              ...mockCoordinationEvents[0],
              timestamp: Date.now() - i * 1000,
              message: `Event ${i}`
            });
          });
        }
      }

      // Switch to event stream tab
      const user = userEvent.setup();
      const eventStreamTab = screen.getByText('Event Stream');
      await user.click(eventStreamTab);

      // Should only show the most recent 20 events in the UI
      expect(screen.getByText('Event 0')).toBeInTheDocument();
      expect(screen.queryByText('Event 149')).not.toBeInTheDocument();
    });

    test('debounces frequent WebSocket updates', async () => {
      const { rerender } = render(
        <ConsensusVisualization
          rounds={mockConsensusRounds}
          currentRound={0}
        />
      );

      // Simulate rapid consensus updates
      const updatedRounds = mockConsensusRounds.map(round => ({
        ...round,
        convergence: 0.75
      }));

      rerender(
        <ConsensusVisualization
          rounds={updatedRounds}
          currentRound={0}
        />
      );

      // Should handle updates smoothly without performance issues
      expect(screen.getByText('75%')).toBeInTheDocument();
    });
  });
});

describe('Integration with KHIVE Backend', () => {
  test('sends correct API requests for planning workflow', async () => {
    const user = userEvent.setup();
    render(<PlanningWizard />);

    const taskInput = screen.getByLabelText('Task Description');
    await user.type(taskInput, 'Complex orchestration task');

    const maxAgentsInput = screen.getByLabelText('Max Agents');
    await user.clear(maxAgentsInput);
    await user.type(maxAgentsInput, '7');

    const planButton = screen.getByText('Start Consensus Planning');
    await user.click(planButton);

    await waitFor(() => {
      expect(mockKhiveApiService.submitPlan).toHaveBeenCalledWith({
        task_description: 'Complex orchestration task',
        complexity: 'medium',
        pattern: 'P∥',
        max_agents: 7
      });
    });
  });

  test('processes planning response correctly', async () => {
    const user = userEvent.setup();
    render(<PlanningWizard />);

    const taskInput = screen.getByLabelText('Task Description');
    await user.type(taskInput, 'Test task');

    const planButton = screen.getByText('Start Consensus Planning');
    await user.click(planButton);

    await waitFor(() => {
      expect(screen.getByText('Consensus Planning Progress')).toBeInTheDocument();
      expect(screen.getByText('Multi-agent orchestration plan for test task')).toBeInTheDocument();
    });

    // Advance to results
    const reviewButton = screen.getByText('Review Planning Results');
    await user.click(reviewButton);

    await waitFor(() => {
      expect(screen.getByText('Planning Results')).toBeInTheDocument();
      expect(screen.getByText('0.60')).toBeInTheDocument(); // complexity score
      expect(screen.getByText('P∥')).toBeInTheDocument(); // pattern
      expect(screen.getByText('85%')).toBeInTheDocument(); // confidence
    });
  });
});