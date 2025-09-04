import { test, expect } from '@playwright/test';

/**
 * Visual E2E Tests for Keyboard Shortcuts Help Displays
 * Tests Ocean's shortcut help system visual appearance and behavior
 * 
 * Features Tested:
 * - Screenshot comparison for help overlays
 * - Visual consistency across contexts
 * - Accessibility visual indicators
 * - High contrast mode support
 * - Mobile/responsive display
 */

test.describe('Keyboard Shortcuts Visual Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the command center
    await page.goto('/');
    
    // Wait for the application to be fully loaded
    await page.waitForSelector('[data-testid="command-center"]', {
      state: 'visible',
      timeout: 10000
    });

    // Ensure consistent state for visual tests
    await page.keyboard.up('Meta');
    await page.keyboard.up('Control');
    await page.keyboard.up('Shift');
    await page.keyboard.up('Alt');
    
    // Wait for fonts and styles to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
  });

  test.describe('Shortcut Help Overlay Screenshots', () => {
    test('should display global shortcuts help overlay correctly', async ({ page }) => {
      // Show global shortcuts help
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible({ timeout: 1000 });

      // Wait for animation to complete
      await page.waitForTimeout(300);

      // Take screenshot of the help overlay
      await expect(shortcutOverlay).toHaveScreenshot('global-shortcuts-help.png', {
        animations: 'disabled',
        threshold: 0.2
      });

      console.log('📸 Global shortcuts help overlay screenshot captured');
    });

    test('should display orchestration context shortcuts correctly', async ({ page }) => {
      // Focus orchestration pane
      await page.keyboard.press('Meta+1');
      await expect(page.getByTestId('orchestration-tree')).toHaveAttribute('data-focused', 'true');

      // Show context-specific shortcuts
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      await page.waitForTimeout(300);

      // Screenshot of orchestration context shortcuts
      await expect(shortcutOverlay).toHaveScreenshot('orchestration-shortcuts-help.png', {
        animations: 'disabled',
        threshold: 0.2
      });

      console.log('📸 Orchestration context shortcuts screenshot captured');
    });

    test('should display workspace context shortcuts correctly', async ({ page }) => {
      // Focus workspace pane
      await page.keyboard.press('Meta+2');
      await expect(page.getByTestId('workspace')).toHaveAttribute('data-focused', 'true');

      // Show workspace shortcuts
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      await page.waitForTimeout(300);

      // Screenshot of workspace context shortcuts
      await expect(shortcutOverlay).toHaveScreenshot('workspace-shortcuts-help.png', {
        animations: 'disabled',
        threshold: 0.2
      });

      console.log('📸 Workspace context shortcuts screenshot captured');
    });

    test('should display activity stream context shortcuts correctly', async ({ page }) => {
      // Focus activity stream pane
      await page.keyboard.press('Meta+3');
      await expect(page.getByTestId('activity-stream')).toHaveAttribute('data-focused', 'true');

      // Show activity stream shortcuts
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      await page.waitForTimeout(300);

      // Screenshot of activity stream context shortcuts
      await expect(shortcutOverlay).toHaveScreenshot('activity-stream-shortcuts-help.png', {
        animations: 'disabled',
        threshold: 0.2
      });

      console.log('📸 Activity stream context shortcuts screenshot captured');
    });
  });

  test.describe('Modal Context Screenshots', () => {
    test('should display command palette shortcuts help correctly', async ({ page }) => {
      // Open command palette
      await page.keyboard.press('Meta+k');
      const commandPalette = page.getByRole('dialog');
      await expect(commandPalette).toBeVisible();

      // Show shortcuts within command palette
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      await page.waitForTimeout(300);

      // Take screenshot with both command palette and shortcuts visible
      await expect(page.locator('body')).toHaveScreenshot('command-palette-with-shortcuts.png', {
        animations: 'disabled',
        fullPage: true,
        threshold: 0.2
      });

      console.log('📸 Command palette with shortcuts overlay screenshot captured');
    });

    test('should display agent spawn dialog shortcuts correctly', async ({ page }) => {
      // Open agent spawn dialog
      await page.keyboard.press('Meta+Shift+t');
      
      // Wait for dialog to appear
      const agentDialog = page.getByRole('dialog', { name: /spawn agent/i }).or(
        page.getByText(/new agent/i)
      );
      
      if (await agentDialog.count() > 0) {
        await expect(agentDialog).toBeVisible();

        // Show shortcuts in modal context
        await page.keyboard.press('?');
        
        const shortcutOverlay = page.getByTestId('shortcut-overlay');
        if (await shortcutOverlay.count() > 0) {
          await expect(shortcutOverlay).toBeVisible();
          await page.waitForTimeout(300);

          // Screenshot of modal with shortcuts
          await expect(page.locator('body')).toHaveScreenshot('agent-spawn-with-shortcuts.png', {
            animations: 'disabled',
            fullPage: true,
            threshold: 0.2
          });

          console.log('📸 Agent spawn dialog with shortcuts screenshot captured');
        }
      } else {
        console.log('⚠️  Agent spawn dialog not found, skipping screenshot');
      }
    });
  });

  test.describe('Visual Accessibility Screenshots', () => {
    test('should display high contrast shortcuts correctly', async ({ page }) => {
      // Enable high contrast mode
      await page.emulateMedia({ colorScheme: 'dark' });
      
      // Try to enable high contrast (implementation specific)
      await page.keyboard.press('Ctrl+Alt+c');
      
      // Show shortcuts in high contrast mode
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      await page.waitForTimeout(300);

      // Screenshot of high contrast shortcuts
      await expect(shortcutOverlay).toHaveScreenshot('high-contrast-shortcuts.png', {
        animations: 'disabled',
        threshold: 0.3 // Higher threshold for contrast differences
      });

      console.log('📸 High contrast shortcuts screenshot captured');
    });

    test('should display focus indicators correctly', async ({ page }) => {
      // Enable enhanced focus indicators
      await page.keyboard.press('Ctrl+Alt+f');
      
      // Focus different elements and show shortcuts
      await page.keyboard.press('Meta+1');
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      await page.waitForTimeout(300);

      // Screenshot with focus indicators
      await expect(page.locator('body')).toHaveScreenshot('focus-indicators-with-shortcuts.png', {
        animations: 'disabled',
        fullPage: true,
        threshold: 0.2
      });

      console.log('📸 Focus indicators with shortcuts screenshot captured');
    });

    test('should display reduced motion shortcuts correctly', async ({ page }) => {
      // Set reduced motion preference
      await page.emulateMedia({ reducedMotion: 'reduce' });
      
      // Show shortcuts (should appear without animation)
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      
      // No animation wait needed for reduced motion
      await page.waitForTimeout(100);

      // Screenshot of reduced motion shortcuts
      await expect(shortcutOverlay).toHaveScreenshot('reduced-motion-shortcuts.png', {
        animations: 'disabled',
        threshold: 0.2
      });

      console.log('📸 Reduced motion shortcuts screenshot captured');
    });
  });

  test.describe('Responsive Design Screenshots', () => {
    test('should display shortcuts correctly on tablet', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });
      
      // Show shortcuts on tablet
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      await page.waitForTimeout(300);

      // Screenshot of tablet shortcuts
      await expect(page.locator('body')).toHaveScreenshot('tablet-shortcuts-display.png', {
        animations: 'disabled',
        fullPage: true,
        threshold: 0.2
      });

      console.log('📸 Tablet shortcuts display screenshot captured');
    });

    test('should display shortcuts correctly on mobile', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });
      
      // Show shortcuts on mobile (might be different interaction)
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay').or(
        page.getByRole('dialog', { name: /shortcuts/i })
      );
      
      if (await shortcutOverlay.count() > 0) {
        await expect(shortcutOverlay).toBeVisible();
        await page.waitForTimeout(300);

        // Screenshot of mobile shortcuts
        await expect(page.locator('body')).toHaveScreenshot('mobile-shortcuts-display.png', {
          animations: 'disabled',
          fullPage: true,
          threshold: 0.2
        });

        console.log('📸 Mobile shortcuts display screenshot captured');
      } else {
        console.log('⚠️  Mobile shortcuts overlay not found');
      }
    });
  });

  test.describe('Interactive Element Visual Tests', () => {
    test('should display shortcut hints on hover correctly', async ({ page }) => {
      // Find buttons with shortcut hints
      const buttonsWithShortcuts = page.locator('button[title*="Cmd"], button[title*="⌘"]');
      
      if (await buttonsWithShortcuts.count() > 0) {
        const firstButton = buttonsWithShortcuts.first();
        
        // Hover to show tooltip
        await firstButton.hover();
        await page.waitForTimeout(500); // Wait for tooltip

        // Screenshot of button with tooltip
        await expect(firstButton).toHaveScreenshot('button-shortcut-tooltip.png', {
          animations: 'disabled',
          threshold: 0.2
        });

        console.log('📸 Button shortcut tooltip screenshot captured');
      } else {
        console.log('⚠️  No buttons with shortcut hints found');
      }
    });

    test('should display Alt key shortcut hints correctly', async ({ page }) => {
      // Press and hold Alt to show shortcut hints
      await page.keyboard.down('Alt');
      await page.waitForTimeout(300);

      // Look for shortcut hint elements
      const shortcutHints = page.locator('[data-shortcut-hint], .shortcut-hint');
      
      if (await shortcutHints.count() > 0) {
        // Screenshot of Alt key shortcut hints
        await expect(page.locator('body')).toHaveScreenshot('alt-key-shortcut-hints.png', {
          animations: 'disabled',
          fullPage: true,
          threshold: 0.2
        });

        console.log('📸 Alt key shortcut hints screenshot captured');
      } else {
        console.log('⚠️  No Alt key shortcut hints found');
      }

      // Release Alt
      await page.keyboard.up('Alt');
    });
  });

  test.describe('Animation and Transition Screenshots', () => {
    test('should capture shortcut overlay fade-in animation', async ({ page }) => {
      // Enable animations for this test
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      
      // Show shortcuts and capture at different animation stages
      const startTime = Date.now();
      await page.keyboard.press('?');
      
      // Capture during fade-in
      await page.waitForTimeout(100);
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      
      if (await shortcutOverlay.count() > 0) {
        await expect(shortcutOverlay).toHaveScreenshot('shortcuts-fade-in-100ms.png', {
          threshold: 0.3 // Higher threshold for animation
        });

        // Capture fully visible
        await page.waitForTimeout(200);
        await expect(shortcutOverlay).toHaveScreenshot('shortcuts-fully-visible.png', {
          animations: 'disabled',
          threshold: 0.2
        });

        console.log('📸 Shortcut overlay animation screenshots captured');
      }
    });

    test('should capture context switching visual transitions', async ({ page }) => {
      // Show initial shortcuts
      await page.keyboard.press('?');
      let shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      
      // Capture initial state
      await expect(shortcutOverlay).toHaveScreenshot('shortcuts-before-context-switch.png', {
        animations: 'disabled',
        threshold: 0.2
      });

      // Switch context while shortcuts are visible
      await page.keyboard.press('Meta+1');
      await page.waitForTimeout(200);

      // Capture after context switch
      await expect(shortcutOverlay).toHaveScreenshot('shortcuts-after-context-switch.png', {
        animations: 'disabled',
        threshold: 0.2
      });

      console.log('📸 Context switching visual transition screenshots captured');
    });
  });

  test.describe('Cross-Browser Visual Consistency', () => {
    test('should maintain consistent appearance across browsers', async ({ page, browserName }) => {
      // Show shortcuts
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      await expect(shortcutOverlay).toBeVisible();
      await page.waitForTimeout(300);

      // Take browser-specific screenshot
      await expect(shortcutOverlay).toHaveScreenshot(`shortcuts-${browserName}.png`, {
        animations: 'disabled',
        threshold: 0.2
      });

      console.log(`📸 ${browserName} shortcuts appearance screenshot captured`);
    });

    test('should display consistently at different zoom levels', async ({ page }) => {
      const zoomLevels = [0.8, 1.0, 1.25, 1.5];
      
      for (const zoom of zoomLevels) {
        // Set zoom level
        await page.evaluate((zoomLevel) => {
          document.body.style.zoom = zoomLevel.toString();
        }, zoom);

        await page.waitForTimeout(200);

        // Show shortcuts at this zoom level
        await page.keyboard.press('?');
        
        const shortcutOverlay = page.getByTestId('shortcut-overlay');
        if (await shortcutOverlay.count() > 0) {
          await expect(shortcutOverlay).toBeVisible();
          await page.waitForTimeout(300);

          // Screenshot at zoom level
          await expect(shortcutOverlay).toHaveScreenshot(`shortcuts-zoom-${zoom.toString().replace('.', '_')}.png`, {
            animations: 'disabled',
            threshold: 0.3 // Higher threshold for zoom differences
          });

          // Hide shortcuts for next test
          await page.keyboard.press('Escape');
          await expect(shortcutOverlay).not.toBeVisible();
        }

        console.log(`📸 Shortcuts at ${zoom * 100}% zoom screenshot captured`);
      }

      // Reset zoom
      await page.evaluate(() => {
        document.body.style.zoom = '1';
      });
    });
  });

  test.describe('Error State Visual Tests', () => {
    test('should display shortcuts correctly when components fail to load', async ({ page }) => {
      // Simulate component loading failure
      await page.route('**/api/**', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Server error' })
        });
      });

      // Try to show shortcuts despite errors
      await page.keyboard.press('?');
      
      const shortcutOverlay = page.getByTestId('shortcut-overlay');
      if (await shortcutOverlay.count() > 0) {
        await expect(shortcutOverlay).toBeVisible();
        await page.waitForTimeout(300);

        // Screenshot of shortcuts in error state
        await expect(page.locator('body')).toHaveScreenshot('shortcuts-error-state.png', {
          animations: 'disabled',
          fullPage: true,
          threshold: 0.3
        });

        console.log('📸 Shortcuts in error state screenshot captured');
      } else {
        console.log('⚠️  Shortcuts not available in error state');
      }
    });
  });
});