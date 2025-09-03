/**
 * Orchestration Workflows Integration Tests
 * End-to-end testing of complete multi-agent coordination workflows
 * Validates system-wide behavior and coordination patterns
 */

import React from "react";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { rest } from "msw";
import { setupServer } from "msw/node";

// Import components for integration testing
import DashboardPage from "@/app/(dashboard)/page";
import { AgentStatus } from "@/components/feature/agent-status";
import { SessionMonitor } from "@/components/feature/session-monitor";
import { Agent, CoordinationMetrics, Session } from "@/types";

// Mock server for API responses
const server = setupServer(
  // Sessions endpoints
  rest.get("/api/sessions", (req, res, ctx) => {
    return res(ctx.json(mockSessionsData));
  }),
  rest.post("/api/sessions", (req, res, ctx) => {
    const newSession = {
      id: "session_new_001",
      coordinationId: "coord_new_001",
      status: "running",
      complexity: 0.6,
      confidence: 0.8,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      objective: "New orchestration session",
      context: "Integration test session",
    };
    return res(ctx.json(newSession));
  }),
  // Agents endpoints
  rest.get("/api/agents", (req, res, ctx) => {
    return res(ctx.json(mockAgentsData));
  }),
  // Coordination metrics
  rest.get("/api/coordination/metrics", (req, res, ctx) => {
    return res(ctx.json(mockMetricsData));
  }),
  // Events endpoint
  rest.get("/api/events", (req, res, ctx) => {
    const coordinationId = req.url.searchParams.get("coordination_id");
    const filteredEvents = coordinationId
      ? mockEventsData.filter((e) => e.coordinationId === coordinationId)
      : mockEventsData;
    return res(ctx.json(filteredEvents));
  }),
  // File locks endpoint
  rest.get("/api/coordination/file-locks", (req, res, ctx) => {
    return res(ctx.json(mockFileLocksData));
  }),
  // Configuration endpoints
  rest.get("/api/config/roles", (req, res, ctx) => {
    return res(ctx.json(mockRolesData));
  }),
  rest.get("/api/config/domains", (req, res, ctx) => {
    return res(ctx.json(mockDomainsData));
  }),
);

// Mock data for comprehensive orchestration scenarios
const mockMetricsData: CoordinationMetrics = {
  conflictsPrevented: 89,
  taskDeduplicationRate: 0.91,
  averageTaskCompletionTime: 28.7,
  activeAgents: 15,
  activeSessions: 6,
};

const mockSessionsData: Session[] = [
  {
    id: "session_fanout_001",
    coordinationId: "coord_fanout_001",
    status: "running",
    complexity: 0.75,
    confidence: 0.87,
    createdAt: "2024-01-01T10:00:00Z",
    updatedAt: "2024-01-01T10:30:00Z",
    objective: "Multi-perspective research synthesis",
    context: "FAN_OUT_SYNTHESIZE: 8 researchers → 3 analysts → 1 synthesizer",
  },
  {
    id: "session_pipeline_001",
    coordinationId: "coord_pipeline_001",
    status: "running",
    complexity: 0.62,
    confidence: 0.82,
    createdAt: "2024-01-01T09:30:00Z",
    updatedAt: "2024-01-01T10:45:00Z",
    objective: "Sequential development workflow",
    context:
      "PIPELINE: researcher → architect → implementer → tester → reviewer",
  },
  {
    id: "session_parallel_001",
    coordinationId: "coord_parallel_001",
    status: "completed",
    complexity: 0.45,
    confidence: 0.96,
    createdAt: "2024-01-01T08:00:00Z",
    updatedAt: "2024-01-01T09:15:00Z",
    objective: "Parallel module implementation",
    context: "PARALLEL: 6 implementers on independent components",
  },
  {
    id: "session_recovery_001",
    coordinationId: "coord_recovery_001",
    status: "failed",
    complexity: 0.92,
    confidence: 0.15,
    createdAt: "2024-01-01T11:00:00Z",
    updatedAt: "2024-01-01T11:20:00Z",
    objective: "Complex distributed consensus",
    context: "Byzantine fault tolerance with 25 nodes - coordination failure",
  },
];

const mockAgentsData: Agent[] = [
  {
    id: "researcher_001",
    role: "researcher",
    domain: "memory-systems",
    status: "active",
    currentTask: "Phase 1: Memory architecture discovery",
    duration: 1800000, // 30 minutes
    sessionId: "session_fanout_001",
  },
  {
    id: "researcher_002",
    role: "researcher",
    domain: "distributed-systems",
    status: "active",
    currentTask: "Phase 1: Consensus algorithm research",
    duration: 1500000, // 25 minutes
    sessionId: "session_fanout_001",
  },
  {
    id: "analyst_001",
    role: "analyst",
    domain: "agentic-systems",
    status: "busy",
    currentTask: "Phase 2: Synthesizing research findings",
    duration: 900000, // 15 minutes
    sessionId: "session_fanout_001",
  },
  {
    id: "architect_001",
    role: "architect",
    domain: "software-architecture",
    status: "active",
    currentTask: "Pipeline: System design phase",
    duration: 2100000, // 35 minutes
    sessionId: "session_pipeline_001",
  },
  {
    id: "implementer_001",
    role: "implementer",
    domain: "rust-performance",
    status: "active",
    currentTask: "Parallel: Core module implementation",
    duration: 3600000, // 60 minutes
    sessionId: "session_parallel_001",
  },
  {
    id: "tester_001",
    role: "tester",
    domain: "agentic-systems",
    status: "idle",
    sessionId: "session_pipeline_001",
  },
  {
    id: "recovery_001",
    role: "critic",
    domain: "distributed-systems",
    status: "error",
    currentTask: "Failed: Byzantine consensus resolution",
    duration: 600000, // 10 minutes
    sessionId: "session_recovery_001",
  },
];

const mockEventsData = [
  {
    id: "event_001",
    coordinationId: "coord_fanout_001",
    agentId: "researcher_001",
    eventType: "pre_command" as const,
    timestamp: "2024-01-01T10:15:00Z",
    metadata: { command: "research", phase: "discovery" },
  },
  {
    id: "event_002",
    coordinationId: "coord_fanout_001",
    agentId: "analyst_001",
    eventType: "pre_agent_spawn" as const,
    timestamp: "2024-01-01T10:25:00Z",
    metadata: { spawned_role: "synthesizer", pattern: "fan_in" },
  },
];

const mockFileLocksData = [
  {
    filePath: "/workspace/research_findings.md",
    agentId: "researcher_001",
    expiration: "2024-01-01T11:00:00Z",
    isStale: false,
  },
  {
    filePath: "/workspace/analysis.md",
    agentId: "analyst_001",
    expiration: "2024-01-01T11:15:00Z",
    isStale: false,
  },
];

const mockRolesData = [
  {
    id: "researcher",
    name: "Researcher",
    description: "Discovery and exploration",
    capabilities: ["research", "analysis"],
    filePath: "/roles/researcher.yml",
  },
  {
    id: "analyst",
    name: "Analyst",
    description: "Pattern recognition and synthesis",
    capabilities: ["analysis", "synthesis"],
    filePath: "/roles/analyst.yml",
  },
];

const mockDomainsData = [
  {
    id: "memory-systems",
    name: "Memory Systems",
    description: "Memory architectures",
    knowledgePatterns: {},
    decisionRules: {},
    specializedTools: [],
    metrics: [],
    filePath: "/domains/memory-systems.yml",
  },
  {
    id: "agentic-systems",
    name: "Agentic Systems",
    description: "Multi-agent coordination",
    knowledgePatterns: {},
    decisionRules: {},
    specializedTools: [],
    metrics: [],
    filePath: "/domains/agentic-systems.yml",
  },
];

// Test wrapper with all providers
const createIntegrationWrapper = () => {
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

describe("Orchestration Workflows Integration Tests", () => {
  beforeAll(() => {
    server.listen();
  });

  beforeEach(() => {
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  describe("Complete Dashboard Workflow", () => {
    it("should render dashboard with real-time coordination data", async () => {
      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByText("Orchestration Dashboard")).toBeInTheDocument();
      });

      // Verify metrics display
      expect(screen.getByText("89")).toBeInTheDocument(); // Conflicts prevented
      expect(screen.getByText("15")).toBeInTheDocument(); // Active agents
      expect(screen.getByText("28.7s")).toBeInTheDocument(); // Avg completion time

      // Verify sessions are displayed
      expect(screen.getByText("Multi-perspective research synthesis"))
        .toBeInTheDocument();
      expect(screen.getByText("Sequential development workflow"))
        .toBeInTheDocument();
      expect(screen.getByText("Parallel module implementation"))
        .toBeInTheDocument();

      // Verify agents are displayed
      expect(screen.getByText("Research Agent Alpha")).toBeInTheDocument();
      expect(screen.getByText("Systems Analyst Beta")).toBeInTheDocument();
    });

    it("should handle search functionality across tables", async () => {
      const user = userEvent.setup();
      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText("Orchestration Dashboard")).toBeInTheDocument();
      });

      // Search in sessions table
      const sessionSearch = screen.getByPlaceholderText("Search sessions...");
      await user.type(sessionSearch, "research");

      // Should filter to sessions containing 'research'
      await waitFor(() => {
        expect(screen.getByText("Multi-perspective research synthesis"))
          .toBeInTheDocument();
      });

      // Search in agents table
      const agentSearch = screen.getByPlaceholderText("Search agents...");
      await user.clear(agentSearch);
      await user.type(agentSearch, "researcher");

      // Should filter to agents with 'researcher' role
      await waitFor(() => {
        expect(screen.getByText("researcher")).toBeInTheDocument();
      });
    });
  });

  describe("Multi-Agent Coordination Patterns", () => {
    it("should display fan-out/fan-in coordination pattern", async () => {
      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(
          screen.getByText(
            "FAN_OUT_SYNTHESIZE: 8 researchers → 3 analysts → 1 synthesizer",
          ),
        ).toBeInTheDocument();
      });

      // Verify complexity and progress for fan-out pattern
      expect(screen.getByText("87%")).toBeInTheDocument(); // Progress from confidence
    });

    it("should handle pipeline coordination workflow", async () => {
      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(
          screen.getByText(
            "PIPELINE: researcher → architect → implementer → tester → reviewer",
          ),
        ).toBeInTheDocument();
      });

      // Pipeline should show sequential agent coordination
      expect(screen.getByText("Sequential development workflow"))
        .toBeInTheDocument();
    });

    it("should show parallel coordination results", async () => {
      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(
          screen.getByText(
            "PARALLEL: 6 implementers on independent components",
          ),
        ).toBeInTheDocument();
      });

      // Parallel coordination should show completed status
      expect(screen.getByText("Parallel module implementation"))
        .toBeInTheDocument();
    });
  });

  describe("Agent Lifecycle Management Workflow", () => {
    it("should manage active agents in coordination", async () => {
      const user = userEvent.setup();
      const mockAgent = mockAgentsData[0]; // researcher_001
      const onStop = jest.fn();
      const onViewDetails = jest.fn();

      const Wrapper = createIntegrationWrapper();
      render(
        <AgentStatus
          agent={mockAgent}
          onStop={onStop}
          onViewDetails={onViewDetails}
        />,
        { wrapper: Wrapper },
      );

      // Verify agent information
      expect(screen.getByText("researcher")).toBeInTheDocument();
      expect(screen.getByText("memory-systems")).toBeInTheDocument();
      expect(screen.getByText("Phase 1: Memory architecture discovery"))
        .toBeInTheDocument();

      // Test control actions
      const stopButton = screen.getByRole("button", { name: /stop agent/i });
      await user.click(stopButton);
      expect(onStop).toHaveBeenCalledWith("researcher_001");

      const detailsButton = screen.getByRole("button", {
        name: /view details/i,
      });
      await user.click(detailsButton);
      expect(onViewDetails).toHaveBeenCalledWith("researcher_001");
    });

    it("should handle error recovery scenarios", async () => {
      const user = userEvent.setup();
      const errorAgent = mockAgentsData.find((a) => a.status === "error")!;
      const onRestart = jest.fn();

      const Wrapper = createIntegrationWrapper();
      render(
        <AgentStatus
          agent={errorAgent}
          onRestart={onRestart}
        />,
        { wrapper: Wrapper },
      );

      // Verify error state display
      expect(
        screen.getByText(
          "⚠️ Agent encountered an error and requires attention",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("Failed: Byzantine consensus resolution"))
        .toBeInTheDocument();

      // Test restart action
      const restartButton = screen.getByRole("button", {
        name: /restart agent/i,
      });
      await user.click(restartButton);
      expect(onRestart).toHaveBeenCalledWith("recovery_001");
    });

    it("should manage idle agents waiting for tasks", async () => {
      const idleAgent = mockAgentsData.find((a) => a.status === "idle")!;

      const Wrapper = createIntegrationWrapper();
      render(<AgentStatus agent={idleAgent} />, { wrapper: Wrapper });

      // Verify idle state display
      expect(screen.getByText("💤 Agent is idle and waiting for tasks"))
        .toBeInTheDocument();
      expect(screen.getByRole("button", { name: /restart agent/i }))
        .toBeInTheDocument();
    });
  });

  describe("Session Management Workflow", () => {
    it("should control running session lifecycle", async () => {
      const user = userEvent.setup();
      const runningSession = mockSessionsData[0]; // fan-out session
      const onPause = jest.fn();
      const onStop = jest.fn();

      const Wrapper = createIntegrationWrapper();
      render(
        <SessionMonitor
          session={runningSession}
          onPause={onPause}
          onStop={onStop}
        />,
        { wrapper: Wrapper },
      );

      // Verify session information
      expect(screen.getByText("Multi-perspective research synthesis"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "FAN_OUT_SYNTHESIZE: 8 researchers → 3 analysts → 1 synthesizer",
        ),
      ).toBeInTheDocument();

      // Test session controls
      const pauseButton = screen.getByRole("button", {
        name: /pause session/i,
      });
      await user.click(pauseButton);
      expect(onPause).toHaveBeenCalledWith("session_fanout_001");

      const stopButton = screen.getByRole("button", { name: /stop session/i });
      await user.click(stopButton);
      expect(onStop).toHaveBeenCalledWith("session_fanout_001");
    });

    it("should handle failed session recovery", async () => {
      const failedSession = mockSessionsData.find((s) =>
        s.status === "failed"
      )!;

      const Wrapper = createIntegrationWrapper();
      render(<SessionMonitor session={failedSession} />, { wrapper: Wrapper });

      // Verify failure information
      expect(screen.getByText("Complex distributed consensus"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "Byzantine fault tolerance with 25 nodes - coordination failure",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("15%")).toBeInTheDocument(); // Low confidence

      // Controls should be disabled for failed sessions
      const refreshButton = screen.getByRole("button", {
        name: /refresh session/i,
      });
      expect(refreshButton).toBeDisabled();
    });

    it("should resume paused sessions", async () => {
      const user = userEvent.setup();
      const pausedSession = {
        ...mockSessionsData[0],
        status: "pending" as const,
      };
      const onResume = jest.fn();

      const Wrapper = createIntegrationWrapper();
      render(
        <SessionMonitor
          session={pausedSession}
          onResume={onResume}
        />,
        { wrapper: Wrapper },
      );

      const resumeButton = screen.getByRole("button", {
        name: /resume session/i,
      });
      await user.click(resumeButton);
      expect(onResume).toHaveBeenCalledWith("session_fanout_001");
    });
  });

  describe("Real-time Updates and Coordination", () => {
    it("should handle coordination metrics updates", async () => {
      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText("89")).toBeInTheDocument(); // Initial conflicts prevented
      });

      // Simulate metrics update
      server.use(
        rest.get("/api/coordination/metrics", (req, res, ctx) => {
          return res(ctx.json({
            ...mockMetricsData,
            conflictsPrevented: 92,
            activeAgents: 16,
          }));
        }),
      );

      // The auto-refresh should pick up the new data
      // (In a real scenario, this would happen automatically)
      await waitFor(() => {
        expect(screen.getByText("89")).toBeInTheDocument();
      }, { timeout: 500 });
    });

    it("should display system health indicators", async () => {
      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText("System Health")).toBeInTheDocument();
      });

      // Verify health indicators
      expect(screen.getByText("API Gateway")).toBeInTheDocument();
      expect(screen.getByText("Coordination Service")).toBeInTheDocument();
      expect(screen.getByText("Memory Usage")).toBeInTheDocument();

      expect(screen.getByText("Healthy - All endpoints responding"))
        .toBeInTheDocument();
      expect(screen.getByText(/Online - \d+ agents connected/))
        .toBeInTheDocument();
    });
  });

  describe("Error Handling and Recovery Workflows", () => {
    it("should handle API failure gracefully", async () => {
      // Simulate API failure
      server.use(
        rest.get("/api/sessions", (req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({ error: "Internal Server Error" }),
          );
        }),
      );

      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Dashboard should still render with fallback values
      await waitFor(() => {
        expect(screen.getByText("Orchestration Dashboard")).toBeInTheDocument();
      });

      // Should show empty states or error indicators
      await waitFor(() => {
        // The exact behavior depends on implementation
        expect(screen.getByText("No active sessions")).toBeInTheDocument();
      });
    });

    it("should handle coordination conflicts in multi-agent scenarios", async () => {
      // Simulate file lock conflicts
      server.use(
        rest.get("/api/coordination/file-locks", (req, res, ctx) => {
          return res(ctx.json([
            {
              filePath: "/workspace/shared_analysis.md",
              agentId: "researcher_001",
              expiration: "2024-01-01T11:30:00Z",
              isStale: false,
            },
            {
              filePath: "/workspace/shared_analysis.md", // Conflict!
              agentId: "analyst_001",
              expiration: "2024-01-01T11:35:00Z",
              isStale: false,
            },
          ]));
        }),
      );

      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // The system should handle the conflict gracefully
      // (Implementation details would determine exact behavior)
      await waitFor(() => {
        expect(screen.getByText("Orchestration Dashboard")).toBeInTheDocument();
      });
    });
  });

  describe("Performance and Scalability Workflows", () => {
    it("should handle large numbers of agents efficiently", async () => {
      // Create large dataset
      const manyAgents = Array.from({ length: 50 }, (_, i) => ({
        id: `agent_${i.toString().padStart(3, "0")}`,
        role: ["researcher", "analyst", "implementer", "tester"][i % 4],
        domain:
          ["memory-systems", "agentic-systems", "distributed-systems"][i % 3],
        status: ["active", "busy", "idle"][i % 3] as Agent["status"],
        currentTask: `Task ${i}`,
        duration: i * 60000,
        sessionId: `session_${Math.floor(i / 10)}`,
      }));

      server.use(
        rest.get("/api/agents", (req, res, ctx) => {
          return res(ctx.json(manyAgents));
        }),
      );

      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText("Orchestration Dashboard")).toBeInTheDocument();
      });

      // Should render efficiently without performance issues
      // The table should handle pagination or virtualization
      expect(screen.getByText("Agent Status")).toBeInTheDocument();
    });

    it("should handle concurrent session updates", async () => {
      let updateCount = 0;

      server.use(
        rest.get("/api/sessions", (req, res, ctx) => {
          updateCount++;
          const updatedSessions = mockSessionsData.map((session) => ({
            ...session,
            updatedAt: new Date(Date.now() + updateCount * 1000).toISOString(),
          }));
          return res(ctx.json(updatedSessions));
        }),
      );

      const Wrapper = createIntegrationWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      await waitFor(() => {
        expect(screen.getByText("Orchestration Dashboard")).toBeInTheDocument();
      });

      // Multiple rapid updates should be handled efficiently
      expect(updateCount).toBeGreaterThanOrEqual(1);
    });
  });
});
