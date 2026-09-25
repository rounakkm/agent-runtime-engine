"""Basic execution example demonstrating Agent Runtime Engine."""

import json
from pathlib import Path
import sys

# Ensure src/ is on sys.path for direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agent_runtime import (
    ActionRequest,
    AgentRuntime,
    EchoTool,
    FilesystemTool,
    ShellTool,
)


def main() -> None:
    # 1. Initialize runtime
    runtime = AgentRuntime()

    # 2. Register initial tools
    workspace_dir = Path(__file__).resolve().parent.parent / "workspace"
    runtime.register_tool(EchoTool())
    runtime.register_tool(FilesystemTool(workspace_dir=workspace_dir))
    runtime.register_tool(ShellTool(workspace_dir=workspace_dir))

    print("Registered tools:", runtime.registry.list_tools())
    print("-" * 50)

    # 3. Submit echo action
    act_echo = ActionRequest(
        action_id="act_001",
        tool="echo",
        operation="run",
        arguments={"message": "hello"},
    )
    result_echo = runtime.execute(act_echo)
    print(f"[{result_echo.action_id}] {result_echo.status.value}")
    print(result_echo.result)
    print("-" * 50)

    # 4. Submit filesystem action (write)
    act_fs_write = ActionRequest(
        action_id="act_002",
        tool="filesystem",
        operation="write",
        arguments={
            "path": "greeting.txt",
            "content": "Hello from the agent execution runtime!\n",
        },
    )
    result_fs_write = runtime.execute(act_fs_write)
    print(f"[{result_fs_write.action_id}] {result_fs_write.status.value}")
    print(result_fs_write.result)
    print("-" * 50)

    # 5. Submit filesystem action (read)
    act_fs_read = ActionRequest(
        action_id="act_003",
        tool="filesystem",
        operation="read",
        arguments={"path": "greeting.txt"},
    )
    result_fs_read = runtime.execute(act_fs_read)
    print(f"[{result_fs_read.action_id}] {result_fs_read.status.value}")
    print(result_fs_read.result.strip())
    print("-" * 50)

    # 6. Submit shell action
    # Use standard echo command
    act_shell = ActionRequest(
        action_id="act_004",
        tool="shell",
        operation="run",
        arguments={"command": "echo hello from shell"},
    )
    result_shell = runtime.execute(act_shell)
    print(f"[{result_shell.action_id}] {result_shell.status.value}")
    if result_shell.result and isinstance(result_shell.result, dict):
        print(result_shell.result.get("stdout", "").strip())
    else:
        print(result_shell.result)
    print("-" * 50)

    # 7. Demonstrate structured error handling (unknown tool)
    act_err = ActionRequest(
        action_id="act_005",
        tool="unknown_tool",
        operation="run",
        arguments={},
    )
    result_err = runtime.execute(act_err)
    print(f"[{result_err.action_id}] {result_err.status.value}")
    print(json.dumps(result_err.to_dict(), indent=2))


if __name__ == "__main__":
    main()
