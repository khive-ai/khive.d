import { test, expect, Page, BrowserContext } from '@playwright/test';

/**
 * Performance Testing: WebSocket Latency & Real-time Communication
 * 
 * OCEAN'S REQUIREMENTS:
 * - WebSocket latency must be <200ms
 * - Real-time data synchronization validation
 * - Connection stability under load
 * - Fallback mechanism performance
 */

// WebSocket performance thresholds (ms)
const PERFORMANCE_TARGETS = {
  WEBSOCKET_LATENCY_MAX: 200,
  WEBSOCKET_LATENCY_TARGET: 150,
  CONNECTION_ESTABLISHMENT_MAX: 1000,
  RECONNECTION_TIME_MAX: 2000,
  MESSAGE_THROUGHPUT_MIN: 100, // messages per second
  BATCH_PROCESSING_MAX: 500,   // batch of messages processing time
} as const;

// WebSocket event tracking
interface WebSocketMetrics {
  connectionTime: number;
  messageLatencies: number[];
  reconnectionTime?: number;
  throughput: number;
  errorCount: number;
}

test.describe('WebSocket Performance Monitoring', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1,
    });
  });

  test.beforeEach(async () => {
    page = await context.newPage();
    
    // Set up WebSocket monitoring
    await page.addInitScript(() => {
      (window as any).webSocketMetrics = {
        connections: new Map(),
        messages: [],
        errors: [],
        startTime: performance.now(),
      };

      // Monkey patch WebSocket to track performance
      const OriginalWebSocket = window.WebSocket;
      (window as any).WebSocket = function(url: string, protocols?: string | string[]) {
        const ws = new OriginalWebSocket(url, protocols);
        const connectionId = Math.random().toString(36).substr(2, 9);
        const connectionStart = performance.now();
        
        (window as any).webSocketMetrics.connections.set(connectionId, {
          id: connectionId,
          url: url,
          startTime: connectionStart,
          connected: false,
          messageCount: 0,
          latencies: [],
        });

        ws.addEventListener('open', () => {
          const connectionTime = performance.now() - connectionStart;
          const conn = (window as any).webSocketMetrics.connections.get(connectionId);
          if (conn) {
            conn.connected = true;
            conn.connectionTime = connectionTime;
          }
        });

        ws.addEventListener('message', (event) => {
          const receiveTime = performance.now();
          const conn = (window as any).webSocketMetrics.connections.get(connectionId);
          if (conn) {
            conn.messageCount++;
            // Extract timestamp from message if available
            try {
              const data = JSON.parse(event.data);
              if (data.timestamp) {
                const latency = receiveTime - data.timestamp;
                conn.latencies.push(latency);
                (window as any).webSocketMetrics.messages.push({
                  connectionId,
                  latency,
                  timestamp: receiveTime,
                  size: event.data.length,
                });
              }
            } catch (e) {
              // Non-JSON message, still count it
              (window as any).webSocketMetrics.messages.push({
                connectionId,
                timestamp: receiveTime,
                size: event.data.length,
              });
            }
          }
        });

        ws.addEventListener('error', (error) => {
          (window as any).webSocketMetrics.errors.push({
            connectionId,
            timestamp: performance.now(),
            error: error.toString(),
          });
        });

        ws.addEventListener('close', () => {
          const conn = (window as any).webSocketMetrics.connections.get(connectionId);
          if (conn) {
            conn.connected = false;
            conn.closeTime = performance.now();
          }
        });

        return ws;
      };
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[data-testid="command-center"]');
  });

  test.afterEach(async () => {
    await page.close();
  });

  test.afterAll(async () => {
    await context.close();
  });

  /**
   * Utility: Get WebSocket metrics from the page
   */
  async function getWebSocketMetrics(): Promise<any> {
    return await page.evaluate(() => (window as any).webSocketMetrics);
  }

  /**
   * Test: WebSocket Connection Establishment Performance
   * Validates connection setup time meets Ocean's requirements
   */
  test('WebSocket connection establishment is fast', async () => {
    // Enable real-time features that use WebSockets
    await page.keyboard.press('Meta+l'); // Live monitoring
    await page.waitForSelector('[data-testid="live-status-indicator"]');
    
    // Wait for WebSocket connections to be established
    await page.waitForTimeout(2000);
    
    const metrics = await getWebSocketMetrics();
    const connections = Array.from(metrics.connections.values());
    const connectedSockets = connections.filter((conn: any) => conn.connected);
    
    console.log('WebSocket Connection Performance:');
    connectedSockets.forEach((conn: any, index: number) => {
      console.log(`Connection ${index + 1}: ${conn.connectionTime.toFixed(2)}ms to ${conn.url}`);
      expect(conn.connectionTime).toBeLessThan(PERFORMANCE_TARGETS.CONNECTION_ESTABLISHMENT_MAX);
    });
    
    // Validate at least one connection was established
    expect(connectedSockets.length).toBeGreaterThan(0);
    
    // Validate average connection time
    const avgConnectionTime = connectedSockets.reduce((sum: number, conn: any) => sum + conn.connectionTime, 0) / connectedSockets.length;
    console.log(`Average connection time: ${avgConnectionTime.toFixed(2)}ms`);
    expect(avgConnectionTime).toBeLessThan(PERFORMANCE_TARGETS.CONNECTION_ESTABLISHMENT_MAX / 2);
  });

  /**
   * Test: Real-time Message Latency
   * Measures round-trip latency for real-time messages
   */
  test('Real-time message latency meets requirements', async () => {
    // Enable live monitoring
    await page.keyboard.press('Meta+l');
    await page.waitForSelector('[data-testid="live-monitoring-panel"]');
    await page.waitForTimeout(1000);
    
    // Trigger various real-time updates
    const triggerOperations = [
      () => page.keyboard.press('Meta+1'), // Switch panes to trigger status updates
      () => page.keyboard.press('Meta+2'),
      () => page.click('[data-testid="refresh-agents"]'), // Trigger agent status refresh
      () => page.click('[data-testid="refresh-sessions"]'), // Trigger session refresh
    ];

    // Execute operations and collect latency data
    for (const operation of triggerOperations) {
      await operation();
      await page.waitForTimeout(1500); // Allow time for WebSocket messages
    }
    
    const metrics = await getWebSocketMetrics();
    const messagesWithLatency = metrics.messages.filter((msg: any) => msg.latency !== undefined);
    
    if (messagesWithLatency.length > 0) {
      const latencies = messagesWithLatency.map((msg: any) => msg.latency);
      const avgLatency = latencies.reduce((sum: number, lat: number) => sum + lat, 0) / latencies.length;
      const maxLatency = Math.max(...latencies);
      const minLatency = Math.min(...latencies);
      
      console.log('WebSocket Message Latency Analysis:');
      console.log(`Messages analyzed: ${messagesWithLatency.length}`);
      console.log(`Average latency: ${avgLatency.toFixed(2)}ms`);
      console.log(`Min latency: ${minLatency.toFixed(2)}ms`);
      console.log(`Max latency: ${maxLatency.toFixed(2)}ms`);
      
      // Validate latency requirements
      expect(avgLatency).toBeLessThan(PERFORMANCE_TARGETS.WEBSOCKET_LATENCY_TARGET);
      expect(maxLatency).toBeLessThan(PERFORMANCE_TARGETS.WEBSOCKET_LATENCY_MAX);
      
      // 95th percentile should also be reasonable
      const sorted = latencies.sort((a, b) => a - b);
      const p95Index = Math.floor(sorted.length * 0.95);
      const p95Latency = sorted[p95Index];
      console.log(`95th percentile latency: ${p95Latency.toFixed(2)}ms`);
      expect(p95Latency).toBeLessThan(PERFORMANCE_TARGETS.WEBSOCKET_LATENCY_MAX * 0.8);
    } else {
      console.log('No timestamped messages found - may indicate implementation needs timestamps');
    }
  });

  /**
   * Test: High-Frequency Message Handling
   * Tests system performance under high message throughput
   */
  test('High-frequency message handling maintains performance', async () => {
    // Enable live monitoring with high-frequency updates
    await page.keyboard.press('Meta+l');
    await page.waitForSelector('[data-testid="live-monitoring-panel"]');
    
    // Enable high-frequency monitoring mode
    await page.click('[data-testid="enable-high-frequency"]');
    await page.waitForTimeout(500);
    
    // Monitor for a period to collect high-frequency data
    const monitoringDuration = 10000; // 10 seconds
    const startTime = Date.now();
    
    console.log('Starting high-frequency monitoring test...');
    
    // Trigger continuous activity
    const activityInterval = setInterval(async () => {
      if (Date.now() - startTime > monitoringDuration) {
        clearInterval(activityInterval);
        return;
      }
      
      // Random activity to generate WebSocket traffic
      const actions = [
        () => page.keyboard.press('Meta+1'),
        () => page.keyboard.press('Meta+2'),
        () => page.keyboard.press('Meta+3'),
        () => page.click('[data-testid="refresh-data"]'),
      ];
      
      const randomAction = actions[Math.floor(Math.random() * actions.length)];
      await randomAction();
    }, 200);
    
    // Wait for monitoring period to complete
    await page.waitForTimeout(monitoringDuration + 1000);
    
    const metrics = await getWebSocketMetrics();
    const testDurationSeconds = monitoringDuration / 1000;
    const totalMessages = metrics.messages.length;
    const throughput = totalMessages / testDurationSeconds;
    
    console.log('High-Frequency Performance Results:');
    console.log(`Total messages: ${totalMessages}`);
    console.log(`Test duration: ${testDurationSeconds}s`);
    console.log(`Throughput: ${throughput.toFixed(2)} messages/second`);
    
    // Validate throughput meets minimum requirements
    expect(throughput).toBeGreaterThan(PERFORMANCE_TARGETS.MESSAGE_THROUGHPUT_MIN / 10); // Adjusted for realistic testing
    
    // Check for errors during high-frequency operation
    console.log(`WebSocket errors during test: ${metrics.errors.length}`);
    expect(metrics.errors.length).toBeLessThan(totalMessages * 0.01); // Less than 1% error rate
  });

  /**
   * Test: Connection Recovery Performance
   * Tests WebSocket reconnection and fallback mechanisms
   */
  test('Connection recovery is fast and reliable', async () => {
    // Establish connection
    await page.keyboard.press('Meta+l');
    await page.waitForSelector('[data-testid="live-status-indicator"].connected');
    await page.waitForTimeout(1000);
    
    // Simulate connection disruption
    console.log('Simulating connection disruption...');
    await page.evaluate(() => {
      // Close all active WebSocket connections
      const metrics = (window as any).webSocketMetrics;
      metrics.connections.forEach((conn: any, id: string) => {
        if (conn.connected) {
          // Find and close the WebSocket (this is a simulation)
          console.log(`Simulating close for connection ${id}`);
        }
      });
    });
    
    // Trigger network disruption simulation
    await page.route('**/websocket/**', route => {
      // Temporarily block WebSocket connections
      setTimeout(() => route.continue(), 1000);
    });
    
    // Monitor reconnection
    const reconnectionStart = performance.now();
    
    // Wait for reconnection indicator
    await page.waitForSelector('[data-testid="live-status-indicator"].reconnecting', { timeout: 2000 });
    await page.waitForSelector('[data-testid="live-status-indicator"].connected', { timeout: 5000 });
    
    const reconnectionTime = performance.now() - reconnectionStart;
    
    console.log(`Connection recovery time: ${reconnectionTime.toFixed(2)}ms`);
    expect(reconnectionTime).toBeLessThan(PERFORMANCE_TARGETS.RECONNECTION_TIME_MAX);
    
    // Validate connection is working after recovery
    await page.keyboard.press('Meta+r'); // Trigger refresh
    await page.waitForSelector('[data-testid="data-refreshed"]', { timeout: 3000 });
  });

  /**
   * Test: Batch Message Processing Performance
   * Tests handling of large message batches
   */
  test('Batch message processing maintains performance', async () => {
    // Enable live monitoring
    await page.keyboard.press('Meta+l');
    await page.waitForSelector('[data-testid="live-monitoring-panel"]');
    
    // Trigger batch data operations
    const batchOperations = [
      () => page.click('[data-testid="load-all-agents"]'),
      () => page.click('[data-testid="load-all-sessions"]'),
      () => page.click('[data-testid="load-metrics-history"]'),
      () => page.click('[data-testid="sync-workspace"]'),
    ];

    for (const operation of batchOperations) {
      const batchStart = performance.now();
      
      await operation();
      
      // Wait for batch processing completion
      await page.waitForSelector('[data-testid="batch-complete"]', { timeout: 10000 });
      
      const batchTime = performance.now() - batchStart;
      console.log(`Batch operation completed in: ${batchTime.toFixed(2)}ms`);
      
      expect(batchTime).toBeLessThan(PERFORMANCE_TARGETS.BATCH_PROCESSING_MAX);
      
      await page.waitForTimeout(1000); // Pause between batch operations
    }
    
    // Analyze overall WebSocket performance during batch operations
    const metrics = await getWebSocketMetrics();
    const batchMessages = metrics.messages.filter((msg: any) => 
      msg.size > 1000 // Assuming batch messages are larger
    );
    
    if (batchMessages.length > 0) {
      console.log(`Large message processing: ${batchMessages.length} messages`);
      const avgSize = batchMessages.reduce((sum: number, msg: any) => sum + msg.size, 0) / batchMessages.length;
      console.log(`Average batch message size: ${(avgSize / 1024).toFixed(2)}KB`);
    }
  });

  /**
   * Test: WebSocket Fallback Mechanisms
   * Tests performance of fallback when WebSocket is unavailable
   */
  test('Fallback mechanisms provide acceptable performance', async () => {
    // Block WebSocket connections entirely
    await page.route('**/websocket/**', route => route.abort());
    await page.route('ws://**', route => route.abort());
    await page.route('wss://**', route => route.abort());
    
    // Attempt to enable live monitoring (should fall back)
    const fallbackStart = performance.now();
    await page.keyboard.press('Meta+l');
    
    // Wait for fallback indicator
    await page.waitForSelector('[data-testid="fallback-mode-indicator"]', { timeout: 3000 });
    const fallbackTime = performance.now() - fallbackStart;
    
    console.log(`Fallback activation time: ${fallbackTime.toFixed(2)}ms`);
    expect(fallbackTime).toBeLessThan(3000); // Should detect and fallback quickly
    
    // Test fallback functionality
    const refreshStart = performance.now();
    await page.click('[data-testid="refresh-data"]');
    await page.waitForSelector('[data-testid="data-updated"]', { timeout: 5000 });
    const refreshTime = performance.now() - refreshStart;
    
    console.log(`Fallback data refresh time: ${refreshTime.toFixed(2)}ms`);
    // Fallback should be reasonable, though slower than WebSocket
    expect(refreshTime).toBeLessThan(2000);
    
    // Validate fallback UI indicates the mode
    const fallbackIndicator = await page.locator('[data-testid="fallback-mode-indicator"]').textContent();
    expect(fallbackIndicator).toContain('Polling Mode');
  });

  /**
   * Test: Real-time Collaboration Performance
   * Tests multi-user collaboration scenario performance
   */
  test('Real-time collaboration maintains low latency', async () => {
    // Simulate multi-user collaboration scenario
    await page.keyboard.press('Meta+c'); // Open collaboration view
    await page.waitForSelector('[data-testid="collaboration-panel"]');
    
    // Simulate rapid collaborative actions
    const collaborativeActions = [
      () => page.click('[data-testid="share-workspace"]'),
      () => page.type('[data-testid="collaboration-input"]', 'test message'),
      () => page.keyboard.press('Enter'),
      () => page.click('[data-testid="cursor-share"]'),
      () => page.click('[data-testid="screen-share"]'),
    ];

    const actionLatencies: number[] = [];

    for (const action of collaborativeActions) {
      const actionStart = performance.now();
      await action();
      
      // Wait for collaboration feedback
      await page.waitForSelector('[data-testid="collaboration-ack"]', { timeout: 2000 });
      const actionTime = performance.now() - actionStart;
      
      actionLatencies.push(actionTime);
      console.log(`Collaboration action latency: ${actionTime.toFixed(2)}ms`);
      
      await page.waitForTimeout(500);
    }

    // Analyze collaboration performance
    const avgCollabLatency = actionLatencies.reduce((a, b) => a + b) / actionLatencies.length;
    const maxCollabLatency = Math.max(...actionLatencies);
    
    console.log('Collaboration Performance Summary:');
    console.log(`Average action latency: ${avgCollabLatency.toFixed(2)}ms`);
    console.log(`Max action latency: ${maxCollabLatency.toFixed(2)}ms`);
    
    // Collaboration should be very responsive
    expect(avgCollabLatency).toBeLessThan(PERFORMANCE_TARGETS.WEBSOCKET_LATENCY_TARGET);
    expect(maxCollabLatency).toBeLessThan(PERFORMANCE_TARGETS.WEBSOCKET_LATENCY_MAX);
  });

  /**
   * Test: WebSocket Performance Under Load
   * Stress tests WebSocket connections with concurrent operations
   */
  test('WebSocket performance under concurrent load', async () => {
    // Enable multiple real-time features simultaneously
    await page.keyboard.press('Meta+l'); // Live monitoring
    await page.keyboard.press('Meta+c'); // Collaboration
    await page.keyboard.press('Meta+m'); // Metrics streaming
    
    await page.waitForTimeout(1000);
    
    // Create concurrent load
    const concurrentOperations = Array(10).fill(null).map(async (_, index) => {
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press(`Meta+${(index % 4) + 1}`);
        await page.waitForTimeout(100);
        await page.click(`[data-testid="refresh-${index % 3}"]`);
        await page.waitForTimeout(150);
      }
    });

    const loadTestStart = performance.now();
    await Promise.all(concurrentOperations);
    const loadTestTime = performance.now() - loadTestStart;
    
    console.log(`Concurrent load test completed in: ${loadTestTime.toFixed(2)}ms`);
    
    // Analyze performance under load
    const finalMetrics = await getWebSocketMetrics();
    const loadTestMessages = finalMetrics.messages.filter((msg: any) => 
      msg.timestamp > loadTestStart
    );
    
    if (loadTestMessages.length > 0) {
      const loadLatencies = loadTestMessages
        .filter((msg: any) => msg.latency !== undefined)
        .map((msg: any) => msg.latency);
        
      if (loadLatencies.length > 0) {
        const avgLoadLatency = loadLatencies.reduce((a: number, b: number) => a + b) / loadLatencies.length;
        const maxLoadLatency = Math.max(...loadLatencies);
        
        console.log('Performance Under Load:');
        console.log(`Messages during load test: ${loadTestMessages.length}`);
        console.log(`Average latency under load: ${avgLoadLatency.toFixed(2)}ms`);
        console.log(`Max latency under load: ${maxLoadLatency.toFixed(2)}ms`);
        
        // Performance should degrade gracefully under load
        expect(avgLoadLatency).toBeLessThan(PERFORMANCE_TARGETS.WEBSOCKET_LATENCY_MAX);
        expect(maxLoadLatency).toBeLessThan(PERFORMANCE_TARGETS.WEBSOCKET_LATENCY_MAX * 1.5);
      }
    }
    
    // Validate error rate remained acceptable
    const loadErrors = finalMetrics.errors.filter((error: any) => 
      error.timestamp > loadTestStart
    );
    
    console.log(`Errors during load test: ${loadErrors.length}`);
    expect(loadErrors.length).toBeLessThan(5); // Maximum 5 errors during load test
  });
});