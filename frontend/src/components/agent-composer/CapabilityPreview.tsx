/**
 * Capability Preview - Real-time Capability Inference
 * Architectural Pattern: Observer Pattern with Capability Synthesis
 */

"use client";

import React, { useMemo } from "react";
import {
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Build as CapabilityIcon,
  Psychology as CognitiveIcon,
  Speed as PerformanceIcon,
  TrendingUp as StrengthIcon,
  Warning as LimitationIcon,
} from "@mui/icons-material";

import type { AgentComposition } from "./AgentComposer";

interface AgentCapability {
  name: string;
  description: string;
  type: "analysis" | "execution" | "coordination" | "validation";
  confidence: number;
  source: "role" | "domain" | "synthesis";
}

interface CapabilityPreviewProps {
  composition: AgentComposition;
  onUpdate: (updates: Partial<AgentComposition>) => void;
}

export function CapabilityPreview(
  { composition, onUpdate }: CapabilityPreviewProps,
) {
  const theme = useTheme();

  // Synthesize detailed capabilities from role + domain combination
  const synthesizedCapabilities = useMemo((): AgentCapability[] => {
    if (!composition.role || !composition.domain) return [];

    const capabilities: AgentCapability[] = [];

    // Role-based capabilities
    const roleCapabilities = composition.role.capabilities || [];
    roleCapabilities.forEach((cap) => {
      capabilities.push({
        name: cap,
        description: `Core capability inherited from ${
          composition.role!.name
        } role`,
        type: inferCapabilityType(cap),
        confidence: 0.9,
        source: "role",
      });
    });

    // Domain-specific capabilities
    const domainTools = composition.domain.specializedTools || [];
    domainTools.forEach((tool) => {
      capabilities.push({
        name: tool,
        description: `Specialized tool from ${composition.domain!.name} domain`,
        type: inferCapabilityType(tool),
        confidence: 0.8,
        source: "domain",
      });
    });

    // Synthetic capabilities based on role + domain combination
    const syntheticCaps = generateSyntheticCapabilities(
      composition.role,
      composition.domain,
    );
    capabilities.push(...syntheticCaps);

    return capabilities.sort((a, b) => b.confidence - a.confidence);
  }, [composition.role, composition.domain]);

  // Infer capability type from name (architectural decision rule)
  function inferCapabilityType(
    capabilityName: string,
  ): AgentCapability["type"] {
    const name = capabilityName.toLowerCase();
    if (
      name.includes("analy") || name.includes("research") ||
      name.includes("insight")
    ) {
      return "analysis";
    }
    if (
      name.includes("implement") || name.includes("build") ||
      name.includes("create")
    ) {
      return "execution";
    }
    if (
      name.includes("coordinate") || name.includes("manage") ||
      name.includes("orchestrate")
    ) {
      return "coordination";
    }
    if (
      name.includes("test") || name.includes("review") ||
      name.includes("validate")
    ) {
      return "validation";
    }
    return "execution"; // default
  }

  // Generate synthetic capabilities based on role + domain synergy
  function generateSyntheticCapabilities(
    role: any,
    domain: any,
  ): AgentCapability[] {
    const roleId = role.id;
    const domainId = domain.id;
    const synthetic: AgentCapability[] = [];

    // Architectural decision: Pattern-based capability synthesis
    if (roleId === "architect" && domainId.includes("software")) {
      synthetic.push({
        name: "System Blueprint Generation",
        description: "Creates comprehensive system architecture blueprints",
        type: "execution",
        confidence: 0.95,
        source: "synthesis",
      });
      synthetic.push({
        name: "Interface Contract Design",
        description: "Designs clear component interfaces and contracts",
        type: "execution",
        confidence: 0.9,
        source: "synthesis",
      });
    }

    if (roleId === "implementer" && domainId.includes("frontend")) {
      synthetic.push({
        name: "Component Implementation",
        description: "Implements React components following design patterns",
        type: "execution",
        confidence: 0.92,
        source: "synthesis",
      });
      synthetic.push({
        name: "UI/UX Integration",
        description: "Integrates user interface with backend systems",
        type: "execution",
        confidence: 0.85,
        source: "synthesis",
      });
    }

    if (roleId === "tester" && domainId.includes("quality")) {
      synthetic.push({
        name: "Automated Test Generation",
        description: "Creates comprehensive test suites and scenarios",
        type: "validation",
        confidence: 0.88,
        source: "synthesis",
      });
    }

    return synthetic;
  }

  // Calculate capability distribution
  const capabilityStats = useMemo(() => {
    const typeCount = {
      analysis: 0,
      execution: 0,
      coordination: 0,
      validation: 0,
    };

    synthesizedCapabilities.forEach((cap) => {
      typeCount[cap.type]++;
    });

    const total = synthesizedCapabilities.length;
    return {
      analysis: Math.round((typeCount.analysis / total) * 100),
      execution: Math.round((typeCount.execution / total) * 100),
      coordination: Math.round((typeCount.coordination / total) * 100),
      validation: Math.round((typeCount.validation / total) * 100),
    };
  }, [synthesizedCapabilities]);

  // Overall agent strength assessment
  const strengthAssessment = useMemo(() => {
    if (!composition.role || !composition.domain) return null;

    const avgConfidence = synthesizedCapabilities.reduce((sum, cap) =>
      sum + cap.confidence, 0) / synthesizedCapabilities.length;
    const capabilityCount = synthesizedCapabilities.length;

    let strength = "Moderate";
    let color: "success" | "warning" | "error" = "warning";

    if (avgConfidence > 0.9 && capabilityCount > 8) {
      strength = "Excellent";
      color = "success";
    } else if (avgConfidence > 0.8 && capabilityCount > 6) {
      strength = "Good";
      color = "success";
    } else if (avgConfidence < 0.6 || capabilityCount < 4) {
      strength = "Limited";
      color = "error";
    }

    return {
      strength,
      color,
      confidence: avgConfidence,
      count: capabilityCount,
    };
  }, [synthesizedCapabilities, composition.role, composition.domain]);

  if (!composition.role || !composition.domain) {
    return (
      <Box textAlign="center" py={8}>
        <CognitiveIcon sx={{ fontSize: 48, color: "text.disabled", mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          Select Role and Domain
        </Typography>
        <Typography variant="body2" color="text.disabled">
          Capability preview will appear when both role and domain are selected
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        Capability Preview
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        Predicted capabilities based on {composition.role.name} +{" "}
        {composition.domain.name} combination
      </Typography>

      <Grid container spacing={4}>
        {/* Strength Assessment */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                spacing={2}
                sx={{ mb: 3 }}
              >
                <StrengthIcon color={strengthAssessment?.color || "action"} />
                <Typography variant="h6">Agent Strength Assessment</Typography>
                <Chip
                  label={strengthAssessment?.strength || "Unknown"}
                  color={strengthAssessment?.color || "default"}
                  variant="outlined"
                />
              </Stack>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Overall Confidence
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={(strengthAssessment?.confidence || 0) * 100}
                    color={strengthAssessment?.color || "primary"}
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {Math.round((strengthAssessment?.confidence || 0) * 100)}%
                  </Typography>
                </Grid>

                <Grid item xs={12} sm={4}>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Capability Count
                  </Typography>
                  <Typography
                    variant="h4"
                    color={strengthAssessment?.color + ".main"}
                  >
                    {strengthAssessment?.count || 0}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Total capabilities
                  </Typography>
                </Grid>

                <Grid item xs={12} sm={4}>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Specialization
                  </Typography>
                  <Typography variant="body1" fontWeight="medium">
                    {Object.entries(capabilityStats).reduce((a, b) =>
                      capabilityStats[a[0]] > capabilityStats[b[0]] ? a : b
                    )[0]}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Primary strength
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Capability Distribution */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                spacing={1}
                sx={{ mb: 3 }}
              >
                <PerformanceIcon color="primary" />
                <Typography variant="h6">Capability Distribution</Typography>
              </Stack>

              <Stack spacing={3}>
                {Object.entries(capabilityStats).map(([type, percentage]) => (
                  <Box key={type}>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      alignItems="center"
                      sx={{ mb: 1 }}
                    >
                      <Typography
                        variant="body2"
                        sx={{ textTransform: "capitalize" }}
                      >
                        {type}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {percentage}%
                      </Typography>
                    </Stack>
                    <LinearProgress
                      variant="determinate"
                      value={percentage}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        bgcolor: alpha(theme.palette.grey[300], 0.3),
                      }}
                    />
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Detailed Capabilities */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                spacing={1}
                sx={{ mb: 3 }}
              >
                <CapabilityIcon color="secondary" />
                <Typography variant="h6">Detailed Capabilities</Typography>
              </Stack>

              <Stack spacing={2} sx={{ maxHeight: 400, overflow: "auto" }}>
                {synthesizedCapabilities.map((capability, index) => (
                  <Paper
                    key={index}
                    sx={{
                      p: 2,
                      bgcolor: alpha(
                        theme.palette[
                          capability.source === "role"
                            ? "primary"
                            : capability.source === "domain"
                            ? "secondary"
                            : "success"
                        ].main,
                        0.05,
                      ),
                      border: `1px solid ${
                        alpha(
                          theme.palette[
                            capability.source === "role"
                              ? "primary"
                              : capability.source === "domain"
                              ? "secondary"
                              : "success"
                          ].main,
                          0.2,
                        )
                      }`,
                    }}
                  >
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      alignItems="flex-start"
                      sx={{ mb: 1 }}
                    >
                      <Typography variant="body2" fontWeight="medium">
                        {capability.name}
                      </Typography>
                      <Stack direction="row" spacing={1}>
                        <Chip
                          label={capability.type}
                          size="small"
                          variant="outlined"
                          color={capability.type === "analysis"
                            ? "primary"
                            : capability.type === "execution"
                            ? "success"
                            : capability.type === "coordination"
                            ? "warning"
                            : "info"}
                        />
                        <Tooltip
                          title={`${
                            Math.round(capability.confidence * 100)
                          }% confidence`}
                        >
                          <LinearProgress
                            variant="determinate"
                            value={capability.confidence * 100}
                            sx={{ width: 40, height: 4, borderRadius: 2 }}
                          />
                        </Tooltip>
                      </Stack>
                    </Stack>
                    <Typography variant="caption" color="text.secondary">
                      {capability.description}
                    </Typography>
                  </Paper>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Potential Limitations */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                spacing={1}
                sx={{ mb: 2 }}
              >
                <LimitationIcon color="warning" />
                <Typography variant="h6">
                  Considerations & Limitations
                </Typography>
              </Stack>

              <Stack spacing={1}>
                <Typography variant="body2" color="text.secondary">
                  • This agent will excel in{" "}
                  {Object.entries(capabilityStats).reduce((a, b) =>
                    capabilityStats[a[0]] > capabilityStats[b[0]] ? a : b
                  )[0]} tasks
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Limited capabilities in{" "}
                  {Object.entries(capabilityStats).reduce((a, b) =>
                    capabilityStats[a[0]] < capabilityStats[b[0]] ? a : b
                  )[0]} compared to other areas
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Performance will depend on task complexity and
                  domain-specific context
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Consider testing with sample tasks before production
                  deployment
                </Typography>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default CapabilityPreview;
