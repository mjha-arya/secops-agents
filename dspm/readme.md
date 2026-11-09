# DSPM

Contoso's Data Security Posture Management platform, built from scratch, Databricks-first.
**Architecture of record:** `..\agentDaya\knowledge\dspmBlueprint.md` — five layers, build order,
stack defaults, definition of done. **Team:** AgentNolan writes the PRD, AgentPradyuman plans,
AgentDaya (`..\agentDaya\`) specs and reviews, AgentDino (`..\agentDino\`) builds — hand-off via
`..\program\readme.md`. Manish approves every ADR and every commit.

**Status:** Phase 0 — skeleton. No layer built, nothing verified.

## Layout

```
discover\    layer 1 - inventory of data stores (Databricks managed MCP, system tables)
classify\    layer 2 - three-tier classification (regex/checksum -> UC tags/SITs -> Claude, sampled)
access\      layer 3 - identity -> asset graph
posture\     layer 4 - thin adapter over the control tool (secopsCurrentProjects\databricks\controlTool)
remediate\   layer 5 - propose -> approve -> apply -> verify -> evidence
ui\          phase 6 - dashboard (frontend-design plugin)
knowledge\   data, not code: connectors.yaml, taxonomy.yaml (P9)
tests\       stdlib unittest; runs with no credentials
docs\adr\    architecture decision records - one per deviation from the blueprint
docs\specs\  feature-dev specs, one per component, written before its code
```

## Phase status (keep current)

| Phase | Ships | Status |
|---|---|---|
| 0 | Skeleton, blueprint, ADR-0001 stack, CI running `unittest` | In progress — skeleton and blueprint exist; ADR-0001 written by AgentDaya 2026-09-27, **Proposed** (awaiting Manish); CI not set up |
| 1 | Discover against one non-prod Databricks workspace | Not started |
| 2 | Classify tiers 1–2 + `knowledge\taxonomy.yaml` | Not started |
| 3 | Access graph + posture adapter over the control tool | Not started |
| 4 | Classify tier 3 (Claude, Batch API, sampled) | Not started |
| 5 | Remediate for one reversible control, non-prod | Not started (gated on the control tool's registry being ratified) |
| 6 | Dashboard | Not started |

## Epic dbSat status (D-milestones, parallel to the phases — `program\roadmap.md`)

| Milestone | Status |
|---|---|
| D1 slice 1 (`docs\specs\dbSatSlice1.md`) | **Turn A** (control tool: items 1, 2, 5, 3a–3d) — verified and committed: red run 35F + 10E against old `ctl\`; fixture regenerated (7 planes, 103 keys); suite 135/135 OK; `ctl.py validate` consistent; `ctl.py run` = 16/8/4/1/2 as predicted (Manish ran it, 2026-09-27). Daya review: accepted 2026-09-27. **Turn B** (items 10–14) — verified and committed: red 42F + 3E; suite 182/182; `run` = 16/7/4/1/3 (O16). Daya review: accepted 2026-09-27. **Turn C** (items 15, 6, 7, 8, 9 incl. `posture\adapter.py`) authored by AgentDino 2026-09-27 — code + 57 CT tests + 18 dspm tests written, **not run** (unattended, shell refused); fixture not regenerated; baseline must hold at 16/7/4/1/3; hand-back `docs\buildNotes\dbSatSlice1TurnC.md`; awaiting Manish's run + Daya review. dbSat-1.9 live run waits on turn C |
| D2 slice 2 (`docs\specs\dbSatSlice2.md`) | **Turn A** (item A: provenance model, `sources.yaml`, V1–V10, two-file registry, legacy flag) authored by AgentDino 2026-09-27 — control-tool code + 41 tests written, **not run** (unattended); registry untouched; baseline must hold at 16/7/4/1/3 under `CTL_ALLOW_LEGACY_PROVENANCE=1`; hand-back `docs\buildNotes\dbSatSlice2TurnA.md`; awaiting Manish's run + Daya review. Items B–E not started |

## Run

```
%USERPROFILE%\.venvs\agentDaya\Scripts\python.exe -m unittest discover -s tests
```

Credentials (Databricks MCP token, SP secret) never live in this repo — see `knowledge\connectors.yaml`
for the environment variables and who provisions them.
