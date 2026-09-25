"""Tests for AgentRuntime."""

import pytest

from agent_runtime.errors import InvalidAction
from agent_runtime.models import ActionRequest, ExecutionResult, ExecutionStatus
from agent_runtime.runtime import AgentRuntime
from agent_runtime.tools.echo import EchoTool


def test_runtime_valid_action_request_object():
    runtime = AgentRuntime()
    runtime.register_tool(EchoTool())

    req = ActionRequest(
        action_id="act_100",
        tool="echo",
        operation="run",
        arguments={"message": "hello runtime"},
    )
    result = runtime.execute(req)

    assert isinstance(result, ExecutionResult)
    assert result.action_id == "act_100"
    assert result.status == ExecutionStatus.SUCCESS
    assert result.result == "hello runtime"
    assert result.error is None


def test_runtime_valid_action_dict():
    runtime = AgentRuntime()
    runtime.register_tool(EchoTool())

    action_dict = {
        "action_id": "act_101",
        "tool": "echo",
        "operation": "run",
        "arguments": {"message": "from dict"},
    }
    result = runtime.execute(action_dict)

    assert result.action_id == "act_101"
    assert result.status == ExecutionStatus.SUCCESS
    assert result.result == "from dict"


def test_runtime_malformed_action_dict_missing_tool():
    runtime = AgentRuntime()

    bad_dict = {
        "action_id": "act_102",
        "operation": "run",
        "arguments": {},
    }
    result = runtime.execute(bad_dict)

    assert result.action_id == "act_102"
    assert result.status == ExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.type == "InvalidAction"
    assert "Missing required field 'tool'" in result.error.message


def test_runtime_malformed_action_invalid_type():
    runtime = AgentRuntime()

    result = runtime.execute(12345)  # type: ignore

    assert result.status == ExecutionStatus.FAILED
    assert result.error is not None
    assert result.error.type == "InvalidAction"


def test_action_request_validation_empty_fields():
    with pytest.raises(InvalidAction):
        ActionRequest(action_id="", tool="echo", operation="run")

    with pytest.raises(InvalidAction):
        ActionRequest(action_id="1", tool="", operation="run")

    with pytest.raises(InvalidAction):
        ActionRequest(action_id="1", tool="echo", operation="")

    with pytest.raises(InvalidAction):
        ActionRequest(action_id="1", tool="echo", operation="run", arguments="bad")  # type: ignore


def test_execution_result_to_dict():
    res = ExecutionResult.success("act_1", "output_val")
    d = res.to_dict()
    assert d == {
        "action_id": "act_1",
        "status": "SUCCESS",
        "result": "output_val",
        "error": None,
    }
