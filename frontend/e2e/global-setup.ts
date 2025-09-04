import { chromium, FullConfig } from '@playwright/test';

/**
 * Global setup for KHIVE E2E tests
 * Handles WebSocket mock server setup and other global dependencies
 */
async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting KHIVE E2E Test Setup');
  
  const baseURL = config.webServer?.url || 'http://localhost:3000';
  
  // Start mock WebSocket server for KHIVE integration testing
  await startMockWebSocketServer();
  
  // Ensure Next.js dev server is ready
  await waitForServer(baseURL, 120000); // 2 minutes timeout
  
  // Pre-warm browser for faster test execution
  await prewarmBrowser();
  
  console.log('✅ KHIVE E2E Test Setup Complete');
}

/**
 * Start mock WebSocket server for KHIVE agent communication
 */
async function startMockWebSocketServer(): Promise<void> {
  console.log('🔌 Starting KHIVE WebSocket Mock Server on port 8000');
  
  try {
    // Create a simple WebSocket mock server
    const mockServerScript = `
      const WebSocket = require('ws');
      const server = new WebSocket.Server({ port: 8000 });
      
      console.log('KHIVE Mock WebSocket Server started on port 8000');
      
      server.on('connection', (ws) => {
        console.log('Client connected to KHIVE mock server');
        
        // Send mock agent status updates
        const sendMockStatus = () => {
          ws.send(JSON.stringify({
            type: 'agent_status',
            data: {
              id: 'mock-agent-001',
              status: 'active',
              task: 'Processing mock orchestration',
              timestamp: Date.now()
            }
          }));
        };
        
        // Mock orchestration events
        const sendMockOrchestration = () => {
          ws.send(JSON.stringify({
            type: 'orchestration_event',
            data: {
              phase: 'planning',
              agents: ['researcher_001', 'architect_001'],
              status: 'active',
              timestamp: Date.now()
            }
          }));
        };
        
        // Send initial status
        setTimeout(sendMockStatus, 1000);
        setTimeout(sendMockOrchestration, 2000);
        
        // Handle incoming messages
        ws.on('message', (message) => {
          console.log('Received:', message.toString());
          
          // Echo back with mock response
          ws.send(JSON.stringify({
            type: 'response',
            data: { 
              success: true, 
              message: 'Mock server response',
              timestamp: Date.now()
            }
          }));
        });
        
        ws.on('close', () => {
          console.log('Client disconnected from KHIVE mock server');
        });
      });
      
      // Keep the server alive
      process.stdin.resume();
    `;
    
    // Write and execute the mock server
    require('fs').writeFileSync('/tmp/khive-mock-ws-server.js', mockServerScript);
    
    // Start the server in background
    const { spawn } = require('child_process');
    const mockServer = spawn('node', ['/tmp/khive-mock-ws-server.js'], {
      detached: true,
      stdio: 'ignore'
    });
    
    mockServer.unref();
    
    // Store PID for cleanup
    require('fs').writeFileSync('/tmp/khive-mock-ws-server.pid', mockServer.pid.toString());
    
    // Wait a moment for server to start
    await new Promise(resolve => setTimeout(resolve, 2000));
    
  } catch (error) {
    console.warn('⚠️  Failed to start KHIVE mock WebSocket server:', error);
  }
}

/**
 * Wait for a server to be ready
 */
async function waitForServer(url: string, timeout: number): Promise<void> {
  console.log(`⏳ Waiting for server at ${url}...`);
  
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(url);
      if (response.ok || response.status === 404) {
        console.log(`✅ Server ready at ${url}`);
        return;
      }
    } catch (error) {
      // Server not ready yet, continue waiting
    }
    
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  throw new Error(`Server at ${url} did not become ready within ${timeout}ms`);
}

/**
 * Pre-warm browser for faster test execution
 */
async function prewarmBrowser(): Promise<void> {
  console.log('🔥 Pre-warming browser...');
  
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Load a simple page to warm up the browser
  await page.goto('about:blank');
  
  await browser.close();
  console.log('✅ Browser pre-warmed');
}

export default globalSetup;