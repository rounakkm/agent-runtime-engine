"""Tool dispatcher for resolving and executing tools."""

from typing import Any, Optional

from agent_runtime.errors import (
    AgentRuntimeError,
    InvalidAction,
    OperationNotSupported,
    ToolExecutionError,
    ToolNotFound,
)
from agent_runtime.models import ActionRequest, ErrorPayload, ExecutionResult
from agent_runtime.registry import ToolRegistry


class ToolDispatcher:
    """Dispatches validated ActionRequests to resolved tools and standardizes results."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def dispatch(self, request: ActionRequest) -> ExecutionResult:
        """Dispatch an action request to the appropriate tool.
        
        Args:
            request: The ActionRequest to execute.
            
        Returns:
            An ExecutionResult with SUCCESS or FAILED status.
        """
        # Validate request type
        if not isinstance(request, ActionRequest):
            return ExecutionResult.failure(
                action_id="unknown",
                error=InvalidAction(f"Expected ActionRequest instance, got {type(request).__name__}"),
            )

        action_id = request.action_id

        # Resolve tool from registry
        try:
            tool = self.registry.get(request.tool)
        except ToolNotFound as e:
            return ExecutionResult.failure(action_id=action_id, error=e)
        except Exception as e:
            return ExecutionResult.failure(
                action_id=action_id,
                error=ErrorPayload(type="ToolResolutionError", message=str(e)),
            )

        # Validate operation support
        if request.operation not in tool.supported_operations:
            err = OperationNotSupported(
                f"Operation '{request.operation}' is not supported by tool '{tool.name}'. "
                f"Supported operations: {sorted(tool.supported_operations)}"
            )
            return ExecutionResult.failure(action_id=action_id, error=err)

        # Execute tool
        try:
            output = tool.execute(request.operation, request.arguments)
            return ExecutionResult.success(action_id=action_id, result=output)
        except (AgentRuntimeError, ToolExecutionError, OperationNotSupported) as e:
            return ExecutionResult.failure(action_id=action_id, error=e)
        except Exception as e:
            return ExecutionResult.failure(
                action_id=action_id,
                error=ErrorPayload(
                    type="ToolExecutionError",
                    message=f"Unhandled error during execution of tool '{tool.name}': {e}",
                ),
            )
