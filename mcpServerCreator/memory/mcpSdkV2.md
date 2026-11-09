---
name: mcpSdkV2
description: MCP Python SDK 2.x API facts - MCPServer rename, ToolError-only error messages, mcp_types package, snake_case annotations
type: reference
---

In `mcp` 2.x, `from mcp.server.fastmcp import FastMCP` raises `ModuleNotFoundError`. Use
`from mcp.server.mcpserver import MCPServer` instead. The `@server.tool()` decorator and `.run()`
(stdio by default) work as before. Migration guide:
https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver

Other facts, checked against installed mcp 2.2.0 source (`%USERPROFILE%\.venvs\purviewMcp`) on
2026-09-24:
- **Only `ToolError` messages reach the model.** Import it from `mcp.server.mcpserver.exceptions`.
  Any other exception becomes the bare text "Error executing tool <name>". Raise `ToolError` for
  auth and Graph failures, or the model can't tell the human what to do.
- Protocol types live in a separate top-level package, **`mcp_types`** (dist `mcp-types`, pinned
  by mcp). There is no `mcp/types.py`.
- `ToolAnnotations` fields are **snake_case**: `read_only_hint`, `destructive_hint`,
  `idempotent_hint`, `open_world_hint`. Pass them with `@server.tool(annotations=...)`.
- `await server.list_tools()` and `await server.call_tool(name, args)` work without a transport.
  Useful for verification levels 1 and 3.
- mcp 2.2 depends on `httpx2`, not `httpx`.

**Why:** the rename was hit on 2026-09-24 on the first Purview build, and the draft's
`RuntimeError`s would have been invisible to the model. `approach.md` still shows the v1 import.
Manish chose v2 over pinning `mcp<2`.

**How to apply:** pin `mcp>=2,<3`. Treat any v1 sample code as needing translation. When unsure,
read the installed source under the venv rather than relying on recall.
