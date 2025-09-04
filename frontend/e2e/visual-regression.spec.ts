import { test, expect, Page } from '@playwright/test';

/**
 * Visual Regression Testing Suite for Ocean's Agentic ERP Command Center
 * 
 * Tests pixel-perfect consistency across browsers and ensures terminal aesthetics
 * are maintained across all UI states and interactions.
 */

// Helper function to wait for app stability
async function waitForAppStability(page: Page) {
  // Wait for main components to be visible
  await expect(page.locator('[data-testid="command-center"]')).toBeVisible();
  await expect(page.locator('[data-testid="orchestration-tree"]')).toBeVisible();
  await expect(page.locator('[data-testid="workspace"]')).toBeVisible();
  await expect(page.locator('[data-testid="activity-stream"]')).toBeVisible();
  
  // Wait for WebSocket connection
  await expect(page.locator('[data-testid="connection-status"]')).toContainText('ONLINE', { timeout: 10000 });
  
  // Ensure fonts are loaded
  await page.evaluate(() => document.fonts.ready);
  
  // Wait for any animations to complete
  await page.waitForTimeout(1000);
}

// Helper function to hide dynamic content for consistent screenshots
async function hideVariableContent(page: Page) {
  await page.addStyleTag({
    content: `
      /* Hide timestamps and other dynamic content */
      [data-testid="timestamp"],
      [data-testid="connection-latency"],
      [data-testid="session-count"],
      .pulse {
        visibility: hidden !important;
      }
      
      /* Ensure consistent animation states */
      *,
      *::before,
      *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `
  });
}

test.describe('Command Center Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForAppStability(page);
    await hideVariableContent(page);
  });

  test('full command center layout - default state', async ({ page }) => {
    // Take full page screenshot of default layout
    await expect(page).toHaveScreenshot('command-center-default.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('command center - orchestration tree focused', async ({ page }) => {
    // Focus on orchestration tree (left pane)
    await page.keyboard.press('Meta+1');
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('command-center-tree-focused.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('command center - workspace focused', async ({ page }) => {
    // Focus on main workspace (center pane)
    await page.keyboard.press('Meta+2');
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('command-center-workspace-focused.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('command center - activity stream focused', async ({ page }) => {
    // Focus on activity stream (right pane)
    await page.keyboard.press('Meta+3');
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('command-center-activity-focused.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('status bar - terminal styling consistency', async ({ page }) => {
    // Test the terminal-style status bar
    const statusBar = page.locator('[data-testid="status-bar"]');
    await expect(statusBar).toBeVisible();
    
    await expect(statusBar).toHaveScreenshot('status-bar-terminal-style.png', {
      animations: 'disabled',
    });
  });

  test('status bar - connection states', async ({ page }) => {
    // Test different connection states
    const statusBar = page.locator('[data-testid="status-bar"]');
    
    // Online state (default)
    await expect(statusBar).toHaveScreenshot('status-bar-online.png', {
      animations: 'disabled',
    });
    
    // Simulate offline state for visual testing
    await page.evaluate(() => {
      const statusElement = document.querySelector('[data-testid="connection-status"]');
      if (statusElement) {
        statusElement.textContent = '● KHIVE OFFLINE';
        statusElement.style.color = '#ef4444';
      }
    });
    
    await expect(statusBar).toHaveScreenshot('status-bar-offline.png', {
      animations: 'disabled',
    });
  });

  test('workspace views - planning mode', async ({ page }) => {
    // Navigate to planning view
    await page.keyboard.press('g');
    await page.keyboard.press('p');
    await page.waitForTimeout(1000);
    
    await expect(page.locator('[data-testid="workspace"]')).toHaveScreenshot('workspace-planning.png', {
      animations: 'disabled',
    });
  });

  test('workspace views - monitoring mode', async ({ page }) => {
    // Navigate to monitoring view
    await page.keyboard.press('g');
    await page.keyboard.press('m');
    await page.waitForTimeout(1000);
    
    await expect(page.locator('[data-testid="workspace"]')).toHaveScreenshot('workspace-monitoring.png', {
      animations: 'disabled',
    });
  });

  test('workspace views - agents mode', async ({ page }) => {
    // Navigate to agents view
    await page.keyboard.press('g');
    await page.keyboard.press('a');
    await page.waitForTimeout(1000);
    
    await expect(page.locator('[data-testid="workspace"]')).toHaveScreenshot('workspace-agents.png', {
      animations: 'disabled',
    });
  });

  test('workspace views - analytics mode', async ({ page }) => {
    // Navigate to analytics view
    await page.keyboard.press('g');
    await page.keyboard.press('n'); // Using 'n' for analytics as per shortcuts
    await page.waitForTimeout(1000);
    
    await expect(page.locator('[data-testid="workspace"]')).toHaveScreenshot('workspace-analytics.png', {
      animations: 'disabled',
    });
  });

  test('workspace views - settings mode', async ({ page }) => {
    // Navigate to settings view
    await page.keyboard.press('g');
    await page.keyboard.press('s');
    await page.waitForTimeout(1000);
    
    await expect(page.locator('[data-testid="workspace"]')).toHaveScreenshot('workspace-settings.png', {
      animations: 'disabled',
    });
  });
});

test.describe('Command Palette Visual Regression', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForAppStability(page);
    await hideVariableContent(page);
  });

  test('command palette - closed state', async ({ page }) => {
    // Ensure command palette is closed
    const palette = page.locator('[data-testid="command-palette"]');
    await expect(palette).not.toBeVisible();
    
    // Screenshot showing no overlay
    await expect(page).toHaveScreenshot('command-palette-closed.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('command palette - open state (empty query)', async ({ page }) => {
    // Open command palette
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(500);
    
    const palette = page.locator('[data-testid="command-palette"]');
    await expect(palette).toBeVisible();
    
    await expect(palette).toHaveScreenshot('command-palette-open-empty.png', {
      animations: 'disabled',
    });
  });

  test('command palette - search results', async ({ page }) => {
    // Open command palette and search
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(500);
    
    const input = page.locator('[data-testid="command-input"]');
    await input.fill('plan');
    await page.waitForTimeout(300);
    
    const palette = page.locator('[data-testid="command-palette"]');
    await expect(palette).toHaveScreenshot('command-palette-search-plan.png', {
      animations: 'disabled',
    });
  });

  test('command palette - category filtering', async ({ page }) => {
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(500);
    
    // Test different search terms for different categories
    const searches = [
      { term: 'orchestration', filename: 'orchestration-commands' },
      { term: 'agent', filename: 'agent-commands' },
      { term: 'system', filename: 'system-commands' },
      { term: 'navigation', filename: 'navigation-commands' }
    ];
    
    for (const search of searches) {
      const input = page.locator('[data-testid="command-input"]');
      await input.fill('');
      await input.fill(search.term);
      await page.waitForTimeout(300);
      
      const palette = page.locator('[data-testid="command-palette"]');
      await expect(palette).toHaveScreenshot(`command-palette-${search.filename}.png`, {
        animations: 'disabled',
      });
    }
  });

  test('command palette - keyboard navigation', async ({ page }) => {
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(500);
    
    const input = page.locator('[data-testid="command-input"]');
    await input.fill('plan');
    await page.waitForTimeout(300);
    
    // Navigate down to select second item
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('ArrowDown');
    await page.waitForTimeout(200);
    
    const palette = page.locator('[data-testid="command-palette"]');
    await expect(palette).toHaveScreenshot('command-palette-keyboard-selection.png', {
      animations: 'disabled',
    });
  });

  test('command palette - help dialog', async ({ page }) => {
    // Open help dialog
    await page.keyboard.press('Meta+Shift+k');
    await page.waitForTimeout(500);
    
    const helpDialog = page.locator('[data-testid="help-dialog"]');
    await expect(helpDialog).toBeVisible();
    
    await expect(helpDialog).toHaveScreenshot('command-palette-help-dialog.png', {
      animations: 'disabled',
    });
  });
});

test.describe('Terminal Font Consistency Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForAppStability(page);
    await hideVariableContent(page);
  });

  test('terminal font rendering - status bar', async ({ page }) => {
    const statusBar = page.locator('[data-testid="status-bar"]');
    
    // Test font rendering at different zoom levels
    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect(statusBar).toHaveScreenshot('font-status-bar-100percent.png');
    
    // 125% zoom (common high-DPI setting)
    await page.evaluate(() => {
      document.body.style.zoom = '1.25';
    });
    await page.waitForTimeout(500);
    await expect(statusBar).toHaveScreenshot('font-status-bar-125percent.png');
    
    // Reset zoom
    await page.evaluate(() => {
      document.body.style.zoom = '1';
    });
  });

  test('terminal font rendering - command palette', async ({ page }) => {
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(500);
    
    const palette = page.locator('[data-testid="command-palette"]');
    
    // Test different font rendering scenarios
    await expect(palette).toHaveScreenshot('font-command-palette-default.png');
    
    // Test with different font-rendering CSS properties
    await page.addStyleTag({
      content: `
        .command-palette * {
          text-rendering: optimizeSpeed;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
      `
    });
    await page.waitForTimeout(300);
    
    await expect(palette).toHaveScreenshot('font-command-palette-optimized.png');
  });

  test('font fallback testing', async ({ page }) => {
    // Test font fallback behavior by disabling primary fonts
    await page.addStyleTag({
      content: `
        @font-face {
          font-family: 'SFMono-Regular';
          src: url('data:,') format('woff2');
        }
        body {
          font-family: 'Monaco', 'Inconsolata', 'Roboto Mono', 'Consolas', monospace;
        }
      `
    });
    
    await page.waitForTimeout(1000);
    
    await expect(page).toHaveScreenshot('font-fallback-no-sfmono.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});

test.describe('Responsive Design Visual Tests', () => {
  const viewports = [
    { name: 'desktop-1920', width: 1920, height: 1080 },
    { name: 'desktop-1366', width: 1366, height: 768 },
    { name: 'ultrawide', width: 3440, height: 1440 },
    { name: 'laptop-small', width: 1280, height: 720 },
  ];

  viewports.forEach(viewport => {
    test(`layout consistency - ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/');
      await waitForAppStability(page);
      await hideVariableContent(page);
      
      await expect(page).toHaveScreenshot(`layout-${viewport.name}.png`, {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });

  test('responsive command palette', async ({ page }) => {
    const viewports = [
      { name: 'desktop', width: 1920, height: 1080 },
      { name: 'laptop', width: 1366, height: 768 },
      { name: 'tablet', width: 1024, height: 768 },
    ];

    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/');
      await waitForAppStability(page);
      await hideVariableContent(page);
      
      await page.keyboard.press('Meta+k');
      await page.waitForTimeout(500);
      
      const palette = page.locator('[data-testid="command-palette"]');
      await expect(palette).toHaveScreenshot(`command-palette-${viewport.name}.png`, {
        animations: 'disabled',
      });
      
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }
  });
});

test.describe('Dark Mode Consistency Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForAppStability(page);
    await hideVariableContent(page);
  });

  test('dark mode - color scheme consistency', async ({ page }) => {
    // Ensure dark mode is active
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('dark-mode-full-layout.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('dark mode - component-level consistency', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await page.waitForTimeout(500);
    
    // Test individual components for consistent dark mode styling
    const components = [
      { selector: '[data-testid="orchestration-tree"]', name: 'orchestration-tree' },
      { selector: '[data-testid="workspace"]', name: 'workspace' },
      { selector: '[data-testid="activity-stream"]', name: 'activity-stream' },
      { selector: '[data-testid="status-bar"]', name: 'status-bar' },
    ];
    
    for (const component of components) {
      const element = page.locator(component.selector);
      await expect(element).toBeVisible();
      await expect(element).toHaveScreenshot(`dark-mode-${component.name}.png`, {
        animations: 'disabled',
      });
    }
  });

  test('contrast verification - accessibility', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark', prefersReducedMotion: 'reduce' });
    await page.waitForTimeout(500);
    
    // Test high contrast mode
    await page.addStyleTag({
      content: `
        :root {
          --khive-text-primary: #ffffff;
          --khive-text-secondary: #cccccc;
          --khive-bg-primary: #000000;
          --khive-bg-secondary: #111111;
        }
      `
    });
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('high-contrast-mode.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});

test.describe('Animation and Interaction States', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForAppStability(page);
  });

  test('button hover states', async ({ page }) => {
    // Find interactive elements and test hover states
    const buttons = page.locator('button:visible').first();
    await expect(buttons).toBeVisible();
    
    // Before hover
    await expect(buttons).toHaveScreenshot('button-default-state.png');
    
    // Hover state
    await buttons.hover();
    await page.waitForTimeout(200);
    await expect(buttons).toHaveScreenshot('button-hover-state.png');
  });

  test('focus states - keyboard navigation', async ({ page }) => {
    // Test focus states for keyboard navigation
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
    
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
    await expect(focusedElement).toHaveScreenshot('focus-state-first-element.png');
  });

  test('loading states', async ({ page }) => {
    // Simulate loading state by intercepting network requests
    await page.route('**/api/**', route => {
      setTimeout(() => {
        route.fulfill({ status: 200, body: '{}' });
      }, 2000);
    });
    
    await page.reload();
    await page.waitForTimeout(500);
    
    // Capture loading state
    await expect(page).toHaveScreenshot('loading-state.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});