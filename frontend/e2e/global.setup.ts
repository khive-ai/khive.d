import { chromium, FullConfig } from '@playwright/test';
import { writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

/**
 * Global E2E Test Setup for Performance Monitoring
 * 
 * Ensures proper environment initialization for Ocean's performance requirements
 */

const RESULTS_DIR = join(process.cwd(), 'test-results');
const BASELINE_DIR = join(RESULTS_DIR, 'performance-baselines');

async function globalSetup(config: FullConfig) {
  console.log('🚀 Initializing Performance Testing Environment...');
  
  // Ensure required directories exist
  [RESULTS_DIR, BASELINE_DIR].forEach(dir => {
    if (!existsSync(dir)) {
      mkdirSync(dir, { recursive: true });
      console.log(`Created directory: ${dir}`);
    }
  });

  // Validate test environment
  const testEnvironment = {
    ci: !!process.env.CI,
    nodeVersion: process.version,
    platform: process.platform,
    arch: process.arch,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    timestamp: new Date().toISOString(),
  };

  console.log('Test Environment:', testEnvironment);

  // Browser warming and capability detection
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  
  const page = await context.newPage();

  try {
    // Test basic application accessibility
    console.log('Validating application availability...');
    const baseURL = config.projects[0]?.use?.baseURL || 'http://127.0.0.1:3000';
    
    await page.goto(baseURL, { waitUntil: 'networkidle', timeout: 30000 });
    
    // Validate core elements exist
    const requiredElements = [
      '[data-testid="command-center"]',
      'body',
      'html',
    ];

    for (const selector of requiredElements) {
      const element = await page.locator(selector).first();
      if (!await element.isVisible()) {
        throw new Error(`Required element not found or visible: ${selector}`);
      }
    }

    // Test performance monitoring capabilities
    console.log('Testing performance monitoring capabilities...');
    const performanceCapabilities = await page.evaluate(() => {
      return {
        performanceMemory: !!(performance as any).memory,
        performanceNow: !!performance.now,
        performanceMark: !!performance.mark,
        performanceMeasure: !!performance.measure,
        requestAnimationFrame: !!window.requestAnimationFrame,
        webSocket: !!window.WebSocket,
        eventTarget: !!window.EventTarget,
        getBoundingClientRect: !!document.createElement('div').getBoundingClientRect,
      };
    });

    console.log('Performance Capabilities:', performanceCapabilities);

    // Verify essential performance monitoring features
    const missingCapabilities = Object.entries(performanceCapabilities)
      .filter(([_, available]) => !available)
      .map(([name, _]) => name);

    if (missingCapabilities.length > 0) {
      console.warn('⚠️ Missing performance monitoring capabilities:', missingCapabilities);
    }

    // Initialize performance baseline files if they don't exist
    const baselineTemplate = {
      CLI_RESPONSE: { target: 80, max: 100, unit: 'ms' },
      CONTEXT_SWITCHING: { target: 30, max: 50, unit: 'ms' },
      MEMORY_USAGE: { target: 75, max: 100, unit: 'MB' },
      WEBSOCKET_LATENCY: { target: 150, max: 200, unit: 'ms' },
      UI_RESPONSIVENESS: { target: 16, max: 32, unit: 'ms' },
    };

    const envSuffix = testEnvironment.ci ? 'ci' : 'local';
    
    for (const [category, config] of Object.entries(baselineTemplate)) {
      const baselineFile = join(BASELINE_DIR, `baseline-${category}-${envSuffix}.json`);
      
      if (!existsSync(baselineFile)) {
        const initialBaseline = {
          category,
          baseline: config.target * 1.2, // Start with 20% above target
          target: config.target,
          max: config.max,
          unit: config.unit,
          description: `Performance baseline for ${category.toLowerCase().replace('_', ' ')}`,
          establishedAt: Date.now(),
          environment: envSuffix,
          sampleSize: 0,
          confidence: 0.0,
          status: 'INITIAL',
        };
        
        writeFileSync(baselineFile, JSON.stringify(initialBaseline, null, 2));
        console.log(`Created initial baseline: ${baselineFile}`);
      }
    }

    // Save environment info for test runs
    const envInfoFile = join(RESULTS_DIR, 'test-environment.json');
    writeFileSync(envInfoFile, JSON.stringify({
      ...testEnvironment,
      performanceCapabilities,
      baseURL,
      setupTimestamp: Date.now(),
    }, null, 2));

    console.log('✅ Performance testing environment initialized successfully');

  } catch (error) {
    console.error('❌ Failed to initialize performance testing environment:', error);
    throw error;
  } finally {
    await context.close();
    await browser.close();
  }

  // Performance test execution strategy based on environment
  const performanceStrategy = {
    local: {
      iterations: 3,
      warmupCycles: 1,
      measurementDelay: 100,
      enableVerboseLogging: true,
    },
    ci: {
      iterations: 2,
      warmupCycles: 1,
      measurementDelay: 200,
      enableVerboseLogging: false,
    },
  };

  const strategy = testEnvironment.ci ? performanceStrategy.ci : performanceStrategy.local;
  
  const strategyFile = join(RESULTS_DIR, 'performance-strategy.json');
  writeFileSync(strategyFile, JSON.stringify(strategy, null, 2));
  
  console.log(`Performance testing strategy: ${JSON.stringify(strategy)}`);
  console.log(`Strategy saved: ${strategyFile}`);
}

export default globalSetup;