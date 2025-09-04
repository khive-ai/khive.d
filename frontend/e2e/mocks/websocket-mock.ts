import { EventEmitter } from 'events';
import WebSocket from 'ws';

/**
 * WebSocket Mock Server for KHIVE Agent Communication Testing
 * Simulates the KHIVE orchestration backend for E2E tests
 */
export class KhiveWebSocketMock extends EventEmitter {
  private server: WebSocket.Server | null = null;
  private clients: Set<WebSocket> = new Set();
  private port: number;
  private url: string;
  
  constructor(url: string = 'ws://localhost:8000') {
    super();
    this.url = url;
    this.port = parseInt(url.split(':').pop() || '8000');
  }

  /**
   * Start the mock WebSocket server
   */
  async start(): Promise<void> {
    if (this.server) {
      return; // Already running
    }

    return new Promise((resolve, reject) => {
      try {
        this.server = new WebSocket.Server({ port: this.port });
        
        this.server.on('connection', (ws: WebSocket) => {
          console.log(`[KHIVE Mock] Client connected`);
          this.clients.add(ws);
          
          // Set up client event handlers
          this.setupClientHandlers(ws);
          
          // Send initial connection message
          this.sendToClient(ws, {
            type: 'connection_established',
            data: {
              serverId: 'khive-mock-server',
              timestamp: Date.now(),
              version: '1.0.0'
            }
          });
        });
        
        this.server.on('listening', () => {
          console.log(`[KHIVE Mock] WebSocket server listening on port ${this.port}`);
          resolve();
        });
        
        this.server.on('error', (error) => {
          console.error('[KHIVE Mock] Server error:', error);
          reject(error);
        });
        
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Stop the mock WebSocket server
   */
  async stop(): Promise<void> {
    if (!this.server) {
      return; // Already stopped
    }

    return new Promise((resolve) => {
      // Close all client connections
      this.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
          client.close();
        }
      });
      this.clients.clear();
      
      // Close server
      this.server?.close(() => {
        console.log('[KHIVE Mock] WebSocket server stopped');
        this.server = null;
        resolve();
      });
    });
  }

  /**
   * Send message to all connected clients
   */
  async sendMessage(message: any): Promise<void> {
    const payload = JSON.stringify(message);
    
    this.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(payload);
      }
    });
    
    this.emit('sent', message);
  }

  /**
   * Send message to a specific client
   */
  private sendToClient(client: WebSocket, message: any): void {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(message));
    }
  }

  /**
   * Set up event handlers for a client connection
   */
  private setupClientHandlers(ws: WebSocket): void {
    ws.on('message', (data: WebSocket.Data) => {
      try {
        const message = JSON.parse(data.toString());
        console.log('[KHIVE Mock] Received:', message);
        
        this.emit('message', message);
        
        // Handle specific message types
        this.handleMessage(ws, message);
        
      } catch (error) {
        console.error('[KHIVE Mock] Error parsing message:', error);
      }
    });
    
    ws.on('close', () => {
      console.log('[KHIVE Mock] Client disconnected');
      this.clients.delete(ws);
      this.emit('disconnect');
    });
    
    ws.on('error', (error) => {
      console.error('[KHIVE Mock] Client error:', error);
      this.clients.delete(ws);
    });
  }

  /**
   * Handle incoming messages and generate appropriate responses
   */
  private handleMessage(client: WebSocket, message: any): void {
    switch (message.type) {
      case 'ping':
        this.sendToClient(client, {
          type: 'pong',
          timestamp: Date.now()
        });
        break;
        
      case 'agent_command':
        this.handleAgentCommand(client, message);
        break;
        
      case 'orchestration_request':
        this.handleOrchestrationRequest(client, message);
        break;
        
      case 'status_request':
        this.handleStatusRequest(client, message);
        break;
        
      default:
        // Echo back unknown messages with mock response
        this.sendToClient(client, {
          type: 'response',
          originalType: message.type,
          data: {
            success: true,
            message: 'Mock response generated',
            timestamp: Date.now()
          }
        });
    }
  }

  /**
   * Handle agent command messages
   */
  private handleAgentCommand(client: WebSocket, message: any): void {
    const { command, agentId, parameters } = message.data || {};
    
    // Simulate agent execution
    setTimeout(() => {
      this.sendToClient(client, {
        type: 'agent_response',
        data: {
          id: agentId,
          command,
          status: 'completed',
          result: {
            success: true,
            output: `Mock execution of ${command}`,
            duration: Math.random() * 1000 + 500, // 500-1500ms
          },
          timestamp: Date.now()
        }
      });
    }, Math.random() * 2000 + 1000); // 1-3 second delay
  }

  /**
   * Handle orchestration request messages
   */
  private handleOrchestrationRequest(client: WebSocket, message: any): void {
    const { workflow, agents, parameters } = message.data || {};
    
    // Simulate orchestration planning
    this.sendToClient(client, {
      type: 'orchestration_response',
      data: {
        workflowId: `mock-workflow-${Date.now()}`,
        status: 'planning',
        agents: agents || ['researcher_001', 'architect_001', 'implementer_001'],
        estimatedDuration: Math.random() * 300000 + 60000, // 1-6 minutes
        timestamp: Date.now()
      }
    });
    
    // Simulate workflow progress updates
    const phases = ['planning', 'execution', 'review', 'completed'];
    let currentPhase = 0;
    
    const updateInterval = setInterval(() => {
      if (currentPhase < phases.length - 1) {
        currentPhase++;
        this.sendToClient(client, {
          type: 'orchestration_update',
          data: {
            workflowId: `mock-workflow-${Date.now()}`,
            phase: phases[currentPhase],
            progress: (currentPhase / (phases.length - 1)) * 100,
            timestamp: Date.now()
          }
        });
      } else {
        clearInterval(updateInterval);
      }
    }, 3000); // Update every 3 seconds
  }

  /**
   * Handle status request messages
   */
  private handleStatusRequest(client: WebSocket, message: any): void {
    this.sendToClient(client, {
      type: 'status_response',
      data: {
        server: 'khive-mock-server',
        version: '1.0.0',
        uptime: Date.now() - (this.server as any)?.startTime || 0,
        connections: this.clients.size,
        agents: {
          active: Math.floor(Math.random() * 5) + 1,
          idle: Math.floor(Math.random() * 3),
          total: Math.floor(Math.random() * 8) + 3
        },
        workflows: {
          running: Math.floor(Math.random() * 3),
          queued: Math.floor(Math.random() * 2),
          completed: Math.floor(Math.random() * 10) + 5
        },
        timestamp: Date.now()
      }
    });
  }

  /**
   * Simulate agent status updates (for testing)
   */
  simulateAgentActivity(): void {
    const agents = [
      'researcher_001', 'architect_001', 'implementer_001',
      'reviewer_001', 'tester_001'
    ];
    
    const statuses = ['idle', 'active', 'thinking', 'executing'];
    
    const sendUpdate = () => {
      const agent = agents[Math.floor(Math.random() * agents.length)];
      const status = statuses[Math.floor(Math.random() * statuses.length)];
      
      this.sendMessage({
        type: 'agent_status',
        data: {
          id: agent,
          status,
          task: `Mock task for ${agent}`,
          progress: Math.random() * 100,
          timestamp: Date.now()
        }
      });
    };
    
    // Send periodic updates
    setInterval(sendUpdate, 5000 + Math.random() * 5000); // 5-10 seconds
  }

  /**
   * Get connection information
   */
  getConnectionInfo() {
    return {
      url: this.url,
      port: this.port,
      clientCount: this.clients.size,
      isRunning: !!this.server
    };
  }
}