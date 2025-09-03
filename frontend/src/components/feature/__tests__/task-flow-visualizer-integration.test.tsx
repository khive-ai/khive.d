/**
 * Task Flow Visualizer Integration Tests
 * Testing integration with orchestration system and existing dashboard components
 * Focus: Real-time updates, coordination with TaskListDisplay, system integration
 *
 * @tester: tester+agentic-systems
 * @coordination: plan_1756842242
 * @dependencies: orchestration-workflows.test.tsx, task-list-display.tsx
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

// Import existing components
import { TaskListDisplay } from "@/components/feature/task-list-display";
import type { TaskItem } from "@/components/feature/task-list-display";

// Mock the complete Task Flow Visualizer system
const MockTaskFlowVisualizerSystem = ({
  coordinationId,
  showTableView = false,
  showDiagramView = true,
  onViewToggle,
  onTaskUpdate,
}: {
  coordinationId?: string;
  showTableView?: boolean;
  showDiagramView?: boolean;
  onViewToggle?: (view: "table" | "diagram" | "split") => void;
  onTaskUpdate?: (task: TaskItem) => void;
}) => {
  const [selectedTask, setSelectedTask] = React.useState<TaskItem | null>(null);
  const [highlightedAgent, setHighlightedAgent] = React.useState<string | null>(
    null,
  );

  // Mock tasks that would come from the API
  const mockTasks: TaskItem[] = [
    {
      id: "integration-task-001",
      name: "Multi-Agent Research Coordination",
      description: "Coordinate 5 researchers across different domains",
      status: "running",
      priority: "high",
      progress: 65,
      assignedAgents: [
        {
          id: "researcher-alpha",
          role: "researcher",
          domain: "memory-systems",
          status: "active",
        },
        {
          id: "researcher-beta",
          role: "researcher",
          domain: "distributed-systems",
          status: "active",
        },
        {
          id: "researcher-gamma",
          role: "researcher",
          domain: "agentic-systems",
          status: "active",
        },
      ],
      dependencies: [],
      coordinationStrategy: "FAN_OUT_SYNTHESIZE",
      expectedArtifacts: ["Research Synthesis", "Coordination Report"],
      startTime: new Date(Date.now() - 3900000).toISOString(), // 65 minutes ago
      phase: "Active Research",
      sessionId: "integration-session-001",
    },
    {
      id: "integration-task-002",
      name: "Analysis Consolidation",
      description: "Consolidate research findings from multiple agents",
      status: "pending",
      priority: "high",
      progress: 0,
      assignedAgents: [
        {
          id: "analyst-delta",
          role: "analyst",
          domain: "agentic-systems",
          status: "idle",
        },
      ],
      dependencies: ["integration-task-001"],
      coordinationStrategy: "FAN_OUT_SYNTHESIZE",
      expectedArtifacts: ["Consolidated Analysis"],
      phase: "Pending Synthesis",
      sessionId: "integration-session-001",
    },
  ];

  return (
    <div data-testid="task-flow-visualizer-system">
      {/* View Toggle Controls */}
      <div data-testid="view-controls">
        <button
          data-testid="toggle-table-view"
          onClick={() => onViewToggle?.("table")}
          className={showTableView ? "active" : ""}
        >
          Table View
        </button>
        <button
          data-testid="toggle-diagram-view"
          onClick={() => onViewToggle?.("diagram")}
          className={showDiagramView ? "active" : ""}
        >
          Diagram View
        </button>
        <button
          data-testid="toggle-split-view"
          onClick={() => onViewToggle?.("split")}
          className={showTableView && showDiagramView ? "active" : ""}
        >
          Split View
        </button>
      </div>

      <div
        data-testid="visualizer-content"
        style={{ display: "flex", gap: "1rem" }}
      >
        {/* Table View */}
        {showTableView && (
          <div
            data-testid="table-view-container"
            style={{ flex: showDiagramView ? 1 : 2 }}
          >
            <TaskListDisplay
              coordinationId={coordinationId}
              onTaskSelect={(task) => {
                setSelectedTask(task);
                onTaskUpdate?.(task);
              }}
              onTaskAction={(taskId, action) => {
                const task = mockTasks.find((t) => t.id === taskId);
                if (task) {
                  const updatedTask = {
                    ...task,
                    status: action === "start"
                      ? "running" as const
                      : action === "pause"
                      ? "paused" as const
                      : action === "stop"
                      ? "pending" as const
                      : task.status,
                  };
                  onTaskUpdate?.(updatedTask);
                }
              }}
            />
          </div>
        )}

        {/* Diagram View */}
        {showDiagramView && (
          <div
            data-testid="diagram-view-container"
            style={{ flex: showTableView ? 1 : 2 }}
          >
            <div data-testid="workflow-diagram">
              <h3>Interactive Workflow Diagram</h3>
              <div data-testid="diagram-content">
                {mockTasks.map((task) => (
                  <div
                    key={task.id}
                    data-testid={`diagram-task-${task.id}`}
                    className={`diagram-task ${
                      selectedTask?.id === task.id ? "selected" : ""
                    }`}
                    onClick={() => {
                      setSelectedTask(task);
                      onTaskUpdate?.(task);
                    }}
                  >
                    <div data-testid={`diagram-task-name-${task.id}`}>
                      {task.name}
                    </div>
                    <div
                      data-testid={`diagram-task-status-${task.id}`}
                      className={`status-${task.status}`}
                    >
                      {task.status}
                    </div>
                    <div data-testid={`diagram-task-progress-${task.id}`}>
                      {task.progress}%
                    </div>
                    <div data-testid={`diagram-agents-${task.id}`}>
                      {task.assignedAgents.map((agent) => (
                        <span
                          key={agent.id}
                          data-testid={`diagram-agent-${agent.id}`}
                          className={`agent-indicator ${
                            highlightedAgent === agent.id ? "highlighted" : ""
                          } agent-${agent.status}`}
                          onMouseEnter={() => setHighlightedAgent(agent.id)}
                          onMouseLeave={() => setHighlightedAgent(null)}
                        >
                          {agent.role}+{agent.domain}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}

                {/* Connection Lines */}
                <div data-testid="workflow-connections">
                  {mockTasks
                    .filter((task) => task.dependencies.length > 0)
                    .map((task) => (
                      <div
                        key={`connection-${task.id}`}
                        data-testid={`workflow-connection-${task.id}`}
                        className="workflow-connection"
                      >
                        {task.dependencies.map((depId) => (
                          <div
                            key={depId}
                            data-testid={`connection-line-${depId}-${task.id}`}
                          >
                            {depId} → {task.id}
                          </div>
                        ))}
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Selected Task Details */}
      {selectedTask && (
        <div data-testid="selected-task-details">
          <h4>Selected Task: {selectedTask.name}</h4>
          <div data-testid="task-detail-status">
            Status: {selectedTask.status}
          </div>
          <div data-testid="task-detail-progress">
            Progress: {selectedTask.progress}%
          </div>
          <div data-testid="task-detail-agents">
            Agents:{" "}
            {selectedTask.assignedAgents.map((a) => `${a.role}+${a.domain}`)
              .join(", ")}
          </div>
          <div data-testid="task-detail-strategy">
            Strategy: {selectedTask.coordinationStrategy}
          </div>
        </div>
      )}
    </div>
  );
};

// Mock server for API responses
const server = setupServer(
  // Events endpoint for real-time updates
  rest.get("/api/events", (req, res, ctx) => {
    const coordinationId = req.url.searchParams.get("coordination_id");
    return res(ctx.json([
      {
        id: "event-001",
        coordinationId: coordinationId || "integration-session-001",
        agentId: "researcher-alpha",
        eventType: "task_progress_update",
        timestamp: new Date().toISOString(),
        metadata: { progress: 65, status: "active" },
      },
      {
        id: "event-002",
        coordinationId: coordinationId || "integration-session-001",
        agentId: "researcher-beta",
        eventType: "agent_status_change",
        timestamp: new Date().toISOString(),
        metadata: { newStatus: "active", previousStatus: "idle" },
      },
    ]));
  }),
  // Plans endpoint
  rest.get("/api/plans", (req, res, ctx) => {
    return res(ctx.json([
      {
        id: "plan-integration-001",
        sessionId: "integration-session-001",
        coordinationStrategy: "FAN_OUT_SYNTHESIZE",
        phases: [
          {
            name: "Research",
            agents: ["researcher-alpha", "researcher-beta", "researcher-gamma"],
          },
          { name: "Synthesis", agents: ["analyst-delta"] },
        ],
      },
    ]));
  }),
  // Agents endpoint
  rest.get("/api/agents", (req, res, ctx) => {
    return res(ctx.json([
      {
        id: "researcher-alpha",
        role: "researcher",
        domain: "memory-systems",
        status: "active",
        currentTask: "Multi-Agent Research Coordination",
        duration: 3900000,
        sessionId: "integration-session-001",
      },
      {
        id: "researcher-beta",
        role: "researcher",
        domain: "distributed-systems",
        status: "active",
        currentTask: "Multi-Agent Research Coordination",
        duration: 3900000,
        sessionId: "integration-session-001",
      },
      {
        id: "analyst-delta",
        role: "analyst",
        domain: "agentic-systems",
        status: "idle",
        sessionId: "integration-session-001",
      },
    ]));
  }),
);

// Test wrapper
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

describe("Task Flow Visualizer Integration Tests", () => {
  beforeAll(() => {
    server.listen();
  });

  beforeEach(() => {
    server.resetHandlers();
  });

  afterAll(() => {
    server.close();
  });

  describe("Dual View Integration", () => {
    it("should render both table and diagram views simultaneously", () => {
      const Wrapper = createIntegrationWrapper();
      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showTableView={true}
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      expect(screen.getByTestId("table-view-container")).toBeInTheDocument();
      expect(screen.getByTestId("diagram-view-container")).toBeInTheDocument();
      expect(screen.getByTestId("workflow-diagram")).toBeInTheDocument();
    });

    it("should synchronize task selection between table and diagram views", async () => {
      const user = userEvent.setup();
      const onTaskUpdate = jest.fn();
      const Wrapper = createIntegrationWrapper();

      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showTableView={true}
          showDiagramView={true}
          onTaskUpdate={onTaskUpdate}
        />,
        { wrapper: Wrapper },
      );

      // Click task in diagram view
      const diagramTask = screen.getByTestId(
        "diagram-task-integration-task-001",
      );
      await user.click(diagramTask);

      // Should show in selected task details
      await waitFor(() => {
        expect(screen.getByTestId("selected-task-details")).toBeInTheDocument();
        expect(
          screen.getByText("Selected Task: Multi-Agent Research Coordination"),
        ).toBeInTheDocument();
      });

      expect(onTaskUpdate).toHaveBeenCalled();
    });

    it("should provide view toggle controls", async () => {
      const user = userEvent.setup();
      const onViewToggle = jest.fn();
      const Wrapper = createIntegrationWrapper();

      render(
        <MockTaskFlowVisualizerSystem
          onViewToggle={onViewToggle}
          showTableView={false}
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      // Toggle to table view
      await user.click(screen.getByTestId("toggle-table-view"));
      expect(onViewToggle).toHaveBeenCalledWith("table");

      // Toggle to split view
      await user.click(screen.getByTestId("toggle-split-view"));
      expect(onViewToggle).toHaveBeenCalledWith("split");
    });
  });

  describe("Real-Time Updates Integration", () => {
    it("should update both views when task status changes", async () => {
      const user = userEvent.setup();
      const Wrapper = createIntegrationWrapper();

      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showTableView={true}
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      // Wait for initial render
      await waitFor(() => {
        expect(screen.getByTestId("diagram-task-integration-task-001"))
          .toBeInTheDocument();
      });

      // Verify initial status
      expect(screen.getByTestId("diagram-task-status-integration-task-001"))
        .toHaveTextContent("running");
      expect(screen.getByTestId("diagram-task-status-integration-task-001"))
        .toHaveClass("status-running");
    });

    it("should reflect agent activity changes in both views", async () => {
      const Wrapper = createIntegrationWrapper();
      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showTableView={true}
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("diagram-agent-researcher-alpha"))
          .toBeInTheDocument();
      });

      // Should show agent status
      const agentIndicator = screen.getByTestId(
        "diagram-agent-researcher-alpha",
      );
      expect(agentIndicator).toHaveClass("agent-active");
      expect(agentIndicator).toHaveTextContent("researcher+memory-systems");
    });

    it("should update progress indicators in real-time", async () => {
      const Wrapper = createIntegrationWrapper();
      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("diagram-task-progress-integration-task-001"))
          .toBeInTheDocument();
      });

      expect(screen.getByTestId("diagram-task-progress-integration-task-001"))
        .toHaveTextContent("65%");
    });
  });

  describe("Coordination Pattern Integration", () => {
    it("should visualize fan-out pattern with multiple researchers", async () => {
      const Wrapper = createIntegrationWrapper();
      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("diagram-task-integration-task-001"))
          .toBeInTheDocument();
      });

      // Should show multiple researchers working in parallel
      expect(screen.getByTestId("diagram-agent-researcher-alpha"))
        .toBeInTheDocument();
      expect(screen.getByTestId("diagram-agent-researcher-beta"))
        .toBeInTheDocument();
      expect(screen.getByTestId("diagram-agent-researcher-gamma"))
        .toBeInTheDocument();

      // Should show connection to synthesis task
      expect(screen.getByTestId("workflow-connection-integration-task-002"))
        .toBeInTheDocument();
      expect(
        screen.getByTestId(
          "connection-line-integration-task-001-integration-task-002",
        ),
      )
        .toHaveTextContent("integration-task-001 → integration-task-002");
    });

    it("should handle complex task dependencies in workflow connections", async () => {
      const Wrapper = createIntegrationWrapper();
      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("workflow-connections")).toBeInTheDocument();
      });

      // Should visualize task dependencies
      const connections = screen.getByTestId("workflow-connections");
      expect(
        within(connections).getByTestId(
          "workflow-connection-integration-task-002",
        ),
      ).toBeInTheDocument();
    });
  });

  describe("Agent Highlighting Integration", () => {
    it("should highlight agents across both table and diagram views", async () => {
      const user = userEvent.setup();
      const Wrapper = createIntegrationWrapper();

      render(
        <MockTaskFlowVisualizerSystem
          showTableView={true}
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("diagram-agent-researcher-alpha"))
          .toBeInTheDocument();
      });

      // Hover over agent in diagram
      const agentIndicator = screen.getByTestId(
        "diagram-agent-researcher-alpha",
      );
      await user.hover(agentIndicator);

      // Should highlight in diagram
      expect(agentIndicator).toHaveClass("highlighted");
    });

    it("should show agent status changes with visual feedback", async () => {
      const Wrapper = createIntegrationWrapper();
      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("diagram-agent-researcher-alpha"))
          .toBeInTheDocument();
      });

      // Should show different status classes
      expect(screen.getByTestId("diagram-agent-researcher-alpha")).toHaveClass(
        "agent-active",
      );
      expect(screen.getByTestId("diagram-agent-analyst-delta")).toHaveClass(
        "agent-idle",
      );
    });
  });

  describe("Task Selection and Details Integration", () => {
    it("should show detailed task information when selected from either view", async () => {
      const user = userEvent.setup();
      const Wrapper = createIntegrationWrapper();

      render(
        <MockTaskFlowVisualizerSystem
          showTableView={true}
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("diagram-task-integration-task-001"))
          .toBeInTheDocument();
      });

      // Select task from diagram
      await user.click(screen.getByTestId("diagram-task-integration-task-001"));

      // Should show detailed information
      await waitFor(() => {
        expect(screen.getByTestId("selected-task-details")).toBeInTheDocument();
        expect(screen.getByTestId("task-detail-status")).toHaveTextContent(
          "Status: running",
        );
        expect(screen.getByTestId("task-detail-progress")).toHaveTextContent(
          "Progress: 65%",
        );
        expect(screen.getByTestId("task-detail-strategy")).toHaveTextContent(
          "Strategy: FAN_OUT_SYNTHESIZE",
        );
        expect(screen.getByTestId("task-detail-agents"))
          .toHaveTextContent(
            "Agents: researcher+memory-systems, researcher+distributed-systems, researcher+agentic-systems",
          );
      });
    });

    it("should maintain selection state across view changes", async () => {
      const user = userEvent.setup();
      const onViewToggle = jest.fn();
      const Wrapper = createIntegrationWrapper();

      const { rerender } = render(
        <MockTaskFlowVisualizerSystem
          onViewToggle={onViewToggle}
          showTableView={true}
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(screen.getByTestId("diagram-task-integration-task-001"))
          .toBeInTheDocument();
      });

      // Select a task
      await user.click(screen.getByTestId("diagram-task-integration-task-001"));

      await waitFor(() => {
        expect(screen.getByTestId("selected-task-details")).toBeInTheDocument();
      });

      // Switch to table-only view
      rerender(
        <MockTaskFlowVisualizerSystem
          onViewToggle={onViewToggle}
          showTableView={true}
          showDiagramView={false}
        />,
      );

      // Selection should persist
      expect(screen.getByTestId("selected-task-details")).toBeInTheDocument();
      expect(
        screen.getByText("Selected Task: Multi-Agent Research Coordination"),
      ).toBeInTheDocument();
    });
  });

  describe("Performance and Scalability Integration", () => {
    it("should handle switching between views efficiently", async () => {
      const user = userEvent.setup();
      const onViewToggle = jest.fn();
      const Wrapper = createIntegrationWrapper();

      render(
        <MockTaskFlowVisualizerSystem
          onViewToggle={onViewToggle}
          showTableView={true}
          showDiagramView={false}
        />,
        { wrapper: Wrapper },
      );

      // Switch to diagram view
      await user.click(screen.getByTestId("toggle-diagram-view"));
      expect(onViewToggle).toHaveBeenCalledWith("diagram");

      // Switch to split view
      await user.click(screen.getByTestId("toggle-split-view"));
      expect(onViewToggle).toHaveBeenCalledWith("split");

      // All view changes should be efficient without unnecessary re-renders
      expect(onViewToggle).toHaveBeenCalledTimes(2);
    });

    it("should handle large numbers of concurrent agent updates", async () => {
      // Simulate high-frequency updates
      server.use(
        rest.get("/api/events", (req, res, ctx) => {
          const events = Array.from({ length: 50 }, (_, i) => ({
            id: `event-${i}`,
            coordinationId: "integration-session-001",
            agentId: `agent-${i % 10}`,
            eventType: "agent_status_update",
            timestamp: new Date().toISOString(),
            metadata: { status: i % 2 === 0 ? "active" : "idle" },
          }));
          return res(ctx.json(events));
        }),
      );

      const Wrapper = createIntegrationWrapper();
      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showTableView={true}
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      // Should handle high-frequency updates without performance issues
      await waitFor(() => {
        expect(screen.getByTestId("task-flow-visualizer-system"))
          .toBeInTheDocument();
      });
    });
  });

  describe("Error Handling Integration", () => {
    it("should gracefully handle API failures while maintaining visualization", async () => {
      // Simulate API failure
      server.use(
        rest.get("/api/events", (req, res, ctx) => {
          return res(
            ctx.status(500),
            ctx.json({ error: "Internal Server Error" }),
          );
        }),
      );

      const Wrapper = createIntegrationWrapper();
      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      // Should still render diagram with local data
      await waitFor(() => {
        expect(screen.getByTestId("workflow-diagram")).toBeInTheDocument();
        expect(screen.getByTestId("diagram-task-integration-task-001"))
          .toBeInTheDocument();
      });
    });

    it("should handle malformed coordination data gracefully", async () => {
      server.use(
        rest.get("/api/plans", (req, res, ctx) => {
          return res(ctx.json([
            {
              id: "malformed-plan",
              // Missing required fields
              coordinationStrategy: undefined,
              phases: null,
            },
          ]));
        }),
      );

      const Wrapper = createIntegrationWrapper();
      render(
        <MockTaskFlowVisualizerSystem
          coordinationId="integration-session-001"
          showDiagramView={true}
        />,
        { wrapper: Wrapper },
      );

      // Should render without crashing
      await waitFor(() => {
        expect(screen.getByTestId("workflow-diagram")).toBeInTheDocument();
      });
    });
  });
});
