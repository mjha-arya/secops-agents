# AgentDaya — Memory Index

- [Control tool state](controlToolState.md) — what the Databricks Control Tool has and hasn't
  verified, the placeholders that block a live run, and the agreed next-steps order
- [Plugin loading](pluginLoading.md) — how the six plugins reach this agent (user-scope install +
  `setting_sources`), their exact skill/agent names, and their context cost
- [Workstation constraints](workstationConstraints.md) — CLM PowerShell, venvs outside OneDrive,
  gated shell, fixture-only until preflight is clean
- [False-green sources](falseGreenSources.md) — filtered/truncated/chunked reads, placeholders, and
  fixture-shaped assertions (keys only the fixture has); ask "can this be compliant from an empty
  read, or from a key the live API never returns?" in every review
- [Schema transitions](schemaTransitions.md) — legacy registry shape is detected from data, never
  an env flag; grep every `registry.load` caller before approving a migration

The DSPM architecture itself is not memory — it is `..\knowledge\dspmBlueprint.md`, loaded into
every session. ADRs live in `..\..\dspm\docs\adr\`.
