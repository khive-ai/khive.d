/**
 * Agent Test Results Component
 * Display comprehensive test results with recommendations for agent deployment
 * Implements agentic-systems analysis patterns for result interpretation
 */

import React from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  LinearProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import {
  Assessment as MetricsIcon,
  CheckCircle as PassIcon,
  Error as FailIcon,
  ExpandMore as ExpandIcon,
  Lightbulb as RecommendationIcon,
  Speed as PerformanceIcon,
  TrendingUp as TrendIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

import type { AgentDefinition, TestResults } from "@/app/composer/page";

interface AgentTestResultsProps {
  testResults: TestResults;
  agentDefinition: AgentDefinition;
}

export const AgentTestResults: React.FC<AgentTestResultsProps> = ({
  testResults,
  agentDefinition,
}) => {
  // Calculate deployment readiness
  const getDeploymentReadiness = () => {
    const { metrics, overall } = testResults;

    if (overall === "passed" && metrics.capabilityScore >= 80) {
      return {
        status: "ready",
        message: "Agent is ready for deployment",
        color: "success",
      };
    } else if (overall === "partial" && metrics.capabilityScore >= 60) {
      return {
        status: "caution",
        message: "Agent may be deployed with monitoring",
        color: "warning",
      };
    } else {
      return {
        status: "not_ready",
        message: "Agent needs improvement before deployment",
        color: "error",
      };
    }
  };

  const deploymentStatus = getDeploymentReadiness();

  // Get status icon for overall result
  const getOverallStatusIcon = () => {
    switch (testResults.overall) {
      case "passed":
        return <PassIcon color="success" fontSize="large" />;
      case "partial":
        return <WarningIcon color="warning" fontSize="large" />;
      case "failed":
        return <FailIcon color="error" fontSize="large" />;
      default:
        return null;
    }
  };

  // Get color for metric values
  const getMetricColor = (
    value: number,
    type: "percentage" | "score" | "time",
  ) => {
    if (type === "percentage") {
      return value >= 0.8 ? "success" : value >= 0.6 ? "warning" : "error";
    } else if (type === "score") {
      return value >= 80 ? "success" : value >= 60 ? "warning" : "error";
    } else if (type === "time") {
      return value <= 1000 ? "success" : value <= 2000 ? "warning" : "error";
    }
    return "default";
  };

  // Format test result details
  const formatTestResult = (result: string) => {
    return result.length > 100 ? `${result.substring(0, 100)}...` : result;
  };

  return (
    <Box>
      {/* Overall Status Header */}
      <Alert
        severity={deploymentStatus.color as any}
        sx={{ mb: 3 }}
        iconMapping={{
          success: <PassIcon />,
          warning: <WarningIcon />,
          error: <FailIcon />,
        }}
      >
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="subtitle1" fontWeight={600}>
              {deploymentStatus.message}
            </Typography>
            <Typography variant="body2">
              Agent: {agentDefinition.role}+{agentDefinition.domain} | Overall:
              {" "}
              {testResults.overall.toUpperCase()} | Score:{" "}
              {testResults.metrics.capabilityScore}/100
            </Typography>
          </Box>
          <Box>
            {getOverallStatusIcon()}
          </Box>
        </Box>
      </Alert>

      <Grid container spacing={3}>
        {/* Metrics Summary Cards */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
              >
                <Box>
                  <Typography
                    variant="h4"
                    color={`${
                      getMetricColor(testResults.metrics.passRate, "percentage")
                    }.main`}
                    fontWeight="bold"
                  >
                    {(testResults.metrics.passRate * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Pass Rate
                  </Typography>
                </Box>
                <TrendIcon
                  color={getMetricColor(
                    testResults.metrics.passRate,
                    "percentage",
                  ) as any}
                />
              </Box>
              <LinearProgress
                variant="determinate"
                value={testResults.metrics.passRate * 100}
                color={getMetricColor(
                  testResults.metrics.passRate,
                  "percentage",
                ) as any}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
              >
                <Box>
                  <Typography
                    variant="h4"
                    color={`${
                      getMetricColor(
                        testResults.metrics.capabilityScore,
                        "score",
                      )
                    }.main`}
                    fontWeight="bold"
                  >
                    {testResults.metrics.capabilityScore}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Capability Score
                  </Typography>
                </Box>
                <MetricsIcon
                  color={getMetricColor(
                    testResults.metrics.capabilityScore,
                    "score",
                  ) as any}
                />
              </Box>
              <Box sx={{ position: "relative", mt: 1 }}>
                <CircularProgress
                  variant="determinate"
                  value={testResults.metrics.capabilityScore}
                  size={40}
                  thickness={6}
                  color={getMetricColor(
                    testResults.metrics.capabilityScore,
                    "score",
                  ) as any}
                />
                <Box
                  sx={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    bottom: 0,
                    right: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Typography
                    variant="caption"
                    component="div"
                    color="text.secondary"
                    fontWeight="bold"
                  >
                    /100
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
              >
                <Box>
                  <Typography
                    variant="h4"
                    color={`${
                      getMetricColor(
                        testResults.metrics.averageExecutionTime,
                        "time",
                      )
                    }.main`}
                    fontWeight="bold"
                  >
                    {testResults.metrics.averageExecutionTime}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Avg Time (ms)
                  </Typography>
                </Box>
                <PerformanceIcon
                  color={getMetricColor(
                    testResults.metrics.averageExecutionTime,
                    "time",
                  ) as any}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Test Results Details */}
        <Grid item xs={12}>
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandIcon />}>
              <Typography
                variant="h6"
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <MetricsIcon color="primary" />
                Test Results Details ({testResults.scenarios.length} tests)
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Status</TableCell>
                      <TableCell>Test Name</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Time (ms)</TableCell>
                      <TableCell>Result</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {testResults.scenarios.map((scenario) => (
                      <TableRow key={scenario.id} hover>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            {scenario.status === "passed" && (
                              <PassIcon color="success" fontSize="small" />
                            )}
                            {scenario.status === "failed" && (
                              <FailIcon color="error" fontSize="small" />
                            )}
                            <Chip
                              label={scenario.status}
                              size="small"
                              color={scenario.status === "passed"
                                ? "success"
                                : "error"}
                              variant="outlined"
                            />
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight={600}>
                            {scenario.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {scenario.description}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={scenario.testType}
                            size="small"
                            variant="outlined"
                            color="default"
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontFamily="monospace">
                            {scenario.executionTime || "-"}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontSize="0.8rem">
                            {scenario.result
                              ? formatTestResult(scenario.result)
                              : "No result"}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </AccordionDetails>
          </Accordion>
        </Grid>

        {/* Recommendations */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography
                variant="h6"
                gutterBottom
                sx={{ display: "flex", alignItems: "center", gap: 1 }}
              >
                <RecommendationIcon color="primary" />
                Recommendations & Next Steps
              </Typography>

              {testResults.recommendations.length > 0
                ? (
                  <Stack spacing={1}>
                    {testResults.recommendations.map((
                      recommendation,
                      index,
                    ) => (
                      <Alert
                        key={index}
                        severity={recommendation.includes("Excellent") ||
                            recommendation.includes("ready")
                          ? "success"
                          : recommendation.includes("Consider") ||
                              recommendation.includes("recommended")
                          ? "warning"
                          : "info"}
                        variant="outlined"
                      >
                        {recommendation}
                      </Alert>
                    ))}
                  </Stack>
                )
                : (
                  <Alert severity="info" variant="outlined">
                    No specific recommendations - standard deployment process
                    can proceed.
                  </Alert>
                )}

              {/* Configuration Summary */}
              <Box
                sx={{
                  mt: 3,
                  p: 2,
                  backgroundColor: "grey.50",
                  borderRadius: 1,
                }}
              >
                <Typography variant="subtitle2" gutterBottom>
                  Agent Configuration Summary
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Role + Domain
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {agentDefinition.role}+{agentDefinition.domain}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Quality Gate
                    </Typography>
                    <Typography
                      variant="body2"
                      fontWeight={600}
                      textTransform="capitalize"
                    >
                      {agentDefinition.qualityGate}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Coordination
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {agentDefinition.coordinationStrategy.replace(/_/g, " ")}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Capabilities
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {agentDefinition.expectedCapabilities.length} defined
                    </Typography>
                  </Grid>
                </Grid>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};
