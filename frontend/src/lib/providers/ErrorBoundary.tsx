"use client";

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { ErrorOutline as ErrorIcon, Refresh as RefreshIcon } from '@mui/icons-material';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('KHIVE Command Center Error:', error, errorInfo);
    this.setState({
      hasError: true,
      error,
      errorInfo,
    });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  public override render() {
    if (this.state.hasError) {
      return (
        <Box sx={{
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          bgcolor: 'background.default',
          p: 3
        }}>
          <Paper sx={{
            p: 4,
            maxWidth: 600,
            width: '100%',
            textAlign: 'center',
            border: '1px solid',
            borderColor: 'error.main'
          }}>
            <ErrorIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
            
            <Typography variant="h5" gutterBottom>
              KHIVE Command Center Error
            </Typography>
            
            <Typography variant="body2" color="text.secondary" paragraph>
              The command center has encountered an unexpected error. This may be due to a 
              WebSocket connection issue or a component rendering problem.
            </Typography>

            {this.state.error && (
              <Paper sx={{
                p: 2,
                mb: 3,
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider',
                textAlign: 'left'
              }}>
                <Typography variant="subtitle2" color="error.main" gutterBottom>
                  Error Details:
                </Typography>
                <Typography 
                  variant="caption" 
                  component="pre" 
                  sx={{ 
                    fontFamily: 'monospace',
                    fontSize: '0.7rem',
                    wordBreak: 'break-word',
                    whiteSpace: 'pre-wrap',
                    color: 'text.secondary'
                  }}
                >
                  {this.state.error.message}
                  {this.state.errorInfo && `\n\nStack trace:\n${this.state.errorInfo.componentStack}`}
                </Typography>
              </Paper>
            )}

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
              <Button
                variant="outlined"
                onClick={this.handleReset}
                startIcon={<RefreshIcon />}
              >
                Try Again
              </Button>
              <Button
                variant="contained"
                onClick={this.handleReload}
                color="primary"
              >
                Reload Application
              </Button>
            </Box>

            <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
              If this error persists, check the browser console for more details or 
              restart the KHIVE daemon connection.
            </Typography>
          </Paper>
        </Box>
      );
    }

    return this.props.children;
  }
}