---
issue_num: 58
flow_name: "58_database_schema_design"
pattern: "W_REFINEMENT"
project_phase: "exploration"
is_critical_path: true
is_experimental: false
blocks_issues: [70]
enables_issues: [61]
dependencies: []
workspace_path: ".khive/workspaces/58_database_schema_design"

# Refinement Configuration
refinement_enabled: true
refinement_desc: "Refine schema to avoid major structural issues that would require rework"
critic_domain: "database-design"
gate_instruction: "Evaluate if schema covers basic requirements and avoids obvious structural problems. Foundation level - just needs to work, not be perfect."
gates: ["design"]
---

# Issue #58: Database Schema Design

## System Prompt

You are orchestrating simple database schema design for khive dashboard
foundation.

## Description

Design PostgreSQL database schema for khive dashboard

## Planning Instructions

Plan simple database schema design: Focus on core entities, relationships, and
basic constraints. Keep it pragmatic - no need for perfect normalization.

Target: Working schema that can be implemented in issue #70.

**Notes:**

- This is FOUNDATION work - focus on getting basics working, not production
  perfection
- Avoid over-engineering - we can iterate and improve later
- If multiple agents work together, ensure they build on each other's work

## Synthesis Instructions

Synthesize database schema design:

1. ER diagram with core entities (users, projects, dashboards, metrics)
2. Basic table definitions with primary keys and foreign keys
3. Simple indexing strategy for common queries
4. Basic RLS policy ideas (don't over-engineer)

**Output Location:**

- Consolidate agent work from workspace:
  `.khive/workspaces/58_database_schema_design`
- Place database files in `apps/dashboard/backend/database/`
- Place API files in `apps/dashboard/backend/src/`
- Keep exploration notes in workspace, not in main codebase

## Context

khive dashboard foundation - Simple PostgreSQL schema to get started
