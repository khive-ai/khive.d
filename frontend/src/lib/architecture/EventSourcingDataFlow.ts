/**
 * Advanced Data Flow Architecture with Event Sourcing & Reactive Streams
 * Built by architect+software-architecture for Ocean's Agentic ERP Command Center
 * 
 * Architecture Patterns:
 * - Event Sourcing: Complete audit trail of all agent actions
 * - CQRS: Separate read/write models for optimal performance
 * - Reactive Streams: High-throughput data processing with backpressure
 * - Event Bus: Decoupled agent communication architecture
 * - Stream Processing: Real-time data transformations and aggregations
 */

import { Subject, BehaviorSubject, Observable, merge, combineLatest } from 'rxjs';
import { 
  map, 
  filter, 
  scan, 
  debounceTime, 
  throttleTime, 
  bufferTime,
  mergeMap,
  catchError,
  shareReplay,
  distinctUntilChanged,
  withLatestFrom
} from 'rxjs/operators';
import { AgentRealTimeStatus } from '../types/agent-composition';

// ============================================================================
// EVENT SOURCING ARCHITECTURE
// ============================================================================

/**
 * Domain Event - Base interface for all agent events
 */
export interface DomainEvent {
  readonly id: string;
  readonly type: string;
  readonly aggregateId: string;
  readonly aggregateType: 'agent' | 'session' | 'coordination';
  readonly timestamp: number;
  readonly version: number;
  readonly metadata: Record<string, any>;
  readonly causationId?: string; // Event that caused this event
  readonly correlationId?: string; // Business process correlation
}

/**
 * Agent-specific domain events
 */
export interface AgentSpawnedEvent extends DomainEvent {
  type: 'agent.spawned';
  aggregateType: 'agent';
  payload: {
    agentId: string;
    roleId: string;
    domainId: string;
    coordinationId: string;
    composition: any;
  };
}

export interface AgentStatusChangedEvent extends DomainEvent {
  type: 'agent.status.changed';
  aggregateType: 'agent';
  payload: {
    agentId: string;
    previousStatus: string;
    newStatus: string;
    reason?: string;
  };
}

export interface AgentTaskCompletedEvent extends DomainEvent {
  type: 'agent.task.completed';
  aggregateType: 'agent';
  payload: {
    agentId: string;
    taskId: string;
    result: any;
    duration: number;
    cost: number;
    success: boolean;
  };
}

export interface AgentResourceUsageEvent extends DomainEvent {
  type: 'agent.resource.usage';
  aggregateType: 'agent';
  payload: {
    agentId: string;
    cpu: number;
    memory: number;
    tokensUsed: number;
    apiCalls: number;
    timestamp: number;
  };
}

export type AgentEvent = 
  | AgentSpawnedEvent 
  | AgentStatusChangedEvent 
  | AgentTaskCompletedEvent 
  | AgentResourceUsageEvent;

/**
 * Event Store - Immutable append-only log of all domain events
 */
export class EventStore {
  private events: DomainEvent[] = [];
  private eventSubject = new Subject<DomainEvent>();
  private snapshotCache = new Map<string, any>();

  /**
   * Append event to store - fundamental operation for event sourcing
   */
  async append(event: DomainEvent): Promise<void> {
    console.log(`[EVENT-STORE] Appending event: ${event.type} for ${event.aggregateId}`);
    
    // Validate event version for optimistic concurrency control
    const lastEvent = this.getLastEventForAggregate(event.aggregateId);
    if (lastEvent && event.version !== lastEvent.version + 1) {
      throw new Error(`Concurrency conflict: Expected version ${lastEvent.version + 1}, got ${event.version}`);
    }

    // Store event immutably
    this.events.push(Object.freeze(event));
    
    // Publish to reactive stream
    this.eventSubject.next(event);
    
    // Invalidate snapshot cache for this aggregate
    this.snapshotCache.delete(event.aggregateId);
  }

  /**
   * Get all events for an aggregate - used for state reconstruction
   */
  getEventsForAggregate(aggregateId: string, fromVersion = 0): DomainEvent[] {
    return this.events
      .filter(event => event.aggregateId === aggregateId && event.version > fromVersion)
      .sort((a, b) => a.version - b.version);
  }

  /**
   * Get events by type - used for projections and analytics
   */
  getEventsByType(eventType: string, limit?: number): DomainEvent[] {
    const filtered = this.events.filter(event => event.type === eventType);
    return limit ? filtered.slice(-limit) : filtered;
  }

  /**
   * Event stream for reactive subscriptions
   */
  getEventStream(): Observable<DomainEvent> {
    return this.eventSubject.asObservable();
  }

  /**
   * Get last event for aggregate (for version checking)
   */
  private getLastEventForAggregate(aggregateId: string): DomainEvent | undefined {
    return this.events
      .filter(event => event.aggregateId === aggregateId)
      .sort((a, b) => b.version - a.version)[0];
  }

  /**
   * Create snapshot for performance optimization
   */
  createSnapshot(aggregateId: string, snapshot: any, version: number): void {
    this.snapshotCache.set(aggregateId, { snapshot, version, timestamp: Date.now() });
    console.log(`[EVENT-STORE] Created snapshot for ${aggregateId} at version ${version}`);
  }

  /**
   * Get snapshot if available
   */
  getSnapshot(aggregateId: string): { snapshot: any; version: number; timestamp: number } | undefined {
    return this.snapshotCache.get(aggregateId);
  }
}

// ============================================================================
// CQRS ARCHITECTURE - COMMAND & QUERY SEPARATION
// ============================================================================

/**
 * Command - Represents an intent to change state
 */
export interface Command {
  readonly id: string;
  readonly type: string;
  readonly aggregateId: string;
  readonly payload: any;
  readonly timestamp: number;
  readonly userId?: string;
}

/**
 * Query - Represents a request for data
 */
export interface Query {
  readonly id: string;
  readonly type: string;
  readonly parameters: Record<string, any>;
  readonly timestamp: number;
}

/**
 * Command Handler - Processes commands and generates events
 */
export interface CommandHandler<T extends Command> {
  handle(command: T): Promise<DomainEvent[]>;
}

/**
 * Query Handler - Processes queries from read models
 */
export interface QueryHandler<T extends Query> {
  handle(query: T): Promise<any>;
}

/**
 * Agent Command Handlers
 */
export class SpawnAgentCommandHandler implements CommandHandler<any> {
  constructor(private eventStore: EventStore) {}

  async handle(command: any): Promise<DomainEvent[]> {
    const event: AgentSpawnedEvent = {
      id: `event_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      type: 'agent.spawned',
      aggregateId: command.payload.agentId,
      aggregateType: 'agent',
      timestamp: Date.now(),
      version: 1,
      metadata: { commandId: command.id },
      payload: command.payload
    };

    await this.eventStore.append(event);
    return [event];
  }
}

export class ChangeAgentStatusCommandHandler implements CommandHandler<any> {
  constructor(private eventStore: EventStore) {}

  async handle(command: any): Promise<DomainEvent[]> {
    // Get current state to determine previous status
    const currentState = await this.reconstructAgentState(command.aggregateId);
    
    const event: AgentStatusChangedEvent = {
      id: `event_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      type: 'agent.status.changed',
      aggregateId: command.aggregateId,
      aggregateType: 'agent',
      timestamp: Date.now(),
      version: currentState.version + 1,
      metadata: { commandId: command.id },
      payload: {
        agentId: command.aggregateId,
        previousStatus: currentState.status,
        newStatus: command.payload.newStatus,
        reason: command.payload.reason
      }
    };

    await this.eventStore.append(event);
    return [event];
  }

  private async reconstructAgentState(agentId: string): Promise<any> {
    // Simplified state reconstruction - in real implementation would be more sophisticated
    const events = this.eventStore.getEventsForAggregate(agentId);
    return events.reduce((state, event) => {
      switch (event.type) {
        case 'agent.spawned':
          return { ...state, status: 'spawning', version: event.version };
        case 'agent.status.changed':
          return { ...state, status: (event as AgentStatusChangedEvent).payload.newStatus, version: event.version };
        default:
          return state;
      }
    }, { status: 'unknown', version: 0 });
  }
}

// ============================================================================
// REACTIVE STREAMS ARCHITECTURE
// ============================================================================

/**
 * Agent Data Stream Processor - Reactive processing of agent events
 */
export class AgentDataStreamProcessor {
  private eventStore: EventStore;
  private agentStatusSubject = new BehaviorSubject<Map<string, AgentRealTimeStatus>>(new Map());
  private resourceMetricsSubject = new Subject<any>();

  constructor(eventStore: EventStore) {
    this.eventStore = eventStore;
    this.initializeStreams();
  }

  private initializeStreams(): void {
    // Stream 1: Real-time agent status projection
    this.eventStore.getEventStream()
      .pipe(
        filter(event => event.type.startsWith('agent.')),
        debounceTime(100), // Reduce noise from rapid events
        scan(this.buildAgentStatusProjection.bind(this), new Map<string, AgentRealTimeStatus>()),
        shareReplay(1) // Cache latest state for new subscribers
      )
      .subscribe(agentStatuses => {
        console.log(`[STREAM-PROCESSOR] Agent status projection updated: ${agentStatuses.size} agents`);
        this.agentStatusSubject.next(agentStatuses);
      });

    // Stream 2: Resource usage aggregation
    this.eventStore.getEventStream()
      .pipe(
        filter(event => event.type === 'agent.resource.usage'),
        bufferTime(5000), // Collect 5 seconds worth of resource events
        filter(events => events.length > 0),
        map(this.aggregateResourceMetrics.bind(this))
      )
      .subscribe(metrics => {
        console.log(`[STREAM-PROCESSOR] Resource metrics aggregated: ${Object.keys(metrics).length} agents`);
        this.resourceMetricsSubject.next(metrics);
      });

    // Stream 3: Performance analytics
    this.eventStore.getEventStream()
      .pipe(
        filter(event => event.type === 'agent.task.completed'),
        throttleTime(1000), // Limit processing to once per second
        scan(this.buildPerformanceMetrics.bind(this), new Map()),
        distinctUntilChanged((prev, curr) => prev.size === curr.size)
      )
      .subscribe(performanceMetrics => {
        console.log(`[STREAM-PROCESSOR] Performance metrics updated`);
        // Could emit to performance subject here
      });
  }

  /**
   * Build agent status projection from events
   */
  private buildAgentStatusProjection(
    currentState: Map<string, AgentRealTimeStatus>, 
    event: DomainEvent
  ): Map<string, AgentRealTimeStatus> {
    const newState = new Map(currentState);
    
    switch (event.type) {
      case 'agent.spawned': {
        const spawned = event as AgentSpawnedEvent;
        newState.set(spawned.payload.agentId, this.createInitialAgentStatus(spawned));
        break;
      }
      case 'agent.status.changed': {
        const statusChanged = event as AgentStatusChangedEvent;
        const current = newState.get(statusChanged.payload.agentId);
        if (current) {
          newState.set(statusChanged.payload.agentId, {
            ...current,
            status: statusChanged.payload.newStatus as any,
            last_activity: event.timestamp
          });
        }
        break;
      }
      case 'agent.task.completed': {
        const taskCompleted = event as AgentTaskCompletedEvent;
        const current = newState.get(taskCompleted.payload.agentId);
        if (current) {
          newState.set(taskCompleted.payload.agentId, {
            ...current,
            performance_metrics: {
              ...current.performance_metrics,
              tasks_completed: current.performance_metrics.tasks_completed + 1,
              cost: current.performance_metrics.cost + taskCompleted.payload.cost,
              success_rate: taskCompleted.payload.success ? 
                (current.performance_metrics.success_rate + 1) / 2 : 
                current.performance_metrics.success_rate / 2
            },
            last_activity: event.timestamp
          });
        }
        break;
      }
      case 'agent.resource.usage': {
        const resourceUsage = event as AgentResourceUsageEvent;
        const current = newState.get(resourceUsage.payload.agentId);
        if (current) {
          newState.set(resourceUsage.payload.agentId, {
            ...current,
            resource_usage: {
              cpu: resourceUsage.payload.cpu,
              memory: resourceUsage.payload.memory,
              tokens_used: resourceUsage.payload.tokensUsed,
              api_calls: resourceUsage.payload.apiCalls
            },
            last_activity: event.timestamp
          });
        }
        break;
      }
    }

    return newState;
  }

  /**
   * Create initial agent status from spawn event
   */
  private createInitialAgentStatus(event: AgentSpawnedEvent): AgentRealTimeStatus {
    return {
      agent_id: event.payload.agentId,
      status: 'spawning',
      current_task: 'Initializing agent composition',
      progress: 0,
      resource_usage: {
        cpu: 0,
        memory: 0,
        tokens_used: 0,
        api_calls: 0
      },
      performance_metrics: {
        tasks_completed: 0,
        avg_task_time: 0,
        success_rate: 0,
        cost: 0
      },
      coordination: {
        locks_held: [],
        waiting_for: [],
        conflicts: []
      },
      last_activity: event.timestamp
    };
  }

  /**
   * Aggregate resource metrics from multiple events
   */
  private aggregateResourceMetrics(events: DomainEvent[]): Record<string, any> {
    const metrics: Record<string, any> = {};
    
    events.forEach(event => {
      const resourceEvent = event as AgentResourceUsageEvent;
      const agentId = resourceEvent.payload.agentId;
      
      if (!metrics[agentId]) {
        metrics[agentId] = {
          agent_id: agentId,
          samples: 0,
          avg_cpu: 0,
          avg_memory: 0,
          total_tokens: 0,
          total_api_calls: 0
        };
      }
      
      const agent = metrics[agentId];
      agent.samples += 1;
      agent.avg_cpu = (agent.avg_cpu * (agent.samples - 1) + resourceEvent.payload.cpu) / agent.samples;
      agent.avg_memory = (agent.avg_memory * (agent.samples - 1) + resourceEvent.payload.memory) / agent.samples;
      agent.total_tokens += resourceEvent.payload.tokensUsed;
      agent.total_api_calls += resourceEvent.payload.apiCalls;
    });

    return metrics;
  }

  /**
   * Build performance metrics from task completion events
   */
  private buildPerformanceMetrics(
    currentMetrics: Map<string, any>,
    event: DomainEvent
  ): Map<string, any> {
    const taskCompleted = event as AgentTaskCompletedEvent;
    const agentId = taskCompleted.payload.agentId;
    
    const current = currentMetrics.get(agentId) || {
      agent_id: agentId,
      total_tasks: 0,
      successful_tasks: 0,
      total_cost: 0,
      total_duration: 0
    };

    current.total_tasks += 1;
    if (taskCompleted.payload.success) {
      current.successful_tasks += 1;
    }
    current.total_cost += taskCompleted.payload.cost;
    current.total_duration += taskCompleted.payload.duration;
    
    // Calculate derived metrics
    current.success_rate = current.successful_tasks / current.total_tasks;
    current.avg_duration = current.total_duration / current.total_tasks;
    current.avg_cost = current.total_cost / current.total_tasks;

    currentMetrics.set(agentId, current);
    return currentMetrics;
  }

  /**
   * Get reactive stream of agent statuses
   */
  getAgentStatusStream(): Observable<Map<string, AgentRealTimeStatus>> {
    return this.agentStatusSubject.asObservable();
  }

  /**
   * Get reactive stream of resource metrics
   */
  getResourceMetricsStream(): Observable<any> {
    return this.resourceMetricsSubject.asObservable();
  }

  /**
   * Get current agent status snapshot
   */
  getCurrentAgentStatuses(): Map<string, AgentRealTimeStatus> {
    return this.agentStatusSubject.getValue();
  }
}

// ============================================================================
// EVENT BUS ARCHITECTURE
// ============================================================================

/**
 * Event Bus - Decoupled communication between agent system components
 */
export class EventBus {
  private subjects = new Map<string, Subject<any>>();
  private eventStore: EventStore;

  constructor(eventStore: EventStore) {
    this.eventStore = eventStore;
  }

  /**
   * Publish event to specific channel
   */
  publish(channel: string, event: any): void {
    console.log(`[EVENT-BUS] Publishing to ${channel}:`, event.type || event);
    
    // Store domain events in event store
    if (this.isDomainEvent(event)) {
      this.eventStore.append(event);
    }

    // Publish to reactive streams
    if (!this.subjects.has(channel)) {
      this.subjects.set(channel, new Subject());
    }
    
    this.subjects.get(channel)!.next(event);
  }

  /**
   * Subscribe to channel events
   */
  subscribe(channel: string): Observable<any> {
    if (!this.subjects.has(channel)) {
      this.subjects.set(channel, new Subject());
    }
    
    return this.subjects.get(channel)!.asObservable();
  }

  /**
   * Subscribe to multiple channels with pattern matching
   */
  subscribePattern(pattern: RegExp): Observable<{ channel: string; event: any }> {
    const matchingChannels = Array.from(this.subjects.keys())
      .filter(channel => pattern.test(channel));
    
    const streams = matchingChannels.map(channel => 
      this.subscribe(channel).pipe(
        map(event => ({ channel, event }))
      )
    );
    
    return merge(...streams);
  }

  /**
   * Check if event is a domain event that should be stored
   */
  private isDomainEvent(event: any): event is DomainEvent {
    return event && 
           typeof event.id === 'string' &&
           typeof event.type === 'string' &&
           typeof event.aggregateId === 'string' &&
           typeof event.timestamp === 'number';
  }
}

// ============================================================================
// ARCHITECTURAL FACADE - UNIFIED INTERFACE
// ============================================================================

/**
 * Data Flow Architecture Facade - Single entry point for advanced data flow patterns
 */
export class DataFlowArchitecture {
  public readonly eventStore: EventStore;
  public readonly eventBus: EventBus;
  public readonly streamProcessor: AgentDataStreamProcessor;
  public readonly commandHandlers: Map<string, CommandHandler<any>>;
  public readonly queryHandlers: Map<string, QueryHandler<any>>;

  constructor() {
    // Initialize core components
    this.eventStore = new EventStore();
    this.eventBus = new EventBus(this.eventStore);
    this.streamProcessor = new AgentDataStreamProcessor(this.eventStore);
    
    // Initialize command handlers
    this.commandHandlers = new Map();
    this.commandHandlers.set('spawn.agent', new SpawnAgentCommandHandler(this.eventStore));
    this.commandHandlers.set('change.agent.status', new ChangeAgentStatusCommandHandler(this.eventStore));
    
    // Initialize query handlers
    this.queryHandlers = new Map();
    
    console.log('[DATA-FLOW-ARCH] Advanced data flow architecture initialized');
  }

  /**
   * Execute command through CQRS pattern
   */
  async executeCommand(command: Command): Promise<DomainEvent[]> {
    const handler = this.commandHandlers.get(command.type);
    if (!handler) {
      throw new Error(`No command handler found for: ${command.type}`);
    }
    
    console.log(`[DATA-FLOW-ARCH] Executing command: ${command.type}`);
    return await handler.handle(command);
  }

  /**
   * Execute query through CQRS pattern
   */
  async executeQuery(query: Query): Promise<any> {
    const handler = this.queryHandlers.get(query.type);
    if (!handler) {
      throw new Error(`No query handler found for: ${query.type}`);
    }
    
    console.log(`[DATA-FLOW-ARCH] Executing query: ${query.type}`);
    return await handler.handle(query);
  }

  /**
   * Get reactive agent data streams
   */
  getAgentDataStreams() {
    return {
      agentStatuses: this.streamProcessor.getAgentStatusStream(),
      resourceMetrics: this.streamProcessor.getResourceMetricsStream(),
      events: this.eventStore.getEventStream()
    };
  }
}

// Export singleton instance for application use
export const dataFlowArchitecture = new DataFlowArchitecture();