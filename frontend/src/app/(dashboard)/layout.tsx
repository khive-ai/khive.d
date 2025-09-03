/**
 * Dashboard Layout - Provides navigation and consistent structure
 * Includes sidebar navigation, header with actions, and main content area
 */

"use client";

import { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  alpha,
  AppBar,
  Avatar,
  Badge,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import {
  AccountCircle as AccountIcon,
  AccountTree as TaskFlowIcon,
  Analytics as ObservabilityIcon,
  AutoAwesome as StudioIcon,
  Close as CloseIcon,
  ControlPoint as OrchestrationIcon,
  Dashboard as DashboardIcon,
  Folder as SessionIcon,
  Help as HelpIcon,
  Logout as LogoutIcon,
  Menu as MenuIcon,
  Notifications as NotificationIcon,
  Psychology as AgentIcon,
  Settings as SettingsIcon,
  Timeline as MetricsIcon,
} from "@mui/icons-material";

const drawerWidth = 260;

interface NavigationItem {
  label: string;
  path: string;
  icon: React.ReactNode;
  badge?: number;
  disabled?: boolean;
}

const navigationItems: NavigationItem[] = [
  {
    label: "Overview",
    path: "/dashboard",
    icon: <DashboardIcon />,
  },
  {
    label: "Composer Studio",
    path: "/dashboard/studio",
    icon: <StudioIcon />,
  },
  {
    label: "Orchestration",
    path: "/dashboard/orchestration",
    icon: <OrchestrationIcon />,
  },
  {
    label: "Sessions",
    path: "/dashboard/sessions",
    icon: <SessionIcon />,
  },
  {
    label: "Agents",
    path: "/dashboard/agents",
    icon: <AgentIcon />,
  },
  {
    label: "Coordination",
    path: "/dashboard/coordination",
    icon: <MetricsIcon />,
  },
  {
    label: "Task Flow",
    path: "/dashboard/task-flow",
    icon: <TaskFlowIcon />,
  },
  {
    label: "Observability",
    path: "/dashboard/observability",
    icon: <ObservabilityIcon />,
  },
  {
    label: "Plans",
    path: "/dashboard/plans",
    icon: <MetricsIcon />,
  },
  {
    label: "Settings",
    path: "/dashboard/settings",
    icon: <SettingsIcon />,
  },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const theme = useTheme();
  const router = useRouter();
  const pathname = usePathname();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(
    null,
  );

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUserMenuAnchor(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
  };

  const handleNavigate = (path: string) => {
    router.push(path);
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const drawer = (
    <Box>
      {/* Logo/Brand Area */}
      <Box
        sx={{
          p: 2,
          display: "flex",
          alignItems: "center",
          minHeight: 64,
          bgcolor: alpha(theme.palette.primary.main, 0.08),
        }}
      >
        <Typography
          variant="h6"
          sx={{
            fontWeight: 700,
            background:
              `linear-gradient(45deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Khive Dashboard
        </Typography>
      </Box>

      <Divider />

      {/* Navigation Items */}
      <List sx={{ px: 1 }}>
        {navigationItems.map((item) => {
          const isActive = pathname === item.path;

          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton
                onClick={() => handleNavigate(item.path)}
                disabled={item.disabled}
                sx={{
                  borderRadius: 2,
                  mb: 0.5,
                  mx: 1,
                  bgcolor: isActive
                    ? alpha(theme.palette.primary.main, 0.12)
                    : "transparent",
                  color: isActive
                    ? theme.palette.primary.main
                    : theme.palette.text.primary,
                  "&:hover": {
                    bgcolor: isActive
                      ? alpha(theme.palette.primary.main, 0.16)
                      : alpha(theme.palette.action.hover, 0.08),
                  },
                  "&.Mui-disabled": {
                    opacity: 0.6,
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    color: "inherit",
                    minWidth: 40,
                  }}
                >
                  {item.badge
                    ? (
                      <Badge badgeContent={item.badge} color="error">
                        {item.icon}
                      </Badge>
                    )
                    : (
                      item.icon
                    )}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    fontWeight: isActive ? 600 : 400,
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>

      {/* Status Section */}
      <Box sx={{ position: "absolute", bottom: 16, left: 16, right: 16 }}>
        <Divider sx={{ mb: 2 }} />
        <Box
          sx={{
            p: 2,
            borderRadius: 2,
            bgcolor: alpha(theme.palette.success.main, 0.08),
            border: `1px solid ${alpha(theme.palette.success.main, 0.2)}`,
          }}
        >
          <Typography
            variant="caption"
            color="success.main"
            sx={{ fontWeight: 600 }}
          >
            System Status
          </Typography>
          <Typography variant="body2" color="text.secondary">
            All systems operational
          </Typography>
        </Box>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex" }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          bgcolor: "background.paper",
          color: "text.primary",
          boxShadow: `0 1px 3px ${alpha(theme.palette.common.black, 0.12)}`,
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: "none" } }}
          >
            <MenuIcon />
          </IconButton>

          {/* Dynamic page title */}
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {navigationItems.find((item) => item.path === pathname)?.label ||
              "Dashboard"}
          </Typography>

          {/* Header Actions */}
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Tooltip title="Notifications">
              <IconButton color="inherit">
                <Badge badgeContent={3} color="error">
                  <NotificationIcon />
                </Badge>
              </IconButton>
            </Tooltip>

            <Tooltip title="Help">
              <IconButton color="inherit">
                <HelpIcon />
              </IconButton>
            </Tooltip>

            <Tooltip title="User Menu">
              <IconButton
                color="inherit"
                onClick={handleUserMenuOpen}
                sx={{ ml: 1 }}
              >
                <Avatar sx={{ width: 32, height: 32 }}>
                  <AccountIcon />
                </Avatar>
              </IconButton>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      {/* User Menu */}
      <Menu
        anchorEl={userMenuAnchor}
        open={Boolean(userMenuAnchor)}
        onClose={handleUserMenuClose}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
      >
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <AccountIcon />
          </ListItemIcon>
          Profile
        </MenuItem>
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <SettingsIcon />
          </ListItemIcon>
          Settings
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleUserMenuClose}>
          <ListItemIcon>
            <LogoutIcon />
          </ListItemIcon>
          Logout
        </MenuItem>
      </Menu>

      {/* Navigation Drawer */}
      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile.
          }}
          sx={{
            display: { xs: "block", md: "none" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: drawerWidth,
            },
          }}
        >
          {/* Close button for mobile */}
          <Box sx={{ display: "flex", justifyContent: "flex-end", p: 1 }}>
            <IconButton onClick={handleDrawerToggle}>
              <CloseIcon />
            </IconButton>
          </Box>
          {drawer}
        </Drawer>

        {/* Desktop drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: "none", md: "block" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: drawerWidth,
              border: "none",
              boxShadow: `1px 0 3px ${alpha(theme.palette.common.black, 0.12)}`,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          minHeight: "100vh",
          bgcolor: alpha(theme.palette.grey[50], 0.4),
        }}
      >
        <Toolbar /> {/* Spacer for AppBar */}
        {children}
      </Box>
    </Box>
  );
}
