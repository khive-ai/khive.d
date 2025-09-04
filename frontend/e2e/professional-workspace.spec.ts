import { test, expect } from '@playwright/test';

// Configure for actual running server
test.use({ baseURL: 'http://localhost:3005' });

test.describe('KHIVE Professional Workspace - Ocean Demo', () => {
  
  test('Professional workspace loads without modals or conversational interfaces', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Verify no 404 errors
    await expect(page.locator('text=404')).not.toBeVisible();
    
    // Verify no conversational modals are visible on load
    await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    await expect(page.locator('text=AI Assistant')).not.toBeVisible();
    await expect(page.locator("text=Tell me what you'd like to accomplish")).not.toBeVisible();
    
    // Take screenshot for Ocean
    await page.screenshot({ 
      path: 'test-results/professional-workspace-clean.png',
      fullPage: true 
    });
  });

  test('3-panel layout displays correctly', async ({ page }) => {
    await page.goto('/command-center');
    await page.waitForLoadState('networkidle');
    
    // Verify left panel - Session Management
    const leftPanel = page.locator('text=Sessions').first();
    await expect(leftPanel).toBeVisible();
    await expect(page.locator('text=Manage your KHIVE orchestration sessions')).toBeVisible();
    
    // Verify center panel - Main Work Area  
    const centerPanel = page.locator('text=KHIVE Orchestration Workspace');
    await expect(centerPanel).toBeVisible();
    await expect(page.locator('text=Select a session to view orchestration details')).toBeVisible();
    
    // Verify right panel - Action Controls
    const rightPanel = page.locator('text=Actions').first();
    await expect(rightPanel).toBeVisible();
    await expect(page.locator('text=Direct access to KHIVE commands')).toBeVisible();
    
    // Take screenshot showing all 3 panels
    await page.screenshot({ 
      path: 'test-results/3-panel-layout.png',
      fullPage: true 
    });
  });

  test('Direct action buttons are visible and clickable', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Verify primary action buttons exist and are clickable
    const planButton = page.locator('button', { hasText: 'Plan Orchestration' });
    await expect(planButton).toBeVisible();
    await expect(planButton).toBeEnabled();
    
    const composeButton = page.locator('button', { hasText: 'Compose Agent' });
    await expect(composeButton).toBeVisible();
    await expect(composeButton).toBeEnabled();
    
    const coordinateButton = page.locator('button', { hasText: 'Coordinate' });
    await expect(coordinateButton).toBeVisible();
    await expect(coordinateButton).toBeEnabled();
    
    const monitorButton = page.locator('button', { hasText: 'Monitor Sessions' });
    await expect(monitorButton).toBeVisible();
    await expect(monitorButton).toBeEnabled();
    
    // Test clicking the plan button (should not open modals)
    await planButton.click();
    await page.waitForTimeout(500);
    
    // Verify no modal dialogs opened
    await expect(page.locator('[role="dialog"]')).not.toBeVisible();
    
    // Take screenshot showing clicked state
    await page.screenshot({ 
      path: 'test-results/direct-actions-working.png',
      fullPage: true 
    });
  });

  test('Session list displays with professional styling', async ({ page }) => {
    await page.goto('/command-center');
    await page.waitForLoadState('networkidle');
    
    // Verify session list items are visible
    await expect(page.locator('text=Project Analysis')).toBeVisible();
    await expect(page.locator('text=System Architecture Review')).toBeVisible();
    await expect(page.locator('text=Performance Optimization')).toBeVisible();
    
    // Verify status chips are displayed
    await expect(page.locator('text=Running')).toBeVisible();
    await expect(page.locator('text=Completed')).toBeVisible();
    await expect(page.locator('text=Pending')).toBeVisible();
    
    // Verify agent counts and metadata
    await expect(page.locator('text=3 agents')).toBeVisible();
    await expect(page.locator('text=5 agents')).toBeVisible();
    
    // Take screenshot of session list
    await page.screenshot({ 
      path: 'test-results/session-list-professional.png',
      fullPage: true 
    });
  });

  test('Session selection updates main work area', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Initially should show "No Session Selected"
    await expect(page.locator('text=No Session Selected')).toBeVisible();
    
    // Click on a session
    await page.locator('text=Project Analysis').click();
    await page.waitForTimeout(500);
    
    // Verify main area updates
    await expect(page.locator('text=Session Details')).toBeVisible();
    await expect(page.locator('text=Orchestration session content will be displayed here')).toBeVisible();
    
    // Take screenshot of selected session
    await page.screenshot({ 
      path: 'test-results/session-selected.png',
      fullPage: true 
    });
  });

  test('System status displays connection information', async ({ page }) => {
    await page.goto('/command-center');
    await page.waitForLoadState('networkidle');
    
    // Verify system status information is displayed
    await expect(page.locator('text=KHIVE Daemon:')).toBeVisible();
    await expect(page.locator('text=Connection Status')).toBeVisible();
    await expect(page.locator('text=Active Sessions:')).toBeVisible();
    await expect(page.locator('text=Total Agents:')).toBeVisible();
    
    // Take screenshot of status area
    await page.screenshot({ 
      path: 'test-results/system-status.png',
      fullPage: true 
    });
  });

  test("Professional design matches Ocean's document app style", async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Verify clean, professional styling
    const workspace = page.locator('body');
    
    // Should have clean layout without overwhelming elements
    await expect(workspace).toBeVisible();
    
    // Should not have conversational chat bubbles or messaging interfaces
    await expect(page.locator('.message-bubble')).not.toBeVisible();
    await expect(page.locator('.chat-interface')).not.toBeVisible();
    await expect(page.locator('[data-testid="conversation"]')).not.toBeVisible();
    
    // Should have professional typography and spacing  
    await expect(page.locator('h6:has-text("Sessions")')).toHaveCSS('font-weight', '600');
    
    // Take final professional design screenshot
    await page.screenshot({ 
      path: 'test-results/professional-design-final.png',
      fullPage: true 
    });
  });

  test('Mobile responsive design works correctly', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // On mobile, panels should adapt appropriately
    await expect(page.locator('body')).toBeVisible();
    
    // Take mobile screenshot
    await page.screenshot({ 
      path: 'test-results/mobile-professional.png',
      fullPage: true 
    });
    
    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Desktop should show all panels clearly
    await expect(page.locator('h6:has-text("Sessions")')).toBeVisible();
    await expect(page.locator('h6:has-text("Actions")')).toBeVisible();
    
    // Take desktop screenshot
    await page.screenshot({ 
      path: 'test-results/desktop-professional.png',
      fullPage: true 
    });
  });

  test("Performance meets Ocean's requirements", async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/command-center');
    await page.waitForLoadState('domcontentloaded');
    
    const loadTime = Date.now() - startTime;
    console.log(`Professional workspace load time: ${loadTime}ms`);
    
    // Test interaction responsiveness
    const buttonStartTime = Date.now();
    await page.locator('text=Project Analysis').click();
    await page.waitForTimeout(100);
    const buttonTime = Date.now() - buttonStartTime;
    
    console.log(`Button interaction time: ${buttonTime}ms`);
    
    // Ocean's targets - interactions should be fast
    expect(buttonTime).toBeLessThan(500);
    expect(loadTime).toBeLessThan(5000);
  });
});