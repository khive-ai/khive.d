/**
 * Test Suite for Agent Composer Studio MVP
 * Tests agent composition interface, role/domain selection, and basic capability testing
 *
 * Validated by: tester+agentic-systems [2025-01-15]
 * Agentic Systems Patterns Tested:
 * - Agent composition workflow
 * - Role-domain coupling validation
 * - Capability testing interface
 * - Multi-agent coordination preparation
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import AgentComposerStudio from "../agent-composer-studio";
import { useDomains, useRoles } from "@/lib/api/hooks";

// Mock the API hooks
jest.mock("@/lib/api/hooks", () => ({
  useRoles: jest.fn(),
  useDomains: jest.fn(),
}));

// Mock MUI components that might have issues in tests
jest.mock("@mui/material/LinearProgress", () => {
  return function MockLinearProgress() {
    return <div data-testid="linear-progress">Loading...</div>;
  };
});

// Test data
const mockRoles = [
  {
    id: "1",
    name: "researcher",
    description: "Research and discovery specialist",
    capabilities: ["research", "analysis", "documentation"],
    filePath: "/roles/researcher.py",
  },
  {
    id: "2",
    name: "architect",
    description: "System design and architecture specialist",
    capabilities: ["design", "planning", "integration"],
    filePath: "/roles/architect.py",
  },
  {
    id: "3",
    name: "tester",
    description: "Testing and validation specialist",
    capabilities: ["testing", "validation", "quality-assurance"],
    filePath: "/roles/tester.py",
  },
];

const mockDomains = [
  {
    id: "1",
    name: "agentic-systems",
    description: "Multi-agent coordination and orchestration",
    knowledgePatterns: {
      "multi_agent_coordination": ["orchestrator_worker", "peer_to_peer"],
      "swarm_patterns": ["parallel_discovery", "fan_out_fan_in"],
    },
    decisionRules: {
      "orchestration_selection": ["task_count_based", "complexity_based"],
    },
    specializedTools: ["coordination_framework", "swarm_monitor"],
    metrics: ["coordination_efficiency", "conflict_resolution"],
    filePath: "/domains/agentic-systems.py",
  },
  {
    id: "2",
    name: "memory-systems",
    description: "Memory architecture and optimization",
    knowledgePatterns: {
      "memory_patterns": ["caching", "persistence", "retrieval"],
    },
    decisionRules: {
      "memory_optimization": ["access_pattern_based", "size_based"],
    },
    specializedTools: ["memory_profiler", "cache_analyzer"],
    metrics: ["memory_efficiency", "retrieval_speed"],
    filePath: "/domains/memory-systems.py",
  },
];

// Test wrapper component
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  const theme = createTheme();

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe("Agent Composer Studio MVP", () => {
  beforeEach(() => {
    // Mock successful API responses
    (useRoles as jest.Mock).mockReturnValue({
      data: mockRoles,
      isLoading: false,
      error: null,
    });

    (useDomains as jest.Mock).mockReturnValue({
      data: mockDomains,
      isLoading: false,
      error: null,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe("Component Rendering", () => {
    test("renders main header and description", () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      expect(screen.getByText("Agent Composer Studio")).toBeInTheDocument();
      expect(
        screen.getByText(
          /Design and test intelligent agents by combining roles with domain expertise/,
        ),
      ).toBeInTheDocument();
    });

    test("displays loading state when roles and domains are loading", () => {
      (useRoles as jest.Mock).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      expect(screen.getByText("Loading roles and domains..."))
        .toBeInTheDocument();
    });

    test("shows form sections when data is loaded", () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      expect(screen.getByText("Compose Agent")).toBeInTheDocument();
      expect(screen.getByText("Agent Composition")).toBeInTheDocument();
      expect(screen.getByText("Configuration")).toBeInTheDocument();
    });
  });

  describe("Role and Domain Selection", () => {
    test("populates role dropdown with available roles", async () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      const roleSelect = screen.getByLabelText(/Role/);
      expect(roleSelect).toBeInTheDocument();

      // Check that roles are available in the select
      fireEvent.mouseDown(roleSelect);

      await waitFor(() => {
        expect(
          screen.getByText("researcher - Research and discovery specialist"),
        ).toBeInTheDocument();
        expect(
          screen.getByText(
            "architect - System design and architecture specialist",
          ),
        ).toBeInTheDocument();
        expect(screen.getByText("tester - Testing and validation specialist"))
          .toBeInTheDocument();
      });
    });

    test("populates domain dropdown with available domains", async () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      const domainSelect = screen.getByLabelText(/Domain/);
      expect(domainSelect).toBeInTheDocument();

      fireEvent.mouseDown(domainSelect);

      await waitFor(() => {
        expect(
          screen.getByText(
            "agentic-systems - Multi-agent coordination and orchestration",
          ),
        ).toBeInTheDocument();
        expect(
          screen.getByText(
            "memory-systems - Memory architecture and optimization",
          ),
        ).toBeInTheDocument();
      });
    });

    test("displays preview placeholder when no role/domain selected", () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      expect(screen.getByText("Select Role and Domain")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Choose a role and domain to preview the composed agent",
        ),
      ).toBeInTheDocument();
    });

    test("generates agent preview when role and domain are selected", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      // Select role
      const roleSelect = screen.getByLabelText(/Role/);
      fireEvent.mouseDown(roleSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText("researcher - Research and discovery specialist"),
        );
      });

      // Select domain
      const domainSelect = screen.getByLabelText(/Domain/);
      fireEvent.mouseDown(domainSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText(
            "agentic-systems - Multi-agent coordination and orchestration",
          ),
        );
      });

      // Wait for preview to generate
      await waitFor(() => {
        expect(screen.getByText("researcher+agentic-systems"))
          .toBeInTheDocument();
        expect(screen.getByText("Preview")).toBeInTheDocument();
      }, { timeout: 2000 });
    });
  });

  describe("Agent Configuration", () => {
    test("displays configuration fields with proper validation", () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      expect(screen.getByLabelText(/Task Description/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Max Concurrent Tasks/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Timeout \(seconds\)/)).toBeInTheDocument();
    });

    test("validates required fields on form submission", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      // Try to submit without filling required fields
      const submitButton = screen.getByText("Compose Agent");
      await user.click(submitButton);

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText("Please select a role")).toBeInTheDocument();
        expect(screen.getByText("Please select a domain")).toBeInTheDocument();
        expect(screen.getByText("Please provide a task description"))
          .toBeInTheDocument();
      });
    });

    test("validates task description minimum length", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      const taskDescription = screen.getByLabelText(/Task Description/);
      await user.type(taskDescription, "Short task");

      const submitButton = screen.getByText("Compose Agent");
      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText("Task description must be at least 20 characters"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Capability Testing Interface", () => {
    test("displays agent capabilities when preview is generated", async () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      // Select role and domain to generate preview
      const roleSelect = screen.getByLabelText(/Role/);
      fireEvent.mouseDown(roleSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText("researcher - Research and discovery specialist"),
        );
      });

      const domainSelect = screen.getByLabelText(/Domain/);
      fireEvent.mouseDown(domainSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText(
            "agentic-systems - Multi-agent coordination and orchestration",
          ),
        );
      });

      // Wait for capabilities to appear
      await waitFor(() => {
        expect(screen.getByText("Agent Capabilities (4)")).toBeInTheDocument();
        expect(screen.getByText("Multi-agent coordination"))
          .toBeInTheDocument();
        expect(screen.getByText("Domain expertise application"))
          .toBeInTheDocument();
        expect(screen.getByText("Role-specific execution")).toBeInTheDocument();
        expect(screen.getByText("Quality validation")).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    test("displays test buttons for each capability", async () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      // Generate preview first
      const roleSelect = screen.getByLabelText(/Role/);
      fireEvent.mouseDown(roleSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText("researcher - Research and discovery specialist"),
        );
      });

      const domainSelect = screen.getByLabelText(/Domain/);
      fireEvent.mouseDown(domainSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText(
            "agentic-systems - Multi-agent coordination and orchestration",
          ),
        );
      });

      // Check for test buttons
      await waitFor(() => {
        const testButtons = screen.getAllByText("Test");
        expect(testButtons).toHaveLength(4); // One for each capability
      }, { timeout: 2000 });
    });

    test("shows testing progress when capability test is clicked", async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      // Generate preview
      const roleSelect = screen.getByLabelText(/Role/);
      fireEvent.mouseDown(roleSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText("researcher - Research and discovery specialist"),
        );
      });

      const domainSelect = screen.getByLabelText(/Domain/);
      fireEvent.mouseDown(domainSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText(
            "agentic-systems - Multi-agent coordination and orchestration",
          ),
        );
      });

      // Click first test button
      await waitFor(() => {
        const testButtons = screen.getAllByText("Test");
        user.click(testButtons[0]);
      }, { timeout: 2000 });

      // Should show testing progress
      await waitFor(() => {
        expect(screen.getByText(/Testing capability:/)).toBeInTheDocument();
      });
    });
  });

  describe("Agent Composition Workflow", () => {
    test("completes full composition workflow successfully", async () => {
      const user = userEvent.setup();

      // Mock window.alert to capture the success message
      const alertMock = jest.spyOn(window, "alert").mockImplementation(
        () => {},
      );

      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      // Fill out the form completely
      const roleSelect = screen.getByLabelText(/Role/);
      fireEvent.mouseDown(roleSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText("researcher - Research and discovery specialist"),
        );
      });

      const domainSelect = screen.getByLabelText(/Domain/);
      fireEvent.mouseDown(domainSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText(
            "agentic-systems - Multi-agent coordination and orchestration",
          ),
        );
      });

      const taskDescription = screen.getByLabelText(/Task Description/);
      await user.type(
        taskDescription,
        "Research multi-agent coordination patterns for distributed systems",
      );

      const maxTasks = screen.getByLabelText(/Max Concurrent Tasks/);
      await user.clear(maxTasks);
      await user.type(maxTasks, "5");

      const timeout = screen.getByLabelText(/Timeout/);
      await user.clear(timeout);
      await user.type(timeout, "600");

      // Submit the form
      const submitButton = screen.getByText("Compose Agent");
      await user.click(submitButton);

      // Should show success alert
      await waitFor(() => {
        expect(alertMock).toHaveBeenCalledWith(
          expect.stringContaining("Agent composed successfully!"),
        );
        expect(alertMock).toHaveBeenCalledWith(
          expect.stringContaining("researcher+agentic-systems"),
        );
      });

      alertMock.mockRestore();
    });
  });

  describe("Error Handling", () => {
    test("handles API errors gracefully", () => {
      (useRoles as jest.Mock).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error("Failed to load roles"),
      });

      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      // Should still render basic structure even with errors
      expect(screen.getByText("Agent Composer Studio")).toBeInTheDocument();
    });

    test("shows empty dropdowns when data is unavailable", () => {
      (useRoles as jest.Mock).mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      (useDomains as jest.Mock).mockReturnValue({
        data: [],
        isLoading: false,
        error: null,
      });

      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      const roleSelect = screen.getByLabelText(/Role/);
      const domainSelect = screen.getByLabelText(/Domain/);

      expect(roleSelect).toBeInTheDocument();
      expect(domainSelect).toBeInTheDocument();
    });
  });

  describe("Agentic Systems Patterns Validation", () => {
    test("validates multi-agent coordination patterns are exposed", async () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      // Generate preview for agentic-systems domain
      const roleSelect = screen.getByLabelText(/Role/);
      fireEvent.mouseDown(roleSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText("tester - Testing and validation specialist"),
        );
      });

      const domainSelect = screen.getByLabelText(/Domain/);
      fireEvent.mouseDown(domainSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText(
            "agentic-systems - Multi-agent coordination and orchestration",
          ),
        );
      });

      // Should show coordination capability
      await waitFor(() => {
        expect(screen.getByText("Multi-agent coordination"))
          .toBeInTheDocument();
        expect(
          screen.getByText(
            "Coordinate with other agents through structured communication",
          ),
        ).toBeInTheDocument();
      }, { timeout: 2000 });
    });

    test("validates role-domain coupling in composition string", async () => {
      render(
        <TestWrapper>
          <AgentComposerStudio />
        </TestWrapper>,
      );

      // Select specific role-domain combination
      const roleSelect = screen.getByLabelText(/Role/);
      fireEvent.mouseDown(roleSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText(
            "architect - System design and architecture specialist",
          ),
        );
      });

      const domainSelect = screen.getByLabelText(/Domain/);
      fireEvent.mouseDown(domainSelect);
      await waitFor(() => {
        fireEvent.click(
          screen.getByText(
            "memory-systems - Memory architecture and optimization",
          ),
        );
      });

      // Should show proper composition
      await waitFor(() => {
        expect(screen.getByText("architect+memory-systems"))
          .toBeInTheDocument();
      }, { timeout: 2000 });
    });
  });
});

// Signature: tester+agentic-systems [2025-01-15T12:45:00Z]
