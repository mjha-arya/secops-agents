---
name: workstationConstraints
description: Gated shell, CLM PowerShell, venv location and the API-key placeholder for AgentDino
type: reference
---

- **PowerShell runs in ConstrainedLanguage mode** — Python only; the PowerShell tool is refused
  (canonical record: `myPersonalScripts\readme.md`).
- **Shell is gated:** `Bash` asks Manish `y/N` per command interactively; refused in `--once`
  (list the commands instead). Test runner:
  `%USERPROFILE%\.venvs\agentDino\Scripts\python.exe -m unittest discover -s dspm\tests`.
- **Writes only to `dspm\` and `memory\`**; `dspm\docs\adr\` is Daya's; the control tool's
  `registry\`, `.env`, `ctl\`, `ctl.py` are a human's.
- **Auth (2026-09-27):** the org API key Manish supplied is workspace-unscoped — the API returns
  400 without an `anthropic-workspace-id` header — so it is parked as user env
  `ANTHROPIC_API_KEY_ORG_UNSCOPED`, not `ANTHROPIC_API_KEY`. With the key unset the CLI uses the
  claude.ai Contoso login (that is how AgentCID's first turn ran). To use the key: a
  workspace-scoped key, or `ANTHROPIC_CUSTOM_HEADERS="anthropic-workspace-id: <id>"`.
- venvs live in `%USERPROFILE%\.venvs\<name>`, never inside OneDrive; this agent's is `agentDino`.
