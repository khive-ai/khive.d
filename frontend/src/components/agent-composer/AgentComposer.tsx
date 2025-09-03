/**
 * Agent Composer Studio - Core Component
 * Architectural Design: Layered composition with real-time capability preview
 */

"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  alpha,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Grid,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Build as BuildIcon,
  CheckCircle as CompleteIcon,
  PlayArrow as TestIcon,
  Psychology as AgentIcon,
} from "@mui/icons-material";

import { useDomains, useRoles } from "@/lib/api/hooks";
import type { Domain, Role } from "@/lib/types";

import { AgentDefinitionForm } from "./AgentDefinitionForm";
import { CapabilityPreview } from "./CapabilityPreview";
import { AgentTestingInterface } from "./AgentTestingInterface";
import { AgentCompositionResult } from "./AgentCompositionResult";

// Agent composition data structure
export interface AgentComposition {
  id?: string;
  role: Role | null;
  domain: Domain | null;
  capabilities: string[];
  configuration: {
    maxConcurrentTasks: number;
    timeout: number;
    retryCount: number;
  };
  testResults?: {
    passed: number;
    failed: number;
    score: number;
  };
}

// Composition steps for the wizard interface
const COMPOSITION_STEPS = [
  { label: "Define Agent", icon: AgentIcon },
  { label: "Review Capabilities", icon: BuildIcon },
  { label: "Test Agent", icon: TestIcon },
  { label: "Complete", icon: CompleteIcon },
];

interface AgentComposerProps {
  onAgentComposed?: (composition: AgentComposition) => void;
  initialComposition?: Partial<AgentComposition>;
}

export function AgentComposer({
  onAgentComposed,
  initialComposition = {},
}: AgentComposerProps) {
  const theme = useTheme();
  const [activeStep, setActiveStep] = useState(0);
  const [composition, setComposition] = useState<AgentComposition>({
    role: null,
    domain: null,
    capabilities: [],
    configuration: {
      maxConcurrentTasks: 3,
      timeout: 300,
      retryCount: 3,
    },
    ...initialComposition,
  });

  // Fetch available roles and domains
  const { data: roles, isLoading: rolesLoading, error: rolesError } =
    useRoles();
  const { data: domains, isLoading: domainsLoading, error: domainsError } =
    useDomains();

  const isLoading = rolesLoading || domainsLoading;
  const hasError = rolesError || domainsError;

  // Calculate predicted capabilities based on role + domain selection
  const predictedCapabilities = useMemo(() => {
    if (!composition.role || !composition.domain) return [];

    const capabilities = new Set<string>();

    // Add role-based capabilities
    if (composition.role.capabilities) {
      composition.role.capabilities.forEach((cap) => capabilities.add(cap));
    }

    // Add domain-specific tools and patterns
    if (composition.domain.specializedTools) {
      composition.domain.specializedTools.forEach((tool) =>
        capabilities.add(tool)
      );
    }

    // Add cross-functional capabilities based on role + domain combination
    const roleId = composition.role.id;
    const domainId = composition.domain.id;

    // Pattern-based capability inference (architectural decision)
    if (roleId === "architect" && domainId.includes("architecture")) {
      capabilities.add("system_design");
      capabilities.add("interface_contracts");
      capabilities.add("component_modeling");
    }

    if (roleId === "implementer" && domainId.includes("frontend")) {
      capabilities.add("component_implementation");
      capabilities.add("ui_testing");
      capabilities.add("responsive_design");
    }

    return Array.from(capabilities).sort();
  }, [composition.role, composition.domain]);

  // Update composition when capabilities change
  useEffect(() => {
    setComposition((prev) => ({
      ...prev,
      capabilities: predictedCapabilities,
    }));
  }, [predictedCapabilities]);

  // Handle role/domain selection updates
  const handleCompositionUpdate = (updates: Partial<AgentComposition>) => {
    setComposition((prev) => ({ ...prev, ...updates }));
  };

  // Navigate between steps
  const handleNext = () => {
    if (activeStep < COMPOSITION_STEPS.length - 1) {
      setActiveStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep((prev) => prev - 1);
    }
  };

  // Complete agent composition
  const handleComplete = () => {
    const finalComposition = {
      ...composition,
      id: `${composition.role?.id}_${composition.domain?.id}_${Date.now()}`,
    };

    onAgentComposed?.(finalComposition);
  };

  // Validate current step
  const isStepValid = (step: number) => {
    switch (step) {
      case 0:
        return composition.role && composition.domain;
      case 1:
        return composition.capabilities.length > 0;
      case 2:
        return true; // Testing is optional
      case 3:
        return true;
      default:
        return false;
    }
  };

  // Render step content
  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <AgentDefinitionForm
            roles={roles || []}
            domains={domains || []}
            composition={composition}
            onUpdate={handleCompositionUpdate}
            isLoading={isLoading}
            error={hasError}
          />
        );

      case 1:
        return (
          <CapabilityPreview
            composition={composition}
            onUpdate={handleCompositionUpdate}
          />
        );

      case 2:
        return (
          <AgentTestingInterface
            composition={composition}
            onTestComplete={(results) =>
              handleCompositionUpdate({ testResults: results })}
          />
        );

      case 3:
        return (
          <AgentCompositionResult
            composition={composition}
            onComplete={handleComplete}
          />
        );

      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight={400}
      >
        <Stack alignItems="center" spacing={2}>
          <CircularProgress size={48} />
          <Typography variant="body1" color="text.secondary">
            Loading agent composition resources...
          </Typography>
        </Stack>
      </Box>
    );
  }

  if (hasError) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Failed to Load Composition Resources
        </Typography>
        <Typography variant="body2">
          Unable to load roles or domains. Please check your connection and try
          again.
        </Typography>
      </Alert>
    );
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: "auto", p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          component="h1"
          gutterBottom
          sx={{ fontWeight: 700 }}
        >
          Agent Composer Studio
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Compose intelligent agents by combining roles with domain expertise
        </Typography>
      </Box>

      {/* Progress Stepper */}
      <Paper sx={{ mb: 4, p: 3 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {COMPOSITION_STEPS.map((step, index) => {
            const StepIcon = step.icon;
            return (
              <Step key={step.label} completed={index < activeStep}>
                <StepLabel
                  StepIconComponent={() => (
                    <Box
                      sx={{
                        width: 40,
                        height: 40,
                        borderRadius: "50%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        backgroundColor: index <= activeStep
                          ? theme.palette.primary.main
                          : alpha(theme.palette.grey[400], 0.5),
                        color: index <= activeStep
                          ? theme.palette.primary.contrastText
                          : theme.palette.text.secondary,
                      }}
                    >
                      <StepIcon sx={{ fontSize: 20 }} />
                    </Box>
                  )}
                >
                  {step.label}
                </StepLabel>
              </Step>
            );
          })}
        </Stepper>
      </Paper>

      {/* Step Content */}
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 4 }}>
          {renderStepContent()}
        </CardContent>
      </Card>

      {/* Navigation Controls */}
      <Paper sx={{ p: 3 }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
        >
          <Button
            onClick={handleBack}
            disabled={activeStep === 0}
            variant="outlined"
          >
            Back
          </Button>

          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="body2" color="text.secondary">
              Step {activeStep + 1} of {COMPOSITION_STEPS.length}
            </Typography>
          </Box>

          {activeStep === COMPOSITION_STEPS.length - 1
            ? (
              <Button
                onClick={handleComplete}
                variant="contained"
                size="large"
                disabled={!isStepValid(activeStep)}
                startIcon={<CompleteIcon />}
              >
                Complete Composition
              </Button>
            )
            : (
              <Button
                onClick={handleNext}
                variant="contained"
                disabled={!isStepValid(activeStep)}
              >
                Next
              </Button>
            )}
        </Stack>
      </Paper>
    </Box>
  );
}

export default AgentComposer;
