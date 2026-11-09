# AgentC (agent)

A Claude Agent SDK agent that builds and extends the certificate-expiry notification automation in
`certificateExpiryNotifications\`. It's a **builder**: it discovers, designs, writes and validates
IaC, and a human deploys it.

**Status:** Authored. The SDK import and the permission gate are tested. It hasn't done a real run yet.

## Phases

1. Defender TVM: finish the existing Logic App (reconcile the docs, validate, hand over, verify)
2. Azure Key Vault certificates
3. Entra app registration secrets and certificates
4. App Gateway / App Service TLS bindings

## Files

| File | Purpose |
|---|---|
| `soul.md` | Attitude, point of view and problem-solving steps. Appended to the Claude Code system prompt |
| `memory\MEMORY.md` + topic files | Persistent memory, seeded with the phase plan and the workstream's open conflicts |
| `agent.py` | Runner: interactive REPL, or `--once` for one unattended task |
| `runs\session*.md` | Audit trail: prompts, agent output and every permission decision (P12) |

## Guardrails (in `agent.py`)

- Read, Glob, Grep, WebFetch and WebSearch run automatically.
- Write and Edit are allowed **only** in `certificateExpiryNotifications\`, this agent's folder and `CLAUDE.md`.
- **Read-only Azure CLI** calls run automatically, through the CLI's `python.exe`. That covers
  `list`, `show`, `rest --method get`, `bicep build` and `deployment group what-if`. A call is
  refused if it has shell operators or mentions secrets, keys, app settings, credentials or tokens.
- Any other shell command asks you `y/N`. In `--once` mode it's refused automatically.
- Deploying, RBAC changes, consent and secret rotation are `needs_human` in `soul.md`.

## Run

```
python -m venv %USERPROFILE%\.venvs\agentC
%USERPROFILE%\.venvs\agentC\Scripts\python.exe -m pip install -r requirements.txt
%USERPROFILE%\.venvs\agentC\Scripts\python.exe agent.py --phase 1
```

This needs `ANTHROPIC_API_KEY`. To change the model, set `AGENTC_MODEL` (the default is
`claude-opus-5-5`).
