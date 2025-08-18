from lionagi import Session


def get_operations():
    from .execute_issue import execute_issue
    from .git_cycle import git_cycle
    from .review_gate import review_gate

    return {
        "execute_issue": execute_issue,
        "review_gate": review_gate,
        "git_cycle": git_cycle,
    }


def get_worker_session():
    worker = Session()
    for k, v in get_operations().items():
        worker.register_operation(k, v)
    return worker
