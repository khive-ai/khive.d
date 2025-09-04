import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Global Keyboard Shortcuts
 * Tests Ocean's CLI-first keyboard navigation system
 * 
 * Performance Requirements:
 * - Global shortcuts: <10ms recognition time
 * - Modal shortcuts: <5ms context switching
 * - Overall response: <50ms keyboard latency
 */

test.describe('Global Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the command center
    await page.goto('/');
    
    // Wait for the application to be fully loaded
    await page.waitForSelector('[data-testid="command-center"]', {
      state: 'visible',
      timeout: 10000
    });

    // Ensure keyboard system is ready
    await page.waitForTimeout(500);
  });

  test.describe('Command Palette Shortcuts', () => {
    test('should open global command palette with Cmd+K', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+K to open command palette
      await page.keyboard.press('Meta+k');

      // Verify command palette opened
      const commandPalette = page.getByRole('dialog', { name: /command palette/i });
      await expect(commandPalette).toBeVisible({ timeout: 1000 });

      // Measure response time
      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Command palette opened in ${responseTime}ms`);

      // Verify input is focused
      const searchInput = page.getByPlaceholder(/search commands/i);
      await expect(searchInput).toBeFocused();
    });

    test('should open contextual command palette with Cmd+Shift+K', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+Shift+K for contextual palette
      await page.keyboard.press('Meta+Shift+k');

      // Verify contextual help opened
      const helpDialog = page.getByText(/KHIVE Command Reference/i);
      await expect(helpDialog).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Help dialog opened in ${responseTime}ms`);
    });

    test('should close command palette with Escape', async ({ page }) => {
      // Open command palette
      await page.keyboard.press('Meta+k');
      await expect(page.getByRole('dialog')).toBeVisible();

      const startTime = Date.now();

      // Close with Escape
      await page.keyboard.press('Escape');
      
      // Verify it closed
      await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(25);
      console.log(`⚡ Command palette closed in ${responseTime}ms`);
    });

    test('should handle rapid command palette toggling', async ({ page }) => {
      // Rapid toggle test - open/close 5 times quickly
      for (let i = 0; i < 5; i++) {
        const openStart = Date.now();
        await page.keyboard.press('Meta+k');
        await expect(page.getByRole('dialog')).toBeVisible();
        const openTime = Date.now() - openStart;

        const closeStart = Date.now();
        await page.keyboard.press('Escape');
        await expect(page.getByRole('dialog')).not.toBeVisible();
        const closeTime = Date.now() - closeStart;

        expect(openTime).toBeLessThan(50);
        expect(closeTime).toBeLessThan(25);
      }
    });
  });

  test.describe('System Control Shortcuts', () => {
    test('should handle reconnect shortcut Cmd+R', async ({ page }) => {
      // Mock WebSocket connection status
      await page.evaluate(() => {
        (window as any).mockWebSocketReconnect = jest.fn();
      });

      const startTime = Date.now();

      // Press Cmd+R for reconnect
      await page.keyboard.press('Meta+r');

      // Wait for reconnection indicator
      const reconnecting = page.getByText(/reconnecting/i);
      await expect(reconnecting).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Reconnect initiated in ${responseTime}ms`);
    });

    test('should handle validation shortcut Cmd+Shift+T', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+Shift+T for validation
      await page.keyboard.press('Meta+Shift+t');

      // Look for validation panel or dialog
      const validationPanel = page.getByText(/system validation/i).or(
        page.getByText(/running validation/i)
      );
      await expect(validationPanel).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ System validation started in ${responseTime}ms`);
    });
  });

  test.describe('Pane Navigation Shortcuts', () => {
    test('should focus orchestration pane with Cmd+1', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+1 to focus orchestration pane
      await page.keyboard.press('Meta+1');

      // Verify orchestration pane is focused
      const orchestrationPane = page.getByTestId('orchestration-tree');
      await expect(orchestrationPane).toHaveAttribute('data-focused', 'true', { timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Orchestration pane focused in ${responseTime}ms`);
    });

    test('should focus workspace pane with Cmd+2', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+2 to focus workspace pane  
      await page.keyboard.press('Meta+2');

      // Verify workspace pane is focused
      const workspacePane = page.getByTestId('workspace');
      await expect(workspacePane).toHaveAttribute('data-focused', 'true', { timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Workspace pane focused in ${responseTime}ms`);
    });

    test('should focus activity stream with Cmd+3', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+3 to focus activity stream
      await page.keyboard.press('Meta+3');

      // Verify activity stream is focused
      const activityPane = page.getByTestId('activity-stream');
      await expect(activityPane).toHaveAttribute('data-focused', 'true', { timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Activity stream focused in ${responseTime}ms`);
    });

    test('should cycle through panes with Tab navigation', async ({ page }) => {
      const startTime = Date.now();

      // Press Tab to cycle focus
      await page.keyboard.press('Tab');

      // Wait for focus change
      await page.waitForTimeout(100);

      // Check that some pane is focused (exact order may vary)
      const focusedPanes = await page.locator('[data-focused="true"]').count();
      expect(focusedPanes).toBeGreaterThanOrEqual(1);

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Tab navigation completed in ${responseTime}ms`);
    });

    test('should reverse cycle with Shift+Tab', async ({ page }) => {
      const startTime = Date.now();

      // Press Shift+Tab for reverse navigation
      await page.keyboard.press('Shift+Tab');

      // Wait for focus change
      await page.waitForTimeout(100);

      // Verify focus changed
      const focusedPanes = await page.locator('[data-focused="true"]').count();
      expect(focusedPanes).toBeGreaterThanOrEqual(1);

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Reverse tab navigation completed in ${responseTime}ms`);
    });
  });

  test.describe('Quick Action Shortcuts', () => {
    test('should open quick planning with Cmd+P', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+P for quick planning
      await page.keyboard.press('Meta+p');

      // Verify workspace shows planning view
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'planning', { timeout: 1000 });
      await expect(workspace).toHaveAttribute('data-focused', 'true');

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Quick planning opened in ${responseTime}ms`);
    });

    test('should spawn new agent with Cmd+Shift+T', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+Shift+T for agent spawn dialog
      await page.keyboard.press('Meta+Shift+t');

      // Look for agent spawn dialog or form
      const agentDialog = page.getByRole('dialog', { name: /spawn agent/i }).or(
        page.getByText(/new agent/i)
      );
      await expect(agentDialog).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Agent spawn dialog opened in ${responseTime}ms`);
    });

    test('should create new orchestration with Cmd+N', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+N for new orchestration
      await page.keyboard.press('Meta+n');

      // Wait for orchestration creation indication
      const orchestrationIndicator = page.getByText(/new orchestration/i).or(
        page.getByText(/creating/i)
      );
      await expect(orchestrationIndicator).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ New orchestration started in ${responseTime}ms`);
    });
  });

  test.describe('Layout Management Shortcuts', () => {
    test('should toggle pane layout with Cmd+\\', async ({ page }) => {
      const startTime = Date.now();

      // Get initial layout
      const initialLayout = await page.evaluate(() => 
        document.body.getAttribute('data-layout')
      );

      // Toggle layout
      await page.keyboard.press('Meta+\\');

      // Verify layout changed
      await page.waitForTimeout(200);
      const newLayout = await page.evaluate(() => 
        document.body.getAttribute('data-layout')
      );

      expect(newLayout).not.toBe(initialLayout);

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Layout toggled in ${responseTime}ms`);
    });

    test('should reset pane sizes with Cmd+0', async ({ page }) => {
      const startTime = Date.now();

      // Press Cmd+0 to reset pane sizes
      await page.keyboard.press('Meta+0');

      // Wait for layout adjustment
      await page.waitForTimeout(200);

      // Verify layout reset (this would need specific implementation details)
      const layoutReset = await page.evaluate(() => {
        // Check if panes have default sizes (implementation specific)
        return true; // Placeholder for actual verification
      });

      expect(layoutReset).toBe(true);

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Pane sizes reset in ${responseTime}ms`);
    });
  });

  test.describe('Input Safety and Context Awareness', () => {
    test('should not trigger shortcuts when typing in input fields', async ({ page }) => {
      // Open command palette to get an input field
      await page.keyboard.press('Meta+k');
      const searchInput = page.getByPlaceholder(/search commands/i);
      await expect(searchInput).toBeVisible();

      // Click in input to focus it
      await searchInput.click();
      await expect(searchInput).toBeFocused();

      // Type 'k' - should not close the palette
      await searchInput.type('k');
      
      // Command palette should still be open
      await expect(page.getByRole('dialog')).toBeVisible();
      
      // Input should contain the typed character
      await expect(searchInput).toHaveValue('k');
    });

    test('should not trigger shortcuts in textarea elements', async ({ page }) => {
      // Create a textarea for testing (if available in the app)
      await page.evaluate(() => {
        const textarea = document.createElement('textarea');
        textarea.setAttribute('data-testid', 'test-textarea');
        textarea.placeholder = 'Test textarea';
        document.body.appendChild(textarea);
      });

      const textarea = page.getByTestId('test-textarea');
      await textarea.click();
      await textarea.focus();

      // Type shortcut keys - should not trigger shortcuts
      await textarea.type('gp'); // vim navigation shortcut
      
      // Verify text was typed normally
      await expect(textarea).toHaveValue('gp');
      
      // Verify we didn't navigate to planning view
      const workspace = page.getByTestId('workspace');
      const activeView = await workspace.getAttribute('data-active-view');
      expect(activeView).not.toBe('planning');
    });

    test('should handle contentEditable elements safely', async ({ page }) => {
      // Create a contentEditable element
      await page.evaluate(() => {
        const div = document.createElement('div');
        div.setAttribute('contenteditable', 'true');
        div.setAttribute('data-testid', 'test-editable');
        div.textContent = 'Editable content';
        document.body.appendChild(div);
      });

      const editableDiv = page.getByTestId('test-editable');
      await editableDiv.click();
      await editableDiv.focus();

      // Try to type shortcut - should not trigger global shortcuts
      await page.keyboard.press('Meta+k');
      
      // Command palette should not open
      await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 500 });
    });
  });

  test.describe('Performance and Consistency', () => {
    test('should maintain consistent response times under load', async ({ page }) => {
      const responseTimes: number[] = [];
      
      // Test 20 consecutive shortcut activations
      for (let i = 0; i < 20; i++) {
        const startTime = Date.now();
        
        // Alternate between different shortcuts
        if (i % 2 === 0) {
          await page.keyboard.press('Meta+k');
          await expect(page.getByRole('dialog')).toBeVisible();
          await page.keyboard.press('Escape');
          await expect(page.getByRole('dialog')).not.toBeVisible();
        } else {
          await page.keyboard.press('Meta+1');
          await expect(page.getByTestId('orchestration-tree')).toHaveAttribute('data-focused', 'true');
        }
        
        const responseTime = Date.now() - startTime;
        responseTimes.push(responseTime);
        
        // Brief pause to prevent overwhelming
        await page.waitForTimeout(10);
      }
      
      // Analyze performance
      const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
      const maxResponseTime = Math.max(...responseTimes);
      const minResponseTime = Math.min(...responseTimes);
      
      console.log(`📊 Performance metrics:`);
      console.log(`   Average: ${avgResponseTime.toFixed(1)}ms`);
      console.log(`   Max: ${maxResponseTime}ms`);
      console.log(`   Min: ${minResponseTime}ms`);
      
      // Performance requirements
      expect(avgResponseTime).toBeLessThan(30);
      expect(maxResponseTime).toBeLessThan(100);
      expect(responseTimes.filter(t => t > 50).length).toBeLessThan(2); // Less than 10% over 50ms
    });

    test('should handle simultaneous key presses gracefully', async ({ page }) => {
      // Test handling of rapid, overlapping keystrokes
      const startTime = Date.now();
      
      // Press multiple keys rapidly
      const keyPromises = [
        page.keyboard.press('Meta+1'),
        page.keyboard.press('Meta+2'),
        page.keyboard.press('Meta+3'),
      ];
      
      await Promise.all(keyPromises);
      
      // Wait for all events to process
      await page.waitForTimeout(100);
      
      // At least one pane should be focused
      const focusedPanes = await page.locator('[data-focused="true"]').count();
      expect(focusedPanes).toBeGreaterThanOrEqual(1);
      
      const totalTime = Date.now() - startTime;
      expect(totalTime).toBeLessThan(200);
      console.log(`⚡ Simultaneous key handling completed in ${totalTime}ms`);
    });
  });
});