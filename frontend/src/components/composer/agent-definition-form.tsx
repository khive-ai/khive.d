/**
 * Agent Definition Form Component
 * Focused form for defining agent configuration in the composer studio
 * Implements role+domain pattern with simplified UX for MVP
 */

import React, { useEffect, useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  FormHelperText,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  Info as InfoIcon,
  Preview as PreviewIcon,
  Psychology as RoleIcon,
  School as DomainIcon,
  Speed as QualityIcon,
  Task as TaskIcon,
} from "@mui/icons-material";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useDomains, useRoles } from "@/lib/api/hooks";
import type { AgentDefinition } from "@/app/composer/page";

// Form validation schema
const agentDefinitionSchema = z.object({
  role: z.string().min(1, "Role selection is required"),
  domain: z.string().min(1, "Domain selection is required"),
  taskContext: z.string().min(
    20,
    "Task context must be at least 20 characters",
  ),
  expectedCapabilities: z.array(z.string()).min(
    1,
    "At least one capability is required",
  ),
  qualityGate: z.enum(["basic", "thorough", "critical"]),
  coordinationStrategy: z.enum(["FAN_OUT_SYNTHESIZE", "PIPELINE", "PARALLEL"]),
});

type FormData = z.infer<typeof agentDefinitionSchema>;

interface AgentDefinitionFormProps {
  onAgentDefined: (definition: AgentDefinition) => void;
  initialData?: AgentDefinition | null;
}

// Predefined capability options for quick selection
const commonCapabilities = [
  "Research and Analysis",
  "Code Implementation",
  "Testing and Validation",
  "System Architecture",
  "Documentation Writing",
  "Problem Solving",
  "Pattern Recognition",
  "Data Processing",
  "Quality Assurance",
  "Performance Optimization",
];

// Quality gate descriptions
const qualityGateInfo = {
  basic: "Basic validation - format checking and output validation",
  thorough: "Thorough validation - cross-validation and consistency checking",
  critical:
    "Critical validation - multi-round verification with external checks",
};

// Coordination strategy descriptions
const coordinationStrategyInfo = {
  FAN_OUT_SYNTHESIZE: "Deploy multiple agents, then synthesize their results",
  PIPELINE: "Sequential processing with handoffs between specialized agents",
  PARALLEL: "Independent parallel execution across multiple agents",
};

export const AgentDefinitionForm: React.FC<AgentDefinitionFormProps> = ({
  onAgentDefined,
  initialData,
}) => {
  const [selectedCapabilities, setSelectedCapabilities] = useState<string[]>(
    [],
  );
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  // API hooks for roles and domains
  const { data: roles, isLoading: rolesLoading } = useRoles();
  const { data: domains, isLoading: domainsLoading } = useDomains();

  // Form setup
  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
  } = useForm<FormData>({
    resolver: zodResolver(agentDefinitionSchema),
    defaultValues: {
      role: initialData?.role || "",
      domain: initialData?.domain || "",
      taskContext: initialData?.taskContext || "",
      expectedCapabilities: initialData?.expectedCapabilities || [],
      qualityGate: initialData?.qualityGate || "thorough",
      coordinationStrategy: initialData?.coordinationStrategy ||
        "FAN_OUT_SYNTHESIZE",
    },
  });

  const watchedRole = watch("role");
  const watchedDomain = watch("domain");

  // Update capabilities when role/domain changes
  useEffect(() => {
    if (watchedRole && watchedDomain && !initialData) {
      // Auto-suggest capabilities based on role+domain combination
      const suggestedCapabilities = [];

      if (watchedRole.includes("researcher")) {
        suggestedCapabilities.push("Research and Analysis", "Data Processing");
      }
      if (watchedRole.includes("implementer")) {
        suggestedCapabilities.push("Code Implementation", "Problem Solving");
      }
      if (watchedRole.includes("tester")) {
        suggestedCapabilities.push(
          "Testing and Validation",
          "Quality Assurance",
        );
      }
      if (watchedRole.includes("architect")) {
        suggestedCapabilities.push(
          "System Architecture",
          "Pattern Recognition",
        );
      }

      if (suggestedCapabilities.length > 0) {
        setSelectedCapabilities(suggestedCapabilities);
        setValue("expectedCapabilities", suggestedCapabilities);
      }
    }
  }, [watchedRole, watchedDomain, setValue, initialData]);

  // Handle capability selection
  const handleCapabilityChange = (capabilities: string[]) => {
    setSelectedCapabilities(capabilities);
    setValue("expectedCapabilities", capabilities, { shouldValidate: true });
  };

  // Form submission
  const onSubmit = (data: FormData) => {
    const agentDefinition: AgentDefinition = {
      ...data,
      expectedCapabilities: selectedCapabilities,
    };

    onAgentDefined(agentDefinition);
  };

  // Generate role+domain preview
  const getAgentPreview = () => {
    if (!watchedRole || !watchedDomain) return null;

    const selectedRole = roles?.find((r) => r.name === watchedRole);
    const selectedDomain = domains?.find((d) => d.name === watchedDomain);

    return {
      role: selectedRole,
      domain: selectedDomain,
      composition: `${watchedRole}+${watchedDomain}`,
    };
  };

  const preview = getAgentPreview();

  return (
    <Box>
      {/* Form Header */}
      <Box sx={{ mb: 3 }}>
        <Typography
          variant="subtitle1"
          gutterBottom
          sx={{ display: "flex", alignItems: "center", gap: 1 }}
        >
          <TaskIcon color="primary" />
          Agent Configuration
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Define the agent's behavioral role and domain expertise following the
          Role + Domain pattern.
        </Typography>
      </Box>

      <form onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={3}>
          {/* Role Selection */}
          <Grid item xs={12} md={6}>
            <Controller
              name="role"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth error={!!errors.role}>
                  <InputLabel>Agent Role</InputLabel>
                  <Select
                    {...field}
                    label="Agent Role"
                    disabled={rolesLoading}
                    startAdornment={
                      <RoleIcon sx={{ mr: 1, color: "action.active" }} />
                    }
                  >
                    {roles?.map((role) => (
                      <MenuItem key={role.name} value={role.name}>
                        <Box>
                          <Typography variant="body2" fontWeight={600}>
                            {role.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {role.description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                  <FormHelperText>
                    {errors.role?.message ||
                      "Behavioral archetype that defines agent operations"}
                  </FormHelperText>
                </FormControl>
              )}
            />
          </Grid>

          {/* Domain Selection */}
          <Grid item xs={12} md={6}>
            <Controller
              name="domain"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth error={!!errors.domain}>
                  <InputLabel>Domain Expertise</InputLabel>
                  <Select
                    {...field}
                    label="Domain Expertise"
                    disabled={domainsLoading}
                    startAdornment={
                      <DomainIcon sx={{ mr: 1, color: "action.active" }} />
                    }
                  >
                    {domains?.map((domain) => (
                      <MenuItem key={domain.name} value={domain.name}>
                        <Box>
                          <Typography variant="body2" fontWeight={600}>
                            {domain.name}
                            {domain.parent && (
                              <Chip
                                label={domain.parent}
                                size="small"
                                sx={{ ml: 1, height: 16, fontSize: "0.7rem" }}
                              />
                            )}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {domain.description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                  <FormHelperText>
                    {errors.domain?.message ||
                      "Specialized knowledge area for capability augmentation"}
                  </FormHelperText>
                </FormControl>
              )}
            />
          </Grid>

          {/* Agent Preview */}
          {preview && (
            <Grid item xs={12}>
              <Card variant="outlined" sx={{ backgroundColor: "primary.50" }}>
                <CardContent sx={{ py: 2 }}>
                  <Box
                    display="flex"
                    alignItems="center"
                    justifyContent="space-between"
                  >
                    <Box>
                      <Typography
                        variant="subtitle2"
                        color="primary"
                        gutterBottom
                      >
                        Agent Composition Preview: {preview.composition}
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        <Chip
                          icon={<RoleIcon />}
                          label={`Role: ${preview.role?.name}`}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                        <Chip
                          icon={<DomainIcon />}
                          label={`Domain: ${preview.domain?.name}`}
                          size="small"
                          color="secondary"
                          variant="outlined"
                        />
                      </Stack>
                    </Box>
                    <Tooltip title="View detailed capability matrix">
                      <IconButton
                        onClick={() => setIsPreviewOpen(!isPreviewOpen)}
                        color="primary"
                      >
                        <PreviewIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>

                  {isPreviewOpen && (
                    <Box
                      sx={{
                        mt: 2,
                        p: 2,
                        backgroundColor: "grey.50",
                        borderRadius: 1,
                      }}
                    >
                      <Grid container spacing={2}>
                        <Grid item xs={6}>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            gutterBottom
                          >
                            Role Capabilities
                          </Typography>
                          <Stack spacing={0.5}>
                            {preview.role?.capabilities.slice(0, 3).map((
                              cap,
                              index,
                            ) => (
                              <Typography
                                key={index}
                                variant="body2"
                                fontSize="0.75rem"
                              >
                                • {cap}
                              </Typography>
                            ))}
                          </Stack>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            gutterBottom
                          >
                            Domain Tools
                          </Typography>
                          <Stack spacing={0.5}>
                            {preview.domain?.specializedTools.slice(0, 3).map((
                              tool,
                              index,
                            ) => (
                              <Typography
                                key={index}
                                variant="body2"
                                fontSize="0.75rem"
                              >
                                • {tool}
                              </Typography>
                            ))}
                          </Stack>
                        </Grid>
                      </Grid>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          )}

          {/* Task Context */}
          <Grid item xs={12}>
            <Controller
              name="taskContext"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Task Context"
                  multiline
                  rows={4}
                  fullWidth
                  required
                  error={!!errors.taskContext}
                  helperText={errors.taskContext?.message ||
                    "Describe the specific task or objective this agent will handle"}
                  placeholder="e.g., Research and analyze memory management patterns in distributed systems, focusing on consistency models and performance trade-offs..."
                />
              )}
            />
          </Grid>

          {/* Expected Capabilities */}
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>
              Expected Capabilities
            </Typography>
            <Autocomplete
              multiple
              options={commonCapabilities}
              value={selectedCapabilities}
              onChange={(_, newValue) => handleCapabilityChange(newValue)}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => (
                  <Chip
                    variant="outlined"
                    label={option}
                    size="small"
                    {...getTagProps({ index })}
                    key={option}
                  />
                ))}
              renderInput={(params) => (
                <TextField
                  {...params}
                  placeholder="Select or type capabilities..."
                  error={!!errors.expectedCapabilities}
                  helperText={errors.expectedCapabilities?.message ||
                    "Capabilities this agent should demonstrate during testing"}
                />
              )}
            />
          </Grid>

          {/* Quality Gate */}
          <Grid item xs={12} md={6}>
            <Controller
              name="qualityGate"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth>
                  <InputLabel>Quality Gate</InputLabel>
                  <Select
                    {...field}
                    label="Quality Gate"
                    startAdornment={
                      <QualityIcon sx={{ mr: 1, color: "action.active" }} />
                    }
                  >
                    {Object.entries(qualityGateInfo).map((
                      [value, description],
                    ) => (
                      <MenuItem key={value} value={value}>
                        <Box>
                          <Typography
                            variant="body2"
                            fontWeight={600}
                            textTransform="capitalize"
                          >
                            {value}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                  <FormHelperText>
                    Validation rigor level for capability testing
                  </FormHelperText>
                </FormControl>
              )}
            />
          </Grid>

          {/* Coordination Strategy */}
          <Grid item xs={12} md={6}>
            <Controller
              name="coordinationStrategy"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth>
                  <InputLabel>Coordination Strategy</InputLabel>
                  <Select {...field} label="Coordination Strategy">
                    {Object.entries(coordinationStrategyInfo).map((
                      [value, description],
                    ) => (
                      <MenuItem key={value} value={value}>
                        <Box>
                          <Typography variant="body2" fontWeight={600}>
                            {value.replace(/_/g, " ")}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                  <FormHelperText>
                    How this agent coordinates with others in multi-agent
                    scenarios
                  </FormHelperText>
                </FormControl>
              )}
            />
          </Grid>

          {/* Form Actions */}
          <Grid item xs={12}>
            <Box
              sx={{
                display: "flex",
                justifyContent: "flex-end",
                gap: 2,
                mt: 2,
              }}
            >
              <Button
                type="submit"
                variant="contained"
                disabled={!isValid || rolesLoading || domainsLoading}
                sx={{ minWidth: 140 }}
              >
                {initialData ? "Update Agent" : "Define Agent"}
              </Button>
            </Box>

            {/* Validation Errors */}
            {Object.keys(errors).length > 0 && (
              <Alert severity="error" sx={{ mt: 2 }}>
                Please fix the form errors before proceeding.
              </Alert>
            )}
          </Grid>
        </Grid>
      </form>
    </Box>
  );
};
