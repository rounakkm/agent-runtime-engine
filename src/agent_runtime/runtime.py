"""Agent Runtime engine orchestrator."""

from typing import Any, Optional, Union

from agent_runtime.dispatcher import ToolDispatcher
from agent_runtime.errors import InvalidAction
from agent_runtime.models import ActionRequest, ExecutionResult
from agent_runtime.registry import ToolRegistry
from agent_runtime.tools.base import Tool


class AgentRuntime:
    """Core runtime layer for executing agent actions in a controlled environment."""

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        dispatcher: Optional[ToolDispatcher] = None,
    ) -> None:
        self.registry = registry if registry is not None else ToolRegistry()
        self.dispatcher = dispatcher if dispatcher is not None else ToolDispatcher(self.registry)

    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the runtime registry."""
        self.registry.register(tool)

    def execute(self, action: Union[ActionRequest, dict[str, Any]]) -> ExecutionResult:
        """Execute an action request through the dispatcher pipeline.
        
        Args:
            action: An ActionRequest instance or dictionary containing action data.
            
        Returns:
            Structured ExecutionResult containing status, output, or error details.
        """
        # Parse and validate action request
        if isinstance(action, dict):
            try:
                action_request = ActionRequest.from_dict(action)
            except InvalidAction as e:
                # Extract action_id if present for structured error attribution
                action_id = str(action.get("action_id", "unknown")) if isinstance(action, dict) else "unknown"
                return ExecutionResult.failure(action_id=action_id, error=e)
        elif isinstance(action, ActionRequest):
            action_request = action
        else:
            return ExecutionResult.failure(
                action_id="unknown",
                error=InvalidAction(
                    f"Action must be an ActionRequest instance or a dict, got {type(action).__name__}"
                ),
            )

        # Dispatch execution
        return self.dispatcher.dispatch(action_request)
