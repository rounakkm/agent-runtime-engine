"""Tests for ShellTool."""

from pathlib import Path
import sys
import pytest

from agent_runtime.errors import OperationNotSupported, ToolExecutionError
from agent_runtime.tools.shell import ShellTool


@pytest.fixture
def temp_shell(tmp_path: Path) -> ShellTool:
    return ShellTool(workspace_dir=tmp_path)


def test_shell_successful_command(temp_shell: ShellTool):
    # Run python command which is cross-platform
    cmd = f'"{sys.executable}" -c "print(\'shell test\')"'
    res = temp_shell.execute("run", {"command": cmd})

    assert isinstance(res, dict)
    assert res["exit_code"] == 0
    assert "shell test" in res["stdout"]
    assert res["stderr"] == ""


def test_shell_nonzero_exit_code(temp_shell: ShellTool):
    cmd = f'"{sys.executable}" -c "import sys; sys.stderr.write(\'an error occurred\\n\'); sys.exit(42)"'
    res = temp_shell.execute("run", {"command": cmd})

    assert isinstance(res, dict)
    assert res["exit_code"] == 42
    assert "an error occurred" in res["stderr"]


def test_shell_executes_in_workspace_dir(temp_shell: ShellTool, tmp_path: Path):
    cmd = f'"{sys.executable}" -c "import pathlib; pathlib.Path(\'from_shell.txt\').write_text(\'created by shell\')"'
    res = temp_shell.execute("run", {"command": cmd})

    assert res["exit_code"] == 0
    created_file = tmp_path / "from_shell.txt"
    assert created_file.exists()
    assert created_file.read_text() == "created by shell"


def test_shell_missing_command_argument(temp_shell: ShellTool):
    with pytest.raises(ToolExecutionError) as exc_info:
        temp_shell.execute("run", {})

    assert "Missing required argument 'command'" in str(exc_info.value)


def test_shell_unsupported_operation(temp_shell: ShellTool):
    with pytest.raises(OperationNotSupported):
        temp_shell.execute("kill", {"command": "dir"})
