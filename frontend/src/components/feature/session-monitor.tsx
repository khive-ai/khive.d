/**
 * Session Monitor Component
 * Displays real-time session information and status
 */

import React from 'react';
import { 
  Box, 
  Typography, 
  Grid, 
  LinearProgress, 
  Tooltip,
  IconButton,
  Chip,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { Card, CardHeader, CardContent, StatusBadge } from '@/ui';
import { Session } from '@/types';
import { formatDate, formatDuration } from '@/utils';

export interface SessionMonitorProps {
  session: Session;
  onPause?: (sessionId: string) => void;
  onResume?: (sessionId: string) => void;
  onStop?: (sessionId: string) => void;
  onRefresh?: (sessionId: string) => void;
  className?: string;
}

export const SessionMonitor: React.FC<SessionMonitorProps> = ({
  session,
  onPause,
  onResume,
  onStop,
  onRefresh,
  className,
}) => {
  const getStatusColor = (status: Session['status']) => {
    switch (status) {
      case 'running':
        return 'success';
      case 'completed':
        return 'info';
      case 'failed':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getProgressValue = () => {
    if (session.status === 'completed') return 100;
    if (session.status === 'failed') return 100;
    if (session.status === 'running') return session.confidence * 100;
    return 0;
  };

  const getProgressColor = () => {
    if (session.status === 'failed') return 'error';
    if (session.status === 'completed') return 'success';
    return 'primary';
  };

  const handleAction = (action: 'pause' | 'resume' | 'stop' | 'refresh') => {
    switch (action) {
      case 'pause':
        onPause?.(session.id);
        break;
      case 'resume':
        onResume?.(session.id);
        break;
      case 'stop':
        onStop?.(session.id);
        break;
      case 'refresh':
        onRefresh?.(session.id);
        break;
    }
  };

  const actions = (
    <Box display="flex" alignItems="center" gap={1}>
      <Tooltip title="Refresh Session">
        <IconButton 
          size="small" 
          onClick={() => handleAction('refresh')}
          disabled={session.status === 'completed' || session.status === 'failed'}
        >
          <RefreshIcon />
        </IconButton>
      </Tooltip>
      
      {session.status === 'running' && (
        <>
          <Tooltip title="Pause Session">
            <IconButton size="small" onClick={() => handleAction('pause')}>
              <PauseIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Stop Session">
            <IconButton size="small" onClick={() => handleAction('stop')}>
              <StopIcon />
            </IconButton>
          </Tooltip>
        </>
      )}
      
      {session.status === 'pending' && (
        <Tooltip title="Resume Session">
          <IconButton size="small" onClick={() => handleAction('resume')}>
            <PlayIcon />
          </IconButton>
        </Tooltip>
      )}
      
      <Tooltip title="Session Info">
        <IconButton size="small">
          <InfoIcon />
        </IconButton>
      </Tooltip>
    </Box>
  );

  return (
    <Card className={className} variant="outlined">
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={2}>
            <Typography variant="h6" component="h3">
              Session {session.id.slice(-8)}
            </Typography>
            <StatusBadge status={session.status} />
          </Box>
        }
        subtitle={
          <Typography variant="body2" color="text.secondary">
            Coordination ID: {session.coordinationId}
          </Typography>
        }
        action={actions}
      />
      
      <CardContent>
        <Grid container spacing={3}>
          {/* Session Objective */}
          <Grid item xs={12}>
            <Box mb={2}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Objective
              </Typography>
              <Typography variant="body1">
                {session.objective}
              </Typography>
            </Box>
          </Grid>
          
          {/* Progress and Metrics */}
          <Grid item xs={12} md={6}>
            <Box mb={2}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="subtitle2" color="text.secondary">
                  Progress
                </Typography>
                <Typography variant="body2">
                  {getProgressValue().toFixed(0)}%
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={getProgressValue()}
                color={getProgressColor() as any}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Box display="flex" flexDirection="column" gap={1}>
              <Box display="flex" justifyContent="between" alignItems="center">
                <Typography variant="subtitle2" color="text.secondary">
                  Complexity
                </Typography>
                <Chip 
                  label={session.complexity.toFixed(1)} 
                  size="small"
                  color={session.complexity > 0.7 ? 'error' : session.complexity > 0.4 ? 'warning' : 'success'}
                />
              </Box>
              
              <Box display="flex" justifyContent="between" alignItems="center">
                <Typography variant="subtitle2" color="text.secondary">
                  Confidence
                </Typography>
                <Chip 
                  label={`${(session.confidence * 100).toFixed(0)}%`}
                  size="small"
                  color={session.confidence > 0.7 ? 'success' : session.confidence > 0.4 ? 'warning' : 'error'}
                />
              </Box>
            </Box>
          </Grid>
          
          {/* Timestamps */}
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Created
            </Typography>
            <Typography variant="body2">
              {formatDate(session.createdAt)}
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" color="text.secondary">
              Last Updated
            </Typography>
            <Typography variant="body2">
              {formatDate(session.updatedAt)}
            </Typography>
          </Grid>
          
          {/* Context */}
          {session.context && (
            <Grid item xs={12}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Context
              </Typography>
              <Typography 
                variant="body2" 
                sx={{ 
                  backgroundColor: 'grey.50', 
                  p: 2, 
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                }}
              >
                {session.context}
              </Typography>
            </Grid>
          )}
        </Grid>
      </CardContent>
    </Card>
  );
};