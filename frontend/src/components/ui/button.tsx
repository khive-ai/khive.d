/**
 * Button component with multiple variants and sizes
 * Built with Material-UI but enhanced with our design system
 */

import * as React from 'react';
import { Button as MuiButton, ButtonProps as MuiButtonProps, CircularProgress } from '@mui/material';
import { styled } from '@mui/material/styles';
import { cn } from '@/utils';

export interface ButtonProps extends Omit<MuiButtonProps, 'variant' | 'size'> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
  loading?: boolean;
  asChild?: boolean;
}

const StyledButton = styled(MuiButton)<ButtonProps>(({ theme, variant, size }) => ({
  textTransform: 'none',
  fontWeight: 500,
  borderRadius: theme.spacing(1),
  transition: 'all 0.2s ease-in-out',
  
  // Variant styles
  ...(variant === 'default' && {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
    '&:hover': {
      backgroundColor: theme.palette.primary.dark,
    },
  }),
  
  ...(variant === 'destructive' && {
    backgroundColor: theme.palette.error.main,
    color: theme.palette.error.contrastText,
    '&:hover': {
      backgroundColor: theme.palette.error.dark,
    },
  }),
  
  ...(variant === 'outline' && {
    backgroundColor: 'transparent',
    color: theme.palette.text.primary,
    border: `1px solid ${theme.palette.divider}`,
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
    },
  }),
  
  ...(variant === 'secondary' && {
    backgroundColor: theme.palette.grey[100],
    color: theme.palette.text.primary,
    '&:hover': {
      backgroundColor: theme.palette.grey[200],
    },
  }),
  
  ...(variant === 'ghost' && {
    backgroundColor: 'transparent',
    color: theme.palette.text.primary,
    '&:hover': {
      backgroundColor: theme.palette.action.hover,
    },
  }),
  
  ...(variant === 'link' && {
    backgroundColor: 'transparent',
    color: theme.palette.primary.main,
    textDecoration: 'underline',
    '&:hover': {
      textDecoration: 'none',
    },
  }),
  
  // Size styles
  ...(size === 'sm' && {
    height: 32,
    padding: theme.spacing(0, 2),
    fontSize: '0.875rem',
  }),
  
  ...(size === 'default' && {
    height: 40,
    padding: theme.spacing(0, 3),
    fontSize: '1rem',
  }),
  
  ...(size === 'lg' && {
    height: 48,
    padding: theme.spacing(0, 4),
    fontSize: '1.125rem',
  }),
  
  ...(size === 'icon' && {
    height: 40,
    width: 40,
    padding: 0,
    minWidth: 40,
  }),
}));

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    className, 
    variant = 'default', 
    size = 'default', 
    loading = false,
    disabled,
    children,
    ...props 
  }, ref) => {
    return (
      <StyledButton
        ref={ref}
        className={cn(className)}
        variant={variant}
        size={size}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <CircularProgress 
            size={size === 'sm' ? 16 : size === 'lg' ? 24 : 20} 
            sx={{ mr: 1 }}
          />
        )}
        {children}
      </StyledButton>
    );
  }
);

Button.displayName = 'Button';