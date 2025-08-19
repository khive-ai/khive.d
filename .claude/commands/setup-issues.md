# Setup Issues Command

**Purpose**: Automated GitHub issues and orchestration flow creation for
comprehensive project workflows

**Category**: Project Management **Complexity**: Advanced **Dependencies**:
GitHub CLI (gh), file system access, khive orchestration system

## Quick Start

```bash
# Create testing workflow
/project:setup-issues testing_v5

# Create feature workflow with context
/project:setup-issues user_auth_system --context="Implement OAuth2 authentication with JWT tokens"

# Create architecture review workflow
/project:setup-issues microservices_design --context="Design event-driven microservices architecture"
```

## Synopsis

```bash
/project:setup-issues <flow_name> [--context="additional context"]
```

## Description

This command automates the complete workflow creation process from initial
context gathering through GitHub issue creation to fully configured khive
orchestration flows. It streamlines project setup by creating comprehensive
issue plans, dependency management, and executable workflows.

## Process Overview

**Target Output**: Complete orchestration flow with 3-10 GitHub issues and
executable runner

### 1. Context Gathering

- Interactive user prompts for project goals and requirements
- Automatic extraction from recent session summaries
- Integration with existing conversation context
- Analysis of work type (testing, feature, architecture, bugfix)

### 2. Issue Proposal & Confirmation

- AI-powered issue generation based on context and work type
- Interactive issue review and editing capabilities
- Dependency analysis and critical path identification
- Pattern selection (FANOUT vs W_REFINEMENT)

### 3. GitHub Integration

- Automated GitHub issue creation using gh CLI
- Intelligent labeling based on priority and pattern
- Issue number extraction and tracking
- Error handling and rollback capabilities

### 4. Flow Structure Creation

- Directory structure setup in `flows/{flow_name}/`
- Issue plans directory with proper organization
- Python package structure with `__init__.py` files
- Workspace path configuration

### 5. Issue Plan Generation

- Template-based markdown file creation for each issue
- YAML frontmatter with orchestration metadata
- Dependency chain and execution pattern configuration
- System prompts and planning instructions

### 6. Runner Creation

- Dynamic `runner.py` generation based on issue sequence
- Proper dependency ordering and execution configuration
- Integration with khive IssueRunner system
- Async execution setup with concurrency control

### 7. Verification & Validation

- Automated issue plan validation using `.claude/scripts/verify_issue_plans.py`
- YAML frontmatter structure verification against required fields
- Template compliance checking for orchestration parser compatibility
- Execution readiness confirmation with detailed error reporting

## MANDATORY: Template Integration

**CRITICAL**: This command MUST use the official issue plan template located at:
`.claude/templates/issue_plan_template.md`

### Required Template Structure

```yaml
---
issue_num: {issue_num}
flow_name: "{flow_name}"
pattern: "{pattern}"
project_phase: "{project_phase}"
is_critical_path: {is_critical_path}
is_experimental: {is_experimental}
blocks_issues: {blocks_issues}
enables_issues: {enables_issues}
dependencies: {dependencies}
workspace_path: ".khive/workspaces/{flow_name}"

# Refinement Configuration (W_REFINEMENT only)
refinement_enabled: true
refinement_desc: "Refinement description"
critic_domain: "domain-expertise"
gate_instruction: "Quality gate instruction"
gates: ["gate1", "gate2"]
---

# Issue #{issue_num}: {title}

## System Prompt
{orchestration_context}

## Description
{issue_description}

## Planning Instructions
{multi_agent_planning_guidance}

## Synthesis Instructions
{deliverable_consolidation_guidance}

## Context
{flow_context}
```

## Issue Generation Strategies

### Testing Workflows

- Test infrastructure setup (W_REFINEMENT, critical path)
- Unit testing implementation (FANOUT, high priority)
- Integration testing (FANOUT, medium priority)
- Security testing suite (W_REFINEMENT if security-critical)
- Performance benchmarking (FANOUT, medium priority)

### Feature Development

- Architecture design (W_REFINEMENT, critical path)
- Core implementation (FANOUT, high priority)
- Testing and validation (FANOUT, medium priority)
- Documentation and deployment (FANOUT, low priority)

### Architecture Reviews

- Research and analysis (FANOUT, high priority)
- Design and specification (W_REFINEMENT, critical path)
- Validation and refinement (FANOUT, medium priority)
- Implementation planning (FANOUT, medium priority)

### Bug Fixes

- Root cause analysis (FANOUT, high priority)
- Solution design (W_REFINEMENT if complex)
- Implementation and testing (FANOUT, high priority)
- Validation and deployment (FANOUT, medium priority)

## Interactive Features

### Context Gathering Prompts

1. **Main Goal**: Primary problem or objective to solve
2. **Work Type**: testing, feature, architecture, bugfix, or general
3. **Requirements**: Specific constraints, technologies, or standards
4. **Priority Level**: high, medium, or low overall priority

### Issue Editing Commands

- `add`: Create new issue interactively
- `remove <num>`: Delete issue by number
- `edit <num>`: Modify existing issue
- `done`: Proceed with current issue set
- `cancel`: Abort setup process

## Output Structure

```
flows/{flow_name}/
├── __init__.py
├── runner.py                    # Executable orchestration runner
├── issues/
│   ├── __init__.py
│   ├── {issue_num}_{descriptive_name}.md  # e.g., 185_cli_command_testing.md
│   ├── {issue_num}_{descriptive_name}.md  # e.g., 186_agent_composer_testing.md
│   └── ...
└── README.md                   # Flow documentation (auto-generated)
```

## Integration Points

### GitHub Issues

- Automatic creation with proper labeling
- Critical path and pattern-based organization
- Dependency tracking in issue descriptions
- Link generation for orchestration tracking

### Khive Orchestration

- Issue plan validation against orchestration parser
- Proper workspace path configuration
- Agent composition integration ready
- Quality gate configuration for refinement patterns

### Verification System

- **Script Location**: `.claude/scripts/verify_issue_plans.py`
- **Validation Scope**: All generated `.md` files in `flows/{flow_name}/issues/`
- **YAML Structure**: Validates required fields, types, and pattern-specific
  requirements
- **Parser Compatibility**: Ensures compatibility with
  `khive.services.orchestration.issue_parser`
- **Error Reporting**: Detailed validation errors and warnings with line numbers
- **Execution**: Automatically run after issue plan generation

## Examples

### Testing Strategy Setup

```bash
/project:setup-issues comprehensive_testing --context="Zero test coverage, need full TDD implementation"
```

**Generated Issues**:

1. Test Infrastructure Setup (W_REFINEMENT, critical)
2. CLI Testing Suite (FANOUT, high)
3. Security Testing (W_REFINEMENT, high)
4. Integration Testing (FANOUT, medium)
5. Performance Benchmarks (FANOUT, medium)

### Feature Development

```bash
/project:setup-issues payment_gateway --context="Stripe integration with webhook handling"
```

**Generated Issues**:

1. Payment Architecture Design (W_REFINEMENT, critical)
2. Stripe SDK Integration (FANOUT, high)
3. Webhook Processing System (FANOUT, high)
4. Error Handling & Retry Logic (FANOUT, medium)
5. Testing & Validation Suite (FANOUT, medium)

### Architecture Review

```bash
/project:setup-issues event_sourcing --context="Migrate from CRUD to event-sourcing architecture"
```

**Generated Issues**:

1. Event Sourcing Research (FANOUT, high)
2. Migration Strategy Design (W_REFINEMENT, critical)
3. Event Store Implementation (FANOUT, high)
4. Legacy System Integration (FANOUT, medium)
5. Performance Impact Analysis (FANOUT, medium)

## Best Practices

### Flow Naming

- Use descriptive, project-relevant names
- Include version numbers for iterations (v2, v3)
- Separate concerns (testing_v4, auth_system, db_migration)

### Context Provision

- Be specific about technical requirements
- Include relevant technologies and constraints
- Mention existing system dependencies
- Specify performance or security requirements

### Issue Dependencies

- Foundation work should block dependent issues
- Testing issues typically depend on implementation
- Documentation can run parallel to development
- Validation should follow implementation

## Error Handling

### GitHub CLI Issues

- Verify `gh auth status` before running
- Check repository access permissions
- Handle rate limiting gracefully
- Provide clear error messages for CLI failures

### Template Validation

- Verify template files exist before generation
- Validate YAML frontmatter structure
- Check required fields presence
- Report validation failures clearly

### File System Operations

- Ensure directory creation permissions
- Handle existing flow name conflicts
- Validate file write permissions
- Clean up on failure scenarios

## Verification Details

### Manual Verification

```bash
# Verify specific flow
python .claude/scripts/verify_issue_plans.py flows/v4tdd/issues/

# Actual output (tested):
# Validating 185_cli_command_testing.md...
#   ✅ Valid
# Validating 186_agent_composer_testing.md...  
#   ✅ Valid
# Validating 187_orchestration_testing.md...
#   ✅ Valid
# [... 8 more files with format {number}_{descriptive_name}.md ...]
# Validation complete: 11/11 files valid
# ✅ All files passed validation
```

### Validation Checks

**Required YAML Fields**:

- `issue_num` (integer > 0)
- `flow_name` (string)
- `pattern` (FANOUT or W_REFINEMENT)
- `project_phase` (exploration, development, integration, production)
- `is_critical_path` (boolean)
- `is_experimental` (boolean)
- `blocks_issues`, `enables_issues`, `dependencies` (arrays)
- `workspace_path` (string)

**W_REFINEMENT Pattern Requirements**:

- `refinement_enabled` (boolean)
- `refinement_desc` (string)
- `critic_domain` (string)
- `gate_instruction` (string)
- `gates` (array)

**Markdown Structure Requirements**:

- Issue header: `# Issue #{number}: {title}`
- Required sections: System Prompt, Description, Planning Instructions,
  Synthesis Instructions, Context

### Common Validation Errors

- **Missing YAML frontmatter**: File must start with `---`
- **Invalid pattern**: Must be exactly "FANOUT" or "W_REFINEMENT"
- **Missing refinement config**: W_REFINEMENT pattern requires refinement fields
- **Invalid issue number**: Must be positive integer
- **Missing required sections**: All markdown sections must be present

## Advanced Usage

### Custom Templates

- Override default templates with `--template` flag
- Support for organization-specific patterns
- Custom gate configurations
- Specialized domain integrations

### Batch Operations

- Generate multiple related flows
- Cross-flow dependency management
- Shared workspace configurations
- Coordinated execution scheduling

### CI/CD Integration

- GitHub Actions workflow generation
- Automated flow execution triggers
- Progress reporting and notifications
- Quality gate automation

## Supporting Files

**Templates**:

- `.claude/templates/issue_plan_template.md` - Issue plan markdown template with
  YAML frontmatter
- `.claude/templates/session-summary-template.md` - Session summary template
  (for context extraction)

**Scripts**:

- `.claude/scripts/verify_issue_plans.py` - Validation script for issue plan
  files
- Validates YAML structure, required fields, and parser compatibility
- Executable: `python .claude/scripts/verify_issue_plans.py <directory>`

**Generated Structure** (per flow):

```
flows/{flow_name}/
├── __init__.py
├── runner.py                    # AsyncIO orchestration runner
├── issues/
│   ├── __init__.py
│   ├── {issue_num}_{descriptive_name}.md  # e.g., 185_cli_command_testing.md
│   └── ...
└── README.md                   # Auto-generated documentation
```

---

**Note**: This command requires GitHub CLI (`gh`) to be installed and
authenticated. Ensure proper repository permissions before running.

**Dependencies**:

- `gh` CLI authenticated with repository access
- Python 3.10+ for verification script
- Write permissions to `flows/` directory
- Access to `.claude/` configuration directory
