import React, { useState, useCallback, useEffect } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { OrchestrationSession, SessionAction, SessionFilter, SessionGroup } from '@/lib/types/khive';
import { KhiveApiService } from '@/lib/services/khiveApiService';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';
import { 
  Card, 
  CardContent, 
  Typography, 
  Button, 
  Chip, 
  Box, 
  Paper,
  LinearProgress,
  CircularProgress,
  Grid,
  Divider,
  IconButton
} from '@mui/material';

interface SessionManagerProps {
  coordinationId?: string;
  showControls?: boolean;
  onSessionSelect?: (session: OrchestrationSession) => void;
}

/**
 * SessionManagerMUI - Material-UI version of session management component
 */
export function SessionManagerMUI({ 
  coordinationId, 
  showControls = true, 
  onSessionSelect 
}: SessionManagerProps) {
  const [filter, setFilter] = useState<SessionFilter>({
    coordination_id: coordinationId,
  });
  
  const queryClient = useQueryClient();
  const { 
    connected, 
    sessions: realtimeSessions, 
    subscribeToSession,
    unsubscribeFromSession,
    joinCoordination,
    leaveCoordination 
  } = useKhiveWebSocket();

  // Query sessions with API fallback when WebSocket unavailable
  const { 
    data: apiSessions = [], 
    isLoading, 
    error 
  } = useQuery({
    queryKey: ['sessions', coordinationId],
    queryFn: coordinationId 
      ? () => KhiveApiService.getSessionsByCoordination(coordinationId)
      : KhiveApiService.getSessions,
    enabled: !connected,
    refetchInterval: connected ? false : 5000,
  });

  // Use real-time sessions when connected, fallback to API sessions
  const sessions = connected ? realtimeSessions : apiSessions;

  // Session action mutation
  const sessionActionMutation = useMutation({
    mutationFn: (action: SessionAction) => KhiveApiService.sessionAction(action),
    onSuccess: (result, action) => {
      if (result.success) {
        queryClient.setQueryData(['sessions', coordinationId], (oldSessions: OrchestrationSession[] = []) => {
          return oldSessions.map(session => 
            session.sessionId === action.sessionId
              ? { 
                  ...session, 
                  status: action.type === 'pause' ? 'paused' as const 
                          : action.type === 'resume' ? 'executing' as const
                          : action.type === 'terminate' ? 'stopped' as const
                          : session.status
                }
              : session
          );
        });
      }
    },
  });

  // WebSocket coordination management
  useEffect(() => {
    if (connected && coordinationId) {
      joinCoordination(coordinationId);
      return () => leaveCoordination(coordinationId);
    }
  }, [connected, coordinationId, joinCoordination, leaveCoordination]);

  const handleSessionAction = useCallback((sessionId: string, actionType: SessionAction['type']) => {
    sessionActionMutation.mutate({
      type: actionType,
      sessionId,
      reason: `${actionType} requested by user`
    });
  }, [sessionActionMutation]);

  const getStatusColor = (status: OrchestrationSession['status']) => {
    switch (status) {
      case 'completed': return 'success';
      case 'failed': case 'stopped': return 'error';
      case 'executing': return 'primary';
      case 'paused': return 'warning';
      default: return 'default';
    }
  };

  const formatDuration = (duration: number) => {
    if (duration < 60) return `${Math.round(duration)}s`;
    if (duration < 3600) return `${Math.round(duration / 60)}m`;
    return `${Math.round(duration / 3600)}h`;
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading sessions...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3, bgcolor: 'error.light' }}>
        <Typography color="error">
          Error loading sessions: {error instanceof Error ? error.message : 'Unknown error'}
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Session Management</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip
            label={connected ? 'Real-time' : 'API Polling'}
            color={connected ? 'success' : 'default'}
            size="small"
          />
          <Typography variant="body2" color="text.secondary">
            {sessions.length} sessions
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={2}>
        {sessions.map(session => (
          <Grid item xs={12} key={session.sessionId}>
            <Card 
              sx={{ 
                cursor: 'pointer',
                '&:hover': { bgcolor: 'action.hover' }
              }}
              onClick={() => onSessionSelect?.(session)}
            >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'flex-start' }}>
                  <Box sx={{ flex: 1 }}>
                    <Typography variant="h6" noWrap>
                      {session.flowName}
                    </Typography>
                    
                    <Box sx={{ display: 'flex', gap: 1, mt: 1, mb: 1 }}>
                      <Chip 
                        label={session.pattern || 'Expert'}
                        size="small"
                        variant="outlined"
                      />
                      <Chip 
                        label={session.status}
                        size="small"
                        color={getStatusColor(session.status)}
                      />
                    </Box>

                    <Typography variant="body2" color="text.secondary">
                      ID: {session.sessionId.slice(0, 8)}... • 
                      Coord: {session.coordination_id.slice(0, 8)}... • 
                      Phase {session.phase || 1}/{session.totalPhases || 1} • 
                      {session.agents?.length || 0} agents • 
                      {formatDuration(session.duration)}
                    </Typography>

                    {session.metrics && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        Cost: ${session.metrics.cost.toFixed(4)} • 
                        Tokens: {session.metrics.tokensUsed.toLocaleString()} • 
                        API calls: {session.metrics.apiCalls}
                      </Typography>
                    )}
                  </Box>

                  {showControls && (session.status === 'executing' || session.status === 'paused') && (
                    <Box sx={{ display: 'flex', gap: 1, ml: 2 }}>
                      {session.status === 'executing' && (
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSessionAction(session.sessionId, 'pause');
                          }}
                          disabled={sessionActionMutation.isPending}
                        >
                          Pause
                        </Button>
                      )}
                      {session.status === 'paused' && (
                        <Button
                          size="small"
                          variant="outlined"
                          color="primary"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSessionAction(session.sessionId, 'resume');
                          }}
                          disabled={sessionActionMutation.isPending}
                        >
                          Resume
                        </Button>
                      )}
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm('Are you sure you want to terminate this session?')) {
                            handleSessionAction(session.sessionId, 'terminate');
                          }
                        }}
                        disabled={sessionActionMutation.isPending}
                      >
                        Stop
                      </Button>
                    </Box>
                  )}
                </Box>

                {/* Progress bar for active sessions */}
                {(session.status === 'executing' || session.status === 'initializing') && (
                  <LinearProgress 
                    sx={{ mt: 1 }}
                    variant={session.phase && session.totalPhases ? 'determinate' : 'indeterminate'}
                    value={session.phase && session.totalPhases ? (session.phase / session.totalPhases) * 100 : undefined}
                  />
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
        
        {sessions.length === 0 && (
          <Grid item xs={12}>
            <Paper sx={{ p: 6, textAlign: 'center' }}>
              <Typography color="text.secondary">
                No sessions found
                {coordinationId && (
                  <Box sx={{ mt: 1 }}>
                    for coordination: {coordinationId}
                  </Box>
                )}
              </Typography>
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
}