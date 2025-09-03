/**
 * Task Flow Visualizer Tests
 * Unit tests for the interactive workflow diagram components
 */

import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { TaskFlowVisualizer } from "../task-flow-visualizer";
import { Agent, HookEvent, Plan } from "@/lib/types";

// Mock ReactFlow to avoid canvas rendering issues in tests
jest.mock("reactflow", () => ({
  ReactFlow: ({ children, onNodeClick }: any) => (
    <div data-testid="react-flow">
      {children}
      <div
        data-testid="mock-node"
        onClick={() =>
          onNodeClick?.(null, {
            id: "test-node",
            data: { phase: "Test Phase" },
          })}
      >
        Mock Node
      </div>
    </div>
  ),
  Background: () => <div data-testid="flow-background" />,
  Controls: () => <div data-testid="flow-controls" />,
  MiniMap: () => <div data-testid="flow-minimap" />,
  Panel: ({ children }: any) => <div data-testid="flow-panel">{children}</div>,
  useNodesState: () => [[], jest.fn(), jest.fn()],
  useEdgesState: () => [[], jest.fn(), jest.fn()],
  ConnectionMode: { Strict: "strict" },
  MarkerType: { ArrowClosed: "arrowclosed" },
  Position: { Top: "top", Bottom: "bottom", Left: "left", Right: "right" },
  Handle: () => <div data-testid="node-handle" />,
}));

// Mock the individual node components
jest.mock("../task-flow-visualizer/workflow-node", () => ({
  WorkflowNode: () => <div data-testid="workflow-node">Workflow Node</div>,
}));

jest.mock("../task-flow-visualizer/agent-node", () => ({
  AgentNode: () => <div data-testid="agent-node">Agent Node</div>,
}));

jest.mock("../task-flow-visualizer/task-node", () => ({
  TaskNode: () => <div data-testid="task-node">Task Node</div>,
}));

// Mock data
const mockPlan: Plan = {
  id: "test-plan",
  sessionId: "test-session",
  nodes: [
    {
      id: "phase-1",
      phase: "Research Phase",
      status: "completed",
      agents: ["researcher-001"],
      tasks: ["Market research", "User interviews"],
      coordinationStrategy: "FAN_OUT_SYNTHESIZE",
      expectedArtifacts: ["research_report.md"],
      dependencies: [],
    },
    {
      id: "phase-2",
      phase: "Development Phase",
      status: "running",
      agents: ["implementer-001"],
      tasks: ["Build MVP", "Write tests"],
      coordinationStrategy: "PIPELINE",
      expectedArtifacts: ["mvp_code", "test_suite"],
      dependencies: ["phase-1"],
    },
  ],
  edges: [
    { from: "phase-1", to: "phase-2" },
  ],
};

const mockAgents: Agent[] = [
  {
    id: "researcher-001",
    role: "researcher",
    domain: "market-analysis",
    status: "active",
    currentTask: "Market research",
    duration: 1800000,
    sessionId: "test-session",
  },
  {
    id: "implementer-001",
    role: "implementer",
    domain: "frontend-development",
    status: "active",
    currentTask: "Build MVP",
    duration: 3600000,
    sessionId: "test-session",
  },
];

const mockEvents: HookEvent[] = [
  {
    id: "event-001",
    coordinationId: "test-plan",
    agentId: "researcher-001",
    eventType: "post_edit",
    timestamp: new Date(Date.now() - 120000).toISOString(),
    metadata: { operation: "create" },
    filePath: "/workspace/research/report.md",
  },
];

describe("TaskFlowVisualizer", () => {
  beforeEach(() => {
    // Clear any previous mocks
    jest.clearAllMocks();
  });

  it("renders without crashing", () => {
    render(<TaskFlowVisualizer />);
    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
  });

  it("displays ReactFlow components when enabled", () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
        showControls={true}
        showMiniMap={true}
      />,
    );

    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    expect(screen.getByTestId("flow-controls")).toBeInTheDocument();
    expect(screen.getByTestId("flow-minimap")).toBeInTheDocument();
    expect(screen.getByTestId("flow-background")).toBeInTheDocument();
  });

  it("hides optional components when disabled", () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
        showControls={false}
        showMiniMap={false}
      />,
    );

    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    expect(screen.queryByTestId("flow-controls")).not.toBeInTheDocument();
    expect(screen.queryByTestId("flow-minimap")).not.toBeInTheDocument();
  });

  it("displays control panel with correct information", () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
      />,
    );

    expect(screen.getByText("Task Flow")).toBeInTheDocument();
    expect(screen.getByText("2 phases")).toBeInTheDocument();
    expect(screen.getByText("Show Agent Activity")).toBeInTheDocument();
  });

  it("displays status panel with system metrics", () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
      />,
    );

    expect(screen.getByText("System Status")).toBeInTheDocument();
    expect(screen.getByText("Live Updates")).toBeInTheDocument();
  });

  it("handles node click events", () => {
    const mockOnNodeClick = jest.fn();

    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
        onNodeClick={mockOnNodeClick}
      />,
    );

    const mockNode = screen.getByTestId("mock-node");
    fireEvent.click(mockNode);

    expect(mockOnNodeClick).toHaveBeenCalledWith("test-node", {
      phase: "Test Phase",
    });
  });

  it("handles node selection events", () => {
    const mockOnNodeSelect = jest.fn();

    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
        onNodeSelect={mockOnNodeSelect}
      />,
    );

    const mockNode = screen.getByTestId("mock-node");
    fireEvent.click(mockNode);

    // Node selection should be triggered
    expect(mockOnNodeSelect).toHaveBeenCalled();
  });

  it("toggles agent activity display", () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
      />,
    );

    const activityToggle = screen.getByRole("checkbox", {
      name: /show agent activity/i,
    });
    expect(activityToggle).toBeChecked();

    fireEvent.click(activityToggle);
    expect(activityToggle).not.toBeChecked();
  });

  it("switches layout direction", () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
      />,
    );

    const layoutButton = screen.getByRole("button", { name: /vertical/i });
    expect(layoutButton).toBeInTheDocument();

    fireEvent.click(layoutButton);
    expect(screen.getByRole("button", { name: /horizontal/i }))
      .toBeInTheDocument();
  });

  it("opens and closes node details drawer", async () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
      />,
    );

    // Click on a node to open details
    const mockNode = screen.getByTestId("mock-node");
    fireEvent.click(mockNode);

    await waitFor(() => {
      expect(screen.getByText("Node Details")).toBeInTheDocument();
    });

    // Close the drawer
    const closeButton = screen.getByLabelText(/close/i);
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText("Node Details")).not.toBeInTheDocument();
    });
  });

  it("renders with mock data when no plan is provided", () => {
    render(<TaskFlowVisualizer />);

    // Should render with demo data
    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    expect(screen.getByText("Task Flow")).toBeInTheDocument();
  });

  it("displays correct phase count in control panel", () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
      />,
    );

    // Should show count from mockPlan (2 phases)
    expect(screen.getByText("2 phases")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <TaskFlowVisualizer
        plan={mockPlan}
        className="custom-visualizer"
      />,
    );

    expect(container.firstChild).toHaveClass("custom-visualizer");
  });
});

describe("TaskFlowVisualizer Integration", () => {
  it("properly integrates plan data with ReactFlow nodes", () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
      />,
    );

    // Verify the component renders and processes the plan data
    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    expect(screen.getByText("2 phases")).toBeInTheDocument();
  });

  it("updates display when agent activity is toggled", () => {
    render(
      <TaskFlowVisualizer
        plan={mockPlan}
        agents={mockAgents}
        events={mockEvents}
      />,
    );

    const toggle = screen.getByRole("checkbox", {
      name: /show agent activity/i,
    });

    // Initially checked
    expect(toggle).toBeChecked();

    // Toggle off
    fireEvent.click(toggle);
    expect(toggle).not.toBeChecked();

    // Toggle back on
    fireEvent.click(toggle);
    expect(toggle).toBeChecked();
  });

  it("handles empty or undefined props gracefully", () => {
    render(
      <TaskFlowVisualizer
        plan={undefined}
        agents={[]}
        events={[]}
      />,
    );

    // Should still render with fallback/demo data
    expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    expect(screen.getByText("Task Flow")).toBeInTheDocument();
  });
});
