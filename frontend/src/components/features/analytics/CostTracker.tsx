// @ts-nocheck
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { OrchestrationSession, SessionMetrics } from '@/lib/types/khive';
import { KhiveApiService } from '@/lib/services/khiveApiService';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';
import { Card, CardHeader, CardContent, Typography, Chip, Button } from '@mui/material';

interface CostTrackerProps {
  coordinationId?: string;
  sessionId?: string;
  showDetails?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  budgetLimit?: number;
  onBudgetExceeded?: (currentCost: number, limit: number) => void;
}

interface CostBreakdown {
  total: number;
  sessions: Record<string, {
    cost: number;
    tokensUsed: number;
    apiCalls: number;
    duration: number;
    status: string;
  }>;
  agents: Record<string, {
    cost: number;
    tokensUsed: number;
    successRate: number;
    avgTaskTime: number;
  }>;
  timeRange: {
    start: number;
    end: number;
  };
}

/**
 * CostTracker - Real-time cost monitoring and accumulation component
 * 
 * Features:
 * - Real-time cost tracking via WebSocket events
 * - Cost breakdown by sessions and agents
 * - Budget monitoring with alerts
 * - Token usage and API call tracking
 * - Historical cost analysis
 * - Resource utilization metrics
 */
export function CostTracker({
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
      { start: Date.now() - 24 * 60 * 60 * 1000, end: Date.now() } // Last 24 hours
    ),
    refetchInterval: autoRefresh ? refreshInterval : false,
    retry: 2,
  });

  // Query session metrics for detailed breakdown
  const { data: sessionMetrics } = useQuery({
    queryKey: ['session-metrics', sessionId],
    queryFn: () => sessionId ? KhiveApiService.getSessionMetrics(sessionId) : null,
    enabled: !!sessionId,
    refetchInterval: autoRefresh ? refreshInterval : false,
  });

  // Calculate real-time costs from WebSocket data
  const realtimeCosts = useMemo(() => {
    const relevantSessions = sessions.filter(session => {
      if (sessionId && session.sessionId !== sessionId) return false;
      if (coordinationId && session.coordination_id !== coordinationId) return false;
      return true;
    });

    const breakdown: CostBreakdown = {
      total: 0,
      sessions: {},
      agents: {},
      timeRange: {
        start: Math.min(...relevantSessions.map(s => s.startTime)),
        end: Date.now()
      }
    };

    relevantSessions.forEach(session => {
      const sessionCost = session.metrics?.cost || 0;
      breakdown.total += sessionCost;
      
      breakdown.sessions[session.sessionId] = {
        cost: sessionCost,
        tokensUsed: session.metrics?.tokensUsed || 0,
        apiCalls: session.metrics?.apiCalls || 0,
        duration: session.duration,
        status: session.status
      };

      // Aggregate agent costs
      session.agents?.forEach(agent => {
        if (!breakdown.agents[agent.id]) {
          breakdown.agents[agent.id] = {
            cost: agent.metrics?.cost || 0,
            tokensUsed: agent.metrics?.tokensUsed || 0,
            successRate: agent.metrics?.successRate || 0,
            avgTaskTime: agent.metrics?.avgTaskTime || 0
          };
        } else {
          breakdown.agents[agent.id].cost += agent.metrics?.cost || 0;
          breakdown.agents[agent.id].tokensUsed += agent.metrics?.tokensUsed || 0;
        }
      });
    });

    return breakdown;
  }, [sessions, coordinationId, sessionId]);

  // Use API cost analysis as fallback when WebSocket unavailable
  const currentCosts = connected ? realtimeCosts : {
    total: costAnalysis?.total_cost || 0,
    sessions: {},
    agents: {},
    timeRange: { start: Date.now() - 24 * 60 * 60 * 1000, end: Date.now() }
  };

  // Track cost history for trend analysis
  useEffect(() => {
    if (currentCosts.total > 0) {
      setCostHistory(prev => {
        const newEntry = { timestamp: Date.now(), cost: currentCosts.total };
        const updated = [...prev, newEntry];
        
        // Keep only last 100 entries (last ~8 hours with 5s intervals)
        return updated.slice(-100);
      });
    }
  }, [currentCosts.total]);

  // Budget monitoring
  useEffect(() => {
    if (budgetLimit && currentCosts.total > budgetLimit) {
      if (!budgetAlert) {
        setBudgetAlert(true);
        onBudgetExceeded?.(currentCosts.total, budgetLimit);
      }
    } else {
      setBudgetAlert(false);
    }
  }, [currentCosts.total, budgetLimit, budgetAlert, onBudgetExceeded]);

  // Listen for cost-related WebSocket events
  useEffect(() => {
    if (connected) {
      const costEvents = events.filter(event => 
        event.type === 'agent_spawn' || event.type === 'task_complete'
      );
      
      if (costEvents.length > 0) {
        // Invalidate cost queries to refresh with new data
        queryClient.invalidateQueries({ queryKey: ['cost-analysis'] });
        if (sessionId) {
          queryClient.invalidateQueries({ queryKey: ['session-metrics'] });
        }
      }
    }
  }, [events, connected, queryClient, sessionId]);

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

  const calculateCostTrend = useCallback(() => {
    if (costHistory.length < 2) return 0;
    
    const recent = costHistory.slice(-10); // Last 10 data points
    const firstHalf = recent.slice(0, Math.floor(recent.length / 2));
    const secondHalf = recent.slice(Math.floor(recent.length / 2));
    
    const firstAvg = firstHalf.reduce((sum, item) => sum + item.cost, 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((sum, item) => sum + item.cost, 0) / secondHalf.length;
    
    return secondAvg - firstAvg;
  }, [costHistory]);

  const costTrend = calculateCostTrend();
  
  const budgetUtilization = budgetLimit ? (currentCosts.total / budgetLimit) * 100 : 0;

  if (isLoading && !connected) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"></div>
            <span className="ml-2">Loading cost data...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !connected) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-red-600">
            Error loading cost data: {error instanceof Error ? error.message : 'Unknown error'}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Main cost display */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <Typography className="text-lg">Cost Tracking</Typography>
            <div className="flex items-center space-x-2">
              {budgetAlert && (
                <Chip variant="destructive">Budget Exceeded</Chip>
              )}
              <Chip variant={connected ? 'success' : 'secondary'}>
                {connected ? 'Live' : 'API'}
              </Chip>
              <Button
                size="sm"
                variant="outline"
                onClick={() => refetchCosts()}
                disabled={isLoading}
              >
                Refresh
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Total cost */}
            <div className="text-center">
              <div className={`text-3xl font-bold ${budgetAlert ? 'text-red-600' : 'text-green-600'}`}>
                {formatCurrency(currentCosts.total)}
              </div>
              <div className="text-sm text-gray-500 mt-1">Total Cost</div>
              {costTrend !== 0 && (
                <div className={`text-xs mt-1 ${costTrend > 0 ? 'text-red-500' : 'text-green-500'}`}>
                  {costTrend > 0 ? '↑' : '↓'} {formatCurrency(Math.abs(costTrend))} trend
                </div>
              )}
            </div>

            {/* Token usage */}
            <div className="text-center">
              <div className="text-2xl font-semibold text-blue-600">
                {formatTokens(costAnalysis?.token_usage.input + costAnalysis?.token_usage.output || 0)}
              </div>
              <div className="text-sm text-gray-500 mt-1">Tokens Used</div>
              <div className="text-xs text-gray-400 mt-1">
                {formatTokens(costAnalysis?.token_usage.input || 0)} in / 
                {formatTokens(costAnalysis?.token_usage.output || 0)} out
              </div>
            </div>

            {/* API calls */}
            <div className="text-center">
              <div className="text-2xl font-semibold text-purple-600">
                {costAnalysis?.api_calls || Object.keys(currentCosts.sessions).length}
              </div>
              <div className="text-sm text-gray-500 mt-1">API Calls</div>
              <div className="text-xs text-gray-400 mt-1">
                {Object.keys(currentCosts.sessions).length} sessions
              </div>
            </div>
          </div>

          {/* Budget monitoring */}
          {budgetLimit && (
            <div className="mt-6 p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">Budget Status</span>
                <span className={budgetUtilization > 90 ? 'text-red-600' : 'text-gray-600'}>
                  {budgetUtilization.toFixed(1)}% used
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${
                    budgetUtilization > 100 ? 'bg-red-600' :
                    budgetUtilization > 80 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(budgetUtilization, 100)}%` }}
                ></div>
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>{formatCurrency(currentCosts.total)}</span>
                <span>{formatCurrency(budgetLimit)}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detailed breakdown */}
      {showDetails && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Session breakdown */}
          {Object.keys(currentCosts.sessions).length > 0 && (
            <Card>
              <CardHeader>
                <Typography className="text-base">Session Costs</Typography>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(currentCosts.sessions)
                    .sort(([, a], [, b]) => b.cost - a.cost)
                    .slice(0, 5) // Show top 5 most expensive
                    .map(([sessionId, data]) => (
                    <div key={sessionId} className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">
                          {sessionId.slice(0, 8)}...
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatTokens(data.tokensUsed)} tokens • {data.apiCalls} calls
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">{formatCurrency(data.cost)}</div>
                        <Chip variant="outline" className="text-xs">
                          {data.status}
                        </Chip>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Agent breakdown */}
          {Object.keys(currentCosts.agents).length > 0 && (
            <Card>
              <CardHeader>
                <Typography className="text-base">Agent Costs</Typography>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(currentCosts.agents)
                    .sort(([, a], [, b]) => b.cost - a.cost)
                    .slice(0, 5) // Show top 5 most expensive
                    .map(([agentId, data]) => (
                    <div key={agentId} className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">
                          {agentId.slice(0, 12)}...
                        </div>
                        <div className="text-xs text-gray-500">
                          {Math.round(data.successRate * 100)}% success • 
                          {formatTokens(data.tokensUsed)} tokens
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">{formatCurrency(data.cost)}</div>
                        <div className="text-xs text-gray-500">
                          {data.avgTaskTime > 0 && `${Math.round(data.avgTaskTime)}s avg`}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Cost history mini-chart would go here if we had a charting library */}
      {costHistory.length > 5 && (
        <Card>
          <CardHeader>
            <Typography className="text-base">Cost Trend</Typography>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-gray-600">
              Tracking {costHistory.length} data points over time
              {costTrend > 0 ? ' (increasing)' : costTrend < 0 ? ' (decreasing)' : ' (stable)'}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}