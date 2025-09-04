/**
 * Responsive Design Enhancements for Professional Workspace
 * 
 * This file demonstrates the fixes needed to resolve mobile/tablet issues
 * identified in performance testing.
 * 
 * Key Improvements:
 * 1. Mobile drawer navigation for left panel
 * 2. Collapsible right panel on smaller screens
 * 3. Proper viewport-based layout adaptation
 * 4. Touch-optimized interactions
 */

import { useState, useEffect } from 'react';
import {
  Box,
  Drawer,
  IconButton,
  Fab,
  useTheme,
  useMediaQuery,
  Collapse,
  Slide
} from '@mui/material';
import {
  Menu as MenuIcon,
  Close as CloseIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon
} from '@mui/icons-material';

export interface ResponsiveLayoutProps {
  leftPanel: React.ReactNode;
  centerPanel: React.ReactNode;
  rightPanel: React.ReactNode;
}

/**
 * Enhanced Responsive Layout Component
 * 
 * Adapts 3-panel layout for different screen sizes:
 * - Desktop (>1024px): Full 3-panel layout
 * - Tablet (768-1024px): Flexible panels with collapse option
 * - Mobile (<768px): Drawer navigation + floating actions
 */
export function ResponsiveProfessionalWorkspace({
  leftPanel,
  centerPanel,
  rightPanel
}: ResponsiveLayoutProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md')); // <768px
  const isTablet = useMediaQuery(theme.breakpoints.between('md', 'lg')); // 768-1024px
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg')); // >1024px

  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false);

  // Auto-collapse right panel on tablet for better space usage
  useEffect(() => {
    if (isTablet && !rightPanelCollapsed) {
      setRightPanelCollapsed(true);
    }
    if (isDesktop && rightPanelCollapsed) {
      setRightPanelCollapsed(false);
    }
  }, [isTablet, isDesktop, rightPanelCollapsed]);

  // Mobile Layout (Drawer Navigation)
  if (isMobile) {
    return (
      <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        {/* Mobile Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            p: 2,
            borderBottom: `1px solid ${theme.palette.divider}`,
            backgroundColor: 'white',
            zIndex: 1100
          }}
        >
          <IconButton
            onClick={() => setMobileDrawerOpen(true)}
            data-testid="mobile-menu-button"
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1, textAlign: 'center' }}>
            <span style={{ fontWeight: 600 }}>KHIVE Workspace</span>
          </Box>
        </Box>

        {/* Mobile Main Content */}
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          {centerPanel}
        </Box>

        {/* Mobile Left Panel Drawer */}
        <Drawer
          anchor="left"
          open={mobileDrawerOpen}
          onClose={() => setMobileDrawerOpen(false)}
          data-testid="mobile-drawer"
          sx={{
            '& .MuiDrawer-paper': {
              width: 320,
              maxWidth: '85vw'
            }
          }}
        >
          <Box sx={{ p: 1, display: 'flex', justifyContent: 'flex-end' }}>
            <IconButton onClick={() => setMobileDrawerOpen(false)}>
              <CloseIcon />
            </IconButton>
          </Box>
          {leftPanel}
        </Drawer>

        {/* Mobile Right Panel as Bottom Sheet */}
        <Slide direction="up" in={!rightPanelCollapsed}>
          <Box
            sx={{
              position: 'fixed',
              bottom: 0,
              left: 0,
              right: 0,
              backgroundColor: 'white',
              borderTop: `1px solid ${theme.palette.divider}`,
              maxHeight: '50vh',
              overflowY: 'auto',
              zIndex: 1200
            }}
          >
            <Box
              sx={{
                p: 1,
                display: 'flex',
                justifyContent: 'center',
                borderBottom: `1px solid ${theme.palette.divider}`
              }}
            >
              <IconButton
                onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
                data-testid="mobile-actions-toggle"
              >
                {rightPanelCollapsed ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            {rightPanel}
          </Box>
        </Slide>

        {/* Floating Action Button for Actions */}
        <Fab
          color="primary"
          onClick={() => setRightPanelCollapsed(false)}
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            zIndex: 1300,
            display: rightPanelCollapsed ? 'flex' : 'none'
          }}
          data-testid="mobile-fab-actions"
        >
          <MenuIcon />
        </Fab>
      </Box>
    );
  }

  // Tablet Layout (Collapsible Panels)
  if (isTablet) {
    return (
      <Box sx={{ height: '100vh', display: 'flex' }}>
        {/* Tablet Left Panel */}
        <Box
          data-testid="tablet-left-panel"
          sx={{
            width: 280, // Slightly smaller for tablet
            borderRight: `1px solid ${theme.palette.divider}`,
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: 'white'
          }}
        >
          {leftPanel}
        </Box>

        {/* Tablet Center Panel */}
        <Box
          data-testid="tablet-center-panel"
          sx={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            minWidth: 0 // Allow shrinking
          }}
        >
          {centerPanel}
        </Box>

        {/* Tablet Right Panel (Collapsible) */}
        <Collapse
          in={!rightPanelCollapsed}
          orientation="horizontal"
          sx={{ display: 'flex' }}
        >
          <Box
            data-testid="tablet-right-panel"
            sx={{
              width: 240, // Smaller for tablet
              borderLeft: `1px solid ${theme.palette.divider}`,
              display: 'flex',
              flexDirection: 'column',
              backgroundColor: 'white'
            }}
          >
            {rightPanel}
          </Box>
        </Collapse>

        {/* Tablet Panel Toggle */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            borderLeft: !rightPanelCollapsed ? 'none' : `1px solid ${theme.palette.divider}`,
            backgroundColor: 'white'
          }}
        >
          <IconButton
            onClick={() => setRightPanelCollapsed(!rightPanelCollapsed)}
            data-testid="tablet-panel-toggle"
            sx={{
              borderRadius: 0,
              height: '100%',
              width: 32,
              '&:hover': {
                backgroundColor: theme.palette.action.hover
              }
            }}
          >
            {rightPanelCollapsed ? <ExpandMoreIcon sx={{ transform: 'rotate(-90deg)' }} /> : <ExpandLessIcon sx={{ transform: 'rotate(90deg)' }} />}
          </IconButton>
        </Box>
      </Box>
    );
  }

  // Desktop Layout (Full 3-Panel)
  return (
    <Box
      data-testid="desktop-layout"
      sx={{
        height: '100vh',
        display: 'flex',
        backgroundColor: theme.palette.grey[50]
      }}
    >
      {/* Desktop Left Panel */}
      <Box
        data-testid="desktop-left-panel"
        sx={{
          width: 320,
          borderRight: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'white'
        }}
      >
        {leftPanel}
      </Box>

      {/* Desktop Center Panel */}
      <Box
        data-testid="desktop-center-panel"
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {centerPanel}
      </Box>

      {/* Desktop Right Panel */}
      <Box
        data-testid="desktop-right-panel"
        sx={{
          width: 280,
          borderLeft: `1px solid ${theme.palette.divider}`,
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'white'
        }}
      >
        {rightPanel}
      </Box>
    </Box>
  );
}

/**
 * CSS-in-JS Responsive Styles
 * 
 * These styles can be applied to the existing ProfessionalWorkspace
 * to fix responsive issues without major restructuring.
 */
export const responsiveWorkspaceStyles = {
  // Mobile-first approach
  root: {
    height: '100vh',
    display: 'flex',
    backgroundColor: '#f8fafc',
    
    // Mobile (<768px): Stack vertically
    flexDirection: 'column',
    
    // Tablet (768px+): Horizontal with flexible widths
    [theme.breakpoints.up('md')]: {
      flexDirection: 'row'
    }
  },
  
  leftPanel: {
    // Mobile: Full width, controlled by drawer
    display: 'none',
    
    // Tablet: Fixed width
    [theme.breakpoints.up('md')]: {
      display: 'flex',
      width: 280,
      borderRight: `1px solid ${theme.palette.divider}`
    },
    
    // Desktop: Larger width
    [theme.breakpoints.up('lg')]: {
      width: 320
    }
  },
  
  centerPanel: {
    // Mobile: Full space
    flex: 1,
    minHeight: 0,
    
    // All breakpoints: Always flexible
    display: 'flex',
    flexDirection: 'column'
  },
  
  rightPanel: {
    // Mobile: Hidden by default, shown as bottom sheet
    display: 'none',
    
    // Tablet: Collapsible
    [theme.breakpoints.up('md')]: {
      display: 'flex',
      width: 240,
      borderLeft: `1px solid ${theme.palette.divider}`
    },
    
    // Desktop: Full width
    [theme.breakpoints.up('lg')]: {
      width: 280
    }
  }
};

/**
 * Accessibility Enhancements
 */
export const accessibilityProps = {
  // Session list items
  sessionItem: {
    role: 'button',
    tabIndex: 0,
    'aria-label': (sessionName: string) => `Select session: ${sessionName}`,
    onKeyDown: (e: React.KeyboardEvent, onClick: () => void) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick();
      }
    }
  },
  
  // Mobile drawer
  mobileDrawer: {
    'aria-label': 'Session navigation',
    role: 'navigation'
  },
  
  // Panel toggles
  panelToggle: (panelName: string, isOpen: boolean) => ({
    'aria-label': `${isOpen ? 'Collapse' : 'Expand'} ${panelName} panel`,
    'aria-expanded': isOpen
  })
};