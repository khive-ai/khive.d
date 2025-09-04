// @ts-nocheck
"use client";

import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Grid,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Divider
} from '@mui/material';
import {
  TrendingUp,
  Speed,
  AttachMoney,
  CheckCircle,
  ShowChart,
  Download
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter
} from 'recharts';

interface AgentPerformanceAnalyticsProps {
  agentIds: string[];
  sessionId?: string;
  coordinationId?: string;
}

// Mock performance data - in real implementation, this would come from API
const generateMockPerformanceData = (agentIds: string[]) => {
  return agentIds.map(agentId => ({
    agent_id: agentId,
    role: agentId.split('_')[0] || 'unknown',
    domain: agentId.split('_')[1] || 'unknown',
    tasks_completed: Math.floor(Math.random() * 20) + 5,
    avg_task_time: Math.floor(Math.random() * 3600) + 600, // 10min to 1hr
    success_rate: 0.7 + Math.random() * 0.3, // 70-100%
    total_cost: Math.random() * 10 + 2, // $2-$12
    tokens_used: Math.floor(Math.random() * 50000) + 10000,
    api_calls: Math.floor(Math.random() * 200) + 50,
    cpu_avg: Math.random() * 60 + 20, // 20-80%
    memory_avg: Math.random() * 400 + 100, // 100-500MB
    uptime: Math.random() * 7200 + 1800, // 30min to 2hr
    error_count: Math.floor(Math.random() * 5),
    last_7_days: Array.from({ length: 7 }, (_, i) => ({
      day: new Date(Date.now() - (6 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      tasks: Math.floor(Math.random() * 10) + 1,
      success_rate: 0.6 + Math.random() * 0.4,
      cost: Math.random() * 2,
      avg_time: Math.floor(Math.random() * 1800) + 600
    }))
  }));
};

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d'];

export function AgentPerformanceAnalytics({ agentIds, sessionId, coordinationId }: AgentPerformanceAnalyticsProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [timeRange, setTimeRange] = useState('7d');
  const [groupBy, setGroupBy] = useState<'role' | 'domain' | 'agent'>('role');

  const performanceData = useMemo(() => generateMockPerformanceData(agentIds), [agentIds]);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const aggregatedData = useMemo(() => {
    const grouped = performanceData.reduce((acc, agent) => {
      const key = groupBy === 'agent' ? agent.agent_id : agent[groupBy];
      if (!acc[key]) {
        acc[key] = {
          agents: [],
          total_tasks: 0,
          avg_success_rate: 0,
          total_cost: 0,
          avg_task_time: 0,
          total_tokens: 0
        };
      }
      acc[key].agents.push(agent);
      acc[key].total_tasks += agent.tasks_completed;
      acc[key].avg_success_rate += agent.success_rate;
      acc[key].total_cost += agent.total_cost;
      acc[key].avg_task_time += agent.avg_task_time;
      acc[key].total_tokens += agent.tokens_used;
      return acc;
    }, {} as Record<string, any>);

    return Object.entries(grouped).map(([key, data]: [string, any]) => ({
      name: key,
      agents_count: data.agents.length,
      total_tasks: data.total_tasks,
      avg_success_rate: data.avg_success_rate / data.agents.length,
      total_cost: data.total_cost,
      avg_task_time: data.avg_task_time / data.agents.length,
      total_tokens: data.total_tokens,
      efficiency_score: (data.total_tasks / data.agents.length) * (data.avg_success_rate / data.agents.length)
    }));
  }, [performanceData, groupBy]);

  const timeSeriesData = useMemo(() => {
    if (performanceData.length === 0) return [];
    
    const days = performanceData[0]?.last_7_days || [];
    return days.map(day => {
      const dayData: Record<string, any> = { date: day.day };
      performanceData.forEach(agent => {
        const agentDay = agent.last_7_days.find(d => d.day === day.day);
        if (agentDay) {
          dayData[agent.agent_id + '_tasks'] = agentDay.tasks;
          dayData[agent.agent_id + '_cost'] = agentDay.cost;
          dayData[agent.agent_id + '_time'] = agentDay.avg_time;
        }
      });
      return dayData;
    });
  }, [performanceData]);

  const renderOverviewMetrics = () => {
    const totalTasks = performanceData.reduce((sum, agent) => sum + agent.tasks_completed, 0);
    const avgSuccessRate = performanceData.reduce((sum, agent) => sum + agent.success_rate, 0) / performanceData.length;
    const totalCost = performanceData.reduce((sum, agent) => sum + agent.total_cost, 0);
    const avgTaskTime = performanceData.reduce((sum, agent) => sum + agent.avg_task_time, 0) / performanceData.length;

    return (
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <CheckCircle sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
              <Typography variant="h4" component="div">
                {totalTasks}
              </Typography>
              <Typography color="text.secondary">
                Total Tasks Completed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <TrendingUp sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
              <Typography variant="h4" component="div">
                {(avgSuccessRate * 100).toFixed(1)}%
              </Typography>
              <Typography color="text.secondary">
                Average Success Rate
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <AttachMoney sx={{ fontSize: 40, color: 'warning.main', mb: 1 }} />
              <Typography variant="h4" component="div">
                ${totalCost.toFixed(2)}
              </Typography>
              <Typography color="text.secondary">
                Total Cost
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Speed sx={{ fontSize: 40, color: 'info.main', mb: 1 }} />
              <Typography variant="h4" component="div">
                {Math.round(avgTaskTime / 60)}m
              </Typography>
              <Typography color="text.secondary">
                Average Task Time
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    );
  };

  const renderPerformanceTrends = () => {
    return (
      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Task Completion Trends
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timeSeriesData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                {performanceData.slice(0, 5).map((agent, index) => (
                  <Line
                    key={agent.agent_id}
                    type="monotone"
                    dataKey={`${agent.agent_id}_tasks`}
                    stroke={COLORS[index % COLORS.length]}
                    name={agent.agent_id}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Cost Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={performanceData.map(agent => ({
                    name: agent.agent_id,
                    value: agent.total_cost
                  }))}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, value }) => `${name}: $${value.toFixed(2)}`}
                >
                  {performanceData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>
    );
  };

  const renderComparison = () => {
    return (
      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">
            Agent Comparison
          </Typography>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Group By</InputLabel>
            <Select
              value={groupBy}
              label="Group By"
              onChange={(e) => setGroupBy(e.target.value as 'role' | 'domain' | 'agent')}
            >
              <MenuItem value="role">Role</MenuItem>
              <MenuItem value="domain">Domain</MenuItem>
              <MenuItem value="agent">Agent</MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Grid container spacing={3}>
          <Grid item xs={12} lg={8}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Performance vs Cost Analysis
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <ScatterChart>
                  <CartesianGrid />
                  <XAxis 
                    type="number" 
                    dataKey="total_cost" 
                    name="Total Cost"
                    domain={['dataMin', 'dataMax']}
                  />
                  <YAxis 
                    type="number" 
                    dataKey="efficiency_score" 
                    name="Efficiency Score"
                    domain={['dataMin', 'dataMax']}
                  />
                  <Tooltip 
                    cursor={{ strokeDasharray: '3 3' }}
                    formatter={(value, name) => [value, name]}
                  />
                  <Scatter 
                    name="Agents" 
                    data={aggregatedData} 
                    fill="#8884d8"
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
          <Grid item xs={12} lg={4}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Success Rate Comparison
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={aggregatedData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 1]} />
                  <Tooltip formatter={(value) => [(value * 100).toFixed(1) + '%', 'Success Rate']} />
                  <Bar dataKey="avg_success_rate" fill="#00C49F" />
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    );
  };

  const renderDetailedTable = () => {
    const sortedData = [...performanceData].sort((a, b) => b.tasks_completed - a.tasks_completed);

    return (
      <Paper>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            Detailed Agent Performance
          </Typography>
          <Button startIcon={<Download />} size="small">
            Export CSV
          </Button>
        </Box>
        <Divider />
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Agent ID</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Domain</TableCell>
                <TableCell align="right">Tasks</TableCell>
                <TableCell align="right">Success Rate</TableCell>
                <TableCell align="right">Avg Time</TableCell>
                <TableCell align="right">Cost</TableCell>
                <TableCell align="right">Errors</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedData.map((agent) => (
                <TableRow key={agent.agent_id}>
                  <TableCell component="th" scope="row">
                    {agent.agent_id}
                  </TableCell>
                  <TableCell>
                    <Chip label={agent.role} size="small" />
                  </TableCell>
                  <TableCell>
                    <Chip label={agent.domain} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell align="right">{agent.tasks_completed}</TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                      <LinearProgress
                        variant="determinate"
                        value={agent.success_rate * 100}
                        sx={{ width: 50, mr: 1 }}
                      />
                      {(agent.success_rate * 100).toFixed(1)}%
                    </Box>
                  </TableCell>
                  <TableCell align="right">
                    {Math.round(agent.avg_task_time / 60)}m
                  </TableCell>
                  <TableCell align="right">
                    ${agent.total_cost.toFixed(2)}
                  </TableCell>
                  <TableCell align="right">
                    <Chip
                      label={agent.error_count}
                      size="small"
                      color={agent.error_count === 0 ? 'success' : 'error'}
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label="Active"
                      size="small"
                      color="success"
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    );
  };

  if (agentIds.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <ShowChart sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No Performance Data Available
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Spawn some agents and let them complete tasks to see performance analytics
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ height: '100%' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Agent Performance Analytics
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Time Range</InputLabel>
            <Select
              value={timeRange}
              label="Time Range"
              onChange={(e) => setTimeRange(e.target.value)}
            >
              <MenuItem value="1d">Last 24h</MenuItem>
              <MenuItem value="7d">Last 7 days</MenuItem>
              <MenuItem value="30d">Last 30 days</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Box>

      {sessionId && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Showing analytics for session: {sessionId}
          {coordinationId && ` (Coordination: ${coordinationId})`}
        </Alert>
      )}

      <Paper sx={{ mb: 2 }}>
        <Tabs value={activeTab} onChange={handleTabChange}>
          <Tab label="Overview" />
          <Tab label="Trends" />
          <Tab label="Comparison" />
          <Tab label="Details" />
        </Tabs>
      </Paper>

      <Box sx={{ mt: 2 }}>
        {activeTab === 0 && renderOverviewMetrics()}
        {activeTab === 1 && renderPerformanceTrends()}
        {activeTab === 2 && renderComparison()}
        {activeTab === 3 && renderDetailedTable()}
      </Box>
    </Box>
  );
}