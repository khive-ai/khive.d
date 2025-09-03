/**
 * Card component for layout and content grouping
 * Built with Material-UI with custom styling
 */

import * as React from "react";
import {
  Card as MuiCard,
  CardActions as MuiCardActions,
  CardContent as MuiCardContent,
  CardHeader as MuiCardHeader,
  CardProps as MuiCardProps,
  Typography,
} from "@mui/material";
import { styled } from "@mui/material/styles";
import { cn } from "@/lib/utils";

export interface CardProps extends MuiCardProps {
  variant?: "default" | "outlined" | "elevated";
}

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
}

export interface CardContentProps
  extends React.HTMLAttributes<HTMLDivElement> {}

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

const StyledCard = styled(MuiCard)<CardProps>(({ theme, variant }) => ({
  borderRadius: theme.spacing(1.5),

  ...(variant === "default" && {
    boxShadow: "none",
    border: `1px solid ${theme.palette.divider}`,
  }),

  ...(variant === "outlined" && {
    boxShadow: "none",
    border: `2px solid ${theme.palette.divider}`,
  }),

  ...(variant === "elevated" && {
    border: "none",
    boxShadow: theme.shadows[4],
  }),
}));

const StyledCardHeader = styled("div")(({ theme }) => ({
  padding: theme.spacing(3, 3, 0, 3),
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
}));

const StyledCardContent = styled(MuiCardContent)(({ theme }) => ({
  padding: theme.spacing(3),
  "&:last-child": {
    paddingBottom: theme.spacing(3),
  },
}));

const StyledCardFooter = styled("div")(({ theme }) => ({
  padding: theme.spacing(0, 3, 3, 3),
  display: "flex",
  alignItems: "center",
  gap: theme.spacing(2),
}));

const HeaderContent = styled("div")({
  display: "flex",
  flexDirection: "column",
  gap: 4,
  flex: 1,
});

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = "default", ...props }, ref) => (
    <StyledCard
      ref={ref}
      className={cn(className)}
      variant={variant}
      {...props}
    />
  ),
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, title, subtitle, action, ...props }, ref) => (
    <StyledCardHeader ref={ref} className={cn(className)} {...props}>
      <HeaderContent>
        {title && (
          <Typography variant="h6" component="h3" fontWeight={600}>
            {title}
          </Typography>
        )}
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </HeaderContent>
      {action && <div>{action}</div>}
    </StyledCardHeader>
  ),
);
CardHeader.displayName = "CardHeader";

export const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, ...props }, ref) => (
    <StyledCardContent ref={ref} className={cn(className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, ...props }, ref) => (
    <StyledCardFooter ref={ref} className={cn(className)} {...props} />
  ),
);
CardFooter.displayName = "CardFooter";
