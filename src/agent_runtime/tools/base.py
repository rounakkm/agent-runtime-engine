"""Base interface for tools in the Agent Runtime Engine."""

from abc import ABC, abstractmethod
from typing import Any, Set


class Tool(ABC):
    """Abstract base class for all tools."""

    name: str

    @property
    @abstractmethod
    def supported_operations(self) -> Set[str]:
        """Return the set of operation names supported by this tool."""
        pass

    @abstractmethod
    def execute(self, operation: str, arguments: dict[str, Any]) -> Any:
        """Execute the given operation with the provided arguments.
        
        Args:
            operation: Name of the operation to perform.
            arguments: Dictionary of arguments for the operation.
            
        Returns:
            Any structured result returned by the tool.
            
        Raises:
            OperationNotSupported: If the operation is not supported.
            ToolExecutionError: If execution fails.
        """
        pass
