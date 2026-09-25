"""Echo tool for deterministic testing and sanity checks."""

from typing import Any, Set

from agent_runtime.errors import OperationNotSupported, ToolExecutionError
from agent_runtime.tools.base import Tool


class EchoTool(Tool):
    """Tool that echoes back inputs, useful for testing and verification."""

    name: str = "echo"

    @property
    def supported_operations(self) -> Set[str]:
        return {"run"}

    def execute(self, operation: str, arguments: dict[str, Any]) -> Any:
        if operation not in self.supported_operations:
            raise OperationNotSupported(
                f"Operation '{operation}' is not supported by tool '{self.name}'. "
                f"Supported operations: {sorted(self.supported_operations)}"
            )

        if "message" not in arguments:
            raise ToolExecutionError("Missing required argument 'message' for echo.run")

        return str(arguments["message"])
