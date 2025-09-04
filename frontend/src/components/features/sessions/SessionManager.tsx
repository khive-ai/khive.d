import React, { useState, useCallback, useEffect } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { OrchestrationSession, SessionAction, SessionFilter, SessionGroup, Agent } from '@/lib/types/khive';
import { KhiveApiService } from '@/lib/services/khiveApiService';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';
import { Card, CardContent, Typography, Button, Chip, Box, Paper } from '@mui/material';

interface SessionManagerProps {
  coordinationId?: string;
  showControls?: boolean;
  onSessionSelect?: (session: OrchestrationSession) => void;
}

/**
 * SessionManager - Core session lifecycle management component
 * 
 * Provides comprehensive session management capabilities:
 * - Real-time session monitoring via WebSocket
 * - Session lifecycle actions (pause, resume, terminate)
 * - Session grouping by coordination ID
 * - Integration with KHIVE API services
 */
export function SessionManager({ 
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
    enabled: !connected, // Only use API when WebSocket disconnected
    refetchInterval: connected ? false : 5000, // Poll when disconnected
  });

  // Use real-time sessions when connected, fallback to API sessions
  const sessions = connected ? realtimeSessions : apiSessions;

  // Session action mutation for lifecycle management
  const sessionActionMutation = useMutation({
    mutationFn: (action: SessionAction) => KhiveApiService.sessionAction(action),
    onSuccess: (result, action) => {
      if (result.success) {
        // Optimistically update session status
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
    onError: (error) => {
      console.error('Session action failed:', error);
    },
  });

  // Group sessions by coordination ID for better organization
  const groupedSessions = useCallback(() => {
    const groups = new Map<string, SessionGroup>();
    
    sessions.forEach(session => {
      const coordId = session.coordination_id;
      if (!groups.has(coordId)) {
        groups.set(coordId, {
          coordination_id: coordId,
          sessions: [],
          pattern: session.pattern || 'Expert',
          status: 'active',
          totalAgents: 0,
          startTime: session.startTime,
          duration: 0,
          metrics: {
            tokensUsed: 0,
            apiCalls: 0,
            cost: 0,
            avgResponseTime: 0,
            successRate: 0,
            resourceUtilization: { cpu: 0, memory: 0, network: 0 }
          }
        });
      }
      
      const group = groups.get(coordId)!;
      group.sessions.push(session);
      group.totalAgents += session.agents?.length || 0;
      
      // Aggregate metrics
      if (session.metrics) {
        group.metrics.tokensUsed += session.metrics.tokensUsed;
        group.metrics.apiCalls += session.metrics.apiCalls;
        group.metrics.cost += session.metrics.cost;
      }
      
      // Determine group status
      const sessionStatuses = group.sessions.map(s => s.status);
      if (sessionStatuses.every(s => s === 'completed')) {
        group.status = 'completed';
      } else if (sessionStatuses.some(s => s === 'failed')) {
        group.status = 'failed';
      } else if (sessionStatuses.some(s => s === 'executing' || s === 'ready')) {
        group.status = 'active';
      } else {
        group.status = 'mixed';
      }
      
      // Calculate total duration
      group.duration = Math.max(...group.sessions.map(s => s.duration));
    });
    
    return Array.from(groups.values());
  }, [sessions]);

  // WebSocket coordination management
  useEffect(() => {
    if (connected && coordinationId) {
      joinCoordination(coordinationId);
      return () => leaveCoordination(coordinationId);
    }
  }, [connected, coordinationId, joinCoordination, leaveCoordination]);

  // Subscribe to session updates for active sessions
  useEffect(() => {
    if (connected) {
      const activeSessions = sessions.filter(s => 
        s.status === 'executing' || s.status === 'ready' || s.status === 'initializing'
      );
      
      activeSessions.forEach(session => {
        subscribeToSession(session.sessionId);
      });
      
      return () => {
        activeSessions.forEach(session => {
          unsubscribeFromSession(session.sessionId);
        });
      };
    }
  }, [connected, sessions, subscribeToSession, unsubscribeFromSession]);

  const handleSessionAction = useCallback((sessionId: string, actionType: SessionAction['type'], reason?: string) => {
    sessionActionMutation.mutate({
      type: actionType,
      sessionId,
      reason: reason || `${actionType} requested by user`
    });
  }, [sessionActionMutation]);

  const getStatusBadgeVariant = (status: OrchestrationSession['status']) => {
    switch (status) {
      case 'completed': return 'success';
      case 'failed': case 'stopped': return 'destructive';
      case 'executing': return 'default';
      case 'paused': return 'secondary';
      case 'ready': case 'initializing': return 'outline';
      default: return 'secondary';
    }
  };

  const formatDuration = (duration: number) => {
    if (duration < 60) return `${Math.round(duration)}s`;
    if (duration < 3600) return `${Math.round(duration / 60)}m`;
    return `${Math.round(duration / 3600)}h`;
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            <span className="ml-2">Loading sessions...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-red-600">
            Error loading sessions: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        </CardContent>
      </Card>
    );
  }

  const groups = groupedSessions();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Session Management</h2>
        <div className="flex items-center space-x-2">
          <Badge variant={connected ? 'success' : 'destructive'}>
            {connected ? 'Real-time' : 'API Polling'}
          </Badge>
          <span className="text-sm text-gray-500">
            {sessions.length} sessions
          </span>
        </div>
      </div>

      <div className="space-y-4">
        {groups.map(group => (
          <Card key={group.coordination_id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  Coordination: {group.coordination_id.slice(0, 8)}...
                </CardTitle>
                <div className="flex items-center space-x-2">
                  <Badge>{group.pattern}</Badge>
                  <Badge variant={
                    group.status === 'active' ? 'default' :
                    group.status === 'completed' ? 'success' :
                    group.status === 'failed' ? 'destructive' : 'secondary'
                  }>
                    {group.status}
                  </Badge>
                  <span className="text-sm text-gray-500">
                    {group.totalAgents} agents
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {group.sessions.map(session => (
                  <div 
                    key={session.sessionId}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    onClick={() => onSessionSelect?.(session)}
                  >
                    <div className="flex items-center space-x-3">
                      <div>
                        <div className="font-medium">{session.flowName}</div>
                        <div className="text-sm text-gray-500">
                          Phase {session.phase || 1}/{session.totalPhases || 1} • 
                          {formatDuration(session.duration)} • 
                          {session.agents?.length || 0} agents
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Badge variant={getStatusBadgeVariant(session.status)}>
                        {session.status}
                      </Badge>
                      
                      {showControls && (session.status === 'executing' || session.status === 'paused') && (
                        <div className="flex space-x-1">
                          {session.status === 'executing' && (
                            <Button
                              size="sm"
                              variant="outline"
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
                              size="sm"
                              variant="outline"
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
                            size="sm"
                            variant="destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (confirm('Are you sure you want to terminate this session?')) {
                                handleSessionAction(session.sessionId, 'terminate');
                              }
                            }}
                            disabled={sessionActionMutation.isPending}
                          >
                            Stop
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              {group.metrics.cost > 0 && (
                <div className="mt-3 pt-3 border-t">
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="font-medium">${group.metrics.cost.toFixed(4)}</div>
                      <div className="text-gray-500">Total Cost</div>
                    </div>
                    <div>
                      <div className="font-medium">{group.metrics.tokensUsed.toLocaleString()}</div>
                      <div className="text-gray-500">Tokens Used</div>
                    </div>
                    <div>
                      <div className="font-medium">{group.metrics.apiCalls}</div>
                      <div className="text-gray-500">API Calls</div>
                    </div>
                    <div>
                      <div className="font-medium">{Math.round(group.metrics.successRate * 100)}%</div>
                      <div className="text-gray-500">Success Rate</div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        
        {groups.length === 0 && (
          <Card>
            <CardContent className="p-6 text-center text-gray-500">
              No sessions found
              {coordinationId && (
                <div className="text-sm mt-2">
                  for coordination: {coordinationId}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}