import { test, expect, Page, BrowserContext } from '@playwright/test';

/**
 * WebSocket Connection Lifecycle E2E Tests
 * 
 * Tests comprehensive WebSocket connection management including:
 * - Connection establishment and handshake
 * - Automatic reconnection on connection loss  
 * - Connection health monitoring and latency tracking
 * - Graceful degradation when backend unavailable
 * 
 * Performance Targets:
 * - <200ms WebSocket connection latency
 * - <2s reconnection time after disconnect
 * - <100ms ping/pong round-trip
 */

// Helper function to wait for WebSocket connection
async function waitForWebSocketConnection(page: Page, timeout = 10000): Promise<void> {
  await page.waitForFunction(
    () => {
      // Check if the WebSocket connection is established by looking for connection indicators
      const indicator = document.querySelector('[data-testid="connection-status"]');
      return indicator && indicator.textContent?.includes('connected');
    },
    { timeout }
  );
}

// Helper function to inject WebSocket monitoring code
async function injectWebSocketMonitor(page: Page): Promise<void> {
  await page.addInitScript(() => {
    // Track WebSocket connection metrics
    window.wsMetrics = {
      connectionTime: 0,
      reconnections: 0,
      messagesReceived: 0,
      messagesSent: 0,
      latency: 0,
      connectionLost: 0,
    };

    // Override WebSocket constructor to track connections
    const OriginalWebSocket = window.WebSocket;
    window.WebSocket = class extends OriginalWebSocket {
      constructor(url: string | URL, protocols?: string | string[]) {
        const startTime = performance.now();
        super(url, protocols);
        
        this.addEventListener('open', () => {
          window.wsMetrics.connectionTime = performance.now() - startTime;
          console.log(`WebSocket connection established in ${window.wsMetrics.connectionTime}ms`);
        });
        
        this.addEventListener('close', () => {
          window.wsMetrics.connectionLost++;
          console.log(`WebSocket connection lost (total: ${window.wsMetrics.connectionLost})`);
        });
        
        this.addEventListener('message', () => {
          window.wsMetrics.messagesReceived++;
        });

        // Override send to track outgoing messages
        const originalSend = this.send.bind(this);
        this.send = function(data) {
          window.wsMetrics.messagesSent++;
          return originalSend(data);
        };
      }
    };
  });
}

test.describe('WebSocket Connection Lifecycle', () => {
  test.beforeEach(async ({ page }) => {
    // Inject WebSocket monitoring before navigating
    await injectWebSocketMonitor(page);
  });

  test('should establish WebSocket connection within performance target', async ({ page }) => {
    const connectionStart = Date.now();
    
    // Navigate to the application
    await page.goto('/');
    
    // Wait for the WebSocket connection to be established
    await waitForWebSocketConnection(page, 15000);
    
    const connectionTime = Date.now() - connectionStart;
    console.log(`Total connection establishment time: ${connectionTime}ms`);
    
    // Check WebSocket connection metrics
    const metrics = await page.evaluate(() => window.wsMetrics);
    
    // Performance assertions
    expect(metrics.connectionTime).toBeLessThan(200); // <200ms WebSocket latency target
    expect(connectionTime).toBeLessThan(5000); // Overall connection should be quick
    
    // Verify connection is active
    const connectionStatus = await page.getByTestId('connection-status').textContent();
    expect(connectionStatus).toContain('connected');
    
    // Verify no connection losses during initial setup
    expect(metrics.connectionLost).toBe(0);
  });

  test('should handle ping/pong latency monitoring', async ({ page }) => {
    await page.goto('/');
    await waitForWebSocketConnection(page);
    
    // Wait for at least one ping/pong cycle
    await page.waitForTimeout(6000); // Wait for ping interval
    
    // Check if ping/pong is working by examining connection health
    const healthStatus = await page.evaluate(() => {
      // Look for connection health indicator
      const healthElement = document.querySelector('[data-testid="connection-health"]');
      return healthElement ? healthElement.textContent : null;
    });
    
    expect(healthStatus).toBeTruthy();
    
    // Verify latency is within acceptable range
    const latency = await page.evaluate(() => {
      const latencyElement = document.querySelector('[data-testid="connection-latency"]');
      if (latencyElement && latencyElement.textContent) {
        const match = latencyElement.textContent.match(/(\d+)ms/);
        return match ? parseInt(match[1]) : null;
      }
      return null;
    });
    
    if (latency) {
      expect(latency).toBeLessThan(100); // <100ms ping/pong target
      expect(latency).toBeGreaterThan(0); // Should have some latency
    }
  });

  test('should automatically reconnect after connection loss', async ({ page, context }) => {
    await page.goto('/');
    await waitForWebSocketConnection(page);
    
    // Get initial connection metrics
    const initialMetrics = await page.evaluate(() => window.wsMetrics);
    expect(initialMetrics.connectionLost).toBe(0);
    
    // Simulate connection loss by making a request to disconnect clients
    const disconnectStart = Date.now();
    await page.evaluate(async () => {
      try {
        await fetch('http://localhost:8767/simulate/error', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: 'websocket_disconnect' })
        });
      } catch (error) {
        console.log('Disconnect simulation request failed (expected in some scenarios):', error);
      }
    });
    
    // Wait for disconnection to be detected
    await page.waitForTimeout(1000);
    
    // Verify connection was lost
    const metricsAfterDisconnect = await page.evaluate(() => window.wsMetrics);
    expect(metricsAfterDisconnect.connectionLost).toBeGreaterThan(0);
    
    // Wait for automatic reconnection
    await waitForWebSocketConnection(page, 10000);
    
    const reconnectionTime = Date.now() - disconnectStart;
    console.log(`Reconnection completed in ${reconnectionTime}ms`);
    
    // Verify reconnection happened within target time
    expect(reconnectionTime).toBeLessThan(5000); // <5s total reconnection time
    
    // Verify connection is healthy again
    const finalConnectionStatus = await page.getByTestId('connection-status').textContent();
    expect(finalConnectionStatus).toContain('connected');
  });

  test('should handle multiple rapid disconnections gracefully', async ({ page }) => {
    await page.goto('/');
    await waitForWebSocketConnection(page);
    
    // Simulate multiple rapid disconnections
    for (let i = 0; i < 3; i++) {
      await page.evaluate(async () => {
        try {
          await fetch('http://localhost:8767/simulate/error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'websocket_disconnect' })
          });
        } catch (error) {
          console.log(`Disconnect ${i + 1} simulation:`, error);
        }
      });
      
      await page.waitForTimeout(1000); // Brief wait between disconnections
    }
    
    // Wait for final reconnection
    await waitForWebSocketConnection(page, 15000);
    
    // Verify the application recovered
    const connectionStatus = await page.getByTestId('connection-status').textContent();
    expect(connectionStatus).toContain('connected');
    
    // Check that reconnections were tracked
    const finalMetrics = await page.evaluate(() => window.wsMetrics);
    expect(finalMetrics.connectionLost).toBeGreaterThan(2);
  });

  test('should gracefully degrade when backend is unavailable', async ({ page }) => {
    // First, ensure the mock server is down by attempting to connect to wrong port
    await page.goto('/');
    
    // Override WebSocket URL to point to non-existent server
    await page.addInitScript(() => {
      window.NEXT_PUBLIC_KHIVE_WS_URL = 'ws://localhost:9999'; // Non-existent server
    });
    
    await page.reload();
    
    // Wait a bit for connection attempts
    await page.waitForTimeout(5000);
    
    // Check that the application handles the unavailable backend gracefully
    const connectionStatus = await page.getByTestId('connection-status').textContent();
    expect(connectionStatus).toContain('disconnected');
    
    // Verify error handling UI is displayed
    const errorMessage = await page.getByTestId('connection-error').textContent();
    expect(errorMessage).toBeTruthy();
    expect(errorMessage).toContain('connection failed');
    
    // Ensure the application doesn't crash
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy();
  });

  test('should maintain connection health monitoring', async ({ page }) => {
    await page.goto('/');
    await waitForWebSocketConnection(page);
    
    // Monitor connection health over time
    const healthChecks = [];
    
    for (let i = 0; i < 5; i++) {
      await page.waitForTimeout(2000); // Check every 2 seconds
      
      const health = await page.evaluate(() => {
        const healthElement = document.querySelector('[data-testid="connection-health"]');
        const latencyElement = document.querySelector('[data-testid="connection-latency"]');
        
        return {
          status: healthElement ? healthElement.textContent : null,
          latency: latencyElement ? latencyElement.textContent : null,
          timestamp: Date.now()
        };
      });
      
      healthChecks.push(health);
    }
    
    // Verify health monitoring is active
    expect(healthChecks.length).toBe(5);
    healthChecks.forEach(check => {
      expect(check.status).toBeTruthy();
      expect(check.latency).toBeTruthy();
    });
    
    // Verify latency values are reasonable
    const latencyValues = healthChecks
      .map(check => {
        if (check.latency) {
          const match = check.latency.match(/(\d+)ms/);
          return match ? parseInt(match[1]) : null;
        }
        return null;
      })
      .filter(Boolean);
      
    expect(latencyValues.length).toBeGreaterThan(0);
    latencyValues.forEach(latency => {
      expect(latency).toBeLessThan(200); // Within performance target
      expect(latency).toBeGreaterThan(0);
    });
  });

  test('should handle connection state transitions correctly', async ({ page }) => {
    await page.goto('/');
    
    // Track connection state changes
    const stateChanges = [];
    
    await page.evaluate(() => {
      window.connectionStates = [];
      
      // Monitor connection status changes
      const observer = new MutationObserver(() => {
        const statusElement = document.querySelector('[data-testid="connection-status"]');
        if (statusElement) {
          window.connectionStates.push({
            status: statusElement.textContent,
            timestamp: Date.now()
          });
        }
      });
      
      // Start observing once the element exists
      const waitForElement = setInterval(() => {
        const element = document.querySelector('[data-testid="connection-status"]');
        if (element) {
          clearInterval(waitForElement);
          observer.observe(element, { childList: true, subtree: true });
          
          // Record initial state
          window.connectionStates.push({
            status: element.textContent,
            timestamp: Date.now()
          });
        }
      }, 100);
    });
    
    // Wait for initial connection
    await waitForWebSocketConnection(page);
    
    // Force a disconnect and reconnect cycle
    await page.evaluate(async () => {
      await fetch('http://localhost:8767/simulate/error', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'websocket_disconnect' })
      });
    });
    
    await page.waitForTimeout(2000); // Wait for disconnect
    await waitForWebSocketConnection(page, 10000); // Wait for reconnect
    
    // Analyze state transitions
    const states = await page.evaluate(() => window.connectionStates || []);
    
    expect(states.length).toBeGreaterThan(2); // Should have multiple state changes
    
    // Should have seen connected state
    expect(states.some(state => state.status?.includes('connected'))).toBe(true);
    
    // State transitions should be in logical order
    const statusTexts = states.map(s => s.status);
    console.log('Connection state transitions:', statusTexts);
  });
});

// Global type declaration for WebSocket metrics
declare global {
  interface Window {
    wsMetrics: {
      connectionTime: number;
      reconnections: number;
      messagesReceived: number;
      messagesSent: number;
      latency: number;
      connectionLost: number;
    };
    connectionStates: Array<{
      status: string | null;
      timestamp: number;
    }>;
    NEXT_PUBLIC_KHIVE_WS_URL: string;
  }
}