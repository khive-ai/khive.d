#!/usr/bin/env node

/**
 * Mock KHIVE Backend Server for WebSocket E2E Testing
 * 
 * Simulates the real KHIVE backend WebSocket behavior:
 * - Connection management with realistic latency
 * - Event streaming (coordination events, session updates, agent updates)
 * - Command execution pipeline simulation
 * - Error scenarios and connection resilience testing
 */

import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import express from 'express';
import cors from 'cors';
import type { 
  OrchestrationSession, 
  Agent, 
  CoordinationEvent, 
  DaemonStatus 
} from '../../src/lib/types/khive';

const app = express();
const server = createServer(app);

// Configure Socket.IO with CORS for local testing
const io = new SocketIOServer(server, {
  cors: {
    origin: "http://localhost:3000",
    methods: ["GET", "POST"],
    credentials: true
  },
  transports: ['websocket', 'polling']
});

// Enable CORS and JSON parsing for HTTP endpoints
app.use(cors());
app.use(express.json());

// Mock state management
class MockBackendState {
  private sessions: Map<string, OrchestrationSession> = new Map();
  private agents: Map<string, Agent> = new Map();
  private events: CoordinationEvent[] = [];
  private daemonStatus: DaemonStatus;
  private performanceMetrics = {
    connectionLatency: 0,
    messageLatency: 0,
    commandResponseTime: 0,
  };

  constructor() {
    this.daemonStatus = {
      running: true,
      health: 'healthy',
      uptime: Date.now(),
      active_sessions: 0,
      total_agents: 0,
      memory_usage: 45.2,
      cpu_usage: 12.8,
    };
    
    this.initializeMockData();
  }

  private initializeMockData() {
    // Create mock coordination session
    const mockSession: OrchestrationSession = {
      sessionId: 'session_001',
      flowName: 'Test Planning Flow',
      status: 'executing',
      startTime: Date.now() - 30000,
      duration: 30000,
      results: {},
      coordination_id: 'coord_001',
      phase: 2,
      totalPhases: 3,
      pattern: 'P∥',
      priority: 'normal',
      tags: ['test', 'e2e'],
      agents: [],
      dependencies: [],
      metrics: {
        tokensUsed: 1250,
        apiCalls: 8,
        cost: 0.05,
        avgResponseTime: 150,
        successRate: 0.95,
        resourceUtilization: { cpu: 15, memory: 40, network: 25 }
      }
    };

    const mockAgent: Agent = {
      id: 'agent_001',
      role: 'researcher',
      domain: 'real-time-systems',
      priority: 1,
      status: 'working',
      coordination_id: 'coord_001',
      reasoning: 'Testing WebSocket integration patterns',
      sessionId: 'session_001',
      progress: 65,
      currentTask: 'Analyzing real-time event streaming',
      createdAt: Date.now() - 25000,
      lastActivity: Date.now() - 5000,
      metrics: {
        tasksCompleted: 3,
        avgTaskTime: 8500,
        successRate: 1.0,
        tokensUsed: 450,
        cost: 0.02
      }
    };

    this.sessions.set(mockSession.sessionId, mockSession);
    this.agents.set(mockAgent.id, mockAgent);
    this.updateDaemonStatus();
  }

  private updateDaemonStatus() {
    this.daemonStatus.active_sessions = this.sessions.size;
    this.daemonStatus.total_agents = this.agents.size;
    this.daemonStatus.uptime = Date.now() - this.daemonStatus.uptime;
  }

  // Performance tracking methods
  updateLatency(type: 'connection' | 'message' | 'command', latency: number) {
    if (type === 'connection') {
      this.performanceMetrics.connectionLatency = latency;
    } else if (type === 'message') {
      this.performanceMetrics.messageLatency = latency;
    } else if (type === 'command') {
      this.performanceMetrics.commandResponseTime = latency;
    }
  }

  getPerformanceMetrics() {
    return { ...this.performanceMetrics };
  }

  // State management methods
  getSessions(): OrchestrationSession[] {
    return Array.from(this.sessions.values());
  }

  getAgents(): Agent[] {
    return Array.from(this.agents.values());
  }

  getEvents(limit = 100): CoordinationEvent[] {
    return this.events.slice(0, limit);
  }

  getDaemonStatus(): DaemonStatus {
    this.updateDaemonStatus();
    return { ...this.daemonStatus };
  }

  addEvent(event: Omit<CoordinationEvent, 'timestamp'>): CoordinationEvent {
    const fullEvent: CoordinationEvent = {
      ...event,
      timestamp: Date.now(),
    };
    
    this.events.unshift(fullEvent);
    
    // Keep only recent events (last 1000)
    if (this.events.length > 1000) {
      this.events = this.events.slice(0, 1000);
    }
    
    return fullEvent;
  }

  updateSession(sessionId: string, updates: Partial<OrchestrationSession>): OrchestrationSession | null {
    const session = this.sessions.get(sessionId);
    if (!session) return null;
    
    const updatedSession = { ...session, ...updates };
    this.sessions.set(sessionId, updatedSession);
    return updatedSession;
  }

  updateAgent(agentId: string, updates: Partial<Agent>): Agent | null {
    const agent = this.agents.get(agentId);
    if (!agent) return null;
    
    const updatedAgent = { ...agent, ...updates, lastActivity: Date.now() };
    this.agents.set(agentId, updatedAgent);
    return updatedAgent;
  }
}

const mockState = new MockBackendState();

// HTTP endpoints for REST API simulation
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: Date.now() });
});

app.get('/daemon/status', (req, res) => {
  // Simulate API response time (should be <100ms for commands)
  const startTime = Date.now();
  
  setTimeout(() => {
    const responseTime = Date.now() - startTime;
    mockState.updateLatency('command', responseTime);
    
    res.json({
      success: true,
      data: mockState.getDaemonStatus(),
      responseTime,
    });
  }, Math.random() * 50 + 10); // 10-60ms response time
});

app.get('/sessions', (req, res) => {
  const startTime = Date.now();
  
  setTimeout(() => {
    const responseTime = Date.now() - startTime;
    mockState.updateLatency('command', responseTime);
    
    res.json({
      success: true,
      data: mockState.getSessions(),
      responseTime,
    });
  }, Math.random() * 40 + 5); // 5-45ms response time
});

app.post('/commands/execute', (req, res) => {
  const startTime = Date.now();
  const { command, parameters = [], priority = 'normal' } = req.body;
  
  // Simulate command execution time based on complexity
  const baseTime = 20;
  const complexityMultiplier = command.includes('complex') ? 3 : 1;
  const executionTime = baseTime * complexityMultiplier + Math.random() * 30;
  
  setTimeout(() => {
    const responseTime = Date.now() - startTime;
    mockState.updateLatency('command', responseTime);
    
    // Simulate successful execution with occasional failures
    const success = Math.random() > 0.05; // 95% success rate
    
    if (success) {
      // Create a coordination event for the command
      const event = mockState.addEvent({
        type: 'task_start',
        session_id: 'session_001',
        coordination_id: 'coord_001',
        message: `Executed command: ${command}`,
        metadata: { command, parameters, priority, responseTime },
      });
      
      res.json({
        success: true,
        data: {
          commandId: `cmd_${Date.now()}`,
          status: 'completed',
          output: `Command "${command}" executed successfully`,
          executionTime: responseTime,
        },
        responseTime,
      });
      
      // Broadcast the event to connected clients
      io.emit('coordination_event', event);
    } else {
      res.status(500).json({
        success: false,
        error: 'Simulated command execution failure',
        responseTime,
      });
    }
  }, executionTime);
});

// WebSocket connection handling
io.on('connection', (socket) => {
  const connectionStart = Date.now();
  console.log(`WebSocket client connected: ${socket.id}`);
  
  // Track connection latency
  socket.emit('connection_established', { timestamp: connectionStart });

  // Handle ping/pong for latency monitoring
  socket.on('ping', (timestamp: number) => {
    const latency = Date.now() - timestamp;
    mockState.updateLatency('connection', latency);
    
    // Add realistic network latency (10-100ms)
    const networkLatency = Math.random() * 90 + 10;
    setTimeout(() => {
      socket.emit('pong', timestamp);
    }, networkLatency);
  });

  // Coordination room management
  socket.on('join_coordination', (coordinationId: string) => {
    socket.join(`coordination:${coordinationId}`);
    console.log(`Client ${socket.id} joined coordination: ${coordinationId}`);
    
    // Send current coordination events
    const events = mockState.getEvents(50);
    const coordinationEvents = events.filter(e => e.coordination_id === coordinationId);
    coordinationEvents.forEach(event => {
      socket.emit('coordination_event', event);
    });
  });

  socket.on('leave_coordination', (coordinationId: string) => {
    socket.leave(`coordination:${coordinationId}`);
    console.log(`Client ${socket.id} left coordination: ${coordinationId}`);
  });

  // Session subscription management
  socket.on('subscribe_session', (sessionId: string) => {
    socket.join(`session:${sessionId}`);
    console.log(`Client ${socket.id} subscribed to session: ${sessionId}`);
    
    // Send current session state
    const sessions = mockState.getSessions();
    const session = sessions.find(s => s.sessionId === sessionId);
    if (session) {
      socket.emit('session_updated', session);
    }
  });

  socket.on('unsubscribe_session', (sessionId: string) => {
    socket.leave(`session:${sessionId}`);
    console.log(`Client ${socket.id} unsubscribed from session: ${sessionId}`);
  });

  // Handle disconnection
  socket.on('disconnect', (reason) => {
    const connectionDuration = Date.now() - connectionStart;
    console.log(`WebSocket client disconnected: ${socket.id}, reason: ${reason}, duration: ${connectionDuration}ms`);
  });
});

// Simulate periodic events for testing real-time updates
setInterval(() => {
  // Simulate agent status updates
  const agents = mockState.getAgents();
  if (agents.length > 0) {
    const randomAgent = agents[Math.floor(Math.random() * agents.length)];
    const updatedAgent = mockState.updateAgent(randomAgent.id, {
      progress: Math.min(100, randomAgent.progress + Math.random() * 10),
      status: randomAgent.progress >= 100 ? 'completed' : 'working',
    });
    
    if (updatedAgent) {
      io.emit('agent_updated', updatedAgent);
    }
  }
}, 5000); // Update every 5 seconds

setInterval(() => {
  // Simulate coordination events
  const event = mockState.addEvent({
    type: Math.random() > 0.5 ? 'task_complete' : 'task_start',
    session_id: 'session_001',
    coordination_id: 'coord_001',
    agent_id: 'agent_001',
    message: `Automated event at ${new Date().toISOString()}`,
    metadata: { automated: true },
  });
  
  io.to('coordination:coord_001').emit('coordination_event', event);
}, 8000); // New event every 8 seconds

setInterval(() => {
  // Simulate daemon status updates
  const status = mockState.getDaemonStatus();
  status.cpu_usage = 10 + Math.random() * 20;
  status.memory_usage = 40 + Math.random() * 30;
  
  io.emit('daemon_status_updated', status);
}, 10000); // Update every 10 seconds

// Performance metrics endpoint for testing
app.get('/performance', (req, res) => {
  res.json({
    success: true,
    data: mockState.getPerformanceMetrics(),
  });
});

// Error simulation endpoints for testing resilience
app.post('/simulate/error', (req, res) => {
  const { type, duration } = req.body;
  
  if (type === 'websocket_disconnect') {
    // Disconnect all clients to test reconnection
    io.disconnectSockets();
    res.json({ success: true, message: 'Disconnected all WebSocket clients' });
  } else if (type === 'high_latency') {
    // Simulate high latency for a duration
    const originalLatency = 50;
    const highLatency = duration || 5000;
    
    setTimeout(() => {
      // Reset to normal latency
    }, highLatency);
    
    res.json({ success: true, message: `Simulating high latency for ${highLatency}ms` });
  } else {
    res.status(400).json({ success: false, error: 'Unknown error type' });
  }
});

// Start the server
const PORT = process.env.PORT || 8767;
server.listen(PORT, () => {
  console.log(`🚀 Mock KHIVE Backend Server running on port ${PORT}`);
  console.log(`📡 WebSocket server: ws://localhost:${PORT}`);
  console.log(`🌐 HTTP API: http://localhost:${PORT}`);
  console.log(`🎯 Performance targets: <200ms WebSocket latency, <100ms command response`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🛑 Received SIGTERM, shutting down gracefully...');
  server.close(() => {
    console.log('✅ Mock server shut down successfully');
    process.exit(0);
  });
});