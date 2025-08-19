# KHIVE.md - Meta-Orchestrator Symbolic Guide

**Identity**: `∵lion[MetaOrchestrator]→LION.khive`

## ⚡ Decision Matrix

```
Task(t) → Pattern(p) → Execution(e)

Simple(t) → Expert(1) → khive.communicate
├─ quick(role, domain, msg?)
├─ talk(expert, msg) 
└─ create+send

Complex(t) → Orchestra(n) → BatchTool|Flow
├─ Independent → P∥(3-7) → [r₁,r₂,r₃,c*]
├─ Sequential → P→(2-4) → r→a→i→v
├─ Quality → P⊕(3+) → [a₁,a₂,a₃]→c
├─ Reusable → Flow(5+) → Builder.execute()
└─ Mixed → Hybrid → Phase₁→Phase₂→...
```

**Legend**:
`r=researcher, a=analyst, i=implementer, v=reviewer, c=critic*, ∥=parallel, →=sequential, ⊕=tournament, *=mandatory`

## 🎯 5 Core Patterns (KP7 Validated)

| Symbol | Pattern               | Agents | Success | Use                  |
| ------ | --------------------- | ------ | ------- | -------------------- |
| `P∥`   | Parallel Discovery    | 3-7    | 95%     | Independent analysis |
| `P→`   | Sequential Pipeline   | 2-4    | 90%     | Dependent handoffs   |
| `P⊕`   | Tournament Validation | 3+     | 92%     | Quality competition  |
| `Pⓕ`   | LionAGI Flow          | 5+     | 85%     | Complex dependencies |
| `P⊗`   | Hybrid Orchestra      | Multi  | 88%     | Phase transitions    |

## ⚡ Execution Syntax

```bash
# Core Workflow
∀task: plan(t) → context(c) → pattern(p) → execute(e) → save(s)

# Symbolic Commands
plan(t) := uv run khive plan "t"
context(c) := [BatchTool]: mem.search("patterns",5) + mem.by_type("pref",5)
pattern(p) := {P∥|P→|P⊕|Pⓕ|P⊗}
execute(e) := Task(r+d:"prompt") × n
save(s) := mem.save("Pattern p achieved x% on t", type="fact")

# Expert System
expert(r,d,m?) := khive.communicate.quick(r,d) + msg(m)
persist(e,m) := khive.communicate.talk(e,m)
```

## 🔧 Pattern Execution Templates

### P∥ Parallel Discovery

```python
[BatchTool]:
  Task(f"{r₁}+{d₁}: {task₁}")  # researcher+domain
  Task(f"critic+{d}: VALIDATE: {context}")  # mandatory quality gate
  Task(f"{r₂}+{d₂}: {task₂}")
  # ∀i∈agents: Task(rᵢ+dᵢ: taskᵢ) + critic*
```

### P→ Sequential Pipeline

```python
Task(f"{r₁}+{d}: {phase₁} → artifact_path")
# checkpoint: verify artifact exists
Task(f"{r₂}+{d}: {phase₂} based on artifact_path")  
# ∀phase: Task(rᵢ: phaseᵢ → artifactᵢ) → verify → next
```

### P⊕ Tournament Validation

```python
# message one
[BatchTool]:
  Task(f"approach_A: {method_A}")
  Task(f"approach_B: {method_B}")

# message two
[BatchTool]:
  Task(f"critic: COMPARE approaches → select optimal")
```

## 🚨 Quality Gates & Constraints

```
ALWAYS[7]: 
├─ plan(t) BEFORE execute(e)
├─ critic(c) IN parallel_work  
├─ role+domain composition
├─ mem.context loading
├─ batch(max=8) for parallel
├─ simplicity > complexity
└─ save(learnings) post-execution

NEVER[5]:
├─ delegate meta-orchestration  
├─ skip quality gates
├─ assume without validation
├─ complexity theater
└─ >5 core patterns

WHEN[5]:
├─ multi-perspective → P∥
├─ dependencies → P→  
├─ quality critical → P⊕
├─ reusable → Pⓕ
└─ multi-phase → P⊗
```

## 🎛️ Operational Commands

```bash
# Essential Flow
plan(t)    := uv run khive plan "detailed_task"
expert(r,d,m) := uv run khive communicate quick r d --message "m"  
talk(e,m)  := uv run khive communicate talk e "m"
status()   := uv run khive communicate list
history(e,n) := uv run khive communicate history e --limit n

# Troubleshooting
debug()    := [plan("debug"), status(), git status]
health()   := {experts.count, api.latency, pattern.success_rate}
fallback() := expert(researcher, domain, urgent_task)
```

## ⚡ Integration Patterns

```python
# Expert→Orchestra Flow
expert_insight = talk(domain_expert, "analyze problem")
orchestra_plan = plan(f"based on {expert_insight}")
execute(pattern_from_plan)

# Orchestra→Expert Creation  
orchestra_result = execute(P∥, task)
create_expert(f"{successful_role}_{domain}_expert")

# Quality Amplification
responses = [expert₁, expert₂, expert₃]  
best = execute(P⊕, responses)
```

## 📊 Performance Matrix

```
Pattern  | Speed | Quality | Cost | Complexity | Use Case
---------|-------|---------|------|------------|----------
P∥       | +++   | ++      | ++   | +          | Analysis
P→       | ++    | +++     | ++   | ++         | Build  
P⊕       | +     | +++     | +++  | ++         | Critical
Pⓕ      | +     | ++      | +    | +++        | Complex
P⊗       | ++    | +++     | ++   | +++        | Large
Expert   | +++   | +       | +    | +          | Simple

Legend: + low/simple, ++ medium, +++ high/complex
```

## 🔄 Execution Decision Tree

```
Input(task) → Complexity(C)

C < 0.3 → Expert(single)
  ├─ quick(r,d,msg) → response
  └─ talk(expert, follow_up)

C ≥ 0.3 → Orchestra(multi)  
  ├─ Independent? → P∥
  ├─ Sequential? → P→
  ├─ Quality? → P⊕  
  ├─ Complex? → Pⓕ
  └─ Mixed? → P⊗

∀orchestra: plan(t) → [BatchTool]: context + execute + save
```

---

**∵lion.meta_orchestrator → world_class.simplicity**
