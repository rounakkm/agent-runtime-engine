"""Registry for managing and resolving tools."""

from typing import Dict, List

from agent_runtime.errors import AgentRuntimeError, ToolNotFound
from agent_runtime.tools.base import Tool


class ToolRegistry:
    """Manages registered tools for the runtime engine."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a new tool instance.
        
        Args:
            tool: The tool instance to register.
            
        Raises:
            TypeError: If the object is not a Tool instance.
            AgentRuntimeError: If a tool with the same name is already registered.
        """
        if not isinstance(tool, Tool):
            raise TypeError(f"Expected Tool instance, got {type(tool).__name__}")

        if not hasattr(tool, "name") or not isinstance(tool.name, str) or not tool.name.strip():
            raise AgentRuntimeError("Tool must have a non-empty 'name' attribute")

        tool_name = tool.name
        if tool_name in self._tools:
            raise AgentRuntimeError(f"Duplicate tool registration: tool '{tool_name}' is already registered")

        self._tools[tool_name] = tool

    def get(self, name: str) -> Tool:
        """Retrieve a registered tool by its name.
        
        Args:
            name: The name of the tool to retrieve.
            
        Returns:
            The registered Tool instance.
            
        Raises:
            ToolNotFound: If no tool is registered with the given name.
        """
        if not isinstance(name, str) or name not in self._tools:
            raise ToolNotFound(f"Tool '{name}' is not registered")
        return self._tools[name]

    def has(self, name: str) -> bool:
        """Check if a tool with the given name is registered."""
        return name in self._tools

    def list_tools(self) -> List[str]:
        """Return a list of all registered tool names."""
        return sorted(list(self._tools.keys()))

    def __contains__(self, name: str) -> bool:
        return self.has(name)

    def __len__(self) -> int:
        return len(self._tools)
