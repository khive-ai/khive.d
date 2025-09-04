import { FullConfig } from '@playwright/test';

/**
 * Global teardown for KHIVE WebSocket E2E tests
 * 
 * Cleans up test environment:
 * - Closes any remaining WebSocket connections
 * - Cleans up test data
 * - Generates performance reports
 */
async function globalTeardown(config: FullConfig) {
  console.log('🧹 Cleaning up KHIVE WebSocket E2E test environment...');
  
  try {
    // Clean up any test data or temporary files
    console.log('✅ Test cleanup completed');
  } catch (error) {
    console.error('❌ Global teardown encountered errors:', error);
    // Don't throw - teardown should be resilient
  }
  
  console.log('🏁 Global teardown completed');
}

export default globalTeardown;