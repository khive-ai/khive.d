/**
 * Agent Composition Result - Final Configuration Display
 * Architectural Pattern: Summary View with Action Confirmation
 */

"use client";

import React from "react";
import {
  Alert,
  alpha,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Build as ConfigIcon,
  CheckCircle as SuccessIcon,
  ContentCopy as CopyIcon,
  Download as ExportIcon,
  Launch as DeployIcon,
  Psychology as AgentIcon,
  Speed as PerformanceIcon,
} from "@mui/icons-material";

import type { AgentComposition } from "./AgentComposer";

interface AgentCompositionResultProps {
  composition: AgentComposition;
  onComplete: () => void;
}

export function AgentCompositionResult(
  { composition, onComplete }: AgentCompositionResultProps,
) {
  const theme = useTheme();

  // Generate agent configuration export
  const generateExportConfig = () => {
    return JSON.stringify(
      {
        agentId: composition.id,
        role: composition.role?.id,
        domain: composition.domain?.id,
        capabilities: composition.capabilities,
        configuration: composition.configuration,
        metadata: {
          createdAt: new Date().toISOString(),
          version: "1.0.0",
          type: "agent_composition",
        },
      },
      null,
      2,
    );
  };

  // Copy configuration to clipboard
  const handleCopyConfig = async () => {
    try {
      await navigator.clipboard.writeText(generateExportConfig());
      // In a real implementation, you'd show a toast notification
      console.log("Configuration copied to clipboard");
    } catch (error) {
      console.error("Failed to copy to clipboard:", error);
    }
  };

  // Export configuration as file
  const handleExportConfig = () => {
    const config = generateExportConfig();
    const blob = new Blob([config], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download =
      `agent-${composition.role?.id}-${composition.domain?.id}-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const testResults = composition.testResults;
  const hasTestResults = testResults &&
    (testResults.passed > 0 || testResults.failed > 0);

  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ mb: 3 }}>
        Agent Composition Complete
      </Typography>

      {/* Success Header */}
      <Paper
        sx={{
          p: 3,
          mb: 4,
          bgcolor: alpha(theme.palette.success.main, 0.1),
          border: `1px solid ${alpha(theme.palette.success.main, 0.3)}`,
          textAlign: "center",
        }}
      >
        <SuccessIcon sx={{ fontSize: 48, color: "success.main", mb: 2 }} />
        <Typography variant="h5" color="success.main" gutterBottom>
          Agent Successfully Composed
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Your {composition.role?.name} agent specialized in{" "}
          {composition.domain?.name} is ready for deployment
        </Typography>
      </Paper>

      <Grid container spacing={4}>
        {/* Agent Summary */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Stack
                direction="row"
                alignItems="center"
                spacing={1}
                sx={{ mb: 3 }}
              >
                <AgentIcon color="primary" />
                <Typography variant="h6">Agent Summary</Typography>
              </Stack>

              <Stack spacing={3}>
                <Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Agent ID
                  </Typography>
                  <Typography variant="body1" fontFamily="monospace">
                    {composition.id || "Generated on deployment"}
                  </Typography>
                </Box>

                <Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Role & Domain Combination
                  </Typography>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Chip
                      label={composition.role?.name || "Unknown Role"}
                      color="primary"
                      variant="outlined"
                    />
                    <Typography variant="body2" color="text.secondary">
                      +
                    </Typography>
                    <Chip
                      label={composition.domain?.name || "Unknown Domain"}
                      color="secondary"
                      variant="outlined"
                    />
                  </Stack>
                </Box>

                <Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Capabilities ({composition.capabilities.length})
                  </Typography>
                  <Stack
                    direction="row"
                    spacing={0.5}
                    flexWrap="wrap"
                    useFlexGap
                  >
                    {composition.capabilities.slice(0, 6).map((
                      capability,
                      index,
                    ) => (
                      <Chip
                        key={index}
                        label={capability}
                        size="small"
                        variant="outlined"
                        color="default"
                      />
                    ))}
                    {composition.capabilities.length > 6 && (
                      <Chip
                        label={`+${composition.capabilities.length - 6} more`}
                        size="small"
                        variant="outlined"
                        color="default"
                      />
                    )}
                  </Stack>
                </Box>

                <Divider />

                <Box>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    gutterBottom
                  >
                    Description
                  </Typography>
                  <Typography variant="body2">
                    This agent combines the behavioral patterns and
                    decision-making capabilities of a{" "}
                    {composition.role?.name.toLowerCase()}{" "}
                    with specialized expertise in{" "}
                    {composition.domain?.name.toLowerCase()}. It is optimized
                    for tasks that require both{" "}
                    {composition.role?.name.toLowerCase()}{" "}
                    thinking and deep domain knowledge.
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Configuration & Performance */}
        <Grid item xs={12} md={6}>
          <Stack spacing={3}>
            {/* Configuration */}
            <Card>
              <CardContent>
                <Stack
                  direction="row"
                  alignItems="center"
                  spacing={1}
                  sx={{ mb: 3 }}
                >
                  <ConfigIcon color="action" />
                  <Typography variant="h6">Configuration</Typography>
                </Stack>

                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Max Concurrent Tasks
                    </Typography>
                    <Typography variant="h6">
                      {composition.configuration.maxConcurrentTasks}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Timeout
                    </Typography>
                    <Typography variant="h6">
                      {composition.configuration.timeout}s
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Retry Count
                    </Typography>
                    <Typography variant="h6">
                      {composition.configuration.retryCount}
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="body2" color="text.secondary">
                      Version
                    </Typography>
                    <Typography variant="h6">
                      1.0.0
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            {/* Test Results */}
            {hasTestResults && (
              <Card>
                <CardContent>
                  <Stack
                    direction="row"
                    alignItems="center"
                    spacing={1}
                    sx={{ mb: 3 }}
                  >
                    <PerformanceIcon color="primary" />
                    <Typography variant="h6">Test Results</Typography>
                  </Stack>

                  <Grid container spacing={2}>
                    <Grid item xs={4}>
                      <Paper
                        sx={{
                          p: 2,
                          textAlign: "center",
                          bgcolor: alpha(theme.palette.success.main, 0.1),
                        }}
                      >
                        <Typography variant="h4" color="success.main">
                          {testResults!.passed}
                        </Typography>
                        <Typography variant="caption">Passed</Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={4}>
                      <Paper
                        sx={{
                          p: 2,
                          textAlign: "center",
                          bgcolor: alpha(theme.palette.error.main, 0.1),
                        }}
                      >
                        <Typography variant="h4" color="error.main">
                          {testResults!.failed}
                        </Typography>
                        <Typography variant="caption">Failed</Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={4}>
                      <Paper
                        sx={{
                          p: 2,
                          textAlign: "center",
                          bgcolor: alpha(theme.palette.primary.main, 0.1),
                        }}
                      >
                        <Typography variant="h4" color="primary.main">
                          {testResults!.score}
                        </Typography>
                        <Typography variant="caption">Score</Typography>
                      </Paper>
                    </Grid>
                  </Grid>

                  {testResults!.score >= 80
                    ? (
                      <Alert severity="success" sx={{ mt: 2 }}>
                        Excellent performance! This agent is ready for
                        production deployment.
                      </Alert>
                    )
                    : testResults!.score >= 60
                    ? (
                      <Alert severity="warning" sx={{ mt: 2 }}>
                        Good performance with some limitations. Consider
                        additional testing.
                      </Alert>
                    )
                    : (
                      <Alert severity="error" sx={{ mt: 2 }}>
                        Performance needs improvement. Review role/domain
                        combination.
                      </Alert>
                    )}
                </CardContent>
              </Card>
            )}
          </Stack>
        </Grid>

        {/* Export Options */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Export & Deploy Options
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Save your agent configuration or deploy it to the orchestration
                system
              </Typography>

              <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
                <Tooltip title="Copy configuration to clipboard">
                  <Button
                    variant="outlined"
                    startIcon={<CopyIcon />}
                    onClick={handleCopyConfig}
                  >
                    Copy Config
                  </Button>
                </Tooltip>

                <Tooltip title="Download configuration file">
                  <Button
                    variant="outlined"
                    startIcon={<ExportIcon />}
                    onClick={handleExportConfig}
                  >
                    Export JSON
                  </Button>
                </Tooltip>

                <Tooltip title="Deploy to orchestration system">
                  <Button
                    variant="contained"
                    startIcon={<DeployIcon />}
                    onClick={onComplete}
                    color="primary"
                  >
                    Complete Composition
                  </Button>
                </Tooltip>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Next Steps */}
        <Grid item xs={12}>
          <Alert severity="info">
            <Typography variant="body2" gutterBottom>
              <strong>Next Steps:</strong>
            </Typography>
            <Typography variant="body2" component="div">
              <ul style={{ margin: 0, paddingLeft: "1.2em" }}>
                <li>
                  The agent configuration has been validated and is ready for
                  use
                </li>
                <li>
                  You can deploy this agent to handle tasks in the orchestration
                  system
                </li>
                <li>
                  Monitor performance in production and adjust configuration as
                  needed
                </li>
                <li>
                  Consider creating variations with different domains for
                  specialized tasks
                </li>
              </ul>
            </Typography>
          </Alert>
        </Grid>
      </Grid>
    </Box>
  );
}

export default AgentCompositionResult;
