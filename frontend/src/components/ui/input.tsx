/**
 * Input component with various styles and validation states
 */

import * as React from "react";
import { InputAdornment, TextField, TextFieldProps } from "@mui/material";
import { styled } from "@mui/material/styles";
import { cn } from "@/lib/utils";

export interface InputProps extends Omit<TextFieldProps, "variant" | "size"> {
  variant?: "default" | "filled" | "ghost";
  size?: "sm" | "default" | "lg";
  startIcon?: React.ReactNode;
  endIcon?: React.ReactNode;
}

const StyledTextField = styled(TextField)<InputProps>((
  { theme, variant, size },
) => ({
  "& .MuiInputBase-root": {
    borderRadius: theme.spacing(1),
    transition: "all 0.2s ease-in-out",

    // Size styles
    ...(size === "sm" && {
      height: 36,
      fontSize: "0.875rem",
    }),

    ...(size === "default" && {
      height: 44,
      fontSize: "1rem",
    }),

    ...(size === "lg" && {
      height: 52,
      fontSize: "1.125rem",
    }),
  },

  "& .MuiInputBase-input": {
    padding: theme.spacing(1, 1.5),
  },

  // Variant styles
  ...(variant === "default" && {
    "& .MuiOutlinedInput-root": {
      backgroundColor: theme.palette.background.paper,
      "& fieldset": {
        borderColor: theme.palette.divider,
      },
      "&:hover fieldset": {
        borderColor: theme.palette.primary.main,
      },
      "&.Mui-focused fieldset": {
        borderColor: theme.palette.primary.main,
        borderWidth: 2,
      },
    },
  }),

  ...(variant === "filled" && {
    "& .MuiFilledInput-root": {
      backgroundColor: theme.palette.grey[50],
      border: `1px solid ${theme.palette.divider}`,
      borderRadius: theme.spacing(1),
      "&:hover": {
        backgroundColor: theme.palette.grey[100],
        borderColor: theme.palette.primary.main,
      },
      "&.Mui-focused": {
        backgroundColor: theme.palette.background.paper,
        borderColor: theme.palette.primary.main,
        borderWidth: 2,
      },
      "&:before, &:after": {
        display: "none",
      },
    },
  }),

  ...(variant === "ghost" && {
    "& .MuiOutlinedInput-root": {
      backgroundColor: "transparent",
      "& fieldset": {
        border: "none",
      },
      "&:hover": {
        backgroundColor: theme.palette.action.hover,
      },
      "&.Mui-focused": {
        backgroundColor: theme.palette.background.paper,
        boxShadow: `0 0 0 2px ${theme.palette.primary.main}`,
      },
    },
  }),
}));

export const Input = React.forwardRef<HTMLDivElement, InputProps>(
  ({
    className,
    variant = "default",
    size = "default",
    startIcon,
    endIcon,
    ...props
  }, ref) => {
    const InputProps = {
      ...(startIcon && {
        startAdornment: (
          <InputAdornment position="start">
            {startIcon}
          </InputAdornment>
        ),
      }),
      ...(endIcon && {
        endAdornment: (
          <InputAdornment position="end">
            {endIcon}
          </InputAdornment>
        ),
      }),
    };

    return (
      <StyledTextField
        ref={ref}
        className={cn(className)}
        variant={variant === "filled" ? "filled" : "outlined"}
        size={size}
        InputProps={InputProps}
        {...props}
      />
    );
  },
);

Input.displayName = "Input";
