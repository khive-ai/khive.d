def get_workflows():
    from .run_issue import run_issue

    return {
        "run_issue": run_issue,
    }


def get_orc_session():
    from lionagi import Session

    worker = Session()
    for k, v in get_workflows().items():
        worker.register_operation(k, v)
    return worker
