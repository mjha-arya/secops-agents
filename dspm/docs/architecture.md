# dbSAT — architecture

- **Owner:** AgentDaya · **Decider:** Manish Jha · **Date:** 2026-09-27
- **Status:** Authored, not verified. Nothing here has run live. Every endpoint is still written from documentation.
- **Decisions of record:** ADR-0001 (stack), **ADR-0002** (runtime, store, dashboard, connector). Both are Proposed.
- **Requirements:** `program\prd\dbSat.md` (S1–S10). **Azure dependencies:** `azureConnectionModel.md`.
- **Blueprint home:** layer 4 (Posture) plus the phase-6 surface. dbSAT is the control tool running live, on a schedule, with history and a dashboard. It is **not a second scanner**.

## 1. One paragraph

A **check registry** (YAML, human-ratified) says what should be true. The **control tool** (`ctl`)
reads it, runs **read-only collectors** against the Databricks account, workspaces, Unity Catalog
system tables and ARM, **assesses** each observation deterministically into one of five buckets,
and writes a **run artifact** with hashed per-check evidence. A thin **posture adapter**
(`dspm\posture`) turns that artifact into **append-only Delta rows**. **Views** derive history, and
an **AI/BI dashboard** reads the views. Locally the same code runs on fixtures and writes SQLite.
Nothing in the path writes to a scanned setting.

## 2. Components

| # | Component | Lives in | Owner | Status | Reads | Writes |
|---|---|---|---|---|---|---|
| 1 | **Check registry** (`controlRegistry.yaml` + `bestPracticeRegistry.yaml`) | `controlTool\registry\` | Manish ratifies; Dino drafts | SEC part exists (31, unratified); SBP part not started | — | — |
| 2 | **Workspace inventory** | `controlTool\registry\workspaceInventory.yaml` | Manish | Placeholders | — | — |
| 3 | **Exception register** | `controlTool\registry\exceptionRegister.yaml` | Manish | Illustrative entries only | — | — |
| 4 | **Auth** (`ctl\auth.py`) | control tool | reuse | Exists, unit-tested, never live | env | memory only |
| 5 | **Config / preflight** (`ctl\config.py`) | control tool | reuse + extend | Exists | env, inventory | — |
| 6 | **Collectors** (7, `ctl\collectors\`) | control tool | reuse; route fixes | Exist; `HttpBackend` untested | REST, SQL, ARM | — |
| 7 | **Assess / adjudicate / report** (`ctl\stages\`) | control tool | reuse | Exist, 87 tests | observations | run artifact |
| 8 | **Posture adapter** (`dspm\posture\adapter.py`) | dspm | Dino, from spec | Not started | run artifact | `FindingRecord`s |
| 9 | **Store** (`FindingStore`: `SqliteStore`, `DeltaStore`) | `dspm\posture\store\` | Dino | Not started | — | own tables only |
| 10 | **Views** (`dspm\posture\sql\v_*.sql`) | dspm | Dino | Not started | store | — |
| 11 | **Job entry point** (`dspm\posture\job.py`) + bundle (`dspm\deploy\databricks.yml`) | dspm | Dino authors; **Manish deploys/unpauses** | Not started | secret scope | volume, Delta |
| 12 | **Dashboard** (`dspm\ui\dbsat.lvdash.json`) | dspm | Dino, from spec | Not started | views | — |
| 13 | **Coverage map** (`dspm\knowledge\satCoverage.yaml` + report) | dspm | Dino drafts; Manish ratifies | Not started (Q8) | registry | report |

**Reused, not forked** (F6 in ADR-0002):
- `dspm` imports `ctl`. It never copies a module.
- The control tool gains two things, neither of which forks it:
  - a `pyproject.toml`, so `ctl` installs as a package into the job's wheel;
  - two env overrides: `CTL_RUNS_ROOT` (artifacts to a UC volume) and `CTL_ENV_FILE` (the `.env` outside OneDrive).
- Every other change to `ctl` for dbSAT is a correction or a test: route fixes, the visibility guard (§ 6) and the request-log guard. Those changes land in `controlTool\`, which is Q10: Dino's write scope.

## 3. Data flow: check registry → dashboard

```
 controlRegistry.yaml ─┐
 bestPracticeRegistry ─┼─► [1 ingest]  ctl.registry.load + validate ─► registry.snapshot.json (+ sha256)
 workspaceInventory ───┤
 exceptionRegister ────┘
                              │
 env / secret scope ─► ctl.auth (token per audience) ─► ctl.config (hosts, settings, preflight)
                              │                                         │ missing → named, checks → unknown
                              ▼
          [2 discover]  7 collectors ── HttpBackend (GET, SELECT-only SQL) ──►  state.json (Observations;
                        (or FixtureBackend)                                     error set ⇒ observed meaningless)
                              ▼
          [3 assess]    deterministic diff vs desired ─► findings.json   (five buckets; unknown on any error)
          [4 adjudicate] offline rule brain (no model in scheduled path) ─► adjudication.json
          [5–6]         plan / simulate: empty while every check is `observe` (no write credential present)
          [10 report]   position.txt, evidence/<check>.json  (sha256 per record)
                              │            ─── scan boundary: nothing above writes anywhere but the run folder ───
                              ▼
          [publish]     dspm.posture.adapter  → FindingRecord (one per check × scope)
                        dspm.posture.store    → DeltaStore (job) | SqliteStore (local/tests)
                              │                 INSERT only, into <catalog>.dbsat.{runs,findings,evidence_index}
                              ▼                 evidence JSON copied byte-for-byte to /Volumes/<catalog>/dbsat/runs/<run_id>/
          [views]       v_finding_episodes, v_current, v_bucket_counts, v_run_health, v_coverage
                              ▼
          [dashboard]   AI/BI: Overview · Deviations · History · Coverage · Run health   (read-only)
```

**Run modes**

| Mode | Invocation | Backend | Artifacts | Store | Who |
|---|---|---|---|---|---|
| Fixture | `ctl.py run` | `FixtureBackend` | `controlTool\runs\` | SQLite (optional `dspm` publish) | anyone, CI |
| Local live | `ctl.py preflight` → `ctl.py run --live` | `HttpBackend` | `controlTool\runs\` | none (artifacts only) | **Manish** |
| Scheduled | Databricks job → `python -m dspm.posture.job` (= `ctl` run `--live` + publish) | `HttpBackend` | UC volume | Delta | job as SP; **Manish unpauses** |

The job never passes `--promote`, `--approve-all` or `--live-agent`. Its first act is a preflight.
Job-mode preflight adds one check to the usual ones: **it fails if `DATABRICKS_WRITE_TOKEN` or
`ANTHROPIC_API_KEY` is present in the environment.**

## 4. The merged registry

> Detailed schema superseded by `specs\dbSatSlice2.md` §2 (single `provenance {sec, sbp, sat}`
> block, `sources.yaml`, ordinal SBP numbering). The principles below stand.

**One registry, one row per check, provenance on the row.** It's still the control tool's
registry, because the registry is the contract. `dspm` never holds a second copy.

**Files.** One logical registry loaded from two files, so the two provenances get ratified in
separate reviews:
- `controlRegistry.yaml`: the 31 SEC records, including SEC records that also absorb an SBP practice.
- `bestPracticeRegistry.yaml`: SBP-only records.

The loader merges them into one namespace. A duplicate `id` or a duplicate `SBP` ref across files
fails `validate`.

**Record identity**

| Case | `id` | `refs` |
|---|---|---|
| Policy control | `SEC-06` (unchanged, so evidence file names, exceptions, tests and the 17/9/4/1/0 baseline don't churn) | `[SEC-06]` or `[SEC-06, SBP-12]` if merged |
| Vendor best practice with no SEC counterpart | `SBP-40` | `[SBP-40]` |

**Schema additions** (everything else in `ctl.models.Control` stays as it is):

```yaml
sources:                                   # top level: every document a ref can cite
  SEC: {title: "Databricks Security Policy", version: "0.5", ratified: false}
  SBP: {title: "Security Best Practices for Azure Databricks", version: "2.3", ratified: false}

controls:
  - id: SEC-06
    refs: [SEC-06, SBP-12]                 # required, non-empty; ^SEC-\d{2}$ | ^SBP-\d{2}$
    provenance:                            # one entry per ref
      - {ref: SEC-06, section: "§3", ratified: false}
      - {ref: SBP-12, section: "TODO (Q7)", ratified: false, disagreement: "SBP allows PAT with 90-day max; SEC disables"}
    sat_checks: []                         # vendor SAT check ids, reference only (Q8); used by the coverage map
    severity: high                         # SEC severity wins; SBP-only rows map High→high, Medium→medium, Low→low (Q5)
    # ... existing fields: title, domain, planes, detect, desired, implement, enforcement: observe ...
```

**Validation rules** (all in `ctl.registry.validate`, all tested; S1):
- `refs` must be non-empty, and each ref must match `^SEC-\d{2}$` or `^SBP-\d{2}$`. The error names the record.
- Every `refs` entry has exactly one `provenance` entry.
- An SBP id is cited by **exactly one** record across both files.
- A record's `id` must appear in its own `refs`.
- A merged record's `desired` value is the SEC value. Any disagreement goes on the provenance entry and into the import note for Manish.
- A record whose only detect modality is `manual` assesses `procedural`, never `compliant`. This already holds for SEC-26 and is extended to every SBP record with no API.
- `ratified` at record level is derived: true only if every provenance entry is ratified. It's stamped on every finding and drives the dashboard's "draft standard" banner.
- `policy_ref` is kept for backward compatibility and has to agree with the SEC provenance entry.

**Coverage map (S9).** `dspm\knowledge\satCoverage.yaml` maps each vendor SAT check id (pinned
v0.8.0) to one of: `covered: <dbSAT id>`, `not-applicable-azure: <reason>` or `gap`. The report is
generated from that file plus `sat_checks` in the registry, and both have to agree. **Ids only, no
vendor text, until Q8 is answered.**

## 5. Store and views

All tables live in `<catalog>.dbsat`, with `TBLPROPERTIES ('delta.appendOnly' = 'true')`. SQLite uses
the same columns.

| Table | Grain | Key columns |
|---|---|---|
| `runs` | one per run | `run_id` (UTC `YYYYMMDDTHHMMSSZ`), `started_at`, `finished_at`, `status` (`succeeded` \| `failed`), `failure_reason`, `runner` (`local` \| `job`), `estate` (`live` \| `fixture`), `registry_version`, `registry_sha256`, `code_version`, `account_id` |
| `findings` | check × scope × run | `run_id`, `check_id`, `refs` (array), `domain`, `severity`, `scope_type` (`workspace` \| `account` \| `metastore`), `scope_id` (workspace id / account id / metastore id, never the literal `"account"`), `status` (five buckets), `observed` (JSON), `desired` (JSON), `reason`, `method` (JSON), `ratified`, `exception_ref`, `evidence_path`, `evidence_sha256`, `collected_at` |
| `evidence_index` | evidence file × run | `run_id`, `check_id`, `path`, `sha256`, `bytes` |

- **Per-account checks (S5):** `ctl` scopes `account` and `metastore` are mapped by the adapter to `DATABRICKS_ACCOUNT_ID` and the metastore id. Each is assessed once and never fanned out per workspace.
- **Evidence hash:** `ctl` hashes **per check** (`evidence\SEC-06.json` covers every scope). So `findings.evidence_sha256` is that record's hash, and several scopes share it. The re-hash test recomputes it the way `report.evidence_pack` does: `sha256(json.dumps(record_without_sha256, indent=2, sort_keys=True, default=str))`.
- **Failed runs** write a `runs` row with `status=failed` and **no** `findings` rows. Nothing is overwritten, so nothing can flip to compliant (S7).

**Views** (derived, never stored):
- `v_finding_episodes`: gaps-and-islands over `findings` joined to succeeded runs. Returns `first_seen`, `last_seen` and `closed_at` per (check, scope, status episode). Implements S6.
- `v_current`: the latest **succeeded** run's findings, joined with the open episode's `first_seen`.
- `v_bucket_counts`: counts by bucket × severity × provenance × workspace. **Counts only.**
- `v_run_health`: last run, last succeeded run, hours since, and a `stale` flag. Also a `draft_standard` flag (any unratified source).
- `v_coverage`: the SAT coverage map joined to current status.

**No-percentage rule:** a unit test fails if any view definition or the dashboard JSON contains
`percent`, `pct`, `ratio`, a `/` between aggregates, or a percent number format.

## 6. Read-only and honesty guarantees (the review gate checks every one)

| Guarantee | Mechanism | Test |
|---|---|---|
| Scan issues GET + SELECT only | `HttpBackend` has no write method; `_sql` refuses non-`SELECT` | **Request-log guard:** every request in a live/recorded run is either a GET, the POST to `…/api/2.0/sql/statements` whose statement starts with `SELECT`, or the Entra token POST to `login.microsoftonline.com`. Anything else fails the run |
| Publish writes only its own tables | `DeltaStore` takes a fully qualified allowlist `<catalog>.dbsat.{runs,findings,evidence_index}`; INSERT only | Unit test that any other target raises |
| `unknown` on failure | `Collector._one` turns any exception, 401/403, 404 or missing setting into `error` → `unknown` | existing, plus 403 → HTTP status in evidence (S4) |
| **No false green from partial visibility** | `system.information_schema.*` is **privilege-filtered**: a non-admin sees fewer rows, not an error. "No ALL PRIVILEGES grants found" can simply mean "couldn't see them". New **visibility guard**: preflight records whether the SP is metastore admin (and account admin). If it isn't, every check whose assertion concludes from *absence of rows* (SEC-14 credentials, SEC-15 grants, SEC-16 tags) is forced to `unknown` with reason `insufficient-visibility` | Fixture test: non-admin marker + empty rows → `unknown`, never `compliant` |
| Self-declared values never green | `manual` modality → `procedural` | existing (SEC-26), extended to SBP |
| One-way doors unreachable | `one_way_door` filtered in plan; job has no write token | existing |
| Determinism | same input → same findings | existing, plus two-live-run comparison (dbSat-1.11) |

## 7. Known route corrections before the first live run

These all resolve to `unknown` today (a 404 becomes `NotCollected`), so they're honest. But they'll
all be red on run #1, and fixing them is dbSat-1.10 work. Found by reading `ctl\collectors\base.ROUTES`
and the collector prefixes:

| Target | Today | Should be (from docs, verify live) |
|---|---|---|
| `account/settings/identity-sourcing` (SEC-08) | `api/2.0/accounts/settings`, with no account id | `api/2.0/accounts/{DATABRICKS_ACCOUNT_ID}/…`. Needs account-id templating in `ROUTES` |
| `account/network-connectivity-configurations` (SEC-23) | no route; the literal is used as the path | `api/2.0/accounts/{account_id}/network-connectivity-configs` |
| `metastore/delta-sharing-scope` (SEC-29) | `api/2.1/unity-catalog/metastores` sent to the **accounts** host (scope `metastore` has no host) | either the workspace host `api/2.1/unity-catalog/current-metastore-assignment` → `metastores/{id}`, or the account API `api/2.0/accounts/{account_id}/metastores/{id}` |
| `workspace-conf/exfiltration-toggles` (SEC-18) | no route | `api/2.0/workspace-conf?keys=enableResultsDownloading,enableNotebookTableClipboard,enableExportNotebook,enableDbfsFileBrowser` |
| `dbutils.fs.mounts` (SEC-15) | placeholder SELECT that returns a constant | **Is a false-green risk today:** it returns one fake mount row. It must raise `NotCollected` (→ `unknown`) until a real method exists. **Blocking for the live run** |

The last row is a defect against "unknown is never compliant". It goes to Dino as the first item
of the slice-1 spec.

## 8. Scheduling

- Databricks Lakeflow job `dbsat-scan`, defined in `dspm\deploy\databricks.yml` (Asset Bundle).
  - One task: a Python wheel task running `dspm.posture.job:main`.
  - Compute: classic single-node job cluster, dedicated access mode, `run_as` = the scanner SP.
  - The cluster must conform to the SEC-21 cluster policy.
  - `timeout_seconds` 3600, `max_concurrent_runs` 1, retries 0. A failed run is recorded, not retried silently.
- **Cadence:** Q3. Default proposal: nightly 02:00 UTC. Deployed with `pause_status: PAUSED`, and Manish unpauses.
- **Entry point steps:**
  1. read secrets from the scope into the process env (never printed);
  2. run job-mode preflight;
  3. run `ctl` `--live` with `CTL_RUNS_ROOT` set to the volume;
  4. publish;
  5. exit non-zero on failure, after writing the `runs` row.
- **Failure notification:** the job's own email-on-failure to the SecOps DL. Anything richer is out of scope (PRD § 5).
- **Local:** no scheduler. The workstation isn't a runtime of record (ADR-0002 F1).

## 9. Evidence

Each finding carries: `check_id`, `refs`, `severity`, `scope_id`, `observed`, `desired`, `method`
(modality/target/assertion), `registry_version`, `registry_sha256`, `ratified`,
`evidence_sha256`, `evidence_path` and `collected_at`.

The evidence file in the volume is `ctl`'s own output, copied byte-for-byte. The `findings` row
points at it, and an auditor can re-hash it independently. Retention is Q4 (default proposal 365
days). Because the tables are `appendOnly`, pruning is a deliberate, logged property change, never
a routine job.

## 10. Build order (maps to roadmap D1–D4)

1. **D1:** `ctl` fixes only: the mounts false-green, route corrections, the visibility guard, the request-log guard, `CTL_ENV_FILE`, and preflight naming checks → unknown. Then Manish's local live run. No `dspm` code yet.
2. **D2:** registry `refs`/`provenance`/`sources` + validate rules + `bestPracticeRegistry.yaml` + coverage map.
3. **D3:** `pyproject.toml` for `ctl`, `CTL_RUNS_ROOT`, adapter, `FindingStore` (SQLite first, then Delta), views, job entry point, bundle.
4. **D4:** dashboard JSON, no-percentage test, docs changelog from the second-engineer reproduction.

Each step gets a spec in `dspm\docs\specs\` before code (`dbSatSlice1.md` first).

## Changelog

| Date | Change | Why |
|---|---|---|
| 2026-09-27 | First version | ADR-0002 |
