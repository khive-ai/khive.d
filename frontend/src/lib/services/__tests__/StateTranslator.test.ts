import { StateTranslator } from '../StateTranslator';
import { CoordinationEvent, OrchestrationSession, Agent } from '@/lib/types/khive';

describe('StateTranslator', () => {
  describe('translateEvent', () => {
    const mockAgent: Agent = {
      id: 'agent_001',
      name: 'Test Agent',
      role: 'analyst',
      status: 'active',
      created_at: new Date().toISOString()
    };

    const mockEvent: CoordinationEvent = {
      id: 'event_001',
      type: 'agent_spawn',
      timestamp: new Date().toISOString(),
      session_id: 'session_001',
      agent_id: 'agent_001',
      message: 'Agent spawned successfully'
    };

    it('translates agent_spawn event to user-friendly language', () => {
      const translated = StateTranslator.translateEvent(mockEvent, [mockAgent]);
      
      expect(translated.title).toBe('Data Analyst joined your team');
      expect(translated.description).toContain('specialist in analyzing patterns');
      expect(translated.type).toBe('milestone');
      expect(translated.severity).toBe('success');
      expect(translated.category).toBe('team');
    });

    it('translates task_start event correctly', () => {
      const taskEvent: CoordinationEvent = {
        ...mockEvent,
        type: 'task_start',
        task_name: 'analyze_project_metrics'
      };

      const translated = StateTranslator.translateEvent(taskEvent, [mockAgent]);
      
      expect(translated.title).toBe('Started: Analyze Project Metrics');
      expect(translated.description).toContain('AI team has begun working');
      expect(translated.type).toBe('progress');
      expect(translated.severity).toBe('info');
    });

    it('translates task_complete event correctly', () => {
      const completeEvent: CoordinationEvent = {
        ...mockEvent,
        type: 'task_complete',
        task_name: 'data_analysis'
      };

      const translated = StateTranslator.translateEvent(completeEvent, [mockAgent]);
      
      expect(translated.title).toBe('Completed: Data Analysis');
      expect(translated.description).toContain('Successfully finished processing');
      expect(translated.type).toBe('completion');
      expect(translated.severity).toBe('success');
      expect(translated.progress?.percentage).toBe(100);
    });

    it('handles events without agent information', () => {
      const translated = StateTranslator.translateEvent(mockEvent, []);
      
      expect(translated.title).toContain('joined your team');
      expect(translated.agent).toBeUndefined();
    });

    it('creates generic event for unknown event types', () => {
      const unknownEvent: CoordinationEvent = {
        ...mockEvent,
        type: 'unknown_event' as any
      };

      const translated = StateTranslator.translateEvent(unknownEvent, [mockAgent]);
      
      expect(translated.title).toBe('System update');
      expect(translated.type).toBe('status');
      expect(translated.severity).toBe('info');
    });
  });

  describe('translateSession', () => {
    const mockSession: OrchestrationSession = {
      sessionId: 'test_session_001',
      status: 'executing',
      created_at: new Date().toISOString(),
      description: 'Test workflow session',
      active_agents: ['agent_001', 'agent_002']
    };

    const mockAgents: Agent[] = [
      {
        id: 'agent_001',
        name: 'Analyst Agent',
        role: 'analyst',
        status: 'active',
        created_at: new Date().toISOString()
      },
      {
        id: 'agent_002', 
        name: 'Architect Agent',
        role: 'architect',
        status: 'active',
        created_at: new Date().toISOString()
      }
    ];

    it('translates session to user-friendly workflow summary', () => {
      const translated = StateTranslator.translateSession(mockSession, mockAgents);
      
      expect(translated.title).toBe('Workflow "TEST_SESSION Project" initiated');
      expect(translated.description).toContain('Started a collaborative workflow with 2 specialized AI agents');
      expect(translated.type).toBe('milestone');
      expect(translated.severity).toBe('info');
      expect(translated.category).toBe('workflow');
    });

    it('handles sessions without agents', () => {
      const translated = StateTranslator.translateSession(mockSession, []);
      
      expect(translated.description).toContain('multiple specialized agents');
      expect(translated.agent).toBeUndefined();
    });
  });

  describe('analyzeIntent', () => {
    it('recognizes analyze intent patterns', () => {
      const intents = StateTranslator.analyzeIntent('analyze my project performance');
      
      expect(intents).toHaveLength(1);
      expect(intents[0].intent).toBe('analyze_project');
      expect(intents[0].category).toBe('analyze');
      expect(intents[0].confidence).toBeGreaterThan(0.5);
    });

    it('recognizes create intent patterns', () => {
      const intents = StateTranslator.analyzeIntent('create a new workflow for data processing');
      
      expect(intents).toHaveLength(1);
      expect(intents[0].intent).toBe('create_workflow');
      expect(intents[0].category).toBe('create');
      expect(intents[0].userFriendlyAction).toContain('Create a new automated workflow');
    });

    it('recognizes monitor intent patterns', () => {
      const intents = StateTranslator.analyzeIntent('monitor system health and status');
      
      expect(intents).toHaveLength(1);
      expect(intents[0].intent).toBe('setup_monitoring');
      expect(intents[0].category).toBe('monitor');
    });

    it('recognizes optimize intent patterns', () => {
      const intents = StateTranslator.analyzeIntent('optimize performance and make it faster');
      
      expect(intents).toHaveLength(1);
      expect(intents[0].intent).toBe('optimize_system');
      expect(intents[0].category).toBe('manage');
    });

    it('recognizes help intent patterns', () => {
      const intents = StateTranslator.analyzeIntent('help me understand what is happening');
      
      expect(intents).toHaveLength(1);
      expect(intents[0].intent).toBe('get_assistance');
      expect(intents[0].category).toBe('help');
    });

    it('handles complex input with multiple intents', () => {
      const intents = StateTranslator.analyzeIntent('analyze my project and help me optimize it');
      
      expect(intents.length).toBeGreaterThan(0);
      expect(intents[0].confidence).toBeGreaterThan(0);
    });

    it('provides estimated time and resources', () => {
      const intents = StateTranslator.analyzeIntent('create new workflow');
      
      expect(intents[0].estimatedTime).toBeTruthy();
      expect(intents[0].requiredResources).toBeTruthy();
      expect(intents[0].requiredResources.length).toBeGreaterThan(0);
    });
  });

  describe('translateSystemStatus', () => {
    const mockDaemonStatus = {
      running: true,
      health: 'healthy' as const,
      uptime: 3600,
      active_sessions: 3,
      total_agents: 5,
      memory_usage: 512,
      cpu_usage: 25
    };

    const mockSessions: OrchestrationSession[] = [
      {
        sessionId: 'session_001',
        status: 'executing',
        created_at: new Date().toISOString()
      },
      {
        sessionId: 'session_002', 
        status: 'completed',
        created_at: new Date().toISOString()
      }
    ];

    const mockAgents: Agent[] = [
      {
        id: 'agent_001',
        role: 'analyst',
        status: 'active',
        created_at: new Date().toISOString()
      }
    ];

    const mockEvents: CoordinationEvent[] = [
      {
        id: 'event_001',
        type: 'task_complete',
        timestamp: new Date().toISOString(),
        session_id: 'session_001'
      }
    ];

    it('translates healthy system status', () => {
      const status = StateTranslator.translateSystemStatus(
        mockDaemonStatus,
        mockSessions,
        mockAgents,
        mockEvents
      );
      
      expect(status.overall).toBe('active');
      expect(status.message).toContain('Working on your projects');
      expect(status.metrics.activeWorkflows).toBe(1);
      expect(status.metrics.teamSize).toBe(1);
    });

    it('translates offline system status', () => {
      const offlineDaemon = { ...mockDaemonStatus, running: false };
      
      const status = StateTranslator.translateSystemStatus(
        offlineDaemon,
        mockSessions,
        mockAgents,
        mockEvents
      );
      
      expect(status.overall).toBe('offline');
      expect(status.message).toBe('System is currently offline');
      expect(status.actionable).toBeTruthy();
    });

    it('detects high activity situations', () => {
      const highActivitySessions = Array(6).fill(null).map((_, i) => ({
        sessionId: `session_${i}`,
        status: 'executing',
        created_at: new Date().toISOString()
      }));
      
      const status = StateTranslator.translateSystemStatus(
        mockDaemonStatus,
        highActivitySessions,
        mockAgents,
        mockEvents
      );
      
      expect(status.overall).toBe('attention');
      expect(status.message).toBe('High activity detected');
      expect(status.actionable).toContain('Consider monitoring progress');
    });

    it('handles ready system state', () => {
      const status = StateTranslator.translateSystemStatus(
        mockDaemonStatus,
        [], // No active sessions
        mockAgents,
        mockEvents
      );
      
      expect(status.overall).toBe('healthy');
      expect(status.message).toBe('System ready for new work');
    });
  });

  describe('helper functions', () => {
    it('humanizes task names correctly', () => {
      // Test private method through public interface
      const event: CoordinationEvent = {
        id: 'test',
        type: 'task_start',
        task_name: 'analyze_performance_metrics',
        timestamp: new Date().toISOString(),
        session_id: 'session_001'
      };

      const translated = StateTranslator.translateEvent(event, []);
      expect(translated.title).toBe('Started: Analyze Performance Metrics');
    });

    it('capitalizes role names correctly', () => {
      const agent: Agent = {
        id: 'agent_001',
        role: 'system_architect',
        status: 'active',
        created_at: new Date().toISOString()
      };

      const event: CoordinationEvent = {
        id: 'test',
        type: 'agent_spawn',
        timestamp: new Date().toISOString(),
        session_id: 'session_001',
        agent_id: 'agent_001'
      };

      const translated = StateTranslator.translateEvent(event, [agent]);
      expect(translated.agent?.role).toBe('System Architect');
    });
  });
});