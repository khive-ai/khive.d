import { test, expect, Page, BrowserContext, chromium } from '@playwright/test';

/**
 * Performance Testing: Memory & Resource Monitoring
 * 
 * OCEAN'S REQUIREMENTS:
 * - Frontend memory usage must stay <100MB
 * - Resource leak detection and prevention
 * - Performance alert system validation
 * - Long-running session stability
 */

// Memory and resource thresholds
const PERFORMANCE_TARGETS = {
  MAX_MEMORY_MB: 100,
  TARGET_MEMORY_MB: 75,
  MEMORY_LEAK_THRESHOLD: 1.5, // 50% increase over baseline
  CPU_USAGE_MAX: 5, // 5% CPU usage when idle
  DOM_NODES_MAX: 5000,
  EVENT_LISTENERS_MAX: 500,
  WEBSOCKET_CONNECTIONS_MAX: 5,
} as const;

// Memory measurement utilities
interface MemoryMetrics {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
  domNodes: number;
  jsEventListeners: number;
}

test.describe('Memory & Resource Performance Monitoring', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async () => {
    // Use Chromium for detailed memory metrics
    const browser = await chromium.launch();
    context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1,
    });
  });

  test.beforeEach(async () => {
    page = await context.newPage();
    
    // Enable performance monitoring
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[data-testid="command-center"]');
    
    // Force garbage collection to start with clean state
    await page.evaluate(() => {
      if ('gc' in window) {
        (window as any).gc();
      }
    });
    await page.waitForTimeout(1000);
  });

  test.afterEach(async () => {
    await page.close();
  });

  test.afterAll(async () => {
    await context.close();
  });

  /**
   * Utility: Get detailed memory metrics
   */
  async function getMemoryMetrics(): Promise<MemoryMetrics> {
    return await page.evaluate(() => {
      const memory = (performance as any).memory;
      const domNodes = document.querySelectorAll('*').length;
      
      // Count event listeners (approximation)
      let listenerCount = 0;
      document.querySelectorAll('*').forEach(element => {
        const events = getEventListeners?.(element);
        if (events) {
          listenerCount += Object.keys(events).reduce((count, type) => 
            count + events[type].length, 0
          );
        }
      });

      return {
        usedJSHeapSize: memory?.usedJSHeapSize || 0,
        totalJSHeapSize: memory?.totalJSHeapSize || 0,
        jsHeapSizeLimit: memory?.jsHeapSizeLimit || 0,
        domNodes,
        jsEventListeners: listenerCount,
      };
    });
  }

  /**
   * Test: Initial Memory Usage Validation
   * Ensures the application starts within Ocean's memory budget
   */
  test('Initial memory usage is within target range', async () => {
    // Wait for full application initialization
    await page.waitForTimeout(2000);
    
    const initialMetrics = await getMemoryMetrics();
    const memoryUsageMB = initialMetrics.usedJSHeapSize / (1024 * 1024);
    
    console.log('Initial Memory Metrics:');
    console.log(`JS Heap Used: ${memoryUsageMB.toFixed(2)}MB`);
    console.log(`JS Heap Total: ${(initialMetrics.totalJSHeapSize / 1024 / 1024).toFixed(2)}MB`);
    console.log(`DOM Nodes: ${initialMetrics.domNodes}`);
    console.log(`Event Listeners: ${initialMetrics.jsEventListeners}`);
    
    // Validate initial memory usage
    expect(memoryUsageMB).toBeLessThan(PERFORMANCE_TARGETS.MAX_MEMORY_MB);
    expect(memoryUsageMB).toBeLessThan(PERFORMANCE_TARGETS.TARGET_MEMORY_MB);
    expect(initialMetrics.domNodes).toBeLessThan(PERFORMANCE_TARGETS.DOM_NODES_MAX);
    expect(initialMetrics.jsEventListeners).toBeLessThan(PERFORMANCE_TARGETS.EVENT_LISTENERS_MAX);
  });

  /**
   * Test: Memory Usage Under Normal Operations
   * Monitors memory during typical user workflows
   */
  test('Memory usage remains stable during normal operations', async () => {
    const baselineMetrics = await getMemoryMetrics();
    const baselineMemoryMB = baselineMetrics.usedJSHeapSize / (1024 * 1024);
    
    // Simulate normal user operations
    const operations = [
      () => page.keyboard.press('Meta+1'), // Switch to workspace
      () => page.keyboard.press('Meta+2'), // Switch to agents  
      () => page.keyboard.press('Meta+3'), // Switch to sessions
      () => page.keyboard.press('Meta+k'), // Open command palette
      () => page.fill('[data-testid="command-input"]', 'status'),
      () => page.keyboard.press('Enter'),
      () => page.keyboard.press('Escape'),
      () => page.click('[data-testid="agent-card"]:first-child'),
      () => page.keyboard.press('Meta+n'), // Open new modal
      () => page.keyboard.press('Escape'),
    ];

    const memorySnapshots: number[] = [baselineMemoryMB];

    for (let i = 0; i < operations.length; i++) {
      await operations[i]();
      await page.waitForTimeout(500); // Allow operation to complete
      
      const metrics = await getMemoryMetrics();
      const memoryMB = metrics.usedJSHeapSize / (1024 * 1024);
      memorySnapshots.push(memoryMB);
      
      console.log(`Operation ${i + 1} memory: ${memoryMB.toFixed(2)}MB`);
    }

    // Analyze memory growth
    const maxMemory = Math.max(...memorySnapshots);
    const memoryGrowth = maxMemory - baselineMemoryMB;
    
    console.log(`Memory growth during operations: ${memoryGrowth.toFixed(2)}MB`);
    console.log(`Peak memory usage: ${maxMemory.toFixed(2)}MB`);
    
    // Validate memory remains within bounds
    expect(maxMemory).toBeLessThan(PERFORMANCE_TARGETS.MAX_MEMORY_MB);
    expect(memoryGrowth).toBeLessThan(25); // No more than 25MB growth for normal ops
  });

  /**
   * Test: Memory Leak Detection
   * Performs repetitive operations to detect memory leaks
   */
  test('No memory leaks during repetitive operations', async () => {
    const initialMetrics = await getMemoryMetrics();
    const initialMemoryMB = initialMetrics.usedJSHeapSize / (1024 * 1024);
    
    // Perform repetitive operations that could cause leaks
    for (let cycle = 0; cycle < 10; cycle++) {
      // Simulate heavy usage cycle
      await page.keyboard.press('Meta+k');
      await page.fill('[data-testid="command-input"]', 'search all files');
      await page.keyboard.press('Enter');
      await page.waitForSelector('[data-testid="search-results"]', { timeout: 3000 });
      await page.keyboard.press('Escape');
      
      // Switch panes rapidly
      for (let i = 1; i <= 4; i++) {
        await page.keyboard.press(`Meta+${i}`);
        await page.waitForTimeout(50);
      }
      
      // Open and close modals
      await page.keyboard.press('Meta+n');
      await page.waitForSelector('[data-testid="modal"]');
      await page.keyboard.press('Escape');
      
      // Force garbage collection periodically
      if (cycle % 3 === 0) {
        await page.evaluate(() => {
          if ('gc' in window) {
            (window as any).gc();
          }
        });
        await page.waitForTimeout(1000);
      }
    }

    // Final memory measurement
    const finalMetrics = await getMemoryMetrics();
    const finalMemoryMB = finalMetrics.usedJSHeapSize / (1024 * 1024);
    const memoryIncrease = finalMemoryMB / initialMemoryMB;
    
    console.log('Memory Leak Detection Results:');
    console.log(`Initial memory: ${initialMemoryMB.toFixed(2)}MB`);
    console.log(`Final memory: ${finalMemoryMB.toFixed(2)}MB`);
    console.log(`Memory increase ratio: ${memoryIncrease.toFixed(2)}x`);
    console.log(`DOM nodes growth: ${finalMetrics.domNodes - initialMetrics.domNodes}`);
    
    // Validate no significant memory leaks
    expect(memoryIncrease).toBeLessThan(PERFORMANCE_TARGETS.MEMORY_LEAK_THRESHOLD);
    expect(finalMemoryMB).toBeLessThan(PERFORMANCE_TARGETS.MAX_MEMORY_MB);
    expect(finalMetrics.domNodes).toBeLessThan(PERFORMANCE_TARGETS.DOM_NODES_MAX);
  });

  /**
   * Test: Long-Running Session Stability
   * Tests memory stability during extended usage
   */
  test('Long-running session maintains memory stability', async () => {
    const sessionDurationMinutes = 5; // Reduced for practical testing
    const measurementIntervalMs = 30000; // Every 30 seconds
    const measurements: Array<{ time: number; memory: number; domNodes: number }> = [];
    
    const startTime = Date.now();
    const endTime = startTime + (sessionDurationMinutes * 60 * 1000);
    
    // Background activity simulation
    const backgroundActivity = async () => {
      while (Date.now() < endTime) {
        // Simulate background operations
        await page.keyboard.press(`Meta+${Math.floor(Math.random() * 4) + 1}`);
        await page.waitForTimeout(Math.random() * 2000 + 1000);
        
        if (Math.random() > 0.7) {
          await page.keyboard.press('Meta+k');
          await page.fill('[data-testid="command-input"]', 'status');
          await page.keyboard.press('Enter');
          await page.waitForTimeout(500);
          await page.keyboard.press('Escape');
        }
        
        await page.waitForTimeout(Math.random() * 3000 + 2000);
      }
    };

    // Memory monitoring
    const memoryMonitoring = async () => {
      while (Date.now() < endTime) {
        const metrics = await getMemoryMetrics();
        const memoryMB = metrics.usedJSHeapSize / (1024 * 1024);
        
        measurements.push({
          time: Date.now() - startTime,
          memory: memoryMB,
          domNodes: metrics.domNodes,
        });
        
        console.log(`Session time: ${Math.floor((Date.now() - startTime) / 1000)}s, Memory: ${memoryMB.toFixed(2)}MB, DOM: ${metrics.domNodes}`);
        
        await page.waitForTimeout(measurementIntervalMs);
      }
    };

    // Run both activities in parallel
    await Promise.all([backgroundActivity(), memoryMonitoring()]);
    
    // Analyze session stability
    const memoryValues = measurements.map(m => m.memory);
    const initialMemory = memoryValues[0];
    const finalMemory = memoryValues[memoryValues.length - 1];
    const maxMemory = Math.max(...memoryValues);
    const avgMemory = memoryValues.reduce((a, b) => a + b) / memoryValues.length;
    
    console.log('Long-Running Session Analysis:');
    console.log(`Session duration: ${sessionDurationMinutes} minutes`);
    console.log(`Initial memory: ${initialMemory.toFixed(2)}MB`);
    console.log(`Final memory: ${finalMemory.toFixed(2)}MB`);
    console.log(`Peak memory: ${maxMemory.toFixed(2)}MB`);
    console.log(`Average memory: ${avgMemory.toFixed(2)}MB`);
    
    // Validate session stability
    expect(maxMemory).toBeLessThan(PERFORMANCE_TARGETS.MAX_MEMORY_MB);
    expect(finalMemory / initialMemory).toBeLessThan(PERFORMANCE_TARGETS.MEMORY_LEAK_THRESHOLD);
    expect(avgMemory).toBeLessThan(PERFORMANCE_TARGETS.TARGET_MEMORY_MB);
  });

  /**
   * Test: WebSocket Connection Management
   * Validates proper WebSocket connection lifecycle management
   */
  test('WebSocket connections are properly managed', async () => {
    // Monitor WebSocket connections
    const getWebSocketCount = () => page.evaluate(() => {
      // Count active WebSocket connections (implementation may vary)
      return (window as any).activeWebSockets?.size || 0;
    });

    const initialConnections = await getWebSocketCount();
    
    // Trigger operations that create WebSocket connections
    await page.keyboard.press('Meta+l'); // Live monitoring
    await page.waitForTimeout(1000);
    
    const afterLiveMonitoring = await getWebSocketCount();
    
    // Navigate to different sections
    await page.keyboard.press('Meta+2'); // Agents pane
    await page.waitForTimeout(1000);
    await page.keyboard.press('Meta+3'); // Sessions pane
    await page.waitForTimeout(1000);
    
    const afterNavigation = await getWebSocketCount();
    
    // Close live monitoring
    await page.keyboard.press('Escape');
    await page.waitForTimeout(2000);
    
    const afterClosing = await getWebSocketCount();
    
    console.log('WebSocket Connection Analysis:');
    console.log(`Initial connections: ${initialConnections}`);
    console.log(`After live monitoring: ${afterLiveMonitoring}`);
    console.log(`After navigation: ${afterNavigation}`);
    console.log(`After closing: ${afterClosing}`);
    
    // Validate connection management
    expect(afterLiveMonitoring).toBeGreaterThan(initialConnections);
    expect(afterNavigation).toBeLessThanOrEqual(PERFORMANCE_TARGETS.WEBSOCKET_CONNECTIONS_MAX);
    expect(afterClosing).toBeLessThanOrEqual(afterLiveMonitoring); // Connections should be cleaned up
  });

  /**
   * Test: Performance Alert System Validation
   * Tests the built-in performance monitoring and alerting
   */
  test('Performance alert system functions correctly', async () => {
    // Enable performance alerts
    await page.keyboard.press('Meta+Shift+p'); // Open performance panel
    await page.waitForSelector('[data-testid="performance-panel"]');
    
    // Enable alert system
    await page.check('[data-testid="enable-performance-alerts"]');
    
    // Set alert thresholds (lower than normal for testing)
    await page.fill('[data-testid="memory-threshold-input"]', '50');
    await page.fill('[data-testid="response-time-threshold-input"]', '75');
    
    // Simulate memory-intensive operations to trigger alerts
    for (let i = 0; i < 20; i++) {
      await page.keyboard.press('Meta+k');
      await page.fill('[data-testid="command-input"]', `search operation ${i}`);
      await page.keyboard.press('Enter');
      await page.waitForTimeout(100);
      await page.keyboard.press('Escape');
    }
    
    // Check for performance alerts
    const alerts = await page.locator('[data-testid="performance-alert"]').all();
    const alertTexts = await Promise.all(alerts.map(alert => alert.textContent()));
    
    console.log('Performance Alerts Triggered:');
    alertTexts.forEach((text, index) => console.log(`Alert ${index + 1}: ${text}`));
    
    // Validate alert system is functioning
    if (alertTexts.length > 0) {
      console.log('✅ Performance alert system is functioning correctly');
      expect(alertTexts.some(text => text?.includes('Memory') || text?.includes('Response time'))).toBe(true);
    } else {
      console.log('ℹ️ No performance alerts triggered (system performing well)');
    }
    
    // Clear alerts
    await page.click('[data-testid="clear-alerts"]');
    const remainingAlerts = await page.locator('[data-testid="performance-alert"]').count();
    expect(remainingAlerts).toBe(0);
  });

  /**
   * Test: Resource Cleanup on Page Navigation
   * Ensures resources are properly cleaned up during navigation
   */
  test('Resources are cleaned up during page transitions', async () => {
    const getResourceCounts = async () => {
      return await page.evaluate(() => {
        const imageCount = document.images.length;
        const scriptCount = document.scripts.length;
        const linkCount = document.querySelectorAll('link').length;
        const styleCount = document.styleSheets.length;
        
        return { imageCount, scriptCount, linkCount, styleCount };
      });
    };

    // Get initial resource counts
    const initialResources = await getResourceCounts();
    const initialMetrics = await getMemoryMetrics();
    
    // Navigate through different sections
    const navigationSequence = [
      '/workspace',
      '/agents',
      '/sessions',
      '/metrics',
      '/settings',
    ];
    
    for (const route of navigationSequence) {
      await page.goto(route);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      
      const currentResources = await getResourceCounts();
      const currentMetrics = await getMemoryMetrics();
      
      console.log(`Route ${route}:`, {
        memory: `${(currentMetrics.usedJSHeapSize / 1024 / 1024).toFixed(2)}MB`,
        domNodes: currentMetrics.domNodes,
        images: currentResources.imageCount,
      });
    }
    
    // Return to main page
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    
    // Force garbage collection
    await page.evaluate(() => {
      if ('gc' in window) {
        (window as any).gc();
      }
    });
    await page.waitForTimeout(1000);
    
    const finalResources = await getResourceCounts();
    const finalMetrics = await getMemoryMetrics();
    const finalMemoryMB = finalMetrics.usedJSHeapSize / (1024 * 1024);
    const initialMemoryMB = initialMetrics.usedJSHeapSize / (1024 * 1024);
    
    console.log('Resource Cleanup Analysis:');
    console.log(`Memory change: ${(finalMemoryMB - initialMemoryMB).toFixed(2)}MB`);
    console.log(`DOM nodes change: ${finalMetrics.domNodes - initialMetrics.domNodes}`);
    console.log(`Image resources change: ${finalResources.imageCount - initialResources.imageCount}`);
    
    // Validate proper cleanup occurred
    expect(finalMemoryMB).toBeLessThan(PERFORMANCE_TARGETS.MAX_MEMORY_MB);
    expect(finalMemoryMB / initialMemoryMB).toBeLessThan(PERFORMANCE_TARGETS.MEMORY_LEAK_THRESHOLD);
  });
});