# ADR-0002 — dbSAT runtime, store, dashboard surface and connector

- **Status:** Proposed. Waiting for Manish to accept it.
- **Date:** 2026-09-27
- **Author:** AgentDaya
- **Decider:** Manish Jha
- **Resolves:** PRD `program\prd\dbSat.md` conflicts **C1** (store/runtime), **C2** (connector), Q1, Q2
- **Amends:** ADR-0001 (Proposed). The exact lines are in § "What this overturns"
- **Companion docs:** `dspm\docs\architecture.md`, `dspm\docs\azureConnectionModel.md`

## Context

dbSAT scans the security configuration of enrolled Azure Databricks workspaces and their account
against one registry, keeps the history and shows deviations by severity. Manish's instruction on
runtime was "find the best method". This ADR is that decision.

The forces, from the objective, the PRD and the code:

| # | Force | Source |
|---|---|---|
| F1 | It must run **unattended on a schedule** (O1). A workstation that sleeps, reboots and sits behind CLM can't be relied on to do that | Objective § Success 1; `workstationConstraints` memory |
| F2 | The dashboard must answer "what is wrong, how bad, since when" **without a query** (O2), for SecOps and CloudOps, who already work in Databricks | Objective § Success 2 |
| F3 | A second engineer must be able to **reproduce the setup from the docs** (O3). Every extra piece of infrastructure adds a page of docs and a way to fail | Objective § Success 3 |
| F4 | **Tests run with no credentials** (ADR-0001) and the control tool's 87 tests stay the safety net. Notebook-only code breaks this | ADR-0001; control tool README |
| F5 | **Observe-only.** The scan issues GET and SQL `SELECT` only. `HttpBackend` has no write method | PRD § 6; `ctl\collectors\base.py` |
| F6 | **The control tool is layer 4.** It gets reused as it is, not forked. `ctl` already writes a complete run artifact (`runs\<id>\findings.json`, `evidence\*.json` with SHA-256) | Blueprint; objective § Not this |
| F7 | **The managed MCP doesn't expose admin settings.** Workspace-conf, token management, IP access lists, cluster policies, account settings, NCCs and ARM are all REST-only. The control tool already reads them directly | `ctl\collectors\base.ROUTES`; `ctl\config.py` |
| F8 | **Evidence must stand up to an auditor.** It has to be append-only, timestamped and hashed, and not trivially editable by the people being assessed | PRD S6; blueprint invariants |
| F9 | **Serverless is not enabled in the estate.** SEC-16 and SEC-23 are blocked on it, so any job has to run on classic job compute | `controlRegistry.yaml` SEC-16 `blocked_by` |
| F10 | **Databricks runtimes ship Python 3.12**, not 3.14. Code that runs as a job has to be 3.12-compatible | DBR 16.4 LTS / 17.x LTS release notes. Confirm on first deploy |

## Options considered

### A. Hybrid: one Python package, two runners, Delta as the store of record, AI/BI dashboard

`ctl` (unchanged engine) plus `dspm\posture` (a thin adapter) are packaged as one wheel.
- **Local runner:** `ctl.py` on the workstation. Fixtures by default. `--live` when Manish runs it. Artifacts go to `runs\`. A SQLite mirror is used for tests and offline work.
- **Scheduled runner:** a Databricks Lakeflow job running the same entry point on a small classic job cluster. Artifacts go to a UC volume, and an append-only publish step writes them to Delta tables in a dedicated `dbsat` schema.
- **Dashboard:** an AI/BI dashboard over Delta views. The dashboard definition is versioned in the repo.

### B. Inside Databricks only: notebooks, jobs, Delta, AI/BI (the vendor SAT pattern)

The scan logic lives in notebooks deployed into the workspace. There's no local runner and no
package.

### C. Outside Databricks only: workstation runner, SQLite, own UI (ADR-0001 as written)

`ctl` runs from the workstation, either by hand or through a Windows scheduled task. Results go
into SQLite. A `frontend-design` web UI reads the SQLite file.

### D. Azure-hosted runner with a managed identity: Container Apps job, Delta over a SQL warehouse, AI/BI

The same package runs as a container in an Azure Container Apps job. It authenticates with a
**user-assigned managed identity** that is added to Databricks as a service principal, so there's
no client secret anywhere. It publishes to Delta through the Statement Execution API, and the
dashboard is AI/BI.

### Scoring

| Criterion | A Hybrid | B In-Databricks | C Outside + SQLite | D Azure runner + MI |
|---|---|---|---|---|
| F1 unattended schedule | ✅ Databricks job | ✅ | ❌ workstation availability; CLM blocks PowerShell-based task wrappers | ✅ |
| F2 dashboard without a query | ✅ AI/BI, native, zero hosting | ✅ | ⚠️ UI has to be built and hosted, and needs its own auth. Weeks of work before O2 | ✅ |
| F3 reproducible from docs | ✅ one bundle, one SP, one secret scope | ✅ | ⚠️ easy locally, but "reproduce" means "reproduce Manish's laptop" | ⚠️ adds ACR, Container Apps env, managed identity, image pipeline and VNet egress. CloudOps has to own new infrastructure |
| F4 credential-free tests | ✅ same package, fixtures | ❌ notebooks don't unit-test in CI | ✅ | ✅ |
| F5 observe-only provable | ✅ scan stage is `ctl` as-is; publish is a separate, allowlisted stage | ⚠️ same, but harder to test | ✅ | ✅ |
| F6 reuse, not fork | ✅ `ctl` imported as a package | ❌ re-implement in notebooks, which is a fork in all but name | ✅ | ✅ |
| F8 evidence integrity | ⚠️ Delta `appendOnly` + SHA-256, but it sits inside the assessed estate (see Consequences) | ⚠️ same | ❌ one SQLite file on a laptop, synced by OneDrive | ✅ runner outside the estate; store still inside |
| Credential posture | ⚠️ one SP client secret, held in a Key Vault-backed secret scope | ⚠️ same | ⚠️ secret in `.env` inside OneDrive (today's `ctl` default) | ✅ no secret at all |
| New infrastructure | Low: one job, one schema, one volume, one dashboard | Low | None | High |
| Fits blueprint/ADR-0001 | Amends store, connector, UI and Python lines | Violates F4/F6 | Fits as written | Amends the same lines as A, plus hosting |

## Decision

**Option A — hybrid.** Same package, two runners. Delta is the store of record, AI/BI is the
dashboard, and collectors use direct read-only REST.

1. **Runtime.**
   - One Python package: `ctl` (the control tool, made installable) plus `dspm.posture` (adapter and publisher).
   - **Local runner:** development, fixtures and Manish's first live runs.
   - **Scheduled runner:** a Databricks job on classic single-node job compute (serverless isn't available, F9), deployed with a Databricks Asset Bundle. For v1 the job runs in the enrolled non-prod workspace. The prod target is a dedicated tooling workspace. That's a config change, not a new ADR.
   - The job is deployed **paused**. Unpausing it is Manish's act: a scheduled `--live` scan is a standing `--live`, so it stays `needs_human`.
2. **Store.**
   - **Store of record:** Delta tables in UC catalog/schema `<catalog>.dbsat` (the name lives in `dspm\knowledge\dbsat.yaml`, P9). The tables are `runs`, `findings` and `evidence_index`, all **append-only** (`delta.appendOnly = true`). History (first_seen / last_seen / closed_at) is **derived in views**, never updated in place.
   - The per-run evidence JSON (`ctl`'s existing output) is copied unchanged to a UC volume `<catalog>.dbsat.runs`.
   - **SQLite stays** as the local/test implementation behind the same `FindingStore` interface ADR-0001 asked for.
3. **Dashboard.**
   - An **AI/BI dashboard** over `v_*` views. Its `.lvdash.json` lives in the repo and is deployed by the bundle.
   - No view exposes a ratio or percentage column. That rule is test-enforced.
   - The `frontend-design` UI stays blueprint phase 6 for the wider DSPM and will read through the same store interface. dbSAT doesn't wait for it.
4. **Connector (C2).** "Managed MCP only" **does not hold for deterministic collectors**. Decision:
   - **Deterministic collectors** (layer 4 now, and layers 1/3 where the MCP has no coverage) call the Databricks **workspace REST API, account REST API and SQL Statement Execution API** directly, plus ARM, and Graph/ADO for the extended planes.
   - They are read-only by construction: GET only, with one allowlisted POST (`/api/2.0/sql/statements` carrying a statement that starts with `SELECT`, which `ctl` already enforces) and the Entra token POST.
   - **The managed MCP stays the connector for agent-facing tools** (Genie, UC functions, AI Search), where a model is the caller. A deterministic scanner doesn't need a model-shaped interface.
   - The MCP doesn't expose workspace-conf, token management, IP access lists, cluster policies, account settings or NCCs. It also can't be the audit method of record for a check that has to be reproducible call for call.
5. **Identity.**
   - One Entra ID service principal per environment (`dbsat-scanner-nonprod`). Its client secret sits in a Key Vault-backed secret scope for the job and is **never** in a file in OneDrive.
   - Local live runs use `CTL_AUTH_MODE=azcli` or an env file outside OneDrive. The details are in `azureConnectionModel.md`.
   - **Option D is the named upgrade path** for prod, because it removes the secret. The package doesn't change, only the runner. It needs its own ADR when prod enrolment starts.
6. **Model use.** The scheduled scan uses the deterministic offline adjudicator only. There's no `ANTHROPIC_API_KEY` in the job and no model in the scheduled path.

## What this overturns

**ADR-0001** (`dspm\docs\adr\0001-stack.md`). Once this ADR is accepted, these lines change:

| ADR-0001 line | Now reads | Why |
|---|---|---|
| Context: "v1 is Databricks-only, read-only through phases 1–4, single operator, **no hosted service**." | "…single operator; dbSAT runs as a Databricks job in addition to the workstation." | F1 |
| Decision table, **Language**: "Python 3.14" | "Python code must run on **3.12** (Databricks runtime). Developed on 3.14, and CI runs on both 3.12 and 3.14" | F10 |
| Decision table, **Store**: "SQLite for v1 (inventory, graph, evidence); store access behind a small interface…" | "dbSAT store of record: **Delta (UC), append-only**. SQLite is the local/test implementation behind the same `FindingStore` interface. Postgres is still an ADR away." | F1, F2, F8 |
| Decision table, **Connector**: "Databricks managed MCP only (UC functions, Genie, AI Search) + `system.*` tables…" | "**Deterministic collectors: direct read-only REST** (workspace, account, SQL Statement Execution, ARM; Graph/ADO extended). **Agent-facing tools: Databricks managed MCP.** Endpoints in `dspm\knowledge\connectors.yaml`." | F7 |
| Decision table, **UI**: "Built with the `frontend-design` plugin (phase 6); reads SQLite; no write actions in v1" | "dbSAT: **AI/BI dashboard over Delta views**, no write actions. DSPM phase-6 UI: `frontend-design`, reading through the store interface." | F2, F3 |
| Decision table, **Dependencies**: "`pyyaml`, `httpx`…" | Add: `pyspark` is **provided by the runtime** (it's imported only in `dspm.posture.publish_delta` and is never a pip dependency). `requests` stays for `ctl` (it already uses it). The Databricks CLI is a deployment tool, not a dependency | F6 |
| Consequences: "Zero-infrastructure store; the whole product runs from a venv on the workstation." | "Local mode is zero-infrastructure. Scheduled mode needs one job, one schema, one volume, one secret scope and one dashboard." | — |

**Blueprint** (`agentDaya\knowledge\dspmBlueprint.md`). Daya edits it **only after acceptance**:
- § Stack **Store** "SQLite for v1 (inventory, graph, evidence)" → same wording as the ADR-0001 Store row above.
- § Stack **Connector** "Databricks managed MCP only…" → same wording as the ADR-0001 Connector row above.
- § Stack **UI** "…reads from the SQLite store…" → same wording as the ADR-0001 UI row above.
- § Stack **Language** "Python 3.14" → "Python 3.12-compatible, developed on 3.14".
- Layer table row 1 "via the Databricks managed MCP and `system.*` tables" → no change here. Layer 1 isn't in scope for dbSAT.

**Not changed:** the five-bucket invariant, `unknown` ≠ `compliant`, observe-only, the layout of `dspm\`, stdlib `unittest`, and credentials as env var names only.

## Consequences

**Positive**
- O1 is reachable without a new hosting platform, and O2 without building a web app.
- `ctl` stays one codebase. The job imports it, so its 87 credential-free tests keep guarding the scheduled path.
- History is append-only and derived, so an auditor gets immutable rows plus re-hashable evidence files (S6).
- Publishing is a separate stage with a write allowlist of exactly `<catalog>.dbsat.*`. The scan stage keeps its GET/SELECT-only guarantee (S4), and each property is tested on its own.

**Negative / accepted risks**
- **The observer lives inside the observed estate (v1).** A workspace admin of the non-prod workspace could alter the job or the `dbsat` tables.
  - Mitigations: `appendOnly` tables, SHA-256 evidence mirrored in the volume and re-hash-checked, the job owned by the SP, and grants on `dbsat` limited to the SP (write) and `secops-readers` (SELECT).
  - The real fix is the prod topology: a tooling workspace, or Option D.
- **One long-lived client secret** (`AZURE_CLIENT_SECRET`) in a Key Vault-backed scope. It needs rotation and expiry monitoring, and SEC-12 will report it against our own tool. That's correct behaviour, not something to waive. Option D removes it.
- **The job compute has to pass dbSAT's own checks** (SEC-21 cluster policy, SEC-25 artifact allowlist if standard access mode). Treat this as dogfooding, not an exception.
- **Deployment needs the Databricks CLI** (`databricks bundle deploy`). Whether it runs under WDAC/AppLocker on this workstation is unverified. The fallback is an ADO pipeline. `needs_human`.
- **Two store implementations** (Delta, SQLite) behind one interface. The contract tests have to run against both, or they'll drift.
- **Python 3.12 floor.** No 3.13+ syntax or stdlib, in `ctl` or `dspm`.

**Not decided here (open)**
- Cadence (Q3). Proposed default: nightly 02:00 UTC, matching the control tool's design. Manish decides.
- Retention (Q4). Proposed default: 365 days, matching SEC-03. `appendOnly` means pruning is a deliberate, logged property flip.
- Tooling-workspace topology for prod, and Option D. Separate ADR at prod enrolment.
- Sequencing (C3/Q11). **Daya's view: no ADR needed.** dbSAT *is* blueprint layer 4. Running it as parallel D-milestones changes no blueprint default and closes no phase gate. That's a program decision for `decisions.md` (Pradyuman).

## Verification

Authored, not verified. No part of this runtime has been deployed. It's accepted when Manish sets
**Status** to `Accepted` and commits. The design is proven when D3's gate is met: at least 3
scheduled runs on the non-prod workspace with zero human action.
