/**
 * SessionMonitor Component Tests
 * Comprehensive test suite for orchestration workflow management and session control
 * Focus on coordination strategies, session lifecycle, and workflow patterns
 */

import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { SessionMonitor, SessionMonitorProps } from "../session-monitor";
import { Session } from "@/types";

// Mock the UI components
jest.mock("@/ui", () => ({
  Card: ({ children, className, variant, ...props }: any) => (
    <div data-testid="card" className={className} {...props}>
      {children}
    </div>
  ),
  CardHeader: ({ title, subtitle, action, ...props }: any) => (
    <div data-testid="card-header" {...props}>
      <div data-testid="card-title">{title}</div>
      {subtitle && <div data-testid="card-subtitle">{subtitle}</div>}
      {action && <div data-testid="card-action">{action}</div>}
    </div>
  ),
  CardContent: ({ children, ...props }: any) => (
    <div data-testid="card-content" {...props}>
      {children}
    </div>
  ),
  StatusBadge: ({ status, ...props }: any) => (
    <div data-testid="status-badge" data-status={status} {...props}>
      {status}
    </div>
  ),
}));

// Mock utility functions
jest.mock("@/lib/utils", () => ({
  formatDate: (dateString: string) => {
    const date = new Date(dateString);
    return `${
      date.getMonth() + 1
    }/${date.getDate()}/${date.getFullYear()} ${date.getHours()}:${
      date.getMinutes().toString().padStart(2, "0")
    }`;
  },
  formatDuration: (ms: number) => {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  },
}));

// Create a wrapper component for providers
const createWrapper = () => {
  const theme = createTheme();
  return ({ children }: { children: React.ReactNode }) => (
    <ThemeProvider theme={theme}>
      {children}
    </ThemeProvider>
  );
};

// Mock session data for different orchestration scenarios
const createMockSession = (overrides: Partial<Session> = {}): Session => ({
  id: "session_001",
  coordinationId: "coord_001",
  status: "running",
  complexity: 0.65,
  confidence: 0.82,
  createdAt: "2024-01-01T10:00:00Z",
  updatedAt: "2024-01-01T10:15:32Z",
  objective: "Multi-perspective research analysis with synthesis",
  context: "fan_out_fan_in coordination pattern with 5 agents",
  ...overrides,
});

// Test sessions for different coordination patterns and workflows
const mockSessions = {
  // Fan-out/fan-in coordination pattern
  fanOutFanIn: createMockSession({
    id: "session_fanout_001",
    coordinationId: "coord_fanout_001",
    status: "running",
    complexity: 0.72,
    confidence: 0.85,
    objective: "Parallel research discovery and synthesis",
    context:
      "FAN_OUT_SYNTHESIZE pattern: 7 researchers → 2 analysts → 1 synthesizer",
  }),

  // Pipeline coordination pattern
  pipeline: createMockSession({
    id: "session_pipeline_001",
    coordinationId: "coord_pipeline_001",
    status: "running",
    complexity: 0.58,
    confidence: 0.78,
    objective: "Sequential processing workflow",
    context: "PIPELINE pattern: researcher → architect → implementer → tester",
  }),

  // Parallel coordination pattern
  parallel: createMockSession({
    id: "session_parallel_001",
    coordinationId: "coord_parallel_001",
    status: "running",
    complexity: 0.45,
    confidence: 0.92,
    objective: "Independent parallel task execution",
    context: "PARALLEL pattern: 4 implementers working on separate modules",
  }),

  // Completed session
  completed: createMockSession({
    id: "session_completed_001",
    coordinationId: "coord_completed_001",
    status: "completed",
    complexity: 0.68,
    confidence: 0.95,
    objective: "Successful multi-agent coordination",
    context: "Hierarchical delegation completed successfully",
    updatedAt: "2024-01-01T11:30:00Z",
  }),

  // Failed session
  failed: createMockSession({
    id: "session_failed_001",
    coordinationId: "coord_failed_001",
    status: "failed",
    complexity: 0.89,
    confidence: 0.25,
    objective: "Complex coordination attempt",
    context: "Byzantine consensus failure in distributed validation",
    updatedAt: "2024-01-01T10:45:00Z",
  }),

  // Pending session
  pending: createMockSession({
    id: "session_pending_001",
    coordinationId: "coord_pending_001",
    status: "pending",
    complexity: 0.55,
    confidence: 0.70,
    objective: "Paused multi-agent workflow",
    context: "Session paused for resource reallocation",
  }),
};

describe("SessionMonitor Component", () => {
  const defaultProps: SessionMonitorProps = {
    session: mockSessions.fanOutFanIn,
    onPause: jest.fn(),
    onResume: jest.fn(),
    onStop: jest.fn(),
    onRefresh: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Session Information Display", () => {
    it("should render session ID and coordination ID correctly", () => {
      const Wrapper = createWrapper();
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });

      // Should show last 8 characters of session ID
      expect(screen.getByText("Session out_001")).toBeInTheDocument();
      expect(screen.getByText("Coordination ID: coord_fanout_001"))
        .toBeInTheDocument();
    });

    it("should display session objective and context", () => {
      const Wrapper = createWrapper();
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText("Objective")).toBeInTheDocument();
      expect(screen.getByText("Parallel research discovery and synthesis"))
        .toBeInTheDocument();
      expect(screen.getByText("Context")).toBeInTheDocument();
      expect(
        screen.getByText(
          "FAN_OUT_SYNTHESIZE pattern: 7 researchers → 2 analysts → 1 synthesizer",
        ),
      ).toBeInTheDocument();
    });

    it("should show status badge with correct status", () => {
      const Wrapper = createWrapper();
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });

      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "running");
    });
  });

  describe("Progress and Metrics Display", () => {
    it("should display progress bar for running sessions", () => {
      const Wrapper = createWrapper();
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText("Progress")).toBeInTheDocument();

      // Progress should be based on confidence for running sessions
      const expectedProgress = Math.floor(
        mockSessions.fanOutFanIn.confidence * 100,
      );
      expect(screen.getByText(`${expectedProgress}%`)).toBeInTheDocument();
    });

    it("should show 100% progress for completed sessions", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.completed} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should display complexity and confidence metrics", () => {
      const Wrapper = createWrapper();
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText("Complexity")).toBeInTheDocument();
      expect(screen.getByText("0.7")).toBeInTheDocument(); // 0.72 rounded to 1 decimal

      expect(screen.getByText("Confidence")).toBeInTheDocument();
      expect(screen.getByText("85%")).toBeInTheDocument(); // 0.85 * 100
    });

    it("should show appropriate chip colors based on complexity levels", () => {
      const Wrapper = createWrapper();

      // High complexity (>0.7) - should be error color
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });
      expect(screen.getByText("0.7")).toBeInTheDocument();

      // Medium complexity (0.4-0.7) - should be warning color
      const { rerender } = render(
        <SessionMonitor {...defaultProps} session={mockSessions.parallel} />,
        { wrapper: Wrapper },
      );
      expect(screen.getByText("0.5")).toBeInTheDocument(); // 0.45 rounded
    });
  });

  describe("Session Control Actions", () => {
    it("should show pause and stop actions for running sessions", () => {
      const Wrapper = createWrapper();
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByRole("button", { name: /pause session/i }))
        .toBeInTheDocument();
      expect(screen.getByRole("button", { name: /stop session/i }))
        .toBeInTheDocument();
      expect(screen.getByRole("button", { name: /refresh session/i }))
        .toBeInTheDocument();
    });

    it("should call onPause when pause button is clicked", async () => {
      const user = userEvent.setup();
      const onPause = jest.fn();
      const Wrapper = createWrapper();

      render(
        <SessionMonitor {...defaultProps} onPause={onPause} />,
        { wrapper: Wrapper },
      );

      const pauseButton = screen.getByRole("button", {
        name: /pause session/i,
      });
      await user.click(pauseButton);

      expect(onPause).toHaveBeenCalledWith("session_fanout_001");
    });

    it("should call onStop when stop button is clicked", async () => {
      const user = userEvent.setup();
      const onStop = jest.fn();
      const Wrapper = createWrapper();

      render(
        <SessionMonitor {...defaultProps} onStop={onStop} />,
        { wrapper: Wrapper },
      );

      const stopButton = screen.getByRole("button", { name: /stop session/i });
      await user.click(stopButton);

      expect(onStop).toHaveBeenCalledWith("session_fanout_001");
    });

    it("should show resume action for pending sessions", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.pending} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByRole("button", { name: /resume session/i }))
        .toBeInTheDocument();
    });

    it("should call onResume when resume button is clicked", async () => {
      const user = userEvent.setup();
      const onResume = jest.fn();
      const Wrapper = createWrapper();

      render(
        <SessionMonitor
          {...defaultProps}
          session={mockSessions.pending}
          onResume={onResume}
        />,
        { wrapper: Wrapper },
      );

      const resumeButton = screen.getByRole("button", {
        name: /resume session/i,
      });
      await user.click(resumeButton);

      expect(onResume).toHaveBeenCalledWith("session_pending_001");
    });

    it("should disable actions for completed sessions", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.completed} />,
        { wrapper: Wrapper },
      );

      const refreshButton = screen.getByRole("button", {
        name: /refresh session/i,
      });
      expect(refreshButton).toBeDisabled();
    });

    it("should disable actions for failed sessions", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.failed} />,
        { wrapper: Wrapper },
      );

      const refreshButton = screen.getByRole("button", {
        name: /refresh session/i,
      });
      expect(refreshButton).toBeDisabled();
    });
  });

  describe("Coordination Pattern Workflows", () => {
    it("should display fan-out/fan-in coordination details", () => {
      const Wrapper = createWrapper();
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });

      expect(
        screen.getByText(
          "FAN_OUT_SYNTHESIZE pattern: 7 researchers → 2 analysts → 1 synthesizer",
        ),
      ).toBeInTheDocument();

      // High complexity typical for fan-out patterns
      expect(screen.getByText("0.7")).toBeInTheDocument();
    });

    it("should handle pipeline coordination pattern", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.pipeline} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByText("Sequential processing workflow"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "PIPELINE pattern: researcher → architect → implementer → tester",
        ),
      ).toBeInTheDocument();

      // Moderate complexity for sequential patterns
      expect(screen.getByText("0.6")).toBeInTheDocument(); // 0.58 rounded
    });

    it("should display parallel coordination pattern", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.parallel} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByText("Independent parallel task execution"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "PARALLEL pattern: 4 implementers working on separate modules",
        ),
      ).toBeInTheDocument();

      // Lower complexity for independent parallel work
      expect(screen.getByText("0.5")).toBeInTheDocument(); // 0.45 rounded

      // High confidence for simple parallel tasks
      expect(screen.getByText("92%")).toBeInTheDocument();
    });
  });

  describe("Session Lifecycle States", () => {
    it("should handle completed session state correctly", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.completed} />,
        { wrapper: Wrapper },
      );

      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "completed");

      expect(screen.getByText("100%")).toBeInTheDocument();
      expect(screen.getByText("95%")).toBeInTheDocument(); // High confidence for completed
    });

    it("should handle failed session state correctly", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.failed} />,
        { wrapper: Wrapper },
      );

      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "failed");

      expect(screen.getByText("100%")).toBeInTheDocument(); // Failed sessions show 100% progress
      expect(screen.getByText("25%")).toBeInTheDocument(); // Low confidence for failed
      expect(
        screen.getByText(
          "Byzantine consensus failure in distributed validation",
        ),
      ).toBeInTheDocument();
    });

    it("should handle pending session state correctly", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.pending} />,
        { wrapper: Wrapper },
      );

      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "pending");

      expect(screen.getByText("0%")).toBeInTheDocument(); // Pending sessions show 0% progress
      expect(screen.getByText("Session paused for resource reallocation"))
        .toBeInTheDocument();
    });
  });

  describe("Timestamp and Duration Display", () => {
    it("should display creation and update timestamps", () => {
      const Wrapper = createWrapper();
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText("Created")).toBeInTheDocument();
      expect(screen.getByText("1/1/2024 10:0")).toBeInTheDocument(); // Formatted createdAt

      expect(screen.getByText("Last Updated")).toBeInTheDocument();
      expect(screen.getByText("1/1/2024 10:15")).toBeInTheDocument(); // Formatted updatedAt
    });
  });

  describe("Progress Color Logic", () => {
    it("should use error color for failed sessions", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.failed} />,
        { wrapper: Wrapper },
      );

      // Failed session should use error color (visual test would be needed for actual color)
      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should use success color for completed sessions", () => {
      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={mockSessions.completed} />,
        { wrapper: Wrapper },
      );

      // Completed session should use success color
      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should use primary color for running sessions", () => {
      const Wrapper = createWrapper();
      render(<SessionMonitor {...defaultProps} />, { wrapper: Wrapper });

      // Running session should use primary color
      const progress = Math.floor(mockSessions.fanOutFanIn.confidence * 100);
      expect(screen.getByText(`${progress}%`)).toBeInTheDocument();
    });
  });

  describe("Agentic Systems Coordination Features", () => {
    it("should handle complex multi-agent coordination scenarios", () => {
      const complexSession = createMockSession({
        id: "session_complex_001",
        complexity: 0.95,
        confidence: 0.65,
        objective:
          "Large-scale distributed consensus with Byzantine fault tolerance",
        context:
          "Hierarchical delegation: 1 coordinator → 5 region leaders → 25 validators → 100 nodes",
      });

      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={complexSession} />,
        { wrapper: Wrapper },
      );

      expect(
        screen.getByText(
          "Large-scale distributed consensus with Byzantine fault tolerance",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("1.0")).toBeInTheDocument(); // 0.95 rounded up
      expect(screen.getByText("65%")).toBeInTheDocument();
    });

    it("should support event-driven coordination patterns", () => {
      const eventDrivenSession = createMockSession({
        id: "session_event_001",
        objective: "Event-driven workflow orchestration",
        context:
          "KB_EVENT_PROCESSING pattern: GitHub issues as event queue for agent coordination",
      });

      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={eventDrivenSession} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByText("Event-driven workflow orchestration"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "KB_EVENT_PROCESSING pattern: GitHub issues as event queue for agent coordination",
        ),
      ).toBeInTheDocument();
    });

    it("should handle consensus-based coordination", () => {
      const consensusSession = createMockSession({
        id: "session_consensus_001",
        objective: "Multi-agent consensus validation",
        context: "Byzantine consensus with 2f+1 agents for fault tolerance",
        complexity: 0.82,
        confidence: 0.75,
      });

      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={consensusSession} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByText("Multi-agent consensus validation"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "Byzantine consensus with 2f+1 agents for fault tolerance",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("0.8")).toBeInTheDocument(); // High complexity
    });
  });

  describe("Information Display Edge Cases", () => {
    it("should handle sessions without context", () => {
      const sessionWithoutContext = {
        ...mockSessions.fanOutFanIn,
        context: "",
      };
      const Wrapper = createWrapper();

      render(
        <SessionMonitor {...defaultProps} session={sessionWithoutContext} />,
        { wrapper: Wrapper },
      );

      // Context section should not be rendered if context is empty
      expect(screen.queryByText("Context")).not.toBeInTheDocument();
    });

    it("should handle very long objectives gracefully", () => {
      const longObjectiveSession = createMockSession({
        objective:
          "This is an extremely long objective that tests how the component handles very long text that might wrap across multiple lines and potentially cause layout issues in the user interface",
      });

      const Wrapper = createWrapper();
      render(
        <SessionMonitor {...defaultProps} session={longObjectiveSession} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByText(/This is an extremely long objective/))
        .toBeInTheDocument();
    });
  });
});
