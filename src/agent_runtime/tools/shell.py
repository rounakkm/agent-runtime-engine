"""Synchronous shell execution tool restricted to a workspace directory."""

from pathlib import Path
import subprocess
from typing import Any, List, Optional, Set, Union

from agent_runtime.errors import OperationNotSupported, ToolExecutionError
from agent_runtime.tools.base import Tool


class ShellTool(Tool):
    """Tool for synchronous shell command execution in a controlled workspace."""

    name: str = "shell"

    def __init__(
        self,
        workspace_dir: Union[str, Path] = "./workspace",
        timeout: Optional[float] = 30.0,
    ) -> None:
        self.workspace_dir = Path(workspace_dir).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    @property
    def supported_operations(self) -> Set[str]:
        return {"run", "exec", "execute"}

    def execute(self, operation: str, arguments: dict[str, Any]) -> Any:
        if operation not in self.supported_operations:
            raise OperationNotSupported(
                f"Operation '{operation}' is not supported by tool '{self.name}'. "
                f"Supported operations: {sorted(self.supported_operations)}"
            )

        if not isinstance(arguments, dict):
            raise ToolExecutionError(f"Arguments must be a dictionary, got {type(arguments).__name__}")

        if "command" not in arguments:
            raise ToolExecutionError("Missing required argument 'command' for shell execution")

        command = arguments["command"]
        if not isinstance(command, (str, list)):
            raise ToolExecutionError(f"Argument 'command' must be a string or list of strings, got {type(command).__name__}")

        if isinstance(command, str) and not command.strip():
            raise ToolExecutionError("Argument 'command' must be a non-empty string")

        if isinstance(command, list):
            if len(command) == 0:
                raise ToolExecutionError("Argument 'command' list cannot be empty")
            if not all(isinstance(arg, str) for arg in command):
                raise ToolExecutionError("All elements in argument 'command' list must be strings")

        try:
            completed_process = subprocess.run(
                command,
                shell=isinstance(command, str),
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return {
                "stdout": completed_process.stdout,
                "stderr": completed_process.stderr,
                "exit_code": completed_process.returncode,
            }
        except subprocess.TimeoutExpired as e:
            raise ToolExecutionError(
                f"Command timed out after {self.timeout}s: '{command}'",
                details={
                    "stdout": e.stdout if hasattr(e, "stdout") else None,
                    "stderr": e.stderr if hasattr(e, "stderr") else None,
                },
            )
        except Exception as e:
            raise ToolExecutionError(f"Failed to execute command '{command}': {e}")
