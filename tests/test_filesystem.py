"""Tests for FilesystemTool."""

from pathlib import Path
import pytest

from agent_runtime.dispatcher import ToolDispatcher
from agent_runtime.errors import OperationNotSupported, ToolExecutionError
from agent_runtime.models import ActionRequest, ExecutionResult, ExecutionStatus
from agent_runtime.registry import ToolRegistry
from agent_runtime.runtime import AgentRuntime
from agent_runtime.tools.filesystem import FilesystemTool


@pytest.fixture
def temp_workspace(tmp_path: Path) -> FilesystemTool:
    return FilesystemTool(workspace_dir=tmp_path)


# ---------------------------------------------------------------------------
# 1. Write and Read Operations
# ---------------------------------------------------------------------------

def test_write_and_read_file(temp_workspace: FilesystemTool):
    fs = temp_workspace
    write_res = fs.execute("write", {"path": "test.txt", "content": "hello filesystem"})
    assert write_res == "File written successfully"

    read_res = fs.execute("read", {"path": "test.txt"})
    assert read_res == "hello filesystem"


def test_write_overwrite_file(temp_workspace: FilesystemTool):
    fs = temp_workspace
    fs.execute("write", {"path": "data.txt", "content": "initial"})
    assert fs.execute("read", {"path": "data.txt"}) == "initial"

    fs.execute("write", {"path": "data.txt", "content": "overwritten"})
    assert fs.execute("read", {"path": "data.txt"}) == "overwritten"


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


def test_read_directory_as_file_raises(temp_workspace: FilesystemTool):
    fs = temp_workspace
    fs.execute("write", {"path": "sub/file.txt", "content": "data"})
    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {"path": "sub"})

    assert "Path is not a regular file" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. List Operations
# ---------------------------------------------------------------------------

def test_list_files_empty_workspace(temp_workspace: FilesystemTool):
    fs = temp_workspace
    assert fs.execute("list", {}) == []
    assert fs.execute("list_files", {}) == []


def test_list_files_root_workspace(temp_workspace: FilesystemTool):
    fs = temp_workspace
    fs.execute("write", {"path": "b.txt", "content": "b"})
    fs.execute("write", {"path": "a.txt", "content": "a"})
    fs.execute("write", {"path": "sub/c.txt", "content": "c"})

    listing = fs.execute("list", {})
    assert listing == ["a.txt", "b.txt", "sub"]


def test_list_files_subdirectory(temp_workspace: FilesystemTool):
    fs = temp_workspace
    fs.execute("write", {"path": "sub/one.txt", "content": "1"})
    fs.execute("write", {"path": "sub/two.txt", "content": "2"})

    listing = fs.execute("list", {"path": "sub"})
    assert listing == ["one.txt", "two.txt"]


def test_list_nonexistent_directory_raises(temp_workspace: FilesystemTool):
    fs = temp_workspace
    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("list", {"path": "nonexistent_dir"})

    assert "Directory not found" in str(exc_info.value)


def test_list_file_as_directory_raises(temp_workspace: FilesystemTool):
    fs = temp_workspace
    fs.execute("write", {"path": "file.txt", "content": "content"})
    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("list", {"path": "file.txt"})

    assert "Path is not a directory" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Path Traversal & Security Boundary Tests
# ---------------------------------------------------------------------------

def test_workspace_restriction_relative_traversal(temp_workspace: FilesystemTool):
    fs = temp_workspace
    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("write", {"path": "../outside.txt", "content": "escape attempt"})
    assert "Access denied" in str(exc_info.value)

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {"path": "../../secret.txt"})
    assert "Access denied" in str(exc_info.value)

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("list", {"path": "../"})
    assert "Access denied" in str(exc_info.value)


def test_workspace_restriction_nested_relative_traversal(temp_workspace: FilesystemTool):
    fs = temp_workspace
    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {"path": "sub/../../escape.txt"})
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

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("write", {"path": str(outside_file), "content": "compromised"})
    assert "Access denied" in str(exc_info.value)

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("list", {"path": str(outside_dir)})
    assert "Access denied" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 4. Input & Argument Validations
# ---------------------------------------------------------------------------

def test_missing_required_arguments(temp_workspace: FilesystemTool):
    fs = temp_workspace

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {})
    assert "Missing required argument 'path'" in str(exc_info.value)

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("write", {"path": "test.txt"})
    assert "Missing required argument 'content'" in str(exc_info.value)


def test_invalid_path_types(temp_workspace: FilesystemTool):
    fs = temp_workspace

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {"path": 12345})
    assert "Argument 'path' must be a string" in str(exc_info.value)

    with pytest.raises(ToolExecutionError) as exc_info:
        fs.execute("read", {"path": "   "})
    assert "Argument 'path' must be a non-empty string" in str(exc_info.value)


def test_unsupported_operation(temp_workspace: FilesystemTool):
    fs = temp_workspace
    with pytest.raises(OperationNotSupported):
        fs.execute("delete", {"path": "test.txt"})


# ---------------------------------------------------------------------------
# 5. Full Pipeline: ActionRequest → Dispatcher → Registry → Tool → Result
# ---------------------------------------------------------------------------

def test_runtime_pipeline_filesystem_flow(tmp_path: Path):
    runtime = AgentRuntime()
    fs_tool = FilesystemTool(workspace_dir=tmp_path)
    runtime.register_tool(fs_tool)

    # 1. List empty workspace
    res_list_empty = runtime.execute(ActionRequest(
        action_id="act_fs_01",
        tool="filesystem",
        operation="list",
        arguments={},
    ))
    assert res_list_empty.status == ExecutionStatus.SUCCESS
    assert res_list_empty.result == []

    # 2. Write file
    res_write = runtime.execute(ActionRequest(
        action_id="act_fs_02",
        tool="filesystem",
        operation="write",
        arguments={"path": "notes.md", "content": "# Hello Agent"},
    ))
    assert res_write.status == ExecutionStatus.SUCCESS
    assert res_write.result == "File written successfully"

    # 3. Read file
    res_read = runtime.execute(ActionRequest(
        action_id="act_fs_03",
        tool="filesystem",
        operation="read",
        arguments={"path": "notes.md"},
    ))
    assert res_read.status == ExecutionStatus.SUCCESS
    assert res_read.result == "# Hello Agent"

    # 4. List populated workspace
    res_list_pop = runtime.execute(ActionRequest(
        action_id="act_fs_04",
        tool="filesystem",
        operation="list",
        arguments={},
    ))
    assert res_list_pop.status == ExecutionStatus.SUCCESS
    assert res_list_pop.result == ["notes.md"]

    # 5. Attempt path traversal via runtime
    res_escape = runtime.execute(ActionRequest(
        action_id="act_fs_05",
        tool="filesystem",
        operation="read",
        arguments={"path": "../secret_outside.txt"},
    ))
    assert res_escape.status == ExecutionStatus.FAILED
    assert res_escape.error is not None
    assert res_escape.error.type == "ToolExecutionError"
    assert "Access denied" in res_escape.error.message
