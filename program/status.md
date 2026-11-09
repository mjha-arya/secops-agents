# Status

_Owner: AgentPradyuman. Rewritten after every hand-off; blockers always first._
_Updated 2026-09-27 (after turn A accepted; Dino's turn B running). **GitHub writes refused**
(unattended run; github MCP also failed: "Authorization header is badly formatted") — D1–D4 and
all dbSat items are mirrored in `roadmap.md`, not on the tracker. Project artifact **not**
regenerated this turn (as instructed)._

## Blockers — only Manish can clear

1. **Accept ADR-0001 and ADR-0002** (`dspm\docs\adr\0001-stack.md`, `0002-runtime-store-connector.md`,
   both Proposed). ADR-0001 is the M0 gate. Daya's hard condition: no D3/D4 build (store, job,
   dashboard) before both are accepted. Doesn't block slice 1.
2. **Non-prod workspace + SP (Q9 provisioning)** per `dspm\docs\azureConnectionModel.md` — blocks
   live run dbSat-1.9:
   - SP with grants **G1–G6** (§ 3): account admin, workspace `admins` + SQL access, CAN USE on one
     warehouse, system schemas enabled + granted, metastore admin, subscription Reader.
   - Env vars (§ 4, names only): `CTL_AUTH_MODE`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`,
     `AZURE_CLIENT_SECRET`, `DATABRICKS_ACCOUNT_ID`, `DATABRICKS_SQL_HTTP_PATH`,
     `AZURE_SUBSCRIPTION_ID`; later `CTL_ENV_FILE` (turn C item 6).
   - Secret **outside OneDrive** (`controlTool\.env` is synced). Until item 6 lands: session env only.
   - Must **not** be set: `DATABRICKS_WRITE_TOKEN`, static token escape hatches.
   - `registry\workspaceInventory.yaml`: one real non-prod row, other rows `governed: false`
     (human-owned file — Manish edits and commits).
3. **GitHub token** — `GITHUB_PERSONAL_ACCESS_TOKEN` appears set but malformed (MCP rejects the
   header). Fix it, then file D1–D4 + items from `roadmap.md`.
4. **CI host** — blocks the M0 "CI running `unittest`" deliverable (ADR-0001 § Not decided).
5. **Confirm 1.9 waits on turn C too** (my reading, `decisions.md` today): 1.9's done-when needs
   `requests.json` (item 8) and the preflight visibility line (item 7). Your recorded sequencing
   said "waits for turn B"; say if you meant to run live before turn C.

Owed by others (not blocking today): Nolan — O15 curated-schema rule into the PRD (not there
yet). Daya — O2, O3, O17 slice-2 proposals. Manish, later — Q3, Q4 (D3), Q5, Q7 (D2), Q6.

Cleared 2026-09-27: Q8 licence, Q9 (in principle), Q10 write scope, Q11/C3 (Daya: no ADR), O7
(Nolan, PRD S1 baseline), O15 and O16 decided, turn B/C sequencing, turn A committed.

## Gate evidence

| Milestone | Gate (verbatim) | Evidence | State |
|---|---|---|---|
| M0 / phase 0 | Manish accepts the stack ADR | ADR-0001 Proposed | authored, not accepted |
| D1 | The control tool works live and read-only. O1 minus the schedule | Turn A (spec items 1, 2, 5, 3a–3d): red run 35F/10E vs old code → 135/135 green; `validate` consistent; fixture baseline **16 / 8 / 4 / 1 / 2** (= spec prediction); Daya review **accepted** (`dspm\docs\specs\dbSatSlice1Review.md`). **Not live** — zero live runs | in progress — fixture-verified only |
| D2 | One registry, two provenances; vendor coverage evidenced | none | planned |
| D3 | Continuous posture with history. O1 fully | none | planned — ADR-gated |
| D4 | O2 and O3 | none | planned |

Baseline to watch in turn B: items 10, 11, 13, 14 must not move 16/8/4/1/2; item 12 (SEC-24, O16)
should move it to **16 / 7 / 4 / 1 / 3**. Any other movement = stop and report.

## Next hand-offs

| # | From → To | Needed | Done when |
|---|---|---|---|
| 1 | Dino → Manish → Daya | Turn B (1.12–1.16) hand-back; Manish runs the suite; Daya reviews (1.17) | Red runs recorded; suite green; `validate` 0; baseline 16/7/4/1/3; review clean |
| 2 | Daya → Manish | Proposed commits for turn B (control-tool + myAgents) | Committed |
| 3 | Daya → Dino | Turn C: items 6 → 7 → 8 → 9 (1.2a–1.8) | Per spec § (d); Daya review 1.18 clean |
| 4 | Manish | Blockers 2 (provisioning) in parallel with turns B/C, so 1.9 isn't waiting on it | `setup --check` + `preflight` "configuration complete" |
| 5 | Manish → Daya | Live run #1 (1.9) with O1/O4/O5/O6/O9 evidence | `requests.json` GET + SELECT only; 1.10.n items opened |
