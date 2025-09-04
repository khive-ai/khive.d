// @ts-nocheck
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { OrchestrationSession, SessionMetrics } from '@/lib/types/khive';
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
  Alert
} from '@mui/material';

interface CostTrackerProps {
  coordinationId?: string;
  sessionId?: string;
  showDetails?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  budgetLimit?: number;
  onBudgetExceeded?: (currentCost: number, limit: number) => void;
}

/**
 * CostTrackerMUI - Material-UI version of real-time cost monitoring component
 */
export function CostTrackerMUI({
  coordinationId,
  sessionId,
  showDetails = true,
  autoRefresh = true,
  refreshInterval = 5000,
  budgetLimit,
  onBudgetExceeded
}: CostTrackerProps) {
  const [costHistory, setCostHistory] = useState<Array<{ timestamp: number; cost: number }>>([]);
  const [budgetAlert, setBudgetAlert] = useState(false);
  
  const queryClient = useQueryClient();
  const { connected, sessions, events } = useKhiveWebSocket();

  // Query cost analysis from API
  const { 
    data: costAnalysis, 
    isLoading, 
    error,
    refetch: refetchCosts 
  } = useQuery({
    queryKey: ['cost-analysis', coordinationId, sessionId],
    queryFn: () => KhiveApiService.getCostAnalysis(
      coordinationId,
      { start: Date.now() - 24 * 60 * 60 * 1000, end: Date.now() }
    ),
    refetchInterval: autoRefresh ? refreshInterval : false,
    retry: 2,
  });

  // Calculate real-time costs from WebSocket data
  const realtimeCosts = useMemo(() => {
    const relevantSessions = sessions.filter(session => {
      if (sessionId && session.sessionId !== sessionId) return false;
      if (coordinationId && session.coordination_id !== coordinationId) return false;
      return true;
    });

    const totalCost = relevantSessions.reduce((sum, session) => {
      return sum + (session.metrics?.cost || 0);
    }, 0);

    const totalTokens = relevantSessions.reduce((sum, session) => {
      return sum + (session.metrics?.tokensUsed || 0);
    }, 0);

    const totalApiCalls = relevantSessions.reduce((sum, session) => {
      return sum + (session.metrics?.apiCalls || 0);
    }, 0);

    return {
      totalCost,
      totalTokens,
      totalApiCalls,
      sessionCount: relevantSessions.length
    };
  }, [sessions, coordinationId, sessionId]);

  // Use API cost analysis as fallback when WebSocket unavailable
  const currentCosts = connected ? {
    totalCost: realtimeCosts.totalCost,
    totalTokens: realtimeCosts.totalTokens,
    totalApiCalls: realtimeCosts.totalApiCalls
  } : {
    totalCost: costAnalysis?.total_cost || 0,
    totalTokens: (costAnalysis?.token_usage.input || 0) + (costAnalysis?.token_usage.output || 0),
    totalApiCalls: costAnalysis?.api_calls || 0
  };

  // Budget monitoring
  useEffect(() => {
    if (budgetLimit && currentCosts.totalCost > budgetLimit) {
      if (!budgetAlert) {
        setBudgetAlert(true);
        onBudgetExceeded?.(currentCosts.totalCost, budgetLimit);
      }
    } else {
      setBudgetAlert(false);
    }
  }, [currentCosts.totalCost, budgetLimit, budgetAlert, onBudgetExceeded]);

  // Listen for cost-related WebSocket events
  useEffect(() => {
    if (connected) {
      const costEvents = events.filter(event => 
        event.type === 'agent_spawn' || event.type === 'task_complete'
      );
      
      if (costEvents.length > 0) {
        queryClient.invalidateQueries({ queryKey: ['cost-analysis'] });
      }
    }
  }, [events, connected, queryClient]);

  const formatCurrency = useCallback((amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4
    }).format(amount);
  }, []);

  const formatTokens = useCallback((tokens: number) => {
    if (tokens < 1000) return tokens.toString();
    if (tokens < 1000000) return `${(tokens / 1000).toFixed(1)}K`;
    return `${(tokens / 1000000).toFixed(1)}M`;
  }, []);

  const budgetUtilization = budgetLimit ? (currentCosts.totalCost / budgetLimit) * 100 : 0;

  if (isLoading && !connected) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
        <CircularProgress size={24} />
        <Typography sx={{ ml: 2 }}>Loading cost data...</Typography>
      </Box>
    );
  }

  if (error && !connected) {
    return (
      <Alert severity="error">
        Error loading cost data: {error instanceof Error ? error.message : 'Unknown error'}
      </Alert>
    );
  }

  return (
    <Box>
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6">Cost Tracking</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {budgetAlert && (
                <Chip label="Budget Exceeded" color="error" size="small" />
              )}
              <Chip
                label={connected ? 'Live' : 'API'}
                color={connected ? 'success' : 'default'}
                size="small"
              />
              <Button
                size="small"
                variant="outlined"
                onClick={() => refetchCosts()}
                disabled={isLoading}
              >
                Refresh
              </Button>
            </Box>
          </Box>

          <Grid container spacing={3}>
            {/* Total cost */}
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography 
                  variant="h3" 
                  sx={{ 
                    color: budgetAlert ? 'error.main' : 'success.main',
                    fontWeight: 'bold'
                  }}
                >
                  {formatCurrency(currentCosts.totalCost)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Cost
                </Typography>
              </Box>
            </Grid>

            {/* Token usage */}
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ color: 'primary.main', fontWeight: 'bold' }}>
                  {formatTokens(currentCosts.totalTokens)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Tokens Used
                </Typography>
                {costAnalysis && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                    {formatTokens(costAnalysis.token_usage.input)} in / 
                    {formatTokens(costAnalysis.token_usage.output)} out
                  </Typography>
                )}
              </Box>
            </Grid>

            {/* API calls */}
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" sx={{ color: 'secondary.main', fontWeight: 'bold' }}>
                  {currentCosts.totalApiCalls}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  API Calls
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                  {realtimeCosts.sessionCount} sessions
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {/* Budget monitoring */}
          {budgetLimit && (
            <Box sx={{ mt: 4, p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'center', mb: 1 }}>
                <Typography variant="body1" fontWeight="medium">
                  Budget Status
                </Typography>
                <Typography 
                  variant="body2" 
                  color={budgetUtilization > 90 ? 'error.main' : 'text.secondary'}
                >
                  {budgetUtilization.toFixed(1)}% used
                </Typography>
              </Box>
              
              <LinearProgress 
                variant="determinate" 
                value={Math.min(budgetUtilization, 100)}
                sx={{ 
                  height: 8,
                  borderRadius: 1,
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: budgetUtilization > 100 ? 'error.main' :
                                   budgetUtilization > 80 ? 'warning.main' : 'success.main'
                  }
                }}
              />
              
              <Box sx={{ display: 'flex', justifyContent: 'between', mt: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {formatCurrency(currentCosts.totalCost)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {formatCurrency(budgetLimit)}
                </Typography>
              </Box>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Detailed breakdown */}
      {showDetails && costAnalysis?.cost_breakdown && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Cost Breakdown
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {Object.entries(costAnalysis.cost_breakdown).map(([category, cost]) => (
                <Box key={category} sx={{ display: 'flex', justifyContent: 'between', alignItems: 'center' }}>
                  <Typography variant="body1" sx={{ textTransform: 'capitalize' }}>
                    {category.replace('_', ' ')}
                  </Typography>
                  <Box sx={{ textAlign: 'right' }}>
                    <Typography variant="body1" fontWeight="medium">
                      {formatCurrency(cost)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {Math.round((cost / costAnalysis.total_cost) * 100)}%
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}