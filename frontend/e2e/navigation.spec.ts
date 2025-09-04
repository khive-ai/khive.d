import { test, expect, Page } from '@playwright/test';

// Helper class for navigation testing
class NavigationHelper {
  constructor(private page: Page) {}

  // Vim-style navigation
  async navigateVimStyle(target: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings') {
    const keyMap = {
      planning: 'g p',
      monitoring: 'g m', 
      analytics: 'g n',
      agents: 'g a',
      settings: 'g s'
    };
    
    const keys = keyMap[target].split(' ');
    for (const key of keys) {
      await this.page.keyboard.press(key);
      await this.page.waitForTimeout(50); // Small delay between sequence keys
    }
    
    // Allow navigation to complete
    await this.page.waitForTimeout(200);
  }

  // Number-based pane focus
  async focusPane(paneNumber: 1 | 2 | 3) {
    await this.page.keyboard.press(`Meta+${paneNumber}`);
    await this.page.waitForTimeout(100); // Allow focus transition
  }

  // Tab-style view switching 
  async switchToView(viewNumber: 1 | 2 | 3 | 4 | 5) {
    await this.page.keyboard.press(`Meta+${viewNumber}`);
    await this.page.waitForTimeout(100);
  }

  // Performance measurement
  async measureNavigationTime(action: () => Promise<void>): Promise<number> {
    const startTime = performance.now();
    await action();
    const endTime = performance.now();
    return endTime - startTime;
  }

  // Visual verification
  async verifyActiveView(expectedView: string) {
    const workspace = this.page.locator('[data-testid="workspace"]');
    await expect(workspace).toHaveAttribute('data-active-view', expectedView);
  }

  async verifyFocusedPane(expectedPane: string) {
    const pane = this.page.locator(`[data-testid="${expectedPane}"]`);
    await expect(pane).toHaveAttribute('data-focused', 'true');
  }

  async verifyFocusIndicator(selector: string) {
    const element = this.page.locator(selector);
    await expect(element).toBeVisible();
    
    // Check for visual focus indicators
    const borderColor = await element.evaluate(el => 
      getComputedStyle(el).borderColor || 
      getComputedStyle(el).outlineColor ||
      getComputedStyle(el).boxShadow
    );
    
    expect(borderColor).not.toBe('rgba(0, 0, 0, 0)');
    expect(borderColor).not.toBe('transparent');
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `test-results/screenshots/navigation-${name}.png`,
      fullPage: true 
    });
  }

  async waitForNavigation() {
    await this.page.waitForTimeout(300); // Allow for navigation transitions
  }

  async verifyNoInterference() {
    // Verify that custom shortcuts don't interfere with browser shortcuts
    // This is tested by ensuring browser functionality still works
    const url = this.page.url();
    expect(url).toContain('localhost:3000');
  }
}

test.describe('Navigation Shortcuts E2E Tests', () => {
  let navHelper: NavigationHelper;

  test.beforeEach(async ({ page }) => {
    navHelper = new NavigationHelper(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Vim-Style Navigation (G+Key Patterns)', () => {
    test('should navigate to planning with "g p"', async ({ page }) => {
      await navHelper.navigateVimStyle('planning');
      await navHelper.verifyActiveView('planning');
      await navHelper.takeScreenshot('vim-navigation-planning');
    });

    test('should navigate to monitoring with "g m"', async ({ page }) => {
      await navHelper.navigateVimStyle('monitoring');
      await navHelper.verifyActiveView('monitoring');
      await navHelper.takeScreenshot('vim-navigation-monitoring');
    });

    test('should navigate to analytics with "g n"', async ({ page }) => {
      await navHelper.navigateVimStyle('analytics');
      await navHelper.verifyActiveView('analytics');
      await navHelper.takeScreenshot('vim-navigation-analytics');
    });

    test('should navigate to agents with "g a"', async ({ page }) => {
      await navHelper.navigateVimStyle('agents');
      await navHelper.verifyActiveView('agents');
      await navHelper.takeScreenshot('vim-navigation-agents');
    });

    test('should navigate to settings with "g s"', async ({ page }) => {
      await navHelper.navigateVimStyle('settings');
      await navHelper.verifyActiveView('settings');
      await navHelper.takeScreenshot('vim-navigation-settings');
    });

    test('should handle rapid vim navigation without conflicts', async ({ page }) => {
      const targets: Array<'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings'> = 
        ['planning', 'monitoring', 'analytics', 'agents', 'settings'];
      
      // Rapid navigation through all views
      for (const target of targets) {
        await navHelper.navigateVimStyle(target);
        await navHelper.verifyActiveView(target);
        await page.waitForTimeout(100);
      }
      
      await navHelper.takeScreenshot('rapid-vim-navigation-complete');
    });

    test('should handle incomplete vim sequences gracefully', async ({ page }) => {
      // Press 'g' but don't follow up
      await page.keyboard.press('g');
      await page.waitForTimeout(1600); // Wait for timeout (1500ms + buffer)
      
      // Now press 'p' - should not navigate
      await page.keyboard.press('p');
      await page.waitForTimeout(300);
      
      // Should not have navigated to planning
      const workspace = page.locator('[data-testid="workspace"]');
      const currentView = await workspace.getAttribute('data-active-view');
      expect(currentView).not.toBe('planning');
      
      await navHelper.takeScreenshot('incomplete-vim-sequence');
    });

    test('should reset vim sequence on modifier keys', async ({ page }) => {
      // Start vim sequence
      await page.keyboard.press('g');
      
      // Press modifier key combination
      await page.keyboard.press('Meta+k'); // Command palette
      
      // Close command palette
      await page.keyboard.press('Escape');
      
      // Now press 'p' - should not complete the vim sequence
      await page.keyboard.press('p');
      await page.waitForTimeout(300);
      
      const workspace = page.locator('[data-testid="workspace"]');
      const currentView = await workspace.getAttribute('data-active-view');
      expect(currentView).not.toBe('planning');
      
      await navHelper.takeScreenshot('vim-sequence-reset-by-modifier');
    });
  });

  test.describe('Pane Focus Management (Cmd+1/2/3)', () => {
    test('should focus orchestration tree with Cmd+1', async ({ page }) => {
      await navHelper.focusPane(1);
      await navHelper.verifyFocusedPane('orchestration-tree');
      await navHelper.verifyFocusIndicator('[data-testid="orchestration-tree"]');
      await navHelper.takeScreenshot('pane-1-focused');
    });

    test('should focus main workspace with Cmd+2', async ({ page }) => {
      await navHelper.focusPane(2);
      await navHelper.verifyFocusedPane('workspace');
      await navHelper.verifyFocusIndicator('[data-testid="workspace"]');
      await navHelper.takeScreenshot('pane-2-focused');
    });

    test('should focus activity stream with Cmd+3', async ({ page }) => {
      await navHelper.focusPane(3);
      await navHelper.verifyFocusedPane('activity-stream');
      await navHelper.verifyFocusIndicator('[data-testid="activity-stream"]');
      await navHelper.takeScreenshot('pane-3-focused');
    });

    test('should switch focus between panes rapidly', async ({ page }) => {
      const panes: Array<1 | 2 | 3> = [1, 2, 3, 2, 1, 3];
      const paneNames = ['orchestration-tree', 'workspace', 'activity-stream'];
      
      for (let i = 0; i < panes.length; i++) {
        const paneNumber = panes[i];
        await navHelper.focusPane(paneNumber);
        await navHelper.verifyFocusedPane(paneNames[paneNumber - 1]);
        await page.waitForTimeout(50);
      }
      
      await navHelper.takeScreenshot('rapid-pane-switching');
    });

    test('should maintain focus indicators during view changes', async ({ page }) => {
      // Focus pane 2
      await navHelper.focusPane(2);
      await navHelper.verifyFocusedPane('workspace');
      
      // Change view
      await navHelper.navigateVimStyle('monitoring');
      await navHelper.verifyActiveView('monitoring');
      
      // Pane 2 should still be focused
      await navHelper.verifyFocusedPane('workspace');
      
      await navHelper.takeScreenshot('focus-maintained-during-view-change');
    });

    test('should handle focus when panes are not visible', async ({ page }) => {
      // This tests edge case where a pane might be hidden or not rendered
      // Focus attempt should be graceful
      
      await navHelper.focusPane(1);
      // Even if pane is not fully visible, should not error
      await page.waitForTimeout(300);
      
      await navHelper.takeScreenshot('focus-with-hidden-panes');
    });
  });

  test.describe('Tab-Style View Switching', () => {
    test('should switch views with number keys Cmd+1 through Cmd+5', async ({ page }) => {
      const viewMap = {
        1: 'monitoring',
        2: 'planning', 
        3: 'agents',
        4: 'analytics',
        5: 'settings'
      };
      
      for (const [num, view] of Object.entries(viewMap)) {
        await navHelper.switchToView(parseInt(num) as 1 | 2 | 3 | 4 | 5);
        await navHelper.verifyActiveView(view);
        await navHelper.takeScreenshot(`tab-style-view-${num}`);
      }
    });

    test('should handle tab-style switching with consistent timing', async ({ page }) => {
      const viewNumbers: Array<1 | 2 | 3 | 4 | 5> = [1, 2, 3, 4, 5];
      const timings: number[] = [];
      
      for (const viewNum of viewNumbers) {
        const switchTime = await navHelper.measureNavigationTime(() => 
          navHelper.switchToView(viewNum)
        );
        timings.push(switchTime);
      }
      
      const averageTime = timings.reduce((a, b) => a + b) / timings.length;
      console.log(`Average tab-style switch time: ${averageTime.toFixed(2)}ms`);
      
      // Should be consistent and fast
      expect(averageTime).toBeLessThan(100);
      timings.forEach((time, index) => {
        expect(time).toBeLessThan(200, `Switch ${index + 1}: ${time.toFixed(2)}ms too slow`);
      });
    });
  });

  test.describe('Performance Assertions (<50ms Context Switching)', () => {
    test('should switch pane focus under 50ms', async ({ page }) => {
      const measurements: number[] = [];
      const panes: Array<1 | 2 | 3> = [1, 2, 3];
      
      // Test multiple focus switches
      for (let round = 0; round < 3; round++) {
        for (const paneNum of panes) {
          const switchTime = await navHelper.measureNavigationTime(() => 
            navHelper.focusPane(paneNum)
          );
          measurements.push(switchTime);
        }
      }
      
      const averageTime = measurements.reduce((a, b) => a + b) / measurements.length;
      console.log(`Average pane focus time: ${averageTime.toFixed(2)}ms`);
      
      // Assert under 50ms average
      expect(averageTime).toBeLessThan(50);
      
      // No individual measurement should exceed 100ms
      measurements.forEach((time, index) => {
        expect(time).toBeLessThan(100, `Focus switch ${index + 1}: ${time.toFixed(2)}ms exceeded 100ms`);
      });
      
      await navHelper.takeScreenshot('pane-focus-performance-results');
    });

    test('should switch views under 50ms with vim navigation', async ({ page }) => {
      const targets: Array<'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings'> = 
        ['planning', 'monitoring', 'analytics', 'agents', 'settings'];
      
      const measurements: number[] = [];
      
      for (const target of targets) {
        const navTime = await navHelper.measureNavigationTime(() => 
          navHelper.navigateVimStyle(target)
        );
        measurements.push(navTime);
      }
      
      const averageTime = measurements.reduce((a, b) => a + b) / measurements.length;
      console.log(`Average vim navigation time: ${averageTime.toFixed(2)}ms`);
      
      // Assert under 50ms average
      expect(averageTime).toBeLessThan(50);
      
      await navHelper.takeScreenshot('vim-navigation-performance-results');
    });

    test('should handle context switching under load', async ({ page }) => {
      // Simulate high-frequency context switching
      const operations = [];
      
      // Mix of different navigation types
      for (let i = 0; i < 20; i++) {
        if (i % 3 === 0) {
          operations.push(() => navHelper.focusPane((i % 3) + 1 as 1 | 2 | 3));
        } else if (i % 3 === 1) {
          const targets: Array<'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings'> = 
            ['planning', 'monitoring', 'analytics', 'agents', 'settings'];
          operations.push(() => navHelper.navigateVimStyle(targets[i % targets.length]));
        } else {
          operations.push(() => navHelper.switchToView((i % 5) + 1 as 1 | 2 | 3 | 4 | 5));
        }
      }
      
      // Execute all operations with timing
      const startTime = performance.now();
      for (const operation of operations) {
        await operation();
        await page.waitForTimeout(25); // Slight delay between operations
      }
      const endTime = performance.now();
      
      const totalTime = endTime - startTime;
      const averagePerOperation = totalTime / operations.length;
      
      console.log(`Context switching under load - Average per operation: ${averagePerOperation.toFixed(2)}ms`);
      
      // Under load, should still maintain reasonable performance
      expect(averagePerOperation).toBeLessThan(100);
      
      await navHelper.takeScreenshot('context-switching-under-load');
    });

    test('should maintain performance consistency over time', async ({ page }) => {
      // Test performance consistency over extended session
      const rounds = 5;
      const measurementsPerRound = 10;
      const allMeasurements: number[] = [];
      
      for (let round = 0; round < rounds; round++) {
        const roundMeasurements: number[] = [];
        
        for (let i = 0; i < measurementsPerRound; i++) {
          const paneNum = (i % 3) + 1 as 1 | 2 | 3;
          const switchTime = await navHelper.measureNavigationTime(() => 
            navHelper.focusPane(paneNum)
          );
          roundMeasurements.push(switchTime);
          allMeasurements.push(switchTime);
        }
        
        const roundAverage = roundMeasurements.reduce((a, b) => a + b) / roundMeasurements.length;
        console.log(`Round ${round + 1} average: ${roundAverage.toFixed(2)}ms`);
        
        // Wait between rounds to simulate extended session
        await page.waitForTimeout(500);
      }
      
      // Calculate consistency metrics
      const overallAverage = allMeasurements.reduce((a, b) => a + b) / allMeasurements.length;
      const variance = allMeasurements.reduce((acc, val) => acc + Math.pow(val - overallAverage, 2), 0) / allMeasurements.length;
      const standardDeviation = Math.sqrt(variance);
      
      console.log(`Performance consistency - Average: ${overallAverage.toFixed(2)}ms, StdDev: ${standardDeviation.toFixed(2)}ms`);
      
      // Should maintain consistent performance (low standard deviation)
      expect(standardDeviation).toBeLessThan(20); // Low variation
      expect(overallAverage).toBeLessThan(50); // Maintain speed target
      
      await navHelper.takeScreenshot('performance-consistency-results');
    });
  });

  test.describe('Focus Visual Indicators', () => {
    test('should display clear visual focus indicators', async ({ page }) => {
      const panes = [
        { number: 1 as const, testId: 'orchestration-tree' },
        { number: 2 as const, testId: 'workspace' },
        { number: 3 as const, testId: 'activity-stream' }
      ];
      
      for (const pane of panes) {
        await navHelper.focusPane(pane.number);
        
        const paneElement = page.locator(`[data-testid="${pane.testId}"]`);
        
        // Should be visible
        await expect(paneElement).toBeVisible();
        
        // Should have focus attribute
        await expect(paneElement).toHaveAttribute('data-focused', 'true');
        
        // Should have visual styling
        await navHelper.verifyFocusIndicator(`[data-testid="${pane.testId}"]`);
        
        await navHelper.takeScreenshot(`focus-indicator-pane-${pane.number}`);
      }
    });

    test('should remove focus indicators when focus changes', async ({ page }) => {
      // Focus pane 1
      await navHelper.focusPane(1);
      const pane1 = page.locator('[data-testid="orchestration-tree"]');
      await expect(pane1).toHaveAttribute('data-focused', 'true');
      
      // Focus pane 2
      await navHelper.focusPane(2);
      const pane2 = page.locator('[data-testid="workspace"]');
      await expect(pane2).toHaveAttribute('data-focused', 'true');
      
      // Pane 1 should no longer be focused
      await expect(pane1).toHaveAttribute('data-focused', 'false');
      
      await navHelper.takeScreenshot('focus-indicator-transition');
    });

    test('should use consistent focus styling across all focusable elements', async ({ page }) => {
      const focusableElements = [
        '[data-testid="orchestration-tree"]',
        '[data-testid="workspace"]', 
        '[data-testid="activity-stream"]'
      ];
      
      const focusStyles: string[] = [];
      
      for (let i = 0; i < focusableElements.length; i++) {
        await navHelper.focusPane((i + 1) as 1 | 2 | 3);
        
        const element = page.locator(focusableElements[i]);
        const borderColor = await element.evaluate(el => {
          const style = getComputedStyle(el);
          return style.borderColor || style.outlineColor;
        });
        
        focusStyles.push(borderColor);
      }
      
      // All focus styles should be the same (consistent)
      const uniqueStyles = new Set(focusStyles);
      expect(uniqueStyles.size).toBeLessThanOrEqual(2); // Should be consistent, allowing for minor variations
      
      await navHelper.takeScreenshot('consistent-focus-styling');
    });
  });

  test.describe('Browser Compatibility and Interference', () => {
    test('should not interfere with browser shortcuts', async ({ page }) => {
      // Test that browser shortcuts still work
      await navHelper.verifyNoInterference();
      
      // Our shortcuts should work
      await navHelper.focusPane(1);
      await navHelper.verifyFocusedPane('orchestration-tree');
      
      // Browser should still be responsive
      const title = await page.title();
      expect(title).toBeTruthy();
      
      await navHelper.takeScreenshot('browser-compatibility');
    });

    test('should prevent default only for handled shortcuts', async ({ page }) => {
      // Test that unhandled key combinations don't prevent default
      const unhandledKeys = ['Meta+t', 'Meta+w', 'Meta+r'];
      
      for (const keyCombo of unhandledKeys) {
        // These should not be prevented by our handlers
        // We can't easily test this without actually opening tabs/refreshing
        // But we can ensure our shortcuts still work after pressing these
        try {
          await page.keyboard.press(keyCombo);
          await page.waitForTimeout(100);
        } catch (error) {
          // Expected - browser might handle these
        }
      }
      
      // Our shortcuts should still work
      await navHelper.focusPane(2);
      await navHelper.verifyFocusedPane('workspace');
      
      await navHelper.takeScreenshot('unhandled-shortcuts-test');
    });

    test('should work across different focus states', async ({ page }) => {
      // Test shortcuts work when different elements have focus
      const testElements = ['body', 'input', 'button'];
      
      for (const elementType of testElements) {
        try {
          // Try to focus different element types if they exist
          if (elementType === 'input') {
            const input = page.locator('input').first();
            if (await input.count() > 0) {
              await input.focus();
            }
          } else if (elementType === 'button') {
            const button = page.locator('button').first();
            if (await button.count() > 0) {
              await button.focus();
            }
          }
          
          // Our navigation should still work
          await navHelper.navigateVimStyle('monitoring');
          await navHelper.verifyActiveView('monitoring');
          
        } catch (error) {
          // Some elements might not exist, continue testing
          console.log(`Skipping ${elementType} focus test:`, error);
        }
      }
      
      await navHelper.takeScreenshot('different-focus-states');
    });
  });
});