import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Vim-Style Navigation Sequences
 * Tests Ocean's multi-key navigation shortcuts inspired by vim
 * 
 * Performance Requirements:
 * - Chord sequences: <500ms sequence timeout
 * - Recognition time: <25ms for sequence completion
 * - Timing consistency: ±10ms variance between sequences
 */

test.describe('Vim-Style Navigation Sequences', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the command center
    await page.goto('/');
    
    // Wait for the application to be fully loaded
    await page.waitForSelector('[data-testid="command-center"]', {
      state: 'visible',
      timeout: 10000
    });

    // Ensure keyboard system is ready and no modifiers are pressed
    await page.keyboard.up('Meta');
    await page.keyboard.up('Control');
    await page.keyboard.up('Shift');
    await page.keyboard.up('Alt');
    
    await page.waitForTimeout(500);
  });

  test.describe('Basic Navigation Sequences', () => {
    test('should navigate to planning with "g p" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'g' then 'p' in sequence
      await page.keyboard.press('g');
      await page.keyboard.press('p');

      // Verify workspace switched to planning view
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'planning', { timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "g p" sequence completed in ${responseTime}ms`);
    });

    test('should navigate to monitoring with "g m" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'g' then 'm' in sequence
      await page.keyboard.press('g');
      await page.keyboard.press('m');

      // Verify workspace switched to monitoring view
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'monitoring', { timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "g m" sequence completed in ${responseTime}ms`);
    });

    test('should navigate to agents with "g a" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'g' then 'a' in sequence
      await page.keyboard.press('g');
      await page.keyboard.press('a');

      // Verify workspace switched to agents view
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'agents', { timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "g a" sequence completed in ${responseTime}ms`);
    });

    test('should navigate to analytics with "g n" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'g' then 'n' in sequence
      await page.keyboard.press('g');
      await page.keyboard.press('n');

      // Verify workspace switched to analytics view
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'analytics', { timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "g n" sequence completed in ${responseTime}ms`);
    });

    test('should navigate to settings with "g s" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'g' then 's' in sequence
      await page.keyboard.press('g');
      await page.keyboard.press('s');

      // Verify workspace switched to settings view
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'settings', { timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "g s" sequence completed in ${responseTime}ms`);
    });
  });

  test.describe('Advanced Agent Operations', () => {
    test('should spawn agent with "a s" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'a' then 's' for agent spawn
      await page.keyboard.press('a');
      await page.keyboard.press('s');

      // Look for agent spawn dialog or indication
      const agentSpawn = page.getByRole('dialog', { name: /spawn agent/i }).or(
        page.getByText(/new agent/i)
      );
      await expect(agentSpawn).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "a s" (agent spawn) completed in ${responseTime}ms`);
    });

    test('should show agent metrics with "a m" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'a' then 'm' for agent metrics
      await page.keyboard.press('a');
      await page.keyboard.press('m');

      // Look for agent metrics display
      const metricsView = page.getByText(/agent metrics/i).or(
        page.getByText(/performance/i)
      );
      await expect(metricsView).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "a m" (agent metrics) completed in ${responseTime}ms`);
    });

    test('should show agent logs with "a l" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'a' then 'l' for agent logs
      await page.keyboard.press('a');
      await page.keyboard.press('l');

      // Look for logs view
      const logsView = page.getByText(/logs/i).or(
        page.getByText(/activity/i)
      );
      await expect(logsView).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "a l" (agent logs) completed in ${responseTime}ms`);
    });
  });

  test.describe('File Operations Sequences', () => {
    test('should find files with "f f" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'f' then 'f' for file finder
      await page.keyboard.press('f');
      await page.keyboard.press('f');

      // Look for file finder dialog
      const fileFinder = page.getByRole('dialog', { name: /find files/i }).or(
        page.getByPlaceholder(/search files/i)
      );
      await expect(fileFinder).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "f f" (file finder) completed in ${responseTime}ms`);
    });

    test('should show file locks with "f l" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'f' then 'l' for file locks
      await page.keyboard.press('f');
      await page.keyboard.press('l');

      // Look for file locks display
      const fileLocks = page.getByText(/file locks/i).or(
        page.getByText(/locked files/i)
      );
      await expect(fileLocks).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "f l" (file locks) completed in ${responseTime}ms`);
    });

    test('should show file conflicts with "f c" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 'f' then 'c' for file conflicts
      await page.keyboard.press('f');
      await page.keyboard.press('c');

      // Look for conflicts view
      const conflicts = page.getByText(/conflicts/i).or(
        page.getByText(/file conflicts/i)
      );
      await expect(conflicts).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "f c" (file conflicts) completed in ${responseTime}ms`);
    });
  });

  test.describe('System Operations Sequences', () => {
    test('should show system status with "s s" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 's' then 's' for system status
      await page.keyboard.press('s');
      await page.keyboard.press('s');

      // Look for system status display
      const systemStatus = page.getByText(/system status/i).or(
        page.getByText(/health/i)
      );
      await expect(systemStatus).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "s s" (system status) completed in ${responseTime}ms`);
    });

    test('should show system metrics with "s m" sequence', async ({ page }) => {
      const sequenceStart = Date.now();

      // Press 's' then 'm' for system metrics
      await page.keyboard.press('s');
      await page.keyboard.press('m');

      // Look for metrics display
      const metrics = page.getByText(/system metrics/i).or(
        page.getByText(/performance metrics/i)
      );
      await expect(metrics).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - sequenceStart;
      expect(responseTime).toBeLessThan(100);
      console.log(`⚡ "s m" (system metrics) completed in ${responseTime}ms`);
    });
  });

  test.describe('Sequence Timing and Behavior', () => {
    test('should timeout incomplete sequences after 1.5 seconds', async ({ page }) => {
      // Press 'g' but don't complete the sequence
      await page.keyboard.press('g');

      // Wait for timeout (1500ms + buffer)
      await page.waitForTimeout(1600);

      // Now press 'p' - should not trigger "g p" navigation
      const beforePress = await page.getByTestId('workspace').getAttribute('data-active-view');
      
      await page.keyboard.press('p');
      await page.waitForTimeout(200);

      const afterPress = await page.getByTestId('workspace').getAttribute('data-active-view');
      
      // Active view should not have changed due to timed-out sequence
      expect(afterPress).toBe(beforePress);
      console.log('✅ Sequence timeout working correctly');
    });

    test('should reset sequence on modifier key press', async ({ page }) => {
      // Start a sequence
      await page.keyboard.press('g');

      // Press a modifier key (should reset sequence)
      await page.keyboard.press('Meta+k');

      // Command palette should open (modifier shortcut should work)
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 1000 });

      // Close dialog
      await page.keyboard.press('Escape');

      // Now complete the 'g p' sequence - should work normally
      await page.keyboard.press('g');
      await page.keyboard.press('p');

      // Should navigate to planning
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'planning', { timeout: 1000 });
      
      console.log('✅ Modifier key sequence reset working correctly');
    });

    test('should handle rapid sequence execution', async ({ page }) => {
      const sequences = [
        { keys: ['g', 'p'], expected: 'planning' },
        { keys: ['g', 'm'], expected: 'monitoring' },
        { keys: ['g', 'a'], expected: 'agents' },
        { keys: ['g', 'n'], expected: 'analytics' },
      ];

      const responseTimes: number[] = [];

      for (const sequence of sequences) {
        const startTime = Date.now();

        // Execute sequence
        for (const key of sequence.keys) {
          await page.keyboard.press(key);
        }

        // Verify result
        const workspace = page.getByTestId('workspace');
        await expect(workspace).toHaveAttribute('data-active-view', sequence.expected, { timeout: 1000 });

        const responseTime = Date.now() - startTime;
        responseTimes.push(responseTime);

        // Brief pause between sequences
        await page.waitForTimeout(100);
      }

      // Analyze performance
      const avgTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
      const maxTime = Math.max(...responseTimes);

      console.log(`📊 Rapid sequence performance:`);
      console.log(`   Average: ${avgTime.toFixed(1)}ms`);
      console.log(`   Max: ${maxTime}ms`);

      expect(avgTime).toBeLessThan(75);
      expect(maxTime).toBeLessThan(150);
    });

    test('should prevent sequence conflicts with regular typing', async ({ page }) => {
      // Open command palette to get input field
      await page.keyboard.press('Meta+k');
      const searchInput = page.getByPlaceholder(/search commands/i);
      await expect(searchInput).toBeVisible();
      await searchInput.click();

      // Type a sequence that would normally trigger navigation
      await searchInput.type('gp');

      // Verify input contains the text and no navigation occurred
      await expect(searchInput).toHaveValue('gp');
      
      // Close command palette
      await page.keyboard.press('Escape');

      // Verify we're still on the original view (navigation didn't trigger)
      const workspace = page.getByTestId('workspace');
      const currentView = await workspace.getAttribute('data-active-view');
      expect(currentView).not.toBe('planning'); // Assuming we didn't start on planning
      
      console.log('✅ Input field sequence isolation working correctly');
    });

    test('should handle overlapping sequences gracefully', async ({ page }) => {
      const startTime = Date.now();

      // Start multiple sequences rapidly (simulate user confusion/rapid typing)
      await page.keyboard.press('g');
      await page.keyboard.press('a'); // This should complete 'g a' -> agents
      await page.keyboard.press('g'); // Start new sequence
      await page.keyboard.press('p'); // This should complete 'g p' -> planning

      // The last complete sequence should win
      const workspace = page.getByTestId('workspace');
      await expect(workspace).toHaveAttribute('data-active-view', 'planning', { timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(200);
      console.log(`⚡ Overlapping sequences handled in ${responseTime}ms`);
    });
  });

  test.describe('Context-Sensitive Sequences', () => {
    test('should work differently based on focused pane', async ({ page }) => {
      // Focus orchestration pane first
      await page.keyboard.press('Meta+1');
      await expect(page.getByTestId('orchestration-tree')).toHaveAttribute('data-focused', 'true');

      // Use 'c' shortcut in orchestration context (should compose agent)
      const startTime = Date.now();
      await page.keyboard.press('c');

      // Should trigger compose agent command
      const agentCompose = page.getByText(/compose agent/i).or(
        page.getByText(/khive compose/i)
      );
      await expect(agentCompose).toBeVisible({ timeout: 1000 });

      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Context-sensitive 'c' completed in ${responseTime}ms`);
    });

    test('should handle workspace-focused sequences', async ({ page }) => {
      // Focus workspace pane
      await page.keyboard.press('Meta+2');
      await expect(page.getByTestId('workspace')).toHaveAttribute('data-focused', 'true');

      // Use Enter to toggle workspace focus mode
      const startTime = Date.now();
      await page.keyboard.press('Enter');

      // Should toggle focus mode (implementation specific)
      await page.waitForTimeout(200);
      
      const responseTime = Date.now() - startTime;
      expect(responseTime).toBeLessThan(50);
      console.log(`⚡ Workspace focus toggle completed in ${responseTime}ms`);
    });
  });

  test.describe('Performance Consistency', () => {
    test('should maintain consistent timing across all sequence types', async ({ page }) => {
      const testSequences = [
        ['g', 'p'], ['g', 'm'], ['g', 'a'], ['g', 'n'], ['g', 's'],
        ['a', 's'], ['a', 'l'], ['a', 'm'],
        ['f', 'f'], ['f', 'l'], ['f', 'c'],
        ['s', 's'], ['s', 'm']
      ];

      const timings: { sequence: string; time: number }[] = [];

      for (const sequence of testSequences) {
        const startTime = Date.now();

        // Execute sequence
        for (const key of sequence) {
          await page.keyboard.press(key);
        }

        // Wait for some response (any visible change)
        await page.waitForTimeout(100);

        const responseTime = Date.now() - startTime;
        timings.push({
          sequence: sequence.join(' '),
          time: responseTime
        });

        // Brief pause between tests
        await page.waitForTimeout(50);
      }

      // Analyze consistency
      const times = timings.map(t => t.time);
      const avgTime = times.reduce((a, b) => a + b, 0) / times.length;
      const variance = times.reduce((acc, time) => acc + Math.pow(time - avgTime, 2), 0) / times.length;
      const stdDev = Math.sqrt(variance);

      console.log('📊 Sequence timing analysis:');
      timings.forEach(({ sequence, time }) => {
        console.log(`   "${sequence}": ${time}ms`);
      });
      console.log(`   Average: ${avgTime.toFixed(1)}ms`);
      console.log(`   Std Dev: ${stdDev.toFixed(1)}ms`);

      // Performance expectations
      expect(avgTime).toBeLessThan(150);
      expect(stdDev).toBeLessThan(50); // Consistent timing
      expect(times.filter(t => t > 200).length).toBe(0); // No outliers over 200ms
    });
  });
});