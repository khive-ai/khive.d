import { Page, expect } from '@playwright/test';

/**
 * Keyboard Shortcut Testing Utilities for KHIVE CLI-First Interface
 * Handles cross-platform keyboard shortcut testing with proper timing
 */
export class KeyboardShortcutTester {
  private page: Page;
  private platform: 'darwin' | 'win32' | 'linux';
  
  constructor(page: Page) {
    this.page = page;
    this.platform = process.platform as 'darwin' | 'win32' | 'linux';
  }

  /**
   * Get the appropriate modifier key for the current platform
   */
  private getModifier(type: 'command' | 'control' | 'alt' | 'shift'): string {
    const modifiers = {
      darwin: {
        command: 'Meta',
        control: 'Control',
        alt: 'Alt',
        shift: 'Shift'
      },
      win32: {
        command: 'Control', // Command key maps to Ctrl on Windows
        control: 'Control',
        alt: 'Alt',
        shift: 'Shift'
      },
      linux: {
        command: 'Control', // Command key maps to Ctrl on Linux
        control: 'Control',
        alt: 'Alt',
        shift: 'Shift'
      }
    };

    return modifiers[this.platform][type];
  }

  /**
   * Press a keyboard shortcut with proper modifiers
   */
  async pressShortcut(shortcut: string): Promise<void> {
    // Parse shortcut format like "Cmd+K", "Ctrl+Shift+P", etc.
    const parts = shortcut.split('+').map(part => part.trim());
    const keys: string[] = [];
    
    for (const part of parts) {
      switch (part.toLowerCase()) {
        case 'cmd':
        case 'command':
          keys.push(this.getModifier('command'));
          break;
        case 'ctrl':
        case 'control':
          keys.push(this.getModifier('control'));
          break;
        case 'alt':
        case 'option':
          keys.push(this.getModifier('alt'));
          break;
        case 'shift':
          keys.push(this.getModifier('shift'));
          break;
        default:
          // Handle special keys
          if (part.length === 1) {
            keys.push(`Key${part.toUpperCase()}`);
          } else {
            keys.push(part);
          }
      }
    }
    
    const keyCombo = keys.join('+');
    console.log(`⌨️  Pressing keyboard shortcut: ${shortcut} (${keyCombo})`);
    
    await this.page.keyboard.press(keyCombo);
  }

  /**
   * Test command palette shortcuts
   */
  async testCommandPalette(): Promise<void> {
    console.log('🎯 Testing Command Palette shortcuts');
    
    // Test opening command palette
    await this.pressShortcut('Cmd+K');
    
    // Verify command palette opened
    await expect(this.page.locator('[data-testid="command-palette"]')).toBeVisible({
      timeout: 5000
    });
    
    // Test closing with Escape
    await this.page.keyboard.press('Escape');
    
    // Verify command palette closed
    await expect(this.page.locator('[data-testid="command-palette"]')).toBeHidden({
      timeout: 2000
    });
  }

  /**
   * Test orchestration shortcuts
   */
  async testOrchestrationShortcuts(): Promise<void> {
    console.log('🎯 Testing Orchestration shortcuts');
    
    // Quick orchestration (Cmd+O)
    await this.pressShortcut('Cmd+O');
    await this.page.waitForTimeout(1000);
    
    // Agent spawning (Cmd+Shift+A)
    await this.pressShortcut('Cmd+Shift+A');
    await this.page.waitForTimeout(1000);
    
    // Task execution (Cmd+Enter)
    await this.pressShortcut('Cmd+Enter');
    await this.page.waitForTimeout(1000);
  }

  /**
   * Test navigation shortcuts
   */
  async testNavigationShortcuts(): Promise<void> {
    console.log('🎯 Testing Navigation shortcuts');
    
    const shortcuts = [
      { key: 'Cmd+1', description: 'Switch to Dashboard' },
      { key: 'Cmd+2', description: 'Switch to Agents' },
      { key: 'Cmd+3', description: 'Switch to Orchestration' },
      { key: 'Cmd+4', description: 'Switch to Monitor' },
      { key: 'Cmd+5', description: 'Switch to Settings' },
    ];
    
    for (const shortcut of shortcuts) {
      console.log(`  Testing: ${shortcut.description} (${shortcut.key})`);
      await this.pressShortcut(shortcut.key);
      await this.page.waitForTimeout(500); // Allow navigation to complete
    }
  }

  /**
   * Test terminal/CLI shortcuts
   */
  async testTerminalShortcuts(): Promise<void> {
    console.log('🎯 Testing Terminal shortcuts');
    
    // Open terminal (Cmd+`)
    await this.pressShortcut('Cmd+`');
    
    // Clear terminal (Cmd+L)
    await this.pressShortcut('Cmd+L');
    
    // Copy output (Cmd+Shift+C)
    await this.pressShortcut('Cmd+Shift+C');
    
    // Paste into terminal (Cmd+V)
    await this.pressShortcut('Cmd+V');
  }

  /**
   * Test all KHIVE keyboard shortcuts
   */
  async testAllShortcuts(): Promise<void> {
    console.log('🎯 Running comprehensive keyboard shortcut tests');
    
    try {
      await this.testCommandPalette();
      await this.page.waitForTimeout(1000);
      
      await this.testNavigationShortcuts();
      await this.page.waitForTimeout(1000);
      
      await this.testOrchestrationShortcuts();
      await this.page.waitForTimeout(1000);
      
      await this.testTerminalShortcuts();
      await this.page.waitForTimeout(1000);
      
      console.log('✅ All keyboard shortcut tests completed');
      
    } catch (error) {
      console.error('❌ Keyboard shortcut test failed:', error);
      throw error;
    }
  }

  /**
   * Test keyboard shortcuts with visual verification
   */
  async testShortcutWithScreenshot(
    shortcut: string,
    expectedSelector: string,
    screenshotName: string
  ): Promise<void> {
    console.log(`📸 Testing ${shortcut} with screenshot verification`);
    
    // Take before screenshot
    await this.page.screenshot({ 
      path: `e2e/screenshots/before-${screenshotName}.png`,
      fullPage: true 
    });
    
    // Press shortcut
    await this.pressShortcut(shortcut);
    
    // Wait for expected element
    await this.page.waitForSelector(expectedSelector, { timeout: 5000 });
    
    // Take after screenshot
    await this.page.screenshot({ 
      path: `e2e/screenshots/after-${screenshotName}.png`,
      fullPage: true 
    });
    
    // Verify element is visible
    await expect(this.page.locator(expectedSelector)).toBeVisible();
  }

  /**
   * Test keyboard shortcut accessibility
   */
  async testAccessibilityShortcuts(): Promise<void> {
    console.log('♿ Testing accessibility shortcuts');
    
    // Skip links (Tab navigation)
    await this.page.keyboard.press('Tab');
    await this.page.waitForTimeout(200);
    
    // Focus management
    await this.page.keyboard.press('Shift+Tab');
    await this.page.waitForTimeout(200);
    
    // Screen reader navigation (Arrow keys)
    await this.page.keyboard.press('ArrowDown');
    await this.page.waitForTimeout(200);
    
    await this.page.keyboard.press('ArrowUp');
    await this.page.waitForTimeout(200);
  }

  /**
   * Test keyboard shortcuts in different contexts
   */
  async testContextualShortcuts(context: 'dashboard' | 'terminal' | 'orchestration'): Promise<void> {
    console.log(`🎯 Testing shortcuts in ${context} context`);
    
    switch (context) {
      case 'dashboard':
        await this.testDashboardShortcuts();
        break;
      case 'terminal':
        await this.testTerminalContextShortcuts();
        break;
      case 'orchestration':
        await this.testOrchestrationContextShortcuts();
        break;
    }
  }

  /**
   * Dashboard-specific shortcuts
   */
  private async testDashboardShortcuts(): Promise<void> {
    // Refresh dashboard (Cmd+R or F5)
    await this.pressShortcut('Cmd+R');
    await this.page.waitForTimeout(1000);
    
    // Toggle sidebar (Cmd+B)
    await this.pressShortcut('Cmd+B');
    await this.page.waitForTimeout(500);
    
    // Focus search (Cmd+F)
    await this.pressShortcut('Cmd+F');
    await this.page.waitForTimeout(500);
  }

  /**
   * Terminal context shortcuts
   */
  private async testTerminalContextShortcuts(): Promise<void> {
    // Interrupt process (Ctrl+C)
    await this.pressShortcut('Ctrl+C');
    await this.page.waitForTimeout(200);
    
    // End of input (Ctrl+D)
    await this.pressShortcut('Ctrl+D');
    await this.page.waitForTimeout(200);
    
    // History search (Ctrl+R)
    await this.pressShortcut('Ctrl+R');
    await this.page.waitForTimeout(200);
  }

  /**
   * Orchestration context shortcuts
   */
  private async testOrchestrationContextShortcuts(): Promise<void> {
    // Start orchestration (Space)
    await this.page.keyboard.press('Space');
    await this.page.waitForTimeout(500);
    
    // Pause orchestration (P)
    await this.page.keyboard.press('KeyP');
    await this.page.waitForTimeout(500);
    
    // Stop orchestration (Escape)
    await this.page.keyboard.press('Escape');
    await this.page.waitForTimeout(500);
  }

  /**
   * Verify shortcut doesn't interfere with typing
   */
  async testShortcutIsolation(): Promise<void> {
    console.log('🔒 Testing shortcut isolation from text input');
    
    // Focus on a text input
    const input = this.page.locator('input[type="text"]').first();
    if (await input.count() > 0) {
      await input.click();
      
      // Type text that includes potential shortcut characters
      await input.fill('Testing Cmd+K and Ctrl+C in text input');
      
      // Verify text was typed correctly (shortcuts didn't trigger)
      const value = await input.inputValue();
      expect(value).toBe('Testing Cmd+K and Ctrl+C in text input');
    }
  }

  /**
   * Test rapid shortcut sequences
   */
  async testRapidShortcuts(): Promise<void> {
    console.log('⚡ Testing rapid shortcut sequences');
    
    const shortcuts = ['Cmd+1', 'Cmd+2', 'Cmd+3', 'Cmd+K', 'Escape'];
    
    for (const shortcut of shortcuts) {
      await this.pressShortcut(shortcut);
      await this.page.waitForTimeout(100); // Minimal delay between shortcuts
    }
    
    // Wait for UI to stabilize
    await this.page.waitForTimeout(1000);
  }

  /**
   * Get platform-specific shortcut help
   */
  getShortcutHelp(): Record<string, string> {
    const baseShortcuts = {
      'Open Command Palette': 'Cmd+K',
      'Quick Orchestration': 'Cmd+O',
      'Agent Management': 'Cmd+Shift+A',
      'Execute Task': 'Cmd+Enter',
      'Switch Dashboard': 'Cmd+1',
      'Switch Agents': 'Cmd+2',
      'Switch Orchestration': 'Cmd+3',
      'Switch Monitor': 'Cmd+4',
      'Switch Settings': 'Cmd+5',
      'Open Terminal': 'Cmd+`',
      'Clear Terminal': 'Cmd+L',
      'Toggle Sidebar': 'Cmd+B',
      'Search/Find': 'Cmd+F',
      'Refresh': 'Cmd+R',
    };

    // Convert Cmd to appropriate platform modifier
    const platformShortcuts: Record<string, string> = {};
    
    for (const [action, shortcut] of Object.entries(baseShortcuts)) {
      if (this.platform === 'darwin') {
        platformShortcuts[action] = shortcut; // Keep Cmd on macOS
      } else {
        platformShortcuts[action] = shortcut.replace('Cmd', 'Ctrl'); // Use Ctrl on Windows/Linux
      }
    }
    
    return platformShortcuts;
  }
}