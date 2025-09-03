/**
 * Workflow Patterns Guide - Documentation Component for Task Flow Visualizer MVP
 *
 * This component provides educational content about multi-agent coordination patterns
 * to help users understand the workflow diagrams in the Task Flow Visualizer.
 *
 * @author commentator_agentic-systems
 * @version MVP
 */

"use client";

import React, { useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  alpha,
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import {
  AccountTree as HierarchyIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  Groups as CollaborationIcon,
  Hub as FanOutIcon,
  Info as InfoIcon,
  Psychology as AgentIcon,
  Security as SecurityIcon,
  Speed as PerformanceIcon,
  Timeline as PipelineIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

// Types for coordination patterns documentation
interface CoordinationPattern {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
  characteristics: string[];
  useCases: string[];
  agentCount: string;
  advantages: string[];
  considerations: string[];
  example: string;
}

interface WorkflowPatternsGuideProps {
  className?: string;
  compact?: boolean;
}

export function WorkflowPatternsGuide(
  { className, compact = false }: WorkflowPatternsGuideProps,
) {
  const theme = useTheme();
  const [expandedPattern, setExpandedPattern] = useState<string | false>(
    "fan_out_synthesize",
  );

  const handlePatternChange =
    (pattern: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
      setExpandedPattern(isExpanded ? pattern : false);
    };

  // Multi-agent coordination patterns from agentic-systems domain expertise
  const coordinationPatterns: CoordinationPattern[] = [
    {
      id: "fan_out_synthesize",
      name: "Fan-out & Synthesize",
      icon: <FanOutIcon />,
      description:
        "Multiple agents work on parallel subtasks, then results are consolidated by a synthesis agent.",
      characteristics: [
        "Parallel execution of independent tasks",
        "Central synthesis of distributed results",
        "High concurrency and throughput",
      ],
      useCases: [
        "Research projects with multiple perspectives",
        "Code analysis across different components",
        "Market research with diverse data sources",
      ],
      agentCount: "5-20 agents",
      advantages: [
        "Maximum parallelization",
        "Diverse perspectives gathered",
        "Reduced overall completion time",
      ],
      considerations: [
        "Requires effective synthesis strategy",
        "Potential for conflicting findings",
        "Higher coordination overhead",
      ],
      example:
        "8 researcher agents analyze different market segments → 1 analyst synthesizes comprehensive report",
    },
    {
      id: "hierarchical_delegation",
      name: "Hierarchical Delegation",
      icon: <HierarchyIcon />,
      description:
        "Multi-tier coordination with specialized agents at each level, from strategy to execution.",
      characteristics: [
        "Clear command hierarchy",
        "Specialized roles per tier",
        "Escalation pathways defined",
      ],
      useCases: [
        "Complex system architecture",
        "Large-scale implementations",
        "Multi-phase projects",
      ],
      agentCount: "2 + complexity score",
      advantages: [
        "Clear accountability structure",
        "Specialized expertise at each level",
        "Scalable for large projects",
      ],
      considerations: [
        "Potential bottlenecks at higher levels",
        "Communication delays through hierarchy",
        "Dependency on coordinator effectiveness",
      ],
      example:
        "Architect defines system → Senior implementers create modules → Junior implementers handle details",
    },
    {
      id: "parallel_discovery",
      name: "Parallel Discovery",
      icon: <CollaborationIcon />,
      description:
        "Independent agents explore different aspects simultaneously, then merge discoveries.",
      characteristics: [
        "Independent exploration phases",
        "Knowledge sharing at checkpoints",
        "Emergent synthesis patterns",
      ],
      useCases: [
        "Exploratory research",
        "Problem space analysis",
        "Technology evaluation",
      ],
      agentCount: "3-7 agents",
      advantages: [
        "Comprehensive coverage",
        "Reduced groupthink risk",
        "Natural load distribution",
      ],
      considerations: [
        "Potential for overlapping work",
        "Coordination complexity grows",
        "Synthesis can be challenging",
      ],
      example:
        "5 analysts independently research AI tools → consolidation agent merges findings → recommendation",
    },
  ];

  // Agent activity states for visualization legend
  const activityStates = [
    {
      status: "active",
      label: "Active",
      icon: <SuccessIcon />,
      color: theme.palette.success.main,
      description: "Agent currently executing tasks",
    },
    {
      status: "waiting",
      label: "Waiting",
      icon: <WarningIcon />,
      color: theme.palette.warning.main,
      description: "Agent idle, awaiting task assignment",
    },
    {
      status: "blocked",
      label: "Blocked",
      icon: <ErrorIcon />,
      color: theme.palette.error.main,
      description: "Agent blocked by dependencies or conflicts",
    },
  ];

  if (compact) {
    return (
      <Card className={className} sx={{ mb: 2 }}>
        <CardContent sx={{ pb: 2 }}>
          <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
            <InfoIcon sx={{ mr: 1 }} />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Coordination Patterns
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {coordinationPatterns.map((pattern) => (
              <Chip
                key={pattern.id}
                icon={pattern.icon}
                label={pattern.name}
                variant="outlined"
                size="small"
              />
            ))}
          </Stack>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box className={className}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 700 }}>
          Multi-Agent Workflow Patterns
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Understanding coordination strategies and agent interactions in the
          Task Flow Visualizer
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Coordination Patterns */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Coordination Strategies
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Different patterns for organizing multi-agent work based on task
                complexity and requirements
              </Typography>

              {coordinationPatterns.map((pattern, index) => (
                <Accordion
                  key={pattern.id}
                  expanded={expandedPattern === pattern.id}
                  onChange={handlePatternChange(pattern.id)}
                  sx={{
                    mb: 1,
                    "&:before": { display: "none" },
                    boxShadow: "none",
                    border: `1px solid ${theme.palette.divider}`,
                  }}
                >
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    sx={{
                      bgcolor: expandedPattern === pattern.id
                        ? alpha(theme.palette.primary.main, 0.05)
                        : "transparent",
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        width: "100%",
                      }}
                    >
                      <Box sx={{ mr: 2, color: theme.palette.primary.main }}>
                        {pattern.icon}
                      </Box>
                      <Box sx={{ flexGrow: 1 }}>
                        <Typography
                          variant="subtitle1"
                          sx={{ fontWeight: 600 }}
                        >
                          {pattern.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {pattern.description}
                        </Typography>
                      </Box>
                      <Chip
                        label={pattern.agentCount}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    </Box>
                  </AccordionSummary>

                  <AccordionDetails>
                    <Grid container spacing={3}>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          Key Characteristics
                        </Typography>
                        <List dense>
                          {pattern.characteristics.map((char, i) => (
                            <ListItem key={i} sx={{ py: 0.5 }}>
                              <ListItemIcon sx={{ minWidth: 24 }}>
                                <Box
                                  sx={{
                                    width: 4,
                                    height: 4,
                                    borderRadius: "50%",
                                    bgcolor: theme.palette.primary.main,
                                  }}
                                />
                              </ListItemIcon>
                              <ListItemText primary={char} />
                            </ListItem>
                          ))}
                        </List>

                        <Typography
                          variant="subtitle2"
                          gutterBottom
                          sx={{ mt: 2 }}
                        >
                          Best Use Cases
                        </Typography>
                        <List dense>
                          {pattern.useCases.map((useCase, i) => (
                            <ListItem key={i} sx={{ py: 0.5 }}>
                              <ListItemIcon sx={{ minWidth: 24 }}>
                                <CheckCircle
                                  color="success"
                                  sx={{ fontSize: 16 }}
                                />
                              </ListItemIcon>
                              <ListItemText primary={useCase} />
                            </ListItem>
                          ))}
                        </List>
                      </Grid>

                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          Advantages
                        </Typography>
                        <List dense>
                          {pattern.advantages.map((adv, i) => (
                            <ListItem key={i} sx={{ py: 0.5 }}>
                              <ListItemIcon sx={{ minWidth: 24 }}>
                                <PerformanceIcon
                                  color="success"
                                  sx={{ fontSize: 16 }}
                                />
                              </ListItemIcon>
                              <ListItemText primary={adv} />
                            </ListItem>
                          ))}
                        </List>

                        <Typography
                          variant="subtitle2"
                          gutterBottom
                          sx={{ mt: 2 }}
                        >
                          Considerations
                        </Typography>
                        <List dense>
                          {pattern.considerations.map((cons, i) => (
                            <ListItem key={i} sx={{ py: 0.5 }}>
                              <ListItemIcon sx={{ minWidth: 24 }}>
                                <WarningIcon
                                  color="warning"
                                  sx={{ fontSize: 16 }}
                                />
                              </ListItemIcon>
                              <ListItemText primary={cons} />
                            </ListItem>
                          ))}
                        </List>
                      </Grid>

                      <Grid item xs={12}>
                        <Alert severity="info" sx={{ mt: 2 }}>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            Example: {pattern.example}
                          </Typography>
                        </Alert>
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              ))}
            </CardContent>
          </Card>
        </Grid>

        {/* Sidebar with Activity Legend and Quick Tips */}
        <Grid item xs={12} lg={4}>
          {/* Agent Activity Legend */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Agent Activity States
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Visual indicators in the workflow diagram
              </Typography>

              <Stack spacing={1.5}>
                {activityStates.map((state) => (
                  <Box
                    key={state.status}
                    sx={{ display: "flex", alignItems: "center" }}
                  >
                    <Box sx={{ mr: 2, color: state.color }}>
                      {state.icon}
                    </Box>
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {state.label}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {state.description}
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>

          {/* Quality Gates Reference */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                Quality Gates
              </Typography>

              <Stack spacing={2}>
                <Box>
                  <Chip
                    label="Basic"
                    size="small"
                    color="default"
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    Output validation, format checking
                  </Typography>
                </Box>

                <Box>
                  <Chip
                    label="Thorough"
                    size="small"
                    color="primary"
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    Cross-agent consistency, consolidation review
                  </Typography>
                </Box>

                <Box>
                  <Chip
                    label="Critical"
                    size="small"
                    color="error"
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    Multi-round validation, consensus required
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>

          {/* Performance Tips */}
          <Card>
            <CardContent>
              <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
                <SecurityIcon sx={{ mr: 1 }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Coordination Tips
                </Typography>
              </Box>

              <List dense>
                <ListItem sx={{ px: 0 }}>
                  <ListItemIcon>
                    <InfoIcon color="primary" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText>
                    <Typography variant="body2">
                      Use fan-out patterns for independent parallel work
                    </Typography>
                  </ListItemText>
                </ListItem>

                <ListItem sx={{ px: 0 }}>
                  <ListItemIcon>
                    <InfoIcon color="primary" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText>
                    <Typography variant="body2">
                      Hierarchical delegation scales better for complex tasks
                    </Typography>
                  </ListItemText>
                </ListItem>

                <ListItem sx={{ px: 0 }}>
                  <ListItemIcon>
                    <InfoIcon color="primary" fontSize="small" />
                  </ListItemIcon>
                  <ListItemText>
                    <Typography variant="body2">
                      Monitor for bottlenecks in synthesis phases
                    </Typography>
                  </ListItemText>
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

// Export additional utilities for integration
export const COORDINATION_PATTERNS = [
  "fan_out_synthesize",
  "hierarchical_delegation",
  "parallel_discovery",
] as const;

export type CoordinationPatternType = typeof COORDINATION_PATTERNS[number];

export function getPatternDescription(
  pattern: CoordinationPatternType,
): string {
  const descriptions = {
    fan_out_synthesize:
      "Multiple agents work in parallel, then results are synthesized",
    hierarchical_delegation:
      "Multi-tier coordination with specialized roles at each level",
    parallel_discovery:
      "Independent exploration followed by knowledge consolidation",
  };
  return descriptions[pattern] || "Unknown coordination pattern";
}

export function getPatternIcon(
  pattern: CoordinationPatternType,
): React.ReactNode {
  const icons = {
    fan_out_synthesize: <FanOutIcon />,
    hierarchical_delegation: <HierarchyIcon />,
    parallel_discovery: <CollaborationIcon />,
  };
  return icons[pattern] || <AgentIcon />;
}
