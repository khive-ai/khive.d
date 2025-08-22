from __future__ import annotations

__all__ = (
    "CRITIC_REVIEW_INSTRUCTION",
    "KHIVE_PLAN_REMINDER",
    "REDO_ORCHESTRATOR_INSTRUCTION",
    "SYNTHESIS_INSTRUCTION",
)


KHIVE_PLAN_REMINDER = """
MANDATORY: First run `gh issue view {issue_num}` to read the original requirements.

Planning Constraints:
- Plan the MINIMAL change to satisfy this issue's acceptance criteria
- Reuse existing patterns - no new abstractions unless explicitly required
- Domains for agents must come from @libs/khive/src/khive/prompts/domains
- Use khive plan [CONTEXT] --issue xxx for agent consensus
- Add --json-format flag for JSON/OrchestrationPlan output (default: BatchTool format)

Simplicity Rules:
- What is the simplest approach that meets the issue requirements?
- What existing code/patterns can be reused?
- What would you deliberately NOT do to keep this minimal?
- Remember: Complexity is a bug, not a feature

Agent Coordination:
- If multiple agents: divide work clearly, avoid overlap
- Later agents build on earlier work, don't rebuild
- If redo: improve existing work, don't start over
"""

CRITIC_REVIEW_INSTRUCTION = """
STEP 1: Run `gh issue view {issue_num}` to read the original issue requirements.

STEP 2: Evaluate ONLY against the specific GitHub issue:
- Does the work satisfy the acceptance criteria stated in the issue?
- Is anything explicitly requested still missing?
- Are there any out-of-scope additions that should be removed?

STEP 3: Check for over-engineering (complexity is a bug):
- Are there new abstractions that could be avoided?
- Could this be simpler and still satisfy the issue?
- What files/code should be deleted as unnecessary?
- Are there multiple implementations that should be consolidated?

STEP 4: Context-appropriate quality check:
- Prototype → Does it work? Ship it.
- Development → Are main use cases covered?
- Production → Is it robust for the stated requirements?

REJECT only if:
- Issue acceptance criteria are NOT met
- Unnecessary complexity that creates technical debt
- Missing critical functionality explicitly requested in the issue

Do NOT reject for:
- Missing features not requested in the original issue
- Lack of "perfect" test coverage for experimental work
- Missing documentation for internal prototypes
- Performance optimizations not requested

Remember: Quality means "appropriate for the issue scope," not "gold-plated."
"""

REDO_ORCHESTRATOR_INSTRUCTION = """
REDO EXECUTION - Previous attempt failed critic review.

STEP 1: Run `gh issue view {issue_num}` to re-read original requirements and c heck relevant comments.

STEP 2: Analyze critic feedback:
{redo_ctx}

STEP 3: Fix specific problems identified by critics:
- Address ONLY the issues critics flagged
- Do NOT rebuild from scratch - improve existing work
- Do NOT add new features beyond the original issue scope
- Focus on satisfying the GitHub issue requirements, not gold-plating

STEP 4: Apply simplicity principles:
- Keep changes MINIMAL to address critic concerns
- Remove any over-engineering introduced in previous attempt
- Consolidate redundant work from previous execution
- Reuse existing patterns where possible

Success Criteria:
- Original GitHub issue requirements are met
- Specific critic concerns are addressed
- Solution is as simple as possible while being functional
- No unnecessary complexity or tech debt introduced

Remember: Fix the problems, don't rebuild the world. Complexity is a bug, not a feature.
"""

SYNTHESIS_INSTRUCTION = """
Workspace Management:
- Agent workspaces: `.khive/workspaces/{flow_name}_[agent_spec]/`
- Agents may scatter files - use `git diff` to locate misplaced work
- Move all working files to respective agent workspaces
- Keep only final deliverables in the main codebase

MANDATORY Cleanup (Tech Debt Removal):
- Remove redundant files and multiple versions of same functionality
- Delete unused/dead code and temporary debug files
- Consolidate duplicate implementations
- Remove over-engineered abstractions not needed for the issue
- Clean up any experimental code that didn't make it to final solution

Quality Standards:
- Ensure deliverables meet the GitHub issue requirements (not generic "best practices")
- Verify simplicity - could this be done with less complexity?
- 5 critic agents will evaluate: pass their review by being issue-focused, not gold-plated

Remember: You're optimizing for issue completion, not theoretical perfection. Complexity is a bug, not a feature.
"""

ATOMIC_WORK_GUIDANCE = """
Work Execution Rules:
- Complete the actual work BEFORE submitting deliverable
- Use MINIMAL approach that satisfies requirements
- Reuse existing patterns - avoid creating new abstractions
- Stop when issue acceptance criteria are met

STOP Rules (DO NOT add):
- "Future-proofing" features not requested
- Extra abstractions "just in case"
- Performance optimizations not required
- Generic improvements beyond issue scope

Deliverable Requirements:
- Submit work only AFTER it's complete and tested
- Write markdown summary in workspace for future agents
- Focus on issue satisfaction, not theoretical perfection
- Remember: Complexity is a bug, not a feature
"""
