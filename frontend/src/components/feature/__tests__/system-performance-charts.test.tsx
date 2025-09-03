/**
 * @jest-environment jsdom
 */

import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@mui/material/styles";
import { createTheme } from "@mui/material";
import "@testing-library/jest-dom";

import { SystemPerformanceCharts } from "../system-performance-charts";
import * as hooks from "@/lib/api/hooks";
import type { SystemPerformanceMetrics } from "@/lib/types";

// Mock Recharts to avoid canvas issues in tests
jest.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: any) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  AreaChart: ({ children }: any) => (
    <div data-testid="area-chart">{children}</div>
  ),
  Area: () => <div data-testid="area" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ReferenceLine: () => <div data-testid="reference-line" />,
}));

// Mock the API hooks
jest.mock("@/lib/api/hooks");
const mockUseSystemPerformance = hooks
  .useSystemPerformance as jest.MockedFunction<
    typeof hooks.useSystemPerformance
  >;

// Create test theme
const testTheme = createTheme();

// Test data
const mockSystemPerformance: SystemPerformanceMetrics = {
  cpu: {
    usage: 65.5,
    history: [
      { timestamp: "2024-01-01T10:00:00Z", value: 60.0 },
      { timestamp: "2024-01-01T10:05:00Z", value: 65.5 },
      { timestamp: "2024-01-01T10:10:00Z", value: 62.3 },
    ],
  },
  memory: {
    usage: 72.1,
    total: 8192,
    used: 5904,
    history: [
      { timestamp: "2024-01-01T10:00:00Z", value: 70.0 },
      { timestamp: "2024-01-01T10:05:00Z", value: 72.1 },
      { timestamp: "2024-01-01T10:10:00Z", value: 68.9 },
    ],
  },
  timestamp: "2024-01-01T10:10:00Z",
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

describe("SystemPerformanceCharts", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders without crashing", async () => {
    mockUseSystemPerformance.mockReturnValue({
      data: mockSystemPerformance,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("System Performance")).toBeInTheDocument();
    expect(screen.getByText("Real-time CPU and memory usage monitoring"))
      .toBeInTheDocument();
  });

  it("displays loading state correctly", () => {
    mockUseSystemPerformance.mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("displays error state correctly", () => {
    mockUseSystemPerformance.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error("API Error"),
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("Unable to load performance data"))
      .toBeInTheDocument();
  });

  it("displays current CPU and memory usage", () => {
    mockUseSystemPerformance.mockReturnValue({
      data: mockSystemPerformance,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("65.5%")).toBeInTheDocument(); // CPU usage
    expect(screen.getByText("72.1%")).toBeInTheDocument(); // Memory usage
    expect(screen.getByText("5904MB / 8192MB")).toBeInTheDocument(); // Memory details
  });

  it("renders time range controls", () => {
    mockUseSystemPerformance.mockReturnValue({
      data: mockSystemPerformance,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("1H")).toBeInTheDocument();
    expect(screen.getByText("6H")).toBeInTheDocument();
    expect(screen.getByText("24H")).toBeInTheDocument();
    expect(screen.getByText("7D")).toBeInTheDocument();
  });

  it("allows time range selection", async () => {
    mockUseSystemPerformance.mockReturnValue({
      data: mockSystemPerformance,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    const sixHourButton = screen.getByText("6H");
    fireEvent.click(sixHourButton);

    // The button should be selected (this tests the state change)
    await waitFor(() => {
      expect(sixHourButton).toHaveAttribute("aria-pressed", "true");
    });
  });

  it("displays performance status correctly", () => {
    mockUseSystemPerformance.mockReturnValue({
      data: mockSystemPerformance,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    // Should show "NORMAL" status since CPU (65.5%) and Memory (72.1%) are within normal ranges
    expect(screen.getByText("NORMAL")).toBeInTheDocument();
  });

  it("displays high performance status warning", () => {
    const highUsageData: SystemPerformanceMetrics = {
      ...mockSystemPerformance,
      cpu: { ...mockSystemPerformance.cpu, usage: 85.0 },
      memory: { ...mockSystemPerformance.memory, usage: 90.0 },
    };

    mockUseSystemPerformance.mockReturnValue({
      data: highUsageData,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("85.0%")).toBeInTheDocument(); // High CPU
    expect(screen.getByText("90.0%")).toBeInTheDocument(); // High Memory
  });

  it("renders chart components", () => {
    mockUseSystemPerformance.mockReturnValue({
      data: mockSystemPerformance,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
    expect(screen.getByTestId("area-chart")).toBeInTheDocument();
    expect(screen.getAllByTestId("area")).toHaveLength(2); // CPU and Memory areas
    expect(screen.getByTestId("x-axis")).toBeInTheDocument();
    expect(screen.getByTestId("y-axis")).toBeInTheDocument();
  });

  it("displays data points count", () => {
    mockUseSystemPerformance.mockReturnValue({
      data: mockSystemPerformance,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("Data Points")).toBeInTheDocument();
    expect(screen.getByText("Last 1H")).toBeInTheDocument();
  });

  it("applies custom className when provided", () => {
    mockUseSystemPerformance.mockReturnValue({
      data: mockSystemPerformance,
      isLoading: false,
      error: null,
    } as any);

    const { container } = render(
      <TestWrapper>
        <SystemPerformanceCharts className="custom-class" />
      </TestWrapper>,
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("handles empty history data gracefully", () => {
    const emptyHistoryData: SystemPerformanceMetrics = {
      ...mockSystemPerformance,
      cpu: { usage: 50.0, history: [] },
      memory: { usage: 60.0, total: 8192, used: 4915, history: [] },
    };

    mockUseSystemPerformance.mockReturnValue({
      data: emptyHistoryData,
      isLoading: false,
      error: null,
    } as any);

    render(
      <TestWrapper>
        <SystemPerformanceCharts />
      </TestWrapper>,
    );

    expect(screen.getByText("50.0%")).toBeInTheDocument(); // Current CPU
    expect(screen.getByText("60.0%")).toBeInTheDocument(); // Current Memory
    expect(screen.getByText("0")).toBeInTheDocument(); // 0 data points
  });
});
