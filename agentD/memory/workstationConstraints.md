---
name: workstationConstraints
description: CLM PowerShell, venv location, and app-only (no interactive sign-in) auth for AgentD
type: reference
---

- **PowerShell runs in ConstrainedLanguage mode** on this workstation - write logic in Python, not
  PowerShell (same constraint as every other agent here; see `myPersonalScripts\readme.md` for the
  canonical record).
- **Virtual environments live in `%USERPROFILE%\.venvs\<name>`**, never inside OneDrive - this repo
  is an OneDrive-synced folder, and package installs there sync badly and clutter the workspace.
- **AgentD's Graph access is app-only (client credentials), not delegated.** Unlike AppLocker or the
  Purview MCP, there is no interactive sign-in step for Manish to run - auth failures mean the app
  registration's permissions or its secret/certificate are wrong, not a missing `graphAuth.py`
  device-code login. See [[appRegistration]].
- AgentD has no shell tool access at all (`agent.py`'s `gate()` denies `Bash`/`PowerShell`
  unconditionally) - it doesn't need Azure CLI or any other shell command for a read-only
  Graph-only investigation.
