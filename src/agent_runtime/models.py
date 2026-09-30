"""Data models for Agent Runtime Engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from agent_runtime.capabilities import Capability, FilesystemCapability
from agent_runtime.errors import AgentRuntimeError, InvalidAction


class ExecutionStatus(str, Enum):
    """Execution status for an action."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class ErrorPayload:
    """Structured error information in an execution result."""
    type: str
    message: str
    details: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.type,
            "message": self.message,
        }
        if self.details is not None:
            data["details"] = self.details
        return data


@dataclass
class ActionRequest:
    """Structured action request submitted by an agent."""
    action_id: str
    tool: str
    operation: str
    arguments: dict[str, Any] = field(default_factory=dict)
    capabilities: list[Capability] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.arguments is None:
            self.arguments = {}
        if self.capabilities is None:
            self.capabilities = []
        self.validate()

    def validate(self) -> None:
        """Validate structure and field types of the action request."""
        if not isinstance(self.action_id, str) or not self.action_id.strip():
            raise InvalidAction("Field 'action_id' must be a non-empty string")
        if not isinstance(self.tool, str) or not self.tool.strip():
            raise InvalidAction("Field 'tool' must be a non-empty string")
        if not isinstance(self.operation, str) or not self.operation.strip():
            raise InvalidAction("Field 'operation' must be a non-empty string")
        if not isinstance(self.arguments, dict):
            raise InvalidAction("Field 'arguments' must be a dictionary")
        if not isinstance(self.capabilities, list):
            raise InvalidAction("Field 'capabilities' must be a list")

    @classmethod
    def from_dict(cls, data: Any) -> "ActionRequest":
        """Construct and validate an ActionRequest from a dictionary."""
        if not isinstance(data, dict):
            raise InvalidAction(f"Action request must be a dictionary, got {type(data).__name__}")
        
        if "action_id" not in data:
            raise InvalidAction("Missing required field 'action_id'")
        if not isinstance(data["action_id"], str) or not data["action_id"].strip():
            raise InvalidAction("Field 'action_id' must be a non-empty string")
            
        if "tool" not in data:
            raise InvalidAction("Missing required field 'tool'")
        if not isinstance(data["tool"], str) or not data["tool"].strip():
            raise InvalidAction("Field 'tool' must be a non-empty string")
            
        if "operation" not in data:
            raise InvalidAction("Missing required field 'operation'")
        if not isinstance(data["operation"], str) or not data["operation"].strip():
            raise InvalidAction("Field 'operation' must be a non-empty string")
        
        arguments = data.get("arguments", {})
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise InvalidAction("Field 'arguments' must be a dictionary")

        raw_capabilities = data.get("capabilities", [])
        if raw_capabilities is None:
            raw_capabilities = []
        if not isinstance(raw_capabilities, list):
            raise InvalidAction("Field 'capabilities' must be a list")

        capabilities: list[Capability] = []
        for cap in raw_capabilities:
            if isinstance(cap, Capability):
                capabilities.append(cap)
            elif isinstance(cap, dict):
                capabilities.append(Capability.from_dict(cap))
            else:
                raise InvalidAction(f"Invalid capability element: {cap}")

        return cls(
            action_id=data["action_id"],
            tool=data["tool"],
            operation=data["operation"],
            arguments=arguments,
            capabilities=capabilities,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert ActionRequest to dictionary representation."""
        return {
            "action_id": self.action_id,
            "tool": self.tool,
            "operation": self.operation,
            "arguments": self.arguments,
            "capabilities": [c.to_dict() for c in self.capabilities],
        }


@dataclass
class ExecutionResult:
    """Structured result returned after action execution."""
    action_id: str
    status: ExecutionStatus
    result: Any = None
    error: Optional[ErrorPayload] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert ExecutionResult to dictionary representation."""
        return {
            "action_id": self.action_id,
            "status": self.status.value if isinstance(self.status, ExecutionStatus) else str(self.status),
            "result": self.result,
            "error": self.error.to_dict() if self.error else None,
        }

    @classmethod
    def success(cls, action_id: str, result: Any) -> "ExecutionResult":
        """Create a successful execution result."""
        return cls(
            action_id=action_id,
            status=ExecutionStatus.SUCCESS,
            result=result,
            error=None,
        )

    @classmethod
    def failure(
        cls,
        action_id: str,
        error: ErrorPayload | AgentRuntimeError | Exception | str,
    ) -> "ExecutionResult":
        """Create a failed execution result from an error or exception."""
        if isinstance(error, ErrorPayload):
            payload = error
        elif isinstance(error, AgentRuntimeError):
            payload = ErrorPayload(
                type=error.error_type,
                message=error.message,
                details=error.details if error.details else None,
            )
        elif isinstance(error, Exception):
            payload = ErrorPayload(
                type=error.__class__.__name__,
                message=str(error),
            )
        else:
            payload = ErrorPayload(
                type="ExecutionError",
                message=str(error),
            )
        return cls(
            action_id=action_id,
            status=ExecutionStatus.FAILED,
            result=None,
            error=payload,
        )
