import { test, expect, Page } from '@playwright/test';

// Test helper functions for CLI-optimized workflows
class CLITestHelper {
  constructor(private page: Page) {}

  async openCommandPalette() {
    await this.page.keyboard.press('Meta+k');
    await this.page.waitForSelector('[role="dialog"]', { timeout: 1000 });
  }

  async closeCommandPalette() {
    await this.page.keyboard.press('Escape');
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 1000 });
  }

  async focusPane(paneNumber: 1 | 2 | 3) {
    await this.page.keyboard.press(`Meta+${paneNumber}`);
    // Allow for focus transition
    await this.page.waitForTimeout(100);
  }

  async navigateVimStyle(target: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings') {
    const keyMap = {
      planning: 'g p',
      monitoring: 'g m',
      analytics: 'g n', // analytics/navigation
      agents: 'g a',
      settings: 'g s'
    };
    
    const keys = keyMap[target].split(' ');
    for (const key of keys) {
      await this.page.keyboard.press(key);
      await this.page.waitForTimeout(50); // Small delay between sequence keys
    }
  }

  async waitForContextSwitch() {
    // Wait for context switching animation/transition
    await this.page.waitForTimeout(100);
  }

  async measureContextSwitchTime(action: () => Promise<void>): Promise<number> {
    const startTime = performance.now();
    await action();
    await this.waitForContextSwitch();
    const endTime = performance.now();
    return endTime - startTime;
  }

  async takeWorkflowScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `test-results/screenshots/cli-workflow-${name}.png`,
      fullPage: true 
    });
  }

  async verifyTerminalFont() {
    const fontFamily = await this.page.evaluate(() => {
      const computedStyle = getComputedStyle(document.body);
      return computedStyle.fontFamily;
    });
    
    // Verify terminal-optimized font is being used
    expect(fontFamily).toMatch(/JetBrains Mono|Fira Code|Monaco|Menlo|monospace/);
  }

  async verifyDarkMode() {
    const bodyClasses = await this.page.locator('body').getAttribute('class');
    expect(bodyClasses).toContain('dark');
  }

  async verifyHighInformationDensity() {
    // Check that status bar and key information is visible
    const statusBar = this.page.locator('[data-testid="status-bar"], .status-bar');
    await expect(statusBar).toBeVisible();
    
    // Check that multiple data points are visible
    const infoElements = this.page.locator('[data-testid*="info"], .info-display');
    const count = await infoElements.count();
    expect(count).toBeGreaterThan(3); // High density means multiple info points
  }
}

test.describe('CLI Workflows E2E Tests', () => {
  let cliHelper: CLITestHelper;

  test.beforeEach(async ({ page }) => {
    cliHelper = new CLITestHelper(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Ensure we're in CLI-optimized mode
    await cliHelper.verifyDarkMode();
    await cliHelper.verifyTerminalFont();
  });

  test.describe('Terminal-Optimized UX', () => {
    test('should render with consistent terminal font', async ({ page }) => {
      await cliHelper.verifyTerminalFont();
      
      // Take screenshot for visual verification
      await cliHelper.takeWorkflowScreenshot('terminal-font-rendering');
    });

    test('should display high information density status bar', async ({ page }) => {
      await cliHelper.verifyHighInformationDensity();
      
      // Take screenshot of status bar
      await cliHelper.takeWorkflowScreenshot('high-density-status-bar');
    });

    test('should maintain dark mode CLI aesthetics', async ({ page }) => {
      await cliHelper.verifyDarkMode();
      
      // Verify dark theme colors
      const backgroundColor = await page.evaluate(() => {
        return getComputedStyle(document.body).backgroundColor;
      });
      
      // Should be a dark color
      expect(backgroundColor).toMatch(/rgb\((\d{1,2}), (\d{1,2}), (\d{1,2})\)/);
      const [, r, g, b] = backgroundColor.match(/rgb\((\d+), (\d+), (\d+)\)/) || [];
      const averageBrightness = (parseInt(r) + parseInt(g) + parseInt(b)) / 3;
      expect(averageBrightness).toBeLessThan(50); // Dark theme
      
      await cliHelper.takeWorkflowScreenshot('dark-mode-aesthetics');
    });
  });

  test.describe('Keyboard-Only Navigation Flows', () => {
    test('should support complete keyboard-only workflow', async ({ page }) => {
      // Start workflow: Open command palette
      await cliHelper.takeWorkflowScreenshot('workflow-start');
      await cliHelper.openCommandPalette();
      await cliHelper.takeWorkflowScreenshot('command-palette-opened');
      
      // Type a command
      await page.keyboard.type('plan');
      await page.waitForTimeout(300); // Allow filtering
      await cliHelper.takeWorkflowScreenshot('command-filtered');
      
      // Execute command
      await page.keyboard.press('Enter');
      await cliHelper.closeCommandPalette();
      await cliHelper.takeWorkflowScreenshot('command-executed');
      
      // Navigate using vim-style shortcuts
      await cliHelper.navigateVimStyle('monitoring');
      await cliHelper.takeWorkflowScreenshot('vim-navigation-monitoring');
      
      // Focus different panes
      await cliHelper.focusPane(1);
      await cliHelper.takeWorkflowScreenshot('pane-1-focused');
      
      await cliHelper.focusPane(2);
      await cliHelper.takeWorkflowScreenshot('pane-2-focused');
      
      await cliHelper.focusPane(3);
      await cliHelper.takeWorkflowScreenshot('pane-3-focused');
    });

    test('should handle rapid keyboard navigation without issues', async ({ page }) => {
      // Rapid navigation test
      const targets: Array<'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings'> = 
        ['planning', 'monitoring', 'analytics', 'agents', 'settings'];
      
      for (const target of targets) {
        await cliHelper.navigateVimStyle(target);
        await page.waitForTimeout(100);
      }
      
      // Rapid pane switching
      for (let i = 1; i <= 3; i++) {
        await cliHelper.focusPane(i as 1 | 2 | 3);
        await page.waitForTimeout(100);
      }
      
      await cliHelper.takeWorkflowScreenshot('rapid-navigation-complete');
    });

    test('should prevent interference with system shortcuts', async ({ page }) => {
      // Test that our shortcuts don't interfere with browser shortcuts
      // These should work normally and not be blocked
      
      // Test Cmd+T (new tab) - should not be prevented
      const tabKeyDown = page.keyboard.press('Meta+t');
      // Don't await - we're testing that the event isn't preventDefault'd
      
      // Test Cmd+R (refresh) - should not be prevented  
      const refreshKeyDown = page.keyboard.press('Meta+r');
      // Don't await - we're testing that the event isn't preventDefault'd
      
      // Our custom shortcuts should still work
      await cliHelper.openCommandPalette();
      await expect(page.locator('[role="dialog"]')).toBeVisible();
      await cliHelper.closeCommandPalette();
    });
  });

  test.describe('Context Switching Performance', () => {
    test('should switch pane focus under 50ms', async ({ page }) => {
      const measurements: number[] = [];
      
      // Test multiple pane switches and measure timing
      for (let i = 0; i < 5; i++) {
        const time1 = await cliHelper.measureContextSwitchTime(() => cliHelper.focusPane(1));
        measurements.push(time1);
        
        const time2 = await cliHelper.measureContextSwitchTime(() => cliHelper.focusPane(2));
        measurements.push(time2);
        
        const time3 = await cliHelper.measureContextSwitchTime(() => cliHelper.focusPane(3));
        measurements.push(time3);
      }
      
      const averageTime = measurements.reduce((a, b) => a + b) / measurements.length;
      console.log(`Average pane focus switch time: ${averageTime.toFixed(2)}ms`);
      
      // Assert that average switch time is under 50ms
      expect(averageTime).toBeLessThan(50);
      
      // No individual measurement should exceed 100ms
      measurements.forEach((time, index) => {
        expect(time).toBeLessThan(100, `Measurement ${index + 1}: ${time.toFixed(2)}ms exceeded 100ms`);
      });
      
      await cliHelper.takeWorkflowScreenshot('performance-test-complete');
    });

    test('should switch views under 50ms', async ({ page }) => {
      const views: Array<'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings'> = 
        ['planning', 'monitoring', 'analytics', 'agents', 'settings'];
      
      const measurements: number[] = [];
      
      for (const view of views) {
        const switchTime = await cliHelper.measureContextSwitchTime(() => cliHelper.navigateVimStyle(view));
        measurements.push(switchTime);
      }
      
      const averageTime = measurements.reduce((a, b) => a + b) / measurements.length;
      console.log(`Average view switch time: ${averageTime.toFixed(2)}ms`);
      
      // Assert that average switch time is under 50ms
      expect(averageTime).toBeLessThan(50);
      
      await cliHelper.takeWorkflowScreenshot('view-switch-performance-complete');
    });

    test('should open command palette under 50ms', async ({ page }) => {
      const measurements: number[] = [];
      
      // Test command palette opening multiple times
      for (let i = 0; i < 10; i++) {
        const openTime = await cliHelper.measureContextSwitchTime(async () => {
          await cliHelper.openCommandPalette();
        });
        measurements.push(openTime);
        
        await cliHelper.closeCommandPalette();
        await page.waitForTimeout(100); // Small delay between tests
      }
      
      const averageTime = measurements.reduce((a, b) => a + b) / measurements.length;
      console.log(`Average command palette open time: ${averageTime.toFixed(2)}ms`);
      
      // Assert that average open time is under 50ms
      expect(averageTime).toBeLessThan(50);
      
      // No individual measurement should exceed 100ms
      measurements.forEach((time, index) => {
        expect(time).toBeLessThan(100, `Open time ${index + 1}: ${time.toFixed(2)}ms exceeded 100ms`);
      });
    });
  });

  test.describe('Visual Focus Indicators', () => {
    test('should display clear visual focus indicators for all panes', async ({ page }) => {
      // Test pane 1 focus indicator
      await cliHelper.focusPane(1);
      const pane1 = page.locator('[data-testid="orchestration-tree"], .pane-1');
      await expect(pane1).toHaveAttribute('data-focused', 'true');
      await cliHelper.takeWorkflowScreenshot('pane-1-focus-indicator');
      
      // Test pane 2 focus indicator
      await cliHelper.focusPane(2);
      const pane2 = page.locator('[data-testid="workspace"], .pane-2');
      await expect(pane2).toHaveAttribute('data-focused', 'true');
      await cliHelper.takeWorkflowScreenshot('pane-2-focus-indicator');
      
      // Test pane 3 focus indicator
      await cliHelper.focusPane(3);
      const pane3 = page.locator('[data-testid="activity-stream"], .pane-3');
      await expect(pane3).toHaveAttribute('data-focused', 'true');
      await cliHelper.takeWorkflowScreenshot('pane-3-focus-indicator');
    });

    test('should highlight focused elements with visible styling', async ({ page }) => {
      await cliHelper.focusPane(2);
      
      // Get the focused element
      const focusedElement = page.locator('[data-focused="true"]');
      await expect(focusedElement).toBeVisible();
      
      // Check that focused element has visible styling differences
      const borderColor = await focusedElement.evaluate(el => 
        getComputedStyle(el).borderColor || getComputedStyle(el).outlineColor
      );
      
      // Should have some form of visual distinction
      expect(borderColor).not.toBe('rgba(0, 0, 0, 0)');
      expect(borderColor).not.toBe('transparent');
      
      await cliHelper.takeWorkflowScreenshot('focus-styling-verification');
    });
  });

  test.describe('Accessibility and Error Handling', () => {
    test('should handle invalid key combinations gracefully', async ({ page }) => {
      // Test invalid sequences that shouldn't trigger actions
      await page.keyboard.press('g');
      await page.keyboard.press('x'); // Invalid combination
      await page.waitForTimeout(1000);
      
      // Should not cause any errors or changes
      await expect(page.locator('.error')).not.toBeVisible();
      
      await cliHelper.takeWorkflowScreenshot('invalid-key-handling');
    });

    test('should be accessible via screen readers', async ({ page }) => {
      // Check for proper ARIA labels and roles
      const commandPalette = page.locator('[role="dialog"]');
      
      await cliHelper.openCommandPalette();
      
      // Command palette should have proper accessibility attributes
      await expect(commandPalette).toHaveAttribute('role', 'dialog');
      
      // Input should have label
      const paletteInput = page.locator('[role="dialog"] input');
      const ariaLabel = await paletteInput.getAttribute('aria-label') || 
                       await paletteInput.getAttribute('placeholder');
      expect(ariaLabel).toBeTruthy();
      
      await cliHelper.closeCommandPalette();
    });

    test('should maintain keyboard focus properly', async ({ page }) => {
      // Test that focus is managed correctly through workflows
      await cliHelper.openCommandPalette();
      
      // Focus should be in the command palette input
      const activeElement = await page.evaluate(() => document.activeElement?.tagName);
      expect(activeElement).toBe('INPUT');
      
      await cliHelper.closeCommandPalette();
      
      // Focus should return to body or main content
      const newActiveElement = await page.evaluate(() => document.activeElement?.tagName);
      expect(['BODY', 'DIV', 'MAIN']).toContain(newActiveElement);
      
      await cliHelper.takeWorkflowScreenshot('focus-management-test');
    });
  });

  test.describe('Integration with KHIVE System', () => {
    test('should connect to KHIVE daemon and display status', async ({ page }) => {
      // Wait for WebSocket connection
      await page.waitForTimeout(2000);
      
      // Check for connection status indicator
      const connectionIndicator = page.locator('[data-testid="connection-status"], .connection-status');
      await expect(connectionIndicator).toBeVisible();
      
      await cliHelper.takeWorkflowScreenshot('khive-daemon-connection');
    });

    test('should display real-time session and agent data', async ({ page }) => {
      // Wait for data to load
      await page.waitForTimeout(3000);
      
      // Check that session data is displayed
      const sessionData = page.locator('[data-testid*="session"], .session-display');
      const sessionCount = await sessionData.count();
      expect(sessionCount).toBeGreaterThan(0);
      
      // Check that agent data is displayed
      const agentData = page.locator('[data-testid*="agent"], .agent-display');
      const agentCount = await agentData.count();
      expect(agentCount).toBeGreaterThan(0);
      
      await cliHelper.takeWorkflowScreenshot('real-time-data-display');
    });

    test('should handle command execution through CLI interface', async ({ page }) => {
      await cliHelper.openCommandPalette();
      
      // Type and execute a KHIVE command
      await page.keyboard.type('khive daemon status');
      await page.waitForTimeout(300);
      
      // Should show the command in results
      const commandResult = page.locator('text="Daemon Status"');
      await expect(commandResult).toBeVisible();
      
      // Execute the command
      await page.keyboard.press('Enter');
      
      await cliHelper.takeWorkflowScreenshot('khive-command-execution');
      
      // Should close palette and potentially show results
      await page.waitForSelector('[role="dialog"]', { state: 'hidden' });
    });
  });
});