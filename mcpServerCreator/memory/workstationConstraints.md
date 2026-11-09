---
name: workstationConstraints
description: Constraints on Manish's workstation that break naive MCP server builds
type: project
---

- **PowerShell ConstrainedLanguage mode** (WDAC + AppLocker) applies to all PowerShell, so write
  server logic in Python. Don't run `Activate.ps1`. Call `<venv>\Scripts\python.exe` directly.
- **Virtual environments go in `%USERPROFILE%\.venvs\<name>`**. The repo is under OneDrive, and a
  venv there would sync thousands of files.
- **Interactive Entra sign-in fails from an agent process.** WAM has no parent window, and device
  code has a 120-second limit. Manish runs `graphAuth.py` (or the equivalent) in his own terminal.
  After that, servers use silent token acquisition from the DPAPI-encrypted cache.
- **Azure CLI is already signed in.** Use
  `"%ProgramFiles%\Microsoft SDKs\Azure\CLI2\python.exe" -IBm azure.cli ...` because `az.cmd`
  mangles `?`, `(` and `$`.
- Python 3.14 is installed.

**Why:** each of these caused a real failure or was probed directly (from 2026-08-26 to 2026-09-24).

**How to apply:** check this list before writing setup steps or running installs.
