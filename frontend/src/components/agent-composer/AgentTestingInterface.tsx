/**
 * Agent Testing Interface - Basic Capability Testing
 * Architectural Pattern: Test Runner with Mock Scenarios
 */

"use client";

import React, { useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  alpha,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as PassIcon,
  Error as FailIcon,
  ExpandMore as ExpandIcon,
  Pending as PendingIcon,
  PlayArrow as RunIcon,
  Science as TestIcon,
} from "@mui/icons-material";

import type { AgentComposition } from "./AgentComposer";

interface TestScenario {
  id: string;
  name: string;
  description: string;
  expectedCapability: string;
  mockInput: string;
  expectedOutput: string;
  difficulty: "basic" | "intermediate" | "advanced";
}

interface TestResult {
  scenarioId: string;
  status: "pending" | "running" | "passed" | "failed";
  score: number;
  feedback: string;
  executionTime: number;
}

interface AgentTestingInterfaceProps {
  composition: AgentComposition;
  onTestComplete: (
    results: { passed: number; failed: number; score: number },
  ) => void;
}

export function AgentTestingInterface(
  { composition, onTestComplete }: AgentTestingInterfaceProps,
) {
  const theme = useTheme();
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>([]);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [customTest, setCustomTest] = useState({
    task: "",
    expectedResult: "",
  });

  // Generate test scenarios based on agent composition
  const generateTestScenarios = (): TestScenario[] => {
    if (!composition.role || !composition.domain) return [];

    const scenarios: TestScenario[] = [];
    const roleId = composition.role.id;
    const domainId = composition.domain.id;

    // Role-based scenarios
    if (roleId === "architect") {
      scenarios.push({
        id: "arch_basic",
        name: "System Design",
        description: "Design a simple component architecture",
        expectedCapability: "system_design",
        mockInput: "Create architecture for a user authentication system",
        expectedOutput: "Component diagram with clear interfaces",
        difficulty: "basic",
      });
      scenarios.push({
        id: "arch_advanced",
        name: "Complex Architecture",
        description: "Design scalable microservices architecture",
        expectedCapability: "advanced_architecture",
        mockInput: "Design architecture for e-commerce platform with 1M+ users",
        expectedOutput:
          "Detailed architectural blueprint with scalability patterns",
        difficulty: "advanced",
      });
    }

    if (roleId === "implementer") {
      scenarios.push({
        id: "impl_basic",
        name: "Component Implementation",
        description: "Implement a simple UI component",
        expectedCapability: "component_implementation",
        mockInput: "Implement a reusable button component in React",
        expectedOutput: "Working React component with TypeScript",
        difficulty: "basic",
      });
    }

    if (roleId === "tester") {
      scenarios.push({
        id: "test_basic",
        name: "Test Case Generation",
        description: "Generate test cases for a function",
        expectedCapability: "test_generation",
        mockInput: "Create tests for user input validation function",
        expectedOutput: "Comprehensive test suite with edge cases",
        difficulty: "basic",
      });
    }

    // Domain-specific scenarios
    if (domainId.includes("frontend")) {
      scenarios.push({
        id: "frontend_responsive",
        name: "Responsive Design",
        description: "Create responsive layout",
        expectedCapability: "responsive_design",
        mockInput: "Make dashboard layout responsive for mobile devices",
        expectedOutput: "CSS/component changes for mobile compatibility",
        difficulty: "intermediate",
      });
    }

    if (domainId.includes("backend")) {
      scenarios.push({
        id: "backend_api",
        name: "API Design",
        description: "Design RESTful API endpoints",
        expectedCapability: "api_design",
        mockInput: "Design API for blog post management system",
        expectedOutput: "RESTful endpoints with proper HTTP methods",
        difficulty: "intermediate",
      });
    }

    // Universal scenarios
    scenarios.push({
      id: "problem_solving",
      name: "Problem Solving",
      description: "General problem-solving capability",
      expectedCapability: "problem_solving",
      mockInput: "How would you approach debugging a performance issue?",
      expectedOutput: "Systematic debugging approach with clear steps",
      difficulty: "basic",
    });

    return scenarios;
  };

  const testScenarios = generateTestScenarios();

  // Handle scenario selection
  const handleScenarioToggle = (scenarioId: string) => {
    setSelectedScenarios((prev) =>
      prev.includes(scenarioId)
        ? prev.filter((id) => id !== scenarioId)
        : [...prev, scenarioId]
    );
  };

  // Simulate test execution (MVP implementation)
  const runTests = async () => {
    if (selectedScenarios.length === 0) return;

    setIsRunning(true);
    const results: TestResult[] = [];

    // Initialize pending results
    selectedScenarios.forEach((scenarioId) => {
      results.push({
        scenarioId,
        status: "pending",
        score: 0,
        feedback: "Waiting to start...",
        executionTime: 0,
      });
    });
    setTestResults([...results]);

    // Simulate test execution with delays
    for (let i = 0; i < selectedScenarios.length; i++) {
      const scenarioId = selectedScenarios[i];
      const scenario = testScenarios.find((s) => s.id === scenarioId)!;

      // Update to running status
      results[i] = {
        ...results[i],
        status: "running",
        feedback: "Executing test...",
      };
      setTestResults([...results]);

      // Simulate execution time
      await new Promise((resolve) =>
        setTimeout(resolve, 2000 + Math.random() * 3000)
      );

      // Mock test results based on composition strength
      const capabilities = composition.capabilities || [];
      const hasRelevantCapability = capabilities.some((cap) =>
        cap.toLowerCase().includes(scenario.expectedCapability.toLowerCase()) ||
        scenario.expectedCapability.toLowerCase().includes(cap.toLowerCase())
      );

      const baseSuccessRate = hasRelevantCapability ? 0.85 : 0.6;
      const difficultyMultiplier = scenario.difficulty === "basic"
        ? 1.0
        : scenario.difficulty === "intermediate"
        ? 0.8
        : 0.6;
      const successProbability = baseSuccessRate * difficultyMultiplier;

      const passed = Math.random() < successProbability;
      const score = passed
        ? Math.round(70 + Math.random() * 30)
        : Math.round(20 + Math.random() * 40);

      results[i] = {
        ...results[i],
        status: passed ? "passed" : "failed",
        score,
        feedback: passed
          ? `Test passed successfully. Agent demonstrated good ${scenario.expectedCapability} capabilities.`
          : `Test failed. Agent struggled with ${scenario.expectedCapability} requirements. Consider additional training or different role/domain combination.`,
        executionTime: Math.round(2000 + Math.random() * 3000),
      };
      setTestResults([...results]);
    }

    setIsRunning(false);

    // Calculate overall results
    const passed = results.filter((r) => r.status === "passed").length;
    const failed = results.filter((r) => r.status === "failed").length;
    const averageScore = results.reduce((sum, r) => sum + r.score, 0) /
      results.length;

    onTestComplete({ passed, failed, score: Math.round(averageScore) });
  };

  // Run custom test
  const runCustomTest = async () => {
    if (!customTest.task.trim()) return;

    const customResult: TestResult = {
      scenarioId: "custom",
      status: "running",
      score: 0,
      feedback: "Executing custom test...",
      executionTime: 0,
    };

    setTestResults((prev) => [...prev, customResult]);
    setIsRunning(true);

    // Simulate custom test execution
    await new Promise((resolve) => setTimeout(resolve, 3000));

    const passed = Math.random() > 0.3; // 70% success rate for custom tests
    const score = passed
      ? Math.round(60 + Math.random() * 40)
      : Math.round(30 + Math.random() * 40);

    const updatedResult: TestResult = {
      scenarioId: "custom",
      status: passed ? "passed" : "failed",
      score,
      feedback: passed
        ? "Custom test completed successfully. Agent handled the task appropriately."
        : "Custom test encountered issues. Agent may need additional capabilities for this task.",
      executionTime: 3000,
    };

    setTestResults((prev) =>
      prev.map((r) => r.scenarioId === "custom" ? updatedResult : r)
    );
    setIsRunning(false);
  };

  const overallStats = testResults.length > 0
    ? {
      passed: testResults.filter((r) => r.status === "passed").length,
      failed: testResults.filter((r) => r.status === "failed").length,
      pending: testResults.filter((r) =>
        r.status === "pending" || r.status === "running"
      ).length,
      averageScore: testResults.filter((r) =>
            r.status !== "pending" && r.status !== "running"
          )
            .reduce((sum, r) =>
              sum + r.score, 0) /
          testResults.filter((r) =>
            r.status !== "pending" && r.status !== "running"
          ).length || 0,
    }
    : null;

  if (!composition.role || !composition.domain) {
    return (
      <Box textAlign="center" py={8}>
        <TestIcon sx={{ fontSize: 48, color: "text.disabled", mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Complete Agent Definition
        </Typography>
        <Typography variant="body2" color="text.disabled">
          Testing interface will be available after defining role and domain
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        Agent Testing Interface
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        Test your composed agent's capabilities with predefined scenarios or
        custom tasks
      </Typography>

      <Grid container spacing={4}>
        {/* Test Results Overview */}
        {overallStats && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Test Results Overview
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={3}>
                    <Paper
                      sx={{
                        p: 2,
                        textAlign: "center",
                        bgcolor: alpha(theme.palette.success.main, 0.1),
                      }}
                    >
                      <Typography variant="h4" color="success.main">
                        {overallStats.passed}
                      </Typography>
                      <Typography variant="caption">Passed</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Paper
                      sx={{
                        p: 2,
                        textAlign: "center",
                        bgcolor: alpha(theme.palette.error.main, 0.1),
                      }}
                    >
                      <Typography variant="h4" color="error.main">
                        {overallStats.failed}
                      </Typography>
                      <Typography variant="caption">Failed</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Paper
                      sx={{
                        p: 2,
                        textAlign: "center",
                        bgcolor: alpha(theme.palette.warning.main, 0.1),
                      }}
                    >
                      <Typography variant="h4" color="warning.main">
                        {overallStats.pending}
                      </Typography>
                      <Typography variant="caption">Pending</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Paper
                      sx={{
                        p: 2,
                        textAlign: "center",
                        bgcolor: alpha(theme.palette.primary.main, 0.1),
                      }}
                    >
                      <Typography variant="h4" color="primary.main">
                        {Math.round(overallStats.averageScore) || 0}
                      </Typography>
                      <Typography variant="caption">Avg Score</Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Test Scenarios */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Available Test Scenarios
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Select scenarios to test your agent's capabilities
              </Typography>

              <Stack spacing={1}>
                {testScenarios.map((scenario) => {
                  const result = testResults.find((r) =>
                    r.scenarioId === scenario.id
                  );
                  const isSelected = selectedScenarios.includes(scenario.id);

                  return (
                    <Accordion
                      key={scenario.id}
                      expanded={isSelected}
                      onChange={() => handleScenarioToggle(scenario.id)}
                      disabled={isRunning}
                    >
                      <AccordionSummary expandIcon={<ExpandIcon />}>
                        <Stack
                          direction="row"
                          alignItems="center"
                          spacing={2}
                          sx={{ width: "100%" }}
                        >
                          <Typography variant="body1" fontWeight="medium">
                            {scenario.name}
                          </Typography>
                          <Chip
                            size="small"
                            label={scenario.difficulty}
                            color={scenario.difficulty === "basic"
                              ? "success"
                              : scenario.difficulty === "intermediate"
                              ? "warning"
                              : "error"}
                            variant="outlined"
                          />
                          {result && (
                            <Stack
                              direction="row"
                              alignItems="center"
                              spacing={1}
                            >
                              {result.status === "running" && (
                                <CircularProgress size={16} />
                              )}
                              {result.status === "passed" && (
                                <PassIcon color="success" fontSize="small" />
                              )}
                              {result.status === "failed" && (
                                <FailIcon color="error" fontSize="small" />
                              )}
                              {result.status === "pending" && (
                                <PendingIcon color="warning" fontSize="small" />
                              )}
                              {result.status !== "pending" &&
                                result.status !== "running" && (
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                >
                                  Score: {result.score}
                                </Typography>
                              )}
                            </Stack>
                          )}
                        </Stack>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Stack spacing={2}>
                          <Typography variant="body2" color="text.secondary">
                            {scenario.description}
                          </Typography>
                          <Box>
                            <Typography variant="caption" fontWeight="medium">
                              Expected Capability:
                            </Typography>
                            <Typography variant="body2" sx={{ ml: 1 }}>
                              {scenario.expectedCapability}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" fontWeight="medium">
                              Mock Input:
                            </Typography>
                            <Typography
                              variant="body2"
                              sx={{ ml: 1, fontStyle: "italic" }}
                            >
                              "{scenario.mockInput}"
                            </Typography>
                          </Box>
                          {result && result.feedback && (
                            <Alert
                              severity={result.status === "passed"
                                ? "success"
                                : "error"}
                            >
                              {result.feedback}
                            </Alert>
                          )}
                        </Stack>
                      </AccordionDetails>
                    </Accordion>
                  );
                })}
              </Stack>

              <Box sx={{ mt: 3 }}>
                <Button
                  variant="contained"
                  onClick={runTests}
                  disabled={selectedScenarios.length === 0 || isRunning}
                  startIcon={isRunning
                    ? <CircularProgress size={16} />
                    : <RunIcon />}
                  fullWidth
                >
                  {isRunning
                    ? "Running Tests..."
                    : `Run Selected Tests (${selectedScenarios.length})`}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Custom Test */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Custom Test</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Create your own test scenario
              </Typography>

              <Stack spacing={3}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Custom Task"
                  value={customTest.task}
                  onChange={(e) =>
                    setCustomTest((prev) => ({
                      ...prev,
                      task: e.target.value,
                    }))}
                  placeholder="Describe a task you want the agent to perform..."
                  disabled={isRunning}
                />

                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label="Expected Result"
                  value={customTest.expectedResult}
                  onChange={(e) =>
                    setCustomTest((prev) => ({
                      ...prev,
                      expectedResult: e.target.value,
                    }))}
                  placeholder="What should the agent produce or accomplish?"
                  disabled={isRunning}
                />

                <Button
                  variant="outlined"
                  onClick={runCustomTest}
                  disabled={!customTest.task.trim() || isRunning}
                  startIcon={<RunIcon />}
                  fullWidth
                >
                  Run Custom Test
                </Button>

                {testResults.find((r) => r.scenarioId === "custom") && (
                  <Alert
                    severity={testResults.find((r) => r.scenarioId === "custom")
                        ?.status === "passed"
                      ? "success"
                      : "error"}
                  >
                    {testResults.find((r) => r.scenarioId === "custom")
                      ?.feedback}
                  </Alert>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default AgentTestingInterface;
