"""CLI entry point for the all-in-one file reader app."""

from __future__ import annotations

import argparse

from src.core.workflow import FileReaderWorkflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read and summarize local files (.txt, .md, .json, .csv) from a file or directory."
        )
    )
    parser.add_argument(
        "target",
        help="Path to a file or directory to scan.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workflow = FileReaderWorkflow(args.target)

    try:
        summaries = workflow.run()
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"Error: {exc}") from exc

    for line in summaries:
        print(f"- {line}")


if __name__ == "__main__":
    main()
