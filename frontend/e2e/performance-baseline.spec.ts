import { test, expect, Page, BrowserContext } from '@playwright/test';
import { writeFileSync, readFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

/**
 * Performance Baseline & Regression Detection
 * 
 * OCEAN'S REQUIREMENTS:
 * - Establish performance baselines for all critical metrics
 * - Automated regression detection with <50% degradation threshold
 * - Historical performance tracking and trending
 * - CI/CD integration for performance gating
 */

// Performance baseline storage
const BASELINE_DIR = join(process.cwd(), 'test-results', 'performance-baselines');
const REGRESSION_THRESHOLD = 1.5; // 50% degradation triggers regression alert

// Performance categories and their targets
const PERFORMANCE_CATEGORIES = {
  CLI_RESPONSE: {
    target: 80,
    max: 100,
    unit: 'ms',
    description: 'Command response time',
  },
  CONTEXT_SWITCHING: {
    target: 30,
    max: 50,
    unit: 'ms',
    description: 'Pane switching time',
  },
  WEBSOCKET_LATENCY: {
    target: 150,
    max: 200,
    unit: 'ms',
    description: 'Real-time message latency',
  },
  MEMORY_USAGE: {
    target: 75,
    max: 100,
    unit: 'MB',
    description: 'Frontend memory consumption',
  },
  UI_RESPONSIVENESS: {
    target: 16,
    max: 32,
    unit: 'ms',
    description: 'UI animation frame time',
  },
} as const;

interface PerformanceMetric {
  name: string;
  value: number;
  unit: string;
  timestamp: number;
  environment: string;
  browserVersion: string;
  testId: string;
}

interface PerformanceBaseline {
  category: string;
  baseline: number;
  target: number;
  max: number;
  unit: string;
  description: string;
  establishedAt: number;
  environment: string;
  sampleSize: number;
  confidence: number;
}

interface RegressionReport {
  category: string;
  current: number;
  baseline: number;
  regression: number;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  timestamp: number;
}

test.describe('Performance Baseline & Regression Detection', () => {
  let context: BrowserContext;
  let page: Page;
  let testEnvironment: string;
  let browserInfo: any;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1,
    });
    
    // Ensure baseline directory exists
    if (!existsSync(BASELINE_DIR)) {
      mkdirSync(BASELINE_DIR, { recursive: true });
    }
    
    // Detect test environment
    testEnvironment = process.env.CI ? 'ci' : 'local';
    browserInfo = {
      name: browser.browserType().name(),
      version: browser.version(),
    };
  });

  test.beforeEach(async () => {
    page = await context.newPage();
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
   * Utility: Save performance metric
   */
  function savePerformanceMetric(metric: PerformanceMetric) {
    const filename = join(BASELINE_DIR, `${metric.name}-${testEnvironment}.json`);
    
    let metrics: PerformanceMetric[] = [];
    if (existsSync(filename)) {
      try {
        metrics = JSON.parse(readFileSync(filename, 'utf-8'));
      } catch (e) {
        console.warn(`Failed to read existing metrics for ${metric.name}:`, e);
      }
    }
    
    metrics.push(metric);
    
    // Keep only last 100 measurements to prevent file bloat
    if (metrics.length > 100) {
      metrics = metrics.slice(-100);
    }
    
    writeFileSync(filename, JSON.stringify(metrics, null, 2));
  }

  /**
   * Utility: Load performance baseline
   */
  function loadPerformanceBaseline(category: string): PerformanceBaseline | null {
    const filename = join(BASELINE_DIR, `baseline-${category}-${testEnvironment}.json`);
    
    if (!existsSync(filename)) {
      return null;
    }
    
    try {
      return JSON.parse(readFileSync(filename, 'utf-8'));
    } catch (e) {
      console.warn(`Failed to load baseline for ${category}:`, e);
      return null;
    }
  }

  /**
   * Utility: Save performance baseline
   */
  function savePerformanceBaseline(baseline: PerformanceBaseline) {
    const filename = join(BASELINE_DIR, `baseline-${baseline.category}-${testEnvironment}.json`);
    writeFileSync(filename, JSON.stringify(baseline, null, 2));
  }

  /**
   * Utility: Calculate baseline from historical data
   */
  function calculateBaseline(metrics: PerformanceMetric[]): { baseline: number; confidence: number } {
    if (metrics.length < 5) {
      throw new Error('Insufficient data points to establish baseline (minimum 5 required)');
    }

    // Use recent measurements (last 30 days or 50 measurements, whichever is smaller)
    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
    const recentMetrics = metrics
      .filter(m => m.timestamp > thirtyDaysAgo)
      .slice(-50);

    const values = recentMetrics.map(m => m.value);
    
    // Calculate percentiles for more robust baseline
    values.sort((a, b) => a - b);
    const p50 = values[Math.floor(values.length * 0.5)];
    const p75 = values[Math.floor(values.length * 0.75)];
    const p95 = values[Math.floor(values.length * 0.95)];
    
    // Use 75th percentile as baseline (allows for some natural variance)
    const baseline = p75;
    
    // Calculate confidence based on data consistency
    const stdDev = Math.sqrt(values.reduce((sum, val) => sum + Math.pow(val - baseline, 2), 0) / values.length);
    const coefficientOfVariation = stdDev / baseline;
    const confidence = Math.max(0, Math.min(1, 1 - coefficientOfVariation));
    
    console.log(`Baseline calculation for ${recentMetrics[0]?.name}:`);
    console.log(`  Sample size: ${values.length}`);
    console.log(`  P50: ${p50.toFixed(2)}, P75: ${p75.toFixed(2)}, P95: ${p95.toFixed(2)}`);
    console.log(`  Baseline (P75): ${baseline.toFixed(2)}`);
    console.log(`  Confidence: ${(confidence * 100).toFixed(1)}%`);
    
    return { baseline, confidence };
  }

  /**
   * Test: Establish CLI Response Time Baseline
   */
  test('Establish CLI response time baseline', async () => {
    const commands = ['help', 'status', 'agents', 'sessions', 'metrics'];
    const measurements: number[] = [];

    // Collect multiple measurements for statistical significance
    for (let round = 0; round < 3; round++) {
      for (const command of commands) {
        const startTime = performance.now();
        
        await page.keyboard.press('Meta+k');
        await page.fill('[data-testid="command-input"]', command);
        await page.keyboard.press('Enter');
        await page.waitForSelector('[data-testid="command-result"]');
        await page.keyboard.press('Escape');
        
        const duration = performance.now() - startTime;
        measurements.push(duration);
        
        // Save individual measurement
        savePerformanceMetric({
          name: 'cli_response_time',
          value: duration,
          unit: 'ms',
          timestamp: Date.now(),
          environment: testEnvironment,
          browserVersion: `${browserInfo.name}-${browserInfo.version}`,
          testId: `${command}-${round}`,
        });
        
        await page.waitForTimeout(200);
      }
    }

    // Calculate and save baseline
    const avgTime = measurements.reduce((a, b) => a + b) / measurements.length;
    
    const baseline: PerformanceBaseline = {
      category: 'CLI_RESPONSE',
      baseline: avgTime,
      target: PERFORMANCE_CATEGORIES.CLI_RESPONSE.target,
      max: PERFORMANCE_CATEGORIES.CLI_RESPONSE.max,
      unit: PERFORMANCE_CATEGORIES.CLI_RESPONSE.unit,
      description: PERFORMANCE_CATEGORIES.CLI_RESPONSE.description,
      establishedAt: Date.now(),
      environment: testEnvironment,
      sampleSize: measurements.length,
      confidence: 0.95, // High confidence for fresh baseline
    };
    
    savePerformanceBaseline(baseline);
    
    console.log(`CLI Response Time Baseline Established:`);
    console.log(`  Average: ${avgTime.toFixed(2)}ms`);
    console.log(`  Target: ${baseline.target}ms`);
    console.log(`  Max: ${baseline.max}ms`);
    console.log(`  Sample size: ${baseline.sampleSize}`);
    
    // Validate baseline is within acceptable range
    expect(avgTime).toBeLessThan(PERFORMANCE_CATEGORIES.CLI_RESPONSE.max);
  });

  /**
   * Test: Establish Context Switching Baseline
   */
  test('Establish context switching baseline', async () => {
    const switches = [
      { key: 'Meta+1', name: 'workspace' },
      { key: 'Meta+2', name: 'agents' },
      { key: 'Meta+3', name: 'sessions' },
      { key: 'Meta+4', name: 'metrics' },
    ];
    
    const measurements: number[] = [];

    // Multiple rounds for statistical significance
    for (let round = 0; round < 5; round++) {
      for (const switchConfig of switches) {
        const startTime = performance.now();
        
        await page.keyboard.press(switchConfig.key);
        await page.waitForSelector(`[data-testid="${switchConfig.name}-pane"].active`);
        
        const duration = performance.now() - startTime;
        measurements.push(duration);
        
        savePerformanceMetric({
          name: 'context_switching_time',
          value: duration,
          unit: 'ms',
          timestamp: Date.now(),
          environment: testEnvironment,
          browserVersion: `${browserInfo.name}-${browserInfo.version}`,
          testId: `${switchConfig.name}-${round}`,
        });
        
        await page.waitForTimeout(100);
      }
    }

    const avgTime = measurements.reduce((a, b) => a + b) / measurements.length;
    
    const baseline: PerformanceBaseline = {
      category: 'CONTEXT_SWITCHING',
      baseline: avgTime,
      target: PERFORMANCE_CATEGORIES.CONTEXT_SWITCHING.target,
      max: PERFORMANCE_CATEGORIES.CONTEXT_SWITCHING.max,
      unit: PERFORMANCE_CATEGORIES.CONTEXT_SWITCHING.unit,
      description: PERFORMANCE_CATEGORIES.CONTEXT_SWITCHING.description,
      establishedAt: Date.now(),
      environment: testEnvironment,
      sampleSize: measurements.length,
      confidence: 0.95,
    };
    
    savePerformanceBaseline(baseline);
    
    console.log(`Context Switching Baseline Established:`);
    console.log(`  Average: ${avgTime.toFixed(2)}ms`);
    console.log(`  Target: ${baseline.target}ms`);
    console.log(`  Max: ${baseline.max}ms`);
    
    expect(avgTime).toBeLessThan(PERFORMANCE_CATEGORIES.CONTEXT_SWITCHING.max);
  });

  /**
   * Test: Establish Memory Usage Baseline
   */
  test('Establish memory usage baseline', async () => {
    const measurements: number[] = [];

    // Collect memory measurements during various operations
    const operations = [
      () => page.goto('/'),
      () => page.keyboard.press('Meta+1'),
      () => page.keyboard.press('Meta+2'),
      () => page.keyboard.press('Meta+k'),
      () => page.keyboard.press('Escape'),
    ];

    for (let round = 0; round < 3; round++) {
      for (const operation of operations) {
        await operation();
        await page.waitForTimeout(1000);
        
        // Force garbage collection if available
        await page.evaluate(() => {
          if ('gc' in window) {
            (window as any).gc();
          }
        });
        
        const memoryMetrics = await page.evaluate(() => {
          const memory = (performance as any).memory;
          return {
            usedJSHeapSize: memory?.usedJSHeapSize || 0,
            totalJSHeapSize: memory?.totalJSHeapSize || 0,
          };
        });
        
        const memoryMB = memoryMetrics.usedJSHeapSize / (1024 * 1024);
        measurements.push(memoryMB);
        
        savePerformanceMetric({
          name: 'memory_usage',
          value: memoryMB,
          unit: 'MB',
          timestamp: Date.now(),
          environment: testEnvironment,
          browserVersion: `${browserInfo.name}-${browserInfo.version}`,
          testId: `operation-${round}`,
        });
      }
    }

    const avgMemory = measurements.reduce((a, b) => a + b) / measurements.length;
    const maxMemory = Math.max(...measurements);
    
    const baseline: PerformanceBaseline = {
      category: 'MEMORY_USAGE',
      baseline: avgMemory,
      target: PERFORMANCE_CATEGORIES.MEMORY_USAGE.target,
      max: PERFORMANCE_CATEGORIES.MEMORY_USAGE.max,
      unit: PERFORMANCE_CATEGORIES.MEMORY_USAGE.unit,
      description: PERFORMANCE_CATEGORIES.MEMORY_USAGE.description,
      establishedAt: Date.now(),
      environment: testEnvironment,
      sampleSize: measurements.length,
      confidence: 0.9,
    };
    
    savePerformanceBaseline(baseline);
    
    console.log(`Memory Usage Baseline Established:`);
    console.log(`  Average: ${avgMemory.toFixed(2)}MB`);
    console.log(`  Peak: ${maxMemory.toFixed(2)}MB`);
    console.log(`  Target: ${baseline.target}MB`);
    console.log(`  Max: ${baseline.max}MB`);
    
    expect(maxMemory).toBeLessThan(PERFORMANCE_CATEGORIES.MEMORY_USAGE.max);
  });

  /**
   * Test: Performance Regression Detection
   */
  test('Performance regression detection system', async () => {
    const regressionReports: RegressionReport[] = [];
    
    // Test each performance category for regressions
    for (const [categoryKey, categoryConfig] of Object.entries(PERFORMANCE_CATEGORIES)) {
      const baseline = loadPerformanceBaseline(categoryKey);
      
      if (!baseline) {
        console.log(`No baseline found for ${categoryKey}, skipping regression test`);
        continue;
      }

      // Simulate current performance measurement
      let currentPerformance: number;
      
      switch (categoryKey) {
        case 'CLI_RESPONSE':
          // Quick CLI test
          const startTime = performance.now();
          await page.keyboard.press('Meta+k');
          await page.fill('[data-testid="command-input"]', 'status');
          await page.keyboard.press('Enter');
          await page.waitForSelector('[data-testid="command-result"]');
          await page.keyboard.press('Escape');
          currentPerformance = performance.now() - startTime;
          break;
          
        case 'CONTEXT_SWITCHING':
          const switchStart = performance.now();
          await page.keyboard.press('Meta+2');
          await page.waitForSelector('[data-testid="agents-pane"].active');
          currentPerformance = performance.now() - switchStart;
          break;
          
        case 'MEMORY_USAGE':
          await page.evaluate(() => {
            if ('gc' in window) {
              (window as any).gc();
            }
          });
          await page.waitForTimeout(1000);
          const memoryMetrics = await page.evaluate(() => {
            const memory = (performance as any).memory;
            return memory?.usedJSHeapSize || 0;
          });
          currentPerformance = memoryMetrics / (1024 * 1024);
          break;
          
        default:
          // Skip unknown categories
          continue;
      }

      // Calculate regression
      const regressionRatio = currentPerformance / baseline.baseline;
      const regressionPercent = (regressionRatio - 1) * 100;
      
      // Determine severity
      let severity: RegressionReport['severity'] = 'LOW';
      if (regressionRatio > 2.0) severity = 'CRITICAL';
      else if (regressionRatio > REGRESSION_THRESHOLD) severity = 'HIGH';
      else if (regressionRatio > 1.2) severity = 'MEDIUM';
      
      console.log(`Regression Test - ${categoryKey}:`);
      console.log(`  Current: ${currentPerformance.toFixed(2)}${categoryConfig.unit}`);
      console.log(`  Baseline: ${baseline.baseline.toFixed(2)}${categoryConfig.unit}`);
      console.log(`  Regression: ${regressionPercent.toFixed(1)}%`);
      console.log(`  Severity: ${severity}`);
      
      if (regressionRatio > 1.1) { // Report any regression >10%
        const report: RegressionReport = {
          category: categoryKey,
          current: currentPerformance,
          baseline: baseline.baseline,
          regression: regressionRatio,
          severity,
          timestamp: Date.now(),
        };
        
        regressionReports.push(report);
      }
      
      // Save current measurement for future baseline updates
      savePerformanceMetric({
        name: categoryKey.toLowerCase(),
        value: currentPerformance,
        unit: categoryConfig.unit,
        timestamp: Date.now(),
        environment: testEnvironment,
        browserVersion: `${browserInfo.name}-${browserInfo.version}`,
        testId: 'regression-test',
      });
      
      // Validate against hard limits (fail test for critical regressions)
      if (severity === 'CRITICAL') {
        expect(currentPerformance).toBeLessThan(categoryConfig.max);
      }
    }

    // Generate regression report
    if (regressionReports.length > 0) {
      const reportFilename = join(BASELINE_DIR, `regression-report-${Date.now()}.json`);
      const reportData = {
        timestamp: Date.now(),
        environment: testEnvironment,
        browser: browserInfo,
        regressions: regressionReports,
        summary: {
          totalRegressions: regressionReports.length,
          criticalRegressions: regressionReports.filter(r => r.severity === 'CRITICAL').length,
          highRegressions: regressionReports.filter(r => r.severity === 'HIGH').length,
        },
      };
      
      writeFileSync(reportFilename, JSON.stringify(reportData, null, 2));
      
      console.log('\n🚨 PERFORMANCE REGRESSION REPORT 🚨');
      console.log(`Total regressions detected: ${regressionReports.length}`);
      console.log(`Critical: ${reportData.summary.criticalRegressions}`);
      console.log(`High: ${reportData.summary.highRegressions}`);
      console.log(`Report saved: ${reportFilename}`);
      
      // Fail test if critical regressions detected
      if (reportData.summary.criticalRegressions > 0) {
        throw new Error(`Critical performance regressions detected: ${reportData.summary.criticalRegressions}`);
      }
    } else {
      console.log('✅ No significant performance regressions detected');
    }
  });

  /**
   * Test: Historical Performance Trending
   */
  test('Historical performance trending analysis', async () => {
    const categories = Object.keys(PERFORMANCE_CATEGORIES);
    const trendAnalysis: any = {};

    for (const category of categories) {
      const filename = join(BASELINE_DIR, `${category.toLowerCase()}-${testEnvironment}.json`);
      
      if (!existsSync(filename)) {
        console.log(`No historical data for ${category}`);
        continue;
      }

      try {
        const historicalData: PerformanceMetric[] = JSON.parse(readFileSync(filename, 'utf-8'));
        
        if (historicalData.length < 10) {
          console.log(`Insufficient historical data for ${category} (${historicalData.length} points)`);
          continue;
        }

        // Analyze last 30 data points for trend
        const recentData = historicalData.slice(-30);
        const values = recentData.map(d => d.value);
        
        // Calculate trend using linear regression
        const n = values.length;
        const xSum = (n * (n - 1)) / 2;
        const ySum = values.reduce((a, b) => a + b, 0);
        const xySum = values.reduce((sum, y, x) => sum + x * y, 0);
        const xxSum = (n * (n - 1) * (2 * n - 1)) / 6;
        
        const slope = (n * xySum - xSum * ySum) / (n * xxSum - xSum * xSum);
        const intercept = (ySum - slope * xSum) / n;
        
        // Calculate correlation coefficient
        const yMean = ySum / n;
        const ssRes = values.reduce((sum, y, x) => sum + Math.pow(y - (slope * x + intercept), 2), 0);
        const ssTot = values.reduce((sum, y) => sum + Math.pow(y - yMean, 2), 0);
        const r2 = 1 - (ssRes / ssTot);
        
        trendAnalysis[category] = {
          dataPoints: n,
          currentValue: values[values.length - 1],
          trend: slope > 0.1 ? 'DEGRADING' : slope < -0.1 ? 'IMPROVING' : 'STABLE',
          slope: slope,
          correlation: r2,
          prediction: slope * n + intercept, // Predicted next value
        };
        
        console.log(`Performance Trend Analysis - ${category}:`);
        console.log(`  Data points: ${n}`);
        console.log(`  Current: ${values[values.length - 1].toFixed(2)}`);
        console.log(`  Trend: ${trendAnalysis[category].trend} (slope: ${slope.toFixed(4)})`);
        console.log(`  R²: ${r2.toFixed(3)}`);
        console.log(`  Predicted next: ${trendAnalysis[category].prediction.toFixed(2)}`);
        
        // Alert for concerning trends
        if (trendAnalysis[category].trend === 'DEGRADING' && r2 > 0.7) {
          console.log(`⚠️  Concerning degradation trend detected in ${category}`);
        }
        
      } catch (error) {
        console.warn(`Failed to analyze trends for ${category}:`, error);
      }
    }

    // Save trend analysis
    const trendReportFilename = join(BASELINE_DIR, `trend-analysis-${Date.now()}.json`);
    writeFileSync(trendReportFilename, JSON.stringify({
      timestamp: Date.now(),
      environment: testEnvironment,
      analysis: trendAnalysis,
    }, null, 2));
    
    console.log(`Trend analysis saved: ${trendReportFilename}`);
  });

  /**
   * Test: CI/CD Performance Gate
   */
  test('CI/CD performance gate validation', async () => {
    if (process.env.CI !== 'true') {
      console.log('Skipping CI/CD gate validation (not in CI environment)');
      return;
    }

    const performanceGate = {
      CLI_RESPONSE: 100, // ms
      CONTEXT_SWITCHING: 50, // ms
      MEMORY_USAGE: 100, // MB
      WEBSOCKET_LATENCY: 200, // ms
    };

    const gateResults: Array<{ metric: string; value: number; limit: number; passed: boolean }> = [];

    // Quick performance validation for CI gate
    for (const [metric, limit] of Object.entries(performanceGate)) {
      let currentValue: number;
      
      switch (metric) {
        case 'CLI_RESPONSE':
          const start = performance.now();
          await page.keyboard.press('Meta+k');
          await page.fill('[data-testid="command-input"]', 'status');
          await page.keyboard.press('Enter');
          await page.waitForSelector('[data-testid="command-result"]');
          await page.keyboard.press('Escape');
          currentValue = performance.now() - start;
          break;
          
        case 'MEMORY_USAGE':
          const memMetrics = await page.evaluate(() => {
            return (performance as any).memory?.usedJSHeapSize || 0;
          });
          currentValue = memMetrics / (1024 * 1024);
          break;
          
        default:
          continue;
      }

      const passed = currentValue <= limit;
      gateResults.push({ metric, value: currentValue, limit, passed });
      
      console.log(`CI Gate - ${metric}: ${currentValue.toFixed(2)} <= ${limit} : ${passed ? '✅ PASS' : '❌ FAIL'}`);
    }

    const failedGates = gateResults.filter(result => !result.passed);
    
    if (failedGates.length > 0) {
      console.log('\n❌ CI/CD PERFORMANCE GATE FAILED');
      failedGates.forEach(gate => {
        console.log(`  ${gate.metric}: ${gate.value.toFixed(2)} > ${gate.limit}`);
      });
      
      // Fail the test to block CI/CD pipeline
      throw new Error(`Performance gate validation failed for: ${failedGates.map(g => g.metric).join(', ')}`);
    }

    console.log('\n✅ CI/CD PERFORMANCE GATE PASSED');
  });
});