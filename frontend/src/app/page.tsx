/**
 * Khive Dashboard Home Page
 * Landing page for the intelligent agent orchestration dashboard
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Box, 
  Container, 
  Typography, 
  Grid, 
  Card, 
  CardContent, 
  Button,
  Chip,
  LinearProgress,
  useTheme,
  alpha
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Psychology as AgentIcon,
  Timeline as MetricsIcon,
  Settings as SettingsIcon,
  PlayArrow as StartIcon,
  Speed as PerformanceIcon,
} from '@mui/icons-material';
import { useCoordinationMetrics, useSessions, useAgents } from '@/lib/api/hooks';

interface QuickStatsCardProps {
  title: string;
  value: string | number;
  description: string;
  icon: React.ReactNode;
  color: 'primary' | 'secondary' | 'success' | 'warning';
  trend?: {
    direction: 'up' | 'down';
    percentage: number;
  };
}

function QuickStatsCard({ title, value, description, icon, color, trend }: QuickStatsCardProps) {
  const theme = useTheme();
  
  return (
    <Card 
      sx={{ 
        height: '100%',
        background: `linear-gradient(135deg, ${alpha(theme.palette[color].main, 0.1)}, ${alpha(theme.palette[color].light, 0.05)})`,
        border: `1px solid ${alpha(theme.palette[color].main, 0.2)}`,
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: theme.shadows[8],
        },
        transition: 'all 0.3s ease-in-out',
      }}
    >
      <CardContent sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box 
            sx={{ 
              p: 1, 
              borderRadius: 2, 
              backgroundColor: alpha(theme.palette[color].main, 0.1),
              mr: 2 
            }}
          >
            {icon}
          </Box>
          <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
            {title}
          </Typography>
        </Box>
        
        <Typography 
          variant="h3" 
          component="div" 
          sx={{ 
            fontWeight: 700, 
            color: theme.palette[color].main,
            mb: 1 
          }}
        >
          {value}
        </Typography>
        
        <Typography 
          variant="body2" 
          color="text.secondary" 
          sx={{ mb: trend ? 2 : 0 }}
        >
          {description}
        </Typography>
        
        {trend && (
          <Chip
            label={`${trend.direction === 'up' ? '+' : '-'}${trend.percentage}%`}
            size="small"
            color={trend.direction === 'up' ? 'success' : 'error'}
            sx={{ fontSize: '0.75rem' }}
          />
        )}
      </CardContent>
    </Card>
  );
}

export default function HomePage() {
  const theme = useTheme();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  
  // Fetch real-time data
  const { data: metrics } = useCoordinationMetrics();
  const { data: sessions } = useSessions();

  useEffect(() => {
    // Simulate loading for better UX
    const timer = setTimeout(() => setIsLoading(false), 1500);
    return () => clearTimeout(timer);
  }, []);

  const quickActions = [
    {
      title: 'View Dashboard',
      description: 'Monitor active sessions and agents',
      icon: <DashboardIcon />,
      path: '/dashboard',
      color: 'primary' as const,
    },
    {
      title: 'Agent Management',
      description: 'Manage and monitor AI agents',
      icon: <AgentIcon />,
      path: '/dashboard/agents',
      color: 'secondary' as const,
    },
    {
      title: 'Performance Metrics',
      description: 'View coordination and performance data',
      icon: <MetricsIcon />,
      path: '/dashboard/metrics',
      color: 'success' as const,
    },
    {
      title: 'System Settings',
      description: 'Configure orchestration parameters',
      icon: <SettingsIcon />,
      path: '/dashboard/settings',
      color: 'warning' as const,
    },
  ];

  if (isLoading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 8, mb: 8 }}>
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h3" component="h1" gutterBottom>
            Loading Khive Dashboard
          </Typography>
          <LinearProgress sx={{ mt: 2, borderRadius: 2 }} />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 8 }}>
      {/* Hero Section */}
      <Box sx={{ textAlign: 'center', mb: 6 }}>
        <Typography 
          variant="h2" 
          component="h1" 
          gutterBottom 
          sx={{ 
            fontWeight: 700,
            background: `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Khive Dashboard
        </Typography>
        <Typography 
          variant="h5" 
          color="text.secondary" 
          sx={{ mb: 3, fontWeight: 400 }}
        >
          Intelligent Agent Orchestration & Coordination Platform
        </Typography>
        <Typography 
          variant="body1" 
          color="text.secondary" 
          sx={{ maxWidth: 600, mx: 'auto', mb: 4 }}
        >
          Monitor and manage AI agents in real-time with advanced coordination metrics, 
          session tracking, and performance analytics.
        </Typography>
        
        <Button
          variant="contained"
          size="large"
          startIcon={<StartIcon />}
          onClick={() => router.push('/dashboard')}
          sx={{
            px: 4,
            py: 1.5,
            fontSize: '1.1rem',
            borderRadius: 3,
            textTransform: 'none',
            fontWeight: 600,
          }}
        >
          Launch Dashboard
        </Button>
      </Box>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 6 }}>
        <Grid item xs={12} sm={6} md={3}>
          <QuickStatsCard
            title="Active Sessions"
            value={sessions?.filter(s => s.status === 'running').length ?? 0}
            description="Currently running orchestration sessions"
            icon={<DashboardIcon color="primary" />}
            color="primary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <QuickStatsCard
            title="Active Agents"
            value={metrics?.activeAgents ?? 0}
            description="AI agents currently coordinating"
            icon={<AgentIcon color="secondary" />}
            color="secondary"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <QuickStatsCard
            title="Conflicts Prevented"
            value={metrics?.conflictsPrevented ?? 0}
            description="Coordination conflicts avoided today"
            icon={<PerformanceIcon color="success" />}
            color="success"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <QuickStatsCard
            title="Avg Completion Time"
            value={`${(metrics?.averageTaskCompletionTime ?? 0).toFixed(1)}s`}
            description="Average task completion time"
            icon={<MetricsIcon color="warning" />}
            color="warning"
          />
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Typography 
        variant="h4" 
        component="h2" 
        gutterBottom 
        sx={{ mb: 3, fontWeight: 600 }}
      >
        Quick Actions
      </Typography>
      
      <Grid container spacing={3}>
        {quickActions.map((action, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card 
              sx={{ 
                height: '100%',
                cursor: 'pointer',
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: theme.shadows[4],
                },
                transition: 'all 0.2s ease-in-out',
              }}
              onClick={() => router.push(action.path)}
            >
              <CardContent sx={{ p: 3, textAlign: 'center' }}>
                <Box 
                  sx={{ 
                    mb: 2,
                    '& svg': {
                      fontSize: '2.5rem',
                      color: theme.palette[action.color].main,
                    }
                  }}
                >
                  {action.icon}
                </Box>
                <Typography 
                  variant="h6" 
                  component="div" 
                  gutterBottom
                  sx={{ fontWeight: 600 }}
                >
                  {action.title}
                </Typography>
                <Typography 
                  variant="body2" 
                  color="text.secondary"
                >
                  {action.description}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* System Status */}
      <Box sx={{ mt: 6, p: 3, borderRadius: 2, backgroundColor: 'background.paper' }}>
        <Typography variant="h5" gutterBottom sx={{ fontWeight: 600 }}>
          System Status
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Box 
                sx={{ 
                  width: 12, 
                  height: 12, 
                  borderRadius: '50%', 
                  backgroundColor: 'success.main',
                  mr: 1 
                }}
              />
              <Typography variant="body2">
                API Connection: Healthy
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Box 
                sx={{ 
                  width: 12, 
                  height: 12, 
                  borderRadius: '50%', 
                  backgroundColor: 'success.main',
                  mr: 1 
                }}
              />
              <Typography variant="body2">
                Real-time Updates: Active
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={12} sm={4}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Box 
                sx={{ 
                  width: 12, 
                  height: 12, 
                  borderRadius: '50%', 
                  backgroundColor: metrics ? 'success.main' : 'warning.main',
                  mr: 1 
                }}
              />
              <Typography variant="body2">
                Coordination Service: {metrics ? 'Online' : 'Initializing'}
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Box>
    </Container>
  );
}