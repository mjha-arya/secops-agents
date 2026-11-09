# AgentD (agent)

A Claude Agent SDK agent that investigates Microsoft Defender XDR alerts and incidents. Give it a
`security.microsoft.com` link; it pulls the alert/incident and its evidence via a local read-only
MCP server, checks its memory, and writes a findings report to
`defenderAlertInvestigation\investigations\`. It's **investigate-only**: no write tools, no shell
access, no containment or remediation action, ever.

**Status:** Authored, not verified (P11). Blocked on Graph app permissions - see
`memory\appRegistration.md`.

## Files

| File | Purpose |
|---|---|
| `soul.md` | Attitude, point of view and the investigation workflow. Appended to the system prompt |
| `memory\MEMORY.md` + topic files | Persistent memory: app-registration status, workstation constraints, and accumulated investigation learnings |
| `mcp\defenderMcp.py` | Read-only MCP server (stdio): `resolve_link`, `get_alert`, `get_incident`, `list_incident_alerts` over Microsoft Graph's `security` API |
| `mcp\graphAuth.py` | App-only (client-credentials) Graph auth for the MCP server |
| `agent.py` | Runner: pass a link as an argument, or run interactively |
| `runs\session*.md` + `runs\toolCalls*.jsonl` | Audit trail: prompts, agent output, permission decisions, and every Graph call (P12) |

## Guardrails (in `agent.py` and `mcp\defenderMcp.py`)

- Read, Glob, Grep, WebFetch, WebSearch and the four `defender` MCP tools run automatically - all
  are read-only.
- `Bash` and `PowerShell` are refused unconditionally; AgentD has no shell access at all.
- Write and Edit are allowed **only** in `defenderAlertInvestigation\`, this agent's `memory\`
  folder, and `CLAUDE.md`.
- The MCP server has **no write tools** - it physically cannot change alert state, comment,
  classify, or take a containment action, independent of anything the model decides to try.
- Any other tool call asks `y/N` interactively; in `--once` mode it's refused automatically.

## Setup (needs_human)

See `memory\appRegistration.md` for the full finding. In short:

1. Add application permissions `SecurityAlert.Read.All` and `SecurityIncident.Read.All` to the
   shared app `SecOps - Microsoft Graph Access` (`00000000-0000-0000-0000-000000000000`) and grant
   admin consent.
2. Provision a credential for that app - a certificate is preferred over a client secret:
   - `setx SECOPS_GRAPH_CERT_PATH <path to a PEM private key outside OneDrive>`
   - `setx SECOPS_GRAPH_CERT_THUMBPRINT <thumbprint>`
   - or, less preferred: `setx SECOPS_GRAPH_CLIENT_SECRET <secret>`
3. Open a new terminal so the environment variable is picked up.

## Run

```
python -m venv %USERPROFILE%\.venvs\agentD
%USERPROFILE%\.venvs\agentD\Scripts\python.exe -m pip install -r requirements.txt

REM confirms the credential works (not that the permissions are consented - see step 1 above)
%USERPROFILE%\.venvs\agentD\Scripts\python.exe mcp\graphAuth.py

%USERPROFILE%\.venvs\agentD\Scripts\python.exe agent.py "https://security.microsoft.com/alerts/<id>?tid=..."
```

This needs `ANTHROPIC_API_KEY`. To change the model, set `AGENTD_MODEL` (default `claude-opus-5-5`).

## Known gaps

- No entity-correlation tool yet (e.g. "has this IP/host/user shown up in other recent alerts") -
  Graph's `alerts_v2` doesn't support filtering by evidence fields, so this needs either a bounded
  client-side scan or a different API. Deferred until a real investigation shows it's needed (avoid
  building speculative scope, per the automation principles' toil-first rule).
- `EVIDENCE_FIELDS` in `mcp\defenderMcp.py` is a starting allow-list, not exhaustive - extend it once
  real evidence payloads are seen (see `memory\investigationApproach.md`).
- Nothing has been run against the tenant yet; the MCP server's tool set is authored against the
  documented Graph `security` API shape, not verified against a real alert.
