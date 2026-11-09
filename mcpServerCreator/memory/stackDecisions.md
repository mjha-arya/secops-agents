---
name: stackDecisions
description: Stack choices Manish made for the SecOps MCP program, and why
type: project
---

Decided on 2026-09-24:
- **Model:** Claude, run through the Claude Agent SDK (Python). The earlier idea of hosting an
  open-source model on Azure was dropped for this agent, because the Agent SDK only runs Claude models.
- **MCP servers:** MCP Python SDK **v2** (`MCPServer`), one server per product, starting with
  **Purview**. Defender comes next.
- **Buy before build:** check the Microsoft Sentinel MCP and Azure MCP Server for coverage first.
- **Stages:** a local stdio MVP on Manish's device first. Later, move to Azure (Container Apps,
  Managed Identity, private networking) without changing the tool contracts.
- **Layout:** agents live in `secopsAutomationOperations\agents\<agentName>\`. MCP servers live in
  `secopsAutomationOperations\<serverName>\` (for example `purviewMcp\`).
- **Graph client:** `approach.md` suggests `msgraph-sdk` + `azure-identity`. The first Purview draft
  used `msal` + `httpx` instead, because it's lighter and gives exact control over OData. On
  2026-09-24 Manish said to keep msal + httpx unless there's a concrete reason to switch.

**Why:** Manish's explicit answers to the pre-build questions.

**How to apply:** don't re-ask these questions. Build to them.
