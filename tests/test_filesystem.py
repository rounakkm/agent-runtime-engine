"""Tests for FilesystemTool."""

import os
from pathlib import Path
import pytest

from agent_runtime.errors import OperationNotSupported, ToolExecutionError
from agent_runtime.tools.filesystem import FilesystemTool


@pytest.fixture
def temp_workspace(tmp_path: Path) -> FilesystemTool:
    return FilesystemTool(workspace_dir=tmp_path)


def test_write_and_read_file(temp_workspace: FilesystemTool):
    fs = temp_workspace
    write_res = fs.execute("write", {"path": "test.txt", "content": "hello filesystem"})
    assert write_res == "File written successfully"

    read_res = fs.execute("read", {"path": "test.txt"})
    assert read_res == "hello filesystem"


def test_write_nested_file(temp_workspace: FilesystemTool):
    fs = temp_workspace
    write_res = fs.execute("write", {"path": "sub/dir/nested.txt", "content": "nested content"})
    assert write_res == "File written successfully"

    read_res = fs.execute("read", {"path": "sub/dir/nested.txt"})
    assert read_res == "nested content"


def test_read_missing_file_raises(temp_workspace: FilesystemTool):
    fs = temp_workspace
    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {"path": "does_not_exist.txt"})

    assert "File not found" in str(exc_info.value)


def test_workspace_restriction_relative_traversal(temp_workspace: FilesystemTool):
    fs = temp_workspace
    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("write", {"path": "../outside.txt", "content": "escape attempt"})

    assert "Access denied" in str(exc_info.value)

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {"path": "../../secret.txt"})

    assert "Access denied" in str(exc_info.value)


def test_workspace_restriction_absolute_path_outside(temp_workspace: FilesystemTool, tmp_path: Path):
    fs = temp_workspace
    outside_dir = tmp_path.parent / "other_secret_dir"
    outside_dir.mkdir(exist_ok=True)
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {"path": str(outside_file)})

    assert "Access denied" in str(exc_info.value)


def test_missing_required_arguments(temp_workspace: FilesystemTool):
    fs = temp_workspace

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {})
    assert "Missing required argument 'path'" in str(exc_info.value)

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("write", {"path": "test.txt"})
    assert "Missing required argument 'content'" in str(exc_info.value)


def test_unsupported_operation(temp_workspace: FilesystemTool):
    fs = temp_workspace
    with pytest.raises(OperationNotSupported):
        fs.execute("delete", {"path": "test.txt"})
