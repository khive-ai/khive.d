# Feature Components

This directory contains specialized feature components for the Khive
orchestration system.

## Agent Composer Studio

The Agent Composer Studio (`agent-composer-studio.tsx`) provides an interactive
MVP environment for composing and testing agents before deployment.

### Key Features

- **Role/Domain Selection**: Interactive selection of behavioral roles and
  domain expertise
- **Capability Testing**: Real-time testing of agent capabilities based on
  role/domain combinations
- **Interactive Preview**: Live preview of expected agent capabilities
- **Task Context Validation**: Context-aware capability validation

### Usage

```tsx
import { AgentComposerStudio } from "@/components/feature/agent-composer-studio";

function MyPage() {
  const handleAgentComposed = (composition) => {
    // Handle composed agent
    console.log("Agent composed:", composition);
  };

  return <AgentComposerStudio onAgentComposed={handleAgentComposed} />;
}
```

### Integration

The Agent Composer Studio is integrated into the dashboard at
`/dashboard/composer` and provides:

1. **Agent Definition Form**: Select role, domain, and provide task context
2. **Capability Preview**: Real-time preview of agent capabilities
3. **Testing Interface**: Mock capability testing with realistic scenarios
4. **Composition Output**: Structured agent definition ready for deployment

### Architecture

The component follows agentic-systems domain expertise patterns:

- **Role-based Capabilities**: Different roles (researcher, architect,
  implementer) have specific capability tests
- **Domain Augmentation**: Domain expertise (software-architecture,
  agentic-systems) adds specialized knowledge
- **Multi-agent Coordination Awareness**: Testing includes coordination patterns
  and orchestration strategies

### Future Enhancements

- Real capability testing against live systems
- Integration with actual deployment pipeline
- Advanced configuration options
- Collaboration features for team-based agent composition

## Other Feature Components

- **Agent Spawner** (`agent-spawner.tsx`): Full orchestration interface for
  spawning multiple agents
- **Agent Spawning Form** (`agent-spawning-form.tsx`): Advanced form for
  detailed agent configuration
- **Session Monitor** (`session-monitor.tsx`): Real-time session monitoring
- **Agent Status** (`agent-status.tsx`): Individual agent status display

## Navigation Integration

To add the Composer Studio to navigation, add this item to the `navigationItems`
array in the dashboard layout:

```tsx
{
  label: 'Composer',
  path: '/dashboard/composer',
  icon: <ScienceIcon />,
}
```

Note: Import `Science as ScienceIcon` from '@mui/icons-material'.
