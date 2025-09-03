# KHIVE Planning System

Multi-round consensus planning system for intelligent agent orchestration.
Provides automated complexity analysis, pattern selection, and human guidance
overrides for predictable, reliable agent coordination.

## Overview

The KHIVE planning system transforms task descriptions into structured
multi-agent execution plans through:

1. **Complexity Analysis** - Automated scoring using mathematical models
2. **Pattern Selection** - Choose optimal orchestration strategies
3. **Agent Allocation** - Assign specialized role+domain combinations
4. **Human Guidance** - Override decisions when needed for control
5. **Consensus Building** - Multi-round refinement with judge validation

## Quick Start

```bash
# Basic planning
uv run khive plan "implement user authentication system"

# Force simple execution (single expert)
uv run khive plan "complex distributed system" --simple

# Force complex orchestration  
uv run khive plan "add health endpoint" --complex

# Specify orchestration pattern
uv run khive plan "build microservices" --pattern "P→"

# Set exact agent count
uv run khive plan "create dashboard" --agents 3
```

## Human Guidance Flags

### Complexity Override

- `--simple` - Force Expert pattern (1 agent, bypass orchestration)
- `--complex` - Force multi-agent orchestration (5-8 agents)
- `--pattern <PATTERN>` - Force specific orchestration pattern

### Supported Patterns

- `Expert` - Single expert agent (1 agent)
- `P∥` - Parallel execution (3-5 agents)
- `P→` - Sequential refinement (2-4 agents)
- `P⊕` - Tournament consensus (3-6 agents)

### Agent Count Control

- `--agents <N>` - Target specific total agent count

## Architecture

### Core Components

**Complexity Scorer** (`complexity.py`)

- Sigmoid-based mathematical scoring
- Keyword analysis and feature extraction
- Pattern selection logic
- Expert escalation detection

**Generation Pipeline** (`generators.py`)

- **DecomposerEngine** - Break tasks into phases
- **StrategistEngine** - Assign agents and coordination
- **RefinerEngine** - Validate and merge plans
- **SelfConsistencyEngine** - Stabilize across generations

**Consensus System** (`consensus.py`)

- Pairwise comparisons between candidates
- Bradley-Terry-Luce ranking algorithm
- Multi-round convergence detection

**Judge System** (`judges.py`)

- Multi-criteria evaluation (feasibility, risk, coverage)
- Calibrated reliability tracking
- Cross-validation between judges

**Planning Service** (`service.py`)

- Main orchestration controller
- Human guidance integration
- Timeout management and graceful degradation
- Global agent cap enforcement

### Data Models (`models.py`)

```python
# Core request/response
PlannerRequest(task_description, context, time_budget_seconds)
PlannerResponse(success, summary, complexity, phases, spawn_commands)

# Phase structure  
TaskPhase(name, description, agents, coordination_strategy, quality_gate)
AgentRecommendation(role, domain, priority, reasoning)

# Internal consensus
DecompositionCandidate, StrategyCandidate, JudgeScore, ConsensusResult
```

## Configuration

**Main Config** (`models.yaml`)

```yaml
generators:
  - provider: "openrouter"
    model: "google/gemini-2.0-flash-001"
    role: "decomposer"
    temps: [0.2, 0.5, 0.8]

budgets:
  time_seconds: 60 # Total planning time
  cost_usd: 0.01 # Budget limit
  tokens_per_candidate: 4000

orchestration:
  max_rounds: 1 # Consensus rounds
  candidates_per_round: 5 # Plans per round
  convergence_threshold: 0.15
```

## Examples

### Simple Task (Expert Pattern)

```bash
$ uv run khive plan "add health check endpoint"

🚀 Starting Multi-Round Consensus Planning
⚡ Early Expert Bypass: Task suitable for single expert (complexity: 0.08)
✅ Expert assignment completed in 0.0s

🚀 Agent Spawn Commands:
   Task("implementer+software-architecture: add health check endpoint")
```

### Complex Task (Multi-Agent)

```bash
$ uv run khive plan "implement distributed caching layer with Redis"

🚀 Starting Multi-Round Consensus Planning (60.0s budget)
📊 Initial Complexity Score: 0.31
🧪 Refined Complexity: complex | Pattern: P→
✅ Planning completed in 33.4s - 8 agents across 5 phases

Phase 1: Redis Cluster Deployment - architect+distributed-systems, implementer+software-architecture
Phase 2: Connection Pooling Implementation - implementer+async-programming  
Phase 3: Cache Invalidation Strategies - architect+software-architecture, implementer+async-programming
Phase 4: Monitoring Dashboard - implementer+distributed-systems
Phase 5: Failover Implementation - architect+software-architecture, implementer+async-programming
```

### Human Guidance Override

```bash
$ uv run khive plan "simple task" --complex --agents 4

🎯 Human Override: Target agents set to 4
🧪 Refined Complexity: medium | Pattern: P∥
📉 Trimmed agents from 10 to 4 (pattern: P∥)
```

## Integration

### CLI Integration (`khive_plan.py`)

- Argument parsing and validation
- Human guidance processing
- GitHub issue integration (`--issue 123`)
- JSON output mode (`--json`)

### Spawn Commands

Generated commands integrate with KHIVE coordination:

```bash
Task("architect+distributed-systems: Phase Name | coordination_strategy | quality_gate | coordination_id")
```

### Cost Tracking (`cost_tracker.py`)

- Token usage monitoring
- Cost estimation and budgets
- LionAGI integration for usage extraction

## Development

### Testing

```bash
# Run planning system tests
uv run pytest tests/test_human_guidance.py -v

# Test CLI functionality  
uv run pytest tests/test_planning_cli.py -v

# Full integration tests
uv run pytest tests/services/plan/ -v
```

### Key Design Principles

1. **Trust But Verify** - Human guidance overrides when AI detection fails
2. **Graceful Degradation** - Timeouts and fallbacks prevent failures
3. **Global Agent Caps** - Prevent over-orchestration regardless of generation
4. **Pattern Consistency** - Predictable orchestration strategies
5. **Cost Awareness** - Budget limits and usage tracking

### Configuration Tuning

**Timeout Management:**

- Decomposition: 20s max per phase
- Strategy: 20s max per phase
- Judgments: 15s max per phase
- Refinement: 10s max per phase

**Complexity Thresholds:**

- `< 0.3` → Expert (1 agent)
- `0.3-0.5` → Medium (2-4 agents)
- `0.5-0.8` → Complex (5-8 agents)
- `> 0.8` → Very Complex (5-8 agents)

**Agent Limits by Pattern:**

- Expert: 1 agent exactly
- P∥ (Parallel): 3-5 agents
- P→ (Sequential): 2-4 agents
- P⊕ (Tournament): 3-6 agents

## Files Reference

| File                | Purpose                                 |
| ------------------- | --------------------------------------- |
| `khive_plan.py`     | CLI interface and main entry point      |
| `service.py`        | Core planning orchestration service     |
| `models.py`         | Pydantic data models and types          |
| `models.yaml`       | Configuration for models and budgets    |
| `complexity.py`     | Mathematical complexity scoring         |
| `generators.py`     | LionAGI candidate generation pipeline   |
| `consensus.py`      | Multi-round consensus algorithms        |
| `judges.py`         | Plan evaluation and scoring             |
| `cost_tracker.py`   | Usage monitoring and budget enforcement |
| `HUMAN_GUIDANCE.md` | Detailed human guidance documentation   |

## Troubleshooting

**Planning Timeouts:**

- Increase `time_seconds` in `models.yaml`
- Reduce `candidates_per_round` for faster execution

**Over-Engineering:**

- Use `--simple` flag for straightforward tasks
- Check complexity scorer keywords in `complexity.py`

**Under-Engineering:**

- Use `--complex` flag for sophisticated tasks
- Verify task description includes technical terms

**Agent Count Issues:**

- Use `--agents N` for exact control
- Check global agent limits in `service.py`
