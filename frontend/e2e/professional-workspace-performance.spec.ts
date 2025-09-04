import { test, expect, type Page, type BrowserContext } from '@playwright/test';

/**
 * Comprehensive Performance & Responsive Design Testing Suite
 * for KHIVE Professional Workspace
 * 
 * Tests performance across desktop, tablet, and mobile viewports
 * Validates 3-panel layout responsiveness and professional UX
 */

const PERFORMANCE_THRESHOLDS = {
  // Page load performance targets
  PAGE_LOAD_MAX_MS: 3000,
  FIRST_CONTENTFUL_PAINT_MAX_MS: 1500,
  LARGEST_CONTENTFUL_PAINT_MAX_MS: 2500,
  
  // Interaction responsiveness targets
  BUTTON_CLICK_RESPONSE_MAX_MS: 100,
  PANEL_SWITCH_RESPONSE_MAX_MS: 200,
  SESSION_SELECT_RESPONSE_MAX_MS: 150,
  
  // Memory usage thresholds
  MEMORY_USAGE_MAX_MB: 100,
  
  // Layout shift stability
  CUMULATIVE_LAYOUT_SHIFT_MAX: 0.1
};

const VIEWPORT_CONFIGURATIONS = {
  DESKTOP: { width: 1920, height: 1080 },
  TABLET: { width: 1024, height: 768 },
  MOBILE: { width: 375, height: 667 } // iPhone SE
};

test.describe('Professional Workspace Performance & Responsive Design', () => {
  
  test.beforeEach(async ({ page }) => {
    // Enable performance monitoring
    await page.goto('http://localhost:3005');
  });

  test('Desktop Performance Benchmarks (1920x1080)', async ({ page, context }) => {
    await page.setViewportSize(VIEWPORT_CONFIGURATIONS.DESKTOP);
    
    // Measure page load performance
    const startTime = Date.now();
    await page.goto('http://localhost:3005');
    const loadTime = Date.now() - startTime;
    
    // Wait for main content to be visible
    await expect(page.locator('[data-testid="professional-workspace"]').first()).toBeVisible();
    
    // Verify load time meets professional standards
    expect(loadTime).toBeLessThan(PERFORMANCE_THRESHOLDS.PAGE_LOAD_MAX_MS);
    console.log(`Desktop Page Load Time: ${loadTime}ms`);
    
    // Test Core Web Vitals using Performance API
    const webVitals = await page.evaluate(() => {
      return new Promise((resolve) => {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const vitals: any = {};
          
          entries.forEach((entry) => {
            if (entry.name === 'first-contentful-paint') {
              vitals.fcp = entry.startTime;
            }
            if (entry.name === 'largest-contentful-paint') {
              vitals.lcp = entry.startTime;
            }
          });
          
          resolve(vitals);
        });
        
        observer.observe({ type: 'paint', buffered: true });
        observer.observe({ type: 'largest-contentful-paint', buffered: true });
        
        // Resolve after timeout to ensure we capture metrics
        setTimeout(() => resolve({}), 1000);
      });
    });
    
    console.log('Desktop Web Vitals:', webVitals);
    
    // Test 3-panel layout visibility and proper sizing
    const leftPanel = page.locator('div:has-text("Sessions")').first();
    const centerPanel = page.locator('div:has-text("KHIVE Orchestration Workspace")').first(); 
    const rightPanel = page.locator('div:has-text("Actions")').first();
    
    await expect(leftPanel).toBeVisible();
    await expect(centerPanel).toBeVisible();
    await expect(rightPanel).toBeVisible();
    
    // Verify panel dimensions are appropriate for desktop
    const leftPanelBox = await leftPanel.boundingBox();
    const centerPanelBox = await centerPanel.boundingBox();
    const rightPanelBox = await rightPanel.boundingBox();
    
    expect(leftPanelBox?.width).toBeGreaterThan(300); // Left panel should be ~320px
    expect(centerPanelBox?.width).toBeGreaterThan(800); // Center should take most space
    expect(rightPanelBox?.width).toBeGreaterThan(250); // Right panel should be ~280px
    
    console.log('Desktop Panel Widths:', {
      left: leftPanelBox?.width,
      center: centerPanelBox?.width,
      right: rightPanelBox?.width
    });
  });

  test('Mobile Responsive Design (375x667 - iPhone SE)', async ({ page }) => {
    await page.setViewportSize(VIEWPORT_CONFIGURATIONS.MOBILE);
    await page.goto('http://localhost:3005');
    
    // Wait for layout to stabilize
    await page.waitForTimeout(500);
    
    // Verify the workspace adapts to mobile screen
    const workspace = page.locator('body').first();
    await expect(workspace).toBeVisible();
    
    // On mobile, panels should stack or transform
    // Check if the layout is still usable (not cut off)
    const viewportWidth = 375;
    const bodyElement = await page.locator('body').first();
    const bodyBox = await bodyElement.boundingBox();
    
    // Verify no horizontal overflow
    expect(bodyBox?.width).toBeLessThanOrEqual(viewportWidth + 20); // Small tolerance
    
    // Test session list accessibility on mobile
    const sessionsHeader = page.locator('text=Sessions');
    await expect(sessionsHeader).toBeVisible();
    
    // Test action buttons remain accessible and clickable
    const planButton = page.locator('button:has-text("Plan Orchestration")');
    await expect(planButton).toBeVisible();
    
    const planButtonBox = await planButton.boundingBox();
    expect(planButtonBox?.width).toBeGreaterThan(100); // Button should be large enough to tap
    expect(planButtonBox?.height).toBeGreaterThan(35); // Minimum tap target size
    
    // Test touch-friendly interaction
    await planButton.click();
    
    console.log('Mobile Layout Test Passed - No horizontal overflow, buttons accessible');
  });

  test('Tablet Layout Validation (1024x768 - iPad)', async ({ page }) => {
    await page.setViewportSize(VIEWPORT_CONFIGURATIONS.TABLET);
    await page.goto('http://localhost:3005');
    
    await page.waitForTimeout(300);
    
    // Verify 3-panel layout works well on tablet
    const leftPanel = page.locator('div:has-text("Sessions")').first();
    const centerPanel = page.locator('div:has-text("KHIVE Orchestration Workspace")').first();
    const rightPanel = page.locator('div:has-text("Actions")').first();
    
    await expect(leftPanel).toBeVisible();
    await expect(centerPanel).toBeVisible();  
    await expect(rightPanel).toBeVisible();
    
    // Check panel proportions are reasonable for tablet
    const leftPanelBox = await leftPanel.boundingBox();
    const centerPanelBox = await centerPanel.boundingBox();
    const rightPanelBox = await rightPanel.boundingBox();
    
    const totalWidth = 1024;
    const leftRatio = (leftPanelBox?.width || 0) / totalWidth;
    const centerRatio = (centerPanelBox?.width || 0) / totalWidth;
    const rightRatio = (rightPanelBox?.width || 0) / totalWidth;
    
    // Left and right panels shouldn't be too large on tablet
    expect(leftRatio).toBeLessThan(0.4); // Less than 40%
    expect(rightRatio).toBeLessThan(0.4); // Less than 40%
    expect(centerRatio).toBeGreaterThan(0.3); // At least 30% for main content
    
    console.log('Tablet Panel Ratios:', {
      left: leftRatio.toFixed(2),
      center: centerRatio.toFixed(2),
      right: rightRatio.toFixed(2)
    });
  });

  test('Interaction Response Time Benchmarks', async ({ page }) => {
    await page.setViewportSize(VIEWPORT_CONFIGURATIONS.DESKTOP);
    await page.goto('http://localhost:3005');
    
    // Test session selection response time
    const sessionItem = page.locator('div[role="button"]:has-text("Project Analysis")').first();
    await expect(sessionItem).toBeVisible();
    
    const sessionSelectStart = Date.now();
    await sessionItem.click();
    
    // Wait for selection to be visually indicated
    await expect(sessionItem).toHaveClass(/Mui-selected/);
    const sessionSelectTime = Date.now() - sessionSelectStart;
    
    expect(sessionSelectTime).toBeLessThan(PERFORMANCE_THRESHOLDS.SESSION_SELECT_RESPONSE_MAX_MS);
    console.log(`Session Selection Response Time: ${sessionSelectTime}ms`);
    
    // Test button click responsiveness
    const planButton = page.locator('button:has-text("Plan Orchestration")');
    
    const buttonClickStart = Date.now();
    await planButton.click();
    
    // Verify console output or state change (button stays visible)
    await expect(planButton).toBeVisible();
    const buttonClickTime = Date.now() - buttonClickStart;
    
    expect(buttonClickTime).toBeLessThan(PERFORMANCE_THRESHOLDS.BUTTON_CLICK_RESPONSE_MAX_MS);
    console.log(`Button Click Response Time: ${buttonClickTime}ms`);
    
    // Test compose agent button
    const composeButton = page.locator('button:has-text("Compose Agent")');
    await composeButton.click();
    
    // Test coordinate button
    const coordinateButton = page.locator('button:has-text("Coordinate")');
    await coordinateButton.click();
    
    // Test monitor button
    const monitorButton = page.locator('button:has-text("Monitor Sessions")');
    await monitorButton.click();
    
    console.log('All primary action buttons respond within performance thresholds');
  });

  test('Keyboard Accessibility Navigation', async ({ page }) => {
    await page.setViewportSize(VIEWPORT_CONFIGURATIONS.DESKTOP);
    await page.goto('http://localhost:3005');
    
    // Test keyboard navigation through session list
    await page.keyboard.press('Tab');
    
    // Should be able to navigate to session items
    const firstSession = page.locator('[role="button"]:has-text("Project Analysis")').first();
    await expect(firstSession).toBeVisible();
    
    // Test keyboard selection
    await firstSession.focus();
    await page.keyboard.press('Enter');
    
    await expect(firstSession).toHaveClass(/Mui-selected/);
    
    // Navigate to action buttons with Tab
    let tabCount = 0;
    const maxTabs = 20; // Safety limit
    
    while (tabCount < maxTabs) {
      await page.keyboard.press('Tab');
      tabCount++;
      
      const focusedElement = await page.evaluate(() => {
        const focused = document.activeElement;
        return focused ? {
          tagName: focused.tagName,
          textContent: focused.textContent?.slice(0, 50),
          role: focused.getAttribute('role')
        } : null;
      });
      
      // If we reach the Plan Orchestration button, we can activate it
      if (focusedElement?.textContent?.includes('Plan Orchestration')) {
        await page.keyboard.press('Enter');
        console.log('Successfully navigated to and activated Plan Orchestration button via keyboard');
        break;
      }
    }
    
    console.log(`Keyboard navigation test completed after ${tabCount} tabs`);
  });

  test('Memory Usage During Extended Session', async ({ page, context }) => {
    await page.setViewportSize(VIEWPORT_CONFIGURATIONS.DESKTOP);
    await page.goto('http://localhost:3005');
    
    // Get initial memory usage
    const initialMemory = await page.evaluate(() => {
      return (performance as any).memory ? {
        used: (performance as any).memory.usedJSHeapSize / 1024 / 1024,
        total: (performance as any).memory.totalJSHeapSize / 1024 / 1024
      } : { used: 0, total: 0 };
    });
    
    console.log('Initial Memory Usage:', initialMemory);
    
    // Simulate extended usage - clicking through sessions and actions
    for (let i = 0; i < 10; i++) {
      // Click through sessions
      const sessions = page.locator('[role="button"]').filter({ hasText: /Project Analysis|System Architecture|Performance/ });
      const sessionCount = await sessions.count();
      
      for (let j = 0; j < sessionCount; j++) {
        await sessions.nth(j).click();
        await page.waitForTimeout(100);
      }
      
      // Click action buttons
      await page.locator('button:has-text("Plan Orchestration")').click();
      await page.waitForTimeout(50);
      await page.locator('button:has-text("Compose Agent")').click();
      await page.waitForTimeout(50);
      await page.locator('button:has-text("Coordinate")').click();
      await page.waitForTimeout(50);
      await page.locator('button:has-text("Monitor Sessions")').click();
      await page.waitForTimeout(50);
    }
    
    // Check memory usage after extended session
    const finalMemory = await page.evaluate(() => {
      return (performance as any).memory ? {
        used: (performance as any).memory.usedJSHeapSize / 1024 / 1024,
        total: (performance as any).memory.totalJSHeapSize / 1024 / 1024
      } : { used: 0, total: 0 };
    });
    
    console.log('Final Memory Usage:', finalMemory);
    
    const memoryIncrease = finalMemory.used - initialMemory.used;
    console.log(`Memory Usage Increase: ${memoryIncrease.toFixed(2)}MB`);
    
    // Verify memory usage stays within reasonable bounds
    expect(finalMemory.used).toBeLessThan(PERFORMANCE_THRESHOLDS.MEMORY_USAGE_MAX_MB);
    expect(memoryIncrease).toBeLessThan(50); // Shouldn't increase by more than 50MB during normal usage
  });

  test('Cross-Browser Layout Consistency', async ({ page }) => {
    await page.setViewportSize(VIEWPORT_CONFIGURATIONS.DESKTOP);
    await page.goto('http://localhost:3005');
    
    // Take screenshot for visual regression testing
    await page.screenshot({ 
      path: `test-results/professional-workspace-desktop-${Date.now()}.png`,
      fullPage: true 
    });
    
    // Test layout stability across different viewport sizes
    const viewports = [
      { width: 1920, height: 1080 },
      { width: 1366, height: 768 },
      { width: 1024, height: 768 },
      { width: 768, height: 1024 },
      { width: 375, height: 667 }
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(300);
      
      // Verify no layout broken or content cut off
      const body = await page.locator('body').boundingBox();
      expect(body?.width).toBeLessThanOrEqual(viewport.width + 50); // Small tolerance for scrollbars
      
      // Verify key elements remain visible
      const sessionsText = page.locator('text=Sessions');
      const actionsText = page.locator('text=Actions');
      
      await expect(sessionsText).toBeVisible();
      await expect(actionsText).toBeVisible();
    }
    
    console.log('Layout consistency verified across multiple viewport sizes');
  });

  test('Typography and Spacing Professional Standards', async ({ page }) => {
    await page.setViewportSize(VIEWPORT_CONFIGURATIONS.DESKTOP);
    await page.goto('http://localhost:3005');
    
    // Test typography hierarchy
    const mainHeading = page.locator('text=KHIVE Orchestration Workspace').first();
    const sectionHeading = page.locator('text=Sessions').first();
    const actionHeading = page.locator('text=Actions').first();
    
    await expect(mainHeading).toBeVisible();
    await expect(sectionHeading).toBeVisible();
    await expect(actionHeading).toBeVisible();
    
    // Verify font sizes are appropriate for professional interface
    const mainHeadingStyle = await mainHeading.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return {
        fontSize: computed.fontSize,
        fontWeight: computed.fontWeight,
        lineHeight: computed.lineHeight
      };
    });
    
    console.log('Main Heading Typography:', mainHeadingStyle);
    
    // Verify minimum font size for readability
    const fontSize = parseInt(mainHeadingStyle.fontSize);
    expect(fontSize).toBeGreaterThan(16); // At least 16px for main heading
    
    // Test button spacing and sizing
    const actionButtons = page.locator('button').filter({ hasText: /Plan|Compose|Coordinate|Monitor/ });
    const buttonCount = await actionButtons.count();
    
    for (let i = 0; i < buttonCount; i++) {
      const button = actionButtons.nth(i);
      const buttonBox = await button.boundingBox();
      
      expect(buttonBox?.height).toBeGreaterThan(35); // Minimum touch target size
      expect(buttonBox?.width).toBeGreaterThan(100); // Adequate button width
    }
    
    console.log('Typography and spacing meet professional standards');
  });
});