/**
 * Agent Capability Tester Component
 * Basic capability testing interface for agent validation - the missing MVP piece
 * Implements agentic-systems testing patterns for agent verification
 */

import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Collapse,
  FormControlLabel,
  Grid,
  IconButton,
  LinearProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  CheckCircle as PassIcon,
  Error as FailIcon,
  ExpandLess as CollapseIcon,
  ExpandMore as ExpandIcon,
  PlayArrow as RunIcon,
  Refresh as RetryIcon,
  Schedule as PendingIcon,
  Settings as ConfigIcon,
  Visibility as ViewIcon,
} from "@mui/icons-material";

import type {
  AgentDefinition,
  TestResults,
  TestScenario,
} from "@/app/composer/page";

interface AgentCapabilityTesterProps {
  agentDefinition: AgentDefinition;
  onTestingStart: () => void;
  onTestingComplete: (results: TestResults) => void;
  isLoading: boolean;
}

// Generate test scenarios based on agent configuration
const generateTestScenarios = (
  agentDefinition: AgentDefinition,
): TestScenario[] => {
  const baseScenarios: TestScenario[] = [
    {
      id: "config_validation",
      name: "Configuration Validation",
      description: "Validate agent role+domain configuration is coherent",
      expectedOutput: "Agent configuration passes validation checks",
      testType: "validation",
      status: "pending",
    },
    {
      id: "capability_enumeration",
      name: "Capability Enumeration",
      description: "Enumerate agent capabilities based on role+domain",
      expectedOutput: "List of specific capabilities and tools available",
      testType: "capability",
      status: "pending",
    },
    {
      id: "task_understanding",
      name: "Task Understanding",
      description: "Validate agent understands the assigned task context",
      expectedOutput: "Clear task interpretation and approach outline",
      testType: "capability",
      status: "pending",
    },
  ];

  // Add capability-specific tests
  agentDefinition.expectedCapabilities.forEach((capability, index) => {
    baseScenarios.push({
      id: `capability_${index}`,
      name: `${capability} Test`,
      description: `Test specific capability: ${capability}`,
      expectedOutput: `Demonstration of ${capability} in context`,
      testType: "capability",
      status: "pending",
    });
  });

  // Add coordination strategy test
  baseScenarios.push({
    id: "coordination_strategy",
    name: "Coordination Strategy Test",
    description:
      `Test ${agentDefinition.coordinationStrategy} coordination pattern`,
    expectedOutput: "Proper coordination behavior demonstration",
    testType: "integration",
    status: "pending",
  });

  return baseScenarios;
};

export const AgentCapabilityTester: React.FC<AgentCapabilityTesterProps> = ({
  agentDefinition,
  onTestingStart,
  onTestingComplete,
  isLoading,
}) => {
  const [scenarios, setScenarios] = useState<TestScenario[]>([]);
  const [selectedScenarios, setSelectedScenarios] = useState<string[]>([]);
  const [currentTestIndex, setCurrentTestIndex] = useState(0);
  const [expandedScenario, setExpandedScenario] = useState<string | null>(null);
  const [customScenario, setCustomScenario] = useState("");
  const [showCustom, setShowCustom] = useState(false);

  // Initialize scenarios when agent definition changes
  useEffect(() => {
    const generatedScenarios = generateTestScenarios(agentDefinition);
    setScenarios(generatedScenarios);
    setSelectedScenarios(generatedScenarios.map((s) => s.id));
    setCurrentTestIndex(0);
  }, [agentDefinition]);

  // Mock test execution - in real implementation would call actual testing API
  const runMockTest = async (scenario: TestScenario): Promise<TestScenario> => {
    await new Promise((resolve) =>
      setTimeout(resolve, 1000 + Math.random() * 2000)
    );

    // Mock test results based on scenario type and agent configuration
    const passRate = scenario.testType === "validation"
      ? 0.9
      : scenario.testType === "capability"
      ? 0.8
      : 0.7;

    const passed = Math.random() < passRate;
    const executionTime = 500 + Math.random() * 1500;

    return {
      ...scenario,
      status: passed ? "passed" : "failed",
      result: passed
        ? `✅ ${scenario.expectedOutput}`
        : `❌ Failed to meet expected output: ${scenario.expectedOutput}`,
      executionTime: Math.round(executionTime),
    };
  };

  // Run all selected tests
  const handleRunTests = async () => {
    onTestingStart();

    const selectedTests = scenarios.filter((s) =>
      selectedScenarios.includes(s.id)
    );
    const testResults: TestScenario[] = [];

    // Update scenarios to show running state
    setScenarios((prev) =>
      prev.map((s) =>
        selectedScenarios.includes(s.id)
          ? { ...s, status: "pending" as const }
          : s
      )
    );

    // Run tests sequentially for better UX
    for (let i = 0; i < selectedTests.length; i++) {
      setCurrentTestIndex(i);

      // Mark current test as running
      setScenarios((prev) =>
        prev.map((s) =>
          s.id === selectedTests[i].id
            ? { ...s, status: "running" as const }
            : s
        )
      );

      const result = await runMockTest(selectedTests[i]);
      testResults.push(result);

      // Update with result
      setScenarios((prev) => prev.map((s) => s.id === result.id ? result : s));
    }

    // Calculate overall results
    const passedTests = testResults.filter((r) => r.status === "passed");
    const passRate = passedTests.length / testResults.length;
    const averageTime =
      testResults.reduce((acc, r) => acc + (r.executionTime || 0), 0) /
      testResults.length;

    // Generate capability score based on test results and agent configuration
    const capabilityScore = Math.round(
      (passRate * 0.6) * 100 +
        (agentDefinition.qualityGate === "critical"
          ? 20
          : agentDefinition.qualityGate === "thorough"
          ? 15
          : 10) +
        (testResults.length >= 5 ? 10 : 5),
    );

    // Generate recommendations
    const recommendations = [];
    if (passRate < 0.8) {
      recommendations.push(
        "Consider refining agent configuration - low pass rate detected",
      );
    }
    if (averageTime > 2000) {
      recommendations.push(
        "Performance optimization recommended - high execution time",
      );
    }
    if (agentDefinition.expectedCapabilities.length > 6) {
      recommendations.push(
        "Consider reducing capability scope for better focus",
      );
    }
    if (passRate >= 0.9) {
      recommendations.push(
        "Excellent performance - agent ready for deployment",
      );
    }

    const results: TestResults = {
      overall: passRate >= 0.8
        ? "passed"
        : passRate >= 0.6
        ? "partial"
        : "failed",
      scenarios: testResults,
      metrics: {
        passRate,
        averageExecutionTime: Math.round(averageTime),
        capabilityScore,
      },
      recommendations,
    };

    onTestingComplete(results);
  };

  // Toggle scenario selection
  const toggleScenarioSelection = (scenarioId: string) => {
    setSelectedScenarios((prev) =>
      prev.includes(scenarioId)
        ? prev.filter((id) => id !== scenarioId)
        : [...prev, scenarioId]
    );
  };

  // Add custom scenario
  const handleAddCustomScenario = () => {
    if (!customScenario.trim()) return;

    const newScenario: TestScenario = {
      id: `custom_${Date.now()}`,
      name: "Custom Test",
      description: customScenario,
      expectedOutput: "Custom validation criteria",
      testType: "capability",
      status: "pending",
    };

    setScenarios((prev) => [...prev, newScenario]);
    setSelectedScenarios((prev) => [...prev, newScenario.id]);
    setCustomScenario("");
    setShowCustom(false);
  };

  const getStatusIcon = (status: TestScenario["status"]) => {
    switch (status) {
      case "passed":
        return <PassIcon color="success" />;
      case "failed":
        return <FailIcon color="error" />;
      case "running":
        return <PendingIcon color="primary" />;
      default:
        return <PendingIcon color="disabled" />;
    }
  };

  const getStatusColor = (status: TestScenario["status"]) => {
    switch (status) {
      case "passed":
        return "success";
      case "failed":
        return "error";
      case "running":
        return "primary";
      default:
        return "default";
    }
  };

  return (
    <Box>
      {/* Testing Header */}
      <Box sx={{ mb: 3 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} md={8}>
            <Typography variant="subtitle1" gutterBottom>
              Agent Configuration Test Suite
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Validate agent capabilities for:{" "}
              <strong>{agentDefinition.role}+{agentDefinition.domain}</strong>
            </Typography>
          </Grid>
          <Grid item xs={12} md={4}>
            <Box display="flex" gap={1} justifyContent="flex-end">
              <Tooltip title="Configure test parameters">
                <IconButton onClick={() => setShowCustom(!showCustom)}>
                  <ConfigIcon />
                </IconButton>
              </Tooltip>
              <Button
                variant="contained"
                startIcon={<RunIcon />}
                onClick={handleRunTests}
                disabled={isLoading || selectedScenarios.length === 0}
                sx={{ minWidth: 120 }}
              >
                {isLoading ? "Testing..." : "Run Tests"}
              </Button>
            </Box>
          </Grid>
        </Grid>

        {/* Testing Progress */}
        {isLoading && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress
              variant="determinate"
              value={(currentTestIndex / selectedScenarios.length) * 100}
            />
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ mt: 0.5, display: "block" }}
            >
              Running test {currentTestIndex + 1} of{" "}
              {selectedScenarios.length}...
            </Typography>
          </Box>
        )}
      </Box>

      {/* Custom Test Scenario Input */}
      <Collapse in={showCustom}>
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              Add Custom Test Scenario
            </Typography>
            <Box display="flex" gap={2} alignItems="flex-end">
              <TextField
                fullWidth
                multiline
                rows={2}
                value={customScenario}
                onChange={(e) => setCustomScenario(e.target.value)}
                placeholder="Describe a custom test scenario for this agent..."
                variant="outlined"
                size="small"
              />
              <Button
                variant="outlined"
                onClick={handleAddCustomScenario}
                disabled={!customScenario.trim()}
              >
                Add Test
              </Button>
            </Box>
          </CardContent>
        </Card>
      </Collapse>

      {/* Test Scenarios */}
      <Card>
        <CardContent>
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            sx={{ mb: 2 }}
          >
            <Typography variant="h6">
              Test Scenarios ({selectedScenarios.length} selected)
            </Typography>
            <Stack direction="row" spacing={1}>
              <Button
                size="small"
                onClick={() => setSelectedScenarios(scenarios.map((s) => s.id))}
              >
                Select All
              </Button>
              <Button
                size="small"
                onClick={() => setSelectedScenarios([])}
              >
                Select None
              </Button>
            </Stack>
          </Box>

          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox" width={50}>Run</TableCell>
                  <TableCell width={50}>Status</TableCell>
                  <TableCell>Test Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell width={100}>Time (ms)</TableCell>
                  <TableCell width={50}>Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {scenarios.map((scenario) => (
                  <React.Fragment key={scenario.id}>
                    <TableRow hover>
                      <TableCell padding="checkbox">
                        <FormControlLabel
                          control={
                            <Checkbox
                              size="small"
                              checked={selectedScenarios.includes(scenario.id)}
                              onChange={() =>
                                toggleScenarioSelection(scenario.id)}
                            />
                          }
                          label=""
                        />
                      </TableCell>
                      <TableCell>
                        <Tooltip title={scenario.status}>
                          {getStatusIcon(scenario.status)}
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {scenario.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {scenario.description}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={scenario.testType}
                          size="small"
                          variant="outlined"
                          color={getStatusColor(
                            scenario.testType as any,
                          ) as any}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {scenario.executionTime || "-"}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() =>
                            setExpandedScenario(
                              expandedScenario === scenario.id
                                ? null
                                : scenario.id,
                            )}
                        >
                          {expandedScenario === scenario.id
                            ? <CollapseIcon />
                            : <ExpandIcon />}
                        </IconButton>
                      </TableCell>
                    </TableRow>

                    {/* Expanded Details */}
                    <TableRow>
                      <TableCell colSpan={6} sx={{ p: 0, border: 0 }}>
                        <Collapse in={expandedScenario === scenario.id}>
                          <Box sx={{ p: 2, backgroundColor: "grey.50" }}>
                            <Typography variant="subtitle2" gutterBottom>
                              Expected Output:
                            </Typography>
                            <Typography variant="body2" sx={{ mb: 1 }}>
                              {scenario.expectedOutput}
                            </Typography>

                            {scenario.result && (
                              <>
                                <Typography variant="subtitle2" gutterBottom>
                                  Test Result:
                                </Typography>
                                <Typography
                                  variant="body2"
                                  sx={{ fontFamily: "monospace" }}
                                >
                                  {scenario.result}
                                </Typography>
                              </>
                            )}
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {scenarios.length === 0 && (
            <Alert severity="info" sx={{ mt: 2 }}>
              No test scenarios generated. Please check agent configuration.
            </Alert>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};
