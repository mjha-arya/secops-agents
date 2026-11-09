# ADR-0001 — DSPM v1 stack

- **Status:** Proposed — awaiting Manish's acceptance (phase 0 gate)
- **Date:** 2026-09-27
- **Author:** AgentDaya
- **Decider:** Manish Jha
- **Source:** `agentDaya\knowledge\dspmBlueprint.md` § Stack — this ADR ratifies those defaults unchanged

## Context

Phase 0 of the blueprint closes when Manish accepts the stack. The DSPM is built by agents on a
workstation with fixed constraints:

- PowerShell runs in ConstrainedLanguage mode — scripting must be Python.
- Virtual environments must live in `%USERPROFILE%\.venvs\<name>`, never inside OneDrive.
- Layer 4 reuses the Databricks Control Tool (Python, stdlib `unittest`, YAML registry) — the
  DSPM should share its language and test runner so the adapter stays thin.
- v1 is Databricks-only, read-only through phases 1–4, single operator, no hosted service.
- Credentials must never be in the repo (SEC-09).

## Decision

Adopt the blueprint's stack defaults as the v1 stack:

| Concern | Decision |
|---|---|
| Language | Python 3.14 |
| Tests | stdlib `unittest`; tests run with no credentials (fixtures only) |
| Dependencies | `pyyaml` (knowledge files), `httpx` (HTTP); anything further needs a spec line justifying it |
| Shell | No PowerShell (CLM) |
| Layout | `dspm\` = `discover\` `classify\` `access\` `posture\` `remediate\` `ui\` `knowledge\` `tests\` `docs\adr\` `docs\specs\` |
| Posture layer | `posture\` is a thin adapter over the control tool's artifacts (read via `dct` MCP / `ctl.py` outputs) — never a copy or fork |
| Store | SQLite for v1 (inventory, graph, evidence); store access behind a small interface so Postgres is an ADR, not a rewrite |
| Connector | Databricks managed MCP only (UC functions, Genie, AI Search) + `system.*` tables; endpoints in `dspm\knowledge\connectors.yaml` |
| Credentials | Env var names only in the repo; OAuth on-behalf-of or SP secret in `.env`; provisioning is `needs_human` |
| Model use | Anthropic SDK: Batch API for bulk tier-3 classification, structured outputs, prompt caching on the taxonomy prompt. Default model per `claude-api` guidance; a cheaper model for bulk tiers only once measured (phase 4 gate) |
| UI | Built with the `frontend-design` plugin (phase 6); reads SQLite; no write actions in v1 |
| CI | `python -m unittest discover -s tests` on every change |

## Consequences

**Positive**
- One language and test runner across the control tool and the DSPM; no CLM friction.
- Zero-infrastructure store; the whole product runs from a venv on the workstation.
- Tests need no credentials, so Dino can build phases 1–3 before any access is provisioned.

**Negative / accepted risks**
- SQLite is single-writer — fine for one operator, not for a shared service. Moving to Postgres
  needs a new ADR.
- Databricks managed MCP is the only connector; tool calls inherit the caller's UC permissions,
  so discovery coverage is bounded by the provisioned identity. An under-privileged identity
  must surface as `unknown`, never as "no data found".
- Python 3.14 is recent; if a dependency lacks a 3.14 wheel, fall back needs an ADR amendment.

**Not decided here (open)**
- CI host: GitHub Actions on `mjha-arya/MyAgents` vs. local-only run. Needs Manish.
- Venv of record: blueprint DoD says `.venvs\agentDino`; `dspm\readme.md` Run section says
  `.venvs\agentDaya`. Proposed: tests run under `.venvs\agentDino` (Dino builds, Daya reviews
  in the same venv); readme to be corrected on acceptance.
- Minimum pinned versions of `pyyaml` / `httpx` — Dino proposes in the first spec's build.

## Verification

Authored, not verified. Accepted when Manish changes **Status** to `Accepted` and commits.
