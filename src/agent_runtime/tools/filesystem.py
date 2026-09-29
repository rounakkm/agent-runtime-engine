"""Filesystem tool restricted to a designated workspace directory."""

from pathlib import Path
from typing import Any, List, Optional, Set, Union

from agent_runtime.capabilities import Capability, FilesystemCapability
from agent_runtime.errors import OperationNotSupported, ToolExecutionError
from agent_runtime.tools.base import Tool


class FilesystemTool(Tool):
    """Minimal filesystem tool with capability-based path isolation."""

    name: str = "filesystem"

    def __init__(self, workspace_dir: Optional[Union[str, Path]] = None) -> None:
        self.workspace_dir = Path(workspace_dir).resolve() if workspace_dir is not None else None
        if self.workspace_dir is not None:
            self.workspace_dir.mkdir(parents=True, exist_ok=True)

    @property
    def supported_operations(self) -> Set[str]:
        return {"list", "list_files", "read", "write"}

    def _resolve_safe_path(self, path_str: str, root_dir: Path, allow_empty: bool = False) -> Path:
        """Resolve path and enforce capability root boundary."""
        if not isinstance(path_str, str):
            raise ToolExecutionError(f"Argument 'path' must be a string, got {type(path_str).__name__}")

        if not path_str.strip():
            if allow_empty:
                return root_dir
            raise ToolExecutionError("Argument 'path' must be a non-empty string")

        raw_path = Path(path_str)
        if raw_path.is_absolute():
            resolved = raw_path.resolve()
        else:
            resolved = (root_dir / raw_path).resolve()

        try:
            if not resolved.is_relative_to(root_dir):
                raise ToolExecutionError(
                    f"Access denied: path '{path_str}' resolves outside capability root '{root_dir}'"
                )
        except ValueError:
            # Across drives on Windows
            raise ToolExecutionError(
                f"Access denied: path '{path_str}' is on a different drive or outside capability root '{root_dir}'"
            )

        return resolved

    def execute(
        self,
        operation: str,
        arguments: dict[str, Any],
        capabilities: Optional[List[Capability]] = None,
    ) -> Any:
        if operation not in self.supported_operations:
            raise OperationNotSupported(
                f"Operation '{operation}' is not supported by tool '{self.name}'. "
                f"Supported operations: {sorted(self.supported_operations)}"
            )

        if not isinstance(arguments, dict):
            raise ToolExecutionError(f"Arguments must be a dictionary, got {type(arguments).__name__}")

        # Resolve capability root
        if capabilities is not None:
            fs_cap = next((c for c in capabilities if isinstance(c, FilesystemCapability)), None)
            if fs_cap is None:
                raise ToolExecutionError("Access denied: action does not have filesystem capability granted")
            root_dir = fs_cap.root
        else:
            if self.workspace_dir is not None:
                root_dir = self.workspace_dir
            else:
                raise ToolExecutionError("Access denied: action does not have filesystem capability granted")

        root_dir.mkdir(parents=True, exist_ok=True)

        if operation in {"list", "list_files"}:
            raw_path = arguments.get("path", "")
            if raw_path is None:
                raw_path = ""
            safe_path = self._resolve_safe_path(raw_path, root_dir=root_dir, allow_empty=True)
            return self._list(safe_path, str(raw_path) if raw_path else ".")

        if "path" not in arguments:
            raise ToolExecutionError("Missing required argument 'path'")

        path_str = arguments["path"]
        safe_path = self._resolve_safe_path(path_str, root_dir=root_dir, allow_empty=False)

        if operation == "read":
            return self._read(safe_path, path_str)
        elif operation == "write":
            if "content" not in arguments:
                raise ToolExecutionError("Missing required argument 'content' for write operation")
            return self._write(safe_path, str(arguments["content"]))

    def _list(self, safe_path: Path, display_path: str) -> List[str]:
        if not safe_path.exists():
            raise ToolExecutionError(f"Directory not found: '{display_path}'")
        if not safe_path.is_dir():
            raise ToolExecutionError(f"Path is not a directory: '{display_path}'")

        try:
            return sorted([entry.name for entry in safe_path.iterdir()])
        except Exception as e:
            raise ToolExecutionError(f"Failed to list directory '{display_path}': {e}")

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
