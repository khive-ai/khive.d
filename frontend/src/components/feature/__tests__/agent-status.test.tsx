/**
 * AgentStatus Component Tests
 * Comprehensive test suite for agent lifecycle management and coordination patterns
 * Focuses on multi-agent system behaviors and status monitoring
 */

import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { AgentStatus, AgentStatusProps } from "../agent-status";
import { Agent } from "@/types";

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
  formatDuration: (ms: number) => {
    const minutes = Math.floor(ms / 60000);
    return `${minutes}m`;
  },
  capitalize: (str: string) => str.charAt(0).toUpperCase() + str.slice(1),
  camelCaseToReadable: (str: string) => str.replace(/([A-Z])/g, " $1").trim(),
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

// Mock agent data for different coordination scenarios
const createMockAgent = (overrides: Partial<Agent> = {}): Agent => ({
  id: "agent_001",
  role: "researcher",
  domain: "memory-systems",
  status: "active",
  currentTask: "Analyzing distributed memory patterns",
  duration: 900000, // 15 minutes
  sessionId: "session_001",
  ...overrides,
});

// Test agents for different coordination patterns
const mockAgents = {
  // Fan-out pattern agents
  researcher: createMockAgent({
    id: "researcher_001",
    role: "researcher",
    domain: "memory-systems",
    status: "active",
    currentTask: "Research phase: Discovering memory architecture patterns",
    duration: 600000, // 10 minutes
  }),
  analyst: createMockAgent({
    id: "analyst_001",
    role: "analyst",
    domain: "agentic-systems",
    status: "active",
    currentTask: "Analysis phase: Synthesizing research findings",
    duration: 300000, // 5 minutes
  }),
  critic: createMockAgent({
    id: "critic_001",
    role: "critic",
    domain: "software-architecture",
    status: "idle",
    currentTask: undefined,
    duration: 0,
  }),

  // Parallel pattern agents
  implementer1: createMockAgent({
    id: "implementer_001",
    role: "implementer",
    domain: "distributed-systems",
    status: "active",
    currentTask: "Parallel implementation: Database layer",
    duration: 1200000, // 20 minutes
  }),
  implementer2: createMockAgent({
    id: "implementer_002",
    role: "implementer",
    domain: "microkernel-architecture",
    status: "active",
    currentTask: "Parallel implementation: Service layer",
    duration: 900000, // 15 minutes
  }),

  // Error recovery agent
  errorAgent: createMockAgent({
    id: "recovery_001",
    role: "tester",
    domain: "rust-performance",
    status: "error",
    currentTask: "Failed: Coordination conflict resolution",
    duration: 120000, // 2 minutes
  }),
};

describe("AgentStatus Component", () => {
  const defaultProps: AgentStatusProps = {
    agent: mockAgents.researcher,
    onStop: jest.fn(),
    onRestart: jest.fn(),
    onViewDetails: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("Agent Information Display", () => {
    it("should render agent role and domain correctly", () => {
      const Wrapper = createWrapper();
      render(<AgentStatus {...defaultProps} />, { wrapper: Wrapper });

      // Check role display (should be readable format)
      expect(screen.getByText("researcher")).toBeInTheDocument();

      // Check domain display
      expect(screen.getByText("memory-systems")).toBeInTheDocument();

      // Check agent ID (last 8 characters)
      expect(screen.getByText("her_001")).toBeInTheDocument(); // Last 8 chars of researcher_001
    });

    it("should display avatar with role-based color generation", () => {
      const Wrapper = createWrapper();
      render(<AgentStatus {...defaultProps} />, { wrapper: Wrapper });

      // Avatar should show first letter of role
      const avatar = screen.getByText("R"); // First letter of 'researcher'
      expect(avatar).toBeInTheDocument();
    });

    it("should show status badge with correct status", () => {
      const Wrapper = createWrapper();
      render(<AgentStatus {...defaultProps} />, { wrapper: Wrapper });

      const statusBadge = screen.getByTestId("status-badge");
      expect(statusBadge).toHaveAttribute("data-status", "active");
    });
  });

  describe("Agent Lifecycle Management", () => {
    it("should display current task for active agents", () => {
      const Wrapper = createWrapper();
      render(<AgentStatus {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText("Current Task")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Research phase: Discovering memory architecture patterns",
        ),
      ).toBeInTheDocument();
    });

    it("should show progress bar for active agents with tasks", () => {
      const Wrapper = createWrapper();
      render(<AgentStatus {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText("Progress")).toBeInTheDocument();

      // Progress should be calculated based on duration
      const progressText = screen.getByText(/\d+%/);
      expect(progressText).toBeInTheDocument();
    });

    it("should display duration information", () => {
      const Wrapper = createWrapper();
      render(<AgentStatus {...defaultProps} />, { wrapper: Wrapper });

      expect(screen.getByText("Active: 10m")).toBeInTheDocument();
    });

    it("should show session ID reference", () => {
      const Wrapper = createWrapper();
      render(<AgentStatus {...defaultProps} />, { wrapper: Wrapper });

      // Should show last 6 characters of session ID
      expect(screen.getByText("Session: on_001")).toBeInTheDocument();
    });
  });

  describe("Agent State Management Actions", () => {
    it("should show stop action for active agents", () => {
      const Wrapper = createWrapper();
      render(<AgentStatus {...defaultProps} />, { wrapper: Wrapper });

      const stopButton = screen.getByRole("button", { name: /stop agent/i });
      expect(stopButton).toBeInTheDocument();
    });

    it("should call onStop when stop button is clicked", async () => {
      const user = userEvent.setup();
      const onStop = jest.fn();
      const Wrapper = createWrapper();

      render(
        <AgentStatus {...defaultProps} onStop={onStop} />,
        { wrapper: Wrapper },
      );

      const stopButton = screen.getByRole("button", { name: /stop agent/i });
      await user.click(stopButton);

      expect(onStop).toHaveBeenCalledWith("researcher_001");
    });

    it("should show restart action for idle agents", () => {
      const idleAgent = mockAgents.critic;
      const Wrapper = createWrapper();

      render(
        <AgentStatus {...defaultProps} agent={idleAgent} />,
        { wrapper: Wrapper },
      );

      const restartButton = screen.getByRole("button", {
        name: /restart agent/i,
      });
      expect(restartButton).toBeInTheDocument();
    });

    it("should call onRestart when restart button is clicked", async () => {
      const user = userEvent.setup();
      const onRestart = jest.fn();
      const idleAgent = mockAgents.critic;
      const Wrapper = createWrapper();

      render(
        <AgentStatus
          {...defaultProps}
          agent={idleAgent}
          onRestart={onRestart}
        />,
        { wrapper: Wrapper },
      );

      const restartButton = screen.getByRole("button", {
        name: /restart agent/i,
      });
      await user.click(restartButton);

      expect(onRestart).toHaveBeenCalledWith("critic_001");
    });

    it("should call onViewDetails when info button is clicked", async () => {
      const user = userEvent.setup();
      const onViewDetails = jest.fn();
      const Wrapper = createWrapper();

      render(
        <AgentStatus {...defaultProps} onViewDetails={onViewDetails} />,
        { wrapper: Wrapper },
      );

      const infoButton = screen.getByRole("button", { name: /view details/i });
      await user.click(infoButton);

      expect(onViewDetails).toHaveBeenCalledWith("researcher_001");
    });
  });

  describe("Multi-Agent Coordination Patterns", () => {
    it("should handle fan-out coordination agents correctly", () => {
      const Wrapper = createWrapper();
      const { rerender } = render(
        <AgentStatus {...defaultProps} agent={mockAgents.researcher} />,
        { wrapper: Wrapper },
      );

      // Researcher should show active status with current task
      expect(screen.getByText("researcher")).toBeInTheDocument();
      expect(screen.getByTestId("status-badge")).toHaveAttribute(
        "data-status",
        "active",
      );

      // Rerender with analyst agent
      rerender(
        <AgentStatus {...defaultProps} agent={mockAgents.analyst} />,
      );

      expect(screen.getByText("analyst")).toBeInTheDocument();
      expect(screen.getByText("agentic-systems")).toBeInTheDocument();
      expect(screen.getByText("Analysis phase: Synthesizing research findings"))
        .toBeInTheDocument();
    });

    it("should display parallel implementation agents", () => {
      const Wrapper = createWrapper();
      const { rerender } = render(
        <AgentStatus {...defaultProps} agent={mockAgents.implementer1} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByText("implementer")).toBeInTheDocument();
      expect(screen.getByText("distributed-systems")).toBeInTheDocument();
      expect(screen.getByText("Parallel implementation: Database layer"))
        .toBeInTheDocument();

      // Check second parallel implementer
      rerender(
        <AgentStatus {...defaultProps} agent={mockAgents.implementer2} />,
      );

      expect(screen.getByText("microkernel-architecture")).toBeInTheDocument();
      expect(screen.getByText("Parallel implementation: Service layer"))
        .toBeInTheDocument();
    });
  });

  describe("Error States and Recovery", () => {
    it("should display error state for failed agents", () => {
      const Wrapper = createWrapper();
      render(
        <AgentStatus {...defaultProps} agent={mockAgents.errorAgent} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByTestId("status-badge")).toHaveAttribute(
        "data-status",
        "error",
      );
      expect(screen.getByText("Failed: Coordination conflict resolution"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "⚠️ Agent encountered an error and requires attention",
        ),
      ).toBeInTheDocument();
    });

    it("should show restart action for error state agents", () => {
      const Wrapper = createWrapper();
      render(
        <AgentStatus {...defaultProps} agent={mockAgents.errorAgent} />,
        { wrapper: Wrapper },
      );

      const restartButton = screen.getByRole("button", {
        name: /restart agent/i,
      });
      expect(restartButton).toBeInTheDocument();
    });

    it("should display idle state notification", () => {
      const Wrapper = createWrapper();
      render(
        <AgentStatus {...defaultProps} agent={mockAgents.critic} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByText("💤 Agent is idle and waiting for tasks"))
        .toBeInTheDocument();
    });
  });

  describe("Status Icon Mapping", () => {
    it("should display correct status icons for different states", () => {
      const Wrapper = createWrapper();

      // Test active agent
      const { rerender } = render(
        <AgentStatus {...defaultProps} agent={mockAgents.researcher} />,
        { wrapper: Wrapper },
      );
      expect(screen.getByText("🟢")).toBeInTheDocument();
      expect(screen.getByText("Active")).toBeInTheDocument();

      // Test idle agent
      rerender(<AgentStatus {...defaultProps} agent={mockAgents.critic} />);
      expect(screen.getByText("🟡")).toBeInTheDocument();
      expect(screen.getByText("Idle")).toBeInTheDocument();

      // Test error agent
      rerender(<AgentStatus {...defaultProps} agent={mockAgents.errorAgent} />);
      expect(screen.getByText("🔴")).toBeInTheDocument();
      expect(screen.getByText("Error")).toBeInTheDocument();
    });
  });

  describe("Progress Calculation", () => {
    it("should calculate progress based on agent duration", () => {
      const Wrapper = createWrapper();

      // Agent with 10 minute duration should show progress
      render(<AgentStatus {...defaultProps} agent={mockAgents.researcher} />, {
        wrapper: Wrapper,
      });

      // Progress calculation: (600000 / 60000) * 10 = 100, but capped at 90
      expect(screen.getByText("90%")).toBeInTheDocument();
    });

    it("should handle agents without current tasks", () => {
      const agentWithoutTask = {
        ...mockAgents.researcher,
        currentTask: undefined,
      };
      const Wrapper = createWrapper();

      render(<AgentStatus {...defaultProps} agent={agentWithoutTask} />, {
        wrapper: Wrapper,
      });

      // Should not show progress section
      expect(screen.queryByText("Progress")).not.toBeInTheDocument();
    });
  });

  describe("Agentic Systems Domain Expertise", () => {
    it("should properly display domain-specific agent information", () => {
      const Wrapper = createWrapper();

      // Test memory-systems domain
      const { rerender } = render(
        <AgentStatus {...defaultProps} agent={mockAgents.researcher} />,
        { wrapper: Wrapper },
      );
      expect(screen.getByText("memory-systems")).toBeInTheDocument();

      // Test agentic-systems domain
      rerender(<AgentStatus {...defaultProps} agent={mockAgents.analyst} />);
      expect(screen.getByText("agentic-systems")).toBeInTheDocument();

      // Test distributed-systems domain
      rerender(
        <AgentStatus {...defaultProps} agent={mockAgents.implementer1} />,
      );
      expect(screen.getByText("distributed-systems")).toBeInTheDocument();
    });

    it("should handle coordination-aware task descriptions", () => {
      const Wrapper = createWrapper();
      render(<AgentStatus {...defaultProps} agent={mockAgents.analyst} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByText("Analysis phase: Synthesizing research findings"))
        .toBeInTheDocument();
    });

    it("should support different orchestration roles", () => {
      const orchestrationAgents = [
        mockAgents.researcher, // Discovery role
        mockAgents.analyst, // Synthesis role
        mockAgents.critic, // Validation role
        mockAgents.implementer1, // Execution role
      ];

      const Wrapper = createWrapper();

      orchestrationAgents.forEach((agent) => {
        const { rerender } = render(
          <AgentStatus {...defaultProps} agent={agent} />,
          { wrapper: Wrapper },
        );

        expect(screen.getByText(agent.role)).toBeInTheDocument();
        expect(screen.getByText(agent.domain)).toBeInTheDocument();

        // Each should have appropriate actions based on status
        if (agent.status === "active") {
          expect(screen.getByRole("button", { name: /stop agent/i }))
            .toBeInTheDocument();
        } else if (agent.status === "idle" || agent.status === "error") {
          expect(screen.getByRole("button", { name: /restart agent/i }))
            .toBeInTheDocument();
        }
      });
    });
  });
});
