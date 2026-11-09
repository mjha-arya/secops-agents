---
name: controlToolState
description: Verified vs unverified state of the Databricks Control Tool as of 2026-09-26, what blocks a live run, and the agreed order of next steps
type: project
---

**As of 2026-09-26 the tool has never touched a real system.** Everything it reports comes from
`fixtures\demo\observations.yaml` (107 recorded observations of a deliberately part-broken estate).

**Verified locally (2026-09-26):**
- `python ctl.py validate` — registry 0.5.0, 31 controls, 59 detect specs each routed to exactly
  one collector, internally consistent
- `python -m unittest discover -s tests` — 87/87 pass (the `secopsCurrentProjects\CLAUDE.md`
  status row still says "50 tests" — stale)
- `python ctl.py run` — 17 compliant, 9 deviation, 4 prerequisite-gap, 1 procedural, 0 unknown;
  drift demo catches `0.0.0.0/0` on analytics-prd; zero changes proposed because all 31 controls
  are `enforcement: observe`

**What blocks `--live`** (`ctl.py preflight`, 17 items): all four `workspaceInventory.yaml` URLs
are `adb-0000…` placeholders; no service-principal credential for any of the 7 planes; unset
`DATABRICKS_ACCOUNT_ID`, `DATABRICKS_SQL_HTTP_PATH`, `AZURE_SUBSCRIPTION_ID`,
`AZURE_LOG_ANALYTICS_RESOURCE_ID`, `ADO_ORG`. No `.env` exists.

**Why:** the registry was generated from the policy `.docx` by an agent and has not been
human-ratified; the exception register holds illustrative entries, not real approvals. Until both
are real, the adjudicator is a drift detector, not a judge.

**How to apply:** follow the tool README's next-steps order and don't skip ahead —
1. ratify the registry (every `desired` value, every `reversible`/`rollback` pair);
2. build the real exception register;
3. confirm the workspace inventory (governed set, real ids, per-workspace applicability);
4. `--live` read-only against one non-prod workspace with a reader SP — expect
   `collectors\base.ROUTES` to need correcting;
5. only then consider promoting SEC-24 to `suggest`.
Also: `databricksControlToolArchitecture.md` header still says "no code written against this yet"
— stale since 2026-09-07. Related: [[workstationConstraints]].
