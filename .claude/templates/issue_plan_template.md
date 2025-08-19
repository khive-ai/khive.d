---
issue_number: {issue_number}
flow_name: "{flow_name}"
pattern: "{pattern}"
project_phase: "{project_phase}"
is_critical_path: {is_critical_path}
is_experimental: {is_experimental}
blocks_issues: {blocks_issues}
enables_issues: {enables_issues}
dependencies: {dependencies}
workspace_path: ".khive/workspaces/{flow_name}"

# Refinement Configuration (only if pattern is W_REFINEMENT)
{refinement_config}
---

# Issue #{issue_number}: {title}

## System Prompt

{system_prompt}

## Description

{description}

## Planning Instructions

{planning_instructions}

**Notes:** {planning_notes}

## Synthesis Instructions

{synthesis_instructions}

**Output Location:** {output_location}

## Context

{context}
