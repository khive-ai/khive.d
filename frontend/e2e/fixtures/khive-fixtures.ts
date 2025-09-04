import { test as base, expect, Page, BrowserContext } from '@playwright/test';
import { KhiveWebSocketMock } from '../mocks/websocket-mock';
import { ScreenshotManager } from '../utils/screenshot-manager';
import { KeyboardShortcutTester } from '../utils/keyboard-shortcuts';
import { PerformanceMonitor } from '../utils/performance-monitor';

/**
 * Extended test fixtures for KHIVE E2E testing
 * Provides specialized utilities for CLI-first workflows and agent orchestration
 */
export interface KhiveTestFixtures {
  // Core utilities
  khivePage: Page;
  khiveContext: BrowserContext;
  
  // KHIVE-specific mocks and utilities
  webSocketMock: KhiveWebSocketMock;
  screenshots: ScreenshotManager;
  keyboard: KeyboardShortcutTester;
  performance: PerformanceMonitor;
  
  // Agent orchestration utilities
  orchestrationHelper: OrchestrationHelper;
  cliHelper: CLIHelper;
}

export interface OrchestrationHelper {
  simulateAgentStatus: (agentId: string, status: string) => Promise<void>;
  triggerOrchestrationEvent: (event: string, data: any) => Promise<void>;
  waitForAgentResponse: (agentId: string, timeout?: number) => Promise<any>;
  verifyAgentCommunication: () => Promise<boolean>;
}

export interface CLIHelper {
  openCommandPalette: () => Promise<void>;
  executeCommand: (command: string) => Promise<void>;
  verifyCommandOutput: (expectedOutput: string) => Promise<boolean>;
  getTerminalContent: () => Promise<string>;
  clearTerminal: () => Promise<void>;
}

/**
 * Extended Playwright test with KHIVE fixtures
 */
export const test = base.extend<KhiveTestFixtures>({
  // Enhanced page with KHIVE-specific setup
  khivePage: async ({ page, webSocketMock }, use) => {
    // Use webSocketMock to suppress TypeScript warning
    void webSocketMock;
    // Set up KHIVE-specific page configuration
    await page.setViewportSize({ width: 1280, height: 720 });
    
    // Add custom CSS for consistent terminal rendering
    await page.addStyleTag({
      content: `
        * {
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace !important;
          font-feature-settings: "liga" 0, "kern" 0;
          text-rendering: optimizeSpeed;
        }
        
        .command-palette {
          animation-duration: 0ms !important;
          transition-duration: 0ms !important;
        }
      `
    });
    
    // Set up WebSocket mock interception
    await page.route('**/ws', route => {
      // Redirect to our mock WebSocket server
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/plain' },
        body: 'WebSocket mock active'
      });
    });
    
    // Add KHIVE test markers
    await page.addInitScript(() => {
      (window as any).KHIVE_TEST_MODE = true;
      (window as any).KHIVE_WS_MOCK = true;
    });
    
    await use(page);
  },

  khiveContext: async ({ context }, use) => {
    // Set up context with KHIVE-specific permissions
    await context.grantPermissions(['web-socket', 'notifications']);
    
    // Add request interceptors for API calls
    await context.route('**/api/**', async route => {
      // Add test headers to API requests
      const request = route.request();
      const headers = {
        ...request.headers(),
        'X-Test-Environment': 'playwright-e2e',
        'X-KHIVE-Test': 'true'
      };
      
      await route.continue({ headers });
    });
    
    await use(context);
  },

  // WebSocket mock for agent communication
  webSocketMock: async ({}, use) => {
    const mock = new KhiveWebSocketMock('ws://localhost:8000');
    await mock.start();
    await use(mock);
    await mock.stop();
  },

  // Screenshot management for visual testing
  screenshots: async ({ khivePage }, use) => {
    const manager = new ScreenshotManager(khivePage);
    await use(manager);
  },

  // Keyboard shortcut testing utilities
  keyboard: async ({ khivePage }, use) => {
    const tester = new KeyboardShortcutTester(khivePage);
    await use(tester);
  },

  // Performance monitoring
  performance: async ({ khivePage }, use) => {
    const monitor = new PerformanceMonitor(khivePage);
    await monitor.startMonitoring();
    await use(monitor);
    await monitor.stopMonitoring();
  },

  // Orchestration testing helper
  orchestrationHelper: async ({ webSocketMock }, use) => {
    const helper: OrchestrationHelper = {
      async simulateAgentStatus(agentId: string, status: string) {
        await webSocketMock.sendMessage({
          type: 'agent_status',
          data: {
            id: agentId,
            status,
            timestamp: Date.now()
          }
        });
      },

      async triggerOrchestrationEvent(event: string, data: any) {
        await webSocketMock.sendMessage({
          type: 'orchestration_event',
          event,
          data: {
            ...data,
            timestamp: Date.now()
          }
        });
      },

      async waitForAgentResponse(agentId: string, timeout = 5000) {
        return new Promise((resolve, reject) => {
          const timer = setTimeout(() => {
            reject(new Error(`Agent ${agentId} did not respond within ${timeout}ms`));
          }, timeout);

          const handleMessage = (message: any) => {
            if (message.type === 'agent_response' && message.data.id === agentId) {
              clearTimeout(timer);
              webSocketMock.off('message', handleMessage);
              resolve(message.data);
            }
          };

          webSocketMock.on('message', handleMessage);
        });
      },

      async verifyAgentCommunication() {
        // Send ping and wait for pong
        await webSocketMock.sendMessage({ type: 'ping', timestamp: Date.now() });
        
        return new Promise<boolean>((resolve) => {
          const timer = setTimeout(() => resolve(false), 3000);
          
          const handleMessage = (message: any) => {
            if (message.type === 'pong') {
              clearTimeout(timer);
              webSocketMock.off('message', handleMessage);
              resolve(true);
            }
          };
          
          webSocketMock.on('message', handleMessage);
        });
      }
    };

    await use(helper);
  },

  // CLI testing helper
  cliHelper: async ({ khivePage }, use) => {
    const helper: CLIHelper = {
      async openCommandPalette() {
        // Use Cmd+K (macOS) or Ctrl+K (others) to open command palette
        const modifier = process.platform === 'darwin' ? 'Meta' : 'Control';
        await khivePage.keyboard.press(`${modifier}+KeyK`);
        
        // Wait for command palette to appear
        await khivePage.waitForSelector('[data-testid="command-palette"]', {
          timeout: 5000
        });
      },

      async executeCommand(command: string) {
        await this.openCommandPalette();
        
        // Type the command
        await khivePage.fill('[data-testid="command-input"]', command);
        
        // Press Enter to execute
        await khivePage.keyboard.press('Enter');
        
        // Wait for command to be processed
        await khivePage.waitForTimeout(1000);
      },

      async verifyCommandOutput(expectedOutput: string) {
        const outputElement = khivePage.locator('[data-testid="command-output"]');
        await expect(outputElement).toContainText(expectedOutput);
        return true;
      },

      async getTerminalContent() {
        const terminal = khivePage.locator('[data-testid="terminal-content"]');
        return await terminal.textContent() || '';
      },

      async clearTerminal() {
        // Use keyboard shortcut to clear terminal
        const modifier = process.platform === 'darwin' ? 'Meta' : 'Control';
        await khivePage.keyboard.press(`${modifier}+KeyL`);
      }
    };

    await use(helper);
  },
});

export { expect } from '@playwright/test';