"""Runtime error hierarchy for Agent Runtime Engine."""

from typing import Any, Optional


class AgentRuntimeError(Exception):
    """Base exception for all agent runtime errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    @property
    def error_type(self) -> str:
        return self.__class__.__name__


class InvalidAction(AgentRuntimeError):
    """Raised when an action request is malformed or invalid."""
    pass


class ToolNotFound(AgentRuntimeError):
    """Raised when the requested tool is not registered."""
    pass


class OperationNotSupported(AgentRuntimeError):
    """Raised when the tool does not support the requested operation."""
    pass


class ToolExecutionError(AgentRuntimeError):
    """Raised when an error occurs during tool execution."""
    pass
