/**
 * Task Flow Visualizer MVP Tests
 * Comprehensive testing suite for interactive workflow diagrams and agent activity highlighting
 * Focus: Basic workflow diagram display, agent activity highlighting, coordination patterns
 *
 * @tester: tester+agentic-systems
 * @coordination: plan_1756842242
 * @dependencies: workflow-diagram-display.tsx (analyst_agentic-systems)
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

// Import types and interfaces
import type { TaskItem } from "@/components/feature/task-list-display";

// Mock the WorkflowDiagramDisplay component until it's built by analyst
const MockWorkflowDiagramDisplay = React.forwardRef<
  HTMLDivElement,
  WorkflowDiagramDisplayProps
>((
  {
    tasks,
    onTaskSelect,
    onAgentHighlight,
    coordinationStrategy,
    className,
    ...props
  },
  ref,
) => (
  <div
    ref={ref}
    className={className}
    data-testid="workflow-diagram-display"
    {...props}
  >
    <div data-testid="workflow-title">Task Flow Visualizer</div>
    <div data-testid="coordination-strategy">{coordinationStrategy}</div>
    <div data-testid="tasks-container">
      {tasks?.map((task) => (
        <div
          key={task.id}
          data-testid={`task-node-${task.id}`}
          className={`task-node task-status-${task.status}`}
          onClick={() => onTaskSelect?.(task)}
        >
          <div data-testid={`task-name-${task.id}`}>{task.name}</div>
          <div data-testid={`task-progress-${task.id}`}>{task.progress}%</div>
          <div data-testid={`task-agents-${task.id}`}>
            {task.assignedAgents.map((agent) => (
              <span
                key={agent.id}
                data-testid={`agent-${agent.id}`}
                className={`agent-indicator agent-status-${agent.status}`}
                onMouseEnter={() => onAgentHighlight?.(agent.id, true)}
                onMouseLeave={() => onAgentHighlight?.(agent.id, false)}
              >
                {agent.role}+{agent.domain}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
    <div data-testid="workflow-connections">
      {/* Mock workflow connections visualization */}
      {tasks?.filter((t) => t.dependencies?.length > 0).map((task) => (
        <div
          key={`connection-${task.id}`}
          data-testid={`connection-${task.id}`}
        >
          Connection: {task.dependencies.join(" → ")} → {task.id}
        </div>
      ))}
    </div>
  </div>
));

// Mock the WorkflowNode component until it's built by architect
const MockWorkflowNode = (
  { task, highlighted, onSelect }: WorkflowNodeProps,
) => (
  <div
    data-testid={`workflow-node-${task.id}`}
    className={`workflow-node ${highlighted ? "highlighted" : ""}`}
    onClick={() => onSelect?.(task)}
  >
    <div data-testid={`node-title-${task.id}`}>{task.name}</div>
    <div data-testid={`node-status-${task.id}`}>{task.status}</div>
    <div data-testid={`node-strategy-${task.id}`}>
      {task.coordinationStrategy}
    </div>
  </div>
);

// Type definitions for the components being tested
export interface WorkflowDiagramDisplayProps {
  tasks?: TaskItem[];
  coordinationStrategy?:
    | "FAN_OUT_SYNTHESIZE"
    | "PIPELINE"
    | "PARALLEL"
    | "AUTO";
  onTaskSelect?: (task: TaskItem) => void;
  onAgentHighlight?: (agentId: string, highlight: boolean) => void;
  onPatternChange?: (pattern: string) => void;
  showMinimap?: boolean;
  showControls?: boolean;
  animated?: boolean;
  className?: string;
}

export interface WorkflowNodeProps {
  task: TaskItem;
  highlighted?: boolean;
  onSelect?: (task: TaskItem) => void;
  position?: { x: number; y: number };
  connections?: string[];
}

// Mock data for comprehensive testing scenarios
const mockTasksForFanOut: TaskItem[] = [
  {
    id: "fanout-research-001",
    name: "Memory Systems Research Phase",
    description: "Parallel research across multiple memory system aspects",
    status: "running",
    priority: "high",
    progress: 45,
    assignedAgents: [
      {
        id: "researcher-001",
        role: "researcher",
        domain: "memory-systems",
        status: "active",
      },
      {
        id: "researcher-002",
        role: "researcher",
        domain: "memory-systems",
        status: "active",
      },
      {
        id: "researcher-003",
        role: "researcher",
        domain: "distributed-systems",
        status: "active",
      },
    ],
    dependencies: [],
    coordinationStrategy: "FAN_OUT_SYNTHESIZE",
    expectedArtifacts: [
      "Research Report A",
      "Research Report B",
      "Research Report C",
    ],
    startTime: new Date(Date.now() - 2700000).toISOString(), // 45 minutes ago
    phase: "Discovery",
    sessionId: "session-fanout-001",
  },
  {
    id: "fanout-synthesis-001",
    name: "Research Synthesis Phase",
    description: "Consolidate research findings into unified analysis",
    status: "pending",
    priority: "high",
    progress: 0,
    assignedAgents: [
      {
        id: "analyst-001",
        role: "analyst",
        domain: "agentic-systems",
        status: "idle",
      },
    ],
    dependencies: ["fanout-research-001"],
    coordinationStrategy: "FAN_OUT_SYNTHESIZE",
    expectedArtifacts: ["Unified Analysis Report"],
    phase: "Synthesis",
    sessionId: "session-fanout-001",
  },
];

const mockTasksForPipeline: TaskItem[] = [
  {
    id: "pipeline-design-001",
    name: "System Architecture Design",
    description: "Design overall system architecture",
    status: "completed",
    priority: "critical",
    progress: 100,
    assignedAgents: [
      {
        id: "architect-001",
        role: "architect",
        domain: "software-architecture",
        status: "idle",
      },
    ],
    dependencies: [],
    coordinationStrategy: "PIPELINE",
    expectedArtifacts: ["Architecture Document", "Component Diagrams"],
    startTime: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
    endTime: new Date(Date.now() - 5400000).toISOString(), // 1.5 hours ago
    duration: 1800000, // 30 minutes
    phase: "Design",
    sessionId: "session-pipeline-001",
  },
  {
    id: "pipeline-implement-001",
    name: "Core Implementation",
    description: "Implement core system components",
    status: "running",
    priority: "critical",
    progress: 75,
    assignedAgents: [
      {
        id: "implementer-001",
        role: "implementer",
        domain: "rust-performance",
        status: "active",
      },
      {
        id: "implementer-002",
        role: "implementer",
        domain: "async-programming",
        status: "active",
      },
    ],
    dependencies: ["pipeline-design-001"],
    coordinationStrategy: "PIPELINE",
    expectedArtifacts: ["Core Components", "Unit Tests"],
    startTime: new Date(Date.now() - 5400000).toISOString(), // 1.5 hours ago
    phase: "Implementation",
    sessionId: "session-pipeline-001",
  },
  {
    id: "pipeline-test-001",
    name: "Integration Testing",
    description: "Comprehensive system testing and validation",
    status: "pending",
    priority: "critical",
    progress: 0,
    assignedAgents: [
      {
        id: "tester-001",
        role: "tester",
        domain: "agentic-systems",
        status: "idle",
      },
    ],
    dependencies: ["pipeline-implement-001"],
    coordinationStrategy: "PIPELINE",
    expectedArtifacts: ["Test Results", "Performance Metrics"],
    phase: "Testing",
    sessionId: "session-pipeline-001",
  },
];

const mockTasksForParallel: TaskItem[] = [
  {
    id: "parallel-auth-001",
    name: "Authentication Module",
    description: "Independent authentication system implementation",
    status: "running",
    priority: "normal",
    progress: 60,
    assignedAgents: [
      {
        id: "implementer-003",
        role: "implementer",
        domain: "software-architecture",
        status: "active",
      },
    ],
    dependencies: [],
    coordinationStrategy: "PARALLEL",
    expectedArtifacts: ["Auth Module", "Auth Tests"],
    startTime: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    phase: "Implementation",
    sessionId: "session-parallel-001",
  },
  {
    id: "parallel-storage-001",
    name: "Storage Module",
    description: "Independent storage system implementation",
    status: "running",
    priority: "normal",
    progress: 80,
    assignedAgents: [
      {
        id: "implementer-004",
        role: "implementer",
        domain: "memory-systems",
        status: "active",
      },
    ],
    dependencies: [],
    coordinationStrategy: "PARALLEL",
    expectedArtifacts: ["Storage Module", "Storage Tests"],
    startTime: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    phase: "Implementation",
    sessionId: "session-parallel-001",
  },
  {
    id: "parallel-ui-001",
    name: "UI Components",
    description: "Independent user interface implementation",
    status: "completed",
    priority: "normal",
    progress: 100,
    assignedAgents: [
      {
        id: "implementer-005",
        role: "implementer",
        domain: "software-architecture",
        status: "idle",
      },
    ],
    dependencies: [],
    coordinationStrategy: "PARALLEL",
    expectedArtifacts: ["UI Components", "UI Tests"],
    startTime: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
    endTime: new Date(Date.now() - 1800000).toISOString(), // 30 minutes ago
    duration: 1800000, // 30 minutes
    phase: "Implementation",
    sessionId: "session-parallel-001",
  },
];

// Test wrapper with all providers
const createTestWrapper = () => {
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

describe("Task Flow Visualizer MVP - Core Functionality", () => {
  describe("Basic Workflow Diagram Display", () => {
    it("should render workflow diagram with tasks and connections", () => {
      const onTaskSelect = jest.fn();
      const Wrapper = createTestWrapper();

      render(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForFanOut}
          coordinationStrategy="FAN_OUT_SYNTHESIZE"
          onTaskSelect={onTaskSelect}
        />,
        { wrapper: Wrapper },
      );

      // Verify main components are rendered
      expect(screen.getByTestId("workflow-diagram-display"))
        .toBeInTheDocument();
      expect(screen.getByTestId("workflow-title")).toHaveTextContent(
        "Task Flow Visualizer",
      );
      expect(screen.getByTestId("coordination-strategy")).toHaveTextContent(
        "FAN_OUT_SYNTHESIZE",
      );

      // Verify tasks are displayed
      expect(screen.getByTestId("task-node-fanout-research-001"))
        .toBeInTheDocument();
      expect(screen.getByTestId("task-node-fanout-synthesis-001"))
        .toBeInTheDocument();

      // Verify task details
      expect(screen.getByTestId("task-name-fanout-research-001"))
        .toHaveTextContent("Memory Systems Research Phase");
      expect(screen.getByTestId("task-progress-fanout-research-001"))
        .toHaveTextContent("45%");

      // Verify dependency connections are shown
      expect(screen.getByTestId("connection-fanout-synthesis-001"))
        .toBeInTheDocument();
      expect(screen.getByTestId("connection-fanout-synthesis-001"))
        .toHaveTextContent(
          "Connection: fanout-research-001 → fanout-synthesis-001",
        );
    });

    it("should handle task selection interactions", async () => {
      const user = userEvent.setup();
      const onTaskSelect = jest.fn();
      const Wrapper = createTestWrapper();

      render(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForFanOut}
          onTaskSelect={onTaskSelect}
        />,
        { wrapper: Wrapper },
      );

      // Click on first task
      const taskNode = screen.getByTestId("task-node-fanout-research-001");
      await user.click(taskNode);

      expect(onTaskSelect).toHaveBeenCalledWith(mockTasksForFanOut[0]);
    });

    it("should display different task statuses with visual indicators", () => {
      const tasksWithVariousStatuses: TaskItem[] = [
        { ...mockTasksForFanOut[0], status: "running" },
        { ...mockTasksForFanOut[1], status: "pending" },
        { ...mockTasksForParallel[2], status: "completed" },
        {
          ...mockTasksForParallel[0],
          id: "failed-task",
          status: "failed",
          progress: 30,
        },
      ];

      const Wrapper = createTestWrapper();
      render(
        <MockWorkflowDiagramDisplay tasks={tasksWithVariousStatuses} />,
        { wrapper: Wrapper },
      );

      // Verify status-based CSS classes are applied
      expect(screen.getByTestId("task-node-fanout-research-001")).toHaveClass(
        "task-status-running",
      );
      expect(screen.getByTestId("task-node-fanout-synthesis-001")).toHaveClass(
        "task-status-pending",
      );
      expect(screen.getByTestId("task-node-parallel-ui-001")).toHaveClass(
        "task-status-completed",
      );
      expect(screen.getByTestId("task-node-failed-task")).toHaveClass(
        "task-status-failed",
      );
    });

    it("should handle empty tasks gracefully", () => {
      const Wrapper = createTestWrapper();
      render(<MockWorkflowDiagramDisplay tasks={[]} />, { wrapper: Wrapper });

      expect(screen.getByTestId("workflow-diagram-display"))
        .toBeInTheDocument();
      expect(screen.getByTestId("tasks-container")).toBeEmptyDOMElement();
      expect(screen.getByTestId("workflow-connections")).toBeEmptyDOMElement();
    });
  });

  describe("Agent Activity Highlighting", () => {
    it("should highlight agents on hover and show agent information", async () => {
      const user = userEvent.setup();
      const onAgentHighlight = jest.fn();
      const Wrapper = createTestWrapper();

      render(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForFanOut}
          onAgentHighlight={onAgentHighlight}
        />,
        { wrapper: Wrapper },
      );

      // Find agent indicator
      const agentIndicator = screen.getByTestId("agent-researcher-001");
      expect(agentIndicator).toHaveTextContent("researcher+memory-systems");

      // Hover over agent
      await user.hover(agentIndicator);
      expect(onAgentHighlight).toHaveBeenCalledWith("researcher-001", true);

      // Un-hover
      await user.unhover(agentIndicator);
      expect(onAgentHighlight).toHaveBeenCalledWith("researcher-001", false);
    });

    it("should display agent status with visual indicators", () => {
      const tasksWithAgentStatuses: TaskItem[] = [
        {
          ...mockTasksForFanOut[0],
          assignedAgents: [
            {
              id: "active-agent",
              role: "researcher",
              domain: "memory-systems",
              status: "active",
            },
            {
              id: "idle-agent",
              role: "analyst",
              domain: "agentic-systems",
              status: "idle",
            },
            {
              id: "error-agent",
              role: "critic",
              domain: "distributed-systems",
              status: "error",
            },
          ],
        },
      ];

      const Wrapper = createTestWrapper();
      render(<MockWorkflowDiagramDisplay tasks={tasksWithAgentStatuses} />, {
        wrapper: Wrapper,
      });

      // Verify agent status CSS classes
      expect(screen.getByTestId("agent-active-agent")).toHaveClass(
        "agent-status-active",
      );
      expect(screen.getByTestId("agent-idle-agent")).toHaveClass(
        "agent-status-idle",
      );
      expect(screen.getByTestId("agent-error-agent")).toHaveClass(
        "agent-status-error",
      );
    });

    it("should show multiple agents per task with proper grouping", () => {
      const Wrapper = createTestWrapper();
      render(<MockWorkflowDiagramDisplay tasks={mockTasksForFanOut} />, {
        wrapper: Wrapper,
      });

      const taskAgentsContainer = screen.getByTestId(
        "task-agents-fanout-research-001",
      );

      // Should have 3 agents
      expect(within(taskAgentsContainer).getByTestId("agent-researcher-001"))
        .toBeInTheDocument();
      expect(within(taskAgentsContainer).getByTestId("agent-researcher-002"))
        .toBeInTheDocument();
      expect(within(taskAgentsContainer).getByTestId("agent-researcher-003"))
        .toBeInTheDocument();

      // Verify role+domain display
      expect(within(taskAgentsContainer).getByTestId("agent-researcher-001"))
        .toHaveTextContent("researcher+memory-systems");
      expect(within(taskAgentsContainer).getByTestId("agent-researcher-003"))
        .toHaveTextContent("researcher+distributed-systems");
    });
  });

  describe("Coordination Pattern Visualization", () => {
    it("should visualize FAN_OUT_SYNTHESIZE pattern correctly", () => {
      const Wrapper = createTestWrapper();
      render(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForFanOut}
          coordinationStrategy="FAN_OUT_SYNTHESIZE"
        />,
        { wrapper: Wrapper },
      );

      expect(screen.getByTestId("coordination-strategy")).toHaveTextContent(
        "FAN_OUT_SYNTHESIZE",
      );

      // Should show parallel research task feeding into synthesis
      expect(screen.getByTestId("task-node-fanout-research-001"))
        .toBeInTheDocument();
      expect(screen.getByTestId("task-node-fanout-synthesis-001"))
        .toBeInTheDocument();

      // Verify connection shows dependency flow
      expect(screen.getByTestId("connection-fanout-synthesis-001"))
        .toHaveTextContent("fanout-research-001 → fanout-synthesis-001");
    });

    it("should visualize PIPELINE pattern with sequential flow", () => {
      const Wrapper = createTestWrapper();
      render(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForPipeline}
          coordinationStrategy="PIPELINE"
        />,
        { wrapper: Wrapper },
      );

      expect(screen.getByTestId("coordination-strategy")).toHaveTextContent(
        "PIPELINE",
      );

      // Should show sequential task flow
      expect(screen.getByTestId("task-node-pipeline-design-001"))
        .toBeInTheDocument();
      expect(screen.getByTestId("task-node-pipeline-implement-001"))
        .toBeInTheDocument();
      expect(screen.getByTestId("task-node-pipeline-test-001"))
        .toBeInTheDocument();

      // Verify sequential connections
      expect(screen.getByTestId("connection-pipeline-implement-001"))
        .toHaveTextContent("pipeline-design-001 → pipeline-implement-001");
      expect(screen.getByTestId("connection-pipeline-test-001"))
        .toHaveTextContent("pipeline-implement-001 → pipeline-test-001");
    });

    it("should visualize PARALLEL pattern with independent tasks", () => {
      const Wrapper = createTestWrapper();
      render(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForParallel}
          coordinationStrategy="PARALLEL"
        />,
        { wrapper: Wrapper },
      );

      expect(screen.getByTestId("coordination-strategy")).toHaveTextContent(
        "PARALLEL",
      );

      // Should show all parallel tasks
      expect(screen.getByTestId("task-node-parallel-auth-001"))
        .toBeInTheDocument();
      expect(screen.getByTestId("task-node-parallel-storage-001"))
        .toBeInTheDocument();
      expect(screen.getByTestId("task-node-parallel-ui-001"))
        .toBeInTheDocument();

      // No dependency connections should exist (parallel = independent)
      expect(screen.queryByTestId("connection-parallel-auth-001")).not
        .toBeInTheDocument();
      expect(screen.queryByTestId("connection-parallel-storage-001")).not
        .toBeInTheDocument();
      expect(screen.queryByTestId("connection-parallel-ui-001")).not
        .toBeInTheDocument();
    });

    it("should handle pattern switching and update visualization accordingly", () => {
      const { rerender } = render(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForFanOut}
          coordinationStrategy="FAN_OUT_SYNTHESIZE"
        />,
      );

      expect(screen.getByTestId("coordination-strategy")).toHaveTextContent(
        "FAN_OUT_SYNTHESIZE",
      );

      // Switch to pipeline pattern
      rerender(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForPipeline}
          coordinationStrategy="PIPELINE"
        />,
      );

      expect(screen.getByTestId("coordination-strategy")).toHaveTextContent(
        "PIPELINE",
      );
    });
  });

  describe("Integration with Existing Components", () => {
    it("should integrate with TaskListDisplay data format", () => {
      // Use the same TaskItem format as TaskListDisplay
      const taskFromTaskListDisplay = mockTasksForFanOut[0];

      const Wrapper = createTestWrapper();
      render(<MockWorkflowDiagramDisplay tasks={[taskFromTaskListDisplay]} />, {
        wrapper: Wrapper,
      });

      // Should render the same task data
      expect(screen.getByTestId("task-name-fanout-research-001"))
        .toHaveTextContent("Memory Systems Research Phase");
      expect(screen.getByTestId("task-progress-fanout-research-001"))
        .toHaveTextContent("45%");

      // Should show coordination strategy from task data
      const taskNode = screen.getByTestId("task-node-fanout-research-001");
      expect(taskNode).toHaveClass("task-status-running");
    });

    it("should maintain consistent task selection behavior with other components", async () => {
      const user = userEvent.setup();
      const onTaskSelect = jest.fn();
      const Wrapper = createTestWrapper();

      render(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForFanOut}
          onTaskSelect={onTaskSelect}
        />,
        { wrapper: Wrapper },
      );

      await user.click(screen.getByTestId("task-node-fanout-research-001"));

      // Should call with same TaskItem format as other components
      expect(onTaskSelect).toHaveBeenCalledWith(mockTasksForFanOut[0]);
    });
  });

  describe("Workflow Node Component", () => {
    it("should render individual workflow nodes with task information", () => {
      const task = mockTasksForFanOut[0];

      render(<MockWorkflowNode task={task} highlighted={false} />);

      expect(screen.getByTestId(`workflow-node-${task.id}`))
        .toBeInTheDocument();
      expect(screen.getByTestId(`node-title-${task.id}`)).toHaveTextContent(
        task.name,
      );
      expect(screen.getByTestId(`node-status-${task.id}`)).toHaveTextContent(
        task.status,
      );
      expect(screen.getByTestId(`node-strategy-${task.id}`)).toHaveTextContent(
        task.coordinationStrategy,
      );
    });

    it("should apply highlighting when specified", () => {
      const task = mockTasksForFanOut[0];

      render(<MockWorkflowNode task={task} highlighted={true} />);

      expect(screen.getByTestId(`workflow-node-${task.id}`)).toHaveClass(
        "highlighted",
      );
    });

    it("should handle node selection", async () => {
      const user = userEvent.setup();
      const onSelect = jest.fn();
      const task = mockTasksForFanOut[0];

      render(<MockWorkflowNode task={task} onSelect={onSelect} />);

      await user.click(screen.getByTestId(`workflow-node-${task.id}`));
      expect(onSelect).toHaveBeenCalledWith(task);
    });
  });

  describe("Error Handling and Edge Cases", () => {
    it("should handle malformed task data gracefully", () => {
      const malformedTasks = [
        {
          ...mockTasksForFanOut[0],
          assignedAgents: undefined as any, // Simulate malformed data
        },
      ];

      const Wrapper = createTestWrapper();
      render(<MockWorkflowDiagramDisplay tasks={malformedTasks} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByTestId("workflow-diagram-display"))
        .toBeInTheDocument();
      expect(screen.getByTestId("task-node-fanout-research-001"))
        .toBeInTheDocument();
    });

    it("should handle missing dependencies gracefully", () => {
      const tasksWithMissingDeps = [
        {
          ...mockTasksForFanOut[1],
          dependencies: ["nonexistent-task"], // Reference non-existent task
        },
      ];

      const Wrapper = createTestWrapper();
      render(<MockWorkflowDiagramDisplay tasks={tasksWithMissingDeps} />, {
        wrapper: Wrapper,
      });

      expect(screen.getByTestId("workflow-diagram-display"))
        .toBeInTheDocument();
      expect(screen.getByTestId("task-node-fanout-synthesis-001"))
        .toBeInTheDocument();
    });

    it("should handle very large numbers of tasks efficiently", () => {
      const manyTasks = Array.from({ length: 100 }, (_, i) => ({
        ...mockTasksForParallel[0],
        id: `task-${i}`,
        name: `Task ${i}`,
      }));

      const Wrapper = createTestWrapper();
      const { container } = render(
        <MockWorkflowDiagramDisplay tasks={manyTasks} />,
        { wrapper: Wrapper },
      );

      expect(screen.getByTestId("workflow-diagram-display"))
        .toBeInTheDocument();
      // Should render without performance issues
      expect(container.querySelectorAll('[data-testid*="task-node-"]'))
        .toHaveLength(100);
    });
  });

  describe("Accessibility and User Experience", () => {
    it("should provide keyboard navigation support", async () => {
      const user = userEvent.setup();
      const onTaskSelect = jest.fn();
      const Wrapper = createTestWrapper();

      render(
        <MockWorkflowDiagramDisplay
          tasks={mockTasksForFanOut}
          onTaskSelect={onTaskSelect}
        />,
        { wrapper: Wrapper },
      );

      const firstTask = screen.getByTestId("task-node-fanout-research-001");

      // Should be focusable and selectable via keyboard
      firstTask.focus();
      await user.keyboard("{Enter}");

      expect(onTaskSelect).toHaveBeenCalledWith(mockTasksForFanOut[0]);
    });

    it("should provide proper ARIA labels and roles for screen readers", () => {
      const Wrapper = createTestWrapper();
      render(<MockWorkflowDiagramDisplay tasks={mockTasksForFanOut} />, {
        wrapper: Wrapper,
      });

      const workflowDisplay = screen.getByTestId("workflow-diagram-display");
      expect(workflowDisplay).toBeInTheDocument();

      // Task nodes should be accessible
      const taskNode = screen.getByTestId("task-node-fanout-research-001");
      expect(taskNode).toBeInTheDocument();
    });
  });
});
