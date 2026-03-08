"""Helper utilities for reading and summarizing files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".csv"}


def read_file(path: Path) -> Any:
    """Read a file based on extension and return parsed content."""
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")

    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))

    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as csv_file:
            return list(csv.DictReader(csv_file))

    raise ValueError(
        f"Unsupported file type '{suffix}'. Supported types: {sorted(SUPPORTED_EXTENSIONS)}"
    )


def summarize_content(path: Path, content: Any) -> str:
    """Create a human-readable summary for parsed file content."""
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md"}:
        text = str(content)
        preview = text.replace("\n", " ").strip()[:120]
        return f"{path.name}: text file with {len(text)} characters. Preview: {preview!r}"

    if suffix == ".json":
        if isinstance(content, dict):
            keys = list(content.keys())[:10]
            return f"{path.name}: JSON object with {len(content)} keys. Sample keys: {keys}"
        if isinstance(content, list):
            return f"{path.name}: JSON array with {len(content)} items."
        return f"{path.name}: JSON value of type {type(content).__name__}."

    if suffix == ".csv":
        rows = content if isinstance(content, list) else []
        columns = list(rows[0].keys()) if rows else []
        return f"{path.name}: CSV with {len(rows)} rows and columns {columns}."

    return f"{path.name}: parsed as {type(content).__name__}."
