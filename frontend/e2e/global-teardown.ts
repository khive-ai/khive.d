import { FullConfig } from '@playwright/test';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs';

const execAsync = promisify(exec);

/**
 * Global teardown for KHIVE E2E tests
 * Cleans up WebSocket mock server and other global resources
 */
async function globalTeardown(_config: FullConfig) {
  console.log('🧹 Starting KHIVE E2E Test Teardown');
  
  // Stop mock WebSocket server
  await stopMockWebSocketServer();
  
  // Clean up temporary files
  await cleanupTempFiles();
  
  // Generate test summary if needed
  await generateTestSummary();
  
  console.log('✅ KHIVE E2E Test Teardown Complete');
}

/**
 * Stop mock WebSocket server
 */
async function stopMockWebSocketServer(): Promise<void> {
  console.log('🛑 Stopping KHIVE Mock WebSocket Server');
  
  try {
    const pidFile = '/tmp/khive-mock-ws-server.pid';
    
    if (fs.existsSync(pidFile)) {
      const pid = fs.readFileSync(pidFile, 'utf8').trim();
      
      try {
        // Try to kill the process
        process.kill(parseInt(pid), 'SIGTERM');
        console.log(`✅ Mock WebSocket server (PID: ${pid}) stopped`);
      } catch (error) {
        // Process might already be dead
        console.log('ℹ️  Mock WebSocket server was already stopped');
      }
      
      // Remove PID file
      fs.unlinkSync(pidFile);
    }
    
    // Also kill any remaining WebSocket servers on port 8000
    try {
      await execAsync('pkill -f "node.*khive-mock-ws-server"');
    } catch (error) {
      // Ignore error if no process found
    }
    
  } catch (error) {
    console.warn('⚠️  Error stopping mock WebSocket server:', error);
  }
}

/**
 * Clean up temporary files
 */
async function cleanupTempFiles(): Promise<void> {
  console.log('🗑️  Cleaning up temporary files');
  
  const tempFiles = [
    '/tmp/khive-mock-ws-server.js',
    '/tmp/khive-mock-ws-server.pid',
  ];
  
  for (const file of tempFiles) {
    try {
      if (fs.existsSync(file)) {
        fs.unlinkSync(file);
        console.log(`✅ Removed ${file}`);
      }
    } catch (error) {
      console.warn(`⚠️  Could not remove ${file}:`, error);
    }
  }
}

/**
 * Generate test summary
 */
async function generateTestSummary(): Promise<void> {
  try {
    const resultsPath = 'test-results/results.json';
    
    if (fs.existsSync(resultsPath)) {
      const results = JSON.parse(fs.readFileSync(resultsPath, 'utf8'));
      
      const summary = {
        timestamp: new Date().toISOString(),
        total: results.stats?.total || 0,
        passed: results.stats?.passed || 0,
        failed: results.stats?.failed || 0,
        skipped: results.stats?.skipped || 0,
        duration: results.stats?.duration || 0,
        projects: results.stats?.projects || [],
      };
      
      console.log('📊 Test Summary:');
      console.log(`   Total: ${summary.total}`);
      console.log(`   Passed: ${summary.passed}`);
      console.log(`   Failed: ${summary.failed}`);
      console.log(`   Skipped: ${summary.skipped}`);
      console.log(`   Duration: ${summary.duration}ms`);
      
      // Write summary to file
      fs.writeFileSync(
        'test-results/summary.json', 
        JSON.stringify(summary, null, 2)
      );
      
    }
  } catch (error) {
    console.warn('⚠️  Could not generate test summary:', error);
  }
}

export default globalTeardown;