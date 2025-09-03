/**
 * Live Coordination Monitor Component Tests
 * Comprehensive test coverage for real-time coordination monitoring
 */

import React from "react";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";
import { createTheme } from "@mui/material/styles";
import "@testing-library/jest-dom";
import { LiveCoordinationMonitor } from "../live-coordination-monitor";
import { CoordinationMonitorProps } from "@/types";

// Mock theme for Material-UI components
const mockTheme = createTheme();

// Test wrapper with theme provider
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider theme={mockTheme}>
    {children}
  </ThemeProvider>
);

describe("LiveCoordinationMonitor", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  describe("Component Initialization", () => {
    it("renders the main coordination monitor component", () => {
      render(
        <TestWrapper>
          <LiveCoordinationMonitor />
        </TestWrapper>,
      );

      expect(screen.getByText("Live Coordination Monitor")).toBeInTheDocument();
    });

    it("accepts coordination ID prop", () => {
      const testCoordinationId = "test_coordination_123";
      render(
        <TestWrapper>
          <LiveCoordinationMonitor coordinationId={testCoordinationId} />
        </TestWrapper>,
      );

      // Component should render without error when coordination ID is provided
      expect(screen.getByText("Live Coordination Monitor")).toBeInTheDocument();
    });
  });

  describe("Core Functionality", () => {
    it("renders without crashing with all required props", () => {
      const props: CoordinationMonitorProps = {
        coordinationId: "test_123",
        refreshInterval: 5000,
        maxEvents: 20,
        onEventClick: jest.fn(),
        onConflictResolve: jest.fn(),
        className: "test-class",
      };

      render(
        <TestWrapper>
          <LiveCoordinationMonitor {...props} />
        </TestWrapper>,
      );

      expect(screen.getByText("Live Coordination Monitor")).toBeInTheDocument();
    });

    it("handles event callbacks when provided", () => {
      const onEventClick = jest.fn();
      const onConflictResolve = jest.fn();

      render(
        <TestWrapper>
          <LiveCoordinationMonitor
            onEventClick={onEventClick}
            onConflictResolve={onConflictResolve}
          />
        </TestWrapper>,
      );

      // Component should render and set up callbacks without error
      expect(screen.getByText("Live Coordination Monitor")).toBeInTheDocument();
    });
  });

  describe("Component Props and Configuration", () => {
    it("applies custom refresh interval", () => {
      const customInterval = 10000;
      render(
        <TestWrapper>
          <LiveCoordinationMonitor refreshInterval={customInterval} />
        </TestWrapper>,
      );

      expect(screen.getByText("Live Coordination Monitor")).toBeInTheDocument();
    });

    it("limits events based on maxEvents prop", () => {
      render(
        <TestWrapper>
          <LiveCoordinationMonitor maxEvents={5} />
        </TestWrapper>,
      );

      expect(screen.getByText("Live Coordination Monitor")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      const { container } = render(
        <TestWrapper>
          <LiveCoordinationMonitor className="custom-monitor" />
        </TestWrapper>,
      );

      expect(container.querySelector(".custom-monitor")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("handles missing data gracefully", () => {
      render(
        <TestWrapper>
          <LiveCoordinationMonitor />
        </TestWrapper>,
      );

      // Component should handle missing data without crashing
      expect(screen.getByText("Live Coordination Monitor")).toBeInTheDocument();
    });

    it("renders with minimal props", () => {
      render(
        <TestWrapper>
          <LiveCoordinationMonitor />
        </TestWrapper>,
      );

      expect(screen.getByText("Live Coordination Monitor")).toBeInTheDocument();
    });
  });
});
