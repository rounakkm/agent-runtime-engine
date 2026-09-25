"""Tests for ToolRegistry."""

import pytest
from agent_runtime.errors import AgentRuntimeError, ToolNotFound
from agent_runtime.registry import ToolRegistry
from agent_runtime.tools.echo import EchoTool
from agent_runtime.tools.filesystem import FilesystemTool


def test_register_and_get_tool():
    registry = ToolRegistry()
    echo = EchoTool()
    registry.register(echo)

    assert registry.has("echo")
    assert "echo" in registry
    assert registry.get("echo") is echo
    assert registry.list_tools() == ["echo"]
    assert len(registry) == 1


def test_register_multiple_tools():
    registry = ToolRegistry()
    echo = EchoTool()
    fs = FilesystemTool()

    registry.register(echo)
    registry.register(fs)

    assert len(registry) == 2
    assert sorted(registry.list_tools()) == ["echo", "filesystem"]
    assert registry.get("echo") is echo
    assert registry.get("filesystem") is fs


def test_duplicate_registration_rejected():
    registry = ToolRegistry()
    echo1 = EchoTool()
    echo2 = EchoTool()

    registry.register(echo1)
    with pytest.raises(AgentRuntimeError) as exc_info:
        registry.register(echo2)

    assert "Duplicate tool registration" in str(exc_info.value)


def test_get_unknown_tool_raises():
    registry = ToolRegistry()

    with pytest.raises(ToolNotFound) as exc_info:
        registry.get("non_existent")

    assert "Tool 'non_existent' is not registered" in str(exc_info.value)


def test_register_invalid_object():
    registry = ToolRegistry()

    with pytest.raises(TypeError):
        registry.register("not_a_tool")  # type: ignore
