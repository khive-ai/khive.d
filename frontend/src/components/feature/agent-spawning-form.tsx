/**
 * Agent Spawning Form Component
 * Advanced interface for spawning specialized agents with role/domain configuration
 * Built with agentic-systems domain expertise for optimal orchestration patterns
 */

import React, { useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Info as InfoIcon,
  PersonAdd as SpawnIcon,
  PlayArrow as LaunchIcon,
  Psychology as RoleIcon,
  School as DomainIcon,
  Settings as ConfigIcon,
} from "@mui/icons-material";
import { FormProvider, SubmitHandler, useForm } from "react-hook-form";
import {
  FormBuilder,
  FormField,
  FormSection,
} from "@/components/ui/form-builder";
import { useDomains, useRoles, useSpawnAgent } from "@/lib/api/hooks";

export interface AgentSpawningFormProps {
  onAgentSpawned?: (agentData: SpawnedAgentData) => void;
  onCancel?: () => void;
  coordinationId?: string;
  className?: string;
}

export interface SpawnedAgentData {
  role: string;
  domain: string;
  taskContext: string;
  coordinationStrategy: "FAN_OUT_SYNTHESIZE" | "PIPELINE" | "PARALLEL";
  qualityGate: "basic" | "thorough" | "critical";
  expectedArtifacts: string[];
  agentCount?: number;
  timeout?: number;
}

interface FormData {
  role: string;
  domain: string;
  taskContext: string;
  coordinationStrategy: "FAN_OUT_SYNTHESIZE" | "PIPELINE" | "PARALLEL";
  qualityGate: "basic" | "thorough" | "critical";
  expectedArtifacts: string;
  agentCount: number;
  timeout: number;
  priority: "low" | "normal" | "high" | "critical";
  isolateWorkspace: boolean;
}

export const AgentSpawningForm: React.FC<AgentSpawningFormProps> = ({
  onAgentSpawned,
  onCancel,
  coordinationId,
  className,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);

  // Async cancellation patterns
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef(true);

  // Cleanup on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Fetch roles and domains from API
  const { data: roles, isLoading: rolesLoading } = useRoles();
  const { data: domains, isLoading: domainsLoading } = useDomains();
  const spawnAgent = useSpawnAgent();

  // Form setup with React Hook Form
  const methods = useForm<FormData>({
    defaultValues: {
      role: "",
      domain: "",
      taskContext: "",
      coordinationStrategy: "FAN_OUT_SYNTHESIZE",
      qualityGate: "thorough",
      expectedArtifacts: "",
      agentCount: 1,
      timeout: 300000, // 5 minutes in ms
      priority: "normal",
      isolateWorkspace: false,
    },
    mode: "onChange",
  });

  // Transform API data into form options
  const roleOptions = roles?.map((role) => ({
    label: `${role.name} - ${role.description}`,
    value: role.name,
  })) || [];

  const domainOptions = domains?.map((domain) => ({
    label: `${domain.name}${
      domain.parent ? ` (${domain.parent})` : ""
    } - ${domain.description}`,
    value: domain.name,
  })) || [];

  const coordinationStrategyOptions = [
    {
      label:
        "Fan-out/Synthesize - Multiple agents explore, then synthesize findings",
      value: "FAN_OUT_SYNTHESIZE",
    },
    {
      label: "Pipeline - Sequential processing with handoffs between agents",
      value: "PIPELINE",
    },
    {
      label: "Parallel - Independent concurrent execution",
      value: "PARALLEL",
    },
  ];

  const qualityGateOptions = [
    {
      label: "Basic - Output validation and format checking",
      value: "basic",
    },
    {
      label: "Thorough - Cross-agent consistency and consolidation review",
      value: "thorough",
    },
    {
      label: "Critical - Multi-round validation with external verification",
      value: "critical",
    },
  ];

  const priorityOptions = [
    { label: "Low Priority", value: "low" },
    { label: "Normal Priority", value: "normal" },
    { label: "High Priority", value: "high" },
    { label: "Critical Priority", value: "critical" },
  ];

  // Form sections configuration based on agentic-systems patterns
  const formSections: FormSection[] = [
    {
      title: "Agent Configuration",
      description: "Define the agent's role and domain expertise",
      fields: [
        {
          name: "role",
          label: "Agent Role",
          type: "select",
          required: true,
          placeholder: "Select agent role...",
          helperText:
            "The behavioral archetype that defines how the agent operates",
          options: roleOptions,
          grid: { xs: 12, md: 6 },
          validation: {
            required: "Agent role is required for spawning",
          },
        },
        {
          name: "domain",
          label: "Domain Expertise",
          type: "select",
          required: true,
          placeholder: "Select domain expertise...",
          helperText:
            "Specialized knowledge area that augments agent capabilities",
          options: domainOptions,
          grid: { xs: 12, md: 6 },
          validation: {
            required:
              "Domain expertise is required for effective agent performance",
          },
        },
      ] as FormField[],
    },
    {
      title: "Task Definition",
      description: "Specify the task context and execution parameters",
      fields: [
        {
          name: "taskContext",
          label: "Task Context",
          type: "textarea",
          required: true,
          placeholder:
            "Describe the task, objectives, and any specific requirements...",
          helperText:
            "Detailed description of what the agent should accomplish",
          rows: 4,
          grid: { xs: 12 },
          validation: {
            required: "Task context is essential for agent understanding",
            minLength: {
              value: 20,
              message:
                "Task context should be at least 20 characters for clarity",
            },
          },
        },
        {
          name: "expectedArtifacts",
          label: "Expected Artifacts",
          type: "textarea",
          placeholder: "List expected deliverables (one per line)...",
          helperText:
            "Specific outputs or deliverables the agent should produce",
          rows: 3,
          grid: { xs: 12 },
        },
      ] as FormField[],
    },
    {
      title: "Coordination Strategy",
      description: "Configure multi-agent coordination and quality controls",
      fields: [
        {
          name: "coordinationStrategy",
          label: "Coordination Pattern",
          type: "radio",
          required: true,
          helperText:
            "How this agent will coordinate with others in the orchestration",
          options: coordinationStrategyOptions,
          grid: { xs: 12 },
        },
        {
          name: "qualityGate",
          label: "Quality Gate Level",
          type: "select",
          required: true,
          options: qualityGateOptions,
          helperText: "Level of validation and quality assurance required",
          grid: { xs: 12, md: 6 },
        },
        {
          name: "agentCount",
          label: "Agent Count",
          type: "number",
          required: true,
          helperText:
            "Number of agents to spawn for this task (1-8 recommended)",
          min: 1,
          max: 8,
          step: 1,
          grid: { xs: 12, md: 6 },
          validation: {
            min: {
              value: 1,
              message: "At least one agent is required",
            },
            max: {
              value: 8,
              message: "Maximum 8 agents per spawning for optimal coordination",
            },
          },
        },
      ] as FormField[],
    },
    {
      title: "Advanced Options",
      description: "Additional configuration for specialized use cases",
      fields: [
        {
          name: "priority",
          label: "Task Priority",
          type: "select",
          options: priorityOptions,
          helperText:
            "Priority level affects resource allocation and scheduling",
          grid: { xs: 12, md: 4 },
        },
        {
          name: "timeout",
          label: "Timeout (seconds)",
          type: "number",
          min: 60,
          max: 3600,
          step: 30,
          helperText: "Maximum execution time before agent termination",
          grid: { xs: 12, md: 4 },
        },
        {
          name: "isolateWorkspace",
          label: "Isolate Workspace",
          type: "checkbox",
          helperText: "Create isolated workspace for this agent's artifacts",
          grid: { xs: 12, md: 4 },
        },
      ] as FormField[],
    },
  ];

  const handleSubmit: SubmitHandler<FormData> = async (data) => {
    // Race condition prevention - cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this request
    abortControllerRef.current = new AbortController();

    setIsSubmitting(true);
    setSubmitError(null);
    setProgress("Initializing agent spawning...");

    try {
      // Transform form data for agent spawning API call
      setProgress("Preparing agent configuration...");
      const spawnRequest = {
        role: data.role,
        domain: data.domain,
        taskContext: data.taskContext,
        coordinationStrategy: data.coordinationStrategy,
        qualityGate: data.qualityGate,
        expectedArtifacts: data.expectedArtifacts.split("\n").filter((a) =>
          a.trim()
        ),
        agentCount: data.agentCount,
        timeout: data.timeout * 1000, // Convert to milliseconds
        priority: data.priority,
        isolateWorkspace: data.isolateWorkspace,
        coordinationId,
      };

      // Check if request was cancelled before API call
      if (abortControllerRef.current?.signal.aborted) {
        return;
      }

      // Call the agent spawning API with progress feedback
      setProgress(`Spawning ${data.agentCount} agent(s)...`);
      const spawnResponse = await spawnAgent.mutateAsync(spawnRequest);

      // Check if request was cancelled after API call
      if (!isMountedRef.current || abortControllerRef.current?.signal.aborted) {
        return;
      }

      setProgress("Agent(s) spawned successfully!");

      // Transform response data for parent component
      const spawnedAgentData: SpawnedAgentData = {
        role: data.role,
        domain: data.domain,
        taskContext: data.taskContext,
        coordinationStrategy: data.coordinationStrategy,
        qualityGate: data.qualityGate,
        expectedArtifacts: spawnRequest.expectedArtifacts,
        agentCount: data.agentCount,
        timeout: data.timeout * 1000,
      };

      // Notify parent component with spawning result
      onAgentSpawned?.(spawnedAgentData);

      // Reset form on successful spawning
      methods.reset();

      // Optionally show success message based on spawn response
      if (spawnResponse.status === "spawning") {
        console.log(
          `Successfully initiated spawning of ${spawnResponse.agents.length} agents`,
        );
        console.log(
          `Session ID: ${spawnResponse.sessionId}, Coordination ID: ${spawnResponse.coordinationId}`,
        );
      }
    } catch (error) {
      // Don't set error if request was cancelled
      if (abortControllerRef.current?.signal.aborted || !isMountedRef.current) {
        return;
      }

      let errorMessage = "Failed to spawn agent. Please try again.";

      if (error instanceof Error) {
        errorMessage = error.message;
      }

      // Handle specific API errors
      if (error.status === 409) {
        errorMessage =
          "Agent spawning conflict detected. Please try again or adjust coordination strategy.";
      } else if (error.status === 503) {
        errorMessage =
          "Backend service is currently unavailable. Please try again in a moment.";
      } else if (error.status >= 400 && error.status < 500) {
        errorMessage = `Invalid request: ${error.message}`;
      }

      setSubmitError(errorMessage);
      setProgress(null);
    } finally {
      // Only update state if component is still mounted
      if (isMountedRef.current) {
        setIsSubmitting(false);
        // Clear progress after a short delay to show success message
        setTimeout(() => {
          if (isMountedRef.current) {
            setProgress(null);
          }
        }, 2000);
      }
    }
  };

  const handleError = (errors: any) => {
    console.error("Form validation errors:", errors);
    setSubmitError("Please fix the form errors before submitting.");
  };

  return (
    <Card className={className} variant="outlined">
      <CardHeader
        avatar={<SpawnIcon color="primary" />}
        title="Agent Spawning Interface"
        subheader="Configure and deploy specialized agents for task execution"
        action={
          <Stack direction="row" spacing={1}>
            <Tooltip title="Agent spawning creates specialized task executors with defined roles and domain expertise">
              <IconButton size="small">
                <InfoIcon />
              </IconButton>
            </Tooltip>
          </Stack>
        }
      />

      <CardContent>
        {/* Loading States */}
        {(rolesLoading || domainsLoading) && (
          <Alert severity="info" sx={{ mb: 3 }}>
            Loading agent roles and domain configurations...
          </Alert>
        )}

        {/* Progress Alert */}
        {progress && (
          <Alert severity="info" sx={{ mb: 3 }}>
            {progress}
          </Alert>
        )}

        {/* Error Alert */}
        {submitError && (
          <Alert
            severity="error"
            sx={{ mb: 3 }}
            onClose={() => setSubmitError(null)}
          >
            {submitError}
          </Alert>
        )}

        {/* Form */}
        <FormProvider {...methods}>
          <FormBuilder<FormData>
            sections={formSections}
            onSubmit={handleSubmit}
            onError={handleError}
            loading={isSubmitting}
            disabled={rolesLoading || domainsLoading}
            submitText="Spawn Agent"
            showReset={true}
            resetText="Clear Form"
            mode="onChange"
          />
        </FormProvider>

        {/* Agent Pattern Information */}
        <Divider sx={{ my: 3 }} />

        <Box>
          <Typography
            variant="subtitle2"
            gutterBottom
            sx={{ display: "flex", alignItems: "center", gap: 1 }}
          >
            <ConfigIcon fontSize="small" />
            Agent = Role + Domain Pattern
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Every agent is a composition of a behavioral role (researcher,
            analyst, architect, etc.) and specialized domain knowledge
            (memory-systems, distributed-systems, etc.). This pattern enables
            precise capability matching for complex orchestration tasks.
          </Typography>

          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 2 }}>
            <Chip
              icon={<RoleIcon />}
              label="Role: Behavioral Archetype"
              size="small"
              variant="outlined"
              color="primary"
            />
            <Chip
              icon={<DomainIcon />}
              label="Domain: Knowledge Expertise"
              size="small"
              variant="outlined"
              color="secondary"
            />
            <Chip
              icon={<LaunchIcon />}
              label="Coordination: Multi-Agent Patterns"
              size="small"
              variant="outlined"
              color="success"
            />
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
};
