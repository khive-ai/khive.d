"use client";

import React, { useState } from 'react';
import { CostAnalytics, CostTracker } from '@/components/features/analytics';
import { SessionList } from '@/components/features/sessions';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';
import { useSessionPersistence } from '@/lib/hooks/useSessionPersistence';
import { OrchestrationSession } from '@/lib/types/khive';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function AnalyticsDashboard() {
  const [selectedTimeRange, setSelectedTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h');
  const [selectedCoordination, setSelectedCoordination] = useState<string | undefined>();
  const [activeView, setActiveView] = useState<'overview' | 'cost-analysis' | 'session-analysis'>('overview');

  const { sessions, connected } = useKhiveWebSocket();
  const { favoriteCoordinationIds, costBudgets } = useSessionPersistence();

  // Calculate analytics from sessions
  const sessionAnalytics = React.useMemo(() => {
    if (!sessions.length) {
      return {
        totalSessions: 0,
        completedSessions: 0,
        successRate: 0,
        avgResponseTime: 0,
        totalCost: 0,
        avgCostPerSession: 0
      };
    }

    const completed = sessions.filter(s => s.status === 'completed');
    const totalCost = sessions.reduce((sum, s) => sum + (s.metrics?.cost || 0), 0);
    const avgResponseTime = sessions.reduce((sum, s) => sum + (s.metrics?.avgResponseTime || 0), 0) / sessions.length;

    return {
      totalSessions: sessions.length,
      completedSessions: completed.length,
      successRate: (completed.length / sessions.length) * 100,
      avgResponseTime,
      totalCost,
      avgCostPerSession: totalCost / sessions.length
    };
  }, [sessions]);

  const timeRangeMap = {
    '1h': { start: Date.now() - 60 * 60 * 1000, end: Date.now() },
    '24h': { start: Date.now() - 24 * 60 * 60 * 1000, end: Date.now() },
    '7d': { start: Date.now() - 7 * 24 * 60 * 60 * 1000, end: Date.now() },
    '30d': { start: Date.now() - 30 * 24 * 60 * 60 * 1000, end: Date.now() }
  };

  const handleSessionSelect = (session: OrchestrationSession) => {
    setSelectedCoordination(session.coordination_id);
  };

  return (
    <div className="h-full overflow-auto">
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
          <div className="flex items-center space-x-2">
            <Badge variant={connected ? 'success' : 'secondary'}>
              {connected ? 'Live Data' : 'Cached'}
            </Badge>
            <span className="text-sm text-gray-500">
              {sessions.length} sessions analyzed
            </span>
          </div>
        </div>

        {/* Quick Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-green-600">
                {sessionAnalytics.successRate.toFixed(1)}%
              </div>
              <div className="text-sm text-gray-500">Success Rate</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-blue-600">
                {Math.round(sessionAnalytics.avgResponseTime)}ms
              </div>
              <div className="text-sm text-gray-500">Avg Response Time</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-purple-600">
                ${sessionAnalytics.totalCost.toFixed(4)}
              </div>
              <div className="text-sm text-gray-500">Total Cost</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-orange-600">
                {sessionAnalytics.totalSessions}
              </div>
              <div className="text-sm text-gray-500">Total Sessions</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-teal-600">
                {sessionAnalytics.completedSessions}
              </div>
              <div className="text-sm text-gray-500">Completed</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-bold text-pink-600">
                ${sessionAnalytics.avgCostPerSession.toFixed(4)}
              </div>
              <div className="text-sm text-gray-500">Avg Cost/Session</div>
            </CardContent>
          </Card>
        </div>

        {/* View Toggle */}
        <div className="flex space-x-1 border-b">
          <Button
            variant={activeView === 'overview' ? 'default' : 'ghost'}
            onClick={() => setActiveView('overview')}
            className="rounded-none border-0"
          >
            Overview
          </Button>
          <Button
            variant={activeView === 'cost-analysis' ? 'default' : 'ghost'}
            onClick={() => setActiveView('cost-analysis')}
            className="rounded-none border-0"
          >
            Cost Analysis
          </Button>
          <Button
            variant={activeView === 'session-analysis' ? 'default' : 'ghost'}
            onClick={() => setActiveView('session-analysis')}
            className="rounded-none border-0"
          >
            Session Analysis
          </Button>
        </div>

        {/* Content based on active view */}
        <div className="flex-1">
          {activeView === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Cost tracking for selected coordination */}
              <div>
                <CostTracker
                  coordinationId={selectedCoordination}
                  showDetails={false}
                  autoRefresh={true}
                  budgetLimit={selectedCoordination ? costBudgets[selectedCoordination] : undefined}
                />
              </div>

              {/* Session list with compact mode */}
              <div>
                <SessionList
                  onSessionSelect={handleSessionSelect}
                  showFilters={false}
                  compact={true}
                />
              </div>
            </div>
          )}

          {activeView === 'cost-analysis' && (
            <div>
              <CostAnalytics
                timeRange={timeRangeMap[selectedTimeRange]}
                coordinationId={selectedCoordination}
              />
            </div>
          )}

          {activeView === 'session-analysis' && (
            <div className="space-y-6">
              {/* Session filters and controls */}
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold">Session Analysis Filters</h3>
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

                  {favoriteCoordinationIds.length > 0 && (
                    <div>
                      <p className="text-sm font-medium mb-2">Favorite Coordinations:</p>
                      <div className="flex flex-wrap gap-2">
                        {favoriteCoordinationIds.map(id => (
                          <Button
                            key={id}
                            variant={selectedCoordination === id ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setSelectedCoordination(
                              selectedCoordination === id ? undefined : id
                            )}
                          >
                            {id.slice(0, 8)}...
                          </Button>
                        ))}
                        {selectedCoordination && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedCoordination(undefined)}
                          >
                            Clear
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Detailed session list */}
              <SessionList
                filter={{
                  coordination_id: selectedCoordination,
                  dateRange: timeRangeMap[selectedTimeRange]
                }}
                onSessionSelect={handleSessionSelect}
                showFilters={true}
                compact={false}
              />
            </div>
          )}
        </div>

        {/* Additional insights */}
        {sessionAnalytics.totalSessions === 0 && (
          <Card>
            <CardContent className="p-6 text-center text-gray-500">
              <div className="text-lg font-medium mb-2">No Data Yet</div>
              <div className="text-sm">
                Start some orchestration sessions to see analytics and cost tracking data here.
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}