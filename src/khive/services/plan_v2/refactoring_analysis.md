# Planner Service Modular Refactoring Analysis

## Current Structure (1726 lines - MONOLITHIC)

```
planner_service.py
├── OrchestrationPlanner (1393 lines!) 
│   ├── Configuration Loading (120 lines)
│   ├── Complexity Assessment (150 lines)
│   ├── Role Selection (100 lines)
│   ├── Group Evaluation (200 lines)
│   ├── Consensus Building (400 lines!)
│   ├── Output Formatting (300 lines)
│   ├── Session Management (100 lines)
│   └── Helper Methods (23 methods!)
└── PlannerService (260 lines - wrapper)
```

## Proposed Modular Architecture

```
services/plan/
├── __init__.py                     # Public API exports
├── planner_service.py              # Main service (thin orchestrator ~200 lines)
├── core/
│   ├── __init__.py
│   ├── models.py                   # Data models (existing)
│   ├── config.py                   # Configuration management (~150 lines)
│   └── session.py                  # Session/artifact management (~150 lines)
├── evaluation/
│   ├── __init__.py
│   ├── group_evaluator.py          # Group assessment engine (~300 lines)
│   ├── agent_configs.py            # Agent perspective definitions (~200 lines)
│   └── complexity_assessor.py      # Complexity assessment logic (~200 lines)
├── consensus/
│   ├── __init__.py
│   ├── consensus_builder.py        # Consensus building logic (~400 lines)
│   ├── role_selector.py            # Role selection and scoring (~150 lines)
│   └── pattern_selector.py         # Pattern recommendation (~100 lines)
├── output/
│   ├── __init__.py
│   ├── formatter.py                # Output formatting (~200 lines)
│   ├── execution_plan.py           # Execution plan generation (~150 lines)
│   └── templates.py                # Output templates (~100 lines)
└── utils/
    ├── __init__.py
    ├── cost_tracker.py             # Existing cost tracking
    └── timeout_manager.py          # Timeout management (~100 lines)
```

## Key Benefits

1. **Separation of Concerns**: Each module has a single responsibility
2. **Testability**: Can unit test each component independently
3. **Maintainability**: Changes to consensus logic don't affect evaluation
4. **Reusability**: Can use group evaluator in other services
5. **Clarity**: Clear module boundaries and interfaces

## Module Interfaces

### 1. Group Evaluator Module
```python
class GroupEvaluator:
    async def evaluate_request(self, request: str, configs: List[AgentConfig]) -> List[Evaluation]
    async def run_concurrent_evaluations(self, request: str) -> List[Dict]
```

### 2. Consensus Builder Module
```python
class ConsensusBuilder:
    def build_consensus(self, evaluations: List[Evaluation]) -> ConsensusResult
    def analyze_meta_insights(self, evaluations: List[Evaluation]) -> str
    def generate_execution_plan(self, consensus: ConsensusResult) -> str
```

### 3. Output Formatter Module
```python
class OutputFormatter:
    def format_consensus_report(self, consensus: ConsensusResult) -> str
    def format_execution_plan(self, plan: ExecutionPlan) -> str
    def format_json_response(self, response: PlannerResponse) -> str
```

## Migration Strategy

### Phase 1: Extract Core Components (Day 1)
- [ ] Create module structure
- [ ] Extract models and config
- [ ] Setup module interfaces

### Phase 2: Extract Evaluation Engine (Day 2)
- [ ] Move group evaluation logic
- [ ] Extract agent configurations
- [ ] Move complexity assessment

### Phase 3: Extract Consensus Building (Day 3)
- [ ] Move consensus logic
- [ ] Extract role selection
- [ ] Move pattern selection

### Phase 4: Extract Output Formatting (Day 4)
- [ ] Move formatting logic
- [ ] Extract execution plan generation
- [ ] Create output templates

### Phase 5: Integration & Testing (Day 5)
- [ ] Wire modules together
- [ ] Ensure identical output
- [ ] Performance testing

## Backwards Compatibility

The refactored service will maintain 100% API compatibility:
```python
# Old usage (unchanged)
service = PlannerService()
response = await service.handle_request(request)

# Internal changes are transparent to users
```

## Performance Considerations

- Module lazy loading for faster startup
- Shared OpenAI client instance
- Cached configuration loading
- Concurrent evaluation preserved

## Testing Strategy

Each module gets its own test file:
```
tests/services/plan/
├── test_group_evaluator.py
├── test_consensus_builder.py
├── test_complexity_assessor.py
├── test_output_formatter.py
└── test_integration.py      # End-to-end tests
```