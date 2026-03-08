"""Core workflow orchestration for an all-in-one local file reader."""

from __future__ import annotations

from pathlib import Path

from src.utils.helpers import SUPPORTED_EXTENSIONS, read_file, summarize_content


class FileReaderWorkflow:
    """Load and summarize supported files from a single file or directory."""

    def __init__(self, target_path: str) -> None:
        self.target = Path(target_path).expanduser().resolve()

    def _iter_supported_files(self) -> list[Path]:
        if not self.target.exists():
            raise FileNotFoundError(f"Path does not exist: {self.target}")

        if self.target.is_file():
            return [self.target]

        files = [
            path
            for path in sorted(self.target.rglob("*"))
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        return files

    def run(self) -> list[str]:
        summaries: list[str] = []
        files = self._iter_supported_files()

        if not files:
            return [
                f"No supported files found in {self.target}. Supported types: {sorted(SUPPORTED_EXTENSIONS)}"
            ]

        for file_path in files:
            parsed = read_file(file_path)
            summaries.append(summarize_content(file_path, parsed))

        return summaries
