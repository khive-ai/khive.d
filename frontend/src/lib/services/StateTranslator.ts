/**
 * StateTranslator Service - Convert System Events to User-Meaningful Language
 * 
 * This service transforms technical system events, states, and data
 * into human-readable, user-friendly language that non-technical users
 * can understand and act upon.
 * 
 * Key Features:
 * - Technical to natural language translation
 * - Context-aware message generation
 * - User intent recognition and mapping
 * - Status humanization
 * - Progress narrative creation
 */

import { OrchestrationSession, CoordinationEvent, Agent } from '@/lib/types/khive';

export interface UserFriendlyEvent {
  id: string;
  timestamp: Date;
  type: 'milestone' | 'progress' | 'completion' | 'insight' | 'issue' | 'status';
  title: string;
  description: string;
  details?: string;
  actionable?: string;
  severity: 'info' | 'success' | 'warning' | 'error';
  category: 'workflow' | 'team' | 'system' | 'result';
  relatedWorkflow?: string;
  agent?: {
    name: string;
    role: string;
    expertise: string;
    avatar: string;
  };
  progress?: {
    percentage: number;
    phase: string;
    estimatedCompletion: string;
  };
}

export interface UserFriendlyStatus {
  overall: 'healthy' | 'active' | 'attention' | 'offline';
  message: string;
  details: string;
  actionable?: string;
  metrics: {
    activeWorkflows: number;
    completedToday: number;
    teamSize: number;
    efficiency: number;
  };
}

export interface UserFriendlyIntent {
  intent: string;
  confidence: number;
  userFriendlyAction: string;
  description: string;
  category: 'create' | 'analyze' | 'monitor' | 'manage' | 'help';
  estimatedTime: string;
  requiredResources: string[];
}

export class StateTranslator {
  private static readonly ROLE_TRANSLATIONS = {
    analyst: {
      name: 'Data Analyst',
      expertise: 'analyzing patterns and extracting insights from data',
      avatar: '📊'
    },
    researcher: {
      name: 'Research Specialist',
      expertise: 'gathering information and conducting thorough research',
      avatar: '🔍'
    },
    architect: {
      name: 'System Designer',
      expertise: 'designing robust system architectures and workflows',
      avatar: '🏗️'
    },
    implementer: {
      name: 'Implementation Expert',
      expertise: 'building and deploying solutions efficiently',
      avatar: '⚒️'
    },
    reviewer: {
      name: 'Quality Reviewer',
      expertise: 'ensuring high standards and quality assurance',
      avatar: '👁️'
    },
    tester: {
      name: 'Quality Tester',
      expertise: 'testing and validating system functionality',
      avatar: '🧪'
    },
    orchestrator: {
      name: 'Project Coordinator',
      expertise: 'coordinating teams and managing workflow execution',
      avatar: '🎭'
    }
  };

  private static readonly EVENT_TRANSLATIONS = {
    agent_spawn: {
      title: (agent: Agent) => `${StateTranslator.translateAgent(agent).name} joined your team`,
      description: (agent: Agent) => `A specialist in ${StateTranslator.translateAgent(agent).expertise} is now available to help with your project`,
      type: 'milestone' as const,
      severity: 'success' as const,
      category: 'team' as const
    },
    task_start: {
      title: (taskName: string) => `Started: ${StateTranslator.humanizeTaskName(taskName)}`,
      description: () => 'Your AI team has begun working on this task with focused attention',
      type: 'progress' as const,
      severity: 'info' as const,
      category: 'workflow' as const
    },
    task_complete: {
      title: (taskName: string) => `Completed: ${StateTranslator.humanizeTaskName(taskName)}`,
      description: () => 'Task finished successfully with high-quality results ready for review',
      type: 'completion' as const,
      severity: 'success' as const,
      category: 'result' as const
    },
    coordination_update: {
      title: () => 'Team coordination update',
      description: () => 'Your AI agents are collaborating effectively and sharing insights',
      type: 'status' as const,
      severity: 'info' as const,
      category: 'team' as const
    },
    error: {
      title: () => 'Attention needed',
      description: (error: string) => `An issue requires your attention: ${StateTranslator.humanizeError(error)}`,
      type: 'issue' as const,
      severity: 'error' as const,
      category: 'system' as const
    }
  };

  private static readonly INTENT_PATTERNS = [
    {
      patterns: [/analyz/i, /performance/i, /metrics/i, /insight/i, /understand/i],
      intent: 'analyze_project',
      userFriendlyAction: 'Analyze your project performance and generate insights',
      description: 'Get comprehensive analysis of your project metrics, performance patterns, and optimization opportunities',
      category: 'analyze' as const,
      estimatedTime: '5-10 minutes',
      requiredResources: ['Data Analyst', 'Performance Monitor']
    },
    {
      patterns: [/create/i, /build/i, /new/i, /setup/i, /make/i],
      intent: 'create_workflow',
      userFriendlyAction: 'Create a new automated workflow',
      description: 'Design and implement a custom workflow tailored to your specific requirements and goals',
      category: 'create' as const,
      estimatedTime: '10-20 minutes',
      requiredResources: ['System Designer', 'Implementation Expert']
    },
    {
      patterns: [/monitor/i, /track/i, /watch/i, /status/i, /health/i],
      intent: 'setup_monitoring',
      userFriendlyAction: 'Set up comprehensive monitoring and alerts',
      description: 'Configure real-time monitoring for your systems, workflows, and performance metrics',
      category: 'monitor' as const,
      estimatedTime: '3-8 minutes',
      requiredResources: ['System Monitor', 'Alert Manager']
    },
    {
      patterns: [/optimize/i, /improve/i, /faster/i, /better/i, /efficiency/i],
      intent: 'optimize_system',
      userFriendlyAction: 'Optimize system performance and efficiency',
      description: 'Identify bottlenecks and implement performance improvements across your workflows',
      category: 'manage' as const,
      estimatedTime: '15-30 minutes',
      requiredResources: ['Performance Analyst', 'System Optimizer']
    },
    {
      patterns: [/help/i, /explain/i, /guide/i, /how/i, /what/i],
      intent: 'get_assistance',
      userFriendlyAction: 'Get personalized guidance and explanations',
      description: 'Receive expert guidance, explanations, and recommendations tailored to your needs',
      category: 'help' as const,
      estimatedTime: '2-5 minutes',
      requiredResources: ['AI Assistant', 'Knowledge Guide']
    }
  ];

  /**
   * Transform system coordination event to user-friendly narrative
   */
  static translateEvent(event: CoordinationEvent, agents: Agent[] = []): UserFriendlyEvent {
    const agent = agents.find(a => a.id === event.agent_id);
    const translation = StateTranslator.EVENT_TRANSLATIONS[event.type as keyof typeof StateTranslator.EVENT_TRANSLATIONS];
    
    if (!translation) {
      return StateTranslator.createGenericEvent(event, agent);
    }

    const title = typeof translation.title === 'function' 
      ? translation.title(event.task_name || agent || event.message || 'Unknown')
      : translation.title;

    const description = typeof translation.description === 'function'
      ? translation.description(event.message || event.task_name || 'system update')
      : translation.description;

    return {
      id: event.id || `event_${Date.now()}`,
      timestamp: new Date(event.timestamp || Date.now()),
      type: translation.type,
      title,
      description,
      details: StateTranslator.generateEventDetails(event, agent),
      actionable: StateTranslator.generateActionableMessage(event),
      severity: translation.severity,
      category: translation.category,
      relatedWorkflow: event.session_id,
      agent: agent ? StateTranslator.translateAgent(agent) : undefined,
      progress: StateTranslator.calculateProgress(event)
    };
  }

  /**
   * Transform orchestration session to user-friendly workflow summary
   */
  static translateSession(session: OrchestrationSession, agents: Agent[] = []): UserFriendlyEvent {
    const sessionAgents = agents.filter(a => session.active_agents?.includes(a.id));
    
    return {
      id: `session_${session.sessionId}`,
      timestamp: new Date(session.created_at || Date.now()),
      type: 'milestone',
      title: `Workflow "${StateTranslator.humanizeSessionName(session.sessionId)}" initiated`,
      description: `Started a collaborative workflow with ${sessionAgents.length || 'multiple'} specialized AI agents`,
      details: `This workflow coordinates ${sessionAgents.length > 0 ? sessionAgents.map(a => StateTranslator.translateAgent(a).name).join(', ') : 'various specialists'} to accomplish your objectives efficiently.`,
      severity: 'info',
      category: 'workflow',
      relatedWorkflow: session.sessionId,
      agent: sessionAgents.length > 0 ? {
        name: `Team of ${sessionAgents.length}`,
        role: 'Coordination Team',
        expertise: 'managing complex multi-agent workflows',
        avatar: '👥'
      } : undefined,
      progress: {
        percentage: StateTranslator.calculateSessionProgress(session),
        phase: StateTranslator.determineSessionPhase(session),
        estimatedCompletion: StateTranslator.estimateSessionCompletion(session)
      }
    };
  }

  /**
   * Analyze natural language input and suggest user-friendly intents
   */
  static analyzeIntent(userInput: string): UserFriendlyIntent[] {
    const input = userInput.toLowerCase();
    const matches: (UserFriendlyIntent & { score: number })[] = [];

    StateTranslator.INTENT_PATTERNS.forEach(pattern => {
      let score = 0;
      let matchCount = 0;

      pattern.patterns.forEach(regex => {
        const match = input.match(regex);
        if (match) {
          score += 1;
          matchCount++;
        }
      });

      if (matchCount > 0) {
        const confidence = Math.min(0.95, (score / pattern.patterns.length) * 0.8 + 0.2);
        matches.push({
          intent: pattern.intent,
          confidence,
          userFriendlyAction: pattern.userFriendlyAction,
          description: pattern.description,
          category: pattern.category,
          estimatedTime: pattern.estimatedTime,
          requiredResources: pattern.requiredResources,
          score
        });
      }
    });

    // Sort by confidence and return top matches
    return matches
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 3)
      .map(({ score, ...intent }) => intent);
  }

  /**
   * Generate overall system status in user-friendly terms
   */
  static translateSystemStatus(
    daemonStatus: any, 
    sessions: OrchestrationSession[], 
    agents: Agent[],
    events: CoordinationEvent[]
  ): UserFriendlyStatus {
    const activeWorkflows = sessions.filter(s => s.status === 'executing').length;
    const completedToday = StateTranslator.countTodayCompletions(events);
    const teamSize = agents.filter(a => a.status === 'active').length;
    
    let overall: UserFriendlyStatus['overall'];
    let message: string;
    let details: string;
    let actionable: string | undefined;

    if (!daemonStatus.running) {
      overall = 'offline';
      message = 'System is currently offline';
      details = 'The AI orchestration system is not responding. This may be due to maintenance or connectivity issues.';
      actionable = 'Please check your connection or contact support if the issue persists.';
    } else if (activeWorkflows === 0) {
      overall = 'healthy';
      message = 'System ready for new work';
      details = `Everything is running smoothly with ${teamSize} AI agents standing by to help with your projects.`;
    } else if (activeWorkflows > 5) {
      overall = 'attention';
      message = 'High activity detected';
      details = `${activeWorkflows} workflows are currently active. The system is working hard but may need attention.`;
      actionable = 'Consider monitoring progress and pausing non-critical workflows if needed.';
    } else {
      overall = 'active';
      message = 'Working on your projects';
      details = `${activeWorkflows} workflows are currently in progress with ${teamSize} AI agents actively contributing.`;
    }

    const efficiency = StateTranslator.calculateEfficiency(sessions, events);

    return {
      overall,
      message,
      details,
      actionable,
      metrics: {
        activeWorkflows,
        completedToday,
        teamSize,
        efficiency
      }
    };
  }

  // Private helper methods
  private static translateAgent(agent: Agent) {
    const roleInfo = StateTranslator.ROLE_TRANSLATIONS[agent.role as keyof typeof StateTranslator.ROLE_TRANSLATIONS] || {
      name: 'AI Specialist',
      expertise: 'specialized task execution',
      avatar: '🤖'
    };

    return {
      name: agent.name || roleInfo.name,
      role: StateTranslator.capitalizeRole(agent.role),
      expertise: roleInfo.expertise,
      avatar: roleInfo.avatar
    };
  }

  private static humanizeTaskName(taskName: string): string {
    if (!taskName) return 'New Task';
    
    return taskName
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .replace(/\b\w/g, l => l.toUpperCase())
      .replace(/khive/gi, 'KHIVE')
      .replace(/api/gi, 'API')
      .trim();
  }

  private static humanizeSessionName(sessionId: string): string {
    if (!sessionId) return 'New Project';
    
    const parts = sessionId.split('_');
    if (parts.length > 1) {
      return `${parts[0].toUpperCase()} Project`;
    }
    return `Project ${sessionId.substring(0, 8).toUpperCase()}`;
  }

  private static humanizeError(error: string): string {
    const errorPatterns = [
      { pattern: /connection/i, message: 'Connection issue detected' },
      { pattern: /timeout/i, message: 'Operation took longer than expected' },
      { pattern: /permission/i, message: 'Access permission required' },
      { pattern: /not found/i, message: 'Required resource not available' },
      { pattern: /invalid/i, message: 'Invalid input or configuration' }
    ];

    for (const { pattern, message } of errorPatterns) {
      if (pattern.test(error)) {
        return message;
      }
    }

    return 'An unexpected issue occurred';
  }

  private static capitalizeRole(role: string): string {
    return role
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  private static generateEventDetails(event: CoordinationEvent, agent?: Agent): string {
    const agentName = agent ? StateTranslator.translateAgent(agent).name : 'AI Agent';
    
    switch (event.type) {
      case 'agent_spawn':
        return `${agentName} has been activated and is ready to contribute specialized expertise to your project. This agent will work autonomously while coordinating with other team members.`;
      case 'task_start':
        return `${agentName} is now focusing on this task, applying specialized knowledge and tools to deliver high-quality results efficiently.`;
      case 'task_complete':
        return `${agentName} has successfully completed this task. All objectives have been met and the output has been validated for quality and accuracy.`;
      case 'coordination_update':
        return 'The AI team is actively sharing information, coordinating efforts, and ensuring all agents are aligned toward your project goals.';
      default:
        return 'The AI team is making progress on your project with continuous coordination and quality monitoring.';
    }
  }

  private static generateActionableMessage(event: CoordinationEvent): string | undefined {
    switch (event.type) {
      case 'task_complete':
        return 'You can now review the completed work and provide feedback or approval.';
      case 'error':
        return 'Please review the issue details and consider if any input or clarification is needed.';
      default:
        return undefined;
    }
  }

  private static calculateProgress(event: CoordinationEvent) {
    if (event.type === 'task_complete') {
      return {
        percentage: 100,
        phase: 'Complete',
        estimatedCompletion: 'Now'
      };
    } else if (event.type === 'task_start') {
      return {
        percentage: 15,
        phase: 'In Progress',
        estimatedCompletion: '5-15 minutes'
      };
    }
    return undefined;
  }

  private static calculateSessionProgress(session: OrchestrationSession): number {
    switch (session.status) {
      case 'completed': return 100;
      case 'executing': return Math.random() * 60 + 20; // 20-80%
      case 'pending': return 0;
      default: return 0;
    }
  }

  private static determineSessionPhase(session: OrchestrationSession): string {
    switch (session.status) {
      case 'completed': return 'Completed';
      case 'executing': return 'Active';
      case 'pending': return 'Initializing';
      default: return 'Unknown';
    }
  }

  private static estimateSessionCompletion(session: OrchestrationSession): string {
    const estimates = ['2 minutes', '5 minutes', '10 minutes', '20 minutes', '45 minutes'];
    return estimates[Math.abs((session.sessionId || '').charCodeAt(0) || 0) % estimates.length];
  }

  private static countTodayCompletions(events: CoordinationEvent[]): number {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    return events.filter(event => {
      const eventDate = new Date(event.timestamp || 0);
      return eventDate >= today && event.type === 'task_complete';
    }).length;
  }

  private static calculateEfficiency(sessions: OrchestrationSession[], events: CoordinationEvent[]): number {
    // Simple efficiency calculation based on completion rate
    const totalSessions = sessions.length;
    const completedSessions = sessions.filter(s => s.status === 'completed').length;
    
    if (totalSessions === 0) return 100;
    
    const baseEfficiency = (completedSessions / totalSessions) * 100;
    const activityBonus = Math.min(20, events.length * 2); // Activity bonus up to 20%
    
    return Math.min(100, Math.round(baseEfficiency + activityBonus));
  }

  private static createGenericEvent(event: CoordinationEvent, agent?: Agent): UserFriendlyEvent {
    return {
      id: event.id || `generic_${Date.now()}`,
      timestamp: new Date(event.timestamp || Date.now()),
      type: 'status',
      title: 'System update',
      description: 'Your AI team has provided a status update',
      details: event.message || 'The AI orchestration system has generated an update.',
      severity: 'info',
      category: 'system',
      relatedWorkflow: event.session_id,
      agent: agent ? StateTranslator.translateAgent(agent) : undefined
    };
  }
}