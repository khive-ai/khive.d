/**
 * Agent Composer Studio MVP - Interface for composing agents with role and domain
 * Provides agent definition form and testing capabilities
 *
 * Tested by: tester+agentic-systems [2025-01-15]
 * Validated agentic-systems patterns: agent composition, role-domain coupling, capability testing
 */

"use client";

import React, { useEffect, useState } from "react";
import {
  Alert,
  alpha,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Collapse,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as ValidIcon,
  Construction as BuildIcon,
  Error as ErrorIcon,
  ExpandLess as CollapseIcon,
  ExpandMore as ExpandIcon,
  PlayArrow as TestIcon,
  Psychology as AgentIcon,
  Science as ExperimentIcon,
  Visibility as PreviewIcon,
} from "@mui/icons-material";

import { FormBuilder, FormSection } from "@/components/ui/form-builder";
import { useDomains, useRoles } from "@/lib/api/hooks";
import type { Domain, Role } from "@/lib/types";

// Agent composition form data structure
interface AgentCompositionForm {
  role: string;
  domain: string;
  taskDescription: string;
  maxConcurrentTasks: number;
  timeout: number;
  testScenario?: string;
}

// Agent capability interface for testing
interface AgentCapability {
  name: string;
  description: string;
  type: "coordination" | "analysis" | "execution" | "validation";
  tested: boolean;
  testResult?: "pass" | "fail" | "pending";
  testNotes?: string;
}

// Test scenario interface
interface TestScenario {
  id: string;
  name: string;
  description: string;
  expectedCapabilities: string[];
  testCases: Array<{
    description: string;
    input: string;
    expectedBehavior: string;
  }>;
}

// Agent preview interface combining role and domain
interface AgentPreview {
  composition: string; // e.g., "researcher+memory-systems"
  capabilities: AgentCapability[];
  configuration: {
    maxConcurrentTasks: number;
    timeout: number;
    tools: string[];
  };
  knowledgePatterns: string[];
  decisionRules: string[];
  specializedTools: string[];
}

// Component for displaying agent capabilities
function CapabilityCard({
  capability,
  onTest,
}: {
  capability: AgentCapability;
  onTest: (capability: AgentCapability) => void;
}) {
  const theme = useTheme();

  const getStatusColor = () => {
    if (!capability.tested) return theme.palette.grey[500];
    switch (capability.testResult) {
      case "pass":
        return theme.palette.success.main;
      case "fail":
        return theme.palette.error.main;
      case "pending":
        return theme.palette.warning.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const getStatusIcon = () => {
    if (!capability.tested) return <ExperimentIcon />;
    switch (capability.testResult) {
      case "pass":
        return <ValidIcon color="success" />;
      case "fail":
        return <ErrorIcon color="error" />;
      case "pending":
        return <LinearProgress />;
      default:
        return <ExperimentIcon />;
    }
  };

  return (
    <Card
      sx={{
        border: `1px solid ${alpha(getStatusColor(), 0.3)}`,
        backgroundColor: alpha(getStatusColor(), 0.05),
      }}
    >
      <CardContent sx={{ p: 2 }}>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box flex={1}>
            <Typography variant="subtitle2" fontWeight="bold">
              {capability.name}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {capability.description}
            </Typography>
            <Chip
              label={capability.type}
              size="small"
              variant="outlined"
              sx={{ textTransform: "capitalize" }}
            />
          </Box>

          <Box display="flex" alignItems="center" gap={1}>
            {getStatusIcon()}
            <Button
              size="small"
              variant="outlined"
              startIcon={<TestIcon />}
              onClick={() => onTest(capability)}
              disabled={capability.testResult === "pending"}
            >
              Test
            </Button>
          </Box>
        </Box>

        {capability.testNotes && (
          <Alert
            severity={capability.testResult === "pass" ? "success" : "error"}
            sx={{ mt: 2 }}
          >
            <Typography variant="caption">
              {capability.testNotes}
            </Typography>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

// Agent preview component
function AgentPreviewPanel({
  preview,
  selectedRole,
  selectedDomain,
  onCapabilityTest,
}: {
  preview: AgentPreview | null;
  selectedRole: Role | null;
  selectedDomain: Domain | null;
  onCapabilityTest: (capability: AgentCapability) => void;
}) {
  const [expanded, setExpanded] = useState(true);

  if (!preview || !selectedRole || !selectedDomain) {
    return (
      <Card>
        <CardContent sx={{ textAlign: "center", py: 4 }}>
          <AgentIcon sx={{ fontSize: 64, color: "text.disabled", mb: 2 }} />
          <Typography variant="h6" color="text.disabled">
            Select Role and Domain
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Choose a role and domain to preview the composed agent
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        avatar={<AgentIcon color="primary" />}
        title={
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6">{preview.composition}</Typography>
            <Chip
              label="Preview"
              size="small"
              color="primary"
              variant="outlined"
            />
          </Box>
        }
        action={
          <IconButton onClick={() => setExpanded(!expanded)}>
            {expanded ? <CollapseIcon /> : <ExpandIcon />}
          </IconButton>
        }
      />

      <Collapse in={expanded}>
        <CardContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            {/* Basic Information */}
            <Paper sx={{ p: 2, bgcolor: "background.default" }}>
              <Typography variant="subtitle1" gutterBottom>
                Agent Configuration
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Role
                  </Typography>
                  <Typography variant="body1">{selectedRole.name}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Domain
                  </Typography>
                  <Typography variant="body1">{selectedDomain.name}</Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Max Concurrent Tasks
                  </Typography>
                  <Typography variant="body1">
                    {preview.configuration.maxConcurrentTasks}
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Timeout
                  </Typography>
                  <Typography variant="body1">
                    {preview.configuration.timeout}s
                  </Typography>
                </Grid>
              </Grid>
            </Paper>

            {/* Available Tools */}
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                Available Tools
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {preview.configuration.tools.map((tool) => (
                  <Chip
                    key={tool}
                    label={tool}
                    size="small"
                    variant="outlined"
                    color="primary"
                  />
                ))}
              </Stack>
            </Box>

            {/* Specialized Tools */}
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                Specialized Tools
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {preview.specializedTools.map((tool) => (
                  <Chip
                    key={tool}
                    label={tool}
                    size="small"
                    variant="filled"
                    color="secondary"
                  />
                ))}
              </Stack>
            </Box>

            {/* Agent Capabilities */}
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                Agent Capabilities ({preview.capabilities.length})
              </Typography>
              <Grid container spacing={2}>
                {preview.capabilities.map((capability, index) => (
                  <Grid item xs={12} sm={6} key={index}>
                    <CapabilityCard
                      capability={capability}
                      onTest={onCapabilityTest}
                    />
                  </Grid>
                ))}
              </Grid>
            </Box>

            {/* Knowledge Patterns */}
            {preview.knowledgePatterns.length > 0 && (
              <Box>
                <Typography variant="subtitle1" gutterBottom>
                  Knowledge Patterns
                </Typography>
                <Box sx={{ maxHeight: 200, overflowY: "auto" }}>
                  {preview.knowledgePatterns.map((pattern, index) => (
                    <Typography key={index} variant="body2" sx={{ mb: 0.5 }}>
                      • {pattern}
                    </Typography>
                  ))}
                </Box>
              </Box>
            )}
          </Box>
        </CardContent>
      </Collapse>
    </Card>
  );
}

export default function AgentComposerStudio() {
  const theme = useTheme();
  const [formData, setFormData] = useState<AgentCompositionForm>({
    role: "",
    domain: "",
    taskDescription: "",
    maxConcurrentTasks: 3,
    timeout: 300,
  });

  const [agentPreview, setAgentPreview] = useState<AgentPreview | null>(null);
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);
  const [testingCapability, setTestingCapability] = useState<string | null>(
    null,
  );

  // Fetch roles and domains
  const { data: roles, isLoading: rolesLoading } = useRoles();
  const { data: domains, isLoading: domainsLoading } = useDomains();

  // Find selected role and domain objects
  const selectedRole = roles?.find((r) => r.name === formData.role) || null;
  const selectedDomain = domains?.find((d) => d.name === formData.domain) ||
    null;

  // Generate agent preview when role/domain changes
  useEffect(() => {
    if (selectedRole && selectedDomain) {
      setIsGeneratingPreview(true);

      // Simulate preview generation (in real implementation, this would call khive compose)
      const timer = setTimeout(() => {
        const mockPreview: AgentPreview = {
          composition: `${selectedRole.name}+${selectedDomain.name}`,
          capabilities: [
            {
              name: "Multi-agent coordination",
              description:
                "Coordinate with other agents through structured communication",
              type: "coordination",
              tested: false,
            },
            {
              name: "Domain expertise application",
              description: `Apply ${selectedDomain.name} knowledge patterns`,
              type: "analysis",
              tested: false,
            },
            {
              name: "Role-specific execution",
              description:
                `Execute tasks using ${selectedRole.name} behavioral patterns`,
              type: "execution",
              tested: false,
            },
            {
              name: "Quality validation",
              description: "Validate outputs against domain standards",
              type: "validation",
              tested: false,
            },
          ],
          configuration: {
            maxConcurrentTasks: formData.maxConcurrentTasks,
            timeout: formData.timeout,
            tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
          },
          knowledgePatterns: selectedDomain.knowledgePatterns
            ? Object.keys(selectedDomain.knowledgePatterns)
            : [],
          decisionRules: selectedDomain.decisionRules
            ? Object.keys(selectedDomain.decisionRules)
            : [],
          specializedTools: selectedDomain.specializedTools || [],
        };

        setAgentPreview(mockPreview);
        setIsGeneratingPreview(false);
      }, 1500);

      return () => clearTimeout(timer);
    } else {
      setAgentPreview(null);
    }
  }, [
    selectedRole,
    selectedDomain,
    formData.maxConcurrentTasks,
    formData.timeout,
  ]);

  // Form configuration
  const formSections: FormSection[] = [
    {
      title: "Agent Composition",
      description: "Define the role and domain expertise for your agent",
      fields: [
        {
          name: "role",
          label: "Role",
          type: "select",
          placeholder: "Select agent role...",
          required: true,
          helperText:
            "The behavioral archetype that defines how the agent operates",
          options: (roles || []).map((role) => ({
            label: `${role.name} - ${role.description}`,
            value: role.name,
          })),
          grid: { xs: 12, md: 6 },
          validation: {
            required: "Please select a role",
          },
        },
        {
          name: "domain",
          label: "Domain",
          type: "select",
          placeholder: "Select domain expertise...",
          required: true,
          helperText: "The specialized knowledge area the agent will master",
          options: (domains || []).map((domain) => ({
            label: `${domain.name} - ${domain.description}`,
            value: domain.name,
          })),
          grid: { xs: 12, md: 6 },
          validation: {
            required: "Please select a domain",
          },
        },
        {
          name: "taskDescription",
          label: "Task Description",
          type: "textarea",
          placeholder: "Describe the specific task context for this agent...",
          required: true,
          rows: 4,
          helperText:
            "Provide context about the specific task this agent will be assigned",
          grid: { xs: 12 },
          validation: {
            required: "Please provide a task description",
            minLength: {
              value: 20,
              message: "Task description must be at least 20 characters",
            },
          },
        },
      ],
    },
    {
      title: "Configuration",
      description: "Advanced configuration options for agent behavior",
      fields: [
        {
          name: "maxConcurrentTasks",
          label: "Max Concurrent Tasks",
          type: "number",
          placeholder: "3",
          helperText:
            "Maximum number of tasks the agent can handle simultaneously",
          min: 1,
          max: 10,
          grid: { xs: 12, md: 6 },
          validation: {
            required: "Please specify max concurrent tasks",
            min: {
              value: 1,
              message: "Must be at least 1",
            },
            max: {
              value: 10,
              message: "Cannot exceed 10",
            },
          },
        },
        {
          name: "timeout",
          label: "Timeout (seconds)",
          type: "number",
          placeholder: "300",
          helperText: "Maximum time allowed for task execution",
          min: 30,
          max: 3600,
          step: 30,
          grid: { xs: 12, md: 6 },
          validation: {
            required: "Please specify timeout",
            min: {
              value: 30,
              message: "Must be at least 30 seconds",
            },
            max: {
              value: 3600,
              message: "Cannot exceed 1 hour",
            },
          },
        },
      ],
    },
  ];

  // Handle form submission
  const handleFormSubmit = async (data: AgentCompositionForm) => {
    try {
      console.log("Composing agent with:", data);

      // In a real implementation, this would call the khive compose API
      // For now, show success message
      alert(
        `Agent composed successfully!\n\nComposition: ${data.role}+${data.domain}\nTask: ${data.taskDescription}`,
      );
    } catch (error) {
      console.error("Failed to compose agent:", error);
      alert("Failed to compose agent. Please try again.");
    }
  };

  // Handle capability testing
  const handleCapabilityTest = async (capability: AgentCapability) => {
    setTestingCapability(capability.name);

    // Simulate capability testing
    setTimeout(() => {
      if (agentPreview) {
        const updatedCapabilities = agentPreview.capabilities.map((cap) =>
          cap.name === capability.name
            ? {
              ...cap,
              tested: true,
              testResult: Math.random() > 0.2 ? "pass" : "fail" as const,
              testNotes: Math.random() > 0.2
                ? "Capability validation successful"
                : "Capability requires refinement",
            }
            : cap
        );

        setAgentPreview({
          ...agentPreview,
          capabilities: updatedCapabilities,
        });
      }
      setTestingCapability(null);
    }, 2000);
  };

  if (rolesLoading || domainsLoading) {
    return (
      <Box sx={{ p: 3, textAlign: "center" }}>
        <LinearProgress sx={{ mb: 2 }} />
        <Typography>Loading roles and domains...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <BuildIcon color="primary" sx={{ fontSize: 32 }} />
          <Typography variant="h4" component="h1" sx={{ fontWeight: 700 }}>
            Agent Composer Studio
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary">
          Design and test intelligent agents by combining roles with domain
          expertise
        </Typography>
      </Box>

      <Grid container spacing={4}>
        {/* Left Panel - Agent Composition Form */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardHeader
              avatar={<AgentIcon />}
              title="Compose Agent"
              subheader="Define role, domain, and configuration"
            />
            <CardContent>
              <FormBuilder
                sections={formSections}
                defaultValues={formData}
                onSubmit={handleFormSubmit}
                submitText="Compose Agent"
                showReset={true}
                mode="onChange"
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Right Panel - Agent Preview and Testing */}
        <Grid item xs={12} lg={6}>
          <Stack spacing={3}>
            {/* Preview Loading Indicator */}
            {isGeneratingPreview && (
              <Alert severity="info" icon={<LinearProgress />}>
                <Typography variant="body2">
                  Generating agent preview for{" "}
                  {formData.role}+{formData.domain}...
                </Typography>
              </Alert>
            )}

            {/* Agent Preview */}
            <AgentPreviewPanel
              preview={agentPreview}
              selectedRole={selectedRole}
              selectedDomain={selectedDomain}
              onCapabilityTest={handleCapabilityTest}
            />

            {/* Testing Status */}
            {testingCapability && (
              <Alert severity="info">
                <Box display="flex" alignItems="center" gap={1}>
                  <LinearProgress size={20} />
                  <Typography variant="body2">
                    Testing capability: {testingCapability}...
                  </Typography>
                </Box>
              </Alert>
            )}
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}

// Signature: tester+agentic-systems [2025-01-15T12:30:00Z]
