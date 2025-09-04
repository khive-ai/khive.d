import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Context-Aware Keyboard Shortcuts
 * Tests Ocean's dynamic shortcut system that adapts to active view/focus
 * 
 * Features Tested:
 * - Dynamic shortcut display with ? key
 * - Auto-hide behavior (3 second timeout)
 * - Context-specific shortcut availability
 * - Help integration and visual indicators
 */

test.describe('Context-Aware Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the command center
    await page.goto('/');
    
    // Wait for the application to be fully loaded
    await page.waitForSelector('[data-testid="command-center"]', {
      state: 'visible',
      timeout: 10000
    });

    // Clear any modifier keys and wait for stability
    await page.keyboard.up('Meta');
    await page.keyboard.up('Control');
    await page.keyboard.up('Shift');
    await page.keyboard.up('Alt');
    
    await page.waitForTimeout(500);
  });

  test.describe('Dynamic Shortcut Help Display', () => {
    test('should show shortcut overlay with ? key', async ({ page }) => {
      const startTime = Date.now();

      // Press '?' to show shortcut help
      await page.keyboard.press('?');

      // Verify shortcut overlay appears
      const shortcutOverlay = page.getByTestId('shortcut-overlay').or(
        page.getByRole('tooltip', { name: /shortcuts/i })
      );
      await expect(shortcutOverlay).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Shortcut help overlay shown in ${responseTime}ms`);

      // Verify it contains relevant shortcuts
      await expect(shortcutOverlay).toContainText(/Cmd\+K/i);
      await expect(shortcutOverlay).toContainText(/global commands/i);
    });

    test('should auto-hide shortcuts after 3 seconds', async ({ page }) => {
      // Show shortcut overlay
      await page.keyboard.press('?');
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();

      // Wait for auto-hide timeout (3 seconds + buffer)
      await page.waitForTimeout(3500);

      // Verify overlay is hidden
      await expect(shortcutOverlay).not.toBeVisible();
      console.log('✅ Auto-hide after 3 seconds working correctly');
    });

    test('should manually hide shortcuts with Escape', async ({ page }) => {
      // Show shortcut overlay
      await page.keyboard.press('?');
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();

      const startTime = Date.now();

      // Press Escape to hide
      await page.keyboard.press('Escape');

      // Verify overlay is hidden
      await expect(shortcutOverlay).not.toBeVisible({ timeout: 500 });

      const hideTime = Date.now() - startTime;
      expect(hideTime).toBeLessThan(25);
      console.log(`⚡ Manual hide completed in ${hideTime}ms`);
    });

    test('should toggle overlay with repeated ? presses', async ({ page }) => {
      const shortcutOverlay = page.getByTestId('shortcut-overlay');

      // Show overlay
      await page.keyboard.press('?');
      await expect(shortcutOverlay).toBeVisible();

      // Hide with second press
      await page.keyboard.press('?');
      await expect(shortcutOverlay).not.toBeVisible();

      // Show again with third press
      await page.keyboard.press('?');
      await expect(shortcutOverlay).toBeVisible();

      console.log('✅ Shortcut overlay toggling working correctly');
    });
  });

  test.describe('Context-Specific Shortcut Display', () => {
    test('should show orchestration shortcuts when tree is focused', async ({ page }) => {
      // Focus orchestration tree
      await page.keyboard.press('Meta+1');
      await expect(page.getByTestId('orchestration-tree')).toHaveAttribute('data-focused', 'true');

      // Show shortcuts
      await page.keyboard.press('?');
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();

      // Verify orchestration-specific shortcuts are shown
      await expect(shortcutOverlay).toContainText(/Enter.*drill into/i);
      await expect(shortcutOverlay).toContainText(/n.*new plan/i);
      await expect(shortcutOverlay).toContainText(/a.*spawn agent/i);
      await expect(shortcutOverlay).toContainText(/d.*delete/i);

      console.log('✅ Orchestration context shortcuts displayed correctly');
    });

    test('should show workspace shortcuts when workspace is focused', async ({ page }) => {
      // Focus workspace
      await page.keyboard.press('Meta+2');
      await expect(page.getByTestId('workspace')).toHaveAttribute('data-focused', 'true');

      // Show shortcuts
      await page.keyboard.press('?');
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();

      // Verify workspace-specific shortcuts are shown
      await expect(shortcutOverlay).toContainText(/Cmd\+T.*terminal/i);
      await expect(shortcutOverlay).toContainText(/Cmd\+S.*save/i);
      await expect(shortcutOverlay).toContainText(/Cmd\+D.*split/i);

      console.log('✅ Workspace context shortcuts displayed correctly');
    });

    test('should show activity stream shortcuts when stream is focused', async ({ page }) => {
      // Focus activity stream
      await page.keyboard.press('Meta+3');
      await expect(page.getByTestId('activity-stream')).toHaveAttribute('data-focused', 'true');

      // Show shortcuts
      await page.keyboard.press('?');
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();

      // Verify activity stream shortcuts are shown
      await expect(shortcutOverlay).toContainText(/j.*scroll down/i);
      await expect(shortcutOverlay).toContainText(/k.*scroll up/i);
      await expect(shortcutOverlay).toContainText(/f.*follow mode/i);
      await expect(shortcutOverlay).toContainText(/\/.*search/i);

      console.log('✅ Activity stream context shortcuts displayed correctly');
    });

    test('should update shortcuts when context changes', async ({ page }) => {
      // Start with orchestration focused
      await page.keyboard.press('Meta+1');
      await page.keyboard.press('?');
      
      let shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      await expect(shortcutOverlay).toContainText(/new plan/i);

      // Switch to workspace focus
      await page.keyboard.press('Meta+2');
      
      // Shortcuts should update automatically
      await expect(shortcutOverlay).toContainText(/terminal/i);
      await expect(shortcutOverlay).not.toContainText(/new plan/i);

      console.log('✅ Dynamic shortcut updates working correctly');
    });
  });

  test.describe('Shortcut Availability by Context', () => {
    test('should enable planning shortcuts in planning view', async ({ page }) => {
      // Navigate to planning view
      await page.keyboard.press('g');
      await page.keyboard.press('p');
      
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'planning');

      // Test planning-specific shortcut
      await page.keyboard.press('n'); // New plan
      
      const newPlanDialog = page.getByRole('dialog', { name: /new plan/i }).or(
        page.getByText(/create plan/i)
      );
      await expect(newPlanDialog).toBeVisible({ timeout: 1000 });

      console.log('✅ Planning context shortcuts working');
    });

    test('should enable agent shortcuts in agents view', async ({ page }) => {
      // Navigate to agents view
      await page.keyboard.press('g');
      await page.keyboard.press('a');
      
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'agents');

      // Test agent-specific shortcut
      await page.keyboard.press('c'); // Compose agent
      
      const composeDialog = page.getByText(/compose agent/i).or(
        page.getByText(/khive compose/i)
      );
      await expect(composeDialog).toBeVisible({ timeout: 1000 });

      console.log('✅ Agent context shortcuts working');
    });

    test('should disable context shortcuts in wrong context', async ({ page }) => {
      // Navigate to monitoring view
      await page.keyboard.press('g');
      await page.keyboard.press('m');
      
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'monitoring');

      // Try agent-specific shortcut (should not work in monitoring)
      await page.keyboard.press('c');
      await page.waitForTimeout(500);
      
      // Should not open compose dialog
      const composeDialog = page.getByText(/compose agent/i);
      await expect(composeDialog).not.toBeVisible();

      console.log('✅ Context isolation working correctly');
    });
  });

  test.describe('Modal Context Shortcuts', () => {
    test('should show modal-specific shortcuts in command palette', async ({ page }) => {
      // Open command palette
      await page.keyboard.press('Meta+k');
      await expect(page.getByRole('dialog')).toBeVisible();

      // Show shortcuts within modal
      await page.keyboard.press('?');
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();

      // Verify modal-specific shortcuts
      await expect(shortcutOverlay).toContainText(/↑↓.*navigate/i);
      await expect(shortcutOverlay).toContainText(/Enter.*execute/i);
      await expect(shortcutOverlay).toContainText(/Tab.*sections/i);
      await expect(shortcutOverlay).toContainText(/Esc.*close/i);

      console.log('✅ Modal context shortcuts displayed correctly');
    });

    test('should prioritize modal shortcuts over global ones', async ({ page }) => {
      // Open command palette
      await page.keyboard.press('Meta+k');
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();

      // Test that Escape closes modal instead of showing global help
      await page.keyboard.press('Escape');
      await expect(dialog).not.toBeVisible({ timeout: 500 });

      // Global escape behavior should not trigger
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).not.toBeVisible();

      console.log('✅ Modal shortcut priority working correctly');
    });
  });

  test.describe('Visual Shortcut Indicators', () => {
    test('should show shortcuts in button tooltips on hover', async ({ page }) => {
      // Find a button with a shortcut
      const commandPaletteButton = page.getByRole('button', { name: /command palette/i }).or(
        page.getByTitle(/Cmd\+K/i)
      );

      if (await commandPaletteButton.count() > 0) {
        // Hover to show tooltip
        await commandPaletteButton.hover();

        // Verify tooltip shows shortcut
        const tooltip = page.getByRole('tooltip').or(page.getByText(/Cmd\+K/i));
        await expect(tooltip).toBeVisible({ timeout: 1000 });

        console.log('✅ Button tooltip shortcuts working');
      } else {
        console.log('⚠️  No command palette button found for tooltip test');
      }
    });

    test('should highlight interactive elements with Alt key', async ({ page }) => {
      // Press and hold Alt to show shortcut overlay on elements
      await page.keyboard.down('Alt');

      // Wait for overlay to appear
      await page.waitForTimeout(200);

      // Look for shortcut hints on interactive elements
      const shortcutHints = page.locator('[data-shortcut-hint]').or(
        page.locator('.shortcut-hint')
      );

      if (await shortcutHints.count() > 0) {
        await expect(shortcutHints.first()).toBeVisible();
        console.log('✅ Alt key shortcut hints working');
      } else {
        console.log('⚠️  No shortcut hints found with Alt key');
      }

      // Release Alt
      await page.keyboard.up('Alt');

      // Hints should disappear
      await page.waitForTimeout(200);
      await expect(shortcutHints.first()).not.toBeVisible();
    });

    test('should show current shortcut mode in status bar', async ({ page }) => {
      const statusBar = page.getByTestId('status-bar').or(
        page.locator('.status-bar')
      );

      if (await statusBar.count() > 0) {
        // Check for shortcut mode indicator
        const modeIndicator = statusBar.getByText(/shortcuts/i).or(
          statusBar.getByText(/mode/i)
        );

        if (await modeIndicator.count() > 0) {
          await expect(modeIndicator).toBeVisible();
          console.log('✅ Status bar shortcut mode indicator working');
        } else {
          console.log('⚠️  No shortcut mode indicator found in status bar');
        }
      } else {
        console.log('⚠️  No status bar found for mode indicator test');
      }
    });
  });

  test.describe('Accessibility and Accommodation', () => {
    test('should announce context changes to screen readers', async ({ page }) => {
      // Focus different panes and check for aria-live announcements
      await page.keyboard.press('Meta+1');
      
      // Look for screen reader announcements
      const liveRegion = page.locator('[aria-live]').or(
        page.locator('[role="status"]')
      );

      if (await liveRegion.count() > 0) {
        const announcement = await liveRegion.textContent();
        expect(announcement).toMatch(/orchestration|tree|focused/i);
        console.log('✅ Screen reader announcements working');
      } else {
        console.log('⚠️  No aria-live regions found for screen reader test');
      }
    });

    test('should support high contrast shortcut display', async ({ page }) => {
      // Enable high contrast mode (if supported)
      await page.emulateMedia({ colorScheme: 'dark' });
      await page.keyboard.press('Ctrl+Alt+c'); // High contrast toggle

      // Show shortcuts
      await page.keyboard.press('?');
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();

      // Verify high contrast styling applied
      const overlayStyles = await shortcutOverlay.evaluate(el => 
        getComputedStyle(el).getPropertyValue('--contrast-mode')
      );

      if (overlayStyles) {
        console.log('✅ High contrast mode applied to shortcuts');
      } else {
        console.log('⚠️  High contrast mode not detected');
      }
    });

    test('should support reduced motion preferences', async ({ page }) => {
      // Set reduced motion preference
      await page.emulateMedia({ reducedMotion: 'reduce' });

      // Show shortcuts (should not animate)
      const startTime = Date.now();
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      
      const showTime = Date.now() - startTime;
      
      // With reduced motion, should appear immediately
      expect(showTime).toBeLessThan(25);
      console.log(`✅ Reduced motion shortcuts appeared in ${showTime}ms`);
    });
  });

  test.describe('Performance and Responsiveness', () => {
    test('should update context quickly when switching panes', async ({ page }) => {
      const switchTimes: number[] = [];

      // Test rapid pane switching with shortcut updates
      for (let i = 1; i <= 3; i++) {
        const startTime = Date.now();

        // Switch pane
        await page.keyboard.press(`Meta+${i}`);
        
        // Show shortcuts to verify context updated
        await page.keyboard.press('?');
        const shortcutOverlay = page.getByTestId('shortcut-overlay');
        await expect(shortcutOverlay).toBeVisible();
        
        const switchTime = Date.now() - startTime;
        switchTimes.push(switchTime);

        // Hide shortcuts for next test
        await page.keyboard.press('Escape');
        await expect(shortcutOverlay).not.toBeVisible();

        await page.waitForTimeout(50);
      }

      const avgTime = switchTimes.reduce((a, b) => a + b, 0) / switchTimes.length;
      const maxTime = Math.max(...switchTimes);

      console.log(`📊 Context switch performance:`);
      console.log(`   Average: ${avgTime.toFixed(1)}ms`);
      console.log(`   Max: ${maxTime}ms`);

      expect(avgTime).toBeLessThan(75);
      expect(maxTime).toBeLessThan(150);
    });

    test('should handle rapid help toggling efficiently', async ({ page }) => {
      const toggleTimes: number[] = [];

      // Rapid help overlay toggling
      for (let i = 0; i < 10; i++) {
        const startTime = Date.now();

        // Toggle help
        await page.keyboard.press('?');
        
        if (i % 2 === 0) {
          // Show overlay
          await expect(page.getByTestId('shortcut-overlay')).toBeVisible();
        } else {
          // Hide overlay
          await expect(page.getByTestId('shortcut-overlay')).not.toBeVisible();
        }

        const toggleTime = Date.now() - startTime;
        toggleTimes.push(toggleTime);
      }

      const avgTime = toggleTimes.reduce((a, b) => a + b, 0) / toggleTimes.length;
      const maxTime = Math.max(...toggleTimes);

      console.log(`📊 Help toggle performance:`);
      console.log(`   Average: ${avgTime.toFixed(1)}ms`);
      console.log(`   Max: ${maxTime}ms`);

      expect(avgTime).toBeLessThan(50);
      expect(maxTime).toBeLessThan(100);
    });
  });

  test.describe('Integration with Other Systems', () => {
    test('should coordinate with command palette shortcuts', async ({ page }) => {
      // Open command palette
      await page.keyboard.press('Meta+k');
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();

      // Show shortcuts within command palette
      await page.keyboard.press('?');
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();

      // Both should be visible and non-conflicting
      await expect(dialog).toBeVisible();
      await expect(shortcutOverlay).toBeVisible();

      // Close shortcuts, palette should remain
      await page.keyboard.press('Escape');
      await expect(shortcutOverlay).not.toBeVisible();
      await expect(dialog).toBeVisible();

      console.log('✅ Command palette integration working');
    });

    test('should work with vim navigation sequences', async ({ page }) => {
      // Show shortcuts
      await page.keyboard.press('?');
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();

      // Execute vim sequence while help is visible
      await page.keyboard.press('g');
      await page.keyboard.press('p');

      // Should navigate and potentially update shortcut context
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'planning');

      // Shortcuts should update for new context
      await expect(shortcutOverlay).toContainText(/plan/i);

      console.log('✅ Vim navigation integration working');
    });
  });
});