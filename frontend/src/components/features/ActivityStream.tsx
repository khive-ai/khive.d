"use client";

import { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  IconButton,
  Tooltip,
  Chip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Clear as ClearIcon,
  Pause as PauseIcon,
  PlayArrow as ResumeIcon,
  Psychology as AgentIcon,
  AccountTree as OrchestrationIcon,
  ErrorOutline as ErrorIcon,
  CheckCircle as SuccessIcon,
  Info as InfoIcon,
  Timeline as ActivityIcon
} from '@mui/icons-material';
import { CoordinationEvent } from '@/lib/types/khive';

interface ActivityStreamProps {
  events: CoordinationEvent[];
  focused: boolean;
}

export function ActivityStream({ events, focused: _focused }: ActivityStreamProps) {
  const theme = useTheme();
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);

  const filters = ['agent_spawn', 'task_start', 'task_complete', 'conflict', 'resolution'];

  const filteredEvents = useMemo(() => {
    if (!filter) return events;
    return events.filter(event => event.type === filter);
  }, [events, filter]);

  const getEventIcon = (type: string) => {
    const iconProps = { sx: { fontSize: 16 } };
    switch (type) {
      case 'agent_spawn': return <AgentIcon color="primary" {...iconProps} />;
      case 'task_start': return <OrchestrationIcon color="info" {...iconProps} />;
      case 'task_complete': return <SuccessIcon color="success" {...iconProps} />;
      case 'conflict': return <ErrorIcon color="error" {...iconProps} />;
      case 'resolution': return <SuccessIcon color="success" {...iconProps} />;
      default: return <InfoIcon color="action" {...iconProps} />;
    }
  };

  const formatTimestamp = (timestamp: number) => {
    const now = Date.now();
    const diff = now - timestamp;
    
    if (diff < 1000) return 'now';
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <Box sx={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <Box sx={{
        p: 2,
        borderBottom: `1px solid ${theme.palette.divider}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ActivityIcon color="primary" sx={{ fontSize: 20 }} />
          <Typography variant="h6" sx={{ fontSize: '14px', fontWeight: 600 }}>
            Activity Stream
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Chip 
            label={filteredEvents.length} 
            size="small"
            color="primary"
            variant="outlined"
            sx={{ height: 20, fontSize: '11px' }}
          />
          
          <Tooltip title={paused ? "Resume updates" : "Pause updates"}>
            <IconButton size="small" onClick={() => setPaused(!paused)}>
              {paused ? <ResumeIcon sx={{ fontSize: 16 }} /> : <PauseIcon sx={{ fontSize: 16 }} />}
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Clear all events">
            <IconButton size="small">
              <ClearIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Filters */}
      <Box sx={{
        p: 1,
        borderBottom: `1px solid ${theme.palette.divider}`,
        display: 'flex',
        gap: 0.5,
        flexWrap: 'wrap'
      }}>
        <Chip
          label="all"
          size="small"
          clickable
          color={filter === null ? "primary" : "default"}
          variant={filter === null ? "filled" : "outlined"}
          onClick={() => setFilter(null)}
          sx={{ height: 24, fontSize: '11px' }}
        />
        {filters.map(f => (
          <Chip
            key={f}
            label={f.replace('_', ' ')}
            size="small"
            clickable
            color={filter === f ? "primary" : "default"}
            variant={filter === f ? "filled" : "outlined"}
            onClick={() => setFilter(f)}
            sx={{ height: 24, fontSize: '11px' }}
          />
        ))}
      </Box>

      {/* Events List */}
      <Box sx={{ 
        flex: 1, 
        overflow: 'auto', 
        p: 1,
        bgcolor: alpha(theme.palette.background.default, 0.3)
      }}>
        {filteredEvents.length === 0 ? (
          <Box sx={{ 
            p: 3, 
            textAlign: 'center',
            color: 'text.secondary'
          }}>
            <ActivityIcon sx={{ fontSize: 48, opacity: 0.3, mb: 1 }} />
            <Typography variant="body2">
              No activity events
            </Typography>
            <Typography variant="caption">
              Events will appear here as orchestrations run
            </Typography>
          </Box>
        ) : (
          filteredEvents.map((event, index) => (
            <Paper 
              key={`${event.coordination_id}-${event.timestamp}-${index}`}
              sx={{
                p: 1.5,
                mb: 1,
                borderLeft: `3px solid ${theme.palette.primary.main}`,
                bgcolor: alpha(theme.palette.primary.main, 0.05),
                transition: 'all 0.2s ease',
                '&:hover': {
                  bgcolor: alpha(theme.palette.primary.main, 0.1)
                }
              }}
            >
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'flex-start', 
                gap: 1
              }}>
                {/* Event Icon */}
                <Box sx={{ mt: 0.25 }}>
                  {getEventIcon(event.type)}
                </Box>
                
                {/* Event Content */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontSize: '13px',
                      lineHeight: 1.4,
                      wordBreak: 'break-word'
                    }}
                  >
                    {event.message}
                  </Typography>
                  
                  {/* Event Metadata */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                    <Typography
                      variant="caption"
                      sx={{
                        color: 'text.secondary',
                        fontFamily: 'monospace',
                        fontSize: '10px'
                      }}
                    >
                      {formatTimestamp(event.timestamp)}
                    </Typography>
                    
                    {event.agent_id && (
                      <Chip
                        label={event.agent_id.split('_')[0]}
                        size="small"
                        sx={{
                          height: 16,
                          fontSize: '9px',
                          bgcolor: alpha(theme.palette.secondary.main, 0.1),
                          color: theme.palette.secondary.main,
                          '& .MuiChip-label': { px: 0.5 }
                        }}
                      />
                    )}
                  </Box>
                </Box>
              </Box>
            </Paper>
          ))
        )}
      </Box>

      {/* Status Bar */}
      <Box sx={{
        p: 1,
        borderTop: `1px solid ${theme.palette.divider}`,
        bgcolor: theme.palette.background.default,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Typography variant="caption" sx={{ 
          color: 'text.secondary',
          fontFamily: 'monospace',
          fontSize: '10px'
        }}>
          {paused ? '⏸ PAUSED' : '▶ LIVE'} • {filteredEvents.length} events
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box
            sx={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              bgcolor: paused ? theme.palette.warning.main : theme.palette.success.main,
              animation: paused ? 'none' : 'pulse 2s infinite'
            }}
          />
        </Box>
      </Box>
    </Box>
  );
}