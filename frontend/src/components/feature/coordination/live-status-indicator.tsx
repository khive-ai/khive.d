/**
 * Live Status Indicator Component
 * Shows real-time connection status and last update time for coordination monitoring
 */

import React, { useEffect, useState } from "react";
import {
  alpha,
  Box,
  Chip,
  Divider,
  IconButton,
  Popover,
  Stack,
  Tooltip,
  Typography,
  useTheme,
} from "@mui/material";
import {
  Circle as CircleIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  Schedule as TimeIcon,
  Wifi as ConnectedIcon,
  WifiOff as DisconnectedIcon,
} from "@mui/icons-material";
import { formatDistanceToNow } from "date-fns";

export interface LiveStatusIndicatorProps {
  isLive: boolean;
  lastUpdate: Date;
  connectionStatus?: "connected" | "disconnected" | "reconnecting";
  refreshRate?: number;
  onRefresh?: () => void;
  className?: string;
}

export const LiveStatusIndicator: React.FC<LiveStatusIndicatorProps> = ({
  isLive,
  lastUpdate,
  connectionStatus = "connected",
  refreshRate = 2000,
  onRefresh,
  className,
}) => {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update current time every second for relative time display
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const getStatusColor = () => {
    if (!isLive) return "default";

    switch (connectionStatus) {
      case "connected":
        return "success";
      case "disconnected":
        return "error";
      case "reconnecting":
        return "warning";
      default:
        return "default";
    }
  };

  const getStatusIcon = () => {
    if (!isLive) {
      return <CircleIcon sx={{ fontSize: 12, color: "grey.500" }} />;
    }

    switch (connectionStatus) {
      case "connected":
        return <CircleIcon sx={{ fontSize: 12, color: "success.main" }} />;
      case "disconnected":
        return <DisconnectedIcon sx={{ fontSize: 14, color: "error.main" }} />;
      case "reconnecting":
        return (
          <CircleIcon
            sx={{
              fontSize: 12,
              color: "warning.main",
              animation: "pulse 1.5s ease-in-out infinite",
              "@keyframes pulse": {
                "0%": { opacity: 1 },
                "50%": { opacity: 0.5 },
                "100%": { opacity: 1 },
              },
            }}
          />
        );
      default:
        return <CircleIcon sx={{ fontSize: 12, color: "grey.500" }} />;
    }
  };

  const getStatusText = () => {
    if (!isLive) return "Offline";

    switch (connectionStatus) {
      case "connected":
        return "Live";
      case "disconnected":
        return "Disconnected";
      case "reconnecting":
        return "Reconnecting";
      default:
        return "Unknown";
    }
  };

  const getUpdateStatus = () => {
    const timeDiff = currentTime.getTime() - lastUpdate.getTime();
    const secondsAgo = Math.floor(timeDiff / 1000);

    if (secondsAgo < 5) return "just updated";
    if (secondsAgo < 30) return `${secondsAgo}s ago`;
    if (secondsAgo < 300) return `${Math.floor(secondsAgo / 60)}m ago`;
    return "stale data";
  };

  const isStale = () => {
    const timeDiff = currentTime.getTime() - lastUpdate.getTime();
    return timeDiff > 60000; // More than 1 minute
  };

  const open = Boolean(anchorEl);

  return (
    <Box className={className}>
      <Stack direction="row" spacing={1} alignItems="center">
        {/* Main Status Chip */}
        <Chip
          icon={getStatusIcon()}
          label={getStatusText()}
          color={getStatusColor() as any}
          size="small"
          variant={isLive ? "filled" : "outlined"}
          sx={{
            fontWeight: 600,
            cursor: "pointer",
            transition: "all 0.2s ease-in-out",
            "&:hover": {
              transform: "scale(1.02)",
            },
          }}
          onClick={handleClick}
        />

        {/* Update Status */}
        <Typography
          variant="caption"
          color={isStale() ? "error.main" : "text.secondary"}
          sx={{
            display: { xs: "none", sm: "inline" },
            fontWeight: isStale() ? 600 : 400,
          }}
        >
          {getUpdateStatus()}
        </Typography>

        {/* Manual Refresh Button */}
        {onRefresh && (
          <Tooltip title="Manual Refresh">
            <IconButton
              size="small"
              onClick={onRefresh}
              sx={{
                width: 24,
                height: 24,
                color: "text.secondary",
                "&:hover": {
                  color: "primary.main",
                },
              }}
            >
              <RefreshIcon sx={{ fontSize: 14 }} />
            </IconButton>
          </Tooltip>
        )}
      </Stack>

      {/* Status Details Popover */}
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
        PaperProps={{
          sx: {
            p: 2,
            minWidth: 280,
            maxWidth: 320,
          },
        }}
      >
        <Box>
          {/* Status Header */}
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            {getStatusIcon()}
            <Typography variant="subtitle2" fontWeight="bold">
              Connection Status
            </Typography>
          </Box>

          <Stack spacing={2}>
            {/* Live Status */}
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
            >
              <Typography variant="body2" color="text.secondary">
                Real-time monitoring
              </Typography>
              <Chip
                label={isLive ? "Enabled" : "Disabled"}
                color={isLive ? "success" : "default"}
                size="small"
                variant="outlined"
              />
            </Box>

            {/* Connection Status */}
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
            >
              <Typography variant="body2" color="text.secondary">
                Connection
              </Typography>
              <Box display="flex" alignItems="center" gap={1}>
                {connectionStatus === "connected"
                  ? (
                    <ConnectedIcon
                      sx={{ fontSize: 16, color: "success.main" }}
                    />
                  )
                  : (
                    <DisconnectedIcon
                      sx={{ fontSize: 16, color: "error.main" }}
                    />
                  )}
                <Typography variant="body2" fontWeight="medium">
                  {connectionStatus}
                </Typography>
              </Box>
            </Box>

            <Divider />

            {/* Update Information */}
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Last Update
              </Typography>
              <Box display="flex" alignItems="center" gap={1}>
                <TimeIcon sx={{ fontSize: 16, color: "text.secondary" }} />
                <Typography variant="body2" fontWeight="medium">
                  {lastUpdate.toLocaleTimeString()}
                </Typography>
              </Box>
              <Typography variant="caption" color="text.secondary">
                {formatDistanceToNow(lastUpdate, { addSuffix: true })}
              </Typography>
            </Box>

            {/* Refresh Rate */}
            {isLive && (
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography variant="body2" color="text.secondary">
                  Refresh Rate
                </Typography>
                <Typography variant="body2" fontWeight="medium">
                  {refreshRate / 1000}s
                </Typography>
              </Box>
            )}

            {/* Status Warnings */}
            {isStale() && (
              <Box
                sx={{
                  p: 1.5,
                  backgroundColor: alpha(theme.palette.warning.main, 0.1),
                  border: `1px solid ${alpha(theme.palette.warning.main, 0.2)}`,
                  borderRadius: 1,
                }}
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <InfoIcon sx={{ fontSize: 16, color: "warning.main" }} />
                  <Typography
                    variant="caption"
                    color="warning.dark"
                    fontWeight="medium"
                  >
                    Data may be stale
                  </Typography>
                </Box>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                  mt={0.5}
                >
                  Last update was more than 1 minute ago
                </Typography>
              </Box>
            )}

            {connectionStatus === "disconnected" && (
              <Box
                sx={{
                  p: 1.5,
                  backgroundColor: alpha(theme.palette.error.main, 0.1),
                  border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
                  borderRadius: 1,
                }}
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <InfoIcon sx={{ fontSize: 16, color: "error.main" }} />
                  <Typography
                    variant="caption"
                    color="error.dark"
                    fontWeight="medium"
                  >
                    Connection lost
                  </Typography>
                </Box>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                  mt={0.5}
                >
                  Real-time updates are not available
                </Typography>
              </Box>
            )}
          </Stack>
        </Box>
      </Popover>
    </Box>
  );
};
