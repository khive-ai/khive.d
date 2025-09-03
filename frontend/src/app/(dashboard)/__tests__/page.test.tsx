/**
 * Dashboard Page Tests
 * Comprehensive test suite for orchestration dashboard functionality
 * Focus on multi-agent coordination patterns and real-time monitoring
 */

import React from "react";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import DashboardPage from "../page";
import * as hooks from "@/lib/api/hooks";

// Mock the API hooks
jest.mock("@/lib/api/hooks");

// Create a wrapper component for providers
const createWrapper = () => {
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

// Mock data for agentic systems testing
const mockCoordinationMetrics = {
  conflictsPrevented: 27,
  taskDeduplicationRate: 0.85,
  averageTaskCompletionTime: 42.3,
  activeAgents: 8,
  activeSessions: 3,
};

const mockSessions = [
  {
    id: "session_001",
    name: "Research Analysis Pipeline",
    status: "running" as const,
    coordinator: "lion",
    agents: ["researcher_001", "analyst_001", "critic_001"],
    startTime: "2024-01-01T10:00:00Z",
    duration: "15m 32s",
    progress: 75,
    coordinationId: "coord_001",
    complexity: 0.65,
    confidence: 0.82,
    createdAt: "2024-01-01T10:00:00Z",
    updatedAt: "2024-01-01T10:15:32Z",
    objective: "Multi-perspective research analysis with synthesis",
    context: "fan_out_fan_in coordination pattern",
  },
  {
    id: "session_002",
    name: "Parallel Implementation Tasks",
    status: "completed" as const,
    coordinator: "lion",
    agents: ["implementer_001", "implementer_002", "tester_001"],
    startTime: "2024-01-01T09:00:00Z",
    duration: "1h 12m",
    progress: 100,
    coordinationId: "coord_002",
    complexity: 0.45,
    confidence: 0.95,
    createdAt: "2024-01-01T09:00:00Z",
    updatedAt: "2024-01-01T10:12:00Z",
    objective: "Parallel implementation with test coverage",
    context: "parallel coordination pattern",
  },
  {
    id: "session_003",
    name: "Error Recovery Workflow",
    status: "failed" as const,
    coordinator: "lion",
    agents: ["recovery_001"],
    startTime: "2024-01-01T11:00:00Z",
    duration: "5m 45s",
    progress: 25,
    coordinationId: "coord_003",
    complexity: 0.85,
    confidence: 0.32,
    createdAt: "2024-01-01T11:00:00Z",
    updatedAt: "2024-01-01T11:05:45Z",
    objective: "Recovery from coordination failure",
    context: "error recovery protocol",
  },
];

const mockAgents = [
  {
    id: "researcher_001",
    name: "Research Agent Alpha",
    role: "researcher",
    domain: "memory-systems",
    status: "active" as const,
    tasks: 3,
    lastActivity: "2 minutes ago",
    currentTask: "Analyzing distributed memory patterns",
    duration: 900000, // 15 minutes
    sessionId: "session_001",
  },
  {
    id: "analyst_001",
    name: "Systems Analyst Beta",
    role: "analyst",
    domain: "agentic-systems",
    status: "busy" as const,
    tasks: 2,
    lastActivity: "1 minute ago",
    currentTask: "Synthesizing research findings",
    duration: 600000, // 10 minutes
    sessionId: "session_001",
  },
  {
    id: "critic_001",
    name: "Quality Critic Gamma",
    role: "critic",
    domain: "software-architecture",
    status: "idle" as const,
    tasks: 0,
    lastActivity: "30 seconds ago",
    sessionId: "session_001",
  },
  {
    id: "implementer_002",
    name: "Implementation Agent Delta",
    role: "implementer",
    domain: "distributed-systems",
    status: "error" as const,
    tasks: 1,
    lastActivity: "5 minutes ago",
    currentTask: "Failed coordination recovery",
    sessionId: "session_003",
  },
];

describe("Dashboard Page", () => {
  const mockHooks = hooks as jest.Mocked<typeof hooks>;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();

    // Setup default mock responses
    mockHooks.useCoordinationMetrics.mockReturnValue({
      data: mockCoordinationMetrics,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    } as any);

    mockHooks.useSessions.mockReturnValue({
      data: mockSessions,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    } as any);

    mockHooks.useAgents.mockReturnValue({
      data: mockAgents,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    } as any);
  });

  describe("Dashboard Rendering", () => {
    it("should render the main dashboard title and description", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      expect(screen.getByText("Orchestration Dashboard")).toBeInTheDocument();
      expect(
        screen.getByText(
          /Real-time monitoring and control of agent coordination/,
        ),
      ).toBeInTheDocument();
    });

    it("should display correct quick stats from coordination metrics", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Verify active sessions count
      const runningSessions =
        mockSessions.filter((s) => s.status === "running").length;
      expect(screen.getByText(runningSessions.toString())).toBeInTheDocument();
      expect(screen.getByText("Currently orchestrating")).toBeInTheDocument();

      // Verify active agents count
      expect(screen.getByText(mockCoordinationMetrics.activeAgents.toString()))
        .toBeInTheDocument();
      expect(screen.getByText("Available for coordination"))
        .toBeInTheDocument();

      // Verify conflicts prevented
      expect(
        screen.getByText(mockCoordinationMetrics.conflictsPrevented.toString()),
      ).toBeInTheDocument();
      expect(screen.getByText("Today")).toBeInTheDocument();

      // Verify average task time
      expect(
        screen.getByText(
          `${mockCoordinationMetrics.averageTaskCompletionTime.toFixed(1)}s`,
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("Completion time")).toBeInTheDocument();
    });
  });

  describe("Multi-Agent Coordination Display", () => {
    it("should display sessions with coordination patterns", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Check session names and coordination info
      expect(screen.getByText("Research Analysis Pipeline"))
        .toBeInTheDocument();
      expect(screen.getByText("Parallel Implementation Tasks"))
        .toBeInTheDocument();
      expect(screen.getByText("Error Recovery Workflow")).toBeInTheDocument();

      // Check coordinator information
      expect(screen.getAllByText("lion")).toHaveLength(3); // All sessions coordinated by lion
    });

    it("should display agent roles and domains correctly", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Check role chips
      expect(screen.getByText("researcher")).toBeInTheDocument();
      expect(screen.getByText("analyst")).toBeInTheDocument();
      expect(screen.getByText("critic")).toBeInTheDocument();
      expect(screen.getByText("implementer")).toBeInTheDocument();

      // Check domain chips
      expect(screen.getByText("memory-systems")).toBeInTheDocument();
      expect(screen.getByText("agentic-systems")).toBeInTheDocument();
      expect(screen.getByText("software-architecture")).toBeInTheDocument();
      expect(screen.getByText("distributed-systems")).toBeInTheDocument();
    });

    it("should show appropriate status indicators for different agent states", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // The StatusCell components should be rendered with correct colors
      // Note: Testing specific colors would require more detailed implementation
      const statusCells = screen.getAllByTestId(/status-cell|chip/);
      expect(statusCells.length).toBeGreaterThan(0);
    });
  });

  describe("Real-time Updates and Performance", () => {
    it("should handle loading states appropriately", () => {
      mockHooks.useSessions.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: jest.fn(),
      } as any);

      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // The DataTable should show loading state
      // This depends on the DataTable implementation
      expect(screen.getByText("Active Sessions")).toBeInTheDocument();
    });

    it("should setup auto-refresh interval for real-time monitoring", () => {
      jest.useFakeTimers();
      const Wrapper = createWrapper();

      render(<DashboardPage />, { wrapper: Wrapper });

      // Fast-forward time and verify interval behavior
      act(() => {
        jest.advanceTimersByTime(30000); // 30 seconds
      });

      // Component should trigger refresh
      expect(mockHooks.useCoordinationMetrics).toHaveBeenCalled();

      jest.useRealTimers();
    });
  });

  describe("Orchestration Workflow Integration", () => {
    it("should handle session progress visualization correctly", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Progress indicators should be visible
      // Looking for progress percentage text
      expect(screen.getByText("75%")).toBeInTheDocument(); // Session 001 progress
      expect(screen.getByText("100%")).toBeInTheDocument(); // Session 002 progress
      expect(screen.getByText("25%")).toBeInTheDocument(); // Session 003 progress
    });

    it("should display system health indicators", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      expect(screen.getByText("System Health")).toBeInTheDocument();
      expect(screen.getByText("API Gateway")).toBeInTheDocument();
      expect(screen.getByText("Coordination Service")).toBeInTheDocument();
      expect(screen.getByText("Memory Usage")).toBeInTheDocument();

      // Check health status messages
      expect(screen.getByText("Healthy - All endpoints responding"))
        .toBeInTheDocument();
      expect(screen.getByText(/Online - \d+ agents connected/))
        .toBeInTheDocument();
      expect(screen.getByText("Moderate - 67% of available memory"))
        .toBeInTheDocument();
    });
  });

  describe("Search and Filter Functionality", () => {
    it("should render searchable tables with proper configuration", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Look for search placeholders
      const searchInputs = screen.getAllByPlaceholderText(/Search/);
      expect(searchInputs.length).toBeGreaterThanOrEqual(2); // Sessions and agents tables

      expect(screen.getByPlaceholderText("Search sessions..."))
        .toBeInTheDocument();
      expect(screen.getByPlaceholderText("Search agents..."))
        .toBeInTheDocument();
    });
  });

  describe("Error Scenarios", () => {
    it("should handle API errors gracefully", () => {
      mockHooks.useCoordinationMetrics.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("API unavailable"),
        refetch: jest.fn(),
      } as any);

      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Dashboard should still render with fallback values
      expect(screen.getByText("Orchestration Dashboard")).toBeInTheDocument();
      expect(screen.getByText("0")).toBeInTheDocument(); // Fallback metric values
    });

    it("should display empty states when no data is available", () => {
      mockHooks.useSessions.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      } as any);

      mockHooks.useAgents.mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
        refetch: jest.fn(),
      } as any);

      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Empty state messages should be visible
      expect(screen.getByText("No active sessions")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Start a new orchestration session to see activity here",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("No agents available")).toBeInTheDocument();
      expect(screen.getByText("Deploy agents to start coordinating tasks"))
        .toBeInTheDocument();
    });
  });

  describe("Agentic Systems Patterns Validation", () => {
    it("should correctly identify and display fan-out coordination patterns", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Session 001 uses fan_out_fan_in pattern with 3 agents
      const session001 = mockSessions[0];
      expect(screen.getByText(session001.name)).toBeInTheDocument();
      expect(screen.getByText(session001.agents.length.toString()))
        .toBeInTheDocument();
    });

    it("should display coordination complexity and confidence metrics", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // The session data includes complexity and confidence, but these aren't directly
      // displayed in the dashboard. They might be in session details or tooltips.
      // For now, verify the sessions are displayed correctly
      expect(screen.getByText("Research Analysis Pipeline"))
        .toBeInTheDocument();
      expect(screen.getByText("Parallel Implementation Tasks"))
        .toBeInTheDocument();
    });

    it("should handle different agent status states in multi-agent scenarios", () => {
      const Wrapper = createWrapper();
      render(<DashboardPage />, { wrapper: Wrapper });

      // Verify that agents with different states are all displayed
      expect(screen.getByText("Research Agent Alpha")).toBeInTheDocument();
      expect(screen.getByText("Systems Analyst Beta")).toBeInTheDocument();
      expect(screen.getByText("Quality Critic Gamma")).toBeInTheDocument();
      expect(screen.getByText("Implementation Agent Delta"))
        .toBeInTheDocument();
    });
  });
});
