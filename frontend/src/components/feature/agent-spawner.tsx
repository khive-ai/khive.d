/**
 * Agent Spawner Component
 * Main interface for spawning agents and managing task orchestrations
 * Implements MVP orchestration center functionality
 */

"use client";

import React, { useEffect, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Autocomplete,
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
} from "@mui/material";
import {
  AccountTree as HierarchyIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  Group as GroupIcon,
  Info as InfoIcon,
  PlayArrow as LaunchIcon,
  Psychology as AgentIcon,
  Settings as ConfigIcon,
  Timeline as PipelineIcon,
} from "@mui/icons-material";
import { Controller, useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useCreateSession, useDomains, useRoles } from "@/lib/api/hooks";
import { Domain, Role } from "@/types";

// Coordination strategies
const coordinationStrategies = [
  {
    value: "FAN_OUT_SYNTHESIZE",
    label: "Fan Out & Synthesize",
    description: "Deploy multiple agents in parallel, then synthesize results",
    icon: <GroupIcon />,
    color: "primary" as const,
  },
  {
    value: "PIPELINE",
    label: "Pipeline",
    description: "Sequential processing with handoffs between agents",
    icon: <PipelineIcon />,
    color: "secondary" as const,
  },
  {
    value: "PARALLEL",
    label: "Parallel",
    description: "Independent parallel execution across agents",
    icon: <HierarchyIcon />,
    color: "success" as const,
  },
];

// Form validation schema
const agentSpawnerSchema = z.object({
  objective: z.string().min(10, "Objective must be at least 10 characters"),
  context: z.string().optional(),
  coordinationStrategy: z.enum(["FAN_OUT_SYNTHESIZE", "PIPELINE", "PARALLEL"]),
  agents: z.array(z.object({
    role: z.string().min(1, "Role is required"),
    domain: z.string().min(1, "Domain is required"),
    specificTask: z.string().optional(),
  })).min(1, "At least one agent is required").max(
    8,
    "Maximum 8 agents allowed",
  ),
  expectedArtifacts: z.array(z.string()).optional(),
  timeoutMinutes: z.number().min(1).max(180).optional(),
});

type AgentSpawnerForm = z.infer<typeof agentSpawnerSchema>;

interface AgentSpawnerProps {
  onSessionCreated?: (sessionId: string) => void;
  className?: string;
}

export const AgentSpawner: React.FC<AgentSpawnerProps> = ({
  onSessionCreated,
  className,
}) => {
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);

  // API hooks
  const { data: roles, isLoading: rolesLoading } = useRoles();
  const { data: domains, isLoading: domainsLoading } = useDomains();
  const createSessionMutation = useCreateSession();

  // Form management
  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
  } = useForm<AgentSpawnerForm>({
    resolver: zodResolver(agentSpawnerSchema),
    defaultValues: {
      objective: "",
      context: "",
      coordinationStrategy: "FAN_OUT_SYNTHESIZE",
      agents: [{ role: "", domain: "", specificTask: "" }],
      expectedArtifacts: [],
      timeoutMinutes: 30,
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "agents",
  });

  const watchedAgents = watch("agents");
  const watchedStrategy = watch("coordinationStrategy");
  const watchedObjective = watch("objective");

  // Get strategy info
  const currentStrategy = coordinationStrategies.find(
    (s) => s.value === watchedStrategy,
  );

  // Auto-suggest roles and domains based on objective
  const suggestAgentsForObjective = (objective: string) => {
    if (!objective || objective.length < 20) return;

    const suggestions = [];
    const objLower = objective.toLowerCase();

    // Basic role suggestions based on keywords
    if (objLower.includes("research") || objLower.includes("analyze")) {
      suggestions.push({ role: "researcher", domain: "software-architecture" });
    }
    if (
      objLower.includes("implement") || objLower.includes("code") ||
      objLower.includes("build")
    ) {
      suggestions.push({
        role: "implementer",
        domain: "software-architecture",
      });
    }
    if (objLower.includes("test") || objLower.includes("validate")) {
      suggestions.push({ role: "tester", domain: "software-architecture" });
    }
    if (objLower.includes("design") || objLower.includes("architecture")) {
      suggestions.push({ role: "architect", domain: "software-architecture" });
    }
    if (objLower.includes("review") || objLower.includes("audit")) {
      suggestions.push({ role: "reviewer", domain: "software-architecture" });
    }

    // Apply suggestions if agents list is minimal
    if (
      suggestions.length > 0 && watchedAgents.length <= 1 &&
      !watchedAgents[0]?.role
    ) {
      setValue("agents", suggestions.slice(0, 3));
    }
  };

  // Debounced objective analysis
  useEffect(() => {
    const timer = setTimeout(() => {
      suggestAgentsForObjective(watchedObjective);
    }, 2000);

    return () => clearTimeout(timer);
  }, [watchedObjective, setValue, watchedAgents]);

  // Add agent
  const addAgent = () => {
    if (fields.length < 8) {
      append({ role: "", domain: "", specificTask: "" });
    }
  };

  // Remove agent
  const removeAgent = (index: number) => {
    if (fields.length > 1) {
      remove(index);
    }
  };

  // Submit form
  const onSubmit = async (data: AgentSpawnerForm) => {
    try {
      // Create session with orchestration plan
      const sessionData = {
        objective: data.objective,
        context:
          `${data.context}\n\nCoordination Strategy: ${data.coordinationStrategy}\nAgents: ${
            data.agents.map((a) => `${a.role}+${a.domain}`).join(", ")
          }`,
        coordinationId: `spawn_${Date.now()}`,
      };

      const response = await createSessionMutation.mutateAsync(sessionData);

      if (response.data?.id) {
        onSessionCreated?.(response.data.id);
      }
    } catch (error) {
      console.error("Failed to create orchestration session:", error);
    }
  };

  return (
    <Card className={className} variant="outlined">
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={2}>
            <AgentIcon color="primary" />
            <Typography variant="h6" fontWeight={600}>
              Agent Spawner
            </Typography>
          </Box>
        }
        subheader="Create new orchestration sessions and deploy agents"
      />

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <Grid container spacing={3}>
            {/* Main Objective */}
            <Grid item xs={12}>
              <Controller
                name="objective"
                control={control}
                render={({ field }) => (
                  <TextField
                    {...field}
                    label="Orchestration Objective"
                    multiline
                    rows={3}
                    fullWidth
                    required
                    error={!!errors.objective}
                    helperText={errors.objective?.message ||
                      "Describe what you want to accomplish with this orchestration"}
                    placeholder="e.g., Implement user authentication system with role-based access control"
                  />
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
                      {coordinationStrategies.map((strategy) => (
                        <MenuItem key={strategy.value} value={strategy.value}>
                          <Box display="flex" alignItems="center" gap={2}>
                            {strategy.icon}
                            <Box>
                              <Typography variant="body2" fontWeight={600}>
                                {strategy.label}
                              </Typography>
                              <Typography
                                variant="caption"
                                color="text.secondary"
                              >
                                {strategy.description}
                              </Typography>
                            </Box>
                          </Box>
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              />
            </Grid>

            {/* Strategy Info */}
            <Grid item xs={12} md={6}>
              {currentStrategy && (
                <Paper sx={{ p: 2, backgroundColor: "grey.50" }}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    {currentStrategy.icon}
                    <Typography variant="subtitle2" fontWeight={600}>
                      {currentStrategy.label}
                    </Typography>
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    {currentStrategy.description}
                  </Typography>
                </Paper>
              )}
            </Grid>

            {/* Agents Configuration */}
            <Grid item xs={12}>
              <Box mb={2}>
                <Box
                  display="flex"
                  alignItems="center"
                  justifyContent="space-between"
                  mb={2}
                >
                  <Typography variant="h6" fontWeight={600}>
                    Agents ({fields.length}/8)
                  </Typography>
                  <Button
                    startIcon={<AddIcon />}
                    onClick={addAgent}
                    disabled={fields.length >= 8}
                    size="small"
                  >
                    Add Agent
                  </Button>
                </Box>

                <Stack spacing={2}>
                  {fields.map((field, index) => (
                    <Card
                      key={field.id}
                      variant="outlined"
                      sx={{ backgroundColor: "grey.25" }}
                    >
                      <CardContent sx={{ py: 2 }}>
                        <Box display="flex" alignItems="center" gap={2} mb={2}>
                          <Typography variant="subtitle2" color="primary">
                            Agent {index + 1}
                          </Typography>
                          {fields.length > 1 && (
                            <Tooltip title="Remove Agent">
                              <IconButton
                                size="small"
                                onClick={() => removeAgent(index)}
                                color="error"
                              >
                                <DeleteIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Box>

                        <Grid container spacing={2}>
                          <Grid item xs={12} sm={4}>
                            <Controller
                              name={`agents.${index}.role`}
                              control={control}
                              render={({ field }) => (
                                <Autocomplete
                                  {...field}
                                  options={roles?.map((r) => r.name) || []}
                                  loading={rolesLoading}
                                  onChange={(_, value) =>
                                    field.onChange(value || "")}
                                  renderInput={(params) => (
                                    <TextField
                                      {...params}
                                      label="Role"
                                      required
                                      error={!!errors.agents?.[index]?.role}
                                      helperText={errors.agents?.[index]?.role
                                        ?.message}
                                    />
                                  )}
                                />
                              )}
                            />
                          </Grid>

                          <Grid item xs={12} sm={4}>
                            <Controller
                              name={`agents.${index}.domain`}
                              control={control}
                              render={({ field }) => (
                                <Autocomplete
                                  {...field}
                                  options={domains?.map((d) => d.name) || []}
                                  loading={domainsLoading}
                                  onChange={(_, value) =>
                                    field.onChange(value || "")}
                                  renderInput={(params) => (
                                    <TextField
                                      {...params}
                                      label="Domain"
                                      required
                                      error={!!errors.agents?.[index]?.domain}
                                      helperText={errors.agents?.[index]?.domain
                                        ?.message}
                                    />
                                  )}
                                />
                              )}
                            />
                          </Grid>

                          <Grid item xs={12} sm={4}>
                            <Controller
                              name={`agents.${index}.specificTask`}
                              control={control}
                              render={({ field }) => (
                                <TextField
                                  {...field}
                                  label="Specific Task (Optional)"
                                  placeholder="Optional task details"
                                  size="small"
                                />
                              )}
                            />
                          </Grid>
                        </Grid>
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              </Box>
            </Grid>

            {/* Advanced Configuration */}
            <Grid item xs={12}>
              <Accordion
                expanded={isAdvancedOpen}
                onChange={(_, expanded) => setIsAdvancedOpen(expanded)}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <ConfigIcon color="action" />
                    <Typography variant="subtitle1" fontWeight={600}>
                      Advanced Configuration
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={3}>
                    <Grid item xs={12}>
                      <Controller
                        name="context"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Additional Context"
                            multiline
                            rows={3}
                            fullWidth
                            helperText="Provide any additional context or constraints for the agents"
                          />
                        )}
                      />
                    </Grid>

                    <Grid item xs={12} sm={6}>
                      <Controller
                        name="timeoutMinutes"
                        control={control}
                        render={({ field }) => (
                          <TextField
                            {...field}
                            label="Timeout (Minutes)"
                            type="number"
                            inputProps={{ min: 1, max: 180 }}
                            helperText="Maximum time for orchestration"
                          />
                        )}
                      />
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>
            </Grid>

            {/* Action Buttons */}
            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
              <Box
                display="flex"
                gap={2}
                justifyContent="space-between"
                alignItems="center"
              >
                <Box>
                  {errors.root && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                      {errors.root.message}
                    </Alert>
                  )}
                </Box>

                <Stack direction="row" spacing={2}>
                  <Button
                    variant="outlined"
                    onClick={() => setPreviewDialogOpen(true)}
                    disabled={!isValid}
                    startIcon={<InfoIcon />}
                  >
                    Preview Plan
                  </Button>

                  <Button
                    type="submit"
                    variant="contained"
                    disabled={!isValid || createSessionMutation.isPending}
                    startIcon={<LaunchIcon />}
                  >
                    {createSessionMutation.isPending
                      ? "Launching..."
                      : "Launch Orchestration"}
                  </Button>
                </Stack>
              </Box>

              {createSessionMutation.isPending && (
                <Box sx={{ mt: 2 }}>
                  <LinearProgress />
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 1, display: "block" }}
                  >
                    Creating orchestration session and deploying agents...
                  </Typography>
                </Box>
              )}

              {createSessionMutation.isError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  Failed to launch orchestration:{" "}
                  {createSessionMutation.error?.message}
                </Alert>
              )}

              {createSessionMutation.isSuccess && (
                <Alert severity="success" sx={{ mt: 2 }}>
                  Orchestration launched successfully! Session ID:{" "}
                  {createSessionMutation.data?.data?.id}
                </Alert>
              )}
            </Grid>
          </Grid>
        </form>

        {/* Preview Dialog */}
        <Dialog
          open={previewDialogOpen}
          onClose={() => setPreviewDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            <Box display="flex" alignItems="center" gap={2}>
              <InfoIcon color="primary" />
              <Typography variant="h6">
                Orchestration Plan Preview
              </Typography>
            </Box>
          </DialogTitle>
          <DialogContent>
            {/* Preview content would go here */}
            <Typography variant="body2" color="text.secondary">
              Preview functionality would show the orchestration plan details.
            </Typography>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setPreviewDialogOpen(false)}>
              Close
            </Button>
          </DialogActions>
        </Dialog>
      </CardContent>
    </Card>
  );
};
