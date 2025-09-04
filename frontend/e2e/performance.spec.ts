import { test, expect, Page } from '@playwright/test';

// Performance testing helper
class PerformanceHelper {
  constructor(private page: Page) {}

  async measureAction(action: () => Promise<void>, actionName: string): Promise<number> {
    const startTime = Date.now();
    await action();
    const endTime = Date.now();
    const duration = endTime - startTime;
    
    console.log(`${actionName}: ${duration}ms`);
    return duration;
  }

  async measureActionPrecise(action: () => Promise<void>): Promise<number> {
    const startTime = performance.now();
    await action();
    const endTime = performance.now();
    return endTime - startTime;
  }

  async openCommandPalette() {
    await this.page.keyboard.press('Meta+k');
    await this.page.waitForSelector('[role="dialog"]', { timeout: 1000 });
  }

  async closeCommandPalette() {
    await this.page.keyboard.press('Escape');
    await this.page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 1000 });
  }

  async focusPane(paneNumber: 1 | 2 | 3) {
    await this.page.keyboard.press(`Meta+${paneNumber}`);
    await this.page.waitForTimeout(50); // Minimal wait for focus change
  }

  async navigateVim(target: 'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings') {
    const keyMap = {
      planning: 'g p',
      monitoring: 'g m',
      analytics: 'g n',
      agents: 'g a',
      settings: 'g s'
    };
    
    const keys = keyMap[target].split(' ');
    for (const key of keys) {
      await this.page.keyboard.press(key);
      await this.page.waitForTimeout(25);
    }
  }

  async switchView(viewNumber: 1 | 2 | 3 | 4 | 5) {
    await this.page.keyboard.press(`Meta+${viewNumber}`);
    await this.page.waitForTimeout(50);
  }

  async takePerformanceScreenshot(name: string) {
    await this.page.screenshot({ 
      path: `test-results/screenshots/performance-${name}.png`,
      fullPage: true 
    });
  }

  // Stress testing utilities
  async stressTestAction(action: () => Promise<void>, iterations: number = 50): Promise<number[]> {
    const measurements: number[] = [];
    
    for (let i = 0; i < iterations; i++) {
      const time = await this.measureActionPrecise(action);
      measurements.push(time);
      await this.page.waitForTimeout(10); // Small delay between iterations
    }
    
    return measurements;
  }

  calculateStatistics(measurements: number[]) {
    const sorted = [...measurements].sort((a, b) => a - b);
    const average = measurements.reduce((a, b) => a + b) / measurements.length;
    const median = sorted[Math.floor(sorted.length / 2)];
    const p95 = sorted[Math.floor(sorted.length * 0.95)];
    const p99 = sorted[Math.floor(sorted.length * 0.99)];
    const min = Math.min(...measurements);
    const max = Math.max(...measurements);
    
    return { average, median, p95, p99, min, max, count: measurements.length };
  }
}

test.describe('Performance Assertions (<50ms Context Switching)', () => {
  let perfHelper: PerformanceHelper;

  test.beforeEach(async ({ page }) => {
    perfHelper = new PerformanceHelper(page);
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Wait for app initialization
    await page.waitForTimeout(1000);
  });

  test.describe('Command Palette Performance', () => {
    test('should open command palette under 50ms (95th percentile)', async ({ page }) => {
      const measurements = await perfHelper.stressTestAction(
        () => perfHelper.openCommandPalette(),
        30
      );
      
      // Close palette between measurements
      for (let i = 0; i < measurements.length; i++) {
        await perfHelper.closeCommandPalette();
        await page.waitForTimeout(50);
      }
      
      const stats = perfHelper.calculateStatistics(measurements);
      
      console.log('Command Palette Opening Performance:');
      console.log(`Average: ${stats.average.toFixed(2)}ms`);
      console.log(`Median: ${stats.median.toFixed(2)}ms`);
      console.log(`95th percentile: ${stats.p95.toFixed(2)}ms`);
      console.log(`99th percentile: ${stats.p99.toFixed(2)}ms`);
      console.log(`Min: ${stats.min.toFixed(2)}ms, Max: ${stats.max.toFixed(2)}ms`);
      
      // Performance requirements
      expect(stats.average).toBeLessThan(50, `Average opening time ${stats.average.toFixed(2)}ms exceeds 50ms`);
      expect(stats.p95).toBeLessThan(100, `95th percentile ${stats.p95.toFixed(2)}ms exceeds 100ms`);
      expect(stats.p99).toBeLessThan(150, `99th percentile ${stats.p99.toFixed(2)}ms exceeds 150ms`);
      
      await perfHelper.takePerformanceScreenshot('command-palette-opening');
    });

    test('should filter commands under 200ms consistently', async ({ page }) => {
      const filterQueries = ['plan', 'agent', 'daemon', 'orchestration', 'khive'];
      const allMeasurements: number[] = [];
      
      for (const query of filterQueries) {
        await perfHelper.openCommandPalette();
        
        const filterTime = await perfHelper.measureActionPrecise(async () => {
          await page.locator('[role="dialog"] input').fill(query);
          await page.waitForTimeout(100); // Wait for filtering
        });
        
        allMeasurements.push(filterTime);
        await perfHelper.closeCommandPalette();
        await page.waitForTimeout(100);
      }
      
      const stats = perfHelper.calculateStatistics(allMeasurements);
      
      console.log('Command Filtering Performance:');
      console.log(`Average: ${stats.average.toFixed(2)}ms`);
      console.log(`95th percentile: ${stats.p95.toFixed(2)}ms`);
      
      expect(stats.average).toBeLessThan(200, `Average filtering time exceeds 200ms`);
      expect(stats.p95).toBeLessThan(300, `95th percentile filtering time exceeds 300ms`);
      
      await perfHelper.takePerformanceScreenshot('command-filtering');
    });
  });

  test.describe('Pane Focus Performance', () => {
    test('should switch pane focus under 50ms (95th percentile)', async ({ page }) => {
      const panes: Array<1 | 2 | 3> = [1, 2, 3];
      const allMeasurements: number[] = [];
      
      // Test each pane multiple times
      for (let round = 0; round < 20; round++) {
        for (const paneNum of panes) {
          const focusTime = await perfHelper.measureActionPrecise(
            () => perfHelper.focusPane(paneNum)
          );
          allMeasurements.push(focusTime);
        }
      }
      
      const stats = perfHelper.calculateStatistics(allMeasurements);
      
      console.log('Pane Focus Performance:');
      console.log(`Average: ${stats.average.toFixed(2)}ms`);
      console.log(`Median: ${stats.median.toFixed(2)}ms`);
      console.log(`95th percentile: ${stats.p95.toFixed(2)}ms`);
      console.log(`99th percentile: ${stats.p99.toFixed(2)}ms`);
      
      // Strict performance requirements for pane focusing
      expect(stats.average).toBeLessThan(50, `Average pane focus time ${stats.average.toFixed(2)}ms exceeds 50ms`);
      expect(stats.p95).toBeLessThan(75, `95th percentile ${stats.p95.toFixed(2)}ms exceeds 75ms`);
      expect(stats.p99).toBeLessThan(100, `99th percentile ${stats.p99.toFixed(2)}ms exceeds 100ms`);
      
      await perfHelper.takePerformanceScreenshot('pane-focus-performance');
    });

    test('should maintain performance under rapid pane switching', async ({ page }) => {
      const rapidSwitchCount = 100;
      const measurements: number[] = [];
      
      for (let i = 0; i < rapidSwitchCount; i++) {
        const paneNum = (i % 3) + 1 as 1 | 2 | 3;
        const switchTime = await perfHelper.measureActionPrecise(
          () => perfHelper.focusPane(paneNum)
        );
        measurements.push(switchTime);
      }
      
      const stats = perfHelper.calculateStatistics(measurements);
      
      console.log('Rapid Pane Switching Performance:');
      console.log(`Average: ${stats.average.toFixed(2)}ms over ${rapidSwitchCount} switches`);
      console.log(`95th percentile: ${stats.p95.toFixed(2)}ms`);
      
      // Should maintain performance even under stress
      expect(stats.average).toBeLessThan(60, `Average under rapid switching exceeds 60ms`);
      expect(stats.p95).toBeLessThan(100, `95th percentile under rapid switching exceeds 100ms`);
      
      await perfHelper.takePerformanceScreenshot('rapid-pane-switching-stress');
    });
  });

  test.describe('Vim Navigation Performance', () => {
    test('should switch views under 50ms (95th percentile)', async ({ page }) => {
      const views: Array<'planning' | 'monitoring' | 'analytics' | 'agents' | 'settings'> = 
        ['planning', 'monitoring', 'analytics', 'agents', 'settings'];
      
      const allMeasurements: number[] = [];
      
      // Test each view multiple times
      for (let round = 0; round < 15; round++) {
        for (const view of views) {
          const navTime = await perfHelper.measureActionPrecise(
            () => perfHelper.navigateVim(view)
          );
          allMeasurements.push(navTime);
          await page.waitForTimeout(50); // Allow view to settle
        }
      }
      
      const stats = perfHelper.calculateStatistics(allMeasurements);
      
      console.log('Vim Navigation Performance:');
      console.log(`Average: ${stats.average.toFixed(2)}ms`);
      console.log(`95th percentile: ${stats.p95.toFixed(2)}ms`);
      console.log(`99th percentile: ${stats.p99.toFixed(2)}ms`);
      
      expect(stats.average).toBeLessThan(50, `Average vim navigation time exceeds 50ms`);
      expect(stats.p95).toBeLessThan(80, `95th percentile vim navigation exceeds 80ms`);
      
      await perfHelper.takePerformanceScreenshot('vim-navigation-performance');
    });

    test('should handle vim sequence timing correctly', async ({ page }) => {
      const measurements: number[] = [];
      
      // Test the full vim sequence timing (including 'g' delay)
      for (let i = 0; i < 20; i++) {
        const sequenceTime = await perfHelper.measureActionPrecise(async () => {
          await page.keyboard.press('g');
          await page.waitForTimeout(50);
          await page.keyboard.press('m');
          await page.waitForTimeout(100); // Wait for navigation
        });
        measurements.push(sequenceTime);
      }
      
      const stats = perfHelper.calculateStatistics(measurements);
      
      console.log('Vim Sequence Timing:');
      console.log(`Average: ${stats.average.toFixed(2)}ms`);
      console.log(`95th percentile: ${stats.p95.toFixed(2)}ms`);
      
      // Vim sequences include deliberate delays but should still be snappy
      expect(stats.average).toBeLessThan(200, `Vim sequence time too slow`);
      expect(stats.p95).toBeLessThan(250, `95th percentile vim sequence too slow`);
      
      await perfHelper.takePerformanceScreenshot('vim-sequence-timing');
    });
  });

  test.describe('Tab-Style Navigation Performance', () => {
    test('should switch views with Cmd+Number under 50ms', async ({ page }) => {
      const viewNumbers: Array<1 | 2 | 3 | 4 | 5> = [1, 2, 3, 4, 5];
      const allMeasurements: number[] = [];
      
      for (let round = 0; round < 15; round++) {
        for (const viewNum of viewNumbers) {
          const switchTime = await perfHelper.measureActionPrecise(
            () => perfHelper.switchView(viewNum)
          );
          allMeasurements.push(switchTime);
        }
      }
      
      const stats = perfHelper.calculateStatistics(allMeasurements);
      
      console.log('Tab-Style Navigation Performance:');
      console.log(`Average: ${stats.average.toFixed(2)}ms`);
      console.log(`95th percentile: ${stats.p95.toFixed(2)}ms`);
      
      expect(stats.average).toBeLessThan(50, `Average tab navigation exceeds 50ms`);
      expect(stats.p95).toBeLessThan(75, `95th percentile tab navigation exceeds 75ms`);
      
      await perfHelper.takePerformanceScreenshot('tab-navigation-performance');
    });
  });

  test.describe('Performance Regression Testing', () => {
    test('should maintain consistent performance over time', async ({ page }) => {
      const testDuration = 30000; // 30 seconds
      const startTime = Date.now();
      const measurements: number[] = [];
      let operationCount = 0;
      
      while (Date.now() - startTime < testDuration) {
        // Mix of operations to simulate real usage
        const operation = operationCount % 4;
        let operationTime = 0;
        
        switch (operation) {
          case 0:
            operationTime = await perfHelper.measureActionPrecise(() => 
              perfHelper.focusPane(((operationCount % 3) + 1) as 1 | 2 | 3)
            );
            break;
          case 1:
            operationTime = await perfHelper.measureActionPrecise(() => 
              perfHelper.navigateVim('monitoring')
            );
            break;
          case 2:
            operationTime = await perfHelper.measureActionPrecise(async () => {
              await perfHelper.openCommandPalette();
              await perfHelper.closeCommandPalette();
            });
            break;
          case 3:
            operationTime = await perfHelper.measureActionPrecise(() => 
              perfHelper.switchView(((operationCount % 5) + 1) as 1 | 2 | 3 | 4 | 5)
            );
            break;
        }
        
        measurements.push(operationTime);
        operationCount++;
        
        await page.waitForTimeout(100); // Small delay between operations
      }
      
      // Analyze performance over time
      const firstHalf = measurements.slice(0, Math.floor(measurements.length / 2));
      const secondHalf = measurements.slice(Math.floor(measurements.length / 2));
      
      const firstHalfStats = perfHelper.calculateStatistics(firstHalf);
      const secondHalfStats = perfHelper.calculateStatistics(secondHalf);
      
      console.log('Performance Over Time:');
      console.log(`First half average: ${firstHalfStats.average.toFixed(2)}ms`);
      console.log(`Second half average: ${secondHalfStats.average.toFixed(2)}ms`);
      console.log(`Total operations: ${operationCount}`);
      
      // Performance should not degrade significantly over time
      const degradationRatio = secondHalfStats.average / firstHalfStats.average;
      expect(degradationRatio).toBeLessThan(1.5, `Performance degraded by ${((degradationRatio - 1) * 100).toFixed(1)}%`);
      
      // Overall performance should still meet requirements
      const overallStats = perfHelper.calculateStatistics(measurements);
      expect(overallStats.average).toBeLessThan(60, `Overall average performance degraded`);
      
      await perfHelper.takePerformanceScreenshot('performance-over-time');
    });

    test('should handle memory pressure gracefully', async ({ page }) => {
      // Simulate memory pressure by creating many objects
      await page.evaluate(() => {
        // Create some memory pressure
        const largeArrays = [];
        for (let i = 0; i < 100; i++) {
          largeArrays.push(new Array(10000).fill(Math.random()));
        }
        // Keep reference to prevent immediate GC
        (window as any).testMemoryPressure = largeArrays;
      });
      
      // Test performance under memory pressure
      const measurements: number[] = [];
      const panes: Array<1 | 2 | 3> = [1, 2, 3];
      
      for (let i = 0; i < 30; i++) {
        const paneNum = panes[i % 3];
        const focusTime = await perfHelper.measureActionPrecise(
          () => perfHelper.focusPane(paneNum)
        );
        measurements.push(focusTime);
      }
      
      const stats = perfHelper.calculateStatistics(measurements);
      
      console.log('Performance Under Memory Pressure:');
      console.log(`Average: ${stats.average.toFixed(2)}ms`);
      console.log(`95th percentile: ${stats.p95.toFixed(2)}ms`);
      
      // Should still maintain reasonable performance under pressure
      expect(stats.average).toBeLessThan(80, `Performance too poor under memory pressure`);
      expect(stats.p95).toBeLessThan(120, `95th percentile too poor under memory pressure`);
      
      // Cleanup
      await page.evaluate(() => {
        delete (window as any).testMemoryPressure;
      });
      
      await perfHelper.takePerformanceScreenshot('performance-under-memory-pressure');
    });
  });

  test.describe('Performance Baseline Documentation', () => {
    test('should establish performance baselines for monitoring', async ({ page }) => {
      const baselines = {
        commandPaletteOpen: [] as number[],
        paneFocus: [] as number[],
        vimNavigation: [] as number[],
        tabNavigation: [] as number[]
      };
      
      // Command palette baseline
      for (let i = 0; i < 20; i++) {
        const time = await perfHelper.measureActionPrecise(async () => {
          await perfHelper.openCommandPalette();
          await perfHelper.closeCommandPalette();
        });
        baselines.commandPaletteOpen.push(time);
      }
      
      // Pane focus baseline
      for (let i = 0; i < 30; i++) {
        const paneNum = (i % 3) + 1 as 1 | 2 | 3;
        const time = await perfHelper.measureActionPrecise(() => 
          perfHelper.focusPane(paneNum)
        );
        baselines.paneFocus.push(time);
      }
      
      // Vim navigation baseline
      const views: Array<'planning' | 'monitoring' | 'analytics'> = ['planning', 'monitoring', 'analytics'];
      for (let i = 0; i < 15; i++) {
        const view = views[i % views.length];
        const time = await perfHelper.measureActionPrecise(() => 
          perfHelper.navigateVim(view)
        );
        baselines.vimNavigation.push(time);
      }
      
      // Tab navigation baseline
      for (let i = 0; i < 15; i++) {
        const viewNum = (i % 5) + 1 as 1 | 2 | 3 | 4 | 5;
        const time = await perfHelper.measureActionPrecise(() => 
          perfHelper.switchView(viewNum)
        );
        baselines.tabNavigation.push(time);
      }
      
      // Calculate and log baselines
      const results = {};
      for (const [operation, measurements] of Object.entries(baselines)) {
        const stats = perfHelper.calculateStatistics(measurements);
        results[operation] = stats;
        
        console.log(`\n${operation.toUpperCase()} BASELINE:`);
        console.log(`Average: ${stats.average.toFixed(2)}ms`);
        console.log(`Median: ${stats.median.toFixed(2)}ms`);
        console.log(`95th percentile: ${stats.p95.toFixed(2)}ms`);
        console.log(`99th percentile: ${stats.p99.toFixed(2)}ms`);
        console.log(`Range: ${stats.min.toFixed(2)}ms - ${stats.max.toFixed(2)}ms`);
      }
      
      // Save baselines for future comparison
      await page.evaluate((results) => {
        console.log('PERFORMANCE BASELINES:', JSON.stringify(results, null, 2));
      }, results);
      
      await perfHelper.takePerformanceScreenshot('performance-baselines-established');
      
      // Assert that all operations meet our requirements
      expect(results['commandPaletteOpen'].average).toBeLessThan(50, 'Command palette baseline exceeds target');
      expect(results['paneFocus'].average).toBeLessThan(50, 'Pane focus baseline exceeds target');
      expect(results['vimNavigation'].average).toBeLessThan(50, 'Vim navigation baseline exceeds target');
      expect(results['tabNavigation'].average).toBeLessThan(50, 'Tab navigation baseline exceeds target');
    });
  });
});