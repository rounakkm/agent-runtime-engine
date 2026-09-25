"""Tests for ToolDispatcher."""

from typing import Any, Set
import pytest

from agent_runtime.dispatcher import ToolDispatcher
from agent_runtime.errors import ToolExecutionError
from agent_runtime.models import ActionRequest, ExecutionStatus
from agent_runtime.registry import ToolRegistry
from agent_runtime.tools.base import Tool
from agent_runtime.tools.echo import EchoTool


class FailingTool(Tool):
    name = "failing"

    @property
    def supported_operations(self) -> Set[str]:
        return {"explode"}

    def execute(self, operation: str, arguments: dict[str, Any]) -> Any:
        raise ToolExecutionError("Boom! Simulated tool failure")


def test_dispatcher_successful_execution():
    registry = ToolRegistry()
    registry.register(EchoTool())
    dispatcher = ToolDispatcher(registry)

    req = ActionRequest(
        action_id="act_01",
        tool="echo",
        operation="run",
        arguments={"message": "hello world"},
    )
    result = dispatcher.dispatch(req)

    assert result.action_id == "act_01"
    assert result.status == ExecutionStatus.SUCCESS
    assert result.result == "hello world"
    assert result.error is None


def test_dispatcher_unknown_tool():
    registry = ToolRegistry()
    dispatcher = ToolDispatcher(registry)

    req = ActionRequest(
        action_id="act_02",
        tool="missing_tool",
        operation="run",
        arguments={},
    )
    result = dispatcher.dispatch(req)

    assert result.action_id == "act_02"
    assert result.status == ExecutionStatus.FAILED
    assert result.result is None
    assert result.error is not None
    assert result.error.type == "ToolNotFound"
    assert "Tool 'missing_tool' is not registered" in result.error.message


def test_dispatcher_unsupported_operation():
    registry = ToolRegistry()
    registry.register(EchoTool())
    dispatcher = ToolDispatcher(registry)

    req = ActionRequest(
        action_id="act_03",
        tool="echo",
        operation="unsupported_op",
        arguments={},
    )
    result = dispatcher.dispatch(req)

    assert result.action_id == "act_03"
    assert result.status == ExecutionStatus.FAILED
    assert result.result is None
    assert result.error is not None
    assert result.error.type == "OperationNotSupported"
    assert "Operation 'unsupported_op' is not supported" in result.error.message


def test_dispatcher_tool_failure():
    registry = ToolRegistry()
    registry.register(FailingTool())
    dispatcher = ToolDispatcher(registry)

    req = ActionRequest(
        action_id="act_04",
        tool="failing",
        operation="explode",
        arguments={},
    )
    result = dispatcher.dispatch(req)

    assert result.action_id == "act_04"
    assert result.status == ExecutionStatus.FAILED
    assert result.result is None
    assert result.error is not None
    assert result.error.type == "ToolExecutionError"
    assert "Boom! Simulated tool failure" in result.error.message


def test_dispatcher_invalid_request_type():
    registry = ToolRegistry()
    dispatcher = ToolDispatcher(registry)

    result = dispatcher.dispatch("not_an_action_request")  # type: ignore
    assert result.status == ExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.type == "InvalidAction"
