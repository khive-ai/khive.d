/**
 * @jest-environment jsdom
 */

import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@mui/material/styles";
import { createTheme } from "@mui/material";
import "@testing-library/jest-dom";

import { AgentAnalyticsCharts } from "../agent-analytics-charts";
import * as hooks from "@/lib/api/hooks";
import type { AgentAnalytics } from "@/lib/types";

// Mock Recharts to avoid canvas issues in tests
jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ children }: any) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div data-testid="bar" />,
  PieChart: ({ children }: any) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div data-testid="cell" />,
  AreaChart: ({ children }: any) => (
    <div data-testid="area-chart">{children}</div>
  ),
  Area: () => <div data-testid="area" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
}));

// Mock the API hooks
jest.mock("@/lib/api/hooks");
const mockUseAgentAnalytics = hooks.useAgentAnalytics as jest.MockedFunction<
  typeof hooks.useAgentAnalytics
>;

// Create test theme
const testTheme = createTheme();

// Test data
const mockAgentAnalytics: AgentAnalytics = {
  successRate: 87.5,
  totalTasks: 1000,
  completedTasks: 875,
  failedTasks: 125,
  performanceByRole: [
    {
      role: "researcher",
      successRate: 92.0,
      totalTasks: 300,
      averageCompletionTime: 45.2,
    },
    {
      role: "implementer",
      successRate: 85.0,
      totalTasks: 250,
      averageCompletionTime: 62.8,
    },
    {
      role: "tester",
      successRate: 88.5,
      totalTasks: 200,
      averageCompletionTime: 38.5,
    },
  ],
  performanceByDomain: [
    {
      domain: "agentic-systems",
      successRate: 90.0,
      totalTasks: 400,
      averageCompletionTime: 52.1,
    },
    {
      domain: "distributed-systems",
      successRate: 85.5,
      totalTasks: 300,
      averageCompletionTime: 58.3,
    },
  ],
  recentActivity: [
    {
      timestamp: "2024-01-01T10:00:00Z",
      successful: 12,
      failed: 2,
    },
    {
      timestamp: "2024-01-01T11:00:00Z",
      successful: 15,
      failed: 3,
    },
    {
      timestamp: "2024-01-01T12:00:00Z",
      successful: 18,
      failed: 1,
    },
  ],
};

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: Infinity,
      },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={testTheme}>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe("AgentAnalyticsCharts", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders without crashing", async () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("Agent Performance Analytics")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Success rates, task completion metrics, and agent effectiveness analysis",
      ),
    ).toBeInTheDocument();
  });

  it("displays loading state correctly", () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("displays error state correctly", () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error("API Error"),
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("Unable to load agent analytics data"))
      .toBeInTheDocument();
  });

  it("displays key metrics correctly", () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("88%")).toBeInTheDocument(); // Success rate (rounded)
    expect(screen.getByText("1,000")).toBeInTheDocument(); // Total tasks
    expect(screen.getByText("875")).toBeInTheDocument(); // Completed tasks
    expect(screen.getByText("125")).toBeInTheDocument(); // Failed tasks
  });

  it("renders tab navigation", () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("By Role")).toBeInTheDocument();
    expect(screen.getByText("By Domain")).toBeInTheDocument();
    expect(screen.getByText("Activity")).toBeInTheDocument();
  });

  it("allows tab switching", async () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    // Click on "By Role" tab
    const roleTab = screen.getByText("By Role");
    fireEvent.click(roleTab);

    await waitFor(() => {
      expect(screen.getByText("Performance by Role")).toBeInTheDocument();
    });
  });

  it("displays role performance data in roles tab", async () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    // Switch to roles tab
    fireEvent.click(screen.getByText("By Role"));

    await waitFor(() => {
      expect(screen.getByText("Performance by Role")).toBeInTheDocument();
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    });
  });

  it("displays domain performance data in domains tab", async () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    // Switch to domains tab
    fireEvent.click(screen.getByText("By Domain"));

    await waitFor(() => {
      expect(screen.getByText("Performance by Domain")).toBeInTheDocument();
      expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
    });
  });

  it("displays activity timeline in activity tab", async () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    // Switch to activity tab
    fireEvent.click(screen.getByText("Activity"));

    await waitFor(() => {
      expect(screen.getByText("Recent Activity Timeline")).toBeInTheDocument();
      expect(screen.getByTestId("area-chart")).toBeInTheDocument();
    });
  });

  it("renders overview charts correctly", () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    // Should show pie chart and performance summary in overview
    expect(screen.getByText("Task Distribution")).toBeInTheDocument();
    expect(screen.getByText("Performance Summary")).toBeInTheDocument();
    expect(screen.getByTestId("pie-chart")).toBeInTheDocument();
  });

  it("displays top performing roles in overview", () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("Top Performing Roles")).toBeInTheDocument();
    expect(screen.getByText("1. researcher")).toBeInTheDocument();
    expect(screen.getByText("2. tester")).toBeInTheDocument();
    expect(screen.getByText("3. implementer")).toBeInTheDocument();
  });

  it("shows success rate progress bar", () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("Overall Success Rate")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("applies custom className when provided", () => {
    mockUseAgentAnalytics.mockReturnValue({
      data: mockAgentAnalytics,
      isLoading: false,
      error: null,
    } as any);

    const { container } = render(
      <TestWrapper>
        <AgentAnalyticsCharts className="custom-class" />
      </TestWrapper>,
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("handles empty analytics data gracefully", () => {
    const emptyAnalytics: AgentAnalytics = {
      successRate: 0,
      totalTasks: 0,
      completedTasks: 0,
      failedTasks: 0,
      performanceByRole: [],
      performanceByDomain: [],
      recentActivity: [],
    };

    mockUseAgentAnalytics.mockReturnValue({
      data: emptyAnalytics,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <AgentAnalyticsCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("0%")).toBeInTheDocument(); // Success rate
    expect(screen.getByText("0")).toBeInTheDocument(); // Total tasks
  });
});
