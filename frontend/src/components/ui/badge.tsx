/**
 * Badge component for status indicators and labels
 */

import * as React from 'react';
import { Chip, ChipProps } from '@mui/material';
import { styled } from '@mui/material/styles';
import { cn } from '@/utils';

export interface BadgeProps extends Omit<ChipProps, 'variant'> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning' | 'info';
  size?: 'sm' | 'default' | 'lg';
}

const StyledChip = styled(Chip)<BadgeProps>(({ theme, variant, size }) => ({
  fontWeight: 500,
  borderRadius: theme.spacing(1),
  
  // Size styles
  ...(size === 'sm' && {
    height: 20,
    fontSize: '0.75rem',
    padding: theme.spacing(0, 1),
    '& .MuiChip-label': {
      padding: theme.spacing(0, 0.5),
    },
  }),
  
  ...(size === 'default' && {
    height: 24,
    fontSize: '0.875rem',
    padding: theme.spacing(0, 1.5),
    '& .MuiChip-label': {
      padding: theme.spacing(0, 1),
    },
  }),
  
  ...(size === 'lg' && {
    height: 32,
    fontSize: '1rem',
    padding: theme.spacing(0, 2),
    '& .MuiChip-label': {
      padding: theme.spacing(0, 1.5),
    },
  }),
  
  // Variant styles
  ...(variant === 'default' && {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
  }),
  
  ...(variant === 'secondary' && {
    backgroundColor: theme.palette.grey[100],
    color: theme.palette.text.primary,
    border: `1px solid ${theme.palette.grey[300]}`,
  }),
  
  ...(variant === 'destructive' && {
    backgroundColor: theme.palette.error.main,
    color: theme.palette.error.contrastText,
  }),
  
  ...(variant === 'outline' && {
    backgroundColor: 'transparent',
    color: theme.palette.text.primary,
    border: `1px solid ${theme.palette.divider}`,
  }),
  
  ...(variant === 'success' && {
    backgroundColor: theme.palette.success.main,
    color: theme.palette.success.contrastText,
  }),
  
  ...(variant === 'warning' && {
    backgroundColor: theme.palette.warning.main,
    color: theme.palette.warning.contrastText,
  }),
  
  ...(variant === 'info' && {
    backgroundColor: theme.palette.info.main,
    color: theme.palette.info.contrastText,
  }),
}));

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    return (
      <StyledChip
        ref={ref}
        className={cn(className)}
        variant={variant}
        size={size}
        {...props}
      />
    );
  }
);

Badge.displayName = 'Badge';

// Status-specific badge variants for common use cases
export const StatusBadge: React.FC<{ 
  status: 'active' | 'idle' | 'error' | 'running' | 'completed' | 'failed' | 'pending';
  children?: React.ReactNode;
  [key: string]: any;
}> = ({ status, children, ...props }) => {
  const getVariant = (status: string) => {
    switch (status) {
      case 'active':
      case 'running':
        return 'success';
      case 'idle':
      case 'pending':
        return 'warning';
      case 'error':
      case 'failed':
        return 'destructive';
      case 'completed':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Badge 
      variant={getVariant(status) as any}
      label={children || status}
      {...props}
    />
  );
};