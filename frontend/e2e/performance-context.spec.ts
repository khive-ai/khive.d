import { test, expect, Page, BrowserContext } from '@playwright/test';

/**
 * Performance Testing: Context Switching & UI Transitions
 * 
 * OCEAN'S REQUIREMENTS:
 * - Context switches must be <50ms (Cmd+1/2/3 pane switching)
 * - View transitions must be smooth and fast
 * - Visual feedback timing validation
 * - UI responsiveness under rapid switching
 */

// Performance thresholds (ms)
const PERFORMANCE_TARGETS = {
  CONTEXT_SWITCH_MAX: 50,
  CONTEXT_SWITCH_TARGET: 30,
  VIEW_TRANSITION_MAX: 100,
  VISUAL_FEEDBACK_MAX: 16, // 60fps = 16.67ms per frame
  RAPID_SWITCH_DEGRADATION: 1.3, // 30% degradation max
} as const;

// Context switch timing data
interface SwitchTiming {
  from: string;
  to: string;
  duration: number;
  visualFeedbackTime: number;
}

test.describe('Context Switching Performance', () => {
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
    
    // Load app and wait for full initialization
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[data-testid="command-center"]');
    
    // Ensure we start in workspace pane
    await page.keyboard.press('Meta+1');
    await page.waitForSelector('[data-testid="workspace-pane"].active');
  });

  test.afterEach(async () => {
    await page.close();
  });

  test.afterAll(async () => {
    await context.close();
  });

  /**
   * Test: Basic Pane Switching Performance
   * Validates Ocean's <50ms context switching requirement
   */
  test('Pane switching meets <50ms requirement', async () => {
    const switches = [
      { key: 'Meta+1', target: '[data-testid="workspace-pane"]', name: 'workspace' },
      { key: 'Meta+2', target: '[data-testid="agents-pane"]', name: 'agents' },
      { key: 'Meta+3', target: '[data-testid="sessions-pane"]', name: 'sessions' },
      { key: 'Meta+4', target: '[data-testid="metrics-pane"]', name: 'metrics' },
    ];

    const switchTimings: SwitchTiming[] = [];

    for (let i = 0; i < switches.length; i++) {
      const currentSwitch = switches[i];
      const previousSwitch = switches[i - 1] || switches[switches.length - 1];
      
      // Measure context switch timing
      const startTime = performance.now();
      
      // Execute context switch
      await page.keyboard.press(currentSwitch.key);
      
      // Wait for active state change
      await page.waitForSelector(`${currentSwitch.target}.active`);
      
      // Measure visual feedback timing (CSS transition completion)
      const visualFeedbackStart = performance.now();
      await page.waitForFunction(
        (selector) => {
          const element = document.querySelector(selector);
          return element && getComputedStyle(element).opacity === '1';
        },
        currentSwitch.target
      );
      const visualFeedbackTime = performance.now() - visualFeedbackStart;
      
      const totalDuration = performance.now() - startTime;
      
      switchTimings.push({
        from: previousSwitch.name,
        to: currentSwitch.name,
        duration: totalDuration,
        visualFeedbackTime,
      });
      
      console.log(`Switch ${previousSwitch.name} → ${currentSwitch.name}: ${totalDuration.toFixed(2)}ms (visual: ${visualFeedbackTime.toFixed(2)}ms)`);
      
      // Individual switch validation
      expect(totalDuration).toBeLessThan(PERFORMANCE_TARGETS.CONTEXT_SWITCH_MAX);
      expect(visualFeedbackTime).toBeLessThan(PERFORMANCE_TARGETS.VISUAL_FEEDBACK_MAX);
      
      // Small pause to ensure clean measurement
      await page.waitForTimeout(100);
    }

    // Overall performance analysis
    const averageSwitchTime = switchTimings.reduce((sum, timing) => sum + timing.duration, 0) / switchTimings.length;
    const slowestSwitch = switchTimings.reduce((prev, current) => (prev.duration > current.duration) ? prev : current);
    
    console.log('Context Switching Performance Summary:');
    console.log(`Average switch time: ${averageSwitchTime.toFixed(2)}ms`);
    console.log(`Slowest switch: ${slowestSwitch.from} → ${slowestSwitch.to} (${slowestSwitch.duration.toFixed(2)}ms)`);
    
    // Validate average performance meets target
    expect(averageSwitchTime).toBeLessThan(PERFORMANCE_TARGETS.CONTEXT_SWITCH_TARGET);
  });

  /**
   * Test: Rapid Context Switching Performance
   * Tests performance degradation under rapid pane switching
   */
  test('Rapid context switching maintains performance', async () => {
    const rapidSwitches = [
      'Meta+1', 'Meta+2', 'Meta+3', 'Meta+4',
      'Meta+3', 'Meta+2', 'Meta+1', 'Meta+4',
      'Meta+2', 'Meta+3', 'Meta+1', 'Meta+2',
    ];

    const rapidTimings: number[] = [];

    for (const switchKey of rapidSwitches) {
      const startTime = performance.now();
      await page.keyboard.press(switchKey);
      
      // Quick validation that switch occurred (less strict for rapid testing)
      const targetMap: { [key: string]: string } = {
        'Meta+1': '[data-testid="workspace-pane"]',
        'Meta+2': '[data-testid="agents-pane"]',
        'Meta+3': '[data-testid="sessions-pane"]',
        'Meta+4': '[data-testid="metrics-pane"]',
      };
      
      await page.waitForSelector(`${targetMap[switchKey]}.active`, { timeout: 1000 });
      const duration = performance.now() - startTime;
      
      rapidTimings.push(duration);
      
      // Minimal delay for rapid switching
      await page.waitForTimeout(25);
    }

    // Performance degradation analysis
    const firstQuarterAvg = rapidTimings.slice(0, 3).reduce((a, b) => a + b) / 3;
    const lastQuarterAvg = rapidTimings.slice(-3).reduce((a, b) => a + b) / 3;
    const degradationRatio = lastQuarterAvg / firstQuarterAvg;
    
    console.log('Rapid Switching Analysis:');
    console.log(`First 3 switches average: ${firstQuarterAvg.toFixed(2)}ms`);
    console.log(`Last 3 switches average: ${lastQuarterAvg.toFixed(2)}ms`);
    console.log(`Performance degradation: ${((degradationRatio - 1) * 100).toFixed(1)}%`);
    
    // Validate minimal performance degradation
    expect(degradationRatio).toBeLessThan(PERFORMANCE_TARGETS.RAPID_SWITCH_DEGRADATION);
    expect(lastQuarterAvg).toBeLessThan(PERFORMANCE_TARGETS.CONTEXT_SWITCH_MAX);
  });

  /**
   * Test: View Transition Smoothness
   * Validates smooth transitions between different view states
   */
  test('View transitions are smooth and responsive', async () => {
    const viewTransitions = [
      { 
        trigger: () => page.click('[data-testid="expand-agents"]'),
        target: '[data-testid="agents-detail-view"]',
        name: 'agents_expand'
      },
      {
        trigger: () => page.click('[data-testid="collapse-agents"]'),
        target: '[data-testid="agents-summary-view"]',
        name: 'agents_collapse'
      },
      {
        trigger: () => page.keyboard.press('Meta+Shift+f'),
        target: '[data-testid="fullscreen-view"]',
        name: 'fullscreen_toggle'
      },
      {
        trigger: () => page.keyboard.press('Escape'),
        target: '[data-testid="normal-view"]',
        name: 'fullscreen_exit'
      },
    ];

    for (const transition of viewTransitions) {
      const startTime = performance.now();
      
      await transition.trigger();
      await page.waitForSelector(transition.target);
      
      const duration = performance.now() - startTime;
      
      console.log(`View transition "${transition.name}": ${duration.toFixed(2)}ms`);
      
      // View transitions can be slightly slower than context switches
      expect(duration).toBeLessThan(PERFORMANCE_TARGETS.VIEW_TRANSITION_MAX);
      
      await page.waitForTimeout(200); // Allow transition to complete fully
    }
  });

  /**
   * Test: Modal and Overlay Performance
   * Tests performance of modal dialogs and overlays
   */
  test('Modal and overlay transitions are performant', async () => {
    const modalOperations = [
      {
        open: () => page.keyboard.press('Meta+n'),
        close: () => page.keyboard.press('Escape'),
        target: '[data-testid="new-item-modal"]',
        name: 'new_item_modal'
      },
      {
        open: () => page.keyboard.press('Meta+s'),
        close: () => page.keyboard.press('Escape'),  
        target: '[data-testid="settings-modal"]',
        name: 'settings_modal'
      },
      {
        open: () => page.keyboard.press('Meta+h'),
        close: () => page.keyboard.press('Escape'),
        target: '[data-testid="help-modal"]',
        name: 'help_modal'
      },
    ];

    for (const modal of modalOperations) {
      // Test modal opening performance
      const openStartTime = performance.now();
      await modal.open();
      await page.waitForSelector(modal.target);
      const openDuration = performance.now() - openStartTime;
      
      // Test modal closing performance
      const closeStartTime = performance.now();
      await modal.close();
      await page.waitForSelector(modal.target, { state: 'detached' });
      const closeDuration = performance.now() - closeStartTime;
      
      console.log(`Modal "${modal.name}" open: ${openDuration.toFixed(2)}ms, close: ${closeDuration.toFixed(2)}ms`);
      
      // Both operations should be fast
      expect(openDuration).toBeLessThan(PERFORMANCE_TARGETS.CONTEXT_SWITCH_MAX);
      expect(closeDuration).toBeLessThan(PERFORMANCE_TARGETS.CONTEXT_SWITCH_MAX);
      
      await page.waitForTimeout(150);
    }
  });

  /**
   * Test: Keyboard Navigation Performance
   * Tests tab navigation and focus management performance
   */
  test('Keyboard navigation maintains high performance', async () => {
    // Navigate through focusable elements
    const tabSequence = Array(20).fill('Tab');
    const shiftTabSequence = Array(10).fill('Shift+Tab');
    
    const navigationTimings: number[] = [];

    // Forward tab navigation
    for (const key of tabSequence) {
      const startTime = performance.now();
      await page.keyboard.press(key);
      
      // Wait for focus change to be visible
      await page.waitForFunction(() => document.activeElement !== null);
      const duration = performance.now() - startTime;
      
      navigationTimings.push(duration);
      
      // Each tab navigation should be nearly instantaneous
      expect(duration).toBeLessThan(PERFORMANCE_TARGETS.VISUAL_FEEDBACK_MAX);
    }

    // Reverse tab navigation
    for (const key of shiftTabSequence) {
      const startTime = performance.now();
      await page.keyboard.press(key);
      await page.waitForFunction(() => document.activeElement !== null);
      const duration = performance.now() - startTime;
      
      navigationTimings.push(duration);
      expect(duration).toBeLessThan(PERFORMANCE_TARGETS.VISUAL_FEEDBACK_MAX);
    }

    const averageNavigationTime = navigationTimings.reduce((a, b) => a + b) / navigationTimings.length;
    console.log(`Average keyboard navigation time: ${averageNavigationTime.toFixed(2)}ms`);
    
    // Overall navigation should be very fast
    expect(averageNavigationTime).toBeLessThan(10);
  });

  /**
   * Test: Animation Frame Rate
   * Validates that UI animations maintain 60fps during transitions
   */
  test('UI animations maintain 60fps during transitions', async () => {
    // Monitor frame rate during a context switch
    await page.evaluate(() => {
      (window as any).frameTimeData = [];
      let lastTime = performance.now();
      
      function measureFrameRate() {
        const currentTime = performance.now();
        (window as any).frameTimeData.push(currentTime - lastTime);
        lastTime = currentTime;
        
        if ((window as any).frameTimeData.length < 60) { // Monitor for 1 second at 60fps
          requestAnimationFrame(measureFrameRate);
        }
      }
      
      requestAnimationFrame(measureFrameRate);
    });

    // Trigger multiple context switches during monitoring
    await page.keyboard.press('Meta+2');
    await page.waitForTimeout(200);
    await page.keyboard.press('Meta+3');
    await page.waitForTimeout(200);
    await page.keyboard.press('Meta+1');
    await page.waitForTimeout(600); // Allow monitoring to complete

    // Analyze frame timing data
    const frameTimeData = await page.evaluate(() => (window as any).frameTimeData);
    const averageFrameTime = frameTimeData.reduce((a: number, b: number) => a + b, 0) / frameTimeData.length;
    const maxFrameTime = Math.max(...frameTimeData);
    const droppedFrames = frameTimeData.filter((time: number) => time > PERFORMANCE_TARGETS.VISUAL_FEEDBACK_MAX).length;
    
    console.log('Animation Performance Analysis:');
    console.log(`Average frame time: ${averageFrameTime.toFixed(2)}ms`);
    console.log(`Max frame time: ${maxFrameTime.toFixed(2)}ms`);
    console.log(`Dropped frames (>16ms): ${droppedFrames}/${frameTimeData.length}`);
    
    // Validate smooth animation performance
    expect(averageFrameTime).toBeLessThan(PERFORMANCE_TARGETS.VISUAL_FEEDBACK_MAX);
    expect(droppedFrames).toBeLessThan(frameTimeData.length * 0.1); // Less than 10% dropped frames
  });

  /**
   * Test: Focus Management Performance
   * Validates that focus management is performant and consistent
   */
  test('Focus management is performant and accurate', async () => {
    const focusTests = [
      { action: () => page.keyboard.press('Meta+k'), target: '[data-testid="command-input"]' },
      { action: () => page.keyboard.press('Escape'), target: 'body' },
      { action: () => page.click('[data-testid="agent-card"]:first-child'), target: '[data-testid="agent-card"]:first-child' },
      { action: () => page.keyboard.press('Tab'), target: '[data-testid="agent-actions"]:first-child' },
    ];

    for (const focusTest of focusTests) {
      const startTime = performance.now();
      await focusTest.action();
      
      // Wait for focus to be established
      await page.waitForFunction(
        (selector) => {
          const element = document.querySelector(selector);
          return element === document.activeElement || element?.contains(document.activeElement);
        },
        focusTest.target
      );
      
      const duration = performance.now() - startTime;
      console.log(`Focus management: ${duration.toFixed(2)}ms`);
      
      // Focus changes should be instantaneous
      expect(duration).toBeLessThan(PERFORMANCE_TARGETS.VISUAL_FEEDBACK_MAX);
      
      await page.waitForTimeout(100);
    }
  });
});