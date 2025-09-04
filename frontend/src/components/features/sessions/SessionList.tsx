import React, { useState, useMemo, useCallback } from 'react';
import { OrchestrationSession, SessionFilter } from '@/lib/types/khive';
import { useKhiveWebSocket } from '@/lib/hooks/useKhiveWebSocket';
import { KhiveApiService } from '@/lib/services/khiveApiService';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface SessionListProps {
  filter?: SessionFilter;
  onSessionSelect?: (session: OrchestrationSession) => void;
  onFilterChange?: (filter: SessionFilter) => void;
  showFilters?: boolean;
  compact?: boolean;
}

/**
 * SessionList - Enhanced session display and filtering component
 * 
 * Features:
 * - Advanced filtering by status, pattern, priority, tags
 * - Real-time search across session properties
 * - Date range filtering for historical analysis
 * - Compact mode for embedded use cases
 * - Integration with session persistence
 */
export function SessionList({
  filter = {},
  onSessionSelect,
  onFilterChange,
  showFilters = true,
  compact = false
}: SessionListProps) {
  const [searchTerm, setSearchTerm] = useState(filter.search || '');
  const [localFilter, setLocalFilter] = useState<SessionFilter>(filter);

  const { connected, sessions: realtimeSessions } = useKhiveWebSocket();

  // API fallback for sessions
  const { data: apiSessions = [] } = useQuery({
    queryKey: ['sessions', 'all'],
    queryFn: KhiveApiService.getSessions,
    enabled: !connected,
    refetchInterval: connected ? false : 10000,
  });

  const sessions = connected ? realtimeSessions : apiSessions;

  // Apply filtering and search
  const filteredSessions = useMemo(() => {
    let filtered = [...sessions];

    // Status filter
    if (localFilter.status?.length) {
      filtered = filtered.filter(s => localFilter.status!.includes(s.status));
    }

    // Pattern filter
    if (localFilter.pattern?.length) {
      filtered = filtered.filter(s => s.pattern && localFilter.pattern!.includes(s.pattern));
    }

    // Priority filter
    if (localFilter.priority?.length) {
      filtered = filtered.filter(s => s.priority && localFilter.priority!.includes(s.priority));
    }

    // Tags filter
    if (localFilter.tags?.length) {
      filtered = filtered.filter(s => 
        s.tags && localFilter.tags!.some(tag => s.tags!.includes(tag))
      );
    }

    // Coordination ID filter
    if (localFilter.coordination_id) {
      filtered = filtered.filter(s => s.coordination_id === localFilter.coordination_id);
    }

    // Date range filter
    if (localFilter.dateRange) {
      const { start, end } = localFilter.dateRange;
      filtered = filtered.filter(s => s.startTime >= start && s.startTime <= end);
    }

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(session => 
        session.flowName.toLowerCase().includes(term) ||
        session.sessionId.toLowerCase().includes(term) ||
        session.coordination_id.toLowerCase().includes(term) ||
        session.status.toLowerCase().includes(term) ||
        session.agents?.some(agent => 
          agent.role.toLowerCase().includes(term) ||
          agent.domain.toLowerCase().includes(term)
        ) ||
        session.tags?.some(tag => tag.toLowerCase().includes(term))
      );
    }

    return filtered;
  }, [sessions, localFilter, searchTerm]);

  // Sort sessions by start time (most recent first)
  const sortedSessions = useMemo(() => {
    return [...filteredSessions].sort((a, b) => b.startTime - a.startTime);
  }, [filteredSessions]);

  const handleFilterChange = useCallback((newFilter: Partial<SessionFilter>) => {
    const updatedFilter = { ...localFilter, ...newFilter };
    setLocalFilter(updatedFilter);
    onFilterChange?.(updatedFilter);
  }, [localFilter, onFilterChange]);

  const handleSearchChange = useCallback((value: string) => {
    setSearchTerm(value);
    const updatedFilter = { ...localFilter, search: value };
    setLocalFilter(updatedFilter);
    onFilterChange?.(updatedFilter);
  }, [localFilter, onFilterChange]);

  const getStatusColor = (status: OrchestrationSession['status']) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'failed': case 'stopped': return 'text-red-600';
      case 'executing': return 'text-blue-600';
      case 'paused': return 'text-yellow-600';
      case 'ready': case 'initializing': return 'text-gray-600';
      default: return 'text-gray-500';
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

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDuration = (duration: number) => {
    if (duration < 60) return `${Math.round(duration)}s`;
    if (duration < 3600) return `${Math.round(duration / 60)}m`;
    return `${Math.round(duration / 3600)}h`;
  };

  // Quick filter buttons
  const quickFilters = [
    { label: 'All', filter: {} },
    { label: 'Active', filter: { status: ['executing', 'ready', 'initializing'] } },
    { label: 'Completed', filter: { status: ['completed'] } },
    { label: 'Failed', filter: { status: ['failed', 'stopped'] } },
    { label: 'Today', filter: { 
      dateRange: { 
        start: new Date().setHours(0, 0, 0, 0), 
        end: new Date().setHours(23, 59, 59, 999) 
      } 
    } },
  ];

  return (
    <div className="space-y-4">
      {showFilters && (
        <Card>
          <CardContent className="p-4">
            <div className="space-y-4">
              {/* Search */}
              <div>
                <Input
                  placeholder="Search sessions by name, ID, status, agent roles..."
                  value={searchTerm}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  className="w-full"
                />
              </div>

              {/* Quick filters */}
              <div className="flex flex-wrap gap-2">
                {quickFilters.map((quickFilter) => (
                  <Button
                    key={quickFilter.label}
                    variant="outline"
                    size="sm"
                    onClick={() => handleFilterChange(quickFilter.filter)}
                    className={
                      JSON.stringify(localFilter) === JSON.stringify(quickFilter.filter)
                        ? 'bg-blue-100 border-blue-300'
                        : ''
                    }
                  >
                    {quickFilter.label}
                  </Button>
                ))}
              </div>

              {/* Active filters display */}
              {(localFilter.status?.length || localFilter.pattern?.length || 
                localFilter.priority?.length || localFilter.coordination_id) && (
                <div className="flex flex-wrap gap-2">
                  {localFilter.status?.map(status => (
                    <Badge key={status} variant="secondary">
                      Status: {status}
                      <button
                        onClick={() => handleFilterChange({
                          status: localFilter.status!.filter(s => s !== status)
                        })}
                        className="ml-1 text-xs"
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                  {localFilter.pattern?.map(pattern => (
                    <Badge key={pattern} variant="secondary">
                      Pattern: {getPatternDescription(pattern)}
                      <button
                        onClick={() => handleFilterChange({
                          pattern: localFilter.pattern!.filter(p => p !== pattern)
                        })}
                        className="ml-1 text-xs"
                      >
                        ×
                      </button>
                    </Badge>
                  ))}
                  {localFilter.coordination_id && (
                    <Badge variant="secondary">
                      Coordination: {localFilter.coordination_id.slice(0, 8)}...
                      <button
                        onClick={() => handleFilterChange({ coordination_id: undefined })}
                        className="ml-1 text-xs"
                      >
                        ×
                      </button>
                    </Badge>
                  )}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results summary */}
      <div className="flex items-center justify-between text-sm text-gray-600">
        <span>
          Showing {sortedSessions.length} of {sessions.length} sessions
        </span>
        <Badge variant={connected ? 'success' : 'secondary'}>
          {connected ? 'Live' : 'Cached'}
        </Badge>
      </div>

      {/* Session list */}
      <div className={`space-y-${compact ? '2' : '3'}`}>
        {sortedSessions.map((session) => (
          <Card 
            key={session.sessionId}
            className={`cursor-pointer hover:bg-gray-50 transition-colors ${
              compact ? 'p-3' : ''
            }`}
            onClick={() => onSessionSelect?.(session)}
          >
            <CardContent className={compact ? 'p-3' : 'p-4'}>
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <h3 className={`font-medium truncate ${compact ? 'text-sm' : ''}`}>
                      {session.flowName}
                    </h3>
                    <Badge variant="outline" className="text-xs">
                      {getPatternDescription(session.pattern || 'Expert')}
                    </Badge>
                    {session.priority && session.priority !== 'normal' && (
                      <Badge 
                        variant={session.priority === 'high' || session.priority === 'critical' 
                          ? 'destructive' : 'secondary'}
                        className="text-xs"
                      >
                        {session.priority}
                      </Badge>
                    )}
                  </div>
                  
                  <div className={`mt-1 text-gray-600 ${compact ? 'text-xs' : 'text-sm'}`}>
                    <div className="flex items-center space-x-4">
                      <span>ID: {session.sessionId.slice(0, 8)}...</span>
                      <span>Coord: {session.coordination_id.slice(0, 8)}...</span>
                      <span>Phase {session.phase || 1}/{session.totalPhases || 1}</span>
                      <span>{session.agents?.length || 0} agents</span>
                    </div>
                    {!compact && (
                      <div className="mt-1 flex items-center space-x-4">
                        <span>Started: {formatTimestamp(session.startTime)}</span>
                        <span>Duration: {formatDuration(session.duration)}</span>
                        {session.metrics && (
                          <span>Cost: ${session.metrics.cost.toFixed(4)}</span>
                        )}
                      </div>
                    )}
                  </div>

                  {session.tags && session.tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {session.tags.map(tag => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex flex-col items-end space-y-1">
                  <Badge 
                    variant="outline" 
                    className={`${getStatusColor(session.status)} border-current`}
                  >
                    {session.status}
                  </Badge>
                  
                  {session.metrics && !compact && (
                    <div className="text-xs text-gray-500 text-right">
                      <div>{session.metrics.tokensUsed.toLocaleString()} tokens</div>
                      <div>{session.metrics.apiCalls} API calls</div>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {sortedSessions.length === 0 && (
          <Card>
            <CardContent className="p-6 text-center text-gray-500">
              <div>No sessions found matching your filters</div>
              {searchTerm && (
                <div className="text-sm mt-2">
                  Try adjusting your search term: "{searchTerm}"
                </div>
              )}
              {Object.keys(localFilter).length > 0 && (
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => {
                    setLocalFilter({});
                    setSearchTerm('');
                    onFilterChange?.({});
                  }}
                  className="mt-2"
                >
                  Clear all filters
                </Button>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}