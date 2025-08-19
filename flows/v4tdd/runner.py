from pathlib import Path


async def main():
    from khive.services.orchestration.issue_runner import IssueRunner

    ir = IssueRunner(
        issue_dir=Path("flows/v4tdd/issues"),
        delay_before_start=5,
        max_concurrent=3,
        throttle_period=60,
    )
    issue_seq = [195, 185, 186, 187, 190, 188, 189, 191, 192, 193, 194]
    ir.load(issue_seq)
    await ir.run()


if __name__ == "__main__":
    import anyio

    anyio.run(main)
