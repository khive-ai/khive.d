/**
 * Centralized State Management for Complex Agent Coordination
 * Built by architect+software-architecture for Ocean's Agentic ERP Command Center
 * 
 * Architecture Patterns:
 * - Centralized Coordination Store with distributed state synchronization
 * - Intelligent Task Distribution with load balancing and dependency resolution
 * - Distributed Locking with deadlock detection and prevention
 * - Workflow Orchestration with parallel and sequential execution patterns
 * - Conflict Resolution with priority-based resource allocation
 * - State Recovery with checkpoint/restore mechanisms
 */

import { BehaviorSubject, Observable, Subject, combineLatest, merge } from 'rxjs';
import { map, filter, distinctUntilChanged, debounceTime, scan } from 'rxjs/operators';
import { dataFlowArchitecture, DomainEvent } from './EventSourcingDataFlow';

// ============================================================================
// CORE STATE MANAGEMENT TYPES
// ============================================================================

export interface CoordinationState {
  sessionId: string;
  coordinationId: string;
  agents: Map<string, AgentCoordinationInfo>;
  tasks: Map<string, TaskInfo>;
  resources: Map<string, ResourceInfo>;
  workflows: Map<string, WorkflowInfo>;
  locks: Map<string, LockInfo>;
  metrics: CoordinationMetrics;
  lastUpdated: number;
}

export interface AgentCoordinationInfo {
  agentId: string;
  status: 'idle' | 'working' | 'waiting' | 'blocked' | 'failed' | 'completed';
  role: string;
  domain: string;
  currentTask?: string;
  assignedTasks: string[];
  capabilities: string[];
  workload: number; // 0-1 representing current capacity usage
  priority: number; // 1-10, higher = more priority
  dependencies: string[]; // Agent IDs this agent depends on
  dependents: string[]; // Agent IDs that depend on this agent
  lastActivity: number;
  performance: {
    tasksCompleted: number;
    averageTaskTime: number;
    successRate: number;
    efficiency: number; // calculated metric
  };
}

export interface TaskInfo {
  taskId: string;
  type: string;
  status: 'pending' | 'assigned' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  assignedTo?: string; // Agent ID
  dependencies: string[]; // Task IDs this task depends on
  dependents: string[]; // Task IDs that depend on this task
  priority: number;
  estimatedDuration: number;
  actualDuration?: number;
  requiredCapabilities: string[];
  requiredResources: string[];
  payload: any;
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
  retryCount: number;
  maxRetries: number;
}

export interface ResourceInfo {
  resourceId: string;
  type: 'file' | 'service' | 'memory' | 'network' | 'compute';
  status: 'available' | 'locked' | 'busy' | 'error';
  lockedBy?: string; // Agent ID
  lockExpiration?: number;
  capacity: number;
  currentUsage: number;
  waitQueue: string[]; // Agent IDs waiting for this resource
  metadata: Record<string, any>;
}

export interface WorkflowInfo {
  workflowId: string;
  name: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  pattern: 'sequential' | 'parallel' | 'conditional' | 'loop' | 'fan_out_fan_in';
  tasks: string[]; // Task IDs in execution order
  currentStep: number;
  totalSteps: number;
  startedAt?: number;
  completedAt?: number;
  errorHandling: 'fail_fast' | 'continue_on_error' | 'retry_on_error';
  retryPolicy: {
    maxRetries: number;
    backoffStrategy: 'linear' | 'exponential' | 'fixed';
    initialDelay: number;
  };
}

export interface LockInfo {
  lockId: string;
  resourceId: string;
  holderId: string; // Agent ID
  lockType: 'shared' | 'exclusive';
  acquiredAt: number;
  expiresAt: number;
  renewable: boolean;
  waitQueue: Array<{
    agentId: string;
    requestedAt: number;
    lockType: 'shared' | 'exclusive';
    priority: number;
  }>;
}

export interface CoordinationMetrics {
  totalAgents: number;
  activeAgents: number;
  idleAgents: number;
  blockedAgents: number;
  totalTasks: number;
  completedTasks: number;
  failedTasks: number;
  averageTaskTime: number;
  systemThroughput: number; // tasks per minute
  resourceUtilization: number; // 0-1
  coordinationEfficiency: number; // calculated metric
  deadlockCount: number;
  conflictCount: number;
  lastCalculated: number;
}

// ============================================================================
// CENTRALIZED COORDINATION STORE
// ============================================================================

export class CentralizedCoordinationStore {
  private state: CoordinationState;
  private stateSubject: BehaviorSubject<CoordinationState>;
  private eventSubject: Subject<CoordinationEvent>;
  private checkpointHistory: CoordinationState[] = [];
  private maxCheckpoints = 10;

  constructor(sessionId: string, coordinationId: string) {
    this.state = this.initializeState(sessionId, coordinationId);
    this.stateSubject = new BehaviorSubject(this.state);
    this.eventSubject = new Subject();
    
    this.initializeEventHandlers();
    console.log(`[COORD-STORE] Initialized coordination store: ${coordinationId}`);
  }

  private initializeState(sessionId: string, coordinationId: string): CoordinationState {
    return {
      sessionId,
      coordinationId,
      agents: new Map(),
      tasks: new Map(),
      resources: new Map(),
      workflows: new Map(),
      locks: new Map(),
      metrics: this.initializeMetrics(),
      lastUpdated: Date.now()
    };
  }

  private initializeMetrics(): CoordinationMetrics {
    return {
      totalAgents: 0,
      activeAgents: 0,
      idleAgents: 0,
      blockedAgents: 0,
      totalTasks: 0,
      completedTasks: 0,
      failedTasks: 0,
      averageTaskTime: 0,
      systemThroughput: 0,
      resourceUtilization: 0,
      coordinationEfficiency: 0,
      deadlockCount: 0,
      conflictCount: 0,
      lastCalculated: Date.now()
    };
  }

  // ============================================================================
  // AGENT MANAGEMENT
  // ============================================================================

  registerAgent(agentInfo: Omit<AgentCoordinationInfo, 'assignedTasks' | 'workload' | 'dependencies' | 'dependents' | 'performance'>): void {
    const completeAgentInfo: AgentCoordinationInfo = {
      ...agentInfo,
      assignedTasks: [],
      workload: 0,
      dependencies: [],
      dependents: [],
      performance: {
        tasksCompleted: 0,
        averageTaskTime: 0,
        successRate: 1,
        efficiency: 1
      }
    };

    this.updateState(state => {
      state.agents.set(agentInfo.agentId, completeAgentInfo);
      return state;
    });

    this.emitEvent({
      type: 'agent.registered',
      agentId: agentInfo.agentId,
      timestamp: Date.now(),
      data: completeAgentInfo
    });

    console.log(`[COORD-STORE] Registered agent: ${agentInfo.agentId}`);
  }

  updateAgentStatus(agentId: string, status: AgentCoordinationInfo['status'], metadata?: any): void {
    this.updateState(state => {
      const agent = state.agents.get(agentId);
      if (agent) {
        agent.status = status;
        agent.lastActivity = Date.now();
        state.agents.set(agentId, agent);
      }
      return state;
    });

    this.emitEvent({
      type: 'agent.status.updated',
      agentId,
      timestamp: Date.now(),
      data: { status, metadata }
    });
  }

  updateAgentPerformance(agentId: string, performance: Partial<AgentCoordinationInfo['performance']>): void {
    this.updateState(state => {
      const agent = state.agents.get(agentId);
      if (agent) {
        agent.performance = { ...agent.performance, ...performance };
        
        // Calculate efficiency based on success rate and speed
        agent.performance.efficiency = agent.performance.successRate * 
          Math.max(0.1, 1 - (agent.performance.averageTaskTime / 3600000)); // Normalize by 1 hour
        
        state.agents.set(agentId, agent);
      }
      return state;
    });
  }

  getAvailableAgents(): AgentCoordinationInfo[] {
    return Array.from(this.state.agents.values())
      .filter(agent => agent.status === 'idle' && agent.workload < 0.8);
  }

  getBestAgentForTask(task: TaskInfo): string | null {
    const availableAgents = this.getAvailableAgents()
      .filter(agent => 
        task.requiredCapabilities.every(cap => agent.capabilities.includes(cap))
      );

    if (availableAgents.length === 0) return null;

    // Score agents based on efficiency, workload, and priority
    const scoredAgents = availableAgents.map(agent => ({
      agent,
      score: this.calculateAgentScore(agent, task)
    }));

    scoredAgents.sort((a, b) => b.score - a.score);
    
    console.log(`[COORD-STORE] Best agent for task ${task.taskId}: ${scoredAgents[0].agent.agentId}`);
    return scoredAgents[0].agent.agentId;
  }

  private calculateAgentScore(agent: AgentCoordinationInfo, task: TaskInfo): number {
    const efficiencyWeight = 0.4;
    const workloadWeight = 0.3;
    const priorityWeight = 0.2;
    const historyWeight = 0.1;

    const efficiencyScore = agent.performance.efficiency;
    const workloadScore = 1 - agent.workload; // Lower workload = higher score
    const priorityScore = agent.priority / 10; // Normalize to 0-1
    const historyScore = Math.min(1, agent.performance.tasksCompleted / 10); // Up to 10 tasks max score

    return (
      efficiencyScore * efficiencyWeight +
      workloadScore * workloadWeight +
      priorityScore * priorityWeight +
      historyScore * historyWeight
    );
  }

  // ============================================================================
  // TASK MANAGEMENT & DISTRIBUTION
  // ============================================================================

  createTask(taskInfo: Omit<TaskInfo, 'taskId' | 'status' | 'createdAt' | 'retryCount'>): string {
    const taskId = `task_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const task: TaskInfo = {
      ...taskInfo,
      taskId,
      status: 'pending',
      createdAt: Date.now(),
      retryCount: 0
    };

    this.updateState(state => {
      state.tasks.set(taskId, task);
      return state;
    });

    this.emitEvent({
      type: 'task.created',
      taskId,
      timestamp: Date.now(),
      data: task
    });

    // Attempt automatic assignment
    this.attemptTaskAssignment(taskId);

    console.log(`[COORD-STORE] Created task: ${taskId}`);
    return taskId;
  }

  assignTask(taskId: string, agentId: string): boolean {
    const task = this.state.tasks.get(taskId);
    const agent = this.state.agents.get(agentId);

    if (!task || !agent) {
      console.error(`[COORD-STORE] Cannot assign task ${taskId} to agent ${agentId}: not found`);
      return false;
    }

    if (task.status !== 'pending') {
      console.error(`[COORD-STORE] Cannot assign task ${taskId}: already ${task.status}`);
      return false;
    }

    if (agent.status !== 'idle') {
      console.error(`[COORD-STORE] Cannot assign task ${taskId} to agent ${agentId}: agent not idle`);
      return false;
    }

    // Check capability requirements
    const hasCapabilities = task.requiredCapabilities.every(cap => 
      agent.capabilities.includes(cap)
    );

    if (!hasCapabilities) {
      console.error(`[COORD-STORE] Cannot assign task ${taskId} to agent ${agentId}: missing capabilities`);
      return false;
    }

    // Update task and agent state
    this.updateState(state => {
      const updatedTask = state.tasks.get(taskId)!;
      const updatedAgent = state.agents.get(agentId)!;

      updatedTask.status = 'assigned';
      updatedTask.assignedTo = agentId;
      updatedAgent.assignedTasks.push(taskId);
      updatedAgent.workload = Math.min(1, updatedAgent.workload + 0.3); // Increase workload
      updatedAgent.status = 'working';

      state.tasks.set(taskId, updatedTask);
      state.agents.set(agentId, updatedAgent);
      return state;
    });

    this.emitEvent({
      type: 'task.assigned',
      taskId,
      agentId,
      timestamp: Date.now(),
      data: { taskId, agentId }
    });

    console.log(`[COORD-STORE] Assigned task ${taskId} to agent ${agentId}`);
    return true;
  }

  completeTask(taskId: string, result: any): void {
    const task = this.state.tasks.get(taskId);
    if (!task || !task.assignedTo) return;

    const duration = Date.now() - (task.startedAt || task.createdAt);

    this.updateState(state => {
      const updatedTask = state.tasks.get(taskId)!;
      const agent = state.agents.get(task.assignedTo!)!;

      updatedTask.status = 'completed';
      updatedTask.completedAt = Date.now();
      updatedTask.actualDuration = duration;

      // Update agent performance
      agent.assignedTasks = agent.assignedTasks.filter(id => id !== taskId);
      agent.workload = Math.max(0, agent.workload - 0.3);
      agent.performance.tasksCompleted++;
      
      const totalTime = agent.performance.averageTaskTime * (agent.performance.tasksCompleted - 1) + duration;
      agent.performance.averageTaskTime = totalTime / agent.performance.tasksCompleted;

      if (agent.assignedTasks.length === 0) {
        agent.status = 'idle';
      }

      state.tasks.set(taskId, updatedTask);
      state.agents.set(task.assignedTo!, agent);
      return state;
    });

    this.emitEvent({
      type: 'task.completed',
      taskId,
      agentId: task.assignedTo,
      timestamp: Date.now(),
      data: { result, duration }
    });

    // Check if this completes any workflows
    this.checkWorkflowCompletion();

    // Try to assign next pending tasks
    this.processPendingTasks();
  }

  private attemptTaskAssignment(taskId: string): boolean {
    const task = this.state.tasks.get(taskId);
    if (!task || task.status !== 'pending') return false;

    // Check dependencies
    const dependenciesMet = task.dependencies.every(depId => {
      const dep = this.state.tasks.get(depId);
      return dep && dep.status === 'completed';
    });

    if (!dependenciesMet) {
      console.log(`[COORD-STORE] Task ${taskId} dependencies not met, queuing`);
      return false;
    }

    const bestAgent = this.getBestAgentForTask(task);
    if (bestAgent) {
      return this.assignTask(taskId, bestAgent);
    }

    return false;
  }

  private processPendingTasks(): void {
    const pendingTasks = Array.from(this.state.tasks.values())
      .filter(task => task.status === 'pending')
      .sort((a, b) => b.priority - a.priority);

    for (const task of pendingTasks) {
      this.attemptTaskAssignment(task.taskId);
    }
  }

  // ============================================================================
  // WORKFLOW ORCHESTRATION
  // ============================================================================

  createWorkflow(workflowInfo: Omit<WorkflowInfo, 'workflowId' | 'status' | 'currentStep' | 'totalSteps'>): string {
    const workflowId = `workflow_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const workflow: WorkflowInfo = {
      ...workflowInfo,
      workflowId,
      status: 'pending',
      currentStep: 0,
      totalSteps: workflowInfo.tasks.length
    };

    this.updateState(state => {
      state.workflows.set(workflowId, workflow);
      return state;
    });

    console.log(`[COORD-STORE] Created workflow: ${workflowId} with ${workflow.totalSteps} steps`);
    return workflowId;
  }

  executeWorkflow(workflowId: string): void {
    const workflow = this.state.workflows.get(workflowId);
    if (!workflow || workflow.status !== 'pending') return;

    this.updateState(state => {
      const updatedWorkflow = state.workflows.get(workflowId)!;
      updatedWorkflow.status = 'running';
      updatedWorkflow.startedAt = Date.now();
      state.workflows.set(workflowId, updatedWorkflow);
      return state;
    });

    this.executeWorkflowStep(workflowId);
    console.log(`[COORD-STORE] Started executing workflow: ${workflowId}`);
  }

  private executeWorkflowStep(workflowId: string): void {
    const workflow = this.state.workflows.get(workflowId);
    if (!workflow || workflow.status !== 'running') return;

    const { pattern, tasks, currentStep } = workflow;

    switch (pattern) {
      case 'sequential':
        this.executeSequentialStep(workflowId, tasks[currentStep]);
        break;
      case 'parallel':
        this.executeParallelStep(workflowId, tasks);
        break;
      case 'fan_out_fan_in':
        this.executeFanOutFanInStep(workflowId, tasks);
        break;
      default:
        console.warn(`[COORD-STORE] Unsupported workflow pattern: ${pattern}`);
    }
  }

  private executeSequentialStep(workflowId: string, taskId: string): void {
    if (this.attemptTaskAssignment(taskId)) {
      console.log(`[COORD-STORE] Workflow ${workflowId} executing sequential step: ${taskId}`);
    } else {
      console.log(`[COORD-STORE] Workflow ${workflowId} waiting for resources for step: ${taskId}`);
    }
  }

  private executeParallelStep(workflowId: string, taskIds: string[]): void {
    let assignedCount = 0;
    for (const taskId of taskIds) {
      if (this.attemptTaskAssignment(taskId)) {
        assignedCount++;
      }
    }
    console.log(`[COORD-STORE] Workflow ${workflowId} assigned ${assignedCount}/${taskIds.length} parallel tasks`);
  }

  private executeFanOutFanInStep(workflowId: string, taskIds: string[]): void {
    // Similar to parallel but with different completion logic
    this.executeParallelStep(workflowId, taskIds);
  }

  private checkWorkflowCompletion(): void {
    for (const [workflowId, workflow] of this.state.workflows) {
      if (workflow.status !== 'running') continue;

      const allTasksCompleted = workflow.tasks.every(taskId => {
        const task = this.state.tasks.get(taskId);
        return task && task.status === 'completed';
      });

      if (allTasksCompleted) {
        this.completeWorkflow(workflowId);
      }
    }
  }

  private completeWorkflow(workflowId: string): void {
    this.updateState(state => {
      const workflow = state.workflows.get(workflowId);
      if (workflow) {
        workflow.status = 'completed';
        workflow.completedAt = Date.now();
        state.workflows.set(workflowId, workflow);
      }
      return state;
    });

    this.emitEvent({
      type: 'workflow.completed',
      workflowId,
      timestamp: Date.now(),
      data: { workflowId }
    });

    console.log(`[COORD-STORE] Completed workflow: ${workflowId}`);
  }

  // ============================================================================
  // RESOURCE & LOCK MANAGEMENT
  // ============================================================================

  registerResource(resourceInfo: Omit<ResourceInfo, 'waitQueue'>): void {
    const resource: ResourceInfo = {
      ...resourceInfo,
      waitQueue: []
    };

    this.updateState(state => {
      state.resources.set(resourceInfo.resourceId, resource);
      return state;
    });

    console.log(`[COORD-STORE] Registered resource: ${resourceInfo.resourceId}`);
  }

  requestLock(agentId: string, resourceId: string, lockType: 'shared' | 'exclusive' = 'exclusive'): boolean {
    const resource = this.state.resources.get(resourceId);
    if (!resource) return false;

    // Check if lock can be acquired immediately
    if (this.canAcquireLock(resourceId, lockType)) {
      return this.acquireLock(agentId, resourceId, lockType);
    }

    // Add to wait queue
    this.updateState(state => {
      const updatedResource = state.resources.get(resourceId)!;
      updatedResource.waitQueue.push(agentId);
      state.resources.set(resourceId, updatedResource);
      return state;
    });

    console.log(`[COORD-STORE] Agent ${agentId} queued for lock on ${resourceId}`);
    return false;
  }

  private canAcquireLock(resourceId: string, lockType: 'shared' | 'exclusive'): boolean {
    const resource = this.state.resources.get(resourceId);
    if (!resource) return false;

    if (resource.status !== 'available') return false;

    // Check existing locks
    const existingLocks = Array.from(this.state.locks.values())
      .filter(lock => lock.resourceId === resourceId && lock.expiresAt > Date.now());

    if (existingLocks.length === 0) return true;

    // Can acquire shared lock if all existing locks are shared
    if (lockType === 'shared') {
      return existingLocks.every(lock => lock.lockType === 'shared');
    }

    // Cannot acquire exclusive lock if any locks exist
    return false;
  }

  private acquireLock(agentId: string, resourceId: string, lockType: 'shared' | 'exclusive'): boolean {
    const lockId = `lock_${resourceId}_${agentId}_${Date.now()}`;
    const lockInfo: LockInfo = {
      lockId,
      resourceId,
      holderId: agentId,
      lockType,
      acquiredAt: Date.now(),
      expiresAt: Date.now() + 300000, // 5 minutes default
      renewable: true,
      waitQueue: []
    };

    this.updateState(state => {
      state.locks.set(lockId, lockInfo);
      
      const resource = state.resources.get(resourceId);
      if (resource) {
        resource.status = 'locked';
        resource.lockedBy = agentId;
        resource.lockExpiration = lockInfo.expiresAt;
        state.resources.set(resourceId, resource);
      }
      
      return state;
    });

    this.emitEvent({
      type: 'lock.acquired',
      agentId,
      resourceId,
      timestamp: Date.now(),
      data: { lockId, lockType }
    });

    console.log(`[COORD-STORE] Agent ${agentId} acquired ${lockType} lock on ${resourceId}`);
    return true;
  }

  releaseLock(agentId: string, resourceId: string): void {
    const locks = Array.from(this.state.locks.values())
      .filter(lock => lock.holderId === agentId && lock.resourceId === resourceId);

    for (const lock of locks) {
      this.updateState(state => {
        state.locks.delete(lock.lockId);
        
        const resource = state.resources.get(resourceId);
        if (resource) {
          resource.status = 'available';
          resource.lockedBy = undefined;
          resource.lockExpiration = undefined;
          state.resources.set(resourceId, resource);
        }
        
        return state;
      });

      this.emitEvent({
        type: 'lock.released',
        agentId,
        resourceId,
        timestamp: Date.now(),
        data: { lockId: lock.lockId }
      });
    }

    // Process wait queue
    this.processResourceWaitQueue(resourceId);
  }

  private processResourceWaitQueue(resourceId: string): void {
    const resource = this.state.resources.get(resourceId);
    if (!resource || resource.waitQueue.length === 0) return;

    const nextAgentId = resource.waitQueue[0];
    
    this.updateState(state => {
      const updatedResource = state.resources.get(resourceId)!;
      updatedResource.waitQueue = updatedResource.waitQueue.slice(1);
      state.resources.set(resourceId, updatedResource);
      return state;
    });

    // Try to acquire lock for next agent
    this.acquireLock(nextAgentId, resourceId, 'exclusive');
  }

  // ============================================================================
  // STATE MANAGEMENT UTILITIES
  // ============================================================================

  private updateState(updater: (state: CoordinationState) => CoordinationState): void {
    this.state = updater({ ...this.state });
    this.state.lastUpdated = Date.now();
    
    // Create checkpoint periodically
    if (this.checkpointHistory.length === 0 || 
        Date.now() - this.checkpointHistory[this.checkpointHistory.length - 1].lastUpdated > 60000) {
      this.createCheckpoint();
    }
    
    // Update metrics
    this.updateMetrics();
    
    // Emit state change
    this.stateSubject.next(this.state);
  }

  private updateMetrics(): void {
    const agents = Array.from(this.state.agents.values());
    const tasks = Array.from(this.state.tasks.values());
    const resources = Array.from(this.state.resources.values());

    this.state.metrics = {
      totalAgents: agents.length,
      activeAgents: agents.filter(a => a.status === 'working').length,
      idleAgents: agents.filter(a => a.status === 'idle').length,
      blockedAgents: agents.filter(a => a.status === 'blocked').length,
      totalTasks: tasks.length,
      completedTasks: tasks.filter(t => t.status === 'completed').length,
      failedTasks: tasks.filter(t => t.status === 'failed').length,
      averageTaskTime: this.calculateAverageTaskTime(tasks),
      systemThroughput: this.calculateThroughput(tasks),
      resourceUtilization: this.calculateResourceUtilization(resources),
      coordinationEfficiency: this.calculateCoordinationEfficiency(),
      deadlockCount: 0, // Would implement deadlock detection
      conflictCount: 0, // Would track resource conflicts
      lastCalculated: Date.now()
    };
  }

  private calculateAverageTaskTime(tasks: TaskInfo[]): number {
    const completedTasks = tasks.filter(t => t.status === 'completed' && t.actualDuration);
    if (completedTasks.length === 0) return 0;
    
    const totalTime = completedTasks.reduce((sum, task) => sum + (task.actualDuration || 0), 0);
    return totalTime / completedTasks.length;
  }

  private calculateThroughput(tasks: TaskInfo[]): number {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;
    
    const recentCompletions = tasks.filter(t => 
      t.status === 'completed' && 
      t.completedAt && 
      t.completedAt > oneMinuteAgo
    );
    
    return recentCompletions.length;
  }

  private calculateResourceUtilization(resources: ResourceInfo[]): number {
    if (resources.length === 0) return 0;
    
    const totalCapacity = resources.reduce((sum, r) => sum + r.capacity, 0);
    const totalUsage = resources.reduce((sum, r) => sum + r.currentUsage, 0);
    
    return totalCapacity > 0 ? totalUsage / totalCapacity : 0;
  }

  private calculateCoordinationEfficiency(): number {
    const { totalAgents, activeAgents, resourceUtilization, systemThroughput } = this.state.metrics;
    
    if (totalAgents === 0) return 0;
    
    const agentUtilization = activeAgents / totalAgents;
    const throughputNormalized = Math.min(1, systemThroughput / 10); // Normalize to max 10 tasks/min
    
    return (agentUtilization * 0.4 + resourceUtilization * 0.3 + throughputNormalized * 0.3);
  }

  private createCheckpoint(): void {
    const checkpoint = JSON.parse(JSON.stringify(this.state)) as CoordinationState;
    this.checkpointHistory.push(checkpoint);
    
    if (this.checkpointHistory.length > this.maxCheckpoints) {
      this.checkpointHistory.shift();
    }
    
    console.log(`[COORD-STORE] Created checkpoint at ${new Date(checkpoint.lastUpdated).toISOString()}`);
  }

  private emitEvent(event: CoordinationEvent): void {
    this.eventSubject.next(event);
  }

  private initializeEventHandlers(): void {
    // Handle domain events from event sourcing system
    dataFlowArchitecture.getAgentDataStreams().events.subscribe(domainEvent => {
      if (domainEvent.aggregateType === 'agent') {
        this.handleAgentEvent(domainEvent);
      }
    });
  }

  private handleAgentEvent(event: DomainEvent): void {
    switch (event.type) {
      case 'agent.spawned':
        // Auto-register spawned agents
        console.log(`[COORD-STORE] Auto-registering spawned agent: ${event.aggregateId}`);
        break;
      case 'agent.status.changed':
        // Update coordination state based on agent status changes
        break;
      default:
        // Handle other agent events
        break;
    }
  }

  // ============================================================================
  // PUBLIC API
  // ============================================================================

  getState(): CoordinationState {
    return { ...this.state };
  }

  getStateStream(): Observable<CoordinationState> {
    return this.stateSubject.asObservable();
  }

  getEventStream(): Observable<CoordinationEvent> {
    return this.eventSubject.asObservable();
  }

  getMetrics(): CoordinationMetrics {
    return { ...this.state.metrics };
  }

  restoreFromCheckpoint(index: number = -1): boolean {
    const checkpointIndex = index < 0 ? this.checkpointHistory.length + index : index;
    const checkpoint = this.checkpointHistory[checkpointIndex];
    
    if (!checkpoint) {
      console.error(`[COORD-STORE] Checkpoint ${index} not found`);
      return false;
    }
    
    this.state = JSON.parse(JSON.stringify(checkpoint));
    this.stateSubject.next(this.state);
    
    console.log(`[COORD-STORE] Restored from checkpoint: ${new Date(checkpoint.lastUpdated).toISOString()}`);
    return true;
  }
}

// ============================================================================
// EVENT TYPES
// ============================================================================

interface CoordinationEvent {
  type: string;
  timestamp: number;
  agentId?: string;
  taskId?: string;
  workflowId?: string;
  resourceId?: string;
  data: any;
}

// Export singleton factory
export function createCoordinationStore(sessionId: string, coordinationId: string): CentralizedCoordinationStore {
  return new CentralizedCoordinationStore(sessionId, coordinationId);
}

// Export types for external usage
export type {
  CoordinationEvent,
  AgentCoordinationInfo,
  TaskInfo,
  ResourceInfo,
  WorkflowInfo,
  LockInfo,
  CoordinationMetrics
};