# Task Flow Visualizer MVP - Integration Guide

**Author:** commentator_agentic-systems\
**Version:** MVP\
**Created:** 2025-09-02

## Overview

The Task Flow Visualizer MVP provides interactive workflow diagrams and agent
activity highlighting for multi-agent orchestration. This document explains the
integration architecture, component relationships, and usage patterns.

## Component Architecture

### Core Components Created

#### 1. WorkflowPatternsGuide (`workflow-patterns-guide.tsx`)

**Purpose:** Educational component explaining multi-agent coordination patterns\
**Integration:** Sidebar or modal overlay in the main workflow visualizer

**Key Features:**

- Interactive accordion interface for coordination patterns
- Agent activity state legend
- Quality gates reference
- Performance optimization tips

**Data Dependencies:**

- Static pattern definitions from agentic-systems domain expertise
- Real-time agent status for activity legend

#### 2. AgentActivityHighlight (`agent-activity-highlight.tsx`)

**Purpose:** Real-time visualization of agent status and performance metrics\
**Integration:** Primary dashboard widget or workflow diagram overlay

**Key Features:**

- Live agent status monitoring (active/idle/blocked)
- Progress indicators for active tasks
- Performance metrics display
- Role-based color coding
- Activity pulse animations

**Data Dependencies:**

- `useAgents()` hook for agent status
- `useCoordinationMetrics()` hook for performance data
- Real-time updates via WebSocket (future enhancement)

### 3. TaskFlowVisualizer (`task-flow-visualizer.tsx`)

**Purpose:** Main interactive workflow diagram using Reactflow\
**Status:** Being implemented by architect_software-architecture\
**Integration Point:** Central orchestration visualization

## Integration Patterns

### 1. Orchestration Center Integration

```tsx
// In /app/(dashboard)/orchestration/page.tsx
import { WorkflowPatternsGuide } from "@/components/feature/workflow-patterns-guide";
import { AgentActivityHighlight } from "@/components/feature/agent-activity-highlight";
import { TaskFlowVisualizer } from "@/components/feature/task-flow-visualizer";

export default function OrchestrationCenterPage() {
  return (
    <Grid container spacing={3}>
      {/* Main workflow visualization */}
      <Grid item xs={12} lg={8}>
        <TaskFlowVisualizer sessionId={currentSession?.id} />
      </Grid>

      {/* Agent activity sidebar */}
      <Grid item xs={12} lg={4}>
        <AgentActivityHighlight
          sessionId={currentSession?.id}
          onAgentClick={handleAgentSelection}
          highlightedAgents={selectedAgents}
        />
        <WorkflowPatternsGuide compact />
      </Grid>
    </Grid>
  );
}
```

### 2. Modal/Drawer Integration

```tsx
// Patterns guide as expandable help drawer
<Drawer anchor="right" open={showPatternsGuide}>
  <WorkflowPatternsGuide />
</Drawer>

// Agent details modal
<Dialog open={showAgentDetails}>
  <AgentActivityHighlight 
    compact={false}
    sessionId={selectedSession}
    highlightedAgents={[selectedAgentId]}
  />
</Dialog>
```

## Data Flow Architecture

### Agent Status Updates

```
API Hooks → Agent Activity Highlight → Visual Updates
    ↓
Coordination Metrics → Performance Display → Real-time Refresh
    ↓
WebSocket Events → Activity Animations → Status Changes
```

### Coordination Pattern Context

```
Static Pattern Data → Workflow Patterns Guide → Educational Content
    ↓
Current Session Strategy → Pattern Highlighting → Context Display
    ↓  
User Selection → Detailed Explanations → Interactive Learning
```

## Styling and Theming

### Design Consistency

- **Material-UI Components:** All components use MUI for consistency
- **Color Scheme:** Role-based colors for agent identification
- **Animation:** Subtle pulse effects for active states
- **Responsive:** Grid layouts adapt to screen sizes

### Role Color Mapping

```tsx
const ROLE_COLORS = {
  researcher: "#1976d2", // Blue
  analyst: "#388e3c", // Green
  architect: "#7b1fa2", // Purple
  implementer: "#f57c00", // Orange
  reviewer: "#c2185b", // Pink
  tester: "#0097a7", // Cyan
  critic: "#d32f2f", // Red
  commentator: "#5e35b1", // Deep Purple
  orchestrator: "#424242", // Grey
};
```

### Activity State Colors

```tsx
const ACTIVITY_STATES = {
  active: "#4caf50", // Green with pulse
  idle: "#ff9800", // Orange
  blocked: "#f44336", // Red with pulse
  completed: "#2196f3", // Blue
};
```

## API Integration

### Required Hooks

```tsx
// Agent data and real-time updates
const { data: agents, refetch } = useAgents(sessionId);

// System performance metrics
const { data: metrics } = useCoordinationMetrics();

// Session and orchestration data
const { data: sessions } = useSessions();

// Plan data for workflow visualization
const { data: plan } = usePlan(sessionId);
```

### Mock Data Structure (MVP)

```tsx
interface AgentActivityData {
  id: string;
  role: string;
  domain: string;
  status: "active" | "idle" | "blocked";
  currentTask?: string;
  progress?: number; // 0-100
  artifactsCreated?: number;
  timeActive?: number; // minutes
  efficiency?: number; // percentage
  lastActivity?: string; // ISO timestamp
}
```

## Coordination Protocol Integration

### File Coordination

- Components respect the coordination protocol
- Agent activity updates trigger coordination events
- File locks prevent editing conflicts

### Event Handling

```tsx
// Agent selection coordination
const handleAgentClick = (agent: AgentActivityData) => {
  // Update highlighted agents in workflow diagram
  setHighlightedAgents([agent.id]);

  // Trigger coordination event
  onAgentSelection?.(agent);

  // Update URL state for deep linking
  router.push(`/orchestration?agent=${agent.id}`);
};
```

## Performance Considerations

### Real-time Updates

- **Refresh Interval:** 15 seconds for agent status
- **Progressive Enhancement:** Basic view works without WebSocket
- **Batch Updates:** Minimize API calls during active orchestration

### Component Optimization

- **Memoization:** useMemo for expensive calculations
- **Virtual Scrolling:** For large agent lists (future enhancement)
- **Lazy Loading:** Activity details loaded on demand

## Testing Strategy

### Component Tests

```bash
# Test workflow patterns guide
npm test workflow-patterns-guide.test.tsx

# Test agent activity highlighting  
npm test agent-activity-highlight.test.tsx

# Integration tests
npm test task-flow-integration.test.tsx
```

### Test Coverage Areas

- Pattern selection and display
- Agent status state changes
- Real-time update handling
- Accessibility compliance
- Mobile responsiveness

## Future Enhancements

### Phase 2 Features

1. **WebSocket Integration** - Real-time status updates
2. **Agent Communication Flow** - Message passing visualization
3. **Performance Analytics** - Historical trend analysis
4. **Workflow Templates** - Saved coordination patterns
5. **Agent Debugging Tools** - Error state analysis

### Accessibility Improvements

- Screen reader support for workflow diagrams
- Keyboard navigation for interactive elements
- High contrast mode support
- Voice command integration

## Usage Examples

### Basic Integration

```tsx
import {
  AgentActivityHighlight,
  WorkflowPatternsGuide,
} from "@/components/feature";

<Box>
  <AgentActivityHighlight
    sessionId="session-123"
    compact={false}
    onAgentClick={handleAgentSelection}
  />
  <WorkflowPatternsGuide compact />
</Box>;
```

### Advanced Orchestration Dashboard

```tsx
const [selectedPattern, setSelectedPattern] = useState("fan_out_synthesize");
const [highlightedAgents, setHighlightedAgents] = useState<string[]>([]);

<Grid container spacing={3}>
  <Grid item xs={12} lg={9}>
    <TaskFlowVisualizer
      sessionId={sessionId}
      coordinationPattern={selectedPattern}
      highlightedAgents={highlightedAgents}
    />
  </Grid>

  <Grid item xs={12} lg={3}>
    <Stack spacing={2}>
      <AgentActivityHighlight
        sessionId={sessionId}
        onAgentClick={(agent) => setHighlightedAgents([agent.id])}
        highlightedAgents={highlightedAgents}
      />

      <WorkflowPatternsGuide
        onPatternSelect={setSelectedPattern}
        activePattern={selectedPattern}
      />
    </Stack>
  </Grid>
</Grid>;
```

## Deployment Notes

### Dependencies Added

- `reactflow: ^11.11.4` - For workflow diagram visualization
- `@mui/material: ^7.3.2` - UI components
- `@mui/icons-material: ^7.3.2` - Icons

### Build Considerations

- Components are tree-shakeable
- No external CSS dependencies beyond MUI
- TypeScript definitions included

---

**Integration Status:** MVP Complete - Ready for Testing\
**Next Steps:** Integration with main TaskFlowVisualizer component by architect
team
