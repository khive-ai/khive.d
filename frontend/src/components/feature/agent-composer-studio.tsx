/**
 * Agent Composer Studio MVP - Interactive Agent Definition and Testing Interface
 * Provides a focused environment for composing agents with role/domain combinations
 * and testing their capabilities before deployment
 */

"use client";

import React, { useEffect, useState } from "react";
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
  CardHeader,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
  TextField,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as SuccessIcon,
  Code as CodeIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  Info as InfoIcon,
  PlayArrow as TestIcon,
  Psychology as RoleIcon,
  School as DomainIcon,
  Science as StudioIcon,
  Settings as ConfigIcon,
  Timeline as CapabilityIcon,
  Visibility as PreviewIcon,
} from "@mui/icons-material";

import { useDomains, useRoles } from "@/lib/api/hooks";

export interface AgentComposition {
  role: string;
  domain: string;
  taskContext: string;
  expectedCapabilities: string[];
}

export interface CapabilityTest {
  id: string;
  name: string;
  description: string;
  testCode: string;
  status: "pending" | "running" | "passed" | "failed";
  result?: string;
}

export interface AgentComposerStudioProps {
  onAgentComposed?: (composition: AgentComposition) => void;
  className?: string;
}

export const AgentComposerStudio: React.FC<AgentComposerStudioProps> = ({
  onAgentComposed,
  className,
}) => {
  const theme = useTheme();
  const [selectedRole, setSelectedRole] = useState<string>("");
  const [selectedDomain, setSelectedDomain] = useState<string>("");
  const [taskContext, setTaskContext] = useState<string>("");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [testResults, setTestResults] = useState<CapabilityTest[]>([]);
  const [isTestingCapabilities, setIsTestingCapabilities] = useState(false);
  const [composedAgent, setComposedAgent] = useState<AgentComposition | null>(
    null,
  );

  // API hooks
  const { data: roles, isLoading: rolesLoading } = useRoles();
  const { data: domains, isLoading: domainsLoading } = useDomains();

  // Capability tests based on role/domain combination
  const generateCapabilityTests = (
    role: string,
    domain: string,
  ): CapabilityTest[] => {
    const tests: CapabilityTest[] = [];

    // Role-specific capability tests
    switch (role) {
      case "researcher":
        tests.push({
          id: "research_1",
          name: "Information Gathering",
          description: "Test ability to gather and synthesize information",
          testCode: `agent.gather_information("${domain} patterns")`,
          status: "pending",
        });
        tests.push({
          id: "research_2",
          name: "Analysis Depth",
          description: "Test analytical thinking and depth of investigation",
          testCode: `agent.analyze_complexity("${domain} architecture")`,
          status: "pending",
        });
        break;

      case "architect":
        tests.push({
          id: "architect_1",
          name: "System Design",
          description: "Test system design and architecture capabilities",
          testCode: `agent.design_system("${domain} architecture")`,
          status: "pending",
        });
        tests.push({
          id: "architect_2",
          name: "Pattern Recognition",
          description: "Test ability to identify and apply design patterns",
          testCode: `agent.identify_patterns("${domain} best practices")`,
          status: "pending",
        });
        break;

      case "implementer":
        tests.push({
          id: "implementer_1",
          name: "Code Generation",
          description: "Test ability to generate working code",
          testCode: `agent.generate_code("${domain} implementation")`,
          status: "pending",
        });
        tests.push({
          id: "implementer_2",
          name: "Best Practices",
          description: "Test adherence to coding standards and best practices",
          testCode: `agent.validate_standards("${domain} code quality")`,
          status: "pending",
        });
        break;

      default:
        tests.push({
          id: "general_1",
          name: "Task Understanding",
          description: "Test ability to understand and break down tasks",
          testCode: `agent.understand_task("${domain} task breakdown")`,
          status: "pending",
        });
    }

    // Domain-specific capability tests
    if (domain.includes("software-architecture")) {
      tests.push({
        id: "domain_software",
        name: "Software Architecture Knowledge",
        description: "Test understanding of software architecture principles",
        testCode: `agent.apply_principles("SOLID, DDD, microservices")`,
        status: "pending",
      });
    }

    if (domain.includes("agentic-systems")) {
      tests.push({
        id: "domain_agentic",
        name: "Multi-Agent Coordination",
        description: "Test understanding of multi-agent patterns",
        testCode: `agent.coordinate_agents("fan-out, pipeline, parallel")`,
        status: "pending",
      });
    }

    return tests;
  };

  // Preview agent capabilities based on role/domain combination
  const previewAgentCapabilities = () => {
    if (!selectedRole || !selectedDomain) return [];

    const capabilities: string[] = [];

    // Role-based capabilities
    const roleCapabilities: Record<string, string[]> = {
      researcher: [
        "Information gathering and synthesis",
        "Pattern recognition and analysis",
        "Literature review and documentation",
        "Data collection and validation",
      ],
      architect: [
        "System design and planning",
        "Architecture pattern application",
        "Technical decision making",
        "Component interaction design",
      ],
      implementer: [
        "Code generation and implementation",
        "Best practice application",
        "Testing and validation",
        "Integration and deployment",
      ],
      analyst: [
        "Data analysis and interpretation",
        "Pattern identification",
        "Report generation",
        "Insight synthesis",
      ],
      tester: [
        "Test case generation",
        "Quality assurance",
        "Bug identification",
        "Validation and verification",
      ],
      reviewer: [
        "Code and design review",
        "Quality assessment",
        "Standards compliance",
        "Improvement recommendations",
      ],
    };

    // Domain-specific capabilities
    const domainCapabilities: Record<string, string[]> = {
      "software-architecture": [
        "SOLID principles application",
        "Design pattern implementation",
        "Microservices architecture",
        "API design and documentation",
      ],
      "agentic-systems": [
        "Multi-agent coordination patterns",
        "Orchestration strategies",
        "Consensus mechanisms",
        "Distributed system design",
      ],
      "distributed-systems": [
        "Consistency and availability tradeoffs",
        "Consensus algorithms",
        "Fault tolerance design",
        "Scalability patterns",
      ],
      "memory-systems": [
        "Memory hierarchy optimization",
        "Caching strategies",
        "Data locality patterns",
        "Performance optimization",
      ],
    };

    capabilities.push(...(roleCapabilities[selectedRole] || []));
    capabilities.push(...(domainCapabilities[selectedDomain] || []));

    return [...new Set(capabilities)]; // Remove duplicates
  };

  // Run capability tests (mock implementation)
  const runCapabilityTests = async () => {
    if (!selectedRole || !selectedDomain) return;

    setIsTestingCapabilities(true);
    const tests = generateCapabilityTests(selectedRole, selectedDomain);
    setTestResults(tests);

    // Simulate running tests with delays
    for (let i = 0; i < tests.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, 1000));

      setTestResults((prev) =>
        prev.map((test, index) =>
          index === i
            ? {
              ...test,
              status: "running",
              result: `Running test: ${test.testCode}`,
            }
            : test
        )
      );

      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Mock test results (80% success rate)
      const success = Math.random() > 0.2;
      setTestResults((prev) =>
        prev.map((test, index) =>
          index === i
            ? {
              ...test,
              status: success ? "passed" : "failed",
              result: success
                ? `✅ Test passed successfully`
                : `❌ Test failed: Capability needs improvement`,
            }
            : test
        )
      );
    }

    setIsTestingCapabilities(false);
  };

  // Compose agent
  const composeAgent = () => {
    if (!selectedRole || !selectedDomain || !taskContext) return;

    const composition: AgentComposition = {
      role: selectedRole,
      domain: selectedDomain,
      taskContext,
      expectedCapabilities: previewAgentCapabilities(),
    };

    setComposedAgent(composition);
    onAgentComposed?.(composition);
  };

  // Get role information
  const selectedRoleInfo = roles?.find((r) => r.name === selectedRole);
  const selectedDomainInfo = domains?.find((d) => d.name === selectedDomain);

  const capabilities = previewAgentCapabilities();

  return (
    <Card className={className} variant="outlined">
      <CardHeader
        avatar={<StudioIcon color="primary" />}
        title={
          <Typography variant="h6" fontWeight={600}>
            Agent Composer Studio
          </Typography>
        }
        subheader="Interactive environment for composing and testing agent capabilities"
      />

      <CardContent>
        <Grid container spacing={4}>
          {/* Agent Definition Section */}
          <Grid item xs={12} md={6}>
            <Typography
              variant="h6"
              gutterBottom
              sx={{ display: "flex", alignItems: "center", gap: 1 }}
            >
              <ConfigIcon color="primary" />
              Agent Definition
            </Typography>

            <Stack spacing={3}>
              {/* Role Selection */}
              <FormControl fullWidth>
                <InputLabel>Agent Role</InputLabel>
                <Select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  label="Agent Role"
                  disabled={rolesLoading}
                >
                  {roles?.map((role) => (
                    <MenuItem key={role.name} value={role.name}>
                      <Box>
                        <Typography variant="body1" fontWeight={500}>
                          {role.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {role.description}
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Domain Selection */}
              <FormControl fullWidth>
                <InputLabel>Domain Expertise</InputLabel>
                <Select
                  value={selectedDomain}
                  onChange={(e) => setSelectedDomain(e.target.value)}
                  label="Domain Expertise"
                  disabled={domainsLoading}
                >
                  {domains?.map((domain) => (
                    <MenuItem key={domain.name} value={domain.name}>
                      <Box>
                        <Typography variant="body1" fontWeight={500}>
                          {domain.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {domain.description}
                        </Typography>
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {/* Task Context */}
              <TextField
                label="Task Context"
                multiline
                rows={4}
                value={taskContext}
                onChange={(e) => setTaskContext(e.target.value)}
                placeholder="Describe the specific task or objective for this agent..."
                helperText="Provide context to help validate agent capabilities"
              />

              {/* Agent Info Display */}
              {selectedRole && selectedDomain && (
                <Paper
                  sx={{
                    p: 2,
                    backgroundColor: alpha(theme.palette.primary.main, 0.05),
                  }}
                >
                  <Typography
                    variant="subtitle2"
                    gutterBottom
                    sx={{ display: "flex", alignItems: "center", gap: 1 }}
                  >
                    <RoleIcon fontSize="small" />
                    <DomainIcon fontSize="small" />
                    Agent Composition
                  </Typography>
                  <Typography
                    variant="h6"
                    color="primary.main"
                    fontWeight={600}
                  >
                    {selectedRole} + {selectedDomain}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Chip
                      label={selectedRoleInfo?.type || "Role"}
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ mr: 1 }}
                    />
                    <Chip
                      label="Domain Expert"
                      size="small"
                      color="secondary"
                      variant="outlined"
                    />
                  </Box>
                </Paper>
              )}
            </Stack>
          </Grid>

          {/* Capabilities Preview */}
          <Grid item xs={12} md={6}>
            <Typography
              variant="h6"
              gutterBottom
              sx={{ display: "flex", alignItems: "center", gap: 1 }}
            >
              <CapabilityIcon color="primary" />
              Expected Capabilities
            </Typography>

            {capabilities.length > 0
              ? (
                <Stack spacing={2}>
                  <Paper sx={{ p: 2, maxHeight: 300, overflow: "auto" }}>
                    <Stack spacing={1}>
                      {capabilities.map((capability, index) => (
                        <Box
                          key={index}
                          sx={{ display: "flex", alignItems: "center", gap: 1 }}
                        >
                          <SuccessIcon
                            sx={{ fontSize: 16, color: "success.main" }}
                          />
                          <Typography variant="body2">{capability}</Typography>
                        </Box>
                      ))}
                    </Stack>
                  </Paper>

                  {/* Action Buttons */}
                  <Stack direction="row" spacing={2}>
                    <Button
                      variant="outlined"
                      startIcon={<TestIcon />}
                      onClick={runCapabilityTests}
                      disabled={isTestingCapabilities || !taskContext}
                    >
                      Test Capabilities
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={<CodeIcon />}
                      onClick={composeAgent}
                      disabled={!selectedRole || !selectedDomain ||
                        !taskContext}
                    >
                      Compose Agent
                    </Button>
                  </Stack>
                </Stack>
              )
              : (
                <Alert severity="info" sx={{ mt: 2 }}>
                  Select a role and domain to preview agent capabilities
                </Alert>
              )}
          </Grid>

          {/* Capability Testing Section */}
          {testResults.length > 0 && (
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography
                    variant="h6"
                    sx={{ display: "flex", alignItems: "center", gap: 1 }}
                  >
                    <TestIcon color="primary" />
                    Capability Test Results
                    {isTestingCapabilities && (
                      <LinearProgress sx={{ ml: 2, width: 100 }} />
                    )}
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Stack spacing={2}>
                    {testResults.map((test) => (
                      <Paper key={test.id} sx={{ p: 2 }}>
                        <Box
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            mb: 1,
                          }}
                        >
                          <Typography variant="subtitle1" fontWeight={500}>
                            {test.name}
                          </Typography>
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              gap: 1,
                            }}
                          >
                            {test.status === "passed" && (
                              <SuccessIcon sx={{ color: "success.main" }} />
                            )}
                            {test.status === "failed" && (
                              <ErrorIcon sx={{ color: "error.main" }} />
                            )}
                            {test.status === "running" && (
                              <LinearProgress sx={{ width: 50 }} />
                            )}
                            <Chip
                              label={test.status}
                              size="small"
                              color={test.status === "passed"
                                ? "success"
                                : test.status === "failed"
                                ? "error"
                                : test.status === "running"
                                ? "primary"
                                : "default"}
                            />
                          </Box>
                        </Box>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          paragraph
                        >
                          {test.description}
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{
                            fontFamily: "monospace",
                            display: "block",
                            mb: 1,
                          }}
                        >
                          {test.testCode}
                        </Typography>
                        {test.result && (
                          <Typography variant="body2" color="text.secondary">
                            {test.result}
                          </Typography>
                        )}
                      </Paper>
                    ))}
                  </Stack>
                </AccordionDetails>
              </Accordion>
            </Grid>
          )}

          {/* Composed Agent Display */}
          {composedAgent && (
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Alert severity="success" sx={{ mb: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Agent Successfully Composed!
                </Typography>
                <Typography variant="body2">
                  Your {composedAgent.role}+{composedAgent.domain}{" "}
                  agent is ready for deployment. It has been configured with
                  {" "}
                  {composedAgent.expectedCapabilities.length} core capabilities.
                </Typography>
              </Alert>

              <Paper
                sx={{
                  p: 2,
                  backgroundColor: alpha(theme.palette.success.main, 0.05),
                }}
              >
                <Typography variant="subtitle1" gutterBottom fontWeight={600}>
                  Agent Summary:
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Role:
                    </Typography>
                    <Typography variant="body1" fontWeight={500}>
                      {composedAgent.role}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Domain:
                    </Typography>
                    <Typography variant="body1" fontWeight={500}>
                      {composedAgent.domain}
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="body2" color="text.secondary">
                      Task Context:
                    </Typography>
                    <Typography variant="body1">
                      {composedAgent.taskContext}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  );
};

AgentComposerStudio.displayName = "AgentComposerStudio";
