import { Page, CDPSession } from '@playwright/test';

/**
 * Performance Monitoring Utilities for KHIVE E2E Tests
 * Tracks CLI responsiveness, WebSocket performance, and UI rendering metrics
 */
export class PerformanceMonitor {
  private page: Page;
  private cdpSession: CDPSession | null = null;
  private metrics: PerformanceMetrics = {};
  private isMonitoring: boolean = false;
  private startTime: number = 0;
  
  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Start performance monitoring
   */
  async startMonitoring(): Promise<void> {
    if (this.isMonitoring) return;
    
    console.log('🔍 Starting performance monitoring');
    
    this.isMonitoring = true;
    this.startTime = Date.now();
    this.metrics = {};
    
    // Enable CDP for detailed metrics
    try {
      this.cdpSession = await this.page.context().newCDPSession(this.page);
      await this.cdpSession.send('Performance.enable');
      await this.cdpSession.send('Runtime.enable');
    } catch (error) {
      console.warn('⚠️  CDP session not available, using basic metrics only');
    }
    
    // Start measuring Core Web Vitals
    await this.setupWebVitalsTracking();
    
    // Start measuring custom KHIVE metrics
    await this.setupKhiveMetrics();
  }

  /**
   * Stop performance monitoring and collect final metrics
   */
  async stopMonitoring(): Promise<PerformanceMetrics> {
    if (!this.isMonitoring) return this.metrics;
    
    console.log('📊 Stopping performance monitoring and collecting metrics');
    
    this.isMonitoring = false;
    
    // Collect final metrics
    await this.collectFinalMetrics();
    
    // Cleanup CDP session
    if (this.cdpSession) {
      try {
        await this.cdpSession.detach();
      } catch (error) {
        console.warn('⚠️  Error detaching CDP session:', error);
      }
      this.cdpSession = null;
    }
    
    // Calculate total monitoring duration
    this.metrics.totalDuration = Date.now() - this.startTime;
    
    console.log('✅ Performance monitoring complete');
    console.log('📈 Metrics summary:', this.getMetricsSummary());
    
    return this.metrics;
  }

  /**
   * Measure command palette responsiveness
   */
  async measureCommandPaletteResponse(): Promise<number> {
    console.log('⏱️  Measuring command palette response time');
    
    const startTime = performance.now();
    
    // Trigger command palette
    await this.page.keyboard.press('Meta+KeyK');
    
    // Wait for command palette to appear
    await this.page.waitForSelector('[data-testid="command-palette"]', {
      state: 'visible',
      timeout: 5000
    });
    
    const responseTime = performance.now() - startTime;
    this.metrics.commandPaletteResponse = responseTime;
    
    console.log(`⚡ Command Palette Response: ${responseTime.toFixed(2)}ms`);
    return responseTime;
  }

  /**
   * Measure WebSocket connection and message latency
   */
  async measureWebSocketLatency(): Promise<WebSocketMetrics> {
    console.log('📡 Measuring WebSocket performance');
    
    const metrics: WebSocketMetrics = {
      connectionTime: 0,
      messageLatency: 0,
      throughput: 0
    };
    
    // Measure connection time
    const connectionStart = performance.now();
    
    // Listen for WebSocket connection events
    await this.page.evaluate(() => {
      return new Promise<void>((resolve) => {
        const ws = new WebSocket('ws://localhost:8000');
        
        ws.onopen = () => {
          (window as any).testWebSocket = ws;
          resolve();
        };
        
        ws.onerror = () => {
          resolve(); // Resolve even on error for test continuity
        };
      });
    });
    
    metrics.connectionTime = performance.now() - connectionStart;
    
    // Measure message latency
    const messageStart = performance.now();
    
    await this.page.evaluate(() => {
      return new Promise<void>((resolve) => {
        const ws = (window as any).testWebSocket;
        if (ws && ws.readyState === WebSocket.OPEN) {
          const testMessage = { type: 'ping', timestamp: Date.now() };
          
          ws.onmessage = (event: MessageEvent) => {
            try {
              const response = JSON.parse(event.data);
              if (response.type === 'pong') {
                resolve();
              }
            } catch (error) {
              resolve();
            }
          };
          
          ws.send(JSON.stringify(testMessage));
        } else {
          resolve();
        }
      });
    });
    
    metrics.messageLatency = performance.now() - messageStart;
    
    this.metrics.webSocket = metrics;
    
    console.log(`📡 WebSocket Connection: ${metrics.connectionTime.toFixed(2)}ms`);
    console.log(`📡 WebSocket Message Latency: ${metrics.messageLatency.toFixed(2)}ms`);
    
    return metrics;
  }

  /**
   * Measure orchestration tree rendering performance
   */
  async measureOrchestrationTreeRendering(): Promise<number> {
    console.log('🌳 Measuring orchestration tree rendering');
    
    const startTime = performance.now();
    
    // Navigate to orchestration page if not already there
    await this.page.goto('/orchestration');
    
    // Wait for orchestration tree to fully render
    await this.page.waitForSelector('[data-testid="orchestration-tree"]', {
      state: 'visible',
      timeout: 10000
    });
    
    // Wait for all agent nodes to load
    await this.page.waitForFunction(
      () => document.querySelectorAll('[data-testid="agent-node"]').length > 0,
      {},
      { timeout: 5000 }
    );
    
    const renderTime = performance.now() - startTime;
    this.metrics.orchestrationTreeRender = renderTime;
    
    console.log(`🌳 Orchestration Tree Render: ${renderTime.toFixed(2)}ms`);
    return renderTime;
  }

  /**
   * Measure CLI command execution time
   */
  async measureCLICommandExecution(command: string): Promise<number> {
    console.log(`⌨️  Measuring CLI command execution: ${command}`);
    
    const startTime = performance.now();
    
    // Open command palette
    await this.page.keyboard.press('Meta+KeyK');
    await this.page.waitForSelector('[data-testid="command-palette"]');
    
    // Enter command
    await this.page.fill('[data-testid="command-input"]', command);
    await this.page.keyboard.press('Enter');
    
    // Wait for command completion indicator
    await this.page.waitForSelector('[data-testid="command-completed"]', {
      timeout: 30000 // CLI commands can take longer
    });
    
    const executionTime = performance.now() - startTime;
    
    if (!this.metrics.cliCommands) {
      this.metrics.cliCommands = {};
    }
    this.metrics.cliCommands[command] = executionTime;
    
    console.log(`⌨️  CLI Command "${command}": ${executionTime.toFixed(2)}ms`);
    return executionTime;
  }

  /**
   * Set up Core Web Vitals tracking
   */
  private async setupWebVitalsTracking(): Promise<void> {
    await this.page.addInitScript(() => {
      // Track Largest Contentful Paint (LCP)
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        (window as any).webVitals = (window as any).webVitals || {};
        (window as any).webVitals.lcp = lastEntry.startTime;
      }).observe({ entryTypes: ['largest-contentful-paint'] });
      
      // Track First Input Delay (FID)
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry: any) => {
          (window as any).webVitals = (window as any).webVitals || {};
          (window as any).webVitals.fid = entry.processingStart - entry.startTime;
        });
      }).observe({ entryTypes: ['first-input'] });
      
      // Track Cumulative Layout Shift (CLS)
      let clsValue = 0;
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry: any) => {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
          }
        });
        (window as any).webVitals = (window as any).webVitals || {};
        (window as any).webVitals.cls = clsValue;
      }).observe({ entryTypes: ['layout-shift'] });
    });
  }

  /**
   * Set up KHIVE-specific metrics tracking
   */
  private async setupKhiveMetrics(): Promise<void> {
    await this.page.addInitScript(() => {
      (window as any).khiveMetrics = {
        agentResponseTimes: [],
        orchestrationEvents: [],
        commandExecutions: [],
        
        // Track agent response times
        trackAgentResponse: (agentId: string, responseTime: number) => {
          (window as any).khiveMetrics.agentResponseTimes.push({
            agentId,
            responseTime,
            timestamp: Date.now()
          });
        },
        
        // Track orchestration events
        trackOrchestrationEvent: (event: string, duration: number) => {
          (window as any).khiveMetrics.orchestrationEvents.push({
            event,
            duration,
            timestamp: Date.now()
          });
        },
        
        // Track command executions
        trackCommandExecution: (command: string, duration: number) => {
          (window as any).khiveMetrics.commandExecutions.push({
            command,
            duration,
            timestamp: Date.now()
          });
        }
      };
    });
  }

  /**
   * Collect final performance metrics
   */
  private async collectFinalMetrics(): Promise<void> {
    // Collect Web Vitals
    const webVitals = await this.page.evaluate(() => (window as any).webVitals);
    if (webVitals) {
      this.metrics.webVitals = webVitals;
    }
    
    // Collect KHIVE metrics
    const khiveMetrics = await this.page.evaluate(() => (window as any).khiveMetrics);
    if (khiveMetrics) {
      this.metrics.khiveSpecific = khiveMetrics;
    }
    
    // Collect navigation timing
    const navigationTiming = await this.page.evaluate(() => {
      const timing = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: timing.domContentLoadedEventEnd - timing.domContentLoadedEventStart,
        load: timing.loadEventEnd - timing.loadEventStart,
        domComplete: timing.domComplete - timing.navigationStart,
        firstPaint: timing.domContentLoadedEventEnd - timing.navigationStart
      };
    });
    
    this.metrics.navigation = navigationTiming;
    
    // Collect memory usage if available
    try {
      const memoryInfo = await this.page.evaluate(() => {
        const memory = (performance as any).memory;
        return memory ? {
          usedJSHeapSize: memory.usedJSHeapSize,
          totalJSHeapSize: memory.totalJSHeapSize,
          jsHeapSizeLimit: memory.jsHeapSizeLimit
        } : null;
      });
      
      if (memoryInfo) {
        this.metrics.memory = memoryInfo;
      }
    } catch (error) {
      // Memory info not available in this browser
    }
  }

  /**
   * Get performance metrics summary
   */
  getMetricsSummary(): PerformanceMetrics {
    return { ...this.metrics };
  }

  /**
   * Generate performance report
   */
  generateReport(): string {
    const report = ['# KHIVE E2E Performance Report\n'];
    
    report.push(`**Total Monitoring Duration:** ${this.metrics.totalDuration}ms\n`);
    
    if (this.metrics.webVitals) {
      report.push('## Core Web Vitals');
      report.push(`- **LCP (Largest Contentful Paint):** ${this.metrics.webVitals.lcp?.toFixed(2) || 'N/A'}ms`);
      report.push(`- **FID (First Input Delay):** ${this.metrics.webVitals.fid?.toFixed(2) || 'N/A'}ms`);
      report.push(`- **CLS (Cumulative Layout Shift):** ${this.metrics.webVitals.cls?.toFixed(3) || 'N/A'}\n`);
    }
    
    if (this.metrics.commandPaletteResponse) {
      report.push('## KHIVE Specific Metrics');
      report.push(`- **Command Palette Response:** ${this.metrics.commandPaletteResponse.toFixed(2)}ms`);
    }
    
    if (this.metrics.webSocket) {
      report.push(`- **WebSocket Connection:** ${this.metrics.webSocket.connectionTime.toFixed(2)}ms`);
      report.push(`- **WebSocket Message Latency:** ${this.metrics.webSocket.messageLatency.toFixed(2)}ms`);
    }
    
    if (this.metrics.orchestrationTreeRender) {
      report.push(`- **Orchestration Tree Render:** ${this.metrics.orchestrationTreeRender.toFixed(2)}ms`);
    }
    
    if (this.metrics.cliCommands) {
      report.push('\n## CLI Command Performance');
      for (const [command, time] of Object.entries(this.metrics.cliCommands)) {
        report.push(`- **${command}:** ${time.toFixed(2)}ms`);
      }
    }
    
    return report.join('\n');
  }

  /**
   * Assess performance against thresholds
   */
  assessPerformance(): PerformanceAssessment {
    const assessment: PerformanceAssessment = {
      overall: 'good',
      issues: []
    };
    
    // Check Core Web Vitals
    if (this.metrics.webVitals?.lcp && this.metrics.webVitals.lcp > 2500) {
      assessment.issues.push('LCP exceeds 2.5s threshold');
      assessment.overall = 'needs_improvement';
    }
    
    if (this.metrics.webVitals?.fid && this.metrics.webVitals.fid > 100) {
      assessment.issues.push('FID exceeds 100ms threshold');
      assessment.overall = 'needs_improvement';
    }
    
    if (this.metrics.webVitals?.cls && this.metrics.webVitals.cls > 0.1) {
      assessment.issues.push('CLS exceeds 0.1 threshold');
      assessment.overall = 'needs_improvement';
    }
    
    // Check KHIVE specific metrics
    if (this.metrics.commandPaletteResponse && this.metrics.commandPaletteResponse > 500) {
      assessment.issues.push('Command Palette response time exceeds 500ms');
      assessment.overall = 'needs_improvement';
    }
    
    if (this.metrics.webSocket?.messageLatency && this.metrics.webSocket.messageLatency > 1000) {
      assessment.issues.push('WebSocket message latency exceeds 1000ms');
      assessment.overall = 'needs_improvement';
    }
    
    if (assessment.issues.length > 2) {
      assessment.overall = 'poor';
    }
    
    return assessment;
  }
}

// Type definitions
interface PerformanceMetrics {
  totalDuration?: number;
  commandPaletteResponse?: number;
  orchestrationTreeRender?: number;
  webSocket?: WebSocketMetrics;
  cliCommands?: Record<string, number>;
  webVitals?: {
    lcp?: number;
    fid?: number;
    cls?: number;
  };
  navigation?: {
    domContentLoaded: number;
    load: number;
    domComplete: number;
    firstPaint: number;
  };
  memory?: {
    usedJSHeapSize: number;
    totalJSHeapSize: number;
    jsHeapSizeLimit: number;
  };
  khiveSpecific?: {
    agentResponseTimes: Array<{ agentId: string; responseTime: number; timestamp: number }>;
    orchestrationEvents: Array<{ event: string; duration: number; timestamp: number }>;
    commandExecutions: Array<{ command: string; duration: number; timestamp: number }>;
  };
}

interface WebSocketMetrics {
  connectionTime: number;
  messageLatency: number;
  throughput: number;
}

interface PerformanceAssessment {
  overall: 'good' | 'needs_improvement' | 'poor';
  issues: string[];
}