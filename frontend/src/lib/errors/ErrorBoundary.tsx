"use client";

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Box, Typography, Button, Alert, Card, CardContent, Collapse, IconButton } from '@mui/material';
import { Error as ErrorIcon, ExpandMore, Refresh, BugReport } from '@mui/icons-material';

/**
 * Error Handling Architecture
 * 
 * Comprehensive error boundary system following software architecture principles:
 * 
 * Principles Applied:
 * - Error Boundary Pattern: Catch and handle React errors gracefully
 * - Strategy Pattern: Different error handling strategies per error type
 * - Observer Pattern: Error reporting and monitoring
 * - Retry Pattern: Automatic and manual error recovery
 * - Graceful Degradation: Fallback UI components
 * - Logging Architecture: Structured error logging and reporting
 */

export interface ErrorInfo {
  error: Error;
  errorInfo: React.ErrorInfo;
  timestamp: number;
  componentStack: string;
  errorBoundary: string;
  userId?: string;
  sessionId?: string;
  url: string;
  userAgent: string;
  additionalContext?: Record<string, any>;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  errorId: string | null;
  retryCount: number;
  showDetails: boolean;
  isRecovering: boolean;
}

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, errorInfo: React.ErrorInfo, retry: () => void) => ReactNode;
  onError?: (error: ErrorInfo) => void;
  enableRetry?: boolean;
  maxRetries?: number;
  retryDelay?: number;
  level?: 'page' | 'section' | 'component';
  isolate?: boolean;
  reportErrors?: boolean;
  showErrorDetails?: boolean;
  errorBoundaryId?: string;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private retryTimeoutId: NodeJS.Timeout | null = null;
  private readonly errorBoundaryId: string;

  constructor(props: ErrorBoundaryProps) {
    super(props);

    this.errorBoundaryId = props.errorBoundaryId || `error-boundary-${Math.random().toString(36).substr(2, 9)}`;
    
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null,
      retryCount: 0,
      showDetails: false,
      isRecovering: false
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
      errorId: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const enhancedErrorInfo: ErrorInfo = {
      error,
      errorInfo,
      timestamp: Date.now(),
      componentStack: errorInfo.componentStack,
      errorBoundary: this.errorBoundaryId,
      url: window.location.href,
      userAgent: navigator.userAgent,
      additionalContext: {
        level: this.props.level,
        retryCount: this.state.retryCount,
        isolate: this.props.isolate
      }
    };

    this.setState({
      errorInfo,
      showDetails: this.props.showErrorDetails ?? process.env.NODE_ENV === 'development'
    });

    // Report error
    this.reportError(enhancedErrorInfo);

    // Call custom error handler
    if (this.props.onError) {
      try {
        this.props.onError(enhancedErrorInfo);
      } catch (handlerError) {
        console.error('Error in custom error handler:', handlerError);
      }
    }
  }

  componentWillUnmount() {
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
    }
  }

  private reportError = (errorInfo: ErrorInfo) => {
    if (!this.props.reportErrors) return;

    try {
      // Send to logging service
      this.sendErrorToLoggingService(errorInfo);

      // Store locally for debugging
      this.storeErrorLocally(errorInfo);

      // Send to monitoring service (e.g., Sentry, LogRocket)
      this.sendToMonitoringService(errorInfo);
    } catch (reportingError) {
      console.error('Failed to report error:', reportingError);
    }
  };

  private sendErrorToLoggingService = (errorInfo: ErrorInfo) => {
    // Implementation would send to your logging service
    console.error('Error reported to logging service:', {
      errorId: this.state.errorId,
      message: errorInfo.error.message,
      stack: errorInfo.error.stack,
      componentStack: errorInfo.errorInfo.componentStack,
      timestamp: errorInfo.timestamp,
      url: errorInfo.url,
      userAgent: errorInfo.userAgent,
      additionalContext: errorInfo.additionalContext
    });
  };

  private storeErrorLocally = (errorInfo: ErrorInfo) => {
    try {
      const storedErrors = JSON.parse(localStorage.getItem('error-boundary-logs') || '[]');
      storedErrors.push({
        errorId: this.state.errorId,
        timestamp: errorInfo.timestamp,
        message: errorInfo.error.message,
        stack: errorInfo.error.stack,
        url: errorInfo.url
      });

      // Keep only last 50 errors
      if (storedErrors.length > 50) {
        storedErrors.splice(0, storedErrors.length - 50);
      }

      localStorage.setItem('error-boundary-logs', JSON.stringify(storedErrors));
    } catch (storageError) {
      console.warn('Failed to store error locally:', storageError);
    }
  };

  private sendToMonitoringService = (errorInfo: ErrorInfo) => {
    // Integration with monitoring services like Sentry
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      (window as any).Sentry.captureException(errorInfo.error, {
        contexts: {
          errorBoundary: {
            errorBoundaryId: this.errorBoundaryId,
            componentStack: errorInfo.errorInfo.componentStack,
            retryCount: this.state.retryCount
          }
        },
        tags: {
          errorBoundary: true,
          level: this.props.level || 'component'
        }
      });
    }
  };

  private handleRetry = () => {
    const { maxRetries = 3, retryDelay = 1000 } = this.props;

    if (this.state.retryCount >= maxRetries) {
      console.warn(`Max retries (${maxRetries}) reached for error boundary ${this.errorBoundaryId}`);
      return;
    }

    this.setState({ isRecovering: true });

    this.retryTimeoutId = setTimeout(() => {
      this.setState({
        hasError: false,
        error: null,
        errorInfo: null,
        errorId: null,
        retryCount: this.state.retryCount + 1,
        showDetails: false,
        isRecovering: false
      });
    }, retryDelay);
  };

  private toggleDetails = () => {
    this.setState({ showDetails: !this.state.showDetails });
  };

  private getErrorSeverity = (error: Error): 'low' | 'medium' | 'high' | 'critical' => {
    // Analyze error to determine severity
    const errorMessage = error.message.toLowerCase();
    const errorStack = error.stack?.toLowerCase() || '';

    if (errorMessage.includes('network') || errorMessage.includes('fetch')) {
      return 'medium';
    }

    if (errorMessage.includes('timeout') || errorMessage.includes('abort')) {
      return 'low';
    }

    if (errorMessage.includes('permission') || errorMessage.includes('auth')) {
      return 'high';
    }

    if (errorStack.includes('chunk') || errorMessage.includes('loading')) {
      return 'medium';
    }

    if (this.props.level === 'page') {
      return 'critical';
    }

    return 'medium';
  };

  private renderErrorFallback = () => {
    const { error, errorInfo, errorId, retryCount, showDetails, isRecovering } = this.state;
    const { enableRetry = true, maxRetries = 3, level = 'component' } = this.props;

    if (!error) return null;

    const severity = this.getErrorSeverity(error);
    const canRetry = enableRetry && retryCount < maxRetries;

    return (
      <Card 
        sx={{ 
          m: 2, 
          borderLeft: 4, 
          borderLeftColor: severity === 'critical' ? 'error.main' : 
                           severity === 'high' ? 'warning.main' : 
                           'info.main'
        }}
      >
        <CardContent>
          <Box display="flex" alignItems="center" gap={2} mb={2}>
            <ErrorIcon color="error" />
            <Box flex={1}>
              <Typography variant="h6" color="error">
                {level === 'page' ? 'Application Error' :
                 level === 'section' ? 'Section Error' :
                 'Component Error'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Something went wrong. Error ID: {errorId}
              </Typography>
            </Box>
          </Box>

          <Alert severity={severity === 'critical' ? 'error' : 'warning'} sx={{ mb: 2 }}>
            <Typography variant="body2">
              {error.message || 'An unexpected error occurred'}
            </Typography>
          </Alert>

          <Box display="flex" alignItems="center" gap={1} mb={2}>
            {canRetry && (
              <Button
                variant="contained"
                startIcon={<Refresh />}
                onClick={this.handleRetry}
                disabled={isRecovering}
                size="small"
              >
                {isRecovering ? 'Recovering...' : `Retry ${retryCount > 0 ? `(${retryCount}/${maxRetries})` : ''}`}
              </Button>
            )}

            {process.env.NODE_ENV === 'development' && (
              <Button
                variant="outlined"
                startIcon={<BugReport />}
                onClick={this.toggleDetails}
                size="small"
              >
                {showDetails ? 'Hide' : 'Show'} Details
              </Button>
            )}
          </Box>

          <Collapse in={showDetails}>
            <Box sx={{ bgcolor: 'grey.100', p: 2, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.75rem' }}>
              <Typography variant="subtitle2" gutterBottom>Error Stack:</Typography>
              <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 'inherit' }}>
                {error.stack}
              </pre>
              
              {errorInfo && (
                <>
                  <Typography variant="subtitle2" gutterBottom sx={{ mt: 2 }}>
                    Component Stack:
                  </Typography>
                  <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 'inherit' }}>
                    {errorInfo.componentStack}
                  </pre>
                </>
              )}
            </Box>
          </Collapse>

          {!canRetry && retryCount >= maxRetries && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Maximum retry attempts reached. Please refresh the page or contact support.
            </Alert>
          )}
        </CardContent>
      </Card>
    );
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback && this.state.error && this.state.errorInfo) {
        try {
          return this.props.fallback(this.state.error, this.state.errorInfo, this.handleRetry);
        } catch (fallbackError) {
          console.error('Error in custom fallback component:', fallbackError);
          return this.renderErrorFallback();
        }
      }

      return this.renderErrorFallback();
    }

    return this.props.children;
  }
}

/**
 * Higher-Order Component for automatic error boundary wrapping
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, 'children'>
) {
  const ComponentWithErrorBoundary = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  ComponentWithErrorBoundary.displayName = 
    `withErrorBoundary(${WrappedComponent.displayName || WrappedComponent.name})`;

  return ComponentWithErrorBoundary;
}

/**
 * Hook for error boundary context and manual error reporting
 */
export function useErrorHandler() {
  const reportError = React.useCallback((error: Error, additionalContext?: Record<string, any>) => {
    // Create synthetic error info for manual reporting
    const errorInfo: ErrorInfo = {
      error,
      errorInfo: {
        componentStack: 'Manual error report'
      } as React.ErrorInfo,
      timestamp: Date.now(),
      componentStack: 'Manual error report',
      errorBoundary: 'manual-report',
      url: window.location.href,
      userAgent: navigator.userAgent,
      additionalContext
    };

    // Report to logging service
    console.error('Manual error report:', errorInfo);

    // Send to monitoring service
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      (window as any).Sentry.captureException(error, {
        extra: additionalContext,
        tags: {
          manual: true
        }
      });
    }
  }, []);

  return { reportError };
}

/**
 * Error boundary for specific coordination operations
 */
export function CoordinationErrorBoundary({ children }: { children: ReactNode }) {
  const handleError = (errorInfo: ErrorInfo) => {
    // Specific handling for coordination errors
    console.error('Coordination error:', errorInfo);
    
    // You might want to reset coordination state here
    // or trigger specific recovery actions
  };

  return (
    <ErrorBoundary
      level="section"
      errorBoundaryId="coordination-boundary"
      onError={handleError}
      enableRetry={true}
      maxRetries={2}
      reportErrors={true}
      showErrorDetails={process.env.NODE_ENV === 'development'}
      fallback={(error, errorInfo, retry) => (
        <Alert 
          severity="error" 
          action={
            <Button color="inherit" size="small" onClick={retry}>
              Retry Coordination
            </Button>
          }
        >
          Coordination system error: {error.message}
        </Alert>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

/**
 * Error boundary for planning operations
 */
export function PlanningErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      level="section"
      errorBoundaryId="planning-boundary"
      enableRetry={true}
      maxRetries={3}
      retryDelay={2000}
      reportErrors={true}
      fallback={(error, errorInfo, retry) => (
        <Box textAlign="center" p={4}>
          <ErrorIcon color="error" sx={{ fontSize: 48, mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Planning System Error
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            {error.message}
          </Typography>
          <Button variant="contained" onClick={retry} startIcon={<Refresh />}>
            Restart Planning
          </Button>
        </Box>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}