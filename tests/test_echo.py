"""Tests for EchoTool."""

import pytest

from agent_runtime.errors import OperationNotSupported, ToolExecutionError
from agent_runtime.tools.echo import EchoTool


def test_echo_tool_success():
    tool = EchoTool()
    res = tool.execute("run", {"message": "hello echo"})
    assert res == "hello echo"


def test_echo_tool_missing_message():
    tool = EchoTool()
    with pytest.raises(ToolExecutionError) as exc_info:
        tool.execute("run", {})
    assert "Missing required argument 'message'" in str(exc_info.value)


def test_echo_tool_unsupported_operation():
    tool = EchoTool()
    with pytest.raises(OperationNotSupported):
        tool.execute("invalid", {"message": "test"})
