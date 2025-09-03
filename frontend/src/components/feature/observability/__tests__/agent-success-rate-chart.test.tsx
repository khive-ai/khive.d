/**
 * Test suite for AgentSuccessRateChart component
 * Validates MVP functionality for agent success/failure rate tracking
 */

import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import "@testing-library/jest-dom";
import { AgentSuccessRateChart } from "../agent-success-rate-chart";
import { AgentPerformanceMetrics } from "@/lib/types/system-metrics";

// Mock data for testing
const mockAgentMetrics: AgentPerformanceMetrics[] = [
  {
    agentId: "agent-001",
    role: "implementer",
    domain: "agentic-systems",
    totalTasks: 50,
    successfulTasks: 45,
    failedTasks: 5,
    successRate: 90.0,
    averageTaskDuration: 3000,
    errorRate: 10.0,
    lastActivity: "2025-01-15T10:30:00Z",
    taskHistory: [],
  },
  {
    agentId: "agent-002",
    role: "tester",
    domain: "software-architecture",
    totalTasks: 30,
    successfulTasks: 25,
    failedTasks: 5,
    successRate: 83.3,
    averageTaskDuration: 2500,
    errorRate: 16.7,
    lastActivity: "2025-01-15T10:25:00Z",
    taskHistory: [],
  },
  {
    agentId: "agent-003",
    role: "researcher",
    domain: "memory-systems",
    totalTasks: 20,
    successfulTasks: 18,
    failedTasks: 2,
    successRate: 90.0,
    averageTaskDuration: 4000,
    errorRate: 10.0,
    lastActivity: "2025-01-15T10:20:00Z",
    taskHistory: [],
  },
];

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>,
  );
};

describe("AgentSuccessRateChart", () => {
  describe("Component Rendering", () => {
    it("renders successfully with agent metrics", () => {
      renderWithTheme(
        <AgentSuccessRateChart agentMetrics={mockAgentMetrics} />,
      );

      expect(screen.getByText("Agent Success & Performance Metrics"))
        .toBeInTheDocument();
      expect(
        screen.getByText(
          "Real-time tracking of agent task completion and success rates",
        ),
      ).toBeInTheDocument();
    });

    it("displays loading state when isLoading is true", () => {
      renderWithTheme(
        <AgentSuccessRateChart agentMetrics={[]} isLoading={true} />,
      );

      expect(screen.getByText("Loading agent performance metrics..."))
        .toBeInTheDocument();
      expect(screen.getByRole("progressbar")).toBeInTheDocument();
    });

    it("displays empty state when no agent metrics provided", () => {
      renderWithTheme(<AgentSuccessRateChart agentMetrics={[]} />);

      expect(screen.getByText("No Agent Performance Data")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Agent success/failure metrics will appear once agents start executing tasks",
        ),
      ).toBeInTheDocument();
    });
  });

  describe("Aggregate Metrics", () => {
    it("calculates and displays correct aggregate metrics", () => {
      renderWithTheme(
        <AgentSuccessRateChart agentMetrics={mockAgentMetrics} />,
      );

      // Check total agents count
      expect(screen.getByText("3")).toBeInTheDocument(); // Total agents
      expect(screen.getByText("Active Agents")).toBeInTheDocument();

      // Check total tasks
      expect(screen.getByText("100")).toBeInTheDocument(); // 50 + 30 + 20 = 100
      expect(screen.getByText("Total Tasks")).toBeInTheDocument();

      // Check average success rate (should be calculated correctly)
      const avgSuccessRate = (90.0 + 83.3 + 90.0) / 3;
      expect(screen.getByText(`${avgSuccessRate.toFixed(1)}%`))
        .toBeInTheDocument();
    });
  });

  describe("View Mode Controls", () => {
    it("switches between different view modes", async () => {
      renderWithTheme(
        <AgentSuccessRateChart agentMetrics={mockAgentMetrics} />,
      );

      // Check default overview mode
      expect(screen.getByText("Overall Task Success Distribution"))
        .toBeInTheDocument();

      // Switch to individual view
      const individualButton = screen.getByRole("button", {
        name: /individual/i,
      });
      fireEvent.click(individualButton);

      await waitFor(() => {
        expect(screen.getByText("implementer")).toBeInTheDocument();
        expect(screen.getByText("tester")).toBeInTheDocument();
        expect(screen.getByText("researcher")).toBeInTheDocument();
      });

      // Switch to comparison view
      const comparisonButton = screen.getByRole("button", { name: /compare/i });
      fireEvent.click(comparisonButton);

      await waitFor(() => {
        // Should still show individual agent cards in comparison mode
        expect(screen.getByText("implementer")).toBeInTheDocument();
        expect(screen.getByText("#1")).toBeInTheDocument(); // Ranking chip
      });
    });
  });

  describe("Agent Performance Cards", () => {
    it("displays agent cards with correct information in individual view", async () => {
      renderWithTheme(
        <AgentSuccessRateChart agentMetrics={mockAgentMetrics} />,
      );

      // Switch to individual view to see agent cards
      const individualButton = screen.getByRole("button", {
        name: /individual/i,
      });
      fireEvent.click(individualButton);

      await waitFor(() => {
        // Check that agent information is displayed
        expect(screen.getByText("implementer")).toBeInTheDocument();
        expect(screen.getByText("agentic-systems")).toBeInTheDocument();
        expect(screen.getByText("90.0%")).toBeInTheDocument(); // Success rate
        expect(screen.getByText("50")).toBeInTheDocument(); // Total tasks
      });
    });
  });

  describe("Performance Status Classification", () => {
    it("correctly classifies agent performance levels", async () => {
      const highPerformanceAgent: AgentPerformanceMetrics = {
        agentId: "high-perf",
        role: "excellent-agent",
        domain: "test-domain",
        totalTasks: 10,
        successfulTasks: 10,
        failedTasks: 0,
        successRate: 100.0, // Excellent performance
        averageTaskDuration: 1000,
        errorRate: 0.0,
        lastActivity: "2025-01-15T10:30:00Z",
        taskHistory: [],
      };

      const lowPerformanceAgent: AgentPerformanceMetrics = {
        agentId: "low-perf",
        role: "struggling-agent",
        domain: "test-domain",
        totalTasks: 10,
        successfulTasks: 5,
        failedTasks: 5,
        successRate: 50.0, // Poor performance
        averageTaskDuration: 5000,
        errorRate: 50.0,
        lastActivity: "2025-01-15T10:30:00Z",
        taskHistory: [],
      };

      renderWithTheme(
        <AgentSuccessRateChart
          agentMetrics={[highPerformanceAgent, lowPerformanceAgent]}
        />,
      );

      const individualButton = screen.getByRole("button", {
        name: /individual/i,
      });
      fireEvent.click(individualButton);

      await waitFor(() => {
        expect(screen.getByText("100.0%")).toBeInTheDocument();
        expect(screen.getByText("50.0%")).toBeInTheDocument();
      });
    });
  });

  describe("Chart Integration", () => {
    it("renders success/failure distribution pie chart", () => {
      renderWithTheme(
        <AgentSuccessRateChart agentMetrics={mockAgentMetrics} />,
      );

      expect(screen.getByText("Overall Task Success Distribution"))
        .toBeInTheDocument();
      expect(screen.getByText("Agent Success Rate Comparison"))
        .toBeInTheDocument();
    });
  });

  describe("Performance Insights", () => {
    it("displays performance insights section", () => {
      renderWithTheme(
        <AgentSuccessRateChart agentMetrics={mockAgentMetrics} />,
      );

      expect(screen.getByText("Performance Insights")).toBeInTheDocument();
      expect(screen.getByText(/System Performance:/)).toBeInTheDocument();
      expect(screen.getByText(/Best Performer:/)).toBeInTheDocument();
      expect(screen.getByText(/Avg Task Duration:/)).toBeInTheDocument();
    });
  });

  describe("Real-time Features", () => {
    it("accepts refresh rate prop and displays it correctly", () => {
      renderWithTheme(
        <AgentSuccessRateChart
          agentMetrics={mockAgentMetrics}
          refreshRate={5000}
        />,
      );

      // Component should render without errors with custom refresh rate
      expect(screen.getByText("Agent Success & Performance Metrics"))
        .toBeInTheDocument();
    });
  });
});

describe("AgentSuccessRateChart Edge Cases", () => {
  it("handles agents with zero tasks gracefully", () => {
    const agentWithNoTasks: AgentPerformanceMetrics = {
      agentId: "no-tasks",
      role: "idle-agent",
      domain: "test",
      totalTasks: 0,
      successfulTasks: 0,
      failedTasks: 0,
      successRate: 0,
      averageTaskDuration: 0,
      errorRate: 0,
      lastActivity: "2025-01-15T10:30:00Z",
      taskHistory: [],
    };

    renderWithTheme(
      <AgentSuccessRateChart agentMetrics={[agentWithNoTasks]} />,
    );

    expect(screen.getByText("Agent Success & Performance Metrics"))
      .toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument(); // Still shows 1 agent
    expect(screen.getByText("0")).toBeInTheDocument(); // Total tasks shows 0
  });

  it("handles very high task counts correctly", () => {
    const highVolumeAgent: AgentPerformanceMetrics = {
      agentId: "high-volume",
      role: "workhorse",
      domain: "high-volume",
      totalTasks: 10000,
      successfulTasks: 9500,
      failedTasks: 500,
      successRate: 95.0,
      averageTaskDuration: 500,
      errorRate: 5.0,
      lastActivity: "2025-01-15T10:30:00Z",
      taskHistory: [],
    };

    renderWithTheme(<AgentSuccessRateChart agentMetrics={[highVolumeAgent]} />);

    // Should handle large numbers properly
    expect(screen.getByText("10000")).toBeInTheDocument();
    expect(screen.getByText("95.0%")).toBeInTheDocument();
  });
});
