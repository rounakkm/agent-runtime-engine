# Agent Runtime Engine (`agent-exec`)

A lightweight, systems-oriented execution runtime for autonomous agents.

> **Note**: Phase 1 is intentionally not an agent, policy engine, security framework, or sandbox. It establishes the execution substrate that later phases will build upon.

---

## 1. What is Agent Runtime Engine?

**Agent Runtime Engine (`agent-exec`)** is a low-level runtime layer through which autonomous agents execute actions in a controlled and structured environment. Rather than allowing agents or LLMs to directly execute arbitrary code or invoke system tools directly, all agent interactions are modeled as explicit, structured **Action Requests** handled by an intermediary runtime.

---

## 2. Why Does It Exist?

Direct tool invocation by autonomous agents introduces serious risks:
- Agents can run unconstrained operations without observation or interception.
- Unstructured execution leaks low-level system exceptions into agent loops.
- Security, capability gating, tracing, and sandboxing cannot be easily retrofitted if the execution path is tightly coupled to agent code.

`agent-exec` decouples agent reasoning from execution mechanics. Every action passes through a deterministic pipeline:

```text
Agent
  ↓
Action Request
  ↓
Runtime
  ↓
Tool Dispatcher
  ↓
Tool Registry
  ↓
Tool
  ↓
Execution Result
  ↓
Runtime
  ↓
Agent
```

---

## 3. Execution Architecture

```text
+-------------------------------------------------------------------+
|                           Agent Layer                             |
+-------------------------------------------------------------------+
                                  │
                       ActionRequest (JSON/Dict)
                                  ▼
+-------------------------------------------------------------------+
|                           AgentRuntime                            |
|  - Validates request format                                       |
|  - Manages execution pipeline                                     |
|  - Coordinates Dispatcher and Registry                            |
+-------------------------------------------------------------------+
                                  │
                                  ▼
+-------------------------------------------------------------------+
|                          ToolDispatcher                           |
|  - Resolves tool from Registry                                    |
|  - Validates requested operation against tool capabilities         |
|  - Executes tool and traps execution failures                     |
|  - Standardizes output into ExecutionResult                       |
+-------------------------------------------------------------------+
          │                                        │
          ▼                                        ▼
+-------------------+                    +-------------------+
|   ToolRegistry    |                    |    Tool Base      |
|  - Named tools    |                    |  - Abstract spec  |
|  - No duplicates  |                    +-------------------+
+-------------------+                              │
                                                   ├───────────────┬───────────────┐
                                                   ▼               ▼               ▼
                                            +------------+  +--------------+  +-----------+
                                            |  EchoTool  |  |FilesystemTool|  | ShellTool |
                                            +------------+  +--------------+  +-----------+
```

---

## 4. Action & Result Model

### Action Request

Agents submit structured requests:

```json
{
  "action_id": "act_001",
  "tool": "filesystem",
  "operation": "write",
  "arguments": {
    "path": "notes.txt",
    "content": "Hello world"
  }
}
```

### Execution Result (Success)

```json
{
  "action_id": "act_001",
  "status": "SUCCESS",
  "result": "File written successfully",
  "error": null
}
```

### Execution Result (Failure)

```json
{
  "action_id": "act_002",
  "status": "FAILED",
  "result": null,
  "error": {
    "type": "ToolNotFound",
    "message": "Tool 'foo' is not registered"
  }
}
```

### Error Taxonomy

Errors are strictly categorized:
- `InvalidAction`: Malformed action request structure or invalid parameter types.
- `ToolNotFound`: Requested tool name is not registered.
- `OperationNotSupported`: Requested operation is not supported by the resolved tool.
- `ToolExecutionError`: Tool encountered an expected or handled failure during execution (e.g., file not found, path violation, command failure).

---

## 5. Tool Abstraction & Built-In Tools

Every tool implements the `Tool` base class:

```python
class Tool(ABC):
    name: str

    @property
    @abstractmethod
    def supported_operations(self) -> Set[str]:
        ...

    @abstractmethod
    def execute(self, operation: str, arguments: dict[str, Any]) -> Any:
        ...
```

### Initial Tools (Phase 1)

1. **`EchoTool` (`echo`)**:
   - Operation: `run`
   - Deterministic echoing for pipeline verification.

2. **`FilesystemTool` (`filesystem`)**:
   - Operations: `read`, `write`
   - Restricted strictly to a specified workspace directory (path traversal and absolute paths outside the workspace are blocked).

3. **`ShellTool` (`shell`)**:
   - Operations: `run`, `exec`, `execute`
   - Synchronously executes commands within the workspace directory, capturing `stdout`, `stderr`, and `exit_code`.

---

## 6. How to Run Examples

Execute the basic execution example:

```bash
python examples/basic_execution.py
```

---

## 7. How to Run Tests

Run the test suite with pytest:

```bash
python -m pytest
```

---

## 8. What is Intentionally NOT Implemented Yet

To maintain architectural focus on the core execution substrate, the following are intentionally deferred to subsequent phases:
- LLM / Model integration & prompt management
- Capability-based authorization & permission policies
- Dynamic permission revocation
- State-aware security policies
- OS sandboxing (containers, bubblewrap, eBPF, seccomp)
- Distributed execution / remote tools / MCP
- REST / Web APIs and UI
- Agent memory, planning, or autonomous loops