---
name: workstationConstraints
description: Gated shell, CLM PowerShell, venv location and the API-key placeholder for AgentCID
type: reference
---

- **PowerShell runs in ConstrainedLanguage mode** — Python only; the PowerShell tool is refused
  (canonical record: `myPersonalScripts\readme.md`).
- **Shell is gated:** `Bash` asks Manish `y/N` per command interactively (mainly
  `python inspectAgents.py …`); refused in `--once`, where the latest `reports\*.json` are the facts.
- **Writes only to `reports\` and `memory\`** — AgentCID never edits another agent.
- **Auth (2026-09-27):** CID's first real turn ($1.03, review of agentDino) ran on the claude.ai
  Contoso login because `ANTHROPIC_API_KEY` was unset. The org key Manish supplied is
  workspace-unscoped (400 without `anthropic-workspace-id`) and is parked as user env
  `ANTHROPIC_API_KEY_ORG_UNSCOPED`. `inspectAgents.py` needs no key and no model.
- venvs live in `%USERPROFILE%\.venvs\<name>`, never inside OneDrive; this agent's is `agentCID`.
  `inspectAgents.py` runs the import check (T1) with each *target* agent's own venv, not this one.
