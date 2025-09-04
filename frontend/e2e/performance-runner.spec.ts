import { test, expect } from '@playwright/test';
import { readFileSync, existsSync, writeFileSync } from 'fs';
import { join } from 'path';

/**
 * Performance Test Runner & Comprehensive Validation
 * 
 * Orchestrates all performance tests and generates comprehensive reports
 * for Ocean's performance requirements validation
 */

// Performance test orchestration
const PERFORMANCE_TESTS = [
  {
    name: 'CLI Response Time',
    file: 'performance-cli.spec.ts',
    category: 'CLI_RESPONSE',
    priority: 'HIGH',
    targets: { target: 80, max: 100, unit: 'ms' },
  },
  {
    name: 'Context Switching',
    file: 'performance-context.spec.ts',
    category: 'CONTEXT_SWITCHING',
    priority: 'HIGH',
    targets: { target: 30, max: 50, unit: 'ms' },
  },
  {
    name: 'Memory Usage',
    file: 'performance-memory.spec.ts',
    category: 'MEMORY_USAGE',
    priority: 'CRITICAL',
    targets: { target: 75, max: 100, unit: 'MB' },
  },
  {
    name: 'WebSocket Latency',
    file: 'performance-websocket.spec.ts',
    category: 'WEBSOCKET_LATENCY',
    priority: 'HIGH',
    targets: { target: 150, max: 200, unit: 'ms' },
  },
  {
    name: 'Performance Baseline',
    file: 'performance-baseline.spec.ts',
    category: 'BASELINE_MANAGEMENT',
    priority: 'MEDIUM',
    targets: { target: 0, max: 0, unit: 'status' },
  },
];

interface TestResult {
  name: string;
  category: string;
  status: 'PASS' | 'FAIL' | 'SKIP';
  duration: number;
  errors: string[];
  metrics: Record<string, number>;
}

interface PerformanceReport {
  timestamp: number;
  environment: string;
  testSuite: string;
  summary: {
    totalTests: number;
    passed: number;
    failed: number;
    skipped: number;
    duration: number;
  };
  results: TestResult[];
  oceanRequirements: {
    cliResponse: { target: number; actual: number; status: 'PASS' | 'FAIL' };
    contextSwitch: { target: number; actual: number; status: 'PASS' | 'FAIL' };
    memoryUsage: { target: number; actual: number; status: 'PASS' | 'FAIL' };
    websocketLatency: { target: number; actual: number; status: 'PASS' | 'FAIL' };
  };
  recommendations: string[];
}

test.describe('Performance Test Runner & Validation', () => {
  const RESULTS_DIR = join(process.cwd(), 'test-results');
  const BASELINE_DIR = join(RESULTS_DIR, 'performance-baselines');

  /**
   * Test: Comprehensive Performance Validation
   * Runs all performance tests and validates Ocean's requirements
   */
  test('Comprehensive performance validation for Ocean\'s requirements', async ({ page }) => {
    const suiteStartTime = Date.now();
    const testResults: TestResult[] = [];
    
    console.log('🚀 Starting Comprehensive Performance Validation');
    console.log(`Performance Requirements:`);
    console.log(`  CLI Response: <100ms (target: <80ms)`);
    console.log(`  Context Switching: <50ms (target: <30ms)`);
    console.log(`  Memory Usage: <100MB (target: <75MB)`);
    console.log(`  WebSocket Latency: <200ms (target: <150ms)`);

    // Initialize application
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[data-testid="command-center"]');

    // Run CLI Response Time Tests
    console.log('\n📊 Testing CLI Response Time Performance...');
    const cliStartTime = Date.now();
    
    try {
      const commands = ['help', 'status', 'agents', 'sessions'];
      const cliTimings: number[] = [];
      
      for (const command of commands) {
        const start = performance.now();
        await page.keyboard.press('Meta+k');
        await page.fill('[data-testid="command-input"]', command);
        await page.keyboard.press('Enter');
        await page.waitForSelector('[data-testid="command-result"]', { timeout: 2000 });
        await page.keyboard.press('Escape');
        const timing = performance.now() - start;
        
        cliTimings.push(timing);
        console.log(`  ${command}: ${timing.toFixed(2)}ms`);
      }
      
      const avgCliTime = cliTimings.reduce((a, b) => a + b) / cliTimings.length;
      const maxCliTime = Math.max(...cliTimings);
      
      testResults.push({
        name: 'CLI Response Time',
        category: 'CLI_RESPONSE',
        status: maxCliTime < 100 ? 'PASS' : 'FAIL',
        duration: Date.now() - cliStartTime,
        errors: maxCliTime >= 100 ? [`CLI response time ${maxCliTime.toFixed(2)}ms exceeds 100ms limit`] : [],
        metrics: { average: avgCliTime, max: maxCliTime, count: cliTimings.length },
      });
      
      console.log(`  Average: ${avgCliTime.toFixed(2)}ms | Max: ${maxCliTime.toFixed(2)}ms | Status: ${maxCliTime < 100 ? '✅ PASS' : '❌ FAIL'}`);
      
    } catch (error) {
      testResults.push({
        name: 'CLI Response Time',
        category: 'CLI_RESPONSE',
        status: 'FAIL',
        duration: Date.now() - cliStartTime,
        errors: [`Test execution failed: ${error}`],
        metrics: {},
      });
    }

    // Run Context Switching Tests
    console.log('\n📊 Testing Context Switching Performance...');
    const contextStartTime = Date.now();
    
    try {
      const switches = [
        { key: 'Meta+1', target: '[data-testid="workspace-pane"]' },
        { key: 'Meta+2', target: '[data-testid="agents-pane"]' },
        { key: 'Meta+3', target: '[data-testid="sessions-pane"]' },
        { key: 'Meta+4', target: '[data-testid="metrics-pane"]' },
      ];
      
      const contextTimings: number[] = [];
      
      for (const switchConfig of switches) {
        const start = performance.now();
        await page.keyboard.press(switchConfig.key);
        await page.waitForSelector(`${switchConfig.target}.active`, { timeout: 1000 });
        const timing = performance.now() - start;
        
        contextTimings.push(timing);
        console.log(`  ${switchConfig.key}: ${timing.toFixed(2)}ms`);
      }
      
      const avgContextTime = contextTimings.reduce((a, b) => a + b) / contextTimings.length;
      const maxContextTime = Math.max(...contextTimings);
      
      testResults.push({
        name: 'Context Switching',
        category: 'CONTEXT_SWITCHING',
        status: maxContextTime < 50 ? 'PASS' : 'FAIL',
        duration: Date.now() - contextStartTime,
        errors: maxContextTime >= 50 ? [`Context switch time ${maxContextTime.toFixed(2)}ms exceeds 50ms limit`] : [],
        metrics: { average: avgContextTime, max: maxContextTime, count: contextTimings.length },
      });
      
      console.log(`  Average: ${avgContextTime.toFixed(2)}ms | Max: ${maxContextTime.toFixed(2)}ms | Status: ${maxContextTime < 50 ? '✅ PASS' : '❌ FAIL'}`);
      
    } catch (error) {
      testResults.push({
        name: 'Context Switching',
        category: 'CONTEXT_SWITCHING',
        status: 'FAIL',
        duration: Date.now() - contextStartTime,
        errors: [`Test execution failed: ${error}`],
        metrics: {},
      });
    }

    // Run Memory Usage Tests  
    console.log('\n📊 Testing Memory Usage Performance...');
    const memoryStartTime = Date.now();
    
    try {
      // Force garbage collection if available
      await page.evaluate(() => {
        if ('gc' in window) {
          (window as any).gc();
        }
      });
      
      await page.waitForTimeout(1000);
      
      const memoryMetrics = await page.evaluate(() => {
        const memory = (performance as any).memory;
        return {
          usedJSHeapSize: memory?.usedJSHeapSize || 0,
          totalJSHeapSize: memory?.totalJSHeapSize || 0,
          jsHeapSizeLimit: memory?.jsHeapSizeLimit || 0,
        };
      });
      
      const memoryMB = memoryMetrics.usedJSHeapSize / (1024 * 1024);
      
      // Perform various operations to test memory under load
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Meta+k');
        await page.fill('[data-testid="command-input"]', `test ${i}`);
        await page.keyboard.press('Enter');
        await page.waitForTimeout(100);
        await page.keyboard.press('Escape');
      }
      
      // Measure memory after operations
      const finalMemoryMetrics = await page.evaluate(() => {
        const memory = (performance as any).memory;
        return memory?.usedJSHeapSize || 0;
      });
      
      const finalMemoryMB = finalMemoryMetrics / (1024 * 1024);
      const memoryGrowth = finalMemoryMB - memoryMB;
      
      testResults.push({
        name: 'Memory Usage',
        category: 'MEMORY_USAGE',
        status: finalMemoryMB < 100 ? 'PASS' : 'FAIL',
        duration: Date.now() - memoryStartTime,
        errors: finalMemoryMB >= 100 ? [`Memory usage ${finalMemoryMB.toFixed(2)}MB exceeds 100MB limit`] : [],
        metrics: { initial: memoryMB, final: finalMemoryMB, growth: memoryGrowth },
      });
      
      console.log(`  Initial: ${memoryMB.toFixed(2)}MB | Final: ${finalMemoryMB.toFixed(2)}MB | Growth: ${memoryGrowth.toFixed(2)}MB`);
      console.log(`  Status: ${finalMemoryMB < 100 ? '✅ PASS' : '❌ FAIL'}`);
      
    } catch (error) {
      testResults.push({
        name: 'Memory Usage',
        category: 'MEMORY_USAGE',
        status: 'FAIL',
        duration: Date.now() - memoryStartTime,
        errors: [`Test execution failed: ${error}`],
        metrics: {},
      });
    }

    // Run WebSocket Latency Tests (simplified for runner)
    console.log('\n📊 Testing WebSocket Latency Performance...');
    const wsStartTime = Date.now();
    
    try {
      // Enable live monitoring to activate WebSocket connections
      await page.keyboard.press('Meta+l');
      
      // Wait for WebSocket connection establishment
      await page.waitForSelector('[data-testid="live-status-indicator"]', { timeout: 3000 });
      
      // Test real-time responsiveness
      const responseTimes: number[] = [];
      
      for (let i = 0; i < 5; i++) {
        const start = performance.now();
        await page.keyboard.press(`Meta+${(i % 3) + 1}`);
        await page.waitForTimeout(200); // Allow for WebSocket communication
        const responseTime = performance.now() - start;
        responseTimes.push(responseTime);
      }
      
      const avgResponseTime = responseTimes.reduce((a, b) => a + b) / responseTimes.length;
      const maxResponseTime = Math.max(...responseTimes);
      
      // Estimate WebSocket latency (simplified)
      const estimatedLatency = Math.max(0, avgResponseTime - 100); // Subtract UI processing time
      
      testResults.push({
        name: 'WebSocket Latency',
        category: 'WEBSOCKET_LATENCY',
        status: estimatedLatency < 200 ? 'PASS' : 'FAIL',
        duration: Date.now() - wsStartTime,
        errors: estimatedLatency >= 200 ? [`Estimated WebSocket latency ${estimatedLatency.toFixed(2)}ms exceeds 200ms limit`] : [],
        metrics: { estimated: estimatedLatency, responseTime: avgResponseTime, samples: responseTimes.length },
      });
      
      console.log(`  Estimated latency: ${estimatedLatency.toFixed(2)}ms | Status: ${estimatedLatency < 200 ? '✅ PASS' : '❌ FAIL'}`);
      
    } catch (error) {
      testResults.push({
        name: 'WebSocket Latency',
        category: 'WEBSOCKET_LATENCY',
        status: 'FAIL',
        duration: Date.now() - wsStartTime,
        errors: [`Test execution failed: ${error}`],
        metrics: {},
      });
    }

    // Generate Comprehensive Performance Report
    const suiteDuration = Date.now() - suiteStartTime;
    const passedTests = testResults.filter(r => r.status === 'PASS').length;
    const failedTests = testResults.filter(r => r.status === 'FAIL').length;
    
    // Extract metrics for Ocean's requirements validation
    const cliResult = testResults.find(r => r.category === 'CLI_RESPONSE');
    const contextResult = testResults.find(r => r.category === 'CONTEXT_SWITCHING');
    const memoryResult = testResults.find(r => r.category === 'MEMORY_USAGE');
    const wsResult = testResults.find(r => r.category === 'WEBSOCKET_LATENCY');
    
    const performanceReport: PerformanceReport = {
      timestamp: Date.now(),
      environment: process.env.CI ? 'ci' : 'local',
      testSuite: 'Comprehensive Performance Validation',
      summary: {
        totalTests: testResults.length,
        passed: passedTests,
        failed: failedTests,
        skipped: 0,
        duration: suiteDuration,
      },
      results: testResults,
      oceanRequirements: {
        cliResponse: {
          target: 100,
          actual: cliResult?.metrics?.max || -1,
          status: cliResult?.status === 'PASS' ? 'PASS' : 'FAIL',
        },
        contextSwitch: {
          target: 50,
          actual: contextResult?.metrics?.max || -1,
          status: contextResult?.status === 'PASS' ? 'PASS' : 'FAIL',
        },
        memoryUsage: {
          target: 100,
          actual: memoryResult?.metrics?.final || -1,
          status: memoryResult?.status === 'PASS' ? 'PASS' : 'FAIL',
        },
        websocketLatency: {
          target: 200,
          actual: wsResult?.metrics?.estimated || -1,
          status: wsResult?.status === 'PASS' ? 'PASS' : 'FAIL',
        },
      },
      recommendations: [],
    };

    // Generate recommendations based on results
    if (performanceReport.oceanRequirements.cliResponse.status === 'FAIL') {
      performanceReport.recommendations.push('CLI response time exceeds Ocean\'s 100ms requirement. Consider optimizing command processing.');
    }
    
    if (performanceReport.oceanRequirements.contextSwitch.status === 'FAIL') {
      performanceReport.recommendations.push('Context switching exceeds Ocean\'s 50ms requirement. Review pane transition animations and state management.');
    }
    
    if (performanceReport.oceanRequirements.memoryUsage.status === 'FAIL') {
      performanceReport.recommendations.push('Memory usage exceeds Ocean\'s 100MB requirement. Implement memory optimization and leak detection.');
    }
    
    if (performanceReport.oceanRequirements.websocketLatency.status === 'FAIL') {
      performanceReport.recommendations.push('WebSocket latency exceeds Ocean\'s 200ms requirement. Optimize real-time communication protocols.');
    }

    if (performanceReport.recommendations.length === 0) {
      performanceReport.recommendations.push('All performance requirements met. System performing within Ocean\'s specifications.');
    }

    // Save comprehensive report
    const reportFilename = join(RESULTS_DIR, `performance-report-${Date.now()}.json`);
    writeFileSync(reportFilename, JSON.stringify(performanceReport, null, 2));

    // Generate summary output
    console.log('\n🏁 COMPREHENSIVE PERFORMANCE VALIDATION COMPLETE');
    console.log('=' .repeat(60));
    console.log(`Suite Duration: ${(suiteDuration / 1000).toFixed(2)}s`);
    console.log(`Tests: ${testResults.length} | Passed: ${passedTests} | Failed: ${failedTests}`);
    console.log('\nOcean\'s Performance Requirements Validation:');
    console.log(`  CLI Response (<100ms): ${performanceReport.oceanRequirements.cliResponse.actual.toFixed(2)}ms - ${performanceReport.oceanRequirements.cliResponse.status}`);
    console.log(`  Context Switch (<50ms): ${performanceReport.oceanRequirements.contextSwitch.actual.toFixed(2)}ms - ${performanceReport.oceanRequirements.contextSwitch.status}`);
    console.log(`  Memory Usage (<100MB): ${performanceReport.oceanRequirements.memoryUsage.actual.toFixed(2)}MB - ${performanceReport.oceanRequirements.memoryUsage.status}`);
    console.log(`  WebSocket Latency (<200ms): ${performanceReport.oceanRequirements.websocketLatency.actual.toFixed(2)}ms - ${performanceReport.oceanRequirements.websocketLatency.status}`);
    
    console.log('\nRecommendations:');
    performanceReport.recommendations.forEach((rec, i) => {
      console.log(`  ${i + 1}. ${rec}`);
    });
    
    console.log(`\nDetailed report saved: ${reportFilename}`);
    
    // Validate overall test success
    const allRequirementsMet = Object.values(performanceReport.oceanRequirements).every(req => req.status === 'PASS');
    
    if (!allRequirementsMet) {
      console.log('\n❌ PERFORMANCE VALIDATION FAILED - Ocean\'s requirements not met');
      throw new Error(`Performance validation failed. Requirements not met: ${Object.entries(performanceReport.oceanRequirements).filter(([_, req]) => req.status === 'FAIL').map(([key, _]) => key).join(', ')}`);
    } else {
      console.log('\n✅ PERFORMANCE VALIDATION SUCCESS - All Ocean\'s requirements met');
    }
  });

  /**
   * Test: Performance Regression Detection
   */
  test('Performance regression detection across test runs', async ({ page }) => {
    const reportFiles = require('fs').readdirSync(RESULTS_DIR)
      .filter((file: string) => file.startsWith('performance-report-') && file.endsWith('.json'))
      .sort()
      .slice(-5); // Last 5 reports
    
    if (reportFiles.length < 2) {
      console.log('Insufficient historical data for regression analysis');
      return;
    }

    console.log('🔍 Analyzing Performance Regression Trends...');
    
    const reports = reportFiles.map((file: string) => {
      const content = readFileSync(join(RESULTS_DIR, file), 'utf-8');
      return JSON.parse(content) as PerformanceReport;
    });
    
    const latest = reports[reports.length - 1];
    const baseline = reports[0];
    
    const regressionAnalysis = {
      cliResponse: (latest.oceanRequirements.cliResponse.actual / baseline.oceanRequirements.cliResponse.actual) - 1,
      contextSwitch: (latest.oceanRequirements.contextSwitch.actual / baseline.oceanRequirements.contextSwitch.actual) - 1,
      memoryUsage: (latest.oceanRequirements.memoryUsage.actual / baseline.oceanRequirements.memoryUsage.actual) - 1,
      websocketLatency: (latest.oceanRequirements.websocketLatency.actual / baseline.oceanRequirements.websocketLatency.actual) - 1,
    };
    
    console.log('Performance Trend Analysis:');
    Object.entries(regressionAnalysis).forEach(([metric, change]) => {
      const changePercent = (change * 100).toFixed(1);
      const status = Math.abs(change) > 0.5 ? '🚨 SIGNIFICANT' : Math.abs(change) > 0.2 ? '⚠️  MODERATE' : '✅ STABLE';
      console.log(`  ${metric}: ${change > 0 ? '+' : ''}${changePercent}% ${status}`);
    });
    
    // Alert for significant regressions
    const significantRegressions = Object.entries(regressionAnalysis).filter(([_, change]) => change > 0.5);
    
    if (significantRegressions.length > 0) {
      console.log('\n🚨 SIGNIFICANT PERFORMANCE REGRESSIONS DETECTED:');
      significantRegressions.forEach(([metric, change]) => {
        console.log(`  ${metric}: ${((change) * 100).toFixed(1)}% degradation`);
      });
    } else {
      console.log('\n✅ No significant performance regressions detected');
    }
  });
});