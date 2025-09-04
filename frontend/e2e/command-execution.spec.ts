import { test, expect, Page } from '@playwright/test';

/**
 * Command Execution Pipeline E2E Tests
 * 
 * Tests comprehensive command execution through WebSocket including:
 * - Command execution through WebSocket
 * - Command response handling and error cases
 * - Concurrent command execution
 * - Command queuing and prioritization
 * - Command history and state management
 * 
 * Performance Targets:
 * - <100ms command response time
 * - >99.5% command success rate
 * - Proper error handling and recovery
 * - Concurrent execution without conflicts
 */

// Helper function to wait for WebSocket connection
async function waitForWebSocketConnection(page: Page, timeout = 10000): Promise<void> {
  await page.waitForFunction(
    () => {
      const indicator = document.querySelector('[data-testid="connection-status"]');
      return indicator && indicator.textContent?.includes('connected');
    },
    { timeout }
  );
}

// Helper to inject command tracking
async function injectCommandTracker(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.commandTracker = {
      executedCommands: [],
      responses: [],
      errors: [],
      timings: new Map(),
      concurrentCommands: 0,
      maxConcurrency: 0
    };
    
    // Track command execution timing
    window.trackCommand = (commandId: string, phase: 'start' | 'response' | 'error' | 'complete') => {
      if (!window.commandTracker.timings.has(commandId)) {
        window.commandTracker.timings.set(commandId, { id: commandId });
      }
      
      const timing = window.commandTracker.timings.get(commandId);
      timing[phase] = performance.now();
      
      if (phase === 'start') {
        window.commandTracker.concurrentCommands++;
        if (window.commandTracker.concurrentCommands > window.commandTracker.maxConcurrency) {
          window.commandTracker.maxConcurrency = window.commandTracker.concurrentCommands;
        }
      } else if (phase === 'complete' || phase === 'error') {
        window.commandTracker.concurrentCommands--;
        if (timing.start && timing.response) {
          timing.responseTime = timing.response - timing.start;
        }
      }
    };
  });
}

test.describe('Command Execution Pipeline', () => {
  test.beforeEach(async ({ page }) => {
    await injectCommandTracker(page);
    await page.goto('/');
    await waitForWebSocketConnection(page, 15000);
  });

  test('should execute simple commands within performance target', async ({ page }) => {
    // Open command palette or command interface
    await page.keyboard.press('Meta+k'); // Trigger command palette
    await page.waitForTimeout(500);
    
    // Check if command input is available
    const commandInputExists = await page.isVisible('[data-testid="command-input"]');
    
    if (commandInputExists) {
      // Execute a simple command
      const testCommand = 'khive daemon status';
      const startTime = performance.now();
      
      await page.fill('[data-testid="command-input"]', testCommand);
      await page.keyboard.press('Enter');
      
      // Wait for command response
      await page.waitForTimeout(2000);
      
      const endTime = performance.now();
      const responseTime = endTime - startTime;
      
      console.log(`Command response time: ${responseTime}ms`);
      
      // Verify performance target
      expect(responseTime).toBeLessThan(2000); // Allow UI overhead
      
      // Check if command was processed
      const commandHistory = await page.isVisible('[data-testid="command-history"]');
      if (commandHistory) {
        const historyItems = await page.locator('[data-testid="command-history-item"]').count();
        expect(historyItems).toBeGreaterThan(0);
      }
    } else {
      // Alternative: Test command execution via direct API
      const result = await page.evaluate(async () => {
        const startTime = performance.now();
        window.trackCommand('test-cmd-1', 'start');
        
        try {
          const response = await fetch('http://localhost:8767/commands/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              command: 'khive daemon status',
              priority: 'normal'
            })
          });
          
          window.trackCommand('test-cmd-1', 'response');
          const data = await response.json();
          window.trackCommand('test-cmd-1', 'complete');
          
          return {
            success: response.ok,
            responseTime: performance.now() - startTime,
            data: data
          };
        } catch (error) {
          window.trackCommand('test-cmd-1', 'error');
          return {
            success: false,
            error: error.message,
            responseTime: performance.now() - startTime
          };
        }
      });
      
      expect(result.success).toBe(true);
      expect(result.responseTime).toBeLessThan(100); // <100ms API response target
      expect(result.data).toBeTruthy();
    }
  });

  test('should handle concurrent command execution', async ({ page }) => {
    const commands = [
      'khive session list',
      'khive agent list', 
      'khive daemon status',
      'khive plan test',
      'khive coordinate status'
    ];
    
    // Execute commands concurrently
    const commandPromises = commands.map(async (command, index) => {
      const commandId = `concurrent-cmd-${index}`;
      
      return await page.evaluate(async (cmd, id) => {
        const startTime = performance.now();
        window.trackCommand(id, 'start');
        
        try {
          const response = await fetch('http://localhost:8767/commands/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              command: cmd,
              priority: 'normal'
            })
          });
          
          window.trackCommand(id, 'response');
          const data = await response.json();
          window.trackCommand(id, 'complete');
          
          return {
            commandId: id,
            command: cmd,
            success: response.ok,
            responseTime: performance.now() - startTime,
            data: data
          };
        } catch (error) {
          window.trackCommand(id, 'error');
          return {
            commandId: id,
            command: cmd,
            success: false,
            error: error.message,
            responseTime: performance.now() - startTime
          };
        }
      }, command, commandId);
    });
    
    // Wait for all commands to complete
    const results = await Promise.all(commandPromises);
    
    // Analyze results
    const successCount = results.filter(r => r.success).length;
    const avgResponseTime = results.reduce((sum, r) => sum + r.responseTime, 0) / results.length;
    const maxResponseTime = Math.max(...results.map(r => r.responseTime));
    
    console.log('Concurrent execution results:', {
      total: results.length,
      successful: successCount,
      avgResponseTime: `${avgResponseTime.toFixed(2)}ms`,
      maxResponseTime: `${maxResponseTime.toFixed(2)}ms`
    });
    
    // Performance and reliability assertions
    expect(successCount / results.length).toBeGreaterThanOrEqual(0.95); // 95% success rate
    expect(avgResponseTime).toBeLessThan(150); // Average within reasonable bounds
    expect(maxResponseTime).toBeLessThan(300); // Max response time reasonable
    
    // Check concurrency tracking
    const concurrencyStats = await page.evaluate(() => ({
      maxConcurrency: window.commandTracker.maxConcurrency,
      totalCommands: window.commandTracker.timings.size
    }));
    
    expect(concurrencyStats.maxConcurrency).toBeGreaterThan(1); // Should have concurrent execution
    expect(concurrencyStats.totalCommands).toBe(commands.length);
  });

  test('should handle command errors gracefully', async ({ page }) => {
    // Test various error scenarios
    const errorCommands = [
      { command: 'invalid-command-xyz', expectedError: true },
      { command: 'khive nonexistent-subcommand', expectedError: true },
      { command: '', expectedError: true },
      { command: 'khive daemon status', expectedError: false } // Valid command for comparison
    ];
    
    const results = [];
    
    for (const testCase of errorCommands) {
      const result = await page.evaluate(async (testCmd) => {
        const startTime = performance.now();
        
        try {
          const response = await fetch('http://localhost:8767/commands/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              command: testCmd.command,
              priority: 'normal'
            })
          });
          
          const data = await response.json();
          
          return {
            command: testCmd.command,
            expectedError: testCmd.expectedError,
            success: response.ok,
            responseTime: performance.now() - startTime,
            data: data,
            statusCode: response.status
          };
        } catch (error) {
          return {
            command: testCmd.command,
            expectedError: testCmd.expectedError,
            success: false,
            error: error.message,
            responseTime: performance.now() - startTime
          };
        }
      }, testCase);
      
      results.push(result);
      await page.waitForTimeout(500); // Brief pause between commands
    }
    
    // Analyze error handling
    results.forEach(result => {
      console.log(`Command: "${result.command}" - Success: ${result.success}, Expected Error: ${result.expectedError}`);
      
      if (result.expectedError) {
        // Commands that should fail
        expect(result.success).toBe(false);
      } else {
        // Commands that should succeed
        expect(result.success).toBe(true);
      }
      
      // All commands should respond within reasonable time
      expect(result.responseTime).toBeLessThan(200);
    });
    
    // Verify connection is still healthy after errors
    const connectionStatus = await page.getByTestId('connection-status').textContent();
    expect(connectionStatus).toContain('connected');
  });

  test('should respect command prioritization', async ({ page }) => {
    // Execute commands with different priorities
    const priorityCommands = [
      { command: 'low-priority-test', priority: 'low' },
      { command: 'high-priority-test', priority: 'high' },
      { command: 'critical-priority-test', priority: 'critical' },
      { command: 'normal-priority-test', priority: 'normal' }
    ];
    
    // Submit all commands rapidly to test priority handling
    const startTime = performance.now();
    const commandPromises = priorityCommands.map(async (cmd, index) => {
      // Add small delay to create submission order
      await new Promise(resolve => setTimeout(resolve, index * 10));
      
      return await page.evaluate(async (cmdData) => {
        const submitTime = performance.now();
        
        const response = await fetch('http://localhost:8767/commands/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            command: cmdData.command,
            priority: cmdData.priority
          })
        });
        
        const responseTime = performance.now() - submitTime;
        const data = await response.json();
        
        return {
          ...cmdData,
          submitTime,
          responseTime,
          success: response.ok,
          data
        };
      }, cmd);
    });
    
    const results = await Promise.all(commandPromises);
    const totalTime = performance.now() - startTime;
    
    console.log('Priority test results:', results.map(r => ({
      command: r.command,
      priority: r.priority,
      responseTime: `${r.responseTime.toFixed(2)}ms`
    })));
    
    // Verify all commands executed successfully
    const successRate = results.filter(r => r.success).length / results.length;
    expect(successRate).toBeGreaterThanOrEqual(0.9); // 90% success rate
    
    // Higher priority commands should generally respond faster
    const criticalResponses = results.filter(r => r.priority === 'critical');
    const lowResponses = results.filter(r => r.priority === 'low');
    
    if (criticalResponses.length > 0 && lowResponses.length > 0) {
      const avgCriticalTime = criticalResponses.reduce((sum, r) => sum + r.responseTime, 0) / criticalResponses.length;
      const avgLowTime = lowResponses.reduce((sum, r) => sum + r.responseTime, 0) / lowResponses.length;
      
      console.log(`Average response times - Critical: ${avgCriticalTime.toFixed(2)}ms, Low: ${avgLowTime.toFixed(2)}ms`);
      
      // Critical should generally be faster (allowing some variance)
      expect(avgCriticalTime).toBeLessThanOrEqual(avgLowTime * 1.5);
    }
  });

  test('should handle command queuing during connection issues', async ({ page }) => {
    // First ensure we have a working connection
    await page.waitForTimeout(2000);
    
    // Simulate connection loss
    await page.evaluate(async () => {
      try {
        await fetch('http://localhost:8767/simulate/error', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ type: 'websocket_disconnect' })
        });
      } catch (error) {
        console.log('Disconnect simulation:', error);
      }
    });
    
    // Wait for disconnection
    await page.waitForTimeout(1000);
    
    // Try to execute commands while disconnected
    const disconnectedCommands = [
      'queued-command-1',
      'queued-command-2',
      'queued-command-3'
    ];
    
    const queuedResults = await Promise.all(
      disconnectedCommands.map(async (command, index) => {
        return await page.evaluate(async (cmd) => {
          const startTime = performance.now();
          
          // This should be queued since WebSocket is down
          const wsService = (window as any).khiveWebSocketService;
          if (wsService && wsService.sendCommand) {
            try {
              const result = await wsService.sendCommand(cmd);
              return {
                command: cmd,
                queued: true,
                responseTime: performance.now() - startTime,
                success: result
              };
            } catch (error) {
              return {
                command: cmd,
                queued: false,
                error: error.message,
                responseTime: performance.now() - startTime
              };
            }
          } else {
            // Fallback to direct API call
            try {
              const response = await fetch('http://localhost:8767/commands/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd, priority: 'normal' })
              });
              
              return {
                command: cmd,
                queued: false,
                success: response.ok,
                responseTime: performance.now() - startTime,
                fallback: true
              };
            } catch (error) {
              return {
                command: cmd,
                queued: false,
                error: error.message,
                responseTime: performance.now() - startTime
              };
            }
          }
        }, command);
      })
    );
    
    console.log('Queued commands results:', queuedResults);
    
    // Wait for reconnection
    await waitForWebSocketConnection(page, 15000);
    
    // Verify system recovered
    const finalConnectionStatus = await page.getByTestId('connection-status').textContent();
    expect(finalConnectionStatus).toContain('connected');
    
    // Commands should have been handled (either queued or executed via fallback)
    queuedResults.forEach(result => {
      expect(result).toBeTruthy();
      expect(result.responseTime).toBeLessThan(5000); // Reasonable timeout
    });
  });

  test('should maintain command history and state', async ({ page }) => {
    // Execute several commands to build history
    const historyCommands = [
      'khive daemon status',
      'khive session list',
      'khive agent compose researcher -d real-time-systems'
    ];
    
    for (const command of historyCommands) {
      await page.evaluate(async (cmd) => {
        try {
          const response = await fetch('http://localhost:8767/commands/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd, priority: 'normal' })
          });
          
          return await response.json();
        } catch (error) {
          console.error('Command execution error:', error);
          return null;
        }
      }, command);
      
      await page.waitForTimeout(500);
    }
    
    // Check if command history is maintained in UI
    const hasCommandHistory = await page.isVisible('[data-testid="command-history"]');
    
    if (hasCommandHistory) {
      const historyItems = await page.locator('[data-testid="command-history-item"]').count();
      expect(historyItems).toBeGreaterThan(0);
      
      // Check history content
      const historyContent = await page.evaluate(() => {
        const items = Array.from(document.querySelectorAll('[data-testid="command-history-item"]'));
        return items.map(item => ({
          command: item.querySelector('[data-testid="command-text"]')?.textContent,
          timestamp: item.querySelector('[data-testid="command-timestamp"]')?.textContent,
          status: item.querySelector('[data-testid="command-status"]')?.textContent
        }));
      });
      
      expect(historyContent.length).toBeGreaterThan(0);
      historyContent.forEach(item => {
        expect(item.command).toBeTruthy();
        expect(item.timestamp).toBeTruthy();
      });
    }
    
    // Test command state persistence across page refresh
    await page.reload();
    await waitForWebSocketConnection(page, 15000);
    
    // Verify connection and basic functionality after reload
    const connectionStatus = await page.getByTestId('connection-status').textContent();
    expect(connectionStatus).toContain('connected');
  });

  test('should handle complex command workflows', async ({ page }) => {
    // Test a complex multi-step workflow
    const workflow = [
      { step: 1, command: 'khive plan "Test WebSocket integration"', waitTime: 1000 },
      { step: 2, command: 'khive coordinate status', waitTime: 500 },
      { step: 3, command: 'khive session list', waitTime: 500 },
      { step: 4, command: 'khive daemon status', waitTime: 500 }
    ];
    
    const workflowResults = [];
    
    for (const workflowStep of workflow) {
      const startTime = performance.now();
      
      const result = await page.evaluate(async (step) => {
        try {
          const response = await fetch('http://localhost:8767/commands/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              command: step.command,
              priority: 'normal'
            })
          });
          
          const data = await response.json();
          
          return {
            step: step.step,
            command: step.command,
            success: response.ok,
            data: data,
            statusCode: response.status
          };
        } catch (error) {
          return {
            step: step.step,
            command: step.command,
            success: false,
            error: error.message
          };
        }
      }, workflowStep);
      
      result.responseTime = performance.now() - startTime;
      workflowResults.push(result);
      
      console.log(`Step ${workflowStep.step}: ${result.success ? 'SUCCESS' : 'FAILED'} (${result.responseTime.toFixed(2)}ms)`);
      
      await page.waitForTimeout(workflowStep.waitTime);
    }
    
    // Analyze workflow execution
    const successfulSteps = workflowResults.filter(r => r.success).length;
    const totalResponseTime = workflowResults.reduce((sum, r) => sum + r.responseTime, 0);
    const avgStepTime = totalResponseTime / workflowResults.length;
    
    console.log('Workflow summary:', {
      totalSteps: workflow.length,
      successful: successfulSteps,
      totalTime: `${totalResponseTime.toFixed(2)}ms`,
      avgStepTime: `${avgStepTime.toFixed(2)}ms`
    });
    
    // Workflow should complete successfully
    expect(successfulSteps / workflow.length).toBeGreaterThanOrEqual(0.9); // 90% success
    expect(avgStepTime).toBeLessThan(200); // Average step time reasonable
    
    // Connection should remain healthy throughout
    const finalStatus = await page.getByTestId('connection-status').textContent();
    expect(finalStatus).toContain('connected');
  });
});

// Global type declarations for command tracking
declare global {
  interface Window {
    commandTracker: {
      executedCommands: any[];
      responses: any[];
      errors: any[];
      timings: Map<string, any>;
      concurrentCommands: number;
      maxConcurrency: number;
    };
    trackCommand: (commandId: string, phase: 'start' | 'response' | 'error' | 'complete') => void;
  }
}