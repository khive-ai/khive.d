/**
 * KHIVE E2E Testing Utilities
 * Centralized exports for all testing utilities
 */

export { ScreenshotManager } from './screenshot-manager';
export { KeyboardShortcutTester } from './keyboard-shortcuts';
export { PerformanceMonitor } from './performance-monitor';

// Re-export commonly used types
export type {
  PerformanceMetrics,
  WebSocketMetrics,
  PerformanceAssessment,
} from './performance-monitor';

// Utility functions for common test operations
export const testUtils = {
  /**
   * Wait for animation to complete
   */
  waitForAnimation: async (page: any, duration = 500) => {
    await page.waitForTimeout(duration);
  },

  /**
   * Wait for network idle
   */
  waitForNetworkIdle: async (page: any, timeout = 5000) => {
    await page.waitForLoadState('networkidle', { timeout });
  },

  /**
   * Generate test data
   */
  generateTestData: (type: 'agent' | 'workflow' | 'command') => {
    switch (type) {
      case 'agent':
        return {
          id: `test-agent-${Date.now()}`,
          name: `Test Agent ${Math.random().toString(36).substr(2, 5)}`,
          status: 'active',
          role: 'tester'
        };
      
      case 'workflow':
        return {
          id: `test-workflow-${Date.now()}`,
          name: `Test Workflow ${Math.random().toString(36).substr(2, 5)}`,
          phase: 'planning',
          agents: ['agent-001', 'agent-002']
        };
      
      case 'command':
        return {
          id: `test-command-${Date.now()}`,
          command: `test-action-${Math.random().toString(36).substr(2, 5)}`,
          parameters: { test: true }
        };
      
      default:
        return { id: `test-${Date.now()}` };
    }
  },

  /**
   * Clean test data
   */
  cleanupTestData: async (page: any) => {
    await page.evaluate(() => {
      // Remove any test elements
      const testElements = document.querySelectorAll('[data-test], [id^="test-"]');
      testElements.forEach(element => element.remove());
      
      // Clear test data from storage
      try {
        localStorage.removeItem('khive-test-data');
        sessionStorage.removeItem('khive-test-data');
      } catch (error) {
        // Ignore storage errors
      }
    });
  }
};

// Constants for test configuration
export const TEST_CONSTANTS = {
  TIMEOUTS: {
    SHORT: 1000,
    MEDIUM: 5000,
    LONG: 10000,
    EXTRA_LONG: 30000
  },
  
  VIEWPORTS: {
    DESKTOP: { width: 1280, height: 720 },
    TABLET: { width: 768, height: 1024 },
    MOBILE: { width: 375, height: 667 }
  },
  
  URLS: {
    WEBSOCKET_MOCK: 'ws://localhost:8000',
    BASE_URL: 'http://localhost:3000'
  },
  
  SELECTORS: {
    COMMAND_PALETTE: '[data-testid="command-palette"]',
    COMMAND_INPUT: '[data-testid="command-input"]',
    TERMINAL_CONTENT: '[data-testid="terminal-content"]',
    ORCHESTRATION_TREE: '[data-testid="orchestration-tree"]',
    AGENT_NODE: '[data-testid="agent-node"]'
  }
};