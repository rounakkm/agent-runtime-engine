"""Tests for ShellTool."""

from pathlib import Path
import sys
import pytest

from agent_runtime.dispatcher import ToolDispatcher
from agent_runtime.errors import OperationNotSupported, ToolExecutionError
from agent_runtime.models import ActionRequest, ExecutionResult, ExecutionStatus
from agent_runtime.registry import ToolRegistry
from agent_runtime.runtime import AgentRuntime
from agent_runtime.tools.shell import ShellTool


@pytest.fixture
def temp_shell(tmp_path: Path) -> ShellTool:
    return ShellTool(workspace_dir=tmp_path)


# ---------------------------------------------------------------------------
# 1. Successful Command and Output Capture
# ---------------------------------------------------------------------------

def test_shell_successful_command(temp_shell: ShellTool):
    cmd = f'"{sys.executable}" -c "print(\'hello stdout\')"'
    res = temp_shell.execute("run", {"command": cmd})

    assert isinstance(res, dict)
    assert res["exit_code"] == 0
    assert "hello stdout" in res["stdout"]
    assert res["stderr"] == ""


def test_shell_stdout_capture(temp_shell: ShellTool):
    cmd = f'"{sys.executable}" -c "import sys; sys.stdout.write(\'line 1\\nline 2\\n\')"'
    res = temp_shell.execute("run", {"command": cmd})

    assert res["exit_code"] == 0
    assert res["stdout"] == "line 1\nline 2\n"
    assert res["stderr"] == ""


def test_shell_stderr_capture(temp_shell: ShellTool):
    cmd = f'"{sys.executable}" -c "import sys; sys.stderr.write(\'warning: deprecation notice\\n\')"'
    res = temp_shell.execute("run", {"command": cmd})

    assert res["exit_code"] == 0
    assert res["stdout"] == ""
    assert "warning: deprecation notice" in res["stderr"]


def test_shell_both_stdout_and_stderr(temp_shell: ShellTool):
    cmd = f'"{sys.executable}" -c "import sys; sys.stdout.write(\'out data\\n\'); sys.stderr.write(\'err data\\n\')"'
    res = temp_shell.execute("run", {"command": cmd})

    assert res["exit_code"] == 0
    assert "out data" in res["stdout"]
    assert "err data" in res["stderr"]


# ---------------------------------------------------------------------------
# 2. Non-zero Exit Code
# ---------------------------------------------------------------------------

def test_shell_nonzero_exit_code(temp_shell: ShellTool):
    cmd = f'"{sys.executable}" -c "import sys; sys.stderr.write(\'fatal error\\n\'); sys.exit(42)"'
    res = temp_shell.execute("run", {"command": cmd})

    assert isinstance(res, dict)
    assert res["exit_code"] == 42
    assert "fatal error" in res["stderr"]


# ---------------------------------------------------------------------------
# 3. Invalid & Nonexistent Commands
# ---------------------------------------------------------------------------

def test_shell_nonexistent_command_string(temp_shell: ShellTool):
    # Running a nonexistent command via shell string returns non-zero exit code with stderr
    res = temp_shell.execute("run", {"command": "nonexistent_command_abc_123_xyz"})
    assert isinstance(res, dict)
    assert res["exit_code"] != 0
    assert len(res["stderr"]) > 0 or res["exit_code"] in (127, 1)


def test_shell_nonexistent_command_list_raises(temp_shell: ShellTool):
    # Direct list invocation when binary does not exist raises ToolExecutionError
    with pytest.raises(ToolExecutionError) as exc_info:
        temp_shell.execute("run", {"command": ["nonexistent_command_abc_123_xyz"]})

    assert "Failed to execute command" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 4. Workspace Execution Directory & Operations
# ---------------------------------------------------------------------------

def test_shell_executes_in_workspace_dir(temp_shell: ShellTool, tmp_path: Path):
    cmd = f'"{sys.executable}" -c "import pathlib; pathlib.Path(\'from_shell.txt\').write_text(\'created by shell\')"'
    res = temp_shell.execute("run", {"command": cmd})

    assert res["exit_code"] == 0
    created_file = tmp_path / "from_shell.txt"
    assert created_file.exists()
    assert created_file.read_text() == "created by shell"


def test_shell_supported_operations_aliases(temp_shell: ShellTool):
    cmd = f'"{sys.executable}" -c "print(\'alias test\')"'
    
    for op in ["run", "exec", "execute"]:
        res = temp_shell.execute(op, {"command": cmd})
        assert res["exit_code"] == 0
        assert "alias test" in res["stdout"]


# ---------------------------------------------------------------------------
# 5. Argument Validation
# ---------------------------------------------------------------------------

def test_shell_missing_command_argument(temp_shell: ShellTool):
    with pytest.raises(ToolExecutionError) as exc_info:
        temp_shell.execute("run", {})

    assert "Missing required argument 'command'" in str(exc_info.value)


def test_shell_invalid_command_types(temp_shell: ShellTool):
    with pytest.raises(ToolExecutionError) as exc_info:
        temp_shell.execute("run", {"command": 12345})
    assert "Argument 'command' must be a string or list" in str(exc_info.value)

    with pytest.raises(ToolExecutionError) as exc_info:
        temp_shell.execute("run", {"command": "   "})
    assert "non-empty string" in str(exc_info.value)

    with pytest.raises(ToolExecutionError) as exc_info:
        temp_shell.execute("run", {"command": []})
    assert "cannot be empty" in str(exc_info.value)


def test_shell_unsupported_operation(temp_shell: ShellTool):
    with pytest.raises(OperationNotSupported):
        temp_shell.execute("kill", {"command": "echo 1"})


# ---------------------------------------------------------------------------
# 6. Full Pipeline: ActionRequest → Dispatcher → Registry → ShellTool → Result
# ---------------------------------------------------------------------------

def test_runtime_pipeline_shell_flow(tmp_path: Path):
    runtime = AgentRuntime()
    shell_tool = ShellTool(workspace_dir=tmp_path)
    runtime.register_tool(shell_tool)

    # 1. Successful shell execution through runtime
    req_success = ActionRequest(
        action_id="act_sh_01",
        tool="shell",
        operation="run",
        arguments={"command": f'"{sys.executable}" -c "print(\'pipeline shell output\')"' },
    )
    res_success = runtime.execute(req_success)

    assert isinstance(res_success, ExecutionResult)
    assert res_success.action_id == "act_sh_01"
    assert res_success.status == ExecutionStatus.SUCCESS
    assert res_success.error is None
    assert isinstance(res_success.result, dict)
    assert res_success.result["exit_code"] == 0
    assert "pipeline shell output" in res_success.result["stdout"]

    # 2. Command with non-zero exit code through runtime
    req_nonzero = ActionRequest(
        action_id="act_sh_02",
        tool="shell",
        operation="run",
        arguments={"command": f'"{sys.executable}" -c "import sys; sys.exit(7)"' },
    )
    res_nonzero = runtime.execute(req_nonzero)

    assert res_nonzero.action_id == "act_sh_02"
    assert res_nonzero.status == ExecutionStatus.SUCCESS
    assert res_nonzero.result["exit_code"] == 7

    # 3. Invalid tool operation failure through runtime
    req_invalid_op = ActionRequest(
        action_id="act_sh_03",
        tool="shell",
        operation="invalid_op",
        arguments={"command": "echo hello"},
    )
    res_invalid_op = runtime.execute(req_invalid_op)

    assert res_invalid_op.status == ExecutionStatus.FAILED
    assert res_invalid_op.error is not None
    assert res_invalid_op.error.type == "OperationNotSupported"

    # 4. Missing required argument failure through runtime
    req_missing_arg = ActionRequest(
        action_id="act_sh_04",
        tool="shell",
        operation="run",
        arguments={},
    )
    res_missing_arg = runtime.execute(req_missing_arg)

    assert res_missing_arg.status == ExecutionStatus.FAILED
    assert res_missing_arg.error is not None
    assert res_missing_arg.error.type == "ToolExecutionError"
    assert "Missing required argument 'command'" in res_missing_arg.error.message
