---
name: workstationConstraints
description: CLM PowerShell, venv location, no shell tool, and fixture-only operation for AgentDaya
type: reference
---

- **PowerShell runs in ConstrainedLanguage mode** on this workstation — the control tool and this
  agent are Python only (canonical record: `myPersonalScripts\readme.md`).
- **Virtual environments live in `%USERPROFILE%\.venvs\<name>`**, never inside OneDrive — this
  repo is OneDrive-synced and package installs there sync badly. AgentDaya's is `.venvs\agentDaya`.
- **AgentDaya has no shell tool.** `agent.py`'s `gate()` denies `Bash`/`PowerShell` unconditionally;
  every `ctl.py` invocation goes through `mcp\dctMcp.py`, which builds the argument vector itself
  and refuses `--live`, `--live-agent`, `--approve-all` and `--promote`. If a check needs a
  command, AgentDaya lists it for Manish to run.
- **Auth (2026-09-27):** a workspace-scoped `ANTHROPIC_API_KEY` is set at user level and works;
  an earlier org-level key is parked as `ANTHROPIC_API_KEY_ORG_UNSCOPED` (400 without
  `anthropic-workspace-id`). With the key set, claude.ai connectors are unavailable to the agent.
- **The gate is verified live (2026-09-27):** Write to `dspm\docs\adr\` allowed; Edit of
  `dspm\readme.md` denied "code is Dino's". `dspm\readme.md`'s phase table is therefore not Daya's
  to update — say so in the hand-off packet to Pradyuman/Dino instead of retrying.
- **Fixture-only until preflight is clean.** With none of the four flags, `ctl.py` always uses
  `FixtureBackend` regardless of what credentials are in the environment — so AgentDaya's numbers
  describe the recorded demo estate, never the tenant, until a human runs `--live` themselves.
- **Writes are limited to `dspm\docs\`, `dspm\knowledge\`, `program\`, `proposals\`, `memory\`
  and `knowledge\`.** Code under `dspm\` is AgentDino's (denied with "write the spec"); the
  control tool's `registry\`, `.env`, `ctl\` and `ctl.py` are denied — the registry is the
  contract and a human commits changes to it. Related: [[controlToolState]], [[pluginLoading]].
