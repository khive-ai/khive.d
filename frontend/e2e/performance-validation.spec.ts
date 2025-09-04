import { test, expect, Page } from '@playwright/test';

/**
 * Performance Validation E2E Tests
 * 
 * Validates specific performance targets for KHIVE WebSocket integration:
 * - <200ms WebSocket connection latency
 * - <100ms command response time
 * - Connection resilience and error recovery
 * - Real-time event propagation performance
 * - Concurrent operation performance
 * 
 * This test suite provides comprehensive performance metrics and validation
 * against Ocean's specified performance targets.
 */

interface PerformanceMetrics {
  webSocketLatency: number[];
  commandResponseTimes: number[];
  eventPropagationTimes: number[];
  reconnectionTimes: number[];
  concurrentCommandTimes: number[];
  memoryUsage: number[];
  cpuUsage: number[];
}

// Helper function to wait for WebSocket connection
async function waitForWebSocketConnection(page: Page, timeout = 10000): Promise<void> {
  await page.waitForFunction(
    () => {
      const indicator = document.querySelector('[data-testid="connection-status"]');
      return indicator && indicator.textContent?.includes('connected');
    },
    { timeout }
  );
}

// Helper to collect performance metrics
async function collectPerformanceMetrics(page: Page): Promise<PerformanceMetrics> {
  return await page.evaluate(() => {
    const metrics = (window as any).performanceMetrics;
    return {
      webSocketLatency: metrics?.webSocketLatency || [],
      commandResponseTimes: metrics?.commandResponseTimes || [],
      eventPropagationTimes: metrics?.eventPropagationTimes || [],
      reconnectionTimes: metrics?.reconnectionTimes || [],
      concurrentCommandTimes: metrics?.concurrentCommandTimes || [],
      memoryUsage: metrics?.memoryUsage || [],
      cpuUsage: metrics?.cpuUsage || []
    };
  });
}

// Helper to inject comprehensive performance monitoring
async function injectPerformanceMonitoring(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.performanceMetrics = {
      webSocketLatency: [],
      commandResponseTimes: [],
      eventPropagationTimes: [],
      reconnectionTimes: [],
      concurrentCommandTimes: [],
      memoryUsage: [],
      cpuUsage: []
    };

    // Performance API monitoring
    window.startPerformanceMonitoring = () => {
      // Memory monitoring
      if ((performance as any).memory) {
        setInterval(() => {
          const memory = (performance as any).memory;
          window.performanceMetrics.memoryUsage.push({
            used: memory.usedJSHeapSize,
            total: memory.totalJSHeapSize,
            timestamp: Date.now()
          });
        }, 1000);
      }

      // CPU usage approximation through frame rate
      let lastFrameTime = performance.now();
      let frameCount = 0;
      
      const measureFrameRate = () => {
        const now = performance.now();
        frameCount++;
        
        if (now - lastFrameTime >= 1000) {
          const fps = frameCount;
          const cpuLoad = Math.max(0, Math.min(100, 100 - (fps / 60) * 100));
          
          window.performanceMetrics.cpuUsage.push({
            fps: fps,
            approximateCpuLoad: cpuLoad,
            timestamp: Date.now()
          });
          
          frameCount = 0;
          lastFrameTime = now;
        }
        
        requestAnimationFrame(measureFrameRate);
      };
      
      requestAnimationFrame(measureFrameRate);
    };

    // WebSocket latency tracking
    window.measureWebSocketLatency = () => {
      return new Promise((resolve) => {
        const startTime = performance.now();
        const ws = new WebSocket('ws://localhost:8767');
        
        ws.onopen = () => {
          const latency = performance.now() - startTime;
          window.performanceMetrics.webSocketLatency.push(latency);
          ws.close();
          resolve(latency);
        };
        
        ws.onerror = () => {
          ws.close();
          resolve(null);
        };
      });
    };

    // Command response time tracking
    window.measureCommandResponse = async (command: string) => {
      const startTime = performance.now();
      
      try {
        const response = await fetch('http://localhost:8767/commands/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command, priority: 'normal' })
        });
        
        const responseTime = performance.now() - startTime;
        window.performanceMetrics.commandResponseTimes.push(responseTime);
        
        return {
          responseTime,
          success: response.ok,
          data: await response.json()
        };
      } catch (error) {
        const responseTime = performance.now() - startTime;
        window.performanceMetrics.commandResponseTimes.push(responseTime);
        
        return {
          responseTime,
          success: false,
          error: error.message
        };
      }
    };

    // Event propagation tracking
    window.measureEventPropagation = () => {
      const eventTimes = new Map();
      
      // Monitor WebSocket messages
      const originalWebSocket = window.WebSocket;
      window.WebSocket = class extends originalWebSocket {
        constructor(url: string | URL, protocols?: string | string[]) {
          super(url, protocols);
          
          this.addEventListener('message', (event) => {
            const receiveTime = performance.now();
            
            try {
              const data = JSON.parse(event.data);
              if (data.timestamp) {
                const propagationTime = receiveTime - data.timestamp;
                window.performanceMetrics.eventPropagationTimes.push(propagationTime);
              }
            } catch (e) {
              // Ignore parsing errors
            }
          });
        }
      };
    };

    // Reconnection time tracking  
    window.measureReconnectionTime = () => {
      return new Promise((resolve) => {
        const startTime = performance.now();
        
        // Simulate disconnect and measure reconnection
        fetch('http://localhost:8767/simulate/error', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: 'websocket_disconnect' })
        }).then(() => {
          // Wait for reconnection
          const checkReconnection = () => {
            const indicator = document.querySelector('[data-testid="connection-status"]');
            if (indicator && indicator.textContent?.includes('connected')) {
              const reconnectionTime = performance.now() - startTime;
              window.performanceMetrics.reconnectionTimes.push(reconnectionTime);
              resolve(reconnectionTime);
            } else {
              setTimeout(checkReconnection, 100);
            }
          };
          
          setTimeout(checkReconnection, 1000); // Give time for disconnect
        });
      });
    };

    // Start monitoring immediately
    window.startPerformanceMonitoring();
    window.measureEventPropagation();
  });
}

test.describe('Performance Validation', () => {
  test.beforeEach(async ({ page }) => {
    await injectPerformanceMonitoring(page);
    await page.goto('/');
    await waitForWebSocketConnection(page, 15000);
  });

  test('should meet WebSocket connection latency target (<200ms)', async ({ page }) => {
    // Measure multiple WebSocket connection attempts
    const connectionAttempts = 5;
    const latencies = [];
    
    for (let i = 0; i < connectionAttempts; i++) {
      const latency = await page.evaluate(() => window.measureWebSocketLatency());
      
      if (latency !== null) {
        latencies.push(latency);
      }
      
      await page.waitForTimeout(1000); // Wait between attempts
    }
    
    expect(latencies.length).toBeGreaterThan(0);
    
    const avgLatency = latencies.reduce((sum, lat) => sum + lat, 0) / latencies.length;
    const maxLatency = Math.max(...latencies);
    const minLatency = Math.min(...latencies);
    
    console.log('WebSocket Connection Latency Analysis:', {
      attempts: connectionAttempts,
      successful: latencies.length,
      average: `${avgLatency.toFixed(2)}ms`,
      min: `${minLatency.toFixed(2)}ms`,
      max: `${maxLatency.toFixed(2)}ms`,
      target: '200ms'
    });
    
    // Performance target validation
    expect(avgLatency).toBeLessThan(200); // <200ms average latency target
    expect(maxLatency).toBeLessThan(300); // Allow some variance but cap maximum
    expect(latencies.filter(lat => lat < 200).length / latencies.length).toBeGreaterThan(0.8); // 80% of connections under 200ms
  });

  test('should meet command response time target (<100ms)', async ({ page }) => {
    const testCommands = [
      'khive daemon status',
      'khive session list',
      'khive agent list',
      'khive coordinate status',
      'khive version'
    ];
    
    const results = [];
    
    for (const command of testCommands) {
      const result = await page.evaluate((cmd) => window.measureCommandResponse(cmd), command);
      results.push({ command, ...result });
      
      await page.waitForTimeout(500); // Brief pause between commands
    }
    
    const successfulResults = results.filter(r => r.success);
    const responseTimes = successfulResults.map(r => r.responseTime);
    
    expect(responseTimes.length).toBeGreaterThan(0);
    
    const avgResponseTime = responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length;
    const maxResponseTime = Math.max(...responseTimes);
    const minResponseTime = Math.min(...responseTimes);
    
    console.log('Command Response Time Analysis:', {
      totalCommands: testCommands.length,
      successful: successfulResults.length,
      average: `${avgResponseTime.toFixed(2)}ms`,
      min: `${minResponseTime.toFixed(2)}ms`,
      max: `${maxResponseTime.toFixed(2)}ms`,
      target: '100ms'
    });
    
    // Performance target validation
    expect(avgResponseTime).toBeLessThan(100); // <100ms average response time target
    expect(maxResponseTime).toBeLessThan(200); // Allow some variance but cap maximum
    expect(responseTimes.filter(time => time < 100).length / responseTimes.length).toBeGreaterThan(0.7); // 70% under 100ms
    
    // Individual command analysis
    results.forEach(result => {
      console.log(`Command: ${result.command} - ${result.responseTime.toFixed(2)}ms (${result.success ? 'SUCCESS' : 'FAILED'})`);
    });
  });

  test('should handle concurrent operations within performance bounds', async ({ page }) => {
    const concurrentCommands = 10;
    const commands = Array.from({ length: concurrentCommands }, (_, i) => `concurrent-test-${i}`);
    
    const startTime = performance.now();
    
    // Execute commands concurrently
    const commandPromises = commands.map(command => 
      page.evaluate((cmd) => window.measureCommandResponse(cmd), command)
    );
    
    const results = await Promise.all(commandPromises);
    const totalTime = performance.now() - startTime;
    
    const successfulResults = results.filter(r => r.success);
    const responseTimes = results.map(r => r.responseTime);
    
    const avgResponseTime = responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length;
    const maxResponseTime = Math.max(...responseTimes);
    const concurrentThroughput = successfulResults.length / (totalTime / 1000); // Commands per second
    
    console.log('Concurrent Operations Performance:', {
      totalCommands: concurrentCommands,
      successful: successfulResults.length,
      totalTime: `${totalTime.toFixed(2)}ms`,
      avgResponseTime: `${avgResponseTime.toFixed(2)}ms`,
      maxResponseTime: `${maxResponseTime.toFixed(2)}ms`,
      throughput: `${concurrentThroughput.toFixed(2)} commands/sec`,
      successRate: `${(successfulResults.length / concurrentCommands * 100).toFixed(1)}%`
    });
    
    // Performance assertions for concurrent operations
    expect(avgResponseTime).toBeLessThan(150); // Allow higher latency for concurrent operations
    expect(maxResponseTime).toBeLessThan(300); // Cap maximum response time
    expect(successfulResults.length / concurrentCommands).toBeGreaterThan(0.9); // 90% success rate
    expect(concurrentThroughput).toBeGreaterThan(5); // At least 5 commands/sec throughput
  });

  test('should maintain performance under sustained load', async ({ page }) => {
    const loadTestDuration = 30000; // 30 seconds
    const commandInterval = 1000; // 1 command per second
    const startTime = Date.now();
    
    const results = [];
    let commandCount = 0;
    
    while (Date.now() - startTime < loadTestDuration) {
      commandCount++;
      const command = `load-test-${commandCount}`;
      
      const result = await page.evaluate((cmd) => window.measureCommandResponse(cmd), command);
      results.push({
        commandId: commandCount,
        timestamp: Date.now() - startTime,
        ...result
      });
      
      await page.waitForTimeout(commandInterval);
    }
    
    // Analyze performance over time
    const timeWindows = Math.floor(loadTestDuration / 5000); // 5-second windows
    const windowAnalysis = [];
    
    for (let i = 0; i < timeWindows; i++) {
      const windowStart = i * 5000;
      const windowEnd = (i + 1) * 5000;
      
      const windowResults = results.filter(r => r.timestamp >= windowStart && r.timestamp < windowEnd);
      const windowSuccessful = windowResults.filter(r => r.success);
      
      if (windowResults.length > 0) {
        const avgResponseTime = windowResults.reduce((sum, r) => sum + r.responseTime, 0) / windowResults.length;
        
        windowAnalysis.push({
          window: i + 1,
          timeRange: `${windowStart/1000}s-${windowEnd/1000}s`,
          commands: windowResults.length,
          successful: windowSuccessful.length,
          avgResponseTime: avgResponseTime,
          successRate: windowSuccessful.length / windowResults.length
        });
      }
    }
    
    console.log('Sustained Load Performance Analysis:');
    windowAnalysis.forEach(window => {
      console.log(`  Window ${window.window} (${window.timeRange}): ${window.successful}/${window.commands} commands, ` +
                  `avg ${window.avgResponseTime.toFixed(2)}ms, ${(window.successRate * 100).toFixed(1)}% success`);
    });
    
    // Performance assertions for sustained load
    const overallSuccessRate = results.filter(r => r.success).length / results.length;
    const overallAvgResponseTime = results.reduce((sum, r) => sum + r.responseTime, 0) / results.length;
    
    expect(overallSuccessRate).toBeGreaterThan(0.95); // 95% success rate under load
    expect(overallAvgResponseTime).toBeLessThan(120); // Average response time under load
    
    // Performance should not degrade significantly over time
    const firstHalfResults = results.slice(0, Math.floor(results.length / 2));
    const secondHalfResults = results.slice(Math.floor(results.length / 2));
    
    const firstHalfAvg = firstHalfResults.reduce((sum, r) => sum + r.responseTime, 0) / firstHalfResults.length;
    const secondHalfAvg = secondHalfResults.reduce((sum, r) => sum + r.responseTime, 0) / secondHalfResults.length;
    
    expect(secondHalfAvg).toBeLessThan(firstHalfAvg * 1.5); // No more than 50% degradation
  });

  test('should recover performance after connection issues', async ({ page }) => {
    // Measure baseline performance
    const baselineResults = [];
    for (let i = 0; i < 5; i++) {
      const result = await page.evaluate(() => window.measureCommandResponse('baseline-test'));
      baselineResults.push(result);
      await page.waitForTimeout(200);
    }
    
    const baselineAvg = baselineResults.reduce((sum, r) => sum + r.responseTime, 0) / baselineResults.length;
    
    // Simulate connection disruption and measure recovery
    const recoveryStart = Date.now();
    const reconnectionTime = await page.evaluate(() => window.measureReconnectionTime());
    const recoveryDuration = Date.now() - recoveryStart;
    
    // Wait for system to stabilize after reconnection
    await page.waitForTimeout(2000);
    
    // Measure post-recovery performance
    const recoveryResults = [];
    for (let i = 0; i < 5; i++) {
      const result = await page.evaluate(() => window.measureCommandResponse('recovery-test'));
      recoveryResults.push(result);
      await page.waitForTimeout(200);
    }
    
    const recoveryAvg = recoveryResults.reduce((sum, r) => sum + r.responseTime, 0) / recoveryResults.length;
    
    console.log('Connection Recovery Performance:', {
      baselineAvg: `${baselineAvg.toFixed(2)}ms`,
      reconnectionTime: `${reconnectionTime}ms`,
      recoveryDuration: `${recoveryDuration}ms`,
      postRecoveryAvg: `${recoveryAvg.toFixed(2)}ms`,
      performanceDegradation: `${((recoveryAvg - baselineAvg) / baselineAvg * 100).toFixed(1)}%`
    });
    
    // Recovery performance assertions
    expect(reconnectionTime).toBeLessThan(5000); // Reconnection within 5 seconds
    expect(recoveryAvg).toBeLessThan(baselineAvg * 1.3); // No more than 30% performance degradation
    expect(recoveryResults.filter(r => r.success).length / recoveryResults.length).toBeGreaterThan(0.8); // 80% success rate post-recovery
  });

  test('should provide comprehensive performance report', async ({ page }) => {
    // Run a comprehensive performance test
    await page.waitForTimeout(10000); // Allow metrics to accumulate
    
    // Collect all performance metrics
    const metrics = await collectPerformanceMetrics(page);
    
    // Measure current connection health
    const connectionHealth = await page.evaluate(() => {
      const healthElement = document.querySelector('[data-testid="connection-health"]');
      const latencyElement = document.querySelector('[data-testid="connection-latency"]');
      
      return {
        status: healthElement?.textContent || 'unknown',
        latency: latencyElement?.textContent || 'unknown'
      };
    });
    
    // Get performance endpoint metrics from mock server
    const serverMetrics = await page.evaluate(async () => {
      try {
        const response = await fetch('http://localhost:8767/performance');
        return await response.json();
      } catch (error) {
        return { error: error.message };
      }
    });
    
    console.log('\n=== COMPREHENSIVE PERFORMANCE REPORT ===');
    console.log('Connection Health:', connectionHealth);
    console.log('Server Metrics:', serverMetrics);
    console.log('Client Metrics Summary:', {
      webSocketConnections: metrics.webSocketLatency.length,
      commandsExecuted: metrics.commandResponseTimes.length,
      eventsPropagated: metrics.eventPropagationTimes.length,
      reconnections: metrics.reconnectionTimes.length
    });
    
    if (metrics.webSocketLatency.length > 0) {
      const avgWsLatency = metrics.webSocketLatency.reduce((sum, lat) => sum + lat, 0) / metrics.webSocketLatency.length;
      console.log(`WebSocket Latency: ${avgWsLatency.toFixed(2)}ms avg (target: <200ms)`);
      expect(avgWsLatency).toBeLessThan(200);
    }
    
    if (metrics.commandResponseTimes.length > 0) {
      const avgCommandTime = metrics.commandResponseTimes.reduce((sum, time) => sum + time, 0) / metrics.commandResponseTimes.length;
      console.log(`Command Response: ${avgCommandTime.toFixed(2)}ms avg (target: <100ms)`);
      expect(avgCommandTime).toBeLessThan(100);
    }
    
    console.log('=== END PERFORMANCE REPORT ===\n');
    
    // Overall system health check
    const finalConnectionStatus = await page.getByTestId('connection-status').textContent();
    expect(finalConnectionStatus).toContain('connected');
  });
});

// Global type declarations
declare global {
  interface Window {
    performanceMetrics: PerformanceMetrics;
    startPerformanceMonitoring: () => void;
    measureWebSocketLatency: () => Promise<number | null>;
    measureCommandResponse: (command: string) => Promise<any>;
    measureEventPropagation: () => void;
    measureReconnectionTime: () => Promise<number>;
  }
}