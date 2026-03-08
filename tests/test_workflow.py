from pathlib import Path

from src.core.workflow import FileReaderWorkflow


def test_reads_single_text_file(tmp_path: Path) -> None:
    text_file = tmp_path / "note.txt"
    text_file.write_text("hello world", encoding="utf-8")

    output = FileReaderWorkflow(str(text_file)).run()

    assert len(output) == 1
    assert "note.txt" in output[0]
    assert "text file" in output[0]


def test_reads_multiple_file_types(tmp_path: Path) -> None:
    (tmp_path / "info.md").write_text("markdown", encoding="utf-8")
    (tmp_path / "data.json").write_text('{"a": 1, "b": 2}', encoding="utf-8")
    (tmp_path / "rows.csv").write_text("name,qty\nitem,3\n", encoding="utf-8")

    output = FileReaderWorkflow(str(tmp_path)).run()

    joined = "\n".join(output)
    assert "info.md" in joined
    assert "data.json" in joined
    assert "rows.csv" in joined


def test_reports_empty_supported_set(tmp_path: Path) -> None:
    (tmp_path / "image.png").write_bytes(b"123")

    output = FileReaderWorkflow(str(tmp_path)).run()

    assert len(output) == 1
    assert "No supported files found" in output[0]
