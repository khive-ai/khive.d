import { chromium, FullConfig } from '@playwright/test';

/**
 * Global setup for KHIVE WebSocket E2E tests
 * 
 * This sets up the test environment including:
 * - Mock backend server verification
 * - WebSocket connection pre-checks
 * - Test data initialization
 */
async function globalSetup(config: FullConfig) {
  console.log('🚀 Setting up KHIVE WebSocket E2E test environment...');

  try {
    // Launch a browser to verify the frontend can start
    const browser = await chromium.launch();
    const page = await browser.newPage();
    
    // Wait for the dev server to be ready
    const maxAttempts = 30;
    let attempts = 0;
    let frontendReady = false;
    
    while (attempts < maxAttempts && !frontendReady) {
      try {
        await page.goto('http://localhost:3000', { 
          waitUntil: 'networkidle',
          timeout: 5000 
        });
        frontendReady = true;
        console.log('✅ Frontend server is ready');
      } catch (error) {
        attempts++;
        console.log(`⏳ Waiting for frontend server... (${attempts}/${maxAttempts})`);
        await page.waitForTimeout(2000);
      }
    }

    if (!frontendReady) {
      throw new Error('Frontend server failed to start');
    }

    // Verify mock WebSocket server is ready
    let wsServerReady = false;
    attempts = 0;
    
    while (attempts < 15 && !wsServerReady) {
      try {
        // Try to connect to the mock WebSocket server
        const wsResponse = await page.evaluate(() => {
          return new Promise((resolve, reject) => {
            const ws = new WebSocket('ws://localhost:8767');
            const timeout = setTimeout(() => {
              ws.close();
              reject(new Error('WebSocket connection timeout'));
            }, 3000);
            
            ws.onopen = () => {
              clearTimeout(timeout);
              ws.close();
              resolve(true);
            };
            
            ws.onerror = (error) => {
              clearTimeout(timeout);
              reject(error);
            };
          });
        });
        
        if (wsResponse) {
          wsServerReady = true;
          console.log('✅ Mock WebSocket server is ready');
        }
      } catch (error) {
        attempts++;
        console.log(`⏳ Waiting for WebSocket server... (${attempts}/15)`);
        await page.waitForTimeout(2000);
      }
    }

    if (!wsServerReady) {
      console.warn('⚠️  Mock WebSocket server may not be ready - some tests may fail');
    }

    await browser.close();
    
    console.log('✅ Global setup completed successfully');
    return true;
    
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  }
}

export default globalSetup;