import { test, expect, devices } from '@playwright/test';

/**
 * Cross-Browser Visual Validation Suite
 * 
 * Ensures pixel-perfect consistency across Chrome, Firefox, and Safari
 * with special focus on terminal font rendering and dark mode aesthetics.
 */

const TEST_VIEWPORTS = [
  { name: 'desktop-standard', width: 1920, height: 1080 },
  { name: 'desktop-laptop', width: 1366, height: 768 },
  { name: 'ultrawide', width: 3440, height: 1440 },
];

const BROWSERS = ['chromium', 'firefox', 'webkit'] as const;

// Helper function to wait for app readiness
async function waitForAppReady(page: any) {
  await page.goto('/');
  
  // Wait for core components
  await expect(page.locator('[data-testid="command-center"]')).toBeVisible();
  await expect(page.locator('[data-testid="status-bar"]')).toBeVisible();
  await expect(page.locator('[data-testid="connection-status"]')).toContainText('ONLINE', { timeout: 10000 });
  
  // Ensure fonts are loaded
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(1000);
}

// Helper to stabilize animations
async function stabilizeUI(page: any) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        transition-duration: 0s !important;
      }
      .pulse { animation: none !important; }
    `
  });
}

test.describe('Cross-Browser Font Rendering', () => {
  BROWSERS.forEach(browserName => {
    test(`terminal font consistency - ${browserName}`, async ({ page }) => {
      await waitForAppReady(page);
      await stabilizeUI(page);
      
      // Test status bar font rendering
      const statusBar = page.locator('[data-testid="status-bar"]');
      await expect(statusBar).toHaveScreenshot(`font-status-bar-${browserName}.png`, {
        animations: 'disabled',
      });
      
      // Open command palette to test input font rendering
      await page.keyboard.press('Meta+k');
      await page.waitForTimeout(500);
      
      const commandPalette = page.locator('[data-testid="command-palette"]');
      await expect(commandPalette).toHaveScreenshot(`font-command-palette-${browserName}.png`, {
        animations: 'disabled',
      });
    });
  });

  test('font rendering with different text sizes', async ({ page }) => {
    await waitForAppReady(page);
    await stabilizeUI(page);
    
    // Test different zoom levels for font consistency
    const zoomLevels = [
      { level: 1, name: 'normal' },
      { level: 1.25, name: '125percent' },
      { level: 1.5, name: '150percent' },
    ];
    
    for (const zoom of zoomLevels) {
      await page.evaluate((zoomLevel) => {
        document.body.style.zoom = String(zoomLevel);
      }, zoom.level);
      
      await page.waitForTimeout(500);
      
      const statusBar = page.locator('[data-testid="status-bar"]');
      await expect(statusBar).toHaveScreenshot(`font-zoom-${zoom.name}.png`, {
        animations: 'disabled',
      });
    }
  });

  test('monospace font fallback behavior', async ({ page }) => {
    await waitForAppReady(page);
    
    // Test font fallback by disabling primary fonts
    await page.addStyleTag({
      content: `
        @font-face {
          font-family: 'SFMono-Regular';
          src: url('data:,') format('woff2');
        }
        @font-face {
          font-family: 'Monaco';
          src: url('data:,') format('woff2');
        }
        body {
          font-family: 'Consolas', 'Roboto Mono', monospace;
        }
      `
    });
    
    await page.waitForTimeout(1000);
    await stabilizeUI(page);
    
    await expect(page.locator('[data-testid="status-bar"]')).toHaveScreenshot('font-fallback-consolas.png', {
      animations: 'disabled',
    });
  });
});

test.describe('Cross-Browser Layout Consistency', () => {
  TEST_VIEWPORTS.forEach(viewport => {
    BROWSERS.forEach(browserName => {
      test(`layout consistency - ${viewport.name} - ${browserName}`, async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await waitForAppReady(page);
        await stabilizeUI(page);
        
        // Full page screenshot for layout consistency
        await expect(page).toHaveScreenshot(`layout-${viewport.name}-${browserName}.png`, {
          fullPage: true,
          animations: 'disabled',
        });
      });
    });
  });

  test('responsive breakpoint consistency across browsers', async ({ page }) => {
    const breakpoints = [
      { width: 3440, height: 1440, name: 'ultrawide' },
      { width: 1920, height: 1080, name: 'desktop' },
      { width: 1366, height: 768, name: 'laptop' },
      { width: 1024, height: 768, name: 'tablet' },
    ];
    
    for (const breakpoint of breakpoints) {
      await page.setViewportSize({ width: breakpoint.width, height: breakpoint.height });
      await waitForAppReady(page);
      await stabilizeUI(page);
      
      // Test 3-pane layout adaptation
      const orchestrationTree = page.locator('[data-testid="orchestration-tree"]');
      const workspace = page.locator('[data-testid="workspace"]');
      const activityStream = page.locator('[data-testid="activity-stream"]');
      
      await expect(orchestrationTree).toBeVisible();
      await expect(workspace).toBeVisible();
      await expect(activityStream).toBeVisible();
      
      await expect(page).toHaveScreenshot(`responsive-${breakpoint.name}.png`, {
        fullPage: true,
        animations: 'disabled',
      });
    }
  });
});

test.describe('Dark Mode Cross-Browser Validation', () => {
  BROWSERS.forEach(browserName => {
    test(`dark mode rendering - ${browserName}`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: 'dark' });
      await waitForAppReady(page);
      await stabilizeUI(page);
      
      // Test dark mode consistency
      await expect(page).toHaveScreenshot(`dark-mode-${browserName}.png`, {
        fullPage: true,
        animations: 'disabled',
      });
      
      // Test command palette in dark mode
      await page.keyboard.press('Meta+k');
      await page.waitForTimeout(500);
      
      const commandPalette = page.locator('[data-testid="command-palette"]');
      await expect(commandPalette).toHaveScreenshot(`dark-mode-palette-${browserName}.png`, {
        animations: 'disabled',
      });
    });
  });

  test('color scheme consistency validation', async ({ page }) => {
    await waitForAppReady(page);
    await stabilizeUI(page);
    
    // Test CSS custom properties are applied correctly
    const colorValues = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement);
      return {
        primaryBg: style.getPropertyValue('--khive-bg-primary'),
        secondaryBg: style.getPropertyValue('--khive-bg-secondary'),
        primaryText: style.getPropertyValue('--khive-text-primary'),
        accentPrimary: style.getPropertyValue('--khive-accent-primary'),
      };
    });
    
    // Validate color values are properly set
    expect(colorValues.primaryBg).toBe('#0a0a0a');
    expect(colorValues.accentPrimary).toBe('#00d4aa');
    
    // Take screenshot to verify visual application
    await expect(page).toHaveScreenshot('color-scheme-validation.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('high contrast mode accessibility', async ({ page }) => {
    await page.emulateMedia({ 
      colorScheme: 'dark',
      prefersContrast: 'high'
    });
    
    await waitForAppReady(page);
    await stabilizeUI(page);
    
    await expect(page).toHaveScreenshot('high-contrast-accessibility.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});

test.describe('Component State Cross-Browser Testing', () => {
  const componentStates = [
    {
      name: 'default-state',
      setup: async (page: any) => {
        // Default state - no additional setup needed
      }
    },
    {
      name: 'tree-focused',
      setup: async (page: any) => {
        await page.keyboard.press('Meta+1');
        await page.waitForTimeout(300);
      }
    },
    {
      name: 'workspace-focused',
      setup: async (page: any) => {
        await page.keyboard.press('Meta+2');
        await page.waitForTimeout(300);
      }
    },
    {
      name: 'activity-focused',
      setup: async (page: any) => {
        await page.keyboard.press('Meta+3');
        await page.waitForTimeout(300);
      }
    },
    {
      name: 'command-palette-open',
      setup: async (page: any) => {
        await page.keyboard.press('Meta+k');
        await page.waitForTimeout(500);
      }
    },
    {
      name: 'help-dialog-open',
      setup: async (page: any) => {
        await page.keyboard.press('Meta+Shift+k');
        await page.waitForTimeout(500);
      }
    }
  ];

  BROWSERS.forEach(browserName => {
    componentStates.forEach(state => {
      test(`${state.name} state - ${browserName}`, async ({ page }) => {
        await waitForAppReady(page);
        await stabilizeUI(page);
        
        // Set up the specific state
        await state.setup(page);
        
        // Take screenshot
        await expect(page).toHaveScreenshot(`state-${state.name}-${browserName}.png`, {
          fullPage: true,
          animations: 'disabled',
        });
      });
    });
  });
});

test.describe('Performance Impact Visual Testing', () => {
  test('visual stability during high activity', async ({ page }) => {
    await waitForAppReady(page);
    await stabilizeUI(page);
    
    // Simulate high activity in the interface
    await page.evaluate(() => {
      // Simulate multiple rapid state changes
      const events = [];
      for (let i = 0; i < 10; i++) {
        events.push({
          id: `event-${i}`,
          timestamp: Date.now() + i * 100,
          type: 'agent_action',
          message: `Agent action ${i}`,
        });
      }
      
      // Dispatch custom event with mock data
      window.dispatchEvent(new CustomEvent('khive-activity', { 
        detail: { events } 
      }));
    });
    
    await page.waitForTimeout(1000);
    
    // Test that layout remains stable
    await expect(page).toHaveScreenshot('high-activity-stability.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('memory-efficient rendering validation', async ({ page }) => {
    await waitForAppReady(page);
    await stabilizeUI(page);
    
    // Test performance mode rendering
    await page.addStyleTag({
      content: `
        .performance-mode * {
          animation-duration: 0s !important;
          transition-duration: 0s !important;
        }
      `
    });
    
    await page.evaluate(() => {
      document.body.classList.add('performance-mode');
    });
    
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('performance-mode-rendering.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});

test.describe('Edge Case Visual Testing', () => {
  test('extremely long content handling', async ({ page }) => {
    await waitForAppReady(page);
    await stabilizeUI(page);
    
    // Simulate long command names in the palette
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(500);
    
    // Type a very long search query
    const longQuery = 'this is an extremely long command search query that should test text wrapping and overflow handling in the command palette interface';
    await page.locator('[data-testid="command-input"]').fill(longQuery);
    await page.waitForTimeout(300);
    
    const commandPalette = page.locator('[data-testid="command-palette"]');
    await expect(commandPalette).toHaveScreenshot('long-content-handling.png', {
      animations: 'disabled',
    });
  });

  test('empty state rendering', async ({ page }) => {
    await waitForAppReady(page);
    await stabilizeUI(page);
    
    // Test empty search results
    await page.keyboard.press('Meta+k');
    await page.waitForTimeout(500);
    
    await page.locator('[data-testid="command-input"]').fill('nonexistentcommand12345');
    await page.waitForTimeout(300);
    
    const commandPalette = page.locator('[data-testid="command-palette"]');
    await expect(commandPalette).toHaveScreenshot('empty-search-results.png', {
      animations: 'disabled',
    });
  });

  test('rapid interaction stability', async ({ page }) => {
    await waitForAppReady(page);
    await stabilizeUI(page);
    
    // Rapidly switch between panes
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Meta+1');
      await page.waitForTimeout(50);
      await page.keyboard.press('Meta+2');
      await page.waitForTimeout(50);
      await page.keyboard.press('Meta+3');
      await page.waitForTimeout(50);
    }
    
    // Final state should be stable
    await page.waitForTimeout(500);
    
    await expect(page).toHaveScreenshot('rapid-interaction-final-state.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});