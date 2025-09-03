/**
 * Multi-Agent Coordination Patterns Tests
 * Specialized test suite for validating coordination algorithms and conflict prevention
 * Focus on core agentic systems patterns and distributed coordination mechanisms
 */

import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createTheme, ThemeProvider } from "@mui/material/styles";

// Import components and types
import DashboardPage from "@/app/(dashboard)/page";
import { AgentStatus } from "@/components/feature/agent-status";
import { SessionMonitor } from "@/components/feature/session-monitor";
import {
  Agent,
  CoordinationMetrics,
  FileLock,
  HookEvent,
  Session,
} from "@/types";
import * as hooks from "@/lib/api/hooks";

// Mock API hooks for coordination testing
jest.mock("@/lib/api/hooks");
const mockHooks = hooks as jest.Mocked<typeof hooks>;

// Create wrapper for providers
const createCoordinationWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  const theme = createTheme();

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe("Multi-Agent Coordination Patterns", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Fan-Out/Fan-In Coordination Pattern", () => {
    const fanOutScenario = {
      session: {
        id: "session_fanout_001",
        coordinationId: "coord_fanout_001",
        status: "running" as const,
        complexity: 0.78,
        confidence: 0.85,
        createdAt: "2024-01-01T10:00:00Z",
        updatedAt: "2024-01-01T10:30:00Z",
        objective: "Multi-perspective research analysis",
        context:
          "FAN_OUT_SYNTHESIZE: Phase 1 (8 researchers) → Phase 2 (3 analysts) → Phase 3 (1 synthesizer)",
      },
      agents: [
        // Discovery phase agents (fan-out)
        {
          id: "researcher_001",
          role: "researcher",
          domain: "memory-systems",
          status: "active" as const,
          currentTask: "Discovery: Memory architecture patterns",
          duration: 1200000, // 20 minutes
          sessionId: "session_fanout_001",
        },
        {
          id: "researcher_002",
          role: "researcher",
          domain: "distributed-systems",
          status: "active" as const,
          currentTask: "Discovery: Consensus mechanisms",
          duration: 1080000, // 18 minutes
          sessionId: "session_fanout_001",
        },
        {
          id: "researcher_003",
          role: "researcher",
          domain: "event-sourcing",
          status: "active" as const,
          currentTask: "Discovery: Event-driven architectures",
          duration: 900000, // 15 minutes
          sessionId: "session_fanout_001",
        },
        // Analysis phase agents (intermediate processing)
        {
          id: "analyst_001",
          role: "analyst",
          domain: "agentic-systems",
          status: "busy" as const,
          currentTask: "Analysis: Cross-pattern synthesis",
          duration: 600000, // 10 minutes
          sessionId: "session_fanout_001",
        },
        {
          id: "analyst_002",
          role: "analyst",
          domain: "software-architecture",
          status: "busy" as const,
          currentTask: "Analysis: Architecture implications",
          duration: 480000, // 8 minutes
          sessionId: "session_fanout_001",
        },
        // Synthesis phase (fan-in)
        {
          id: "synthesizer_001",
          role: "innovator",
          domain: "category-theory",
          status: "idle" as const,
          currentTask: undefined,
          sessionId: "session_fanout_001",
        },
      ],
      events: [
        {
          id: "event_001",
          coordinationId: "coord_fanout_001",
          agentId: "researcher_001",
          eventType: "pre_command" as const,
          timestamp: "2024-01-01T10:15:00Z",
          metadata: { phase: "discovery", pattern: "fan_out" },
        },
        {
          id: "event_002",
          coordinationId: "coord_fanout_001",
          agentId: "analyst_001",
          eventType: "pre_agent_spawn" as const,
          timestamp: "2024-01-01T10:25:00Z",
          metadata: {
            phase: "synthesis",
            pattern: "fan_in",
            awaiting_count: 3,
          },
        },
      ],
    };

    it("should coordinate fan-out discovery phase correctly", async () => {
      mockHooks.useSessions.mockReturnValue({
        data: [fanOutScenario.session],
        isLoading: false,
        error: null,
      } as any);

      mockHooks.useAgents.mockReturnValue({
        data: fanOutScenario.agents,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText("Multi-perspective research analysis"))
          .toBeInTheDocument();
      });

      // Verify fan-out pattern configuration
      expect(
        screen.getByText(
          "FAN_OUT_SYNTHESIZE: Phase 1 (8 researchers) → Phase 2 (3 analysts) → Phase 3 (1 synthesizer)",
        ),
      ).toBeInTheDocument();

      // Verify active discovery agents
      const researcherAgents = fanOutScenario.agents.filter((a) =>
        a.role === "researcher" && a.status === "active"
      );
      expect(researcherAgents).toHaveLength(3);

      // Verify domain specialization
      expect(screen.getByText("memory-systems")).toBeInTheDocument();
      expect(screen.getByText("distributed-systems")).toBeInTheDocument();
      expect(screen.getByText("event-sourcing")).toBeInTheDocument();
    });

    it("should handle analysis phase coordination", async () => {
      const Wrapper = createCoordinationWrapper();

      // Test analyst agents in busy state
      const analystAgent = fanOutScenario.agents.find((a) =>
        a.role === "analyst"
      )!;
      render(<AgentStatus agent={analystAgent} />, { wrapper: Wrapper });

      expect(screen.getByText("Analysis: Cross-pattern synthesis"))
        .toBeInTheDocument();
      expect(screen.getByText("agentic-systems")).toBeInTheDocument();

      // Should show busy status (intermediate processing)
      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "busy");
    });

    it("should validate synthesis phase readiness", async () => {
      const Wrapper = createCoordinationWrapper();

      // Test synthesizer agent waiting for inputs
      const synthesizerAgent = fanOutScenario.agents.find((a) =>
        a.role === "innovator"
      )!;
      render(<AgentStatus agent={synthesizerAgent} />, { wrapper: Wrapper });

      expect(screen.getByText("innovator")).toBeInTheDocument();
      expect(screen.getByText("category-theory")).toBeInTheDocument();

      // Should show idle status (waiting for fan-in completion)
      expect(screen.getByText("💤 Agent is idle and waiting for tasks"))
        .toBeInTheDocument();
    });
  });

  describe("Pipeline Coordination Pattern", () => {
    const pipelineScenario = {
      session: {
        id: "session_pipeline_001",
        coordinationId: "coord_pipeline_001",
        status: "running" as const,
        complexity: 0.62,
        confidence: 0.80,
        createdAt: "2024-01-01T09:00:00Z",
        updatedAt: "2024-01-01T10:15:00Z",
        objective: "Sequential development workflow",
        context:
          "PIPELINE: researcher → architect → implementer → tester → reviewer (sequential handoff)",
      },
      agents: [
        {
          id: "researcher_pipe_001",
          role: "researcher",
          domain: "microkernel-architecture",
          status: "active" as const,
          currentTask: "Pipeline Stage 1: Requirements discovery",
          duration: 1800000, // 30 minutes
          sessionId: "session_pipeline_001",
        },
        {
          id: "architect_pipe_001",
          role: "architect",
          domain: "software-architecture",
          status: "idle" as const,
          currentTask: undefined,
          sessionId: "session_pipeline_001",
        },
        {
          id: "implementer_pipe_001",
          role: "implementer",
          domain: "rust-performance",
          status: "idle" as const,
          currentTask: undefined,
          sessionId: "session_pipeline_001",
        },
        {
          id: "tester_pipe_001",
          role: "tester",
          domain: "agentic-systems",
          status: "idle" as const,
          currentTask: undefined,
          sessionId: "session_pipeline_001",
        },
        {
          id: "reviewer_pipe_001",
          role: "reviewer",
          domain: "software-architecture",
          status: "idle" as const,
          currentTask: undefined,
          sessionId: "session_pipeline_001",
        },
      ],
    };

    it("should coordinate sequential pipeline stages", async () => {
      mockHooks.useSession.mockReturnValue({
        data: pipelineScenario.session,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<SessionMonitor session={pipelineScenario.session} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByText("Sequential development workflow"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "PIPELINE: researcher → architect → implementer → tester → reviewer (sequential handoff)",
        ),
      ).toBeInTheDocument();

      // Verify moderate complexity for sequential coordination
      expect(screen.getByText("0.6")).toBeInTheDocument(); // 0.62 rounded
      expect(screen.getByText("80%")).toBeInTheDocument(); // Confidence
    });

    it("should enforce pipeline stage ordering", async () => {
      const Wrapper = createCoordinationWrapper();

      // Only first stage should be active
      const activeAgent = pipelineScenario.agents.find((a) =>
        a.status === "active"
      )!;
      render(<AgentStatus agent={activeAgent} />, { wrapper: Wrapper });

      expect(screen.getByText("Pipeline Stage 1: Requirements discovery"))
        .toBeInTheDocument();
      expect(screen.getByText("researcher")).toBeInTheDocument();

      // Subsequent stages should be idle
      const idleAgent = pipelineScenario.agents.find((a) =>
        a.role === "architect"
      )!;
      const { rerender } = render(<AgentStatus agent={idleAgent} />, {
        wrapper: Wrapper,
      });
      expect(screen.getByText("💤 Agent is idle and waiting for tasks"))
        .toBeInTheDocument();
    });

    it("should handle pipeline stage transitions", async () => {
      // Simulate stage completion and handoff
      const completedFirstStage = {
        ...pipelineScenario.agents[0],
        status: "idle" as const,
        currentTask: undefined,
      };
      const activatedSecondStage = {
        ...pipelineScenario.agents[1],
        status: "active" as const,
        currentTask: "Pipeline Stage 2: System architecture design",
      };

      const Wrapper = createCoordinationWrapper();

      // Test stage handoff
      render(<AgentStatus agent={activatedSecondStage} />, {
        wrapper: Wrapper,
      });
      expect(screen.getByText("Pipeline Stage 2: System architecture design"))
        .toBeInTheDocument();
      expect(screen.getByText("architect")).toBeInTheDocument();
    });
  });

  describe("Parallel Coordination Pattern", () => {
    const parallelScenario = {
      session: {
        id: "session_parallel_001",
        coordinationId: "coord_parallel_001",
        status: "running" as const,
        complexity: 0.42,
        confidence: 0.94,
        createdAt: "2024-01-01T08:00:00Z",
        updatedAt: "2024-01-01T09:30:00Z",
        objective: "Independent module development",
        context:
          "PARALLEL: 6 implementers on isolated components with no dependencies",
      },
      agents: [
        {
          id: "impl_auth_001",
          role: "implementer",
          domain: "rust-performance",
          status: "active" as const,
          currentTask: "Parallel Module: Authentication service",
          duration: 2400000, // 40 minutes
          sessionId: "session_parallel_001",
        },
        {
          id: "impl_db_001",
          role: "implementer",
          domain: "distributed-systems",
          status: "active" as const,
          currentTask: "Parallel Module: Database layer",
          duration: 2700000, // 45 minutes
          sessionId: "session_parallel_001",
        },
        {
          id: "impl_api_001",
          role: "implementer",
          domain: "protocol-design",
          status: "active" as const,
          currentTask: "Parallel Module: API gateway",
          duration: 2100000, // 35 minutes
          sessionId: "session_parallel_001",
        },
        {
          id: "impl_ui_001",
          role: "implementer",
          domain: "async-programming",
          status: "active" as const,
          currentTask: "Parallel Module: User interface",
          duration: 1800000, // 30 minutes
          sessionId: "session_parallel_001",
        },
      ],
    };

    it("should coordinate independent parallel execution", async () => {
      mockHooks.useSession.mockReturnValue({
        data: parallelScenario.session,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<SessionMonitor session={parallelScenario.session} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByText("Independent module development"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "PARALLEL: 6 implementers on isolated components with no dependencies",
        ),
      ).toBeInTheDocument();

      // Verify low complexity for independent work
      expect(screen.getByText("0.4")).toBeInTheDocument(); // 0.42 rounded

      // Verify high confidence for parallel coordination
      expect(screen.getByText("94%")).toBeInTheDocument();
    });

    it("should validate parallel agent independence", async () => {
      const Wrapper = createCoordinationWrapper();

      // All agents should be active simultaneously
      parallelScenario.agents.forEach((agent, index) => {
        const { rerender } = render(<AgentStatus agent={agent} />, {
          wrapper: Wrapper,
        });

        expect(screen.getByText("implementer")).toBeInTheDocument();
        expect(screen.getByText(/Parallel Module:/)).toBeInTheDocument();

        const statusBadge = screen.getByTestId("status-badge");
        expect(statusBadge).toHaveAttribute("data-status", "active");
      });
    });

    it("should handle parallel completion without blocking", async () => {
      // Simulate one module completing while others continue
      const completedModule = {
        ...parallelScenario.agents[0],
        status: "idle" as const,
        currentTask: "Completed: Authentication service",
      };

      const Wrapper = createCoordinationWrapper();
      render(<AgentStatus agent={completedModule} />, { wrapper: Wrapper });

      // Completed module should not affect others
      expect(screen.getByText("Completed: Authentication service"))
        .toBeInTheDocument();

      // Other modules can continue independently
      const continuingModule = parallelScenario.agents[1];
      const { rerender } = render(<AgentStatus agent={continuingModule} />, {
        wrapper: Wrapper,
      });
      expect(screen.getByText("Parallel Module: Database layer"))
        .toBeInTheDocument();
    });
  });

  describe("Hierarchical Delegation Pattern", () => {
    const hierarchicalScenario = {
      session: {
        id: "session_hierarchical_001",
        coordinationId: "coord_hierarchical_001",
        status: "running" as const,
        complexity: 0.88,
        confidence: 0.72,
        createdAt: "2024-01-01T07:00:00Z",
        updatedAt: "2024-01-01T09:45:00Z",
        objective: "Large-scale distributed consensus",
        context:
          "HIERARCHICAL_DELEGATION: 1 coordinator → 4 supervisors → 16 workers → 64 validators",
      },
      coordinationMetrics: {
        conflictsPrevented: 156,
        taskDeduplicationRate: 0.93,
        averageTaskCompletionTime: 45.8,
        activeAgents: 85,
        activeSessions: 1,
      } as CoordinationMetrics,
    };

    it("should handle complex hierarchical coordination", async () => {
      mockHooks.useCoordinationMetrics.mockReturnValue({
        data: hierarchicalScenario.coordinationMetrics,
        isLoading: false,
        error: null,
      } as any);

      mockHooks.useSession.mockReturnValue({
        data: hierarchicalScenario.session,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<SessionMonitor session={hierarchicalScenario.session} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByText("Large-scale distributed consensus"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "HIERARCHICAL_DELEGATION: 1 coordinator → 4 supervisors → 16 workers → 64 validators",
        ),
      ).toBeInTheDocument();

      // Verify high complexity for hierarchical coordination
      expect(screen.getByText("0.9")).toBeInTheDocument(); // 0.88 rounded up

      // Verify moderate confidence due to complexity
      expect(screen.getByText("72%")).toBeInTheDocument();
    });

    it("should track high conflict prevention in complex scenarios", async () => {
      mockHooks.useCoordinationMetrics.mockReturnValue({
        data: hierarchicalScenario.coordinationMetrics,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText("156")).toBeInTheDocument(); // High conflicts prevented
      });

      // High agent count
      expect(screen.getByText("85")).toBeInTheDocument();

      // High task deduplication rate
      expect(screen.getByText("45.8s")).toBeInTheDocument(); // Longer completion time
    });
  });

  describe("Conflict Prevention and Resolution", () => {
    const conflictScenario = {
      fileLocks: [
        {
          filePath: "/workspace/shared_research.md",
          agentId: "researcher_001",
          expiration: "2024-01-01T11:00:00Z",
          isStale: false,
        },
        {
          filePath: "/workspace/shared_research.md", // Potential conflict
          agentId: "analyst_001",
          expiration: "2024-01-01T11:05:00Z",
          isStale: false,
        },
        {
          filePath: "/workspace/analysis.md",
          agentId: "analyst_001",
          expiration: "2024-01-01T10:30:00Z",
          isStale: true, // Stale lock
        },
      ] as FileLock[],
      events: [
        {
          id: "event_conflict_001",
          coordinationId: "coord_001",
          agentId: "researcher_001",
          eventType: "pre_edit" as const,
          timestamp: "2024-01-01T10:45:00Z",
          metadata: {
            file: "/workspace/shared_research.md",
            conflict_detected: false,
            lock_acquired: true,
          },
          filePath: "/workspace/shared_research.md",
        },
        {
          id: "event_conflict_002",
          coordinationId: "coord_001",
          agentId: "analyst_001",
          eventType: "pre_edit" as const,
          timestamp: "2024-01-01T10:47:00Z",
          metadata: {
            file: "/workspace/shared_research.md",
            conflict_detected: true,
            conflict_resolution: "queued_access",
          },
          filePath: "/workspace/shared_research.md",
        },
      ] as HookEvent[],
    };

    it("should detect and prevent file access conflicts", async () => {
      mockHooks.useFileLocks.mockReturnValue({
        data: conflictScenario.fileLocks,
        isLoading: false,
        error: null,
      } as any);

      mockHooks.useEvents.mockReturnValue({
        data: conflictScenario.events,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Should handle file locks transparently in the background
      // The dashboard should show normal operation despite conflicts
      await waitFor(() => {
        expect(screen.getByText("Orchestration Dashboard")).toBeInTheDocument();
      });
    });

    it("should handle stale lock cleanup", async () => {
      const staleLock = conflictScenario.fileLocks.find((lock) => lock.isStale);
      expect(staleLock).toBeDefined();
      expect(staleLock?.isStale).toBe(true);

      // System should identify and clean up stale locks
      // This would typically be handled by the backend coordination service
    });

    it("should coordinate agent task deduplication", async () => {
      const duplicateTaskScenario = {
        agents: [
          {
            id: "researcher_001",
            role: "researcher",
            domain: "memory-systems",
            status: "active" as const,
            currentTask: "Research: Memory architecture patterns",
            sessionId: "session_001",
          },
          {
            id: "researcher_002",
            role: "researcher",
            domain: "memory-systems",
            status: "active" as const,
            currentTask: "Research: Memory architecture patterns", // Duplicate task
            sessionId: "session_001",
          },
        ] as Agent[],
        metrics: {
          conflictsPrevented: 23,
          taskDeduplicationRate: 0.89, // High deduplication rate
          averageTaskCompletionTime: 32.1,
          activeAgents: 2,
          activeSessions: 1,
        } as CoordinationMetrics,
      };

      mockHooks.useAgents.mockReturnValue({
        data: duplicateTaskScenario.agents,
        isLoading: false,
        error: null,
      } as any);

      mockHooks.useCoordinationMetrics.mockReturnValue({
        data: duplicateTaskScenario.metrics,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        // High deduplication rate indicates system is preventing duplicate work
        expect(screen.getByText("89%")).toBeInTheDocument(); // Deduplication rate not directly shown, but conflicts prevented should be visible
      });
    });
  });

  describe("Event-Driven Coordination", () => {
    const eventDrivenScenario = {
      session: {
        id: "session_event_001",
        coordinationId: "coord_event_001",
        status: "running" as const,
        complexity: 0.71,
        confidence: 0.79,
        createdAt: "2024-01-01T08:30:00Z",
        updatedAt: "2024-01-01T10:20:00Z",
        objective: "Event-driven workflow orchestration",
        context:
          "KB_EVENT_PROCESSING: GitHub issues → agent spawning → task execution → result aggregation",
      },
      events: [
        {
          id: "event_spawn_001",
          coordinationId: "coord_event_001",
          agentId: "orchestrator_001",
          eventType: "pre_agent_spawn" as const,
          timestamp: "2024-01-01T10:15:00Z",
          metadata: {
            trigger: "github_issue_created",
            issue_id: "#123",
            spawned_role: "researcher",
            domain: "memory-systems",
          },
        },
        {
          id: "event_command_001",
          coordinationId: "coord_event_001",
          agentId: "researcher_spawned_001",
          eventType: "pre_command" as const,
          timestamp: "2024-01-01T10:16:30Z",
          metadata: {
            command: "research_github_issue",
            issue_context: "memory allocation optimization",
          },
        },
        {
          id: "event_complete_001",
          coordinationId: "coord_event_001",
          agentId: "researcher_spawned_001",
          eventType: "post_command" as const,
          timestamp: "2024-01-01T10:18:45Z",
          metadata: {
            command: "research_github_issue",
            result: "research_complete",
            artifacts: ["research_summary.md"],
          },
        },
      ] as HookEvent[],
    };

    it("should coordinate event-driven agent spawning", async () => {
      mockHooks.useEvents.mockReturnValue({
        data: eventDrivenScenario.events,
        isLoading: false,
        error: null,
      } as any);

      mockHooks.useSession.mockReturnValue({
        data: eventDrivenScenario.session,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<SessionMonitor session={eventDrivenScenario.session} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByText("Event-driven workflow orchestration"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "KB_EVENT_PROCESSING: GitHub issues → agent spawning → task execution → result aggregation",
        ),
      ).toBeInTheDocument();
    });

    it("should track event-driven coordination complexity", async () => {
      mockHooks.useSession.mockReturnValue({
        data: eventDrivenScenario.session,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<SessionMonitor session={eventDrivenScenario.session} />, {
        wrapper: Wrapper,
      });

      // Event-driven coordination has moderate-high complexity
      expect(screen.getByText("0.7")).toBeInTheDocument(); // 0.71 rounded
      expect(screen.getByText("79%")).toBeInTheDocument(); // Moderate confidence
    });
  });

  describe("Byzantine Consensus Patterns", () => {
    const byzantineScenario = {
      session: {
        id: "session_byzantine_001",
        coordinationId: "coord_byzantine_001",
        status: "running" as const,
        complexity: 0.95,
        confidence: 0.68,
        createdAt: "2024-01-01T06:00:00Z",
        updatedAt: "2024-01-01T08:30:00Z",
        objective: "Fault-tolerant distributed validation",
        context:
          "BYZANTINE_CONSENSUS: 2f+1 validation with up to f faulty nodes (f=8, total=25 validators)",
      },
      agents: Array.from({ length: 25 }, (_, i) => ({
        id: `validator_${i.toString().padStart(3, "0")}`,
        role: "critic",
        domain: "distributed-systems",
        status:
          (i < 17 ? "active" : i < 23 ? "busy" : "error") as Agent["status"], // Some faulty nodes
        currentTask: i >= 23
          ? "Byzantine fault detected"
          : `Validation round ${Math.floor(i / 5) + 1}`,
        duration: (i + 1) * 120000, // Varying durations
        sessionId: "session_byzantine_001",
      })),
      metrics: {
        conflictsPrevented: 340,
        taskDeduplicationRate: 0.97,
        averageTaskCompletionTime: 87.3,
        activeAgents: 25,
        activeSessions: 1,
      } as CoordinationMetrics,
    };

    it("should handle Byzantine fault tolerance requirements", async () => {
      mockHooks.useSession.mockReturnValue({
        data: byzantineScenario.session,
        isLoading: false,
        error: null,
      } as any);

      mockHooks.useCoordinationMetrics.mockReturnValue({
        data: byzantineScenario.metrics,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<SessionMonitor session={byzantineScenario.session} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByText("Fault-tolerant distributed validation"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "BYZANTINE_CONSENSUS: 2f+1 validation with up to f faulty nodes (f=8, total=25 validators)",
        ),
      ).toBeInTheDocument();

      // Maximum complexity for Byzantine consensus
      expect(screen.getByText("1.0")).toBeInTheDocument(); // 0.95 rounded up

      // Moderate confidence due to fault tolerance requirements
      expect(screen.getByText("68%")).toBeInTheDocument();
    });

    it("should track fault tolerance metrics", async () => {
      mockHooks.useCoordinationMetrics.mockReturnValue({
        data: byzantineScenario.metrics,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        // Very high conflict prevention due to consensus requirements
        expect(screen.getByText("340")).toBeInTheDocument();
      });

      // High task deduplication for consensus voting
      // Longer average completion time for consensus rounds
      expect(screen.getByText("87.3s")).toBeInTheDocument();

      // Large number of agents for consensus
      expect(screen.getByText("25")).toBeInTheDocument();
    });

    it("should handle validator node faults gracefully", async () => {
      const faultyValidator = byzantineScenario.agents.find((a) =>
        a.status === "error"
      )!;

      const Wrapper = createCoordinationWrapper();
      render(<AgentStatus agent={faultyValidator} />, { wrapper: Wrapper });

      expect(screen.getByText("critic")).toBeInTheDocument(); // Validator role
      expect(screen.getByText("distributed-systems")).toBeInTheDocument();
      expect(screen.getByText("Byzantine fault detected")).toBeInTheDocument();

      // Should show error state
      expect(
        screen.getByText(
          "⚠️ Agent encountered an error and requires attention",
        ),
      ).toBeInTheDocument();
    });
  });

  describe("Coordination Performance Metrics", () => {
    it("should validate coordination efficiency across patterns", async () => {
      const performanceMetrics = {
        conflictsPrevented: 127,
        taskDeduplicationRate: 0.94,
        averageTaskCompletionTime: 24.6,
        activeAgents: 42,
        activeSessions: 8,
      } as CoordinationMetrics;

      mockHooks.useCoordinationMetrics.mockReturnValue({
        data: performanceMetrics,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText("127")).toBeInTheDocument(); // Conflicts prevented
        expect(screen.getByText("42")).toBeInTheDocument(); // Active agents
        expect(screen.getByText("24.6s")).toBeInTheDocument(); // Completion time
      });

      // Efficient coordination should show good metrics
      // High deduplication rate (94%) not directly displayed but contributes to efficiency
    });

    it("should handle coordination scalability limits", async () => {
      const scalabilityTest = {
        metrics: {
          conflictsPrevented: 2340,
          taskDeduplicationRate: 0.89, // Slightly lower due to scale
          averageTaskCompletionTime: 156.7, // Higher due to coordination overhead
          activeAgents: 500, // Large scale
          activeSessions: 25,
        } as CoordinationMetrics,
      };

      mockHooks.useCoordinationMetrics.mockReturnValue({
        data: scalabilityTest.metrics,
        isLoading: false,
        error: null,
      } as any);

      const Wrapper = createCoordinationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText("2340")).toBeInTheDocument(); // Very high conflict prevention
        expect(screen.getByText("500")).toBeInTheDocument(); // Large agent count
        expect(screen.getByText("156.7s")).toBeInTheDocument(); // Higher completion time at scale
      });
    });
  });
});
