/**
 * Alerts Panel Component
 * Displays system alerts and performance warnings
 */

import React, { useState } from "react";
import {
  Alert,
  AlertTitle,
  alpha,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  IconButton,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import {
  CheckCircle as SuccessIcon,
  Close as CloseIcon,
  Error as ErrorIcon,
  ExpandLess as ExpandLessIcon,
  ExpandMore as ExpandMoreIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  Warning as WarningIcon,
} from "@mui/icons-material";

interface AlertItem {
  id: string;
  type: "error" | "warning" | "info" | "success";
  title: string;
  message: string;
  timestamp: string;
  dismissed?: boolean;
}

interface AlertsPanelProps {
  alerts: AlertItem[];
  onDismiss?: (alertId: string) => void;
  onRefresh?: () => void;
}

const getAlertIcon = (type: string) => {
  switch (type) {
    case "error":
      return <ErrorIcon />;
    case "warning":
      return <WarningIcon />;
    case "info":
      return <InfoIcon />;
    case "success":
      return <SuccessIcon />;
    default:
      return <InfoIcon />;
  }
};

const getAlertColor = (type: string) => {
  switch (type) {
    case "error":
      return "error";
    case "warning":
      return "warning";
    case "info":
      return "info";
    case "success":
      return "success";
    default:
      return "info";
  }
};

export const AlertsPanel: React.FC<AlertsPanelProps> = ({
  alerts,
  onDismiss,
  onRefresh,
}) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(true);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(
    new Set(),
  );

  const visibleAlerts = alerts.filter((alert) =>
    !dismissedAlerts.has(alert.id)
  );

  const handleDismiss = (alertId: string) => {
    setDismissedAlerts((prev) => new Set([...prev, alertId]));
    onDismiss?.(alertId);
  };

  const handleDismissAll = () => {
    setDismissedAlerts(new Set(alerts.map((alert) => alert.id)));
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  if (visibleAlerts.length === 0) {
    return null;
  }

  const criticalAlerts =
    visibleAlerts.filter((alert) => alert.type === "error").length;
  const warningAlerts =
    visibleAlerts.filter((alert) => alert.type === "warning").length;

  return (
    <Card
      sx={{
        border: `1px solid ${alpha(theme.palette.error.main, 0.3)}`,
        background: `linear-gradient(135deg, ${
          alpha(theme.palette.error.main, 0.05)
        }, ${alpha(theme.palette.warning.main, 0.03)})`,
      }}
    >
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            mb: 2,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <WarningIcon sx={{ color: "warning.main" }} />
            <Typography variant="h6" fontWeight={600}>
              System Alerts
            </Typography>
            <Chip
              label={`${visibleAlerts.length} active`}
              size="small"
              color={criticalAlerts > 0 ? "error" : "warning"}
              variant="outlined"
            />
          </Box>

          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            {onRefresh && (
              <IconButton size="small" onClick={onRefresh}>
                <RefreshIcon fontSize="small" />
              </IconButton>
            )}
            <Button
              size="small"
              variant="outlined"
              onClick={handleDismissAll}
              sx={{ minWidth: "auto" }}
            >
              Dismiss All
            </Button>
            <IconButton
              size="small"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        </Box>

        {/* Summary */}
        <Box sx={{ mb: 2 }}>
          <Stack direction="row" spacing={2}>
            {criticalAlerts > 0 && (
              <Chip
                icon={<ErrorIcon />}
                label={`${criticalAlerts} Critical`}
                size="small"
                color="error"
              />
            )}
            {warningAlerts > 0 && (
              <Chip
                icon={<WarningIcon />}
                label={`${warningAlerts} Warning`}
                size="small"
                color="warning"
              />
            )}
          </Stack>
        </Box>

        {/* Alerts List */}
        <Collapse in={expanded}>
          <Stack spacing={2}>
            {visibleAlerts.map((alert) => (
              <Alert
                key={alert.id}
                severity={getAlertColor(alert.type) as any}
                action={
                  <IconButton
                    size="small"
                    onClick={() => handleDismiss(alert.id)}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                }
                sx={{
                  "& .MuiAlert-message": {
                    width: "100%",
                  },
                }}
              >
                <AlertTitle sx={{ fontWeight: 600 }}>
                  {alert.title}
                </AlertTitle>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <Typography variant="body2">
                    {alert.message}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ ml: 2, flexShrink: 0 }}
                  >
                    {formatTimestamp(alert.timestamp)}
                  </Typography>
                </Box>
              </Alert>
            ))}
          </Stack>
        </Collapse>

        {/* Footer */}
        {expanded && visibleAlerts.length > 0 && (
          <Box
            sx={{
              mt: 2,
              pt: 2,
              borderTop: `1px solid ${theme.palette.divider}`,
            }}
          >
            <Typography variant="caption" color="text.secondary">
              Alerts are automatically refreshed every 30 seconds
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};
