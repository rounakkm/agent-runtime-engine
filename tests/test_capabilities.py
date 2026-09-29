"""Tests for Capability Model and Capability-driven Execution."""

from pathlib import Path
import pytest

from agent_runtime.capabilities import Capability, FilesystemCapability
from agent_runtime.errors import InvalidAction, ToolExecutionError
from agent_runtime.models import ActionRequest, ExecutionStatus
from agent_runtime.runtime import AgentRuntime
from agent_runtime.tools.filesystem import FilesystemTool


# ---------------------------------------------------------------------------
# 1. Capability Model Tests
# ---------------------------------------------------------------------------

def test_filesystem_capability_creation():
    cap = FilesystemCapability(root="/tmp/test_workspace")
    assert cap.type == "filesystem"
    assert cap.root == Path("/tmp/test_workspace").resolve()


def test_filesystem_capability_validation():
    with pytest.raises(InvalidAction, match="non-empty string"):
        FilesystemCapability(root="")

    with pytest.raises(InvalidAction, match="must be a string or Path"):
        FilesystemCapability(root=12345)  # type: ignore


def test_filesystem_capability_to_dict_and_from_dict():
    cap = FilesystemCapability(root="/tmp/sandbox")
    d = cap.to_dict()
    assert d == {
        "type": "filesystem",
        "root": str(Path("/tmp/sandbox").resolve()),
    }

    reconstructed = Capability.from_dict(d)
    assert isinstance(reconstructed, FilesystemCapability)
    assert reconstructed.type == "filesystem"
    assert reconstructed.root == Path("/tmp/sandbox").resolve()


def test_action_request_with_capabilities_serialization():
    cap = FilesystemCapability(root="/tmp/sandbox")
    req = ActionRequest(
        action_id="act_cap_01",
        tool="filesystem",
        operation="write",
        arguments={"path": "file.txt", "content": "hello"},
        capabilities=[cap],
    )
    d = req.to_dict()
    assert len(d["capabilities"]) == 1
    assert d["capabilities"][0]["type"] == "filesystem"

    reconstructed = ActionRequest.from_dict(d)
    assert len(reconstructed.capabilities) == 1
    assert isinstance(reconstructed.capabilities[0], FilesystemCapability)
    assert reconstructed.capabilities[0].root == Path("/tmp/sandbox").resolve()


# ---------------------------------------------------------------------------
# 2. Execution With Filesystem Capability
# ---------------------------------------------------------------------------

def test_action_with_filesystem_capability_can_write_and_read(tmp_path: Path):
    runtime = AgentRuntime()
    runtime.register_tool(FilesystemTool())

    fs_cap = FilesystemCapability(root=tmp_path)

    # Write action
    req_write = ActionRequest(
        action_id="act_write_cap",
        tool="filesystem",
        operation="write",
        arguments={"path": "doc.txt", "content": "capability content"},
        capabilities=[fs_cap],
    )
    res_write = runtime.execute(req_write)
    assert res_write.status == ExecutionStatus.SUCCESS
    assert res_write.result == "File written successfully"

    # Read action
    req_read = ActionRequest(
        action_id="act_read_cap",
        tool="filesystem",
        operation="read",
        arguments={"path": "doc.txt"},
        capabilities=[fs_cap],
    )
    res_read = runtime.execute(req_read)
    assert res_read.status == ExecutionStatus.SUCCESS
    assert res_read.result == "capability content"


def test_action_with_filesystem_capability_can_list(tmp_path: Path):
    runtime = AgentRuntime()
    runtime.register_tool(FilesystemTool())

    fs_cap = FilesystemCapability(root=tmp_path)

    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")

    req_list = ActionRequest(
        action_id="act_list_cap",
        tool="filesystem",
        operation="list",
        arguments={},
        capabilities=[fs_cap],
    )
    res_list = runtime.execute(req_list)
    assert res_list.status == ExecutionStatus.SUCCESS
    assert res_list.result == ["a.txt", "b.txt"]


# ---------------------------------------------------------------------------
# 3. Execution Without Filesystem Capability (Rejection)
# ---------------------------------------------------------------------------

def test_action_without_filesystem_capability_is_rejected(tmp_path: Path):
    runtime = AgentRuntime()
    runtime.register_tool(FilesystemTool())

    # Action without any capabilities
    req = ActionRequest(
        action_id="act_no_cap",
        tool="filesystem",
        operation="read",
        arguments={"path": "doc.txt"},
        capabilities=[],
    )
    res = runtime.execute(req)
    assert res.status == ExecutionStatus.FAILED
    assert res.error is not None
    assert res.error.type == "ToolExecutionError"
    assert "Access denied" in res.error.message or "capability" in res.error.message.lower()


def test_action_with_non_matching_capability_is_rejected(tmp_path: Path):
    runtime = AgentRuntime()
    runtime.register_tool(FilesystemTool())

    # Action with a generic/unrelated capability
    req = ActionRequest(
        action_id="act_other_cap",
        tool="filesystem",
        operation="write",
        arguments={"path": "doc.txt", "content": "data"},
        capabilities=[Capability(type="network")],
    )
    res = runtime.execute(req)
    assert res.status == ExecutionStatus.FAILED
    assert res.error is not None
    assert res.error.type == "ToolExecutionError"
    assert "capability" in res.error.message.lower()


# ---------------------------------------------------------------------------
# 4. Access Outside Capability Root is Rejected
# ---------------------------------------------------------------------------

def test_access_outside_capability_root_rejected(tmp_path: Path):
    runtime = AgentRuntime()
    runtime.register_tool(FilesystemTool())

    sub_workspace = tmp_path / "allowed_sub"
    sub_workspace.mkdir()

    outside_dir = tmp_path / "forbidden_outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    fs_cap = FilesystemCapability(root=sub_workspace)

    # Attempt to read absolute path outside granted root
    req_abs = ActionRequest(
        action_id="act_outside_abs",
        tool="filesystem",
        operation="read",
        arguments={"path": str(outside_file)},
        capabilities=[fs_cap],
    )
    res_abs = runtime.execute(req_abs)
    assert res_abs.status == ExecutionStatus.FAILED
    assert res_abs.error is not None
    assert res_abs.error.type == "ToolExecutionError"
    assert "Access denied" in res_abs.error.message


# ---------------------------------------------------------------------------
# 5. Path Traversal Protection Under Capability Root
# ---------------------------------------------------------------------------

def test_path_traversal_under_capability_root_rejected(tmp_path: Path):
    runtime = AgentRuntime()
    runtime.register_tool(FilesystemTool())

    sub_workspace = tmp_path / "allowed_sub"
    sub_workspace.mkdir()

    fs_cap = FilesystemCapability(root=sub_workspace)

    # Attempt relative path traversal
    req_traversal = ActionRequest(
        action_id="act_traversal",
        tool="filesystem",
        operation="write",
        arguments={"path": "../outside.txt", "content": "breach"},
        capabilities=[fs_cap],
    )
    res_traversal = runtime.execute(req_traversal)
    assert res_traversal.status == ExecutionStatus.FAILED
    assert res_traversal.error is not None
    assert res_traversal.error.type == "ToolExecutionError"
    assert "Access denied" in res_traversal.error.message
