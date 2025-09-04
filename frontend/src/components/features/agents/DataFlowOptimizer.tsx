// @ts-nocheck
"use client";

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Grid,
  Tabs,
  Tab,
  Button,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  Timeline,
  Settings,
  Speed,
  Sync,
  Warning,
  CheckCircle,
  Error,
  TrendingUp,
  Memory,
  NetworkCheck,
  Storage,
  PlayArrow,
  Pause,
  Stop,
  Edit,
  Delete,
  Add,
  ExpandMore,
  Refresh,
  TuneRounded
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import {
  useDataFlowPatterns,
  useStreamProcessors,
  useStateSyncConfigurations
} from '../../../lib/services/agent-composition';
import { DataFlowPattern, StreamProcessor, StateSync } from '../../../lib/types/agent-composition';

interface DataFlowOptimizerProps {
  agentIds: string[];
  coordinationId?: string;
}

interface OptimizationRecommendation {
  id: string;
  type: 'performance' | 'reliability' | 'cost';
  severity: 'low' | 'medium' | 'high';
  title: string;
  description: string;
  estimated_improvement: string;
  implementation_effort: 'low' | 'medium' | 'high';
  actions: string[];
}

// Mock optimization recommendations
const generateOptimizationRecommendations = (agentIds: string[]): OptimizationRecommendation[] => [
  {
    id: 'opt_001',
    type: 'performance',
    severity: 'high',
    title: 'Implement Request Batching',
    description: 'Multiple agents are making frequent small API calls. Batching could reduce latency by 40%.',
    estimated_improvement: '40% latency reduction',
    implementation_effort: 'medium',
    actions: [
      'Configure batch processor with 100ms window',
      'Update agent coordination to use batch endpoints',
      'Monitor batch efficiency metrics'
    ]
  },
  {
    id: 'opt_002',
    type: 'cost',
    severity: 'medium',
    title: 'Optimize Token Usage',
    description: 'Agents are using verbose prompts. Token optimization could save 25% on costs.',
    estimated_improvement: '25% cost reduction',
    implementation_effort: 'low',
    actions: [
      'Implement prompt compression',
      'Use structured outputs',
      'Cache common responses'
    ]
  },
  {
    id: 'opt_003',
    type: 'reliability',
    severity: 'high',
    title: 'Add Circuit Breaker Pattern',
    description: 'No fault tolerance for failing services. Circuit breakers would improve reliability.',
    estimated_improvement: '90% uptime improvement during outages',
    implementation_effort: 'high',
    actions: [
      'Implement circuit breaker middleware',
      'Configure failure thresholds',
      'Add fallback mechanisms'
    ]
  }
];

// Mock stream metrics data
const generateStreamMetrics = () => {
  return Array.from({ length: 24 }, (_, i) => ({
    time: `${i}:00`,
    throughput: Math.floor(Math.random() * 1000) + 500,
    latency: Math.floor(Math.random() * 100) + 20,
    errors: Math.floor(Math.random() * 10),
    cpu_usage: Math.random() * 80 + 10,
    memory_usage: Math.random() * 70 + 20
  }));
};

export function DataFlowOptimizer({ agentIds, coordinationId }: DataFlowOptimizerProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [optimizationDialog, setOptimizationDialog] = useState<{
    open: boolean;
    recommendation?: OptimizationRecommendation;
  }>({ open: false });
  const [streamProcessorDialog, setStreamProcessorDialog] = useState<{
    open: boolean;
    processor?: StreamProcessor;
  }>({ open: false });

  const { data: dataFlowPatterns, isLoading: patternsLoading } = useDataFlowPatterns();
  const { data: streamProcessors, isLoading: processorsLoading } = useStreamProcessors();
  const { data: stateSyncConfigs, isLoading: syncLoading } = useStateSyncConfigurations();

  const streamMetrics = generateStreamMetrics();
  const optimizationRecommendations = generateOptimizationRecommendations(agentIds);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleOptimizationClick = (recommendation: OptimizationRecommendation) => {
    setOptimizationDialog({ open: true, recommendation });
  };

  const handleProcessorEdit = (processor: StreamProcessor) => {
    setStreamProcessorDialog({ open: true, processor });
  };

  const getTypeColor = (type: OptimizationRecommendation['type']) => {
    switch (type) {
      case 'performance': return 'primary';
      case 'cost': return 'warning';
      case 'reliability': return 'error';
      default: return 'default';
    }
  };

  const getSeverityColor = (severity: OptimizationRecommendation['severity']) => {
    switch (severity) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const renderOptimizationOverview = () => {
    const highPriorityCount = optimizationRecommendations.filter(r => r.severity === 'high').length;
    const performanceImprovements = optimizationRecommendations.filter(r => r.type === 'performance');
    const costSavings = optimizationRecommendations.filter(r => r.type === 'cost');

    return (
      <Box>
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Warning sx={{ fontSize: 40, color: 'error.main', mb: 1 }} />
                <Typography variant="h4">{highPriorityCount}</Typography>
                <Typography color="text.secondary">High Priority Issues</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Speed sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
                <Typography variant="h4">{performanceImprovements.length}</Typography>
                <Typography color="text.secondary">Performance Optimizations</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <TrendingUp sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
                <Typography variant="h4">${costSavings.length * 50}</Typography>
                <Typography color="text.secondary">Est. Monthly Savings</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Stream Processing Metrics (Last 24h)
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={streamMetrics}>
              <defs>
                <linearGradient id="throughputGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#8884d8" stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="latencyGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#82ca9d" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <RechartsTooltip />
              <Legend />
              <Area
                yAxisId="left"
                type="monotone"
                dataKey="throughput"
                stroke="#8884d8"
                fillOpacity={1}
                fill="url(#throughputGradient)"
                name="Throughput (msgs/s)"
              />
              <Area
                yAxisId="right"
                type="monotone"
                dataKey="latency"
                stroke="#82ca9d"
                fillOpacity={1}
                fill="url(#latencyGradient)"
                name="Latency (ms)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </Paper>

        <Typography variant="h6" gutterBottom>
          Optimization Recommendations
        </Typography>
        <Grid container spacing={2}>
          {optimizationRecommendations.map(recommendation => (
            <Grid item xs={12} key={recommendation.id}>
              <Card 
                sx={{ 
                  cursor: 'pointer',
                  '&:hover': { boxShadow: 3 }
                }}
                onClick={() => handleOptimizationClick(recommendation)}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Typography variant="h6">
                      {recommendation.title}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Chip 
                        label={recommendation.type} 
                        color={getTypeColor(recommendation.type)}
                        size="small"
                      />
                      <Chip 
                        label={recommendation.severity} 
                        color={getSeverityColor(recommendation.severity)}
                        size="small"
                      />
                    </Box>
                  </Box>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {recommendation.description}
                  </Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" sx={{ fontWeight: 'medium', color: 'success.main' }}>
                      {recommendation.estimated_improvement}
                    </Typography>
                    <Chip 
                      label={`${recommendation.implementation_effort} effort`}
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  };

  const renderStreamProcessors = () => {
    if (processorsLoading) {
      return <LinearProgress />;
    }

    return (
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Stream Processors</Typography>
          <Button 
            startIcon={<Add />} 
            variant="contained"
            onClick={() => setStreamProcessorDialog({ open: true })}
          >
            Add Processor
          </Button>
        </Box>

        <Grid container spacing={3}>
          {streamProcessors?.map(processor => (
            <Grid item xs={12} md={6} key={processor.id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Typography variant="h6">{processor.name}</Typography>
                    <Box>
                      <IconButton size="small" onClick={() => handleProcessorEdit(processor)}>
                        <Edit />
                      </IconButton>
                      <IconButton size="small" color="error">
                        <Delete />
                      </IconButton>
                    </Box>
                  </Box>
                  
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Input: {processor.input_stream} → Output: {processor.output_stream}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Function: {processor.processing_function}
                    </Typography>
                  </Box>

                  <Grid container spacing={2} sx={{ mb: 2 }}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Buffer Size</Typography>
                      <Typography variant="body2">{processor.buffer_size}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Batch Interval</Typography>
                      <Typography variant="body2">{processor.batch_interval}ms</Typography>
                    </Grid>
                  </Grid>

                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Chip 
                      label={processor.error_handling}
                      size="small"
                      color={processor.error_handling === 'retry' ? 'success' : 'warning'}
                    />
                    <Box>
                      <IconButton size="small" color="success">
                        <PlayArrow />
                      </IconButton>
                      <IconButton size="small" color="warning">
                        <Pause />
                      </IconButton>
                      <IconButton size="small" color="error">
                        <Stop />
                      </IconButton>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  };

  const renderStateSynchronization = () => {
    if (syncLoading) {
      return <LinearProgress />;
    }

    return (
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">State Synchronization</Typography>
          <Button startIcon={<Add />} variant="contained">
            Add Sync Config
          </Button>
        </Box>

        {stateSyncConfigs?.map(config => (
          <Accordion key={config.id} sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', mr: 2 }}>
                <Typography variant="h6">{config.id}</Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Chip 
                    label={`${config.agents.length} agents`}
                    size="small"
                  />
                  <Chip 
                    label={config.consistency_level}
                    size="small"
                    color={config.consistency_level === 'strong' ? 'success' : 'warning'}
                  />
                </Box>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>Participating Agents</Typography>
                  <List dense>
                    {config.agents.map(agentId => (
                      <ListItem key={agentId}>
                        <ListItemIcon>
                          <CheckCircle color="success" />
                        </ListItemIcon>
                        <ListItemText primary={agentId} />
                      </ListItem>
                    ))}
                  </List>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>Configuration</Typography>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>Sync Frequency</TableCell>
                        <TableCell>{config.sync_frequency / 1000}s</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Conflict Resolution</TableCell>
                        <TableCell>{config.conflict_resolution}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Consistency Level</TableCell>
                        <TableCell>{config.consistency_level}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </Grid>
              </Grid>
              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <Button startIcon={<Edit />} size="small">Edit</Button>
                <Button startIcon={<TuneRounded />} size="small">Tune</Button>
                <Button startIcon={<Delete />} size="small" color="error">Delete</Button>
              </Box>
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>
    );
  };

  const renderDataFlowPatterns = () => {
    if (patternsLoading) {
      return <LinearProgress />;
    }

    return (
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Data Flow Patterns</Typography>
          <Button startIcon={<Timeline />} variant="outlined">
            Visualize Flow
          </Button>
        </Box>

        {dataFlowPatterns?.map(pattern => (
          <Card key={pattern.id} sx={{ mb: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>{pattern.name}</Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                {pattern.description}
              </Typography>
              
              <Typography variant="subtitle2" gutterBottom>Involved Agents</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {pattern.agents_involved.map(agent => (
                  <Chip key={agent} label={agent} size="small" />
                ))}
              </Box>

              <Typography variant="subtitle2" gutterBottom>Data Flow</Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Source</TableCell>
                      <TableCell>Destination</TableCell>
                      <TableCell>Data Type</TableCell>
                      <TableCell>Processing Required</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pattern.data_flow.map((flow, index) => (
                      <TableRow key={index}>
                        <TableCell>{flow.source}</TableCell>
                        <TableCell>{flow.destination}</TableCell>
                        <TableCell>{flow.data_type}</TableCell>
                        <TableCell>
                          {flow.processing_required ? (
                            <CheckCircle color="warning" />
                          ) : (
                            <CheckCircle color="success" />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              {pattern.optimization_suggestions.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Optimization Suggestions</Typography>
                  <List dense>
                    {pattern.optimization_suggestions.map((suggestion, index) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <TrendingUp color="primary" />
                        </ListItemIcon>
                        <ListItemText primary={suggestion} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </CardContent>
          </Card>
        ))}
      </Box>
    );
  };

  const renderOptimizationDialog = () => {
    const { recommendation } = optimizationDialog;
    if (!recommendation) return null;

    return (
      <Dialog
        open={optimizationDialog.open}
        onClose={() => setOptimizationDialog({ open: false })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Optimization Recommendation: {recommendation.title}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body1" paragraph>
              {recommendation.description}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Chip 
                label={recommendation.type} 
                color={getTypeColor(recommendation.type)}
              />
              <Chip 
                label={`${recommendation.severity} priority`}
                color={getSeverityColor(recommendation.severity)}
              />
              <Chip 
                label={`${recommendation.implementation_effort} effort`}
                variant="outlined"
              />
            </Box>
          </Box>

          <Typography variant="h6" gutterBottom>
            Expected Improvement
          </Typography>
          <Alert severity="success" sx={{ mb: 2 }}>
            {recommendation.estimated_improvement}
          </Alert>

          <Typography variant="h6" gutterBottom>
            Implementation Steps
          </Typography>
          <List>
            {recommendation.actions.map((action, index) => (
              <ListItem key={index}>
                <ListItemIcon>
                  <CheckCircle />
                </ListItemIcon>
                <ListItemText primary={action} />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOptimizationDialog({ open: false })}>
            Cancel
          </Button>
          <Button variant="contained">
            Implement Optimization
          </Button>
        </DialogActions>
      </Dialog>
    );
  };

  if (agentIds.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Timeline sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No Data Flow to Optimize
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Spawn some agents to see data flow patterns and optimization opportunities
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ height: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Data Flow Optimizer</Typography>
        <Button startIcon={<Refresh />} onClick={() => window.location.reload()}>
          Refresh
        </Button>
      </Box>

      {coordinationId && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Analyzing data flow for coordination: {coordinationId}
        </Alert>
      )}

      <Paper sx={{ mb: 2 }}>
        <Tabs value={activeTab} onChange={handleTabChange}>
          <Tab label="Overview" icon={<Timeline />} />
          <Tab label="Stream Processors" icon={<Settings />} />
          <Tab label="State Sync" icon={<Sync />} />
          <Tab label="Flow Patterns" icon={<NetworkCheck />} />
        </Tabs>
      </Paper>

      <Box sx={{ mt: 2 }}>
        {activeTab === 0 && renderOptimizationOverview()}
        {activeTab === 1 && renderStreamProcessors()}
        {activeTab === 2 && renderStateSynchronization()}
        {activeTab === 3 && renderDataFlowPatterns()}
      </Box>

      {renderOptimizationDialog()}
    </Box>
  );
}