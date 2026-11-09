---
name: workstationConstraints
description: Constraints on Manish's workstation and access that break naive builds
type: project
---

- **PowerShell ConstrainedLanguage mode** (WDAC + AppLocker), so write logic in Python. Call
  `<venv>\Scripts\python.exe` directly and never run `Activate.ps1`.
- **Azure CLI is signed in.** Call it as
  `"%ProgramFiles%\Microsoft SDKs\Azure\CLI2\python.exe" -IBm azure.cli ...`, because `az.cmd`
  mangles `?`, `(` and `$`.
- **Manish's identity is read-only on the production subscriptions.** A write test returned
  `AuthorizationFailed`. He's in `Azure-Devops-Prod-Deployment`, which suggests deployment is
  meant to go through a pipeline. `what-if` may also fail on permissions.
- **Interactive sign-in and PIM activation fail from an agent process.** Manish runs them in his
  own terminal (`/daily-AzRoles` for PIM).
- Virtual environments go in `%USERPROFILE%\.venvs\<name>`, not in OneDrive.

**Why:** each of these caused a real failure in this workspace.

**How to apply:** check this list before writing setup or deploy steps.
