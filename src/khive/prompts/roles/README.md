# Agent Specifications

This directory contains the core role specifications for the KB system's
autonomous agents.

## Overview

Each agent represents a distinct functional role with specific capabilities,
tools, and decision-making patterns. Agents are designed to be composed with
domain expertise at runtime, allowing flexible specialization without creating
hundreds of specific agent types.

## Agent Roles

### Information Pipeline

- **`researcher.md`** - Information gatherer from all sources
- **`analyst.md`** - Information processor and experimenter
- **`commentator.md`** - Knowledge explainer and documenter

### Creation & Building

- **`innovator.md`** - Possibility creator and paradigm breaker
- **`architect.md`** - System designer and structure creator
- **`implementer.md`** - Solution builder and code writer

### Quality & Validation

- **`critic.md`** - Flaw finder and assumption challenger
- **`tester.md`** - Empirical validator through testing
- **`reviewer.md`** - Quality improver through suggestions

### Planning & Coordination

- **`strategist.md`** - Path optimizer and resource allocator

## How to Use

Agents are not used directly. Instead, they are composed with domain expertise
at runtime:

```bash
# Compose agent with single domain
uv run khive compose researcher -d security

# Compose with multiple domains
uv run khive compose analyst -d python,performance
```

## Agent File Structure

Each agent specification includes:

1. **Identity** - Core metadata and capabilities
2. **Key Differentiator** - What makes this role unique
3. **Role** - Overall purpose and function
4. **Unique Characteristics** - Behavioral traits
5. **Decision Logic** - How the agent makes decisions
6. **Output Focus** - What the agent produces
7. **Relationships** - How it works with other agents

## Key Role Distinctions

### Researcher vs Analyst

- **Researcher**: Gathers information (outward focus)
- **Analyst**: Processes information (inward focus)

### Reviewer vs Critic vs Tester

- **Reviewer**: Improves work constructively
- **Critic**: Finds flaws adversarially
- **Tester**: Proves things work empirically

### Innovator vs Implementer

- **Innovator**: Creates possibilities ("what if?")
- **Implementer**: Builds solutions ("how to?")

### Strategist vs Architect

- **Strategist**: Plans sequences and timing
- **Architect**: Designs structures and interfaces

## Domain Composition

Agents gain specialized expertise by loading domain modules from `../domains/`:

- Security, Python, Rust, Machine Learning, etc.
- Multiple domains can be combined for cross-cutting expertise
- Domain knowledge augments base capabilities

## See Also

- `/docs/agent-framework.md` - Complete composition architecture
- `../guides/agent-orchestration-guide.md` - How to select and deploy agents
- `../domains/` - Available domain expertise modules
- `../../scripts/compose_agent.py` - Agent composition script
