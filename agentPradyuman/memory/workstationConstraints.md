---
name: workstationConstraints
description: No shell, CLM PowerShell, gated GitHub writes and the API-key placeholder for AgentPradyuman
type: reference
---

- **No shell tool** — `agent.py`'s `gate()` refuses `Bash`/`PowerShell`; PowerShell is
  ConstrainedLanguage on this estate anyway. List commands for Manish.
- **Writes only to `program\` and `memory\`.** Requirements are Nolan's, architecture Daya's
  (`dspm\docs\`), code Dino's (`dspm\`).
- **GitHub writes are gated:** the `github` plugin's MCP needs `GITHUB_PERSONAL_ACCESS_TOKEN`;
  every milestone/issue write asks Manish `y/N`; in `--once` they're refused, so the plan is
  mirrored into `roadmap.md` with a note.
- **Auth (2026-09-27):** the org API key Manish supplied is workspace-unscoped — the API returns
  400 without an `anthropic-workspace-id` header — so it is parked as user env
  `ANTHROPIC_API_KEY_ORG_UNSCOPED`, not `ANTHROPIC_API_KEY`. With the key unset the CLI uses the
  claude.ai Contoso login (that is how AgentCID's first turn ran). To use the key: a
  workspace-scoped key, or `ANTHROPIC_CUSTOM_HEADERS="anthropic-workspace-id: <id>"`.
- venvs live in `%USERPROFILE%\.venvs\<name>`, never inside OneDrive; this agent's is `agentPradyuman`.
