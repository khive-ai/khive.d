from __future__ import annotations

__all__ = (
    "KHIVE_PLAN_REMINDER",
    "CRITIC_REVIEW_INSTRUCTION",
    "REDO_ORCHESTRATOR_INSTRUCTION",
    "SYNTHESIS_INSTRUCTION",
)


KHIVE_PLAN_REMINDER = """
Requirement: must use GitHub to fetch issues, must use khive plan [CONTEXT] --issue xxx to get agent consensus for each kind of plan. You must check the GitHub issue #{issue_num} or any updates or changes before proceeding. with git commands. The domains for agents must come from @libs/khive/src/khive/prompts/domains 

Notes:
- If multiple implementers/testers are involved, ensure divide and conquer approach and avoid overlap
- later agents need to be aware of earlier agents' work, so they can build on top of it
- If this is a redo, you need to be mindful of the existing work already completed for this issue, so your agents work on improving it, not rebuilding same broken wheels
"""

CRITIC_REVIEW_INSTRUCTION = """
Review the completion of issue.

EVALUATION CRITERIA:
- Deliverable completeness and quality standards
- Requirements fulfillment and integration readiness  
- Documentation quality and implementation clarity

Evaluate if work meets production standards and is ready for git cycle.
Can suggest re-execution if needed. If the issue work is not satisfactory, 
provide clear feedback on what needs to be improved to pass the quality gate.
You may also propose additional GitHub issues if significant gaps are identified.
"""

REDO_ORCHESTRATOR_INSTRUCTION = """
You are re-executing a previously failed issue with additional context.
{redo_ctx}
You must ensure all previous problems are resolved and the issue is ready for production.
"""

SYNTHESIS_INSTRUCTION = """
Info:
- workspace: `.khvie/workspaces/{flow_name}/`
- Your agents work in their respective workspaces all under .khive/workspaces/, with directory named starting with `{flow_name}_` followed by their specification
- They might misplace files across codebase. You might need to use git diff to find them
- They tend to produce redundant files, or multiple versions of the same file. Must prune before handing off to next agent, keep only updated version in codebase, remove others or move them into workspace
- All non deliverable files from working should be in the dedicated workspace directory
- Your work will be immiediately evaluated by a group of 5 critic agents, do a good job to pass the gate
"""

ATOMIC_WORK_GUIDANCE = """
AFTER, doing your other regular requirements. Present the a deliverable in the following format
- DO NOT only submit the deliverable, the actual work must need to be done first
- DO NOT submit the deliverable if the work is not done
- If you have done substantial work, you must also write a markdown file in flow workspace so that
future agents do not need to redo the work.
"""
