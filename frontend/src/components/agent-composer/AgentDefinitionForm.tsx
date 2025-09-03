/**
 * Agent Definition Form - Role and Domain Selection
 * Architectural Pattern: Form Builder with Real-time Validation
 */

"use client";

import React, { useState } from "react";
import {
  Alert,
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Skeleton,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Domain as DomainIcon,
  Psychology as RoleIcon,
  Settings as ConfigIcon,
} from "@mui/icons-material";

import type { Domain, Role } from "@/lib/types";
import type { AgentComposition } from "./AgentComposer";

interface AgentDefinitionFormProps {
  roles: Role[];
  domains: Domain[];
  composition: AgentComposition;
  onUpdate: (updates: Partial<AgentComposition>) => void;
  isLoading: boolean;
  error: any;
}

export function AgentDefinitionForm({
  roles,
  domains,
  composition,
  onUpdate,
  isLoading,
  error,
}: AgentDefinitionFormProps) {
  const theme = useTheme();
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Handle role selection
  const handleRoleChange = (roleId: string) => {
    const selectedRole = roles.find((role) => role.id === roleId);
    onUpdate({ role: selectedRole || null });
    validateSelection(selectedRole, composition.domain);
  };

  // Handle domain selection
  const handleDomainChange = (domainId: string) => {
    const selectedDomain = domains.find((domain) => domain.id === domainId);
    onUpdate({ domain: selectedDomain || null });
    validateSelection(composition.role, selectedDomain);
  };

  // Handle configuration updates
  const handleConfigurationChange = (field: string, value: number) => {
    onUpdate({
      configuration: {
        ...composition.configuration,
        [field]: value,
      },
    });
  };

  // Validate role + domain combination
  const validateSelection = (
    role: Role | null | undefined,
    domain: Domain | null | undefined,
  ) => {
    const errors: string[] = [];

    if (!role) {
      errors.push("Please select an agent role");
    }

    if (!domain) {
      errors.push("Please select a domain expertise");
    }

    // Check for potential mismatches (architectural decision rule)
    if (role && domain) {
      const roleId = role.id;
      const domainId = domain.id;

      // Warn about potentially ineffective combinations
      if (roleId === "tester" && domainId.includes("strategic")) {
        errors.push(
          "Warning: Testing role may not be optimal for strategic domains",
        );
      }

      if (roleId === "researcher" && domainId.includes("implementation")) {
        errors.push(
          "Warning: Research role may be better suited for analysis domains",
        );
      }
    }

    setValidationErrors(errors);
  };

  if (isLoading) {
    return (
      <Box>
        <Typography variant="h6" gutterBottom>
          Define Agent Composition
        </Typography>
        <Grid container spacing={3}>
          {[1, 2, 3].map((i) => (
            <Grid item xs={12} md={4} key={i}>
              <Skeleton variant="rectangular" height={200} />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        Failed to load roles and domains. Please refresh and try again.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        Define Agent Composition
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        Select a role and domain expertise to compose your intelligent agent
      </Typography>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <Alert
          severity={validationErrors.some((e) => e.startsWith("Warning:"))
            ? "warning"
            : "error"}
          sx={{ mb: 3 }}
        >
          <Typography variant="body2" gutterBottom>
            {validationErrors.filter((e) => !e.startsWith("Warning:")).length >
                0
              ? "Please fix the following issues:"
              : "Please consider the following:"}
          </Typography>
          {validationErrors.map((error, index) => (
            <Typography key={index} variant="body2" component="li">
              {error}
            </Typography>
          ))}
        </Alert>
      )}

      <Grid container spacing={4}>
        {/* Role Selection */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                spacing={1}
                sx={{ mb: 3 }}
              >
                <RoleIcon color="primary" />
                <Typography variant="h6">Agent Role</Typography>
              </Stack>

              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Select Role</InputLabel>
                <Select
                  value={composition.role?.id || ""}
                  onChange={(e) => handleRoleChange(e.target.value)}
                  label="Select Role"
                >
                  {roles.map((role) => (
                    <MenuItem key={role.id} value={role.id}>
                      {role.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {composition.role && (
                <Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    {composition.role.description}
                  </Typography>

                  {composition.role.capabilities.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ mb: 1, display: "block" }}
                      >
                        Core Capabilities:
                      </Typography>
                      <Stack
                        direction="row"
                        spacing={1}
                        flexWrap="wrap"
                        useFlexGap
                      >
                        {composition.role.capabilities.slice(0, 3).map((
                          capability,
                        ) => (
                          <Chip
                            key={capability}
                            label={capability}
                            size="small"
                            variant="outlined"
                            color="primary"
                          />
                        ))}
                        {composition.role.capabilities.length > 3 && (
                          <Chip
                            label={`+${
                              composition.role.capabilities.length - 3
                            } more`}
                            size="small"
                            variant="outlined"
                            color="default"
                          />
                        )}
                      </Stack>
                    </Box>
                  )}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Domain Selection */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                spacing={1}
                sx={{ mb: 3 }}
              >
                <DomainIcon color="secondary" />
                <Typography variant="h6">Domain Expertise</Typography>
              </Stack>

              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Select Domain</InputLabel>
                <Select
                  value={composition.domain?.id || ""}
                  onChange={(e) => handleDomainChange(e.target.value)}
                  label="Select Domain"
                >
                  {domains.map((domain) => (
                    <MenuItem key={domain.id} value={domain.id}>
                      {domain.name}
                      {domain.parent && (
                        <Typography
                          component="span"
                          variant="caption"
                          color="text.secondary"
                          sx={{ ml: 1 }}
                        >
                          ({domain.parent})
                        </Typography>
                      )}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              {composition.domain && (
                <Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    {composition.domain.description}
                  </Typography>

                  {composition.domain.specializedTools.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ mb: 1, display: "block" }}
                      >
                        Specialized Tools:
                      </Typography>
                      <Stack
                        direction="row"
                        spacing={1}
                        flexWrap="wrap"
                        useFlexGap
                      >
                        {composition.domain.specializedTools.slice(0, 3).map((
                          tool,
                        ) => (
                          <Chip
                            key={tool}
                            label={tool}
                            size="small"
                            variant="outlined"
                            color="secondary"
                          />
                        ))}
                        {composition.domain.specializedTools.length > 3 && (
                          <Chip
                            label={`+${
                              composition.domain.specializedTools.length - 3
                            } more`}
                            size="small"
                            variant="outlined"
                            color="default"
                          />
                        )}
                      </Stack>
                    </Box>
                  )}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Configuration */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                spacing={1}
                sx={{ mb: 3 }}
              >
                <ConfigIcon color="action" />
                <Typography variant="h6">Agent Configuration</Typography>
              </Stack>

              <Grid container spacing={3}>
                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Max Concurrent Tasks"
                    value={composition.configuration.maxConcurrentTasks}
                    onChange={(e) =>
                      handleConfigurationChange(
                        "maxConcurrentTasks",
                        parseInt(e.target.value) || 3,
                      )}
                    inputProps={{ min: 1, max: 10 }}
                    helperText="Maximum number of parallel tasks"
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Timeout (seconds)"
                    value={composition.configuration.timeout}
                    onChange={(e) =>
                      handleConfigurationChange(
                        "timeout",
                        parseInt(e.target.value) || 300,
                      )}
                    inputProps={{ min: 30, max: 1800 }}
                    helperText="Task execution timeout"
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Retry Count"
                    value={composition.configuration.retryCount}
                    onChange={(e) =>
                      handleConfigurationChange(
                        "retryCount",
                        parseInt(e.target.value) || 3,
                      )}
                    inputProps={{ min: 0, max: 10 }}
                    helperText="Number of retry attempts"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Composition Preview */}
        {composition.role && composition.domain && (
          <Grid item xs={12}>
            <Paper
              sx={{
                p: 3,
                bgcolor: alpha(theme.palette.success.main, 0.1),
                border: `1px solid ${alpha(theme.palette.success.main, 0.3)}`,
              }}
            >
              <Typography variant="h6" color="success.main" gutterBottom>
                Agent Composition Preview
              </Typography>
              <Typography variant="body1" sx={{ mb: 2 }}>
                <strong>{composition.role.name}</strong> +{" "}
                <strong>{composition.domain.name}</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                This combination will create an agent specialized in{" "}
                {composition.domain.name.toLowerCase()}
                with the behavioral patterns and capabilities of a{" "}
                {composition.role.name.toLowerCase()}.
              </Typography>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}

export default AgentDefinitionForm;
