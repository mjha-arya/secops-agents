# MCP Server Creator — Memory Index

- [MCP SDK v2 API](mcpSdkV2.md) — `MCPServer` rename; only `ToolError` reaches the model; `mcp_types`; snake_case annotations
- [Graph Purview quirks](graphPurviewQuirks.md) — delegated labels need `/me` (beta); audit is v1.0 with workload-scoped perms; httpx collapses `..`
- [Graph app registrations](graphAppRegistrations.md) — the existing SecOps Graph app is app-only; don't reuse it for delegated MCP scopes
- [Workstation constraints](workstationConstraints.md) — CLM PowerShell, venvs outside OneDrive, Manish does the interactive sign-in
- [Stack decisions](stackDecisions.md) — Claude via Agent SDK, MCP Python SDK v2, msal+httpx, local stdio MVP first, then Azure
