"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Typography, Chip, Collapse, useTheme } from '@mui/material';
import { KHIVE_CONFIG } from '@/lib/config/khive';

interface PerformanceMetrics {
  commandResponseTime: number;
  contextSwitchTime: number;
  websocketLatency: number;
  renderTime: number;
  memoryUsage: number;
  keyboardLatency: number;
}

interface PerformanceAlert {
  id: string;
  type: 'warning' | 'critical';
  metric: keyof PerformanceMetrics;
  value: number;
  threshold: number;
  timestamp: number;
}

export function PerformanceMonitor() {
  const theme = useTheme();
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    commandResponseTime: 0,
    contextSwitchTime: 0,
    websocketLatency: 0,
    renderTime: 0,
    memoryUsage: 0,
    keyboardLatency: 0
  });
  
  const [alerts, setAlerts] = useState<PerformanceAlert[]>([]);
  const [isVisible, setIsVisible] = useState(false);
  const startTimeRef = useRef<{ [key: string]: number }>({});
  const frameRef = useRef<number>();

  // Performance thresholds based on Ocean's expectations
  const thresholds = {
    commandResponseTime: KHIVE_CONFIG.UI.COMMAND_RESPONSE_TIME_MS,
    contextSwitchTime: KHIVE_CONFIG.UI.CONTEXT_SWITCH_TIME_MS,
    websocketLatency: 200,
    renderTime: 16, // 60 FPS target
    memoryUsage: 100, // MB
    keyboardLatency: 50
  };

  // Measure command response time
  const measureCommandStart = useCallback((commandId: string) => {
    startTimeRef.current[commandId] = performance.now();
  }, []);

  const measureCommandEnd = useCallback((commandId: string) => {
    const startTime = startTimeRef.current[commandId];
    if (startTime) {
      const responseTime = performance.now() - startTime;
      setMetrics(prev => ({ ...prev, commandResponseTime: responseTime }));
      delete startTimeRef.current[commandId];
      
      // Check for performance issues
      if (responseTime > thresholds.commandResponseTime) {
        addAlert('warning', 'commandResponseTime', responseTime);
      }
    }
  }, [thresholds.commandResponseTime]);

  // Measure keyboard latency
  const measureKeyboardLatency = useCallback(() => {
    const startTime = performance.now();
    
    // Use setTimeout to measure actual processing latency
    setTimeout(() => {
      const latency = performance.now() - startTime;
      setMetrics(prev => ({ ...prev, keyboardLatency: latency }));
      
      if (latency > thresholds.keyboardLatency) {
        addAlert('warning', 'keyboardLatency', latency);
      }
    }, 0);
  }, [thresholds.keyboardLatency]);

  // Measure render performance
  const measureRenderTime = useCallback(() => {
    const startTime = performance.now();
    
    frameRef.current = requestAnimationFrame(() => {
      const renderTime = performance.now() - startTime;
      setMetrics(prev => ({ ...prev, renderTime }));
      
      if (renderTime > thresholds.renderTime) {
        addAlert('critical', 'renderTime', renderTime);
      }
    });
  }, [thresholds.renderTime]);

  // Monitor memory usage
  const monitorMemoryUsage = useCallback(() => {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      const usedMB = memory.usedJSHeapSize / (1024 * 1024);
      setMetrics(prev => ({ ...prev, memoryUsage: usedMB }));
      
      if (usedMB > thresholds.memoryUsage) {
        addAlert('critical', 'memoryUsage', usedMB);
      }
    }
  }, [thresholds.memoryUsage]);

  // Add performance alert
  const addAlert = useCallback((type: 'warning' | 'critical', metric: keyof PerformanceMetrics, value: number) => {
    const alert: PerformanceAlert = {
      id: `${metric}-${Date.now()}`,
      type,
      metric,
      value,
      threshold: thresholds[metric],
      timestamp: Date.now()
    };
    
    setAlerts(prev => [alert, ...prev.slice(0, 4)]); // Keep only 5 most recent alerts
    
    // Auto-dismiss warnings after 5 seconds
    if (type === 'warning') {
      setTimeout(() => {
        setAlerts(prev => prev.filter(a => a.id !== alert.id));
      }, 5000);
    }
  }, [thresholds]);

  // Setup performance monitoring
  useEffect(() => {
    // Monitor render performance
    const renderInterval = setInterval(measureRenderTime, 1000);
    
    // Monitor memory usage
    const memoryInterval = setInterval(monitorMemoryUsage, 5000);
    
    // Listen for keyboard events to measure latency
    const handleKeyDown = () => measureKeyboardLatency();
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      clearInterval(renderInterval);
      clearInterval(memoryInterval);
      document.removeEventListener('keydown', handleKeyDown);
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [measureRenderTime, monitorMemoryUsage, measureKeyboardLatency]);

  // Toggle visibility with Ctrl+Shift+P
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === 'p') {
        setIsVisible(prev => !prev);
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const getMetricColor = (metric: keyof PerformanceMetrics, value: number) => {
    const threshold = thresholds[metric];
    if (value > threshold * 1.5) return '#ef4444'; // Critical
    if (value > threshold) return '#f59e0b'; // Warning
    return '#10b981'; // Good
  };

  const formatMetricValue = (metric: keyof PerformanceMetrics, value: number) => {
    switch (metric) {
      case 'memoryUsage':
        return `${value.toFixed(1)}MB`;
      default:
        return `${value.toFixed(1)}ms`;
    }
  };

  const getMetricLabel = (metric: keyof PerformanceMetrics) => {
    switch (metric) {
      case 'commandResponseTime': return 'Cmd Response';
      case 'contextSwitchTime': return 'Context Switch';
      case 'websocketLatency': return 'WS Latency';
      case 'renderTime': return 'Render Time';
      case 'memoryUsage': return 'Memory';
      case 'keyboardLatency': return 'Keyboard';
      default: return metric;
    }
  };

  // Expose measurement functions globally for integration
  useEffect(() => {
    (window as any).__khive_performance = {
      measureCommandStart,
      measureCommandEnd,
      measureKeyboardLatency
    };
    
    return () => {
      delete (window as any).__khive_performance;
    };
  }, [measureCommandStart, measureCommandEnd, measureKeyboardLatency]);

  return (
    <>
      {/* Performance Alerts */}
      {alerts.length > 0 && (
        <Box sx={{
          position: 'fixed',
          top: 40,
          right: 16,
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
          maxWidth: 300
        }}>
          {alerts.map(alert => (
            <Box
              key={alert.id}
              sx={{
                p: 2,
                bgcolor: alert.type === 'critical' ? '#fef2f2' : '#fefbf3',
                border: `1px solid ${alert.type === 'critical' ? '#fca5a5' : '#fcd34d'}`,
                borderRadius: 1,
                fontSize: '12px',
                fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT
              }}
            >
              <Typography variant="caption" sx={{ 
                fontWeight: 'bold',
                color: alert.type === 'critical' ? '#dc2626' : '#d97706'
              }}>
                {alert.type === 'critical' ? '🔴' : '🟡'} Performance {alert.type.toUpperCase()}
              </Typography>
              <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                {getMetricLabel(alert.metric)}: {formatMetricValue(alert.metric, alert.value)}
                {' > '}{formatMetricValue(alert.metric, alert.threshold)} threshold
              </Typography>
            </Box>
          ))}
        </Box>
      )}

      {/* Performance Monitor Panel */}
      <Collapse in={isVisible}>
        <Box sx={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          width: 320,
          bgcolor: theme.palette.background.paper,
          border: `1px solid ${theme.palette.divider}`,
          borderRadius: 2,
          p: 2,
          zIndex: 1000,
          fontFamily: KHIVE_CONFIG.THEME.TERMINAL_FONT,
          fontSize: '12px'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 'bold', flex: 1 }}>
              Performance Monitor
            </Typography>
            <Chip 
              label="Ctrl+Shift+P" 
              size="small" 
              sx={{ 
                height: 16,
                fontSize: '10px',
                bgcolor: theme.palette.action.hover
              }} 
            />
          </Box>

          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
            {Object.entries(metrics).map(([key, value]) => {
              const metric = key as keyof PerformanceMetrics;
              const color = getMetricColor(metric, value);
              
              return (
                <Box key={key} sx={{ display: 'flex', flexDirection: 'column' }}>
                  <Typography variant="caption" color="text.secondary">
                    {getMetricLabel(metric)}
                  </Typography>
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontWeight: 'bold',
                      color,
                      fontFamily: 'monospace'
                    }}
                  >
                    {formatMetricValue(metric, value)}
                  </Typography>
                  <Box sx={{
                    height: 2,
                    bgcolor: theme.palette.action.hover,
                    borderRadius: 1,
                    overflow: 'hidden',
                    mt: 0.5
                  }}>
                    <Box sx={{
                      height: '100%',
                      width: `${Math.min(100, (value / thresholds[metric]) * 100)}%`,
                      bgcolor: color,
                      transition: 'width 0.3s ease'
                    }} />
                  </Box>
                </Box>
              );
            })}
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ 
            mt: 2,
            display: 'block',
            textAlign: 'center'
          }}>
            Ocean's CLI Performance Targets: {thresholds.commandResponseTime}ms response, {thresholds.contextSwitchTime}ms context switch
          </Typography>
        </Box>
      </Collapse>
    </>
  );
}