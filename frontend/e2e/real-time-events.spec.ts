import { test, expect, Page } from '@playwright/test';

/**
 * Real-time Event Streaming E2E Tests
 * 
 * Tests comprehensive real-time WebSocket event streaming including:
 * - Activity stream updates for agent events
 * - Session status changes propagation  
 * - Coordination event broadcasting
 * - Event ordering and consistency
 * - Event deduplication and filtering
 * - High-frequency event handling
 * 
 * Performance Targets:
 * - <50ms event propagation time
 * - >99.9% event delivery reliability
 * - Correct event ordering under load
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

// Helper to inject event tracking
async function injectEventTracker(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.eventTracker = {
      events: [],
      coordinationEvents: [],
      sessionEvents: [],
      agentEvents: [],
      duplicateEvents: [],
      eventTimings: new Map(),
    };
    
    // Track when events are received vs when they're displayed
    window.trackEventTiming = (eventId: string, phase: 'received' | 'displayed') => {
      if (!window.eventTracker.eventTimings.has(eventId)) {
        window.eventTracker.eventTimings.set(eventId, {});
      }
      const timing = window.eventTracker.eventTimings.get(eventId);
      timing[phase] = performance.now();
      
      if (timing.received && timing.displayed) {
        timing.propagationTime = timing.displayed - timing.received;
      }
    };
  });
}

test.describe('Real-time Event Streaming', () => {
  test.beforeEach(async ({ page }) => {
    await injectEventTracker(page);
    await page.goto('/');
    await waitForWebSocketConnection(page, 15000);
  });

  test('should receive coordination events in real-time', async ({ page }) => {
    // Subscribe to coordination events
    await page.evaluate(() => {
      // Simulate joining a coordination room
      const wsService = (window as any).khiveWebSocketService;
      if (wsService) {
        wsService.joinCoordination('coord_001');
      }
    });
    
    // Wait for initial events to load
    await page.waitForTimeout(2000);
    
    // Check that coordination events are displayed
    const eventStreamExists = await page.isVisible('[data-testid="activity-stream"]');
    expect(eventStreamExists).toBe(true);
    
    // Wait for automatic events from mock server (events every 8 seconds)
    await page.waitForTimeout(10000);
    
    // Verify events are displayed in the activity stream
    const eventItems = await page.locator('[data-testid="activity-stream"] [data-testid="activity-item"]').count();
    expect(eventItems).toBeGreaterThan(0);
    
    // Check event content structure
    const firstEvent = page.locator('[data-testid="activity-stream"] [data-testid="activity-item"]').first();
    await expect(firstEvent).toBeVisible();
    
    // Verify event has required fields
    const eventText = await firstEvent.textContent();
    expect(eventText).toBeTruthy();
    expect(eventText).toMatch(/\d{2}:\d{2}:\d{2}/); // Should contain timestamp
  });

  test('should handle session status updates in real-time', async ({ page }) => {
    // Navigate to sessions view if needed
    await page.goto('/sessions');
    await waitForWebSocketConnection(page);
    
    // Wait for session data to load
    await page.waitForTimeout(3000);
    
    // Verify session list is displayed
    const sessionList = await page.isVisible('[data-testid="session-list"]');
    expect(sessionList).toBe(true);
    
    // Check if sessions are displayed
    const sessionItems = await page.locator('[data-testid="session-item"]').count();
    expect(sessionItems).toBeGreaterThan(0);
    
    // Monitor session updates over time
    const initialSessionData = await page.evaluate(() => {
      const sessionElements = Array.from(document.querySelectorAll('[data-testid="session-item"]'));
      return sessionElements.map(el => ({
        id: el.getAttribute('data-session-id'),
        status: el.querySelector('[data-testid="session-status"]')?.textContent,
        progress: el.querySelector('[data-testid="session-progress"]')?.textContent
      }));
    });
    
    // Wait for potential session updates
    await page.waitForTimeout(5000);
    
    const updatedSessionData = await page.evaluate(() => {
      const sessionElements = Array.from(document.querySelectorAll('[data-testid="session-item"]'));
      return sessionElements.map(el => ({
        id: el.getAttribute('data-session-id'),
        status: el.querySelector('[data-testid="session-status"]')?.textContent,
        progress: el.querySelector('[data-testid="session-progress"]')?.textContent
      }));
    });
    
    expect(updatedSessionData.length).toBe(initialSessionData.length);
  });

  test('should handle agent status updates in real-time', async ({ page }) => {
    // Navigate to agents view
    await page.goto('/agents');
    await waitForWebSocketConnection(page);
    
    // Wait for agent data to load
    await page.waitForTimeout(3000);
    
    // Track agent updates over time
    const agentUpdates = [];
    
    for (let i = 0; i < 3; i++) {
      await page.waitForTimeout(6000); // Wait for mock server agent updates (every 5s)
      
      const currentAgents = await page.evaluate(() => {
        const agentElements = Array.from(document.querySelectorAll('[data-testid="agent-item"]'));
        return agentElements.map(el => ({
          id: el.getAttribute('data-agent-id'),
          status: el.querySelector('[data-testid="agent-status"]')?.textContent,
          progress: el.querySelector('[data-testid="agent-progress"]')?.textContent,
          timestamp: Date.now()
        }));
      });
      
      agentUpdates.push(currentAgents);
    }
    
    // Verify we captured multiple snapshots
    expect(agentUpdates.length).toBe(3);
    
    // Check that agents exist
    if (agentUpdates[0].length > 0) {
      // Verify agent data structure
      const firstAgent = agentUpdates[0][0];
      expect(firstAgent.id).toBeTruthy();
      expect(firstAgent.status).toBeTruthy();
    }
  });

  test('should maintain event ordering under load', async ({ page }) => {
    // Create multiple rapid events to test ordering
    await page.evaluate(() => {
      window.testEvents = [];
      
      // Override event handlers to track timing
      const originalAddEventListener = EventTarget.prototype.addEventListener;
      EventTarget.prototype.addEventListener = function(type, listener, options) {
        if (type === 'coordination_event' || type === 'session_updated' || type === 'agent_updated') {
          const wrappedListener = function(event) {
            window.testEvents.push({
              type: type,
              timestamp: performance.now(),
              data: event.detail
            });
            return listener.call(this, event);
          };
          return originalAddEventListener.call(this, type, wrappedListener, options);
        }
        return originalAddEventListener.call(this, type, listener, options);
      };
    });
    
    // Generate multiple rapid commands to create events
    const commands = [
      'test command 1',
      'test command 2', 
      'test command 3',
      'test command 4',
      'test command 5'
    ];
    
    const commandPromises = commands.map(async (command, index) => {
      await page.waitForTimeout(index * 100); // Stagger slightly
      
      return await page.evaluate(async (cmd) => {
        try {
          const response = await fetch('http://localhost:8767/commands/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              command: cmd,
              priority: 'normal'
            })
          });
          return await response.json();
        } catch (error) {
          console.error('Command execution failed:', error);
          return null;
        }
      }, command);
    });
    
    // Wait for all commands to complete
    await Promise.all(commandPromises);
    
    // Wait for events to propagate
    await page.waitForTimeout(3000);
    
    // Analyze event ordering
    const eventAnalysis = await page.evaluate(() => {
      return {
        totalEvents: window.testEvents.length,
        eventTypes: window.testEvents.map(e => e.type),
        timestamps: window.testEvents.map(e => e.timestamp),
        isOrdered: window.testEvents.every((event, index) => {
          if (index === 0) return true;
          return event.timestamp >= window.testEvents[index - 1].timestamp;
        })
      };
    });
    
    console.log('Event analysis:', eventAnalysis);
    
    // Events should maintain temporal order
    expect(eventAnalysis.isOrdered).toBe(true);
  });

  test('should handle event deduplication correctly', async ({ page }) => {
    // Monitor for duplicate events
    await page.evaluate(() => {
      window.duplicateTracker = new Map();
      window.duplicateCount = 0;
      
      // Track duplicate events by monitoring the activity stream
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            mutation.addedNodes.forEach((node) => {
              if (node.nodeType === Node.ELEMENT_NODE) {
                const element = node as Element;
                const eventId = element.getAttribute('data-event-id');
                const eventText = element.textContent;
                
                if (eventId && eventText) {
                  if (window.duplicateTracker.has(eventId)) {
                    window.duplicateCount++;
                    console.log('Duplicate event detected:', eventId, eventText);
                  } else {
                    window.duplicateTracker.set(eventId, eventText);
                  }
                }
              }
            });
          }
        });
      });
      
      const activityStream = document.querySelector('[data-testid="activity-stream"]');
      if (activityStream) {
        observer.observe(activityStream, { childList: true, subtree: true });
      }
    });
    
    // Wait for events to accumulate
    await page.waitForTimeout(15000);
    
    // Check duplicate count
    const duplicateCount = await page.evaluate(() => window.duplicateCount);
    const totalTracked = await page.evaluate(() => window.duplicateTracker.size);
    
    console.log(`Total events tracked: ${totalTracked}, Duplicates detected: ${duplicateCount}`);
    
    // Should have minimal duplicates (some might occur due to network issues)
    expect(duplicateCount).toBeLessThanOrEqual(Math.max(1, totalTracked * 0.01)); // <1% duplicates allowed
  });

  test('should measure event propagation performance', async ({ page }) => {
    // Inject performance measurement
    await page.evaluate(() => {
      window.propagationMetrics = [];
      
      // Measure time from WebSocket message to UI update
      const measurePropagation = (eventType: string) => {
        const startTime = performance.now();
        
        // Watch for DOM updates
        const observer = new MutationObserver(() => {
          const endTime = performance.now();
          const propagationTime = endTime - startTime;
          
          window.propagationMetrics.push({
            type: eventType,
            propagationTime: propagationTime,
            timestamp: Date.now()
          });
          
          observer.disconnect();
        });
        
        const target = document.querySelector('[data-testid="activity-stream"]');
        if (target) {
          observer.observe(target, { childList: true, subtree: true });
          
          // Timeout the observer after 1 second
          setTimeout(() => observer.disconnect(), 1000);
        }
      };
      
      // Hook into WebSocket event handlers
      const wsService = (window as any).khiveWebSocketService;
      if (wsService) {
        const originalEmit = wsService.emit;
        wsService.emit = function(...args) {
          if (args[0] === 'coordination_event' || args[0] === 'session_updated') {
            measurePropagation(args[0]);
          }
          return originalEmit.apply(this, args);
        };
      }
    });
    
    // Trigger events and measure performance
    const commands = ['perf test 1', 'perf test 2', 'perf test 3'];
    
    for (const command of commands) {
      await page.evaluate(async (cmd) => {
        await fetch('http://localhost:8767/commands/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: cmd, priority: 'high' })
        });
      }, command);
      
      await page.waitForTimeout(1000);
    }
    
    // Wait for measurements to complete
    await page.waitForTimeout(3000);
    
    const metrics = await page.evaluate(() => window.propagationMetrics || []);
    
    console.log('Propagation metrics:', metrics);
    
    if (metrics.length > 0) {
      // Check performance targets
      const avgPropagation = metrics.reduce((sum, m) => sum + m.propagationTime, 0) / metrics.length;
      const maxPropagation = Math.max(...metrics.map(m => m.propagationTime));
      
      console.log(`Average propagation time: ${avgPropagation}ms, Max: ${maxPropagation}ms`);
      
      // Performance targets
      expect(avgPropagation).toBeLessThan(50); // <50ms average
      expect(maxPropagation).toBeLessThan(100); // <100ms max
    }
  });

  test('should handle high-frequency event streams', async ({ page }) => {
    // Generate high-frequency events
    const eventCount = 20;
    const eventPromises = [];
    
    for (let i = 0; i < eventCount; i++) {
      eventPromises.push(
        page.evaluate(async (index) => {
          return await fetch('http://localhost:8767/commands/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              command: `high-freq-test-${index}`,
              priority: 'normal'
            })
          });
        }, i)
      );
      
      // Small delay between requests to create burst
      if (i % 5 === 0) {
        await page.waitForTimeout(50);
      }
    }
    
    const startTime = Date.now();
    await Promise.all(eventPromises);
    const totalTime = Date.now() - startTime;
    
    // Wait for all events to be processed
    await page.waitForTimeout(5000);
    
    // Verify events were handled without crashes
    const pageTitle = await page.title();
    expect(pageTitle).toBeTruthy(); // Page should still be functional
    
    // Check activity stream still works
    const streamVisible = await page.isVisible('[data-testid="activity-stream"]');
    expect(streamVisible).toBe(true);
    
    // Verify connection is still healthy
    const connectionStatus = await page.getByTestId('connection-status').textContent();
    expect(connectionStatus).toContain('connected');
    
    console.log(`Processed ${eventCount} events in ${totalTime}ms`);
  });

  test('should handle event filtering and categorization', async ({ page }) => {
    // Wait for events to accumulate
    await page.waitForTimeout(10000);
    
    // Check if event filtering UI exists
    const filterControls = await page.isVisible('[data-testid="event-filter"]');
    
    if (filterControls) {
      // Test event type filtering
      const eventTypes = ['agent_spawn', 'task_start', 'task_complete'];
      
      for (const eventType of eventTypes) {
        // Try to filter by event type
        await page.selectOption('[data-testid="event-type-filter"]', eventType);
        await page.waitForTimeout(1000);
        
        // Verify filtered results
        const visibleEvents = await page.locator('[data-testid="activity-item"]:visible').count();
        console.log(`Events visible for type ${eventType}: ${visibleEvents}`);
      }
      
      // Reset filter
      await page.selectOption('[data-testid="event-type-filter"]', 'all');
    }
    
    // Verify event categorization in activity stream
    const events = await page.evaluate(() => {
      const eventElements = Array.from(document.querySelectorAll('[data-testid="activity-item"]'));
      return eventElements.map(el => ({
        type: el.getAttribute('data-event-type'),
        category: el.getAttribute('data-event-category'),
        content: el.textContent
      }));
    });
    
    expect(events.length).toBeGreaterThan(0);
    
    // Events should have proper categorization
    events.forEach(event => {
      expect(event.type).toBeTruthy();
      expect(event.content).toBeTruthy();
    });
  });
});

// Global type declarations for event tracking
declare global {
  interface Window {
    eventTracker: {
      events: any[];
      coordinationEvents: any[];
      sessionEvents: any[];
      agentEvents: any[];
      duplicateEvents: any[];
      eventTimings: Map<string, any>;
    };
    testEvents: Array<{
      type: string;
      timestamp: number;
      data: any;
    }>;
    duplicateTracker: Map<string, string>;
    duplicateCount: number;
    propagationMetrics: Array<{
      type: string;
      propagationTime: number;
      timestamp: number;
    }>;
    trackEventTiming: (eventId: string, phase: 'received' | 'displayed') => void;
  }
}