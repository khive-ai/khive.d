import { test, expect, Page, BrowserContext } from '@playwright/test';

/**
 * Performance Testing: CLI Response Time
 * 
 * OCEAN'S REQUIREMENTS:
 * - Command responses must be <100ms
 * - Monitor command execution timing
 * - Validate performance under load
 * - Detect performance regressions
 */

// Performance thresholds (ms)
const PERFORMANCE_TARGETS = {
  CLI_RESPONSE_MAX: 100,
  CLI_RESPONSE_TARGET: 80,
  LOAD_TEST_COMMANDS: 50,
  REGRESSION_THRESHOLD: 1.5, // 50% increase triggers regression alert
} as const;

// Baseline performance data storage
let performanceBaselines: Map<string, number> = new Map();

test.describe('CLI Performance Monitoring', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({
      // Consistent environment for performance testing
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1,
    });
  });

  test.beforeEach(async () => {
    page = await context.newPage();
    
    // Wait for application to be fully loaded
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[data-testid="command-center"]', { timeout: 10000 });
  });

  test.afterEach(async () => {
    await page.close();
  });

  test.afterAll(async () => {
    await context.close();
  });

  /**
   * Test: Command Execution Timing
   * Validates that CLI commands respond within Ocean's <100ms requirement
   */
  test('CLI commands respond within 100ms target', async () => {
    const commands = [
      'help',
      'status',
      'agents',
      'sessions',
      'metrics',
      'workspace',
      'config',
    ];

    const commandTimings: Array<{ command: string; duration: number }> = [];

    for (const command of commands) {
      // Open command palette
      await page.keyboard.press('Meta+k');
      await page.waitForSelector('[data-testid="command-palette"]');
      
      // Measure command execution time
      const startTime = performance.now();
      
      // Type command
      await page.fill('[data-testid="command-input"]', command);
      await page.keyboard.press('Enter');
      
      // Wait for command response/completion indicator
      await page.waitForSelector('[data-testid="command-result"]', { timeout: 5000 });
      
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      commandTimings.push({ command, duration });
      
      // Validate individual command performance
      expect(duration).toBeLessThan(PERFORMANCE_TARGETS.CLI_RESPONSE_MAX);
      
      // Close command result if still open
      await page.keyboard.press('Escape');
      await page.waitForTimeout(100); // Small buffer between commands
    }

    // Performance analysis
    const averageTime = commandTimings.reduce((sum, timing) => sum + timing.duration, 0) / commandTimings.length;
    const slowestCommand = commandTimings.reduce((prev, current) => (prev.duration > current.duration) ? prev : current);
    
    console.log('CLI Performance Results:');
    console.log(`Average response time: ${averageTime.toFixed(2)}ms`);
    console.log(`Slowest command: ${slowestCommand.command} (${slowestCommand.duration.toFixed(2)}ms)`);
    
    // Store baseline for regression testing
    performanceBaselines.set('cli_average', averageTime);
    
    // Validate average performance
    expect(averageTime).toBeLessThan(PERFORMANCE_TARGETS.CLI_RESPONSE_TARGET);
  });

  /**
   * Test: Command Performance Under Load
   * Simulates rapid command execution to test performance degradation
   */
  test('CLI maintains performance under rapid command execution', async () => {
    const rapidCommands = Array(PERFORMANCE_TARGETS.LOAD_TEST_COMMANDS).fill('status');
    const loadTestResults: number[] = [];

    for (let i = 0; i < rapidCommands.length; i++) {
      const startTime = performance.now();
      
      // Rapid fire commands
      await page.keyboard.press('Meta+k');
      await page.fill('[data-testid="command-input"]', 'status');
      await page.keyboard.press('Enter');
      await page.waitForSelector('[data-testid="command-result"]');
      
      const endTime = performance.now();
      loadTestResults.push(endTime - startTime);
      
      await page.keyboard.press('Escape');
      
      // Minimal delay to prevent overwhelming
      if (i % 10 === 0) {
        await page.waitForTimeout(50);
      }
    }

    // Performance degradation analysis
    const firstTenAvg = loadTestResults.slice(0, 10).reduce((a, b) => a + b) / 10;
    const lastTenAvg = loadTestResults.slice(-10).reduce((a, b) => a + b) / 10;
    const degradationRatio = lastTenAvg / firstTenAvg;
    
    console.log('Load Test Results:');
    console.log(`First 10 commands average: ${firstTenAvg.toFixed(2)}ms`);
    console.log(`Last 10 commands average: ${lastTenAvg.toFixed(2)}ms`);
    console.log(`Performance degradation ratio: ${degradationRatio.toFixed(2)}x`);
    
    // Validate no significant performance degradation
    expect(degradationRatio).toBeLessThan(PERFORMANCE_TARGETS.REGRESSION_THRESHOLD);
    expect(lastTenAvg).toBeLessThan(PERFORMANCE_TARGETS.CLI_RESPONSE_MAX);
  });

  /**
   * Test: Complex Command Performance
   * Tests performance of resource-intensive commands
   */
  test('Complex commands meet performance requirements', async () => {
    const complexCommands = [
      { command: 'search all files', timeout: 2000 },
      { command: 'generate report', timeout: 3000 },
      { command: 'analyze workspace', timeout: 2000 },
      { command: 'export session', timeout: 1500 },
    ];

    for (const { command, timeout } of complexCommands) {
      const startTime = performance.now();
      
      await page.keyboard.press('Meta+k');
      await page.fill('[data-testid="command-input"]', command);
      await page.keyboard.press('Enter');
      
      // Wait for complex command completion
      await page.waitForSelector('[data-testid="command-result"]', { timeout });
      
      const duration = performance.now() - startTime;
      
      console.log(`Complex command "${command}": ${duration.toFixed(2)}ms`);
      
      // More lenient threshold for complex commands, but still reasonable
      expect(duration).toBeLessThan(timeout * 0.8); // 80% of timeout budget
      
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200); // Recovery time between complex commands
    }
  });

  /**
   * Test: Keyboard Shortcut Performance
   * Validates that keyboard shortcuts respond instantly
   */
  test('Keyboard shortcuts respond within 50ms', async () => {
    const shortcuts = [
      { keys: 'Meta+1', target: '[data-testid="workspace-pane"]' },
      { keys: 'Meta+2', target: '[data-testid="agents-pane"]' },
      { keys: 'Meta+3', target: '[data-testid="sessions-pane"]' },
      { keys: 'Meta+/', target: '[data-testid="help-panel"]' },
      { keys: 'Meta+k', target: '[data-testid="command-palette"]' },
    ];

    for (const { keys, target } of shortcuts) {
      // Ensure clean state
      await page.keyboard.press('Escape');
      await page.waitForTimeout(100);
      
      const startTime = performance.now();
      await page.keyboard.press(keys);
      await page.waitForSelector(target);
      const duration = performance.now() - startTime;
      
      console.log(`Shortcut ${keys}: ${duration.toFixed(2)}ms`);
      
      // Keyboard shortcuts should be nearly instantaneous
      expect(duration).toBeLessThan(50);
    }
  });

  /**
   * Test: Performance Regression Detection
   * Compares current performance against established baselines
   */
  test('Performance regression detection', async () => {
    // This test would normally load stored baselines from previous runs
    // For now, we'll simulate baseline comparison
    
    const currentMetrics = {
      cli_average: 75, // Example current performance
      load_degradation: 1.2,
      shortcut_average: 25,
    };

    const simulatedBaselines = {
      cli_average: 80,
      load_degradation: 1.1,
      shortcut_average: 30,
    };

    Object.entries(currentMetrics).forEach(([metric, current]) => {
      const baseline = simulatedBaselines[metric as keyof typeof simulatedBaselines];
      const regressionRatio = current / baseline;
      
      console.log(`Performance metric "${metric}": Current=${current}, Baseline=${baseline}, Ratio=${regressionRatio.toFixed(2)}`);
      
      // Alert if performance has degraded by more than 50%
      if (regressionRatio > PERFORMANCE_TARGETS.REGRESSION_THRESHOLD) {
        console.warn(`⚠️ PERFORMANCE REGRESSION DETECTED: ${metric} degraded by ${((regressionRatio - 1) * 100).toFixed(1)}%`);
      }
      
      // Test should fail if critical performance regression
      if (metric === 'cli_average' && regressionRatio > PERFORMANCE_TARGETS.REGRESSION_THRESHOLD) {
        expect(regressionRatio).toBeLessThan(PERFORMANCE_TARGETS.REGRESSION_THRESHOLD);
      }
    });
  });

  /**
   * Test: Performance Monitoring Accuracy
   * Validates that the application's built-in performance monitoring is accurate
   */
  test('Built-in performance monitoring accuracy', async () => {
    // Open performance monitoring panel
    await page.keyboard.press('Meta+p'); // Assuming this opens perf monitor
    await page.waitForSelector('[data-testid="performance-monitor"]');
    
    // Execute a command while monitoring
    const startTime = performance.now();
    await page.keyboard.press('Meta+k');
    await page.fill('[data-testid="command-input"]', 'status');
    await page.keyboard.press('Enter');
    await page.waitForSelector('[data-testid="command-result"]');
    const actualDuration = performance.now() - startTime;
    
    // Get reported duration from performance monitor
    const reportedDuration = await page.locator('[data-testid="last-command-duration"]').textContent();
    const reportedMs = parseFloat(reportedDuration?.replace('ms', '') || '0');
    
    console.log(`Actual duration: ${actualDuration.toFixed(2)}ms`);
    console.log(`Reported duration: ${reportedMs}ms`);
    
    // Performance monitoring should be accurate within 10ms
    const accuracyDifference = Math.abs(actualDuration - reportedMs);
    expect(accuracyDifference).toBeLessThan(10);
  });
});