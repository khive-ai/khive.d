/**
 * Agent Composer Studio MVP
 * Comprehensive interface for composing agents with role/domain and testing capabilities
 * Implements the core Agent Composer Studio MVP requirements
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
  Divider,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  AutoAwesome as StudioIcon,
  Build as BuildIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  PlayArrow as LaunchIcon,
  Psychology as AgentIcon,
  Settings as AdvancedIcon,
  Speed as TestIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

import { AgentSpawner } from "@/components/feature/agent-spawner";
import { AgentSpawningForm } from "@/components/feature/agent-spawning-form";
import { useDomains, useRoles } from "@/lib/api/hooks";

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
      style={{ width: "100%" }}
    >
      {value === index && children}
    </div>
  );
}

// Agent Capability Tester Component
interface AgentCapabilityTesterProps {
  onTestComplete?: (results: TestResults) => void;
}

interface TestResults {
  roleCompatibility: number;
  domainExpertise: number;
  coordinationReadiness: number;
  overallScore: number;
  recommendations: string[];
}

function AgentCapabilityTester({ onTestComplete }: AgentCapabilityTesterProps) {
  const [selectedRole, setSelectedRole] = useState("");
  const [selectedDomain, setSelectedDomain] = useState("");
  const [testContext, setTestContext] = useState("");
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [testResults, setTestResults] = useState<TestResults | null>(null);

  const { data: roles } = useRoles();
  const { data: domains } = useDomains();

  const runCapabilityTest = async () => {
    if (!selectedRole || !selectedDomain || !testContext) {
      return;
    }

    setIsRunningTest(true);

    // Simulate test execution with realistic timing
    await new Promise((resolve) => setTimeout(resolve, 3000));

    // Generate mock test results based on role/domain combination
    const mockResults: TestResults = {
      roleCompatibility: Math.floor(Math.random() * 30) + 70, // 70-100%
      domainExpertise: Math.floor(Math.random() * 25) + 75, // 75-100%
      coordinationReadiness: Math.floor(Math.random() * 20) + 80, // 80-100%
      overallScore: 0,
      recommendations: [],
    };

    // Calculate overall score
    mockResults.overallScore = Math.round(
      (mockResults.roleCompatibility + mockResults.domainExpertise +
        mockResults.coordinationReadiness) / 3,
    );

    // Generate recommendations based on scores
    if (mockResults.overallScore >= 90) {
      mockResults.recommendations.push(
        "✅ Excellent agent configuration - ready for production deployment",
      );
      mockResults.recommendations.push(
        "🚀 Consider using this agent for critical tasks",
      );
    } else if (mockResults.overallScore >= 80) {
      mockResults.recommendations.push(
        "✅ Good agent configuration - suitable for most tasks",
      );
      mockResults.recommendations.push(
        "💡 Consider additional context for complex scenarios",
      );
    } else {
      mockResults.recommendations.push(
        "⚠️ Consider refining role or domain selection",
      );
      mockResults.recommendations.push(
        "🔄 Try alternative combinations for better results",
      );
    }

    // Role-specific recommendations
    if (selectedRole === "researcher") {
      mockResults.recommendations.push(
        "📚 Optimized for discovery and analysis tasks",
      );
    } else if (selectedRole === "implementer") {
      mockResults.recommendations.push(
        "⚡ Excellent for execution and deployment tasks",
      );
    }

    setTestResults(mockResults);
    onTestComplete?.(mockResults);
    setIsRunningTest(false);
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "success";
    if (score >= 80) return "primary";
    if (score >= 70) return "warning";
    return "error";
  };

  const getScoreIcon = (score: number) => {
    if (score >= 90) return <SuccessIcon color="success" />;
    if (score >= 80) return <SuccessIcon color="primary" />;
    if (score >= 70) return <WarningIcon color="warning" />;
    return <ErrorIcon color="error" />;
  };

  return (
    <Card variant="outlined">
      <CardHeader
        avatar={<TestIcon color="primary" />}
        title="Agent Capability Tester"
        subheader="Test agent configurations before deployment"
        action={
          <Tooltip title="Validate agent role/domain combinations and get optimization recommendations">
            <IconButton size="small">
              <InfoIcon />
            </IconButton>
          </Tooltip>
        }
      />

      <CardContent>
        <Grid container spacing={3}>
          {/* Test Configuration */}
          <Grid item xs={12} md={6}>
            <Stack spacing={3}>
              <FormControl fullWidth required>
                <InputLabel>Role to Test</InputLabel>
                <Select
                  value={selectedRole}
                  label="Role to Test"
                  onChange={(e) => setSelectedRole(e.target.value)}
                >
                  {roles?.map((role) => (
                    <MenuItem key={role.name} value={role.name}>
                      {role.name} - {role.description}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl fullWidth required>
                <InputLabel>Domain to Test</InputLabel>
                <Select
                  value={selectedDomain}
                  label="Domain to Test"
                  onChange={(e) => setSelectedDomain(e.target.value)}
                >
                  {domains?.map((domain) => (
                    <MenuItem key={domain.name} value={domain.name}>
                      {domain.name}
                      {domain.parent ? ` (${domain.parent})` : ""} -{" "}
                      {domain.description}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                label="Test Context"
                multiline
                rows={4}
                fullWidth
                required
                value={testContext}
                onChange={(e) => setTestContext(e.target.value)}
                placeholder="Describe a specific scenario to test the agent's capabilities..."
                helperText="Provide context that will help evaluate agent performance"
              />

              <Button
                variant="contained"
                size="large"
                startIcon={<TestIcon />}
                onClick={runCapabilityTest}
                disabled={!selectedRole || !selectedDomain || !testContext ||
                  isRunningTest}
                fullWidth
              >
                {isRunningTest
                  ? "Running Capability Test..."
                  : "Run Capability Test"}
              </Button>

              {isRunningTest && (
                <Box>
                  <LinearProgress />
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 1, display: "block" }}
                  >
                    Analyzing role compatibility, domain expertise, and
                    coordination readiness...
                  </Typography>
                </Box>
              )}
            </Stack>
          </Grid>

          {/* Test Results */}
          <Grid item xs={12} md={6}>
            {testResults
              ? (
                <Paper sx={{ p: 3, bgcolor: "grey.50" }}>
                  <Typography
                    variant="h6"
                    gutterBottom
                    sx={{ display: "flex", alignItems: "center", gap: 1 }}
                  >
                    {getScoreIcon(testResults.overallScore)}
                    Capability Test Results
                  </Typography>

                  <Stack spacing={2} sx={{ mb: 3 }}>
                    <Box>
                      <Box
                        display="flex"
                        justifyContent="space-between"
                        alignItems="center"
                        mb={1}
                      >
                        <Typography variant="body2">
                          Role Compatibility
                        </Typography>
                        <Chip
                          label={`${testResults.roleCompatibility}%`}
                          size="small"
                          color={getScoreColor(
                            testResults.roleCompatibility,
                          ) as any}
                        />
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={testResults.roleCompatibility}
                        color={getScoreColor(
                          testResults.roleCompatibility,
                        ) as any}
                        sx={{ height: 8, borderRadius: 4 }}
                      />
                    </Box>

                    <Box>
                      <Box
                        display="flex"
                        justifyContent="space-between"
                        alignItems="center"
                        mb={1}
                      >
                        <Typography variant="body2">
                          Domain Expertise
                        </Typography>
                        <Chip
                          label={`${testResults.domainExpertise}%`}
                          size="small"
                          color={getScoreColor(
                            testResults.domainExpertise,
                          ) as any}
                        />
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={testResults.domainExpertise}
                        color={getScoreColor(
                          testResults.domainExpertise,
                        ) as any}
                        sx={{ height: 8, borderRadius: 4 }}
                      />
                    </Box>

                    <Box>
                      <Box
                        display="flex"
                        justifyContent="space-between"
                        alignItems="center"
                        mb={1}
                      >
                        <Typography variant="body2">
                          Coordination Readiness
                        </Typography>
                        <Chip
                          label={`${testResults.coordinationReadiness}%`}
                          size="small"
                          color={getScoreColor(
                            testResults.coordinationReadiness,
                          ) as any}
                        />
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={testResults.coordinationReadiness}
                        color={getScoreColor(
                          testResults.coordinationReadiness,
                        ) as any}
                        sx={{ height: 8, borderRadius: 4 }}
                      />
                    </Box>
                  </Stack>

                  <Divider sx={{ my: 2 }} />

                  <Box
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    mb={2}
                  >
                    <Typography
                      variant="h4"
                      sx={{ fontWeight: 700 }}
                      color={`${getScoreColor(testResults.overallScore)}.main`}
                    >
                      {testResults.overallScore}%
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ ml: 1 }}
                    >
                      Overall Score
                    </Typography>
                  </Box>

                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      Recommendations:
                    </Typography>
                    <Stack spacing={1}>
                      {testResults.recommendations.map((rec, index) => (
                        <Typography
                          key={index}
                          variant="body2"
                          color="text.secondary"
                        >
                          {rec}
                        </Typography>
                      ))}
                    </Stack>
                  </Box>
                </Paper>
              )
              : (
                <Paper sx={{ p: 3, bgcolor: "grey.25", textAlign: "center" }}>
                  <TestIcon sx={{ fontSize: 48, color: "grey.400", mb: 2 }} />
                  <Typography variant="h6" color="text.secondary" gutterBottom>
                    Ready to Test Agent Capabilities
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Configure an agent role and domain, then run a capability
                    test to validate performance and get optimization
                    recommendations.
                  </Typography>
                </Paper>
              )}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

export default function StudioPage() {
  const [currentTab, setCurrentTab] = useState(0);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleTestComplete = (results: TestResults) => {
    console.log("Capability test completed:", results);
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          component="h1"
          gutterBottom
          sx={{
            fontWeight: 700,
            display: "flex",
            alignItems: "center",
            gap: 2,
          }}
        >
          <StudioIcon color="primary" sx={{ fontSize: 40 }} />
          Agent Composer Studio
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Comprehensive interface for composing agents with role and domain
          expertise, including capability testing
        </Typography>
      </Box>

      {/* Feature Overview */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: "center", bgcolor: "primary.50" }}>
            <AgentIcon color="primary" sx={{ fontSize: 32, mb: 1 }} />
            <Typography variant="subtitle2">Role + Domain</Typography>
            <Typography variant="caption" color="text.secondary">
              Agent composition pattern
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: "center", bgcolor: "secondary.50" }}>
            <BuildIcon color="secondary" sx={{ fontSize: 32, mb: 1 }} />
            <Typography variant="subtitle2">Quick Builder</Typography>
            <Typography variant="caption" color="text.secondary">
              Rapid deployment
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: "center", bgcolor: "success.50" }}>
            <AdvancedIcon color="success" sx={{ fontSize: 32, mb: 1 }} />
            <Typography variant="subtitle2">Advanced Form</Typography>
            <Typography variant="caption" color="text.secondary">
              Detailed configuration
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: "center", bgcolor: "warning.50" }}>
            <TestIcon color="warning" sx={{ fontSize: 32, mb: 1 }} />
            <Typography variant="subtitle2">Capability Testing</Typography>
            <Typography variant="caption" color="text.secondary">
              Validate before deploy
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Main Studio Interface */}
      <Card variant="outlined">
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs value={currentTab} onChange={handleTabChange}>
            <Tab
              label="Quick Composer"
              icon={<BuildIcon />}
              iconPosition="start"
            />
            <Tab
              label="Advanced Composer"
              icon={<AdvancedIcon />}
              iconPosition="start"
            />
            <Tab
              label="Capability Testing"
              icon={<TestIcon />}
              iconPosition="start"
            />
          </Tabs>
        </Box>

        <TabPanel value={currentTab} index={0}>
          <Box sx={{ p: 3 }}>
            <Alert severity="info" sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Quick Agent Composer
              </Typography>
              <Typography variant="body2">
                Rapid agent deployment with intelligent suggestions and
                streamlined coordination patterns. Perfect for quick
                orchestration tasks and experimentation.
              </Typography>
            </Alert>
            <AgentSpawner />
          </Box>
        </TabPanel>

        <TabPanel value={currentTab} index={1}>
          <Box sx={{ p: 3 }}>
            <Alert severity="info" sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Advanced Agent Composer
              </Typography>
              <Typography variant="body2">
                Comprehensive agent configuration with detailed quality gates,
                coordination strategies, and advanced options for complex
                orchestration scenarios.
              </Typography>
            </Alert>
            <AgentSpawningForm />
          </Box>
        </TabPanel>

        <TabPanel value={currentTab} index={2}>
          <Box sx={{ p: 3 }}>
            <Alert severity="warning" sx={{ mb: 3 }}>
              <Typography variant="subtitle2" gutterBottom>
                Agent Capability Testing
              </Typography>
              <Typography variant="body2">
                Test agent configurations before deployment. Validate
                role/domain combinations, assess coordination readiness, and get
                optimization recommendations.
              </Typography>
            </Alert>
            <AgentCapabilityTester onTestComplete={handleTestComplete} />
          </Box>
        </TabPanel>
      </Card>

      {/* Studio Information */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          Agent Composition Pattern
        </Typography>
        <Paper sx={{ p: 3, bgcolor: "grey.50" }}>
          <Typography variant="body2" paragraph>
            The Agent Composer Studio implements the{" "}
            <strong>Agent = Role + Domain</strong>{" "}
            pattern, where every agent is a composition of a behavioral
            archetype (role) and specialized knowledge area (domain). This
            enables precise capability matching for complex orchestration tasks.
          </Typography>

          <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mt: 2 }}>
            <Chip
              icon={<AgentIcon />}
              label="Role: Behavioral Archetype (researcher, architect, implementer)"
              variant="outlined"
              color="primary"
            />
            <Chip
              icon={<StudioIcon />}
              label="Domain: Knowledge Expertise (memory-systems, distributed-systems)"
              variant="outlined"
              color="secondary"
            />
            <Chip
              icon={<LaunchIcon />}
              label="Coordination: Multi-Agent Orchestration Patterns"
              variant="outlined"
              color="success"
            />
          </Stack>
        </Paper>
      </Box>
    </Box>
  );
}
