/**
 * Task Flow Visualization Page
 * Interactive workflow diagrams for multi-agent tasks with real-time updates
 */

"use client";

import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControlLabel,
  Grid,
  Switch,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import {
  AccountTree as FlowIcon,
  Fullscreen as FullscreenIcon,
  FullscreenExit as ExitFullscreenIcon,
  Refresh as RefreshIcon,
  Timeline as TimelineIcon,
} from "@mui/icons-material";
import { TaskFlowVisualizer } from "@/components/feature/task-flow-visualizer";
import { CoordinationDashboard } from "@/components/feature/coordination-dashboard";
import { Agent, CoordinationMetrics, HookEvent, Plan } from "@/lib/types";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`flow-tabpanel-${index}`}
      aria-labelledby={`flow-tab-${index}`}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

export default function TaskFlowPage() {
  // State management
  const [activeTab, setActiveTab] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showCoordination, setShowCoordination] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Mock data for demonstration
  const [mockPlan] = useState<Plan>({
    id: "task-flow-demo",
    sessionId: "session-flow-123",
    nodes: [
      {
        id: "research-phase",
        phase: "Research & Discovery",
        status: "completed",
        agents: ["researcher-001", "analyst-001"],
        tasks: ["Market research", "User interviews", "Competitive analysis"],
        coordinationStrategy: "FAN_OUT_SYNTHESIZE",
        expectedArtifacts: [
          "research_report.md",
          "user_insights.md",
          "competitor_analysis.md",
        ],
        dependencies: [],
      },
      {
        id: "planning-phase",
        phase: "Strategic Planning",
        status: "running",
        agents: ["strategist-001", "architect-001"],
        tasks: [
          "System architecture design",
          "Implementation roadmap",
          "Resource planning",
        ],
        coordinationStrategy: "PIPELINE",
        expectedArtifacts: [
          "architecture_design.md",
          "roadmap.md",
          "resource_plan.md",
        ],
        dependencies: ["research-phase"],
      },
      {
        id: "development-phase",
        phase: "Development & Implementation",
        status: "pending",
        agents: ["implementer-001", "implementer-002", "tester-001"],
        tasks: [
          "Frontend development",
          "Backend API",
          "Database setup",
          "Testing framework",
        ],
        coordinationStrategy: "PARALLEL",
        expectedArtifacts: [
          "frontend_code",
          "backend_code",
          "database_schema",
          "test_suite",
        ],
        dependencies: ["planning-phase"],
      },
      {
        id: "validation-phase",
        phase: "Validation & Review",
        status: "pending",
        agents: ["reviewer-001", "tester-001", "critic-001"],
        tasks: [
          "Code review",
          "Integration testing",
          "Performance testing",
          "Security audit",
        ],
        coordinationStrategy: "FAN_OUT_SYNTHESIZE",
        expectedArtifacts: [
          "review_report.md",
          "test_results.md",
          "security_audit.md",
        ],
        dependencies: ["development-phase"],
      },
    ],
    edges: [
      { from: "research-phase", to: "planning-phase" },
      { from: "planning-phase", to: "development-phase" },
      { from: "development-phase", to: "validation-phase" },
    ],
  });

  const [mockAgents] = useState<Agent[]>([
    {
      id: "researcher-001",
      role: "researcher",
      domain: "market-analysis",
      status: "active",
      currentTask: "Market trend analysis for Q4 2024",
      duration: 1800000, // 30 minutes
      sessionId: "session-flow-123",
    },
    {
      id: "analyst-001",
      role: "analyst",
      domain: "user-experience",
      status: "active",
      currentTask: "User interview synthesis",
      duration: 1200000, // 20 minutes
      sessionId: "session-flow-123",
    },
    {
      id: "strategist-001",
      role: "strategist",
      domain: "business-planning",
      status: "active",
      currentTask: "Strategic roadmap development",
      duration: 600000, // 10 minutes
      sessionId: "session-flow-123",
    },
    {
      id: "architect-001",
      role: "architect",
      domain: "software-architecture",
      status: "active",
      currentTask: "System architecture design",
      duration: 900000, // 15 minutes
      sessionId: "session-flow-123",
    },
    {
      id: "implementer-001",
      role: "implementer",
      domain: "frontend-development",
      status: "idle",
      sessionId: "session-flow-123",
    },
    {
      id: "implementer-002",
      role: "implementer",
      domain: "backend-development",
      status: "idle",
      sessionId: "session-flow-123",
    },
  ]);

  const [mockEvents] = useState<HookEvent[]>([
    {
      id: "event-001",
      coordinationId: "task-flow-demo",
      agentId: "researcher-001",
      eventType: "post_edit",
      timestamp: new Date(Date.now() - 120000).toISOString(),
      metadata: { operation: "create", confidence: 0.95 },
      filePath: "/workspace/research/market_analysis.md",
    },
    {
      id: "event-002",
      coordinationId: "task-flow-demo",
      agentId: "strategist-001",
      eventType: "pre_command",
      timestamp: new Date(Date.now() - 180000).toISOString(),
      metadata: { operation: "plan_generation" },
      command: 'uv run khive plan "Strategic roadmap for Q1 2025"',
    },
    {
      id: "event-003",
      coordinationId: "task-flow-demo",
      agentId: "architect-001",
      eventType: "post_edit",
      timestamp: new Date(Date.now() - 240000).toISOString(),
      metadata: { operation: "update", version: "v2.1" },
      filePath: "/workspace/architecture/system_design.md",
    },
  ]);

  const [mockMetrics] = useState<CoordinationMetrics>({
    conflictsPrevented: 7,
    taskDeduplicationRate: 0.15,
    averageTaskCompletionTime: 1247.5,
    activeAgents: 4,
    activeSessions: 1,
  });

  // Auto-refresh mechanism
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      setRefreshing(true);
      // Simulate data refresh
      setTimeout(() => setRefreshing(false), 1000);
    }, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleRefresh = async () => {
    setRefreshing(true);
    // Simulate API refresh
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setRefreshing(false);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleNodeClick = (nodeId: string, nodeData: any) => {
    console.log("Node clicked:", nodeId, nodeData);
  };

  const handleNodeSelect = (node: any) => {
    console.log("Node selected:", node);
  };

  const activeAgentCount =
    mockAgents.filter((agent) => agent.status === "active").length;
  const completedPhases =
    mockPlan.nodes.filter((node) => node.status === "completed").length;
  const runningPhases =
    mockPlan.nodes.filter((node) => node.status === "running").length;

  return (
    <Box sx={{ p: 3, height: fullscreen ? "100vh" : "auto" }}>
      {/* Header */}
      <Box
        sx={{
          mb: 3,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <Box>
          <Typography
            variant="h4"
            component="h1"
            gutterBottom
            sx={{ fontWeight: 700 }}
          >
            Task Flow Visualizer
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Interactive workflow diagrams with real-time agent activity
          </Typography>
        </Box>

        <Box display="flex" alignItems="center" gap={2}>
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
            }
            label="Auto Refresh"
          />

          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </Button>

          <Button
            variant="outlined"
            startIcon={fullscreen ? <ExitFullscreenIcon /> : <FullscreenIcon />}
            onClick={() => setFullscreen(!fullscreen)}
          >
            {fullscreen ? "Exit Fullscreen" : "Fullscreen"}
          </Button>
        </Box>
      </Box>

      {/* Status Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography variant="h4" color="primary" sx={{ fontWeight: 700 }}>
                {mockPlan.nodes.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Phases
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography
                variant="h4"
                color="success.main"
                sx={{ fontWeight: 700 }}
              >
                {completedPhases}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Completed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography
                variant="h4"
                color="warning.main"
                sx={{ fontWeight: 700 }}
              >
                {runningPhases}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                In Progress
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: "center" }}>
              <Typography
                variant="h4"
                color="info.main"
                sx={{ fontWeight: 700 }}
              >
                {activeAgentCount}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Active Agents
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Content */}
      <Card variant="outlined">
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab
              label="Flow Diagram"
              icon={<FlowIcon />}
              iconPosition="start"
            />
            <Tab
              label="Coordination Monitor"
              icon={<TimelineIcon />}
              iconPosition="start"
            />
          </Tabs>
        </Box>

        <TabPanel value={activeTab} index={0}>
          <Box sx={{ p: 0 }}>
            <TaskFlowVisualizer
              plan={mockPlan}
              agents={mockAgents}
              events={mockEvents}
              autoLayout={true}
              showMiniMap={true}
              showControls={true}
              onNodeClick={handleNodeClick}
              onNodeSelect={handleNodeSelect}
            />
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          <Box sx={{ p: 2 }}>
            <CoordinationDashboard
              agents={mockAgents}
              events={mockEvents}
              metrics={mockMetrics}
              autoRefresh={autoRefresh}
              onDataRefresh={handleRefresh}
            />
          </Box>
        </TabPanel>
      </Card>

      {/* Footer Info */}
      <Alert severity="info" sx={{ mt: 2 }}>
        <Typography variant="body2">
          <strong>Task Flow Visualizer MVP:</strong>{" "}
          Interactive workflow diagrams showing real-time agent activity,
          coordination strategies, and task dependencies. Click on nodes for
          detailed information, use controls to navigate, and toggle agent
          activity highlighting.
        </Typography>
      </Alert>
    </Box>
  );
}
