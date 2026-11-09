---
name: buildContext
description: Reusable code, stack defaults and the one failure mode AgentDino must design against in the DSPM
type: project
---

- **Reuse before write.** The control tool (`secopsCurrentProjects\databricks\controlTool\`) already
  has: seven read-only collectors (`ctl\collectors\`), a deterministic assess stage, a registry
  loader, per-audience token minting (`ctl\auth.py`), fixture backend + 87 stdlib tests. Layer 4
  of the DSPM is an adapter over its `runs\` artifacts, not a copy of its code. `agentDaya\mcp\dctMcp.py`
  shows the house pattern for a read-only MCP server (allow-listed argv, audit jsonl, `ToolError`).
- **Stack defaults (blueprint, until ADR-0001 says otherwise):** Python 3.14, stdlib `unittest`,
  `pyyaml`, `httpx`; SQLite for v1 stores; knowledge as YAML in `dspm\knowledge\`; no PowerShell.
- **The failure mode to design against:** a collection error that becomes a green. Every layer
  returns `unknown` on failure and the tests assert it — see the control tool's
  `assess.assess` and `collectors.base.Collector._one` for the pattern.
- **Why:** the product's value is *not missing* sensitive data; a false green converts unknown
  risk into believed safety. **How to apply:** every new collector/classifier gets a test where the
  upstream call raises and the result is `unknown`, before the happy-path test. Related:
  [[workstationConstraints]].
