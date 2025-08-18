import logging

from lionagi.ln.concurrency import get_cancelled_exc_class

from khive.services.orchestration.orchestrator import LionOrchestrator

from ..parts import Issue, IssuePlan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KhiveOperations")


async def git_cycle(issue: Issue, **kw) -> Issue:
    issue_plan: IssuePlan = issue.content.issue_plan
    success = issue.last_execution_success
    allow_merge = success is True and issue.content.gate_passed

    orc = LionOrchestrator(issue_plan.flow_name)
    await orc.initialize("sonnet")

    issue_number = issue_plan.issue_number
    print(f"\n🔄 Git Cycle for Issue #{issue_number}")

    status = "completed" if success else "failed"
    commit_msg = f"""feat(001-foundation): {status} issue #{issue_number} - {issue_plan.flow_name}

Issue #{issue_number}: {issue_plan.flow_name}
Status: {"✅ Completed" if success else "❌ Failed"}
Details: [FILL IN DETAILS HERE]

🤖 Generated with [khive.ai](https://khive.ai)

Co-Authored-By: khive.ai <noreply@khive.ai>"""

    # Add git cycle operation to the orchestrator
    git_cycle_instruction = f"""
MANDATORY GIT CYCLE FOR ISSUE #{issue_number}

You MUST complete the following git workflow steps:

1. **Confirm Readiness**: Verify issue #{issue_number} deliverables are complete and ready for commit
2. **Pre-commit Quality**: Run `uv run pre-commit run --all-files` and correct any linting errors until all checks pass
3. **Create Feature Branch**: Create branch `issue-{issue_plan.flow_name.replace("_", "-")}`
4. **Stage Relevant Files**: Only stage files related to issue #{issue_number} work (use `git add -p` for selective staging)
5. **Commit Changes**: Use `uv run khive commit` with the provided commit message and push to remote
6. **Create Pull Request**: Run `uv run khive pr --title "Issue #{issue_number}: {issue_plan.flow_name}" --body "Resolves #{issue_number}"`
7. **Add GitHub Comments**: Comment on issue #{issue_number} with PR link and completion status
8. **Auto merger**: {"allow" if (success and allow_merge) else "disallow"} auto merge of PR if all checks pass
9. **clean up**: If auto merge is completed, switch back to main branch, and pull remote, then delete the feature branch

COMMIT MESSAGE TO USE:
```
{commit_msg}
```

DELIVERABLES:
- ✅ Pre-commit checks passing
- ✅ Clean feature branch with only relevant changes  
- ✅ Conventional commit with proper messaging
- ✅ Pull request created and linked to issue
- ✅ GitHub issue updated with progress


HUMAN REVIEW REQUIRED: This step requires human validation before proceeding to next issue.
"""
    # Add the git cycle operation
    b = orc.new_orc_branch()
    orc.builder.add_operation(
        "communicate",
        instruction=git_cycle_instruction,
        context=f"Git cycle workflow for completed issue #{issue_number} in 001_dashboard_foundation phase",
        branch=b.id,
    )

    # 3. run the orchestration method -----------------------------------------------------------------
    try:
        await orc.run_flow()
        issue.content.git_processed = True
        issue.content.operation_status = "completed" if success else "failed"
    except get_cancelled_exc_class():
        logger.warning(f"⚠️ Issue #{issue_plan.issue_number} git cycle was cancelled.")
        issue.content.operation_status = "cancelled"
    except Exception as e:
        logger.error(f"💥 Issue #{issue_plan.issue_number} error: {e}")
        issue.content.operation_status = "failed"
    await orc.save_json()
    await issue.sync()
    return issue
