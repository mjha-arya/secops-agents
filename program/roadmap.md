# Roadmap

_Owner: AgentPradyuman. Milestones are the blueprint's phases; a phase closes on its gate
evidence, not a date. Dates below are targets for planning conversations only._

_Tracker: **GitHub writes refused** (unattended run; github MCP also failed to connect —
auth header rejected). Every milestone and issue below is mirrored here and **not created on
GitHub**. Ids like `dbSat-1.3` are placeholders; Manish files them as `task`, `epic:dbSat`,
milestone = the D-row, and the placeholder is replaced by the issue number._

| Milestone | Blueprint phase | Gate | Target | Epics / issues | State |
|---|---|---|---|---|---|
| M0 Foundations | 0 | Manish accepts the stack ADR | — | ADR-0001 (`dspm\docs\adr\0001-stack.md`); GitHub milestone/issues not created — mirrored here | in progress — ADR authored (Proposed 2026-09-27), awaiting acceptance; CI deliverable not built |
| M1 See | 1 | Inventory matches what the workspace admin sees | — | — | not started |
| M2 Know | 2 | Precision measured on a labelled sample, recorded | — | — | not started |
| M3 Trace | 3 | One real finding traced asset → identity → control | — | dbSat slices 1–3 feed layer 4 here but do **not** close this gate (no layer 3) | not started |
| M4 Judge | 4 | Cost per 1k columns recorded; false-positive review done | — | — | not started |
| M5 Act | 5 | Clean apply and working rollback, in non-prod | — | Waits on registry ratification | not started |
| M6 Show | 6 | Reads like a product, not a console | — | dbSat slice 4 dashboard is candidate evidence; does not close this gate by itself | not started |

Gate wording above re-copied verbatim from `agentDaya\knowledge\dspmBlueprint.md` (M1–M6 had
drifted into paraphrase) — see `decisions.md` 2026-09-27.

### M0 deliverables (blueprint "Ships" column)

| Item | Evidence | State |
|---|---|---|
| `dspm\` skeleton | `dspm\readme.md`, layer folders; `dspm\tests\` holds only `.gitkeep` | authored |
| Blueprint | `agentDaya\knowledge\dspmBlueprint.md` | authored |
| ADR-0001 (stack) | `dspm\docs\adr\0001-stack.md`, Status: Proposed | authored, awaiting acceptance |
| CI running `unittest` | none — CI host open (ADR-0001 § Not decided) | planned |
| Venv of record + readme fix | ADR proposes `.venvs\agentDino`; `dspm\readme.md` says `.venvs\agentDaya` | planned, on acceptance |

---

## Epic dbSat (working name) — `program\prd\dbSat.md`

Delivery goal: the control tool scans one non-prod workspace and its account live, read-only,
on a schedule, against one two-provenance registry, with history, a five-bucket dashboard and
docs a second engineer can follow.

**Placement (settled — Daya answered Q11/C3 in `dspm\docs\specs\dbSatSlice1.md`: no ADR needed):**
dbSat is an epic over blueprint layer 4, run as its own milestones D1–D4 **alongside** M1–M6, not a
re-sequence of them. No D-milestone closes a blueprint phase gate. The AI/BI dashboard is dbSat's
own surface, not the phase-6 DSPM UI. **Condition:** no D3/D4 build (store, job, dashboard)
starts before Manish accepts ADR-0001 and ADR-0002; if that slips, it becomes an ADR.

### Milestones (= PRD § 8 release slices; gates copied verbatim)

| Milestone | Stories | Gate — "Proves" (PRD § 8, verbatim) | Provable against (verbatim) | Depends on | State |
|---|---|---|---|---|---|
| D1 dbSat slice 1 | S3, S4, S5 | The control tool works live and read-only. O1 minus the schedule | One non-prod workspace + its account (Manish provides the SP) | Turn B (1.12–1.16) + review; turn C (1.2a–1.8); Q9 provisioning (env vars, G1–G6, inventory row) | in progress — turn A fixture-verified + accepted; turn B building; never run live |
| D2 dbSat slice 2 | S1, S2, S9 | One registry, two provenances; vendor coverage evidenced | Fixtures, then re-run slice 1 live | D1 gate (for S2 import + live re-run); Q5, Q7; O15 PRD text; O2, O3, O17 proposals | planned — blocked (Q8, Q10 cleared) |
| D3 dbSat slice 3 | S6, S7 | Continuous posture with history. O1 fully | Same workspace, ≥3 scheduled runs | ADR-0001 **and** ADR-0002 accepted (hard condition, Q11 answer); Q3, Q4 | planned — blocked |
| D4 dbSat slice 4 | S8, S10 | O2 and O3 | Dashboard review + second-engineer reproduction | D3; ADR-0002 (dashboard surface); a named second engineer | planned — blocked |

### Workstreams and items

Each item = one Dino turn (or one Daya/Manish action where marked), traceable to a story and a
layer. **Where** = the folder the change lands in: `controlTool\` =
`secopsCurrentProjects\databricks\controlTool\` (its own git repo). **Q10 decided 2026-09-27:**
Dino may change `ctl\`, `tests\`, `fixtures\`, `ctl.py`, `README.md` with tests; `registry\` and
`.env` stay human-owned. **Spec #** = item number in `dspm\docs\specs\dbSatSlice1.md`.

**WS1 — Live read-only scan (D1)** — state as of 2026-09-27

| Id | Item | Spec # | Story | Where | Owner | Needs | State |
|---|---|---|---|---|---|---|---|
| dbSat-1.1 | Spec: slice-1 live scan (`dspm\docs\specs\dbSatSlice1.md`), incl. § (e) addendum | all | S3–S5 | `dspm\docs\specs\` | Daya | — | **authored** (Q11 answered in it) |
| dbSat-1.1a | Turn A: mounts placeholder, UC visibility guard, shared routing, four API paths | 1, 2, 5, 3a–3d | S4 | `controlTool\` | Dino | 1.1 | **fixture-verified + accepted** (red 35F/10E → 135/135; validate OK; 16/8/4/1/2; `dbSatSlice1Review.md`); committed both repos (myAgents `2e9e50d`) |
| dbSat-1.2 | Connection model (`dspm\docs\azureConnectionModel.md`): identity, G1–G9, env var names, egress, secrets | — | S3 | `dspm\docs\` | Daya | — | **authored** |
| dbSat-1.12 | Statement result completeness + typing (chunks, truncated, row count, types) — O8 | 10 | S4 | `controlTool\` | Dino | 1.1a | **in progress** (turn B) |
| dbSat-1.13 | Absence-based SQL can see the bad row (privilege UNION, untagged tables, LIMIT rule) — O12 | 11 | S4 | `controlTool\` | Dino | 1.12 | **in progress** (turn B) |
| dbSat-1.14 | Assertions read only live fields (SEC-06/25/28/01/03/07, `build_demo` fallback; SEC-24 per O16) | 12 | S4 | `controlTool\` | Dino | 1.13; O16 ✔ | **in progress** (turn B) — only item allowed to move the baseline → 16/7/4/1/3 |
| dbSat-1.15 | Host/token selection 13a–13e — O10, O11 | 13 | S4 | `controlTool\` | Dino | 1.14 | **in progress** (turn B) |
| dbSat-1.16 | Test strengthening (pr-test-analyzer) + `dspm\readme.md` D1 row fix | 14 | S4 | `controlTool\`, `dspm\` | Dino | 1.15 | **in progress** (turn B) |
| dbSat-1.17 | Review of turn B (`/code-review`, silent-failure-hunter, pr-test-analyzer) | — | S4 | `dspm\docs\specs\` | Daya | 1.12–1.16 + Manish's test run | planned |
| dbSat-1.2a | `CTL_ENV_FILE` override + OneDrive secret guard | 6 | S3 | `controlTool\` | Dino | 1.17 | planned (turn C) |
| dbSat-1.3 | `ctl.py preflight`: computed unknown list + UC visibility line | 7 | S3 | `controlTool\` | Dino | 1.2a | planned (turn C) |
| dbSat-1.4 | `ctl.py setup --check`: per-plane token/grant, GETs only | 8 | S3 | `controlTool\` | Dino | 1.3 | planned (turn C) |
| dbSat-1.5 | `GuardedSession` + `requests.json` request-log guard over a full pipeline | 8 | S4 | `controlTool\` | Dino | 1.3 | planned (turn C) |
| dbSat-1.6 | 403/401/404/timeout → `unknown`, run completes | 8 | S4 | `controlTool\` | Dino | 1.5 | planned (turn C) |
| dbSat-1.7 | Run-artifact record test via `dspm.posture` adapter | 9 | S4 | `dspm\posture\` | Dino | 1.6 | planned (turn C) |
| dbSat-1.8 | Per-account records once, attributed to account id | 9 | S5 | `dspm\posture\`, `controlTool\tests\` | Dino | 1.7 | planned (turn C) |
| dbSat-1.18 | Review of turn C | — | S3–S5 | `dspm\docs\specs\` | Daya | 1.2a–1.8 | planned |
| dbSat-1.9 | Live run #1: `ctl.py setup --check`, `preflight`, `run --live` on W; record O1, O4, O5, O6, O9 evidence | — | S4 | — | **Manish** runs | 1.17, 1.18; Q9 env vars + G1–G6 + inventory row | **blocked** |
| dbSat-1.10.n | API path / shape correction, **one item per failing collector**, opened from run #1's log (O1, O9 rulings land here) | — | S4 | `controlTool\` | Dino | 1.9 | planned |
| dbSat-1.11 | Determinism evidence: two consecutive live runs, identical (check_id, workspace, status, observed) | — | S4 | — | Manish runs, Daya reviews | 1.10.* | planned |

Ids 1.12–1.18 and 1.1a/1.2a were added 2026-09-27 for spec § (e) and the turn A/B/C split; 1.10
and 1.11 keep their meaning. See `decisions.md`.

**WS2 — Registry, two provenances, coverage (D2)**

| Id | Item | Story | Layer | Where | Owner | Needs |
|---|---|---|---|---|---|---|
| dbSat-2.1 | Spec: registry `refs` schema + SBP import + coverage report | S1, S2, S9 | 4 | `dspm\docs\specs\` | Daya | 1.1 |
| dbSat-2.2 | `validate`: `refs` required, `^SEC-\d{2}$`/`^SBP-\d{2}$`, duplicate SBP rejected (tests) | S1 | 4 | `controlTool\` | Dino | 2.1, Q10 |
| dbSat-2.3 | `ctl.py controls --provenance SEC\|SBP` (tests) | S1 | 4 | `controlTool\` | Dino | 2.2 |
| dbSat-2.4 | Baseline regression: 31 SEC unchanged → 17 / 9 / 4 / 1 / 0 | S1 | 4 | `controlTool\` | Dino | 2.2 |
| dbSat-2.5 | `manual` modality assesses `procedural`, never `compliant` (tests; O4 guard) | S2 | 4 | `controlTool\` | Dino | 2.1 |
| dbSat-2.6a–d | SBP import, four batches of ~17 (SBP-01..68), `observe`, `ratified: false`, + import note of SEC/SBP disagreements | S2 | 4 | `controlTool\registry\` | Dino drafts, **Manish ratifies** | D1 gate, Q5, Q7, Q8, Q10 |
| dbSat-2.7 | Coverage report vs vendor SAT v0.8.0: covered / not-applicable-on-Azure / gap, ids only | S9 | 4 | `dspm\posture\` or `controlTool\` per 2.1 | Dino | 2.1, Q8 |
| dbSat-2.8 | Live re-run of slice 1 with the extended registry | S1, S2 | 4 | — | Manish runs | 2.6d |

**WS3 — History and schedule (D3)**

| Id | Item | Story | Layer | Where | Owner | Needs |
|---|---|---|---|---|---|---|
| dbSat-3.1 | Spec: store, posture adapter, scheduler per ADR-0002 | S6, S7 | 4 → 5 "prove" | `dspm\docs\specs\` | Daya | ADR-0002 accepted |
| dbSat-3.2 | Findings history: first_seen / last_seen / closed_at; old rows unchanged (tests) | S6 | 4 | `dspm\posture\` | Dino | 3.1 |
| dbSat-3.3 | Posture adapter ingests run artifacts into the store — thin, no copy of the control tool | S6 | 4 | `dspm\posture\` | Dino | 3.2 |
| dbSat-3.4 | Evidence re-hash check equals stored evidence_sha256 (tests) | S6 | 4/5 | `dspm\posture\` | Dino | 3.3 |
| dbSat-3.5 | Scheduled run on the ADR-0002 runtime at the Q3 cadence | S7 | 4 | per ADR-0002 | Dino builds, Manish enables | 3.3, Q3 |
| dbSat-3.6 | Failed run recorded with reason; prior results kept; no flip to `compliant` (tests) | S7 | 4 | per ADR-0002 | Dino | 3.5 |
| dbSat-3.7 | Evidence: ≥3 scheduled runs on W, zero human action | S7 | 4 | — | Manish / Daya review | 3.6 |

**WS4 — Dashboard and docs (D4)**

| Id | Item | Story | Layer | Where | Owner | Needs |
|---|---|---|---|---|---|---|
| dbSat-4.1 | Spec: dashboard (`frontend-design`) on the ADR-0002 surface | S8 | UI (ph. 6) | `dspm\docs\specs\` | Daya | 3.1 |
| dbSat-4.2 | Five-bucket counts, no percentage anywhere, `unknown` its own bucket | S8 | UI | `dspm\ui\` or per ADR-0002 | Dino | 4.1 |
| dbSat-4.3 | Deviation list: severity then first_seen asc, required columns | S8 | UI | as 4.2 | Dino | 4.2 |
| dbSat-4.4 | Filters: workspace, severity, provenance, domain | S8 | UI | as 4.2 | Dino | 4.3 |
| dbSat-4.5 | Stale banner on failed latest run; "draft standard" banner while unratified | S8 | UI | as 4.2 | Dino | 4.2 |
| dbSat-4.6 | Architecture doc + changelog of reproduction questions | S10 | docs | `dspm\docs\` | Daya | 1.2, 3.1 |
| dbSat-4.7 | O2 review: 3 scripted questions answered from dashboard alone, recorded | S8 | UI | — | Daya | 4.5 |
| dbSat-4.8 | O3: second engineer reproduces setup from docs; zero Manish-only answers | S10 | docs | — | **named engineer (TBD)** | 4.6 |

## Dependencies and RAID
_One line each, dated, owner named. Decisions go to `decisions.md`._

- 2026-09-27 · Dependency · Manish · **ADR-0001 + ADR-0002 acceptance** — both Proposed. Hard condition (Daya, Q11): no D3/D4 build before both are accepted. Slice 1 unaffected.
- ~~2026-09-27 · Q11/C3~~ — cleared: Daya, no ADR needed (spec § Q11).
- ~~2026-09-27 · Q10~~ — cleared: Manish decided write scope (`decisions.md`).
- ~~2026-09-27 · Q8~~ — cleared: DB License permits internal use; legal check before any redistribution outside the firm.
- 2026-09-27 · Dependency · Manish · **Q9 provisioning** — decided in principle; still owed: SP with G1–G6 (`azureConnectionModel.md` § 3), the § 4 env vars (names only), one real non-prod row in `workspaceInventory.yaml` (others `governed: false`), secret outside OneDrive. Blocks dbSat-1.9.
- 2026-09-27 · Dependency · Nolan · **O15** curated-schema rule into the PRD (not yet there); Daya specs it in slice 2. Until then SEC-16 measures all non-system tables (honest red).
- 2026-09-27 · Dependency · Manish (run #1) → Daya · O1 AIM read API, O4 list pagination, O5 `ANY FILE` blindness, O6 nested metastore-admin groups, O9 raw NCC body — all evidence gathered on 1.9, rulings as 1.10.n items.
- 2026-09-27 · Dependency · Daya · O2 (visibility/collectable into registry), O3 (network-policies detect spec), O17 (audit SQL by workspace_id) — slice-2 proposals.
- 2026-09-27 · Dependency · Manish · Q5 severity mapping, Q7 SBP v2.3 location → block 2.6. Q3 cadence, Q4 retention → block 3.5 / 3.2. Q6 PAT vs SP → no item blocked.
- 2026-09-27 · Risk · Daya · Fixture-shaped assertions: turn A review found 7 critical pre-existing live false greens. Mitigated by turn B (1.12–1.16) before run #1; residual risk = more of the same class surfacing on run #1.
- 2026-09-27 · Dependency · Manish · CI host — blocks the M0 CI deliverable.
- 2026-09-27 · Dependency · Manish · `GITHUB_PERSONAL_ACCESS_TOKEN` — github MCP still fails: "Authorization header is badly formatted" (token var likely set but empty/malformed, not absent); tracker mirrored here.
- 2026-09-27 · Risk · Dino · Live API paths all written from docs — dbSat-1.10 may be up to 7 items; D1 slips with it.
- 2026-09-27 · Risk · Manish · SP holds admin roles (no read-only role exists) — least-privilege challenge; mitigated by dbSat-1.2 caveat + 1.5 write-guard test.
- 2026-09-27 · Risk · Manish · Registry unratified — findings judged against a draft; mitigated by registry_version + `ratified` on every finding and 4.5 banner.
- 2026-09-27 · Risk · Manish · Manish is the only live-run executor, SP provisioner, ratifier and gate-acceptor — single-person bottleneck on 1.9, 1.11, 2.6, 2.8, 3.7.
- 2026-09-27 · Risk · Daya · Python 3.14 wheel gap for `pyyaml`/`httpx` would force an ADR amendment; Dino to confirm on first build.
- 2026-09-27 · Assumption · Daya · Blueprint phases 1–3 build against fixtures, no credentials (ADR-0001). dbSat D1 is the first live-credential work in the programme.
