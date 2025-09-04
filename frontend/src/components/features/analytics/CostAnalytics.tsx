// @ts-nocheck
import React, { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { OrchestrationSession } from '@/lib/types/khive';
import { KhiveApiService } from '@/lib/services/khiveApiService';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';
import { Card, CardHeader, CardContent, Typography, Chip, Button } from '@mui/material';

interface CostAnalyticsProps {
  timeRange?: {
    start: number;
    end: number;
  };
  coordinationId?: string;
}

interface OptimizationInsight {
  type: 'warning' | 'info' | 'success';
  category: 'cost' | 'performance' | 'efficiency' | 'pattern';
  title: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  recommendation: string;
  estimatedSavings?: number;
}

interface UsagePattern {
  pattern: string;
  sessions: number;
  avgCost: number;
  avgDuration: number;
  successRate: number;
  efficiency: number; // cost per successful task
}

/**
 * CostAnalytics - Usage pattern analysis and optimization insights
 * 
 * Features:
 * - Cost efficiency analysis by orchestration patterns
 * - Agent role performance comparison
 * - Time-based usage trends
 * - Optimization recommendations
 * - ROI analysis for different coordination strategies
 * - Resource utilization patterns
 */
export function CostAnalytics({ timeRange, coordinationId }: CostAnalyticsProps) {
  const [selectedTimeRange, setSelectedTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h');
  
  const { sessions } = useKhiveWebSocket();

  // Calculate time range based on selection
  const analysisTimeRange = useMemo(() => {
    if (timeRange) return timeRange;
    
    const end = Date.now();
    const start = (() => {
      switch (selectedTimeRange) {
        case '1h': return end - 60 * 60 * 1000;
        case '24h': return end - 24 * 60 * 60 * 1000;
        case '7d': return end - 7 * 24 * 60 * 60 * 1000;
        case '30d': return end - 30 * 24 * 60 * 60 * 1000;
        default: return end - 24 * 60 * 60 * 1000;
      }
    })();
    
    return { start, end };
  }, [timeRange, selectedTimeRange]);

  // Query cost analysis data
  const { data: costAnalysis, isLoading } = useQuery({
    queryKey: ['cost-analysis-detailed', coordinationId, analysisTimeRange],
    queryFn: () => KhiveApiService.getCostAnalysis(coordinationId, analysisTimeRange),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Analyze usage patterns from session data
  const usagePatterns = useMemo((): UsagePattern[] => {
    const filteredSessions = sessions.filter(session => {
      if (coordinationId && session.coordination_id !== coordinationId) return false;
      if (session.startTime < analysisTimeRange.start || session.startTime > analysisTimeRange.end) return false;
      return true;
    });

    const patternGroups = new Map<string, OrchestrationSession[]>();
    
    filteredSessions.forEach(session => {
      const pattern = session.pattern || 'Expert';
      if (!patternGroups.has(pattern)) {
        patternGroups.set(pattern, []);
      }
      patternGroups.get(pattern)!.push(session);
    });

    return Array.from(patternGroups.entries()).map(([pattern, patternSessions]) => {
      const completedSessions = patternSessions.filter(s => s.status === 'completed');
      const totalCost = patternSessions.reduce((sum, s) => sum + (s.metrics?.cost || 0), 0);
      const totalDuration = patternSessions.reduce((sum, s) => sum + s.duration, 0);
      const successRate = completedSessions.length / patternSessions.length;
      
      return {
        pattern,
        sessions: patternSessions.length,
        avgCost: totalCost / patternSessions.length,
        avgDuration: totalDuration / patternSessions.length,
        successRate,
        efficiency: totalCost / Math.max(completedSessions.length, 1)
      };
    }).sort((a, b) => b.sessions - a.sessions);
  }, [sessions, coordinationId, analysisTimeRange]);

  // Generate optimization insights
  const optimizationInsights = useMemo((): OptimizationInsight[] => {
    const insights: OptimizationInsight[] = [];

    if (!costAnalysis) return insights;

    // High cost per API call insight
    const avgCostPerCall = costAnalysis.total_cost / Math.max(costAnalysis.api_calls, 1);
    if (avgCostPerCall > 0.10) {
      insights.push({
        type: 'warning',
        category: 'cost',
        title: 'High cost per API call',
        description: `Average cost of $${avgCostPerCall.toFixed(4)} per API call is above optimal range`,
        impact: 'high',
        recommendation: 'Consider optimizing prompt efficiency or using batch processing patterns',
        estimatedSavings: costAnalysis.total_cost * 0.25
      });
    }

    // Token efficiency analysis
    const costPerToken = costAnalysis.total_cost / Math.max(costAnalysis.token_usage.input + costAnalysis.token_usage.output, 1);
    if (costPerToken > 0.00005) {
      insights.push({
        type: 'info',
        category: 'efficiency',
        title: 'Token utilization could be improved',
        description: 'High cost per token suggests opportunities for optimization',
        impact: 'medium',
        recommendation: 'Review prompt templates and context management strategies'
      });
    }

    // Pattern efficiency comparison
    if (usagePatterns.length > 1) {
      const mostEfficientPattern = usagePatterns.reduce((min, pattern) => 
        pattern.efficiency < min.efficiency ? pattern : min
      );
      const leastEfficientPattern = usagePatterns.reduce((max, pattern) => 
        pattern.efficiency > max.efficiency ? pattern : max
      );

      if (leastEfficientPattern.efficiency > mostEfficientPattern.efficiency * 2) {
        insights.push({
          type: 'warning',
          category: 'pattern',
          title: 'Inefficient orchestration pattern detected',
          description: `${leastEfficientPattern.pattern} pattern is ${(leastEfficientPattern.efficiency / mostEfficientPattern.efficiency).toFixed(1)}x more expensive than ${mostEfficientPattern.pattern}`,
          impact: 'high',
          recommendation: `Consider using ${mostEfficientPattern.pattern} pattern for similar tasks`,
          estimatedSavings: (leastEfficientPattern.efficiency - mostEfficientPattern.efficiency) * leastEfficientPattern.sessions
        });
      }
    }

    // Success rate insights
    const avgSuccessRate = usagePatterns.reduce((sum, p) => sum + p.successRate, 0) / Math.max(usagePatterns.length, 1);
    if (avgSuccessRate < 0.85) {
      insights.push({
        type: 'warning',
        category: 'performance',
        title: 'Low success rate impacting costs',
        description: `${Math.round(avgSuccessRate * 100)}% success rate means paying for failed tasks`,
        impact: 'medium',
        recommendation: 'Review task definitions and agent coordination strategies'
      });
    }

    // Time-based optimization
    const timeRange = analysisTimeRange.end - analysisTimeRange.start;
    const costPerHour = costAnalysis.total_cost / (timeRange / (1000 * 60 * 60));
    if (costPerHour > 10) {
      insights.push({
        type: 'info',
        category: 'cost',
        title: 'High hourly cost rate',
        description: `Current rate of $${costPerHour.toFixed(2)}/hour`,
        impact: 'medium',
        recommendation: 'Consider implementing cost controls and session limits'
      });
    }

    return insights.sort((a, b) => {
      const impactOrder = { high: 3, medium: 2, low: 1 };
      return impactOrder[b.impact] - impactOrder[a.impact];
    });
  }, [costAnalysis, usagePatterns, analysisTimeRange]);

  const formatCurrency = useCallback((amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4
    }).format(amount);
  }, []);

  const getInsightBadgeVariant = (insight: OptimizationInsight) => {
    switch (insight.type) {
      case 'warning': return 'destructive';
      case 'info': return 'default';
      case 'success': return 'success';
      default: return 'secondary';
    }
  };

  const getPatternDescription = (pattern: string) => {
    switch (pattern) {
      case 'P∥': return 'Parallel';
      case 'P→': return 'Sequential';
      case 'P⊕': return 'Tournament';
      case 'Pⓕ': return 'Flow';
      case 'P⊗': return 'Hybrid';
      case 'Expert': return 'Expert';
      default: return pattern;
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"></div>
            <span className="ml-2">Analyzing usage patterns...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with time range selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Cost Analytics & Optimization</h2>
        <div className="flex space-x-2">
          {(['1h', '24h', '7d', '30d'] as const).map(range => (
            <Button
              key={range}
              variant={selectedTimeRange === range ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedTimeRange(range)}
            >
              {range}
            </Button>
          ))}
        </div>
      </div>

      {/* Key metrics overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-600">
              {formatCurrency(costAnalysis?.total_cost || 0)}
            </div>
            <div className="text-sm text-gray-500">Total Cost</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-blue-600">
              {costAnalysis?.api_calls || 0}
            </div>
            <div className="text-sm text-gray-500">API Calls</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-purple-600">
              {((costAnalysis?.token_usage.input || 0) + (costAnalysis?.token_usage.output || 0)).toLocaleString()}
            </div>
            <div className="text-sm text-gray-500">Tokens Used</div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-orange-600">
              {usagePatterns.reduce((sum, p) => sum + p.sessions, 0)}
            </div>
            <div className="text-sm text-gray-500">Sessions</div>
          </CardContent>
        </Card>
      </div>

      {/* Optimization insights */}
      {optimizationInsights.length > 0 && (
        <Card>
          <CardHeader>
            <Typography>Optimization Insights</Typography>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {optimizationInsights.map((insight, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <h4 className="font-medium">{insight.title}</h4>
                        <Chip variant={getInsightChipVariant(insight)}>
                          {insight.impact} impact
                        </Chip>
                        <Chip variant="outline" className="text-xs">
                          {insight.category}
                        </Chip>
                      </div>
                      <p className="text-sm text-gray-600 mb-2">{insight.description}</p>
                      <p className="text-sm font-medium text-blue-600">{insight.recommendation}</p>
                    </div>
                    {insight.estimatedSavings && (
                      <div className="text-right">
                        <div className="text-sm font-medium text-green-600">
                          ~{formatCurrency(insight.estimatedSavings)}
                        </div>
                        <div className="text-xs text-gray-500">potential savings</div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Usage patterns analysis */}
      {usagePatterns.length > 0 && (
        <Card>
          <CardHeader>
            <Typography>Orchestration Pattern Analysis</Typography>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {usagePatterns.map((pattern) => (
                <div key={pattern.pattern} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-2">
                      <h4 className="font-medium">{getPatternDescription(pattern.pattern)}</h4>
                      <Chip variant="outline">{pattern.sessions} sessions</Chip>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">{formatCurrency(pattern.avgCost)}</div>
                      <div className="text-xs text-gray-500">avg cost</div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="font-medium">{Math.round(pattern.avgDuration)}s</div>
                      <div className="text-gray-500">Avg Duration</div>
                    </div>
                    <div>
                      <div className="font-medium">{Math.round(pattern.successRate * 100)}%</div>
                      <div className="text-gray-500">Success Rate</div>
                    </div>
                    <div>
                      <div className="font-medium">{formatCurrency(pattern.efficiency)}</div>
                      <div className="text-gray-500">Cost/Success</div>
                    </div>
                    <div>
                      <div className={`font-medium ${
                        pattern.efficiency < usagePatterns.reduce((sum, p) => sum + p.efficiency, 0) / usagePatterns.length 
                          ? 'text-green-600' : 'text-orange-600'
                      }`}>
                        {pattern.efficiency < usagePatterns.reduce((sum, p) => sum + p.efficiency, 0) / usagePatterns.length 
                          ? 'Efficient' : 'Costly'}
                      </div>
                      <div className="text-gray-500">Efficiency</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Cost breakdown */}
      {costAnalysis && (
        <Card>
          <CardHeader>
            <Typography>Cost Breakdown</Typography>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(costAnalysis.cost_breakdown).map(([category, cost]) => (
                <div key={category} className="flex items-center justify-between">
                  <span className="capitalize">{category.replace('_', ' ')}</span>
                  <div className="text-right">
                    <div className="font-medium">{formatCurrency(cost)}</div>
                    <div className="text-xs text-gray-500">
                      {Math.round((cost / costAnalysis.total_cost) * 100)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ROI recommendations */}
      <Card>
        <CardHeader>
          <Typography>ROI Recommendations</Typography>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="p-3 border rounded bg-blue-50">
              <div className="font-medium text-blue-800 mb-1">Cost Efficiency Tips</div>
              <ul className="text-blue-700 space-y-1">
                <li>• Use parallel patterns (P∥) for independent tasks to reduce total duration</li>
                <li>• Implement caching for repetitive agent compositions</li>
                <li>• Monitor token usage and optimize prompt templates</li>
                <li>• Set budget limits for experimental coordination flows</li>
              </ul>
            </div>
            
            <div className="p-3 border rounded bg-green-50">
              <div className="font-medium text-green-800 mb-1">Performance Optimization</div>
              <ul className="text-green-700 space-y-1">
                <li>• Profile agent performance and replace underperforming roles</li>
                <li>• Use tournament patterns (P⊕) for critical quality gates</li>
                <li>• Implement timeout controls to prevent runaway costs</li>
                <li>• Regular analysis of coordination patterns helps identify waste</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}