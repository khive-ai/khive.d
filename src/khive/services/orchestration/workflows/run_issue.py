import logging
from datetime import datetime

from lionagi import Builder

from ..operations.factory import get_worker_session
from ..parts import Issue, IssuePlan

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KhiveOperations")


async def run_issue(issue_plan: IssuePlan, **kw) -> bool:
    """Run all issues sequentially with git cycles"""

    issue_num = issue_plan.issue_num
    issue = await Issue.get(issue_num, issue_plan)
    if issue.content.operation_status == "completed":
        logger.info(
            f"🔵 Skipping already completed issue #{issue.content.issue_num}"
        )
        return True

    _current_timestamp = datetime.now().isoformat()
    print(f"\n🔄 Running Issue #{issue_num} at {_current_timestamp}")

    w = get_worker_session()
    b = Builder("run_issue")
    num_attempts = 4
    gate_passed = issue.content.gate_passed

    dep_on = None
    while not gate_passed and num_attempts > 0:
        logging.info(
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
