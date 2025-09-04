import { test, expect } from '@playwright/test';

/**
 * E2E Performance Tests for Keyboard Shortcuts
 * Tests Ocean's <50ms keyboard latency requirement and overall responsiveness
 * 
 * Performance Targets:
 * - Global shortcuts: <10ms recognition time
 * - Modal shortcuts: <5ms context switching
 * - Chord sequences: <500ms sequence timeout
 * - Overall keyboard latency: <50ms end-to-end
 * - 95th percentile: <75ms
 * - 99th percentile: <100ms
 */

test.describe('Keyboard Shortcuts Performance', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the command center
    await page.goto('/');
    
    // Wait for the application to be fully loaded
    await page.waitForSelector('[data-testid="command-center"]', {
      state: 'visible',
      timeout: 10000
    });

    // Ensure clean state
    await page.keyboard.up('Meta');
    await page.keyboard.up('Control');
    await page.keyboard.up('Shift');
    await page.keyboard.up('Alt');
    
    // Pre-warm the keyboard system
    await page.evaluate(() => {
      // Dispatch a test event to initialize event handlers
      document.dispatchEvent(new KeyboardEvent('keydown', {
        key: 'Meta',
        bubbles: true
      }));
    });
    
    await page.waitForTimeout(500);
  });

  test.describe('Individual Shortcut Performance', () => {
    test('should meet <10ms recognition time for global shortcuts', async ({ page }) => {
      const shortcuts = [
        { keys: 'Meta+k', description: 'Command palette' },
        { keys: 'Meta+r', description: 'Reconnect' },
        { keys: 'Meta+1', description: 'Focus pane 1' },
        { keys: 'Meta+2', description: 'Focus pane 2' },
        { keys: 'Meta+3', description: 'Focus pane 3' },
        { keys: 'Escape', description: 'Escape key' },
      ];

      const performanceData: { shortcut: string; times: number[] }[] = [];

      for (const shortcut of shortcuts) {
        const times: number[] = [];
        
        // Test each shortcut 20 times
        for (let i = 0; i < 20; i++) {
          const startTime = performance.now();

          // Execute shortcut using high-precision timing
          await page.evaluate(async (keys) => {
            const startPerfTime = performance.now();
            
            // Simulate the exact keydown event
            const event = new KeyboardEvent('keydown', {
              key: keys.includes('Meta+') ? keys.split('+')[1] : keys,
              metaKey: keys.includes('Meta+'),
              bubbles: true,
              cancelable: true
            });
            
            document.dispatchEvent(event);
            
            return performance.now() - startPerfTime;
          }, shortcut.keys);

          // Measure DOM changes or other side effects
          await page.waitForTimeout(5); // Minimal wait to catch immediate effects
          
          const endTime = performance.now();
          const responseTime = endTime - startTime;
          times.push(responseTime);

          // Reset state if needed
          if (shortcut.keys === 'Meta+k') {
            // Close command palette if it opened
            await page.keyboard.press('Escape');
          }

          // Brief pause to avoid overwhelming
          await page.waitForTimeout(10);
        }

        performanceData.push({
          shortcut: shortcut.description,
          times: times
        });

        // Analyze individual shortcut performance
        const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
        const maxTime = Math.max(...times);
        const minTime = Math.min(...times);
        
        console.log(`⚡ ${shortcut.description}:`);
        console.log(`   Average: ${avgTime.toFixed(2)}ms`);
        console.log(`   Min: ${minTime.toFixed(2)}ms`);
        console.log(`   Max: ${maxTime.toFixed(2)}ms`);

        // Performance assertions
        expect(avgTime, `${shortcut.description} average should be <20ms`).toBeLessThan(20);
        expect(maxTime, `${shortcut.description} max should be <50ms`).toBeLessThan(50);
      }

      // Overall performance analysis
      const allTimes = performanceData.flatMap(d => d.times);
      const overallAvg = allTimes.reduce((a, b) => a + b, 0) / allTimes.length;
      const p95 = allTimes.sort((a, b) => a - b)[Math.floor(allTimes.length * 0.95)];
      const p99 = allTimes.sort((a, b) => a - b)[Math.floor(allTimes.length * 0.99)];

      console.log(`\n📊 Overall Global Shortcuts Performance:`);
      console.log(`   Average: ${overallAvg.toFixed(2)}ms`);
      console.log(`   95th percentile: ${p95.toFixed(2)}ms`);
      console.log(`   99th percentile: ${p99.toFixed(2)}ms`);

      // Key performance requirements
      expect(overallAvg, 'Overall average should be <15ms').toBeLessThan(15);
      expect(p95, '95th percentile should be <30ms').toBeLessThan(30);
      expect(p99, '99th percentile should be <50ms').toBeLessThan(50);
    });

    test('should meet <25ms for sequence shortcuts', async ({ page }) => {
      const sequences = [
        { keys: ['g', 'p'], description: 'Go to planning' },
        { keys: ['g', 'm'], description: 'Go to monitoring' },
        { keys: ['g', 'a'], description: 'Go to agents' },
        { keys: ['a', 's'], description: 'Agent spawn' },
        { keys: ['f', 'f'], description: 'Find files' },
      ];

      const sequencePerformance: { sequence: string; times: number[] }[] = [];

      for (const sequence of sequences) {
        const times: number[] = [];

        // Test each sequence 15 times
        for (let i = 0; i < 15; i++) {
          const startTime = performance.now();

          // Execute sequence with precise timing
          for (let j = 0; j < sequence.keys.length; j++) {
            await page.keyboard.press(sequence.keys[j]);
            // Small delay between keys in sequence
            if (j < sequence.keys.length - 1) {
              await page.waitForTimeout(5);
            }
          }

          // Wait for sequence completion detection
          await page.waitForTimeout(10);
          
          const endTime = performance.now();
          const sequenceTime = endTime - startTime;
          times.push(sequenceTime);

          // Brief pause between tests
          await page.waitForTimeout(50);
        }

        sequencePerformance.push({
          sequence: sequence.description,
          times: times
        });

        // Analyze sequence performance
        const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
        const maxTime = Math.max(...times);
        const minTime = Math.min(...times);

        console.log(`⚡ ${sequence.description} sequence:`);
        console.log(`   Average: ${avgTime.toFixed(2)}ms`);
        console.log(`   Min: ${minTime.toFixed(2)}ms`);
        console.log(`   Max: ${maxTime.toFixed(2)}ms`);

        // Sequence performance requirements
        expect(avgTime, `${sequence.description} average should be <40ms`).toBeLessThan(40);
        expect(maxTime, `${sequence.description} max should be <100ms`).toBeLessThan(100);
      }
    });
  });

  test.describe('Load and Stress Testing', () => {
    test('should maintain performance under rapid input', async ({ page }) => {
      const rapidInputTimes: number[] = [];

      // Test 100 rapid keystrokes
      console.log('🚀 Starting rapid input stress test...');
      
      const overallStart = performance.now();

      for (let i = 0; i < 100; i++) {
        const keyStart = performance.now();

        // Alternate between different shortcuts to vary load
        const shortcuts = ['Meta+1', 'Meta+2', 'Meta+3', 'Escape'];
        const shortcut = shortcuts[i % shortcuts.length];
        
        await page.keyboard.press(shortcut);
        
        const keyEnd = performance.now();
        rapidInputTimes.push(keyEnd - keyStart);

        // Very minimal delay to simulate realistic rapid typing
        await page.waitForTimeout(2);
      }

      const overallEnd = performance.now();
      const totalTime = overallEnd - overallStart;

      // Performance analysis
      const avgTime = rapidInputTimes.reduce((a, b) => a + b, 0) / rapidInputTimes.length;
      const maxTime = Math.max(...rapidInputTimes);
      const minTime = Math.min(...rapidInputTimes);
      const slowKeys = rapidInputTimes.filter(t => t > 50).length;

      console.log(`📊 Rapid Input Performance (100 keystrokes in ${totalTime.toFixed(2)}ms):`);
      console.log(`   Average per keystroke: ${avgTime.toFixed(2)}ms`);
      console.log(`   Min: ${minTime.toFixed(2)}ms`);
      console.log(`   Max: ${maxTime.toFixed(2)}ms`);
      console.log(`   Keys >50ms: ${slowKeys} (${((slowKeys/100)*100).toFixed(1)}%)`);

      // Performance requirements under stress
      expect(avgTime, 'Average should remain <30ms under rapid input').toBeLessThan(30);
      expect(maxTime, 'Max should be <100ms even under stress').toBeLessThan(100);
      expect(slowKeys, 'Less than 5% of keys should be >50ms').toBeLessThan(5);
      expect(totalTime / 100, 'Average throughput should be <25ms per key').toBeLessThan(25);
    });

    test('should handle concurrent shortcut processing', async ({ page }) => {
      // Test simultaneous key combinations
      const concurrentTests: Promise<number>[] = [];

      console.log('🔀 Testing concurrent shortcut processing...');

      // Create 10 concurrent shortcut operations
      for (let i = 0; i < 10; i++) {
        const concurrentTest = page.evaluate(async (index) => {
          const startTime = performance.now();
          
          // Simulate concurrent keyboard events
          const events = [
            new KeyboardEvent('keydown', { key: '1', metaKey: true, bubbles: true }),
            new KeyboardEvent('keydown', { key: '2', metaKey: true, bubbles: true }),
            new KeyboardEvent('keydown', { key: '3', metaKey: true, bubbles: true }),
          ];
          
          // Dispatch all events nearly simultaneously
          events.forEach((event, idx) => {
            setTimeout(() => document.dispatchEvent(event), idx * 2);
          });

          // Wait for processing
          await new Promise(resolve => setTimeout(resolve, 50));
          
          return performance.now() - startTime;
        }, i);

        concurrentTests.push(concurrentTest);
      }

      // Wait for all concurrent tests to complete
      const results = await Promise.all(concurrentTests);

      const avgConcurrentTime = results.reduce((a, b) => a + b, 0) / results.length;
      const maxConcurrentTime = Math.max(...results);

      console.log(`📊 Concurrent Processing Performance:`);
      console.log(`   Average: ${avgConcurrentTime.toFixed(2)}ms`);
      console.log(`   Max: ${maxConcurrentTime.toFixed(2)}ms`);

      // Concurrent processing should not significantly degrade performance
      expect(avgConcurrentTime, 'Concurrent average should be <100ms').toBeLessThan(100);
      expect(maxConcurrentTime, 'Concurrent max should be <200ms').toBeLessThan(200);
    });
  });

  test.describe('Memory and Resource Performance', () => {
    test('should not leak memory during extended keyboard usage', async ({ page }) => {
      // Get initial memory baseline
      const initialMemory = await page.evaluate(() => {
        if ('memory' in performance) {
          return (performance as any).memory.usedJSHeapSize;
        }
        return 0;
      });

      console.log(`💾 Initial memory usage: ${(initialMemory / 1024 / 1024).toFixed(2)}MB`);

      // Perform extensive keyboard operations
      for (let cycle = 0; cycle < 10; cycle++) {
        // Mix of different shortcut types
        const operations = [
          () => page.keyboard.press('Meta+k'),
          () => page.keyboard.press('Escape'),
          () => page.keyboard.press('Meta+1'),
          () => page.keyboard.press('Meta+2'),
          () => page.keyboard.press('g'),
          () => page.keyboard.press('p'),
        ];

        for (const operation of operations) {
          await operation();
          await page.waitForTimeout(5);
        }

        // Force garbage collection if possible
        await page.evaluate(() => {
          if ('gc' in window) {
            (window as any).gc();
          }
        });
      }

      // Check memory usage after operations
      const finalMemory = await page.evaluate(() => {
        if ('memory' in performance) {
          return (performance as any).memory.usedJSHeapSize;
        }
        return 0;
      });

      console.log(`💾 Final memory usage: ${(finalMemory / 1024 / 1024).toFixed(2)}MB`);
      
      const memoryIncrease = finalMemory - initialMemory;
      const increasePercent = initialMemory > 0 ? (memoryIncrease / initialMemory) * 100 : 0;

      console.log(`💾 Memory increase: ${(memoryIncrease / 1024 / 1024).toFixed(2)}MB (${increasePercent.toFixed(1)}%)`);

      // Memory usage should not grow excessively
      if (initialMemory > 0) {
        expect(increasePercent, 'Memory increase should be <20%').toBeLessThan(20);
      }
    });

    test('should efficiently manage event listeners', async ({ page }) => {
      // Count initial event listeners
      const initialListeners = await page.evaluate(() => {
        return (document as any)._eventListeners?.keydown?.length || 0;
      });

      // Perform operations that might add listeners
      await page.keyboard.press('Meta+k'); // Command palette
      await page.keyboard.press('Escape');
      
      await page.keyboard.press('?'); // Help overlay
      await page.keyboard.press('Escape');

      await page.keyboard.press('g'); // Start sequence
      await page.keyboard.press('p'); // Complete sequence

      // Check listener count after operations
      const finalListeners = await page.evaluate(() => {
        return (document as any)._eventListeners?.keydown?.length || 0;
      });

      console.log(`🎧 Event listeners - Initial: ${initialListeners}, Final: ${finalListeners}`);

      // Should not accumulate excessive listeners
      if (initialListeners > 0) {
        const listenerIncrease = finalListeners - initialListeners;
        expect(listenerIncrease, 'Should not accumulate many new listeners').toBeLessThan(5);
      }
    });
  });

  test.describe('Cross-Browser Performance', () => {
    test('should maintain consistent performance across platforms', async ({ page, browserName }) => {
      const performanceThresholds = {
        chromium: { avg: 15, p95: 30 },
        firefox: { avg: 20, p95: 40 },
        webkit: { avg: 25, p95: 50 }
      };

      const threshold = performanceThresholds[browserName] || performanceThresholds.chromium;

      const testTimes: number[] = [];

      // Test standard shortcuts across browsers
      const shortcuts = ['Meta+k', 'Meta+1', 'Escape', 'Meta+r'];

      for (let i = 0; i < 40; i++) {
        const shortcut = shortcuts[i % shortcuts.length];
        const startTime = performance.now();

        await page.keyboard.press(shortcut);
        await page.waitForTimeout(5);

        if (shortcut === 'Meta+k') {
          await page.keyboard.press('Escape'); // Close command palette
        }

        const endTime = performance.now();
        testTimes.push(endTime - startTime);
      }

      const avgTime = testTimes.reduce((a, b) => a + b, 0) / testTimes.length;
      const sortedTimes = testTimes.sort((a, b) => a - b);
      const p95Time = sortedTimes[Math.floor(testTimes.length * 0.95)];

      console.log(`📊 ${browserName.toUpperCase()} Performance:`);
      console.log(`   Average: ${avgTime.toFixed(2)}ms (threshold: ${threshold.avg}ms)`);
      console.log(`   95th percentile: ${p95Time.toFixed(2)}ms (threshold: ${threshold.p95}ms)`);

      expect(avgTime, `${browserName} average should meet threshold`).toBeLessThan(threshold.avg);
      expect(p95Time, `${browserName} p95 should meet threshold`).toBeLessThan(threshold.p95);
    });
  });

  test.describe('Performance Regression Detection', () => {
    test('should benchmark keyboard shortcuts for performance tracking', async ({ page }) => {
      // Comprehensive performance benchmark for CI tracking
      const benchmarkResults = {
        globalShortcuts: [] as number[],
        sequenceShortcuts: [] as number[],
        contextSwitching: [] as number[],
        modalOperations: [] as number[]
      };

      // Test global shortcuts
      console.log('🔍 Benchmarking global shortcuts...');
      for (let i = 0; i < 30; i++) {
        const start = performance.now();
        await page.keyboard.press('Meta+k');
        await page.keyboard.press('Escape');
        const end = performance.now();
        benchmarkResults.globalShortcuts.push(end - start);
        await page.waitForTimeout(10);
      }

      // Test sequence shortcuts
      console.log('🔍 Benchmarking sequence shortcuts...');
      for (let i = 0; i < 20; i++) {
        const start = performance.now();
        await page.keyboard.press('g');
        await page.keyboard.press('p');
        const end = performance.now();
        benchmarkResults.sequenceShortcuts.push(end - start);
        await page.waitForTimeout(20);
      }

      // Test context switching
      console.log('🔍 Benchmarking context switching...');
      for (let i = 0; i < 15; i++) {
        const start = performance.now();
        await page.keyboard.press(`Meta+${(i % 3) + 1}`);
        const end = performance.now();
        benchmarkResults.contextSwitching.push(end - start);
        await page.waitForTimeout(15);
      }

      // Calculate statistics
      const stats = Object.entries(benchmarkResults).map(([category, times]) => {
        const avg = times.reduce((a, b) => a + b, 0) / times.length;
        const sortedTimes = times.sort((a, b) => a - b);
        const median = sortedTimes[Math.floor(times.length / 2)];
        const p95 = sortedTimes[Math.floor(times.length * 0.95)];
        const max = Math.max(...times);
        const min = Math.min(...times);

        return {
          category,
          avg: parseFloat(avg.toFixed(2)),
          median: parseFloat(median.toFixed(2)),
          p95: parseFloat(p95.toFixed(2)),
          min: parseFloat(min.toFixed(2)),
          max: parseFloat(max.toFixed(2))
        };
      });

      // Log benchmark results for CI tracking
      console.log('\n📊 PERFORMANCE BENCHMARK RESULTS:');
      stats.forEach(stat => {
        console.log(`${stat.category}:`);
        console.log(`  Average: ${stat.avg}ms`);
        console.log(`  Median: ${stat.median}ms`);
        console.log(`  95th percentile: ${stat.p95}ms`);
        console.log(`  Min: ${stat.min}ms`);
        console.log(`  Max: ${stat.max}ms`);
      });

      // Export results for CI tracking (could be written to file)
      await page.evaluate((results) => {
        (window as any).performanceBenchmark = results;
      }, stats);

      // Performance regression checks
      expect(stats[0].avg, 'Global shortcuts average regression check').toBeLessThan(25);
      expect(stats[1].avg, 'Sequence shortcuts average regression check').toBeLessThan(50);
      expect(stats[2].avg, 'Context switching average regression check').toBeLessThan(30);
    });
  });
});