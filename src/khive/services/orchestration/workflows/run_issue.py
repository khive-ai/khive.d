import logging

from khive.core import TimePolicy
from khive.services.orchestration.operations.factory import get_worker_session
from khive.services.orchestration.parts import Issue, IssuePlan
from lionagi import Builder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KhiveOperations")


async def run_issue(issue_plan: IssuePlan, **_kw) -> bool:
    """Run all issues sequentially with git cycles.

    Args:
        issue_plan: Plan for issue execution
        **_kw: Framework parameters passed by orchestration system
    """

    issue_num = issue_plan.issue_num
    issue = await Issue.get(issue_num, issue_plan)
    if issue.content.operation_status == "completed":
        logger.info(f"🔵 Skipping already completed issue #{issue.content.issue_num}")
        return True

    _current_timestamp = TimePolicy.now_local().isoformat()
    print(f"\n🔄 Running Issue #{issue_num} at {_current_timestamp}")

    w = get_worker_session()
    b = Builder("run_issue")
    num_attempts = 4
    gate_passed = issue.content.gate_passed

    dep_on = None
    while not gate_passed and num_attempts > 0:
        logger.info(
            f"🔄 Attempting issue #{issue.content.issue_num} (remaining attempts: {num_attempts})"
        )
        _a = b.add_operation(
            "execute_issue",
            issue=issue,
            issue_plan=issue_plan,
            branch=w.new_branch(),
            depends_on=dep_on,
        )
        _b = b.add_operation(
            "review_gate", issue=issue, branch=w.new_branch(), depends_on=[_a]
        )
        results = await w.flow(b.get_graph())
        success, _ = results["operation_results"][_a]
        gate_passed, issue = results["operation_results"][_b]
        dep_on = [_b]
        num_attempts -= 1

    b.add_operation("git_cycle", issue=issue, branch=w.new_branch(), depends_on=dep_on)
    await w.flow(b.get_graph())
    logger.info(
        f"✅ Issue #{issue.content.issue_num} completed successfully with git cycle"
    )
    return success and gate_passed
