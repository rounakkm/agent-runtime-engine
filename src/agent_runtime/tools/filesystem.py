"""Filesystem tool restricted to a designated workspace directory."""

from pathlib import Path
from typing import Any, Optional, Set, Union

from agent_runtime.errors import OperationNotSupported, ToolExecutionError
from agent_runtime.tools.base import Tool


class FilesystemTool(Tool):
    """Minimal filesystem tool with workspace path isolation."""

    name: str = "filesystem"

    def __init__(self, workspace_dir: Union[str, Path] = "./workspace") -> None:
        self.workspace_dir = Path(workspace_dir).resolve()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    @property
    def supported_operations(self) -> Set[str]:
        return {"read", "write"}

    def _resolve_safe_path(self, path_str: str) -> Path:
        """Resolve path and enforce workspace boundary."""
        if not isinstance(path_str, str) or not path_str.strip():
            raise ToolExecutionError("Argument 'path' must be a non-empty string")

        raw_path = Path(path_str)
        if raw_path.is_absolute():
            resolved = raw_path.resolve()
        else:
            resolved = (self.workspace_dir / raw_path).resolve()

        try:
            if not resolved.is_relative_to(self.workspace_dir):
                raise ToolExecutionError(
                    f"Access denied: path '{path_str}' resolves outside workspace boundary '{self.workspace_dir}'"
                )
        except ValueError:
            # On Windows, is_relative_to may raise ValueError across different drives
            raise ToolExecutionError(
                f"Access denied: path '{path_str}' is on a different drive or outside workspace '{self.workspace_dir}'"
            )

        return resolved

    def execute(self, operation: str, arguments: dict[str, Any]) -> Any:
        if operation not in self.supported_operations:
            raise OperationNotSupported(
                f"Operation '{operation}' is not supported by tool '{self.name}'. "
                f"Supported operations: {sorted(self.supported_operations)}"
            )

        if "path" not in arguments:
            raise ToolExecutionError("Missing required argument 'path'")

        path_str = arguments["path"]
        safe_path = self._resolve_safe_path(path_str)

        if operation == "read":
            return self._read(safe_path, path_str)
        elif operation == "write":
            if "content" not in arguments:
                raise ToolExecutionError("Missing required argument 'content' for write operation")
            return self._write(safe_path, str(arguments["content"]))

    def _read(self, safe_path: Path, display_path: str) -> str:
        if not safe_path.exists():
            raise ToolExecutionError(f"File not found: '{display_path}'")
        if not safe_path.is_file():
            raise ToolExecutionError(f"Path is not a regular file: '{display_path}'")

        try:
            return safe_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ToolExecutionError(f"Failed to read file '{display_path}': {e}")

    def _write(self, safe_path: Path, content: str) -> str:
        try:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(content, encoding="utf-8")
            return "File written successfully"
        except Exception as e:
            raise ToolExecutionError(f"Failed to write file '{safe_path.name}': {e}")
