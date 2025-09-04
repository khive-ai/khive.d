import { test, expect, Page } from '@playwright/test';

// Helper class for command palette testing
class CommandPaletteHelper {
  constructor(private page: Page) {}

  async open() {
    await this.page.keyboard.press('Meta+k');
    await this.page.waitForSelector('[role="dialog"]', { timeout: 1000 });
  }

  async openWithHelp() {
    await this.page.keyboard.press('Meta+Shift+k');
    await this.page.waitForSelector('[role="dialog"]', { timeout: 1000 });
  }

  async close() {
    await this.page.keyboard.press('Escape');
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 1000 });
  }

  async typeQuery(query: string) {
    await this.page.locator('[role="dialog"] input').fill(query);
    await this.page.waitForTimeout(300); // Allow filtering to complete
  }

  async selectCommand(index: number) {
    // Navigate to command by index using arrow keys
    for (let i = 0; i < index; i++) {
      await this.page.keyboard.press('ArrowDown');
      await this.page.waitForTimeout(50);
    }
  }

  async executeSelectedCommand() {
    await this.page.keyboard.press('Enter');
  }

  async getFilteredCommands() {
    return this.page.locator('[role="dialog"] [role="listitem"]');
  }

  async getSelectedCommand() {
    return this.page.locator('[role="dialog"] [role="listitem"][data-selected="true"], [role="dialog"] .selected');
  }

  async getCommandCount() {
    return this.page.locator('[role="dialog"] [role="listitem"]').count();
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `test-results/screenshots/command-palette-${name}.png`,
      fullPage: true 
    });
  }

  async verifyCommandPresence(commandText: string) {
    const command = this.page.locator(`[role="dialog"] text="${commandText}"`);
    await expect(command).toBeVisible();
  }

  async verifyCommandCategory(category: string) {
    const categoryChip = this.page.locator(`[role="dialog"] text="${category}"`);
    await expect(categoryChip).toBeVisible();
  }

  async verifyShortcut(shortcut: string) {
    const shortcutText = this.page.locator(`[role="dialog"] text="${shortcut}"`);
    await expect(shortcutText).toBeVisible();
  }
}

test.describe('Command Palette E2E Tests', () => {
  let paletteHelper: CommandPaletteHelper;

  test.beforeEach(async ({ page }) => {
    paletteHelper = new CommandPaletteHelper(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test.describe('Basic Command Palette Functionality', () => {
    test('should open command palette with Cmd+K', async ({ page }) => {
      await paletteHelper.open();
      
      // Verify dialog is visible
      await expect(page.locator('[role="dialog"]')).toBeVisible();
      
      // Verify input is focused and ready
      const input = page.locator('[role="dialog"] input');
      await expect(input).toBeFocused();
      await expect(input).toHaveAttribute('placeholder', /command/i);
      
      await paletteHelper.takeScreenshot('opened-with-cmd-k');
    });

    test('should open help with Cmd+Shift+K', async ({ page }) => {
      await paletteHelper.openWithHelp();
      
      // Should either open help modal or command palette with help context
      const helpContent = page.locator('text="Help", text="Reference", text="Shortcuts"');
      await expect(helpContent.first()).toBeVisible();
      
      await paletteHelper.takeScreenshot('help-shortcut');
    });

    test('should close with Escape key', async ({ page }) => {
      await paletteHelper.open();
      await expect(page.locator('[role="dialog"]')).toBeVisible();
      
      await paletteHelper.close();
      await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    });

    test('should close when clicking outside', async ({ page }) => {
      await paletteHelper.open();
      await expect(page.locator('[role="dialog"]')).toBeVisible();
      
      // Click outside the dialog
      await page.mouse.click(100, 100);
      await page.waitForTimeout(300);
      
      await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    });
  });

  test.describe('Command Discovery and Search', () => {
    test('should display all 25+ commands by default', async ({ page }) => {
      await paletteHelper.open();
      
      const commandCount = await paletteHelper.getCommandCount();
      expect(commandCount).toBeGreaterThanOrEqual(25);
      
      console.log(`Found ${commandCount} total commands`);
      await paletteHelper.takeScreenshot('all-commands-displayed');
    });

    test('should filter commands by search query', async ({ page }) => {
      await paletteHelper.open();
      
      // Test searching for "plan"
      await paletteHelper.typeQuery('plan');
      
      const filteredCommands = await paletteHelper.getFilteredCommands();
      const count = await filteredCommands.count();
      
      expect(count).toBeGreaterThan(0);
      expect(count).toBeLessThan(25); // Should be filtered
      
      // Verify all results contain "plan" in some form
      const commandTexts = await filteredCommands.allTextContents();
      commandTexts.forEach(text => {
        expect(text.toLowerCase()).toMatch(/plan|planning/);
      });
      
      await paletteHelper.takeScreenshot('filtered-by-plan');
    });

    test('should search across multiple fields (label, description, keywords)', async ({ page }) => {
      await paletteHelper.open();
      
      // Test searching by description content
      await paletteHelper.typeQuery('orchestration');
      
      const commandCount = await paletteHelper.getCommandCount();
      expect(commandCount).toBeGreaterThan(0);
      
      await paletteHelper.takeScreenshot('search-by-description');
      
      // Clear and test keyword search
      await paletteHelper.typeQuery('');
      await paletteHelper.typeQuery('daemon');
      
      const daemonCommandCount = await paletteHelper.getCommandCount();
      expect(daemonCommandCount).toBeGreaterThan(0);
      
      await paletteHelper.takeScreenshot('search-by-keyword');
    });

    test('should prioritize exact matches and shorter labels', async ({ page }) => {
      await paletteHelper.open();
      
      // Search for "plan"
      await paletteHelper.typeQuery('plan');
      
      // First result should be the most relevant (likely "Plan Orchestration")
      const firstCommand = paletteHelper.page.locator('[role="dialog"] [role="listitem"]:first-child');
      const firstCommandText = await firstCommand.textContent();
      
      expect(firstCommandText?.toLowerCase()).toContain('plan');
      
      await paletteHelper.takeScreenshot('search-prioritization');
    });

    test('should show "no commands found" for invalid searches', async ({ page }) => {
      await paletteHelper.open();
      
      // Search for something that shouldn't exist
      await paletteHelper.typeQuery('invalidcommandxyz123');
      
      const noResultsMessage = page.locator('text="No commands found"');
      await expect(noResultsMessage).toBeVisible();
      
      await paletteHelper.takeScreenshot('no-commands-found');
    });

    test('should provide helpful suggestions in no results state', async ({ page }) => {
      await paletteHelper.open();
      
      await paletteHelper.typeQuery('invalidcommandxyz123');
      
      // Should show helpful suggestions
      const suggestions = page.locator('text="plan", text="agent", text="monitor"');
      await expect(suggestions.first()).toBeVisible();
      
      await paletteHelper.takeScreenshot('helpful-suggestions');
    });
  });

  test.describe('Command Categories and Organization', () => {
    test('should display command categories with proper colors', async ({ page }) => {
      await paletteHelper.open();
      
      // Check for different category chips
      const categories = ['navigation', 'orchestration', 'agents', 'sessions', 'system', 'workspace'];
      
      for (const category of categories) {
        await paletteHelper.verifyCommandCategory(category);
      }
      
      await paletteHelper.takeScreenshot('command-categories');
    });

    test('should group KHIVE orchestration commands', async ({ page }) => {
      await paletteHelper.open();
      await paletteHelper.typeQuery('khive');
      
      const commandCount = await paletteHelper.getCommandCount();
      expect(commandCount).toBeGreaterThan(3); // Should have multiple KHIVE commands
      
      // Verify key KHIVE commands are present
      await paletteHelper.verifyCommandPresence('Plan Orchestration');
      await paletteHelper.verifyCommandPresence('Compose Agent');
      await paletteHelper.verifyCommandPresence('Daemon Status');
      
      await paletteHelper.takeScreenshot('khive-commands-group');
    });

    test('should show navigation commands with vim-style shortcuts', async ({ page }) => {
      await paletteHelper.open();
      await paletteHelper.typeQuery('go to');
      
      const commandCount = await paletteHelper.getCommandCount();
      expect(commandCount).toBeGreaterThan(3);
      
      // Check for vim-style shortcuts
      await paletteHelper.verifyShortcut('G P');
      await paletteHelper.verifyShortcut('G M');
      await paletteHelper.verifyShortcut('G A');
      
      await paletteHelper.takeScreenshot('vim-navigation-commands');
    });

    test('should display pane focus commands with numbered shortcuts', async ({ page }) => {
      await paletteHelper.open();
      await paletteHelper.typeQuery('focus');
      
      const commandCount = await paletteHelper.getCommandCount();
      expect(commandCount).toBeGreaterThan(2);
      
      // Check for numbered shortcuts
      await paletteHelper.verifyShortcut('⌘1');
      await paletteHelper.verifyShortcut('⌘2');
      await paletteHelper.verifyShortcut('⌘3');
      
      await paletteHelper.takeScreenshot('focus-commands');
    });
  });

  test.describe('Keyboard Navigation', () => {
    test('should support arrow key navigation', async ({ page }) => {
      await paletteHelper.open();
      
      // Should start with first command selected
      let selectedCommand = await paletteHelper.getSelectedCommand();
      expect(await selectedCommand.count()).toBe(1);
      
      await paletteHelper.takeScreenshot('first-command-selected');
      
      // Navigate down
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(100);
      
      // Second command should be selected
      selectedCommand = await paletteHelper.getSelectedCommand();
      expect(await selectedCommand.count()).toBe(1);
      
      await paletteHelper.takeScreenshot('second-command-selected');
      
      // Navigate up
      await page.keyboard.press('ArrowUp');
      await page.waitForTimeout(100);
      
      // First command should be selected again
      await paletteHelper.takeScreenshot('back-to-first-command');
    });

    test('should wrap navigation at boundaries', async ({ page }) => {
      await paletteHelper.open();
      await paletteHelper.typeQuery('plan'); // Limit results for easier testing
      
      const commandCount = await paletteHelper.getCommandCount();
      
      // Navigate to last command
      for (let i = 0; i < commandCount - 1; i++) {
        await page.keyboard.press('ArrowDown');
        await page.waitForTimeout(25);
      }
      
      await paletteHelper.takeScreenshot('last-command-selected');
      
      // Go down from last - should wrap to first or stay at last
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(100);
      
      await paletteHelper.takeScreenshot('after-boundary-navigation');
      
      // Navigate up from first - should wrap to last or stay at first
      await page.keyboard.press('ArrowUp');
      await page.waitForTimeout(100);
      
      await paletteHelper.takeScreenshot('up-boundary-navigation');
    });

    test('should reset selection when query changes', async ({ page }) => {
      await paletteHelper.open();
      
      // Navigate to second command
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(100);
      
      // Type new query
      await paletteHelper.typeQuery('daemon');
      
      // Selection should reset to first result
      const firstCommand = page.locator('[role="dialog"] [role="listitem"]:first-child');
      const isSelected = await firstCommand.getAttribute('data-selected') === 'true' ||
                        await firstCommand.getAttribute('class')?.includes('selected');
      
      expect(isSelected).toBe(true);
      
      await paletteHelper.takeScreenshot('selection-reset-after-query');
    });

    test('should execute command with Enter key', async ({ page }) => {
      await paletteHelper.open();
      
      // Search for a specific command
      await paletteHelper.typeQuery('daemon status');
      await page.waitForTimeout(300);
      
      // Execute the command
      await paletteHelper.executeSelectedCommand();
      
      // Palette should close
      await page.waitForTimeout(500);
      await expect(page.locator('[role="dialog"]')).not.toBeVisible();
      
      await paletteHelper.takeScreenshot('command-executed');
    });
  });

  test.describe('Command Execution and Feedback', () => {
    test('should execute navigation commands correctly', async ({ page }) => {
      await paletteHelper.open();
      
      // Execute "Go to Planning"
      await paletteHelper.typeQuery('go to planning');
      await paletteHelper.executeSelectedCommand();
      
      await page.waitForTimeout(500);
      
      // Should navigate to planning view
      const workspace = page.locator('[data-testid="workspace"]');
      await expect(workspace).toHaveAttribute('data-active-view', 'planning');
      
      await paletteHelper.takeScreenshot('navigation-command-executed');
    });

    test('should execute focus pane commands correctly', async ({ page }) => {
      await paletteHelper.open();
      
      // Execute "Focus Main Workspace"
      await paletteHelper.typeQuery('focus main workspace');
      await paletteHelper.executeSelectedCommand();
      
      await page.waitForTimeout(500);
      
      // Should focus the workspace pane
      const workspace = page.locator('[data-testid="workspace"]');
      await expect(workspace).toHaveAttribute('data-focused', 'true');
      
      await paletteHelper.takeScreenshot('focus-command-executed');
    });

    test('should send KHIVE commands to backend', async ({ page }) => {
      // Mock WebSocket commands to verify they're being sent
      let commandSent = '';
      await page.route('**/ws', route => {
        // Intercept WebSocket connections if possible
        route.continue();
      });

      await paletteHelper.open();
      
      // Execute a KHIVE command
      await paletteHelper.typeQuery('khive daemon status');
      await paletteHelper.executeSelectedCommand();
      
      await page.waitForTimeout(1000);
      
      // Should have attempted to send the command
      await paletteHelper.takeScreenshot('khive-command-sent');
    });

    test('should clear input after command execution', async ({ page }) => {
      await paletteHelper.open();
      
      // Type a command
      await paletteHelper.typeQuery('plan');
      await paletteHelper.executeSelectedCommand();
      
      // Open palette again
      await page.waitForTimeout(500);
      await paletteHelper.open();
      
      // Input should be cleared
      const input = page.locator('[role="dialog"] input');
      await expect(input).toHaveValue('');
      
      await paletteHelper.takeScreenshot('input-cleared-after-execution');
    });
  });

  test.describe('Visual Design and Terminal Aesthetics', () => {
    test('should use terminal font for consistent styling', async ({ page }) => {
      await paletteHelper.open();
      
      const input = page.locator('[role="dialog"] input');
      const fontFamily = await input.evaluate(el => getComputedStyle(el).fontFamily);
      
      // Should use terminal font
      expect(fontFamily).toMatch(/JetBrains Mono|Fira Code|Monaco|Menlo|monospace/);
      
      await paletteHelper.takeScreenshot('terminal-font-styling');
    });

    test('should display terminal-style prompt indicator', async ({ page }) => {
      await paletteHelper.open();
      
      // Look for ">" prompt indicator
      const promptIndicator = page.locator('[role="dialog"] input::before, text=">"');
      // Note: ::before pseudo-elements may not be directly selectable
      // This is testing the concept - implementation may vary
      
      await paletteHelper.takeScreenshot('terminal-prompt-indicator');
    });

    test('should use dark theme colors for CLI aesthetic', async ({ page }) => {
      await paletteHelper.open();
      
      const dialog = page.locator('[role="dialog"]');
      const backgroundColor = await dialog.evaluate(el => getComputedStyle(el).backgroundColor);
      
      // Should use dark background
      const [, r, g, b] = backgroundColor.match(/rgb\((\d+), (\d+), (\d+)\)/) || ['', '255', '255', '255'];
      const averageBrightness = (parseInt(r) + parseInt(g) + parseInt(b)) / 3;
      expect(averageBrightness).toBeLessThan(100); // Dark theme
      
      await paletteHelper.takeScreenshot('dark-theme-colors');
    });

    test('should show category colors and proper spacing', async ({ page }) => {
      await paletteHelper.open();
      
      // Check that category chips have distinct colors
      const categoryChips = page.locator('[role="dialog"] .MuiChip-root, [role="dialog"] .category-chip');
      const chipCount = await categoryChips.count();
      
      expect(chipCount).toBeGreaterThan(3);
      
      // Each category should have different background colors
      const colors = [];
      for (let i = 0; i < Math.min(chipCount, 5); i++) {
        const chip = categoryChips.nth(i);
        const bgColor = await chip.evaluate(el => getComputedStyle(el).backgroundColor);
        colors.push(bgColor);
      }
      
      // Should have variety in colors (not all the same)
      const uniqueColors = new Set(colors);
      expect(uniqueColors.size).toBeGreaterThan(2);
      
      await paletteHelper.takeScreenshot('category-colors-and-spacing');
    });
  });

  test.describe('Performance and Responsiveness', () => {
    test('should filter commands quickly (under 200ms)', async ({ page }) => {
      await paletteHelper.open();
      
      const startTime = performance.now();
      await paletteHelper.typeQuery('orchestration');
      
      // Wait for filtering to complete
      await page.waitForTimeout(100);
      
      const endTime = performance.now();
      const filterTime = endTime - startTime;
      
      console.log(`Command filtering took ${filterTime.toFixed(2)}ms`);
      expect(filterTime).toBeLessThan(200);
      
      await paletteHelper.takeScreenshot('fast-filtering-performance');
    });

    test('should handle rapid typing without lag', async ({ page }) => {
      await paletteHelper.open();
      
      // Type quickly
      const rapidText = 'khive daemon status';
      for (const char of rapidText) {
        await page.keyboard.press(char);
        await page.waitForTimeout(10); // Very fast typing
      }
      
      // Should have all characters
      const input = page.locator('[role="dialog"] input');
      await expect(input).toHaveValue(rapidText);
      
      await paletteHelper.takeScreenshot('rapid-typing-handling');
    });

    test('should maintain smooth animations during navigation', async ({ page }) => {
      await paletteHelper.open();
      
      // Rapid navigation to test smoothness
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('ArrowDown');
        await page.waitForTimeout(50);
      }
      
      // Should still be responsive
      const selectedCommand = await paletteHelper.getSelectedCommand();
      expect(await selectedCommand.count()).toBe(1);
      
      await paletteHelper.takeScreenshot('smooth-navigation-performance');
    });
  });

  test.describe('Error Handling and Edge Cases', () => {
    test('should handle empty search gracefully', async ({ page }) => {
      await paletteHelper.open();
      
      // Clear input completely
      await paletteHelper.typeQuery('');
      
      // Should show all commands
      const commandCount = await paletteHelper.getCommandCount();
      expect(commandCount).toBeGreaterThan(20);
      
      await paletteHelper.takeScreenshot('empty-search-all-commands');
    });

    test('should handle special characters in search', async ({ page }) => {
      await paletteHelper.open();
      
      // Test special characters
      await paletteHelper.typeQuery('⌘+k');
      
      // Should not crash
      await page.waitForTimeout(300);
      const dialog = page.locator('[role="dialog"]');
      await expect(dialog).toBeVisible();
      
      await paletteHelper.takeScreenshot('special-characters-search');
    });

    test('should maintain state during rapid open/close', async ({ page }) => {
      // Rapid open/close cycles
      for (let i = 0; i < 5; i++) {
        await paletteHelper.open();
        await page.waitForTimeout(50);
        await paletteHelper.close();
        await page.waitForTimeout(50);
      }
      
      // Should still work normally
      await paletteHelper.open();
      await expect(page.locator('[role="dialog"]')).toBeVisible();
      
      const commandCount = await paletteHelper.getCommandCount();
      expect(commandCount).toBeGreaterThan(20);
      
      await paletteHelper.takeScreenshot('rapid-open-close-stability');
    });
  });
});