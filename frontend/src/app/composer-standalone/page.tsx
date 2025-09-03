/**
 * Agent Composer Studio MVP
 * Main interface for composing agents with role/domain and testing capabilities
 * Implements agentic-systems patterns for optimal agent configuration
 */

"use client";

import React, { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Grid,
  IconButton,
  Stack,
  Step,
  StepContent,
  StepLabel,
  Stepper,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  CheckCircle as ValidateIcon,
  Info as InfoIcon,
  Launch as DeployIcon,
  PlayArrow as TestIcon,
  Psychology as AgentIcon,
  Refresh as ResetIcon,
} from "@mui/icons-material";

import { AgentDefinitionForm } from "@/components/composer/agent-definition-form";
import { AgentCapabilityTester } from "@/components/composer/agent-capability-tester";
import { AgentTestResults } from "@/components/composer/agent-test-results";

// Agent composition steps for MVP workflow
const composerSteps = [
  {
    label: "Define Agent",
    description: "Configure role, domain, and basic capabilities",
  },
  {
    label: "Test Capabilities",
    description: "Validate agent configuration with basic tests",
  },
  {
    label: "Review & Deploy",
    description: "Review test results and deploy if satisfactory",
  },
];

// Agent definition interface for the composer
export interface AgentDefinition {
  role: string;
  domain: string;
  taskContext: string;
  expectedCapabilities: string[];
  qualityGate: "basic" | "thorough" | "critical";
  coordinationStrategy: "FAN_OUT_SYNTHESIZE" | "PIPELINE" | "PARALLEL";
  testScenarios?: TestScenario[];
}

// Test scenario interface for capability testing
export interface TestScenario {
  id: string;
  name: string;
  description: string;
  expectedOutput: string;
  testType: "validation" | "capability" | "integration";
  status?: "pending" | "running" | "passed" | "failed";
  result?: string;
  executionTime?: number;
}

// Test results interface
export interface TestResults {
  overall: "passed" | "failed" | "partial";
  scenarios: TestScenario[];
  metrics: {
    passRate: number;
    averageExecutionTime: number;
    capabilityScore: number;
  };
  recommendations: string[];
}

export default function AgentComposerStudio() {
  // Stepper state management
  const [activeStep, setActiveStep] = useState(0);
  const [completed, setCompleted] = useState<Set<number>>(new Set());

  // Agent composition state
  const [agentDefinition, setAgentDefinition] = useState<
    AgentDefinition | null
  >(null);
  const [testResults, setTestResults] = useState<TestResults | null>(null);
  const [isTestingCapabilities, setIsTestingCapabilities] = useState(false);

  // Step navigation handlers
  const handleNext = () => {
    if (activeStep < composerSteps.length - 1) {
      setActiveStep((prevStep) => prevStep + 1);
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep((prevStep) => prevStep - 1);
    }
  };

  const handleStepComplete = (stepIndex: number) => {
    setCompleted((prev) => new Set(prev).add(stepIndex));
    handleNext();
  };

  const handleReset = () => {
    setActiveStep(0);
    setCompleted(new Set());
    setAgentDefinition(null);
    setTestResults(null);
    setIsTestingCapabilities(false);
  };

  // Agent definition completion handler
  const handleAgentDefined = (definition: AgentDefinition) => {
    setAgentDefinition(definition);
    handleStepComplete(0);
  };

  // Capability testing completion handler
  const handleTestingComplete = (results: TestResults) => {
    setTestResults(results);
    setIsTestingCapabilities(false);
    handleStepComplete(1);
  };

  // Start capability testing
  const handleStartTesting = () => {
    setIsTestingCapabilities(true);
  };

  // Deploy agent handler
  const handleDeployAgent = () => {
    if (agentDefinition && testResults) {
      console.log("Deploying agent with configuration:", {
        definition: agentDefinition,
        testResults: testResults,
      });
      // TODO: Integrate with actual deployment API
      alert(
        "Agent deployed successfully! (MVP - would integrate with real deployment)",
      );
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box
        sx={{
          mb: 4,
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
            <Box
              component="span"
              sx={{ display: "flex", alignItems: "center", gap: 2 }}
            >
              <AgentIcon color="primary" fontSize="large" />
              Agent Composer Studio
            </Box>
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Design, test, and deploy specialized agents with role+domain
            configuration
          </Typography>
        </Box>

        <Stack direction="row" spacing={2}>
          <Tooltip title="Reset composer workflow">
            <IconButton onClick={handleReset} color="default">
              <ResetIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Agent composition follows Role + Domain pattern for optimal capability matching">
            <IconButton size="small">
              <InfoIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* Agent Pattern Information */}
      <Alert severity="info" sx={{ mb: 4 }}>
        <Typography variant="subtitle2" gutterBottom>
          🎯 Agent = Role + Domain Pattern
        </Typography>
        <Typography variant="body2">
          Every agent is composed of a <strong>behavioral role</strong>{" "}
          (researcher, analyst, architect, etc.) and{" "}
          <strong>specialized domain knowledge</strong>{" "}
          (memory-systems, distributed-systems, etc.). This MVP allows you to
          define, test, and deploy agents following this proven pattern.
        </Typography>
      </Alert>

      <Grid container spacing={4}>
        {/* Stepper Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardHeader
              title="Composition Workflow"
              subheader="Step-by-step agent creation"
            />
            <CardContent>
              <Stepper activeStep={activeStep} orientation="vertical">
                {composerSteps.map((step, index) => (
                  <Step key={step.label} completed={completed.has(index)}>
                    <StepLabel>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="subtitle2">
                          {step.label}
                        </Typography>
                        {completed.has(index) && (
                          <ValidateIcon color="success" fontSize="small" />
                        )}
                      </Box>
                    </StepLabel>
                    <StepContent>
                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mb: 2 }}
                      >
                        {step.description}
                      </Typography>
                    </StepContent>
                  </Step>
                ))}
              </Stepper>

              {/* Progress Summary */}
              {agentDefinition && (
                <Box
                  sx={{
                    mt: 3,
                    p: 2,
                    backgroundColor: "grey.50",
                    borderRadius: 1,
                  }}
                >
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    gutterBottom
                  >
                    Current Agent Configuration
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                    <Chip
                      label={agentDefinition.role}
                      size="small"
                      variant="outlined"
                      color="primary"
                    />
                    <Chip
                      label={agentDefinition.domain}
                      size="small"
                      variant="outlined"
                      color="secondary"
                    />
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    Quality Gate: {agentDefinition.qualityGate}
                  </Typography>
                </Box>
              )}

              {/* Test Results Summary */}
              {testResults && (
                <Box
                  sx={{
                    mt: 2,
                    p: 2,
                    backgroundColor: "grey.50",
                    borderRadius: 1,
                  }}
                >
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    gutterBottom
                  >
                    Test Results Summary
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                    <Chip
                      label={`${testResults.metrics.passRate * 100}% Pass Rate`}
                      size="small"
                      color={testResults.overall === "passed"
                        ? "success"
                        : "warning"}
                    />
                    <Chip
                      label={`${testResults.metrics.capabilityScore}/100 Score`}
                      size="small"
                      variant="outlined"
                    />
                  </Stack>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Main Content Panel */}
        <Grid item xs={12} md={8}>
          <Card sx={{ minHeight: 600 }}>
            <CardContent sx={{ p: 0 }}>
              {/* Step 1: Agent Definition */}
              {activeStep === 0 && (
                <Box sx={{ p: 3 }}>
                  <Typography
                    variant="h6"
                    gutterBottom
                    sx={{ display: "flex", alignItems: "center", gap: 1 }}
                  >
                    <AgentIcon color="primary" />
                    Define Agent Configuration
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 3 }}
                  >
                    Configure the agent's role, domain expertise, and basic
                    parameters.
                  </Typography>

                  <AgentDefinitionForm
                    onAgentDefined={handleAgentDefined}
                    initialData={agentDefinition}
                  />
                </Box>
              )}

              {/* Step 2: Capability Testing */}
              {activeStep === 1 && agentDefinition && (
                <Box sx={{ p: 3 }}>
                  <Typography
                    variant="h6"
                    gutterBottom
                    sx={{ display: "flex", alignItems: "center", gap: 1 }}
                  >
                    <TestIcon color="primary" />
                    Test Agent Capabilities
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 3 }}
                  >
                    Validate the agent configuration with basic capability
                    tests.
                  </Typography>

                  <AgentCapabilityTester
                    agentDefinition={agentDefinition}
                    onTestingStart={handleStartTesting}
                    onTestingComplete={handleTestingComplete}
                    isLoading={isTestingCapabilities}
                  />
                </Box>
              )}

              {/* Step 3: Review & Deploy */}
              {activeStep === 2 && agentDefinition && testResults && (
                <Box sx={{ p: 3 }}>
                  <Typography
                    variant="h6"
                    gutterBottom
                    sx={{ display: "flex", alignItems: "center", gap: 1 }}
                  >
                    <ValidateIcon color="success" />
                    Review & Deploy
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mb: 3 }}
                  >
                    Review test results and deploy your agent if all validations
                    pass.
                  </Typography>

                  <AgentTestResults
                    testResults={testResults}
                    agentDefinition={agentDefinition}
                  />

                  <Box
                    sx={{
                      mt: 4,
                      display: "flex",
                      gap: 2,
                      justifyContent: "space-between",
                    }}
                  >
                    <Button variant="outlined" onClick={handleBack}>
                      Back to Testing
                    </Button>

                    <Stack direction="row" spacing={2}>
                      <Button
                        variant="outlined"
                        onClick={() =>
                          setActiveStep(1)}
                        startIcon={<TestIcon />}
                      >
                        Re-test
                      </Button>
                      <Button
                        variant="contained"
                        onClick={handleDeployAgent}
                        startIcon={<DeployIcon />}
                        disabled={testResults.overall === "failed"}
                      >
                        Deploy Agent
                      </Button>
                    </Stack>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
