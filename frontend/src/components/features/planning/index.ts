/**
 * Planning Components Architecture Index
 * 
 * This index provides a centralized export for all planning-related components
 * following software architecture principles:
 * 
 * - Barrel Exports: Clean, organized component access
 * - Component Composition: Expose both high-level and granular components
 * - Backward Compatibility: Export both V1 and V2 implementations
 * - Type Safety: Re-export types for consumer convenience
 */

// Main Components (V2 Architecture)
export { PlanningWizardV2 } from './PlanningWizardV2';
export { ConsensusVisualization } from './ConsensusVisualization';
export { AgentCoordinationPanel } from './AgentCoordinationPanel';

// Decomposed Step Components (Composition Architecture)
export { TaskDefinitionStep } from './components/TaskDefinitionStep';
export { ConsensusStep } from './components/ConsensusStep';
export { ResultsReviewStep } from './components/ResultsReviewStep';
export { ExecutionMonitorStep } from './components/ExecutionMonitorStep';

// Legacy Components (V1 - for backward compatibility)
export { PlanningWizard } from '../workspace/PlanningWizard';

// Hooks and State Management
export { usePlanningWorkflow } from '@/lib/hooks/usePlanningWorkflow';
export { useCoordinationStore } from '@/lib/hooks/useCoordinationState';

// Types (Re-exported for convenience)
export type { 
  PlanningWorkflowState,
  ConsensusRound,
  AgentConsensus,
  PlanningMetrics,
  UsePlanningWorkflowOptions
} from '@/lib/hooks/usePlanningWorkflow';

export type {
  CoordinationMetrics,
  CoordinationState
} from '@/lib/architecture/CentralizedStateManagement';

export type {
  PlanningRequest,
  PlanningResponse,
  CoordinationEvent,
  OrchestrationSession,
  Agent
} from '@/lib/types/khive';

/**
 * Component Architecture Guidelines:
 * 
 * 1. Use PlanningWizardV2 for new implementations
 * 2. Use individual step components for custom workflows
 * 3. Use ConsensusVisualization and AgentCoordinationPanel as standalone components
 * 4. Use hooks for state management in custom implementations
 * 5. PlanningWizard (V1) is maintained for backward compatibility only
 */