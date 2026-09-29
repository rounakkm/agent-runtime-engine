"""Capability models for the Agent Runtime Engine."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

from agent_runtime.errors import InvalidAction


@dataclass
class Capability:
    """Base representation of an execution capability."""
    type: str

    def to_dict(self) -> dict[str, Any]:
        """Convert capability to dictionary representation."""
        return {"type": self.type}

    @classmethod
    def from_dict(cls, data: Any) -> "Capability":
        """Construct a Capability from a dictionary."""
        if not isinstance(data, dict):
            raise InvalidAction(f"Capability data must be a dictionary, got {type(data).__name__}")
        cap_type = data.get("type")
        if cap_type == "filesystem" or "root" in data:
            return FilesystemCapability.from_dict(data)
        if not isinstance(cap_type, str) or not cap_type.strip():
            raise InvalidAction("Capability must have a non-empty 'type' string")
        return cls(type=cap_type)


@dataclass
class FilesystemCapability(Capability):
    """Capability granting access to the filesystem restricted to a root path."""
    root: Path

    def __init__(self, root: Union[str, Path] = "./workspace") -> None:
        super().__init__(type="filesystem")
        if not isinstance(root, (str, Path)):
            raise InvalidAction(f"Root path must be a string or Path, got {type(root).__name__}")
        if isinstance(root, str) and not root.strip():
            raise InvalidAction("Root path must be a non-empty string or Path")
        self.root = Path(root).resolve()

    def to_dict(self) -> dict[str, Any]:
        """Convert FilesystemCapability to dictionary representation."""
        return {
            "type": "filesystem",
            "root": str(self.root),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "FilesystemCapability":
        """Construct a FilesystemCapability from a dictionary."""
        if not isinstance(data, dict):
            raise InvalidAction(f"Capability data must be a dictionary, got {type(data).__name__}")
        if "root" not in data:
            raise InvalidAction("Missing required field 'root' for FilesystemCapability")
        root = data["root"]
        if not isinstance(root, (str, Path)) or (isinstance(root, str) and not root.strip()):
            raise InvalidAction("Field 'root' in FilesystemCapability must be a non-empty string or Path")
        return cls(root=root)
