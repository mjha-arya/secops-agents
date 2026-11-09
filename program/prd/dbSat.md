# PRD — dbSAT (working name)

- **Owner:** AgentNolan · **Decider:** Manish Jha · **Date:** 2026-09-27 · **Status:** Draft for review
- **Objective:** `program\objective.md` § Active (set 2026-09-27)
- **Blueprint home:** layer 4 (Posture) + phase 6 UI — an epic over the control tool, not a new product
  (`agentDaya\knowledge\dspmBlueprint.md`)
- **Shape:** Contoso spec conventions (`tech-pdp-spec-writer`): Gherkin criteria, TODO markers for
  unknowns, decisions and open questions kept apart. Section order follows AgentNolan's soul.
- **GitHub:** stories are **not filed** — unattended run, GitHub writes refused (and the github MCP
  failed to connect). They live in § Stories below; Manish files them as `story`, `epic:dbSat`.
- **Grilling:** `/grilling` is interactive-only; the interrogation was done inline — answers are
  folded into the sections, unknowns are in § Open questions.

---

## 1. Problem

The Databricks Security Policy v0.5 (SEC-01..31) is being ratified, and SecOps can't show,
continuously and with evidence, whether our Azure Databricks estate meets it. The only
off-the-shelf option, the vendor's Security Analysis Tool (SAT), checks the vendor's list, not
ours, has no SLA ("for exploration purposes only … not formally supported"), and has to be
installed and configured by hand as notebooks in the workspace. Today, answering "what's wrong,
how bad, since when" means someone running ad-hoc checks.

- **Problem:** there's no continuous, evidence-backed assessment of Azure Databricks security configuration against *our* policy.
- **Users:** SecOps engineers (weekly), CloudOps (platform owner), auditors/insurers (evidence).
- **Outcome:** one registry, scanned without manual steps, deviations by severity on a dashboard, reproducible from docs.

## 2. Discovery — what already exists (P2)

Roughly half of dbSAT is already built. What's left is live running, the second provenance,
persistence, the dashboard and the docs.

| Asset | Path / source | What it already gives dbSAT | Gap for dbSAT |
|---|---|---|---|
| Control tool | `secopsCurrentProjects\databricks\controlTool\` | Registry → 7 read-only collectors → deterministic assess → adjudicate → five-bucket position → per-control evidence. 87 tests. `unknown` ≠ compliant is enforced | **Never run live.** Every API path and SQL statement is written from docs. `HttpBackend` is untested |
| Control registry | `…\controlTool\registry\controlRegistry.yaml` | 31 controls, 59 detect specs, all `enforcement: observe`. Severity scale `critical/high/medium/low` (5/17/8/1) | Single provenance (policy only). Not ratified (`policy: "… v0.5 (DRAFT — not ratified)"`) |
| Live setup + auth | `…\controlTool\ctl\setup.py`, `ctl\auth.py`, `ctl.py preflight` | Entra SP (`spn`) or `azcli` auth, a token per audience, `.env` kept apart from the committed inventory, and preflight refuses placeholder workspace ids | Workspace inventory still has placeholder ids |
| Read-only MCP over the tool | `agentDaya\mcp\dctMcp.py` | Agents can already query the registry and findings | — |
| DSPM skeleton | `dspm\` (`posture\` = thin adapter, never a copy), `dspm\docs\adr\0001-stack.md` (Proposed) | Layout, stack, SQLite store default | Nothing in `posture\` yet |
| Vendor SAT (Azure) | github.com/databricks-industry-solutions/security-analysis-tool, v0.8.0 | Reference for check coverage: 65+ checks in 5 categories (Network Security, Identity & Access, Data Protection, Governance, Informational), severity High/Medium/Low, defined in `configs/security_best_practices.csv`. Some checks are AWS-only or AWS+GCP-only | We only reference it. We don't fork it (objective § Not this) |
| Vendor SBP doc | *Security Best Practices for Azure Databricks* v2.3 (68 configurations) | The second provenance (SBP-nn) | TODO (Manish): repo location of the document |

**How the vendor SAT runs on Azure today** (from the SAT docs, fetched 2026-09-27). This sets
the bar dbSAT has to meet or beat:

- **Identity:** an Entra ID app registration added as a Databricks SP, holding **Account Admin**, **Workspace Admin** on every
  monitored workspace, **metastore admin**, and **Reader** on the subscription. Setup takes 5 values: account id, tenant id,
  subscription id, client id, client secret.
- **Install:** `install.sh` (interactive) or Terraform. Needs Unity Catalog (v0.5.0+), the Databricks CLI, and local Python < 3.12.
- **Jobs:** "SAT Initializer Notebook" runs once. "SAT Driver Notebook" runs on a schedule, by default Mon/Wed/Fri, taking about 10 min per
  workspace. "SAT Secrets Scanner Notebook" (TruffleHog) is optional.
- **Results:** Delta tables in a `security_analysis` schema, or a UC catalog/schema you choose.
- **Dashboards:** "[SAT] Security Analysis Tool – Assessment Results", Executive, and Secret Scanner/Permissions Analysis. Alerts use DBSQL Alerts.
- **Config:** checks are turned on and off by notebook ("7. update_sat_check_configuration"). Manual facts such as `sso_enabled` go in by notebook too.
  **Implication:** some SAT "checks" are self-declared values, not observed ones. dbSAT must report those as `procedural`/`unknown`, never compliant.
- **PAT vs OAuth:** the objective calls SAT "PAT-based". The current Azure docs describe an SP with a client secret. See Q6.

## 3. Users

| User | Cadence | Job to be done | What they need from dbSAT |
|---|---|---|---|
| SecOps engineer (3 + manager) | Weekly | Find and chase deviations | The deviation list by severity, the observed value and first-seen date, plus a check → control link |
| CloudOps (platform owner) | On finding | Fix platform config | The exact setting, the workspace, the desired vs observed value. No write from dbSAT |
| Auditor / insurer | Quarterly / ad hoc | Evidence of control operation | Per-check evidence with timestamp, method, standard version and SHA-256 |
| Data Engineering (later) | On finding | Fix workload-level config | Out of scope for v1. Ownership was disputed at the 25 Aug meeting |

## 4. Outcomes and how we measure them

| # | Outcome (objective § Success) | Measure — how it's checked |
|---|---|---|
| O1 | One non-prod workspace scanned end to end with zero manual steps after setup | A scheduled run completes with no human action. 100% of registry checks applicable to Azure return exactly one status from the five buckets. Every finding carries `check_id`, `severity`, `observed`, `desired`, `evidence_ref` (automated test on the run artifact) |
| O2 | The dashboard answers "what is wrong, how bad, since when" without a query | A reviewer who has never seen it answers 3 scripted questions (worst open finding, count of high/critical, first-seen date of a named finding) from the dashboard alone. Recorded by Daya at review |
| O3 | A second engineer reproduces setup from docs alone | An engineer other than Manish follows the docs to a successful scan of a non-prod workspace. Every question they ask gets logged and fixed in the docs. Pass = zero questions that needed Manish to answer |
| O4 (guard) | No false greens | Zero `compliant` results for checks whose collection failed or which rely on self-declared values (test) |

The product shows five buckets on purpose (blueprint invariant) and never a single compliance percentage.

## 5. Scope

**In**
- Azure Databricks **account** and **workspace** security configuration for enrolled workspaces.
- One registry holding two provenances: policy controls (`SEC-nn`) and vendor best practices (`SBP-nn`, with
  the SAT check id where one exists). One check record may cite both.
- Read-only scan: runs locally and on a schedule. The runtime is decided in ADR-0002 (Daya).
- Persisted results with history (first-seen, last-seen, status changes).
- Severity dashboard, five buckets, filterable by workspace, severity, provenance and domain.
- Architecture doc plus Azure dependency and connection model (identities, roles, env var names, network reach).
- A coverage map: vendor SAT checks → dbSAT checks (covered / not applicable on Azure / gap).

**Out**
- Any write, remediation or promotion above `observe`. That's layer 5 and stays gated as the blueprint says.
- AWS and GCP. Other data stores. A fork of SAT notebooks or a copy of its CSV (see Q8).
- Secret scanning of notebooks (the SAT TruffleHog job) and permissions-graph analysis. Those belong to layers 3/2 and are separate objectives.
- Alerting and ticketing on findings (candidate objective 3 / Sentinel). Only the data the dashboard needs.
- A second scanner beside the control tool.

## 6. Constraints inherited (blueprint + objective)

- **Observe-only.** No code path in dbSAT issues a non-GET/non-SELECT call. The control tool's `HttpBackend` has no write method; keep it that way.
- **`unknown` is never `compliant`.** A collection failure, a missing grant or a missing env var gives `unknown`. Self-declared inputs give `procedural`.
- **Five buckets, no single percentage.**
- **Every finding carries** its evidence, method, standard version (registry version + provenance doc version) and SHA-256.
- **Databricks-first, Azure-only.**
- **Python 3.14, stdlib `unittest`, no PowerShell** (CLM). Venvs in `%USERPROFILE%\.venvs\`, never OneDrive.
- **Credentials:** env var names only, in the repo and in this PRD. Provisioning is `needs_human`.
- **Posture layer is a thin adapter over the control tool.** `dspm\posture\` never copies it.
- **Least privilege, stated honestly.** Databricks has no read-only admin role, so the reader SP is workspace/account admin and read-only only because our code is. The docs must say so (control tool README § "An honest caveat").

**Conflicts with the blueprint → ADR requests to Daya (not decided here)**
- **C1 Store/runtime:** the objective proposes Delta results, a Databricks job and an AI/BI dashboard. Blueprint and ADR-0001 say SQLite and a local
  UI reading SQLite. → **ADR-0002**.
- **C2 Connector:** the blueprint says "Databricks managed MCP only". The control tool reads workspace-conf, account and ARM REST APIs directly,
  and the managed MCP doesn't expose admin settings (TODO (Daya to confirm)). → ADR-0002 or a separate ADR.
- **C3 Sequencing:** the dashboard is blueprint phase 6 and posture is phase 3. dbSAT pulls posture and a dashboard ahead of phases 1–2.
  → Pradyuman/Daya decide whether dbSAT is an out-of-order epic (ADR) or waits.

## 7. Stories

Each story covers one behaviour and names its blueprint layer. Criteria use synthetic values.
"Run artifact" means the per-run output folder (control tool `runs\<timestamp>\`, or whatever
store ADR-0002 settles on).

### S1 — Registry carries two provenances · Layer 4
*As a SecOps engineer I want each check to cite the policy control and/or vendor practice it comes from, so that one scan answers both "are we compliant with our policy" and "are we following vendor best practice".*
```gherkin
Given a registry record with refs [SEC-06, SBP-12] and a record with refs [SBP-40] only
When `ctl.py validate` runs
Then both load, and `ctl.py controls --provenance SBP` lists both records
And `--provenance SEC` lists only the first

Given a record whose refs list is empty, or cites an id not matching ^SEC-\d{2}$ or ^SBP-\d{2}$
When validate runs
Then validate exits non-zero naming the record id

Given two records citing the same SBP id
When validate runs
Then validate exits non-zero (one vendor practice maps to one dbSAT check)

Given the existing 31 SEC records unchanged
When validate and the fixture pipeline run
Then results equal the current baseline (16 compliant, 8 deviations, 4 prerequisite gaps, 1 procedural, 2 unknown)
```

### S2 — Vendor Azure best practices land in the registry at observe · Layer 4
*As a SecOps engineer I want the 68 SBP v2.3 configurations represented as registry records, so that vendor coverage stops depending on the vendor's tool.*
```gherkin
Given SBP v2.3 has 68 configurations
When the import is complete
Then every SBP-01..SBP-68 is cited by exactly one record, either as its own record or merged into an existing SEC record
And every new record has enforcement: observe, a severity from {critical, high, medium, low}, and ratified: false
And a record for a configuration with no Azure API has detection modality manual and assesses to procedural, never compliant

Given a merged record (SEC + SBP)
Then its desired value equals the SEC value, and any disagreement with SBP is listed in the import note for Manish
```
TODO (Manish): source document path. The import is agent-drafted and human-ratified, same as the SEC records.

### S3 — Connection model and preflight name every Azure dependency · Layer 4 (docs + preflight)
*As a new engineer I want one document and one command that say exactly which identity, roles, env vars and network reach a live scan needs, so that I can stand it up without asking.*
```gherkin
Given the connection model doc
Then it lists: identity type, every role per plane (Databricks account, workspace, UC/system schemas + SQL warehouse, Azure Reader scope),
  every env var name the scan reads, the token audiences, and outbound endpoints
And it contains no secret values

Given an environment missing DATABRICKS_ACCOUNT_ID
When `ctl.py preflight` runs
Then it exits non-zero, names the variable, and lists the checks that would report unknown

Given all variables set but the SP lacks workspace admin on the target
When `ctl.py setup --check` runs
Then it reports the missing grant per plane and makes no write call
```

### S4 — Live read-only scan of one non-prod workspace · Layer 4
*As a SecOps engineer I want a live scan of one enrolled non-prod workspace and its account, so that findings reflect the real estate, not fixtures.*
```gherkin
Given a clean preflight against workspace W (non-prod) and its account
When `ctl.py run --live` runs
Then every Azure-applicable registry check yields exactly one status in {compliant, deviation, prerequisite-gap, procedural, unknown}
And every deviation carries check_id, refs, severity, workspace, observed, desired, method, registry_version, evidence_sha256
And the HTTP log contains only GET requests and SQL SELECT statements

Given one collector's endpoint returns 403
Then that collector's checks report unknown with the HTTP status in evidence, and the run completes

Given two consecutive live runs with no config change in between
Then the set of (check_id, workspace, status, observed) is identical
```

### S5 — Account-level checks scanned alongside workspace checks · Layer 4
*As a SecOps engineer I want account-plane settings assessed in the same run, so that account-level gaps aren't invisible.*
```gherkin
Given a registry record scoped per-account
When a live run covers workspaces W1 and W2 in the same account
Then the record is assessed once, attributed to the account id, and not duplicated per workspace
```

### S6 — Results persist with history · Layer 4 → evidence for layer 5 "prove"
*As an auditor I want every run's findings kept with timestamps, so that I can see when a deviation started and whether it was fixed.*
```gherkin
Given check C on workspace W was compliant in run R1 (2026-10-01) and deviation in R2 (2026-10-03) and R3 (2026-10-05)
When results are queried after R3
Then C/W shows status deviation, first_seen 2026-10-03, last_seen 2026-10-05

Given C/W returns to compliant in R4
Then the deviation is closed with closed_at = R4 timestamp, and R2–R3 rows are retained unchanged

Given a stored evidence record
When its payload is re-hashed
Then the SHA-256 equals the stored evidence_sha256
```
Store (Delta vs SQLite) per ADR-0002. Retention: see Q4.

### S7 — Scan runs on a schedule without manual steps · Layer 4
*As a SecOps engineer I want the scan to run unattended, so that the posture is continuous.*
```gherkin
Given setup complete and a schedule configured
When the scheduled time passes
Then a run starts, completes, and persists results with no human action

Given the credential expires or a run fails
Then the run is recorded as failed with the reason, prior results are not overwritten, and no check flips to compliant
```
Cadence: see Q3. Runtime (Databricks job vs local) per ADR-0002.

### S8 — Severity dashboard · UI (phase 6 — see C3)
*As a SecOps engineer I want a dashboard showing what's wrong, how bad and since when, so that I don't need to write a query.*
```gherkin
Given persisted results with 2 critical, 5 high, 3 medium open deviations, 4 unknown and 1 procedural
When the dashboard loads
Then it shows the five buckets as counts, with no single percentage anywhere
And deviations are listed ordered by severity then first_seen ascending, each showing check_id, refs, workspace, observed, desired, first_seen
And unknown is shown as its own bucket and never merged with compliant

When filtered to provenance SBP and workspace W
Then only matching rows and counts show

Given the latest run failed
Then the dashboard shows the last successful run time and a stale banner
```
The dashboard has no write actions.

### S9 — Coverage map against the vendor SAT · Layer 4
*As the product owner I want to see which vendor SAT checks dbSAT covers, so that retiring the vendor tool is an evidenced decision.*
```gherkin
Given the vendor SAT check list for a pinned version (v0.8.0)
When the coverage report is generated
Then every SAT check id appears exactly once as covered (with dbSAT check id), not-applicable-on-Azure (with reason) or gap
And the report states the SAT version it was built against
```
Check ids are referenced only; SAT content isn't copied (see Q8).

### S10 — Architecture document a second engineer can build from · Docs (Daya authors, Nolan accepts against O3)
*As a new engineer I want the architecture and Azure dependency list in one place, so that I can reproduce dbSAT.*
```gherkin
Given the architecture doc and S3 connection model
When an engineer other than Manish follows them against a non-prod workspace
Then they reach a successful live scan (S4 criteria), and every question they had to ask is logged in the doc's changelog as fixed
```

## 8. Release slices

| Slice | Stories | Proves | Provable against |
|---|---|---|---|
| **1** | S3, S4, S5 (SEC records only, local run, run-folder artifacts) | The control tool works live and read-only. O1 minus the schedule | One non-prod workspace + its account (Manish provides the SP) |
| 2 | S1, S2, S9 | One registry, two provenances; vendor coverage evidenced | Fixtures, then re-run slice 1 live |
| 3 | S6, S7 | Continuous posture with history. O1 fully | Same workspace, ≥3 scheduled runs |
| 4 | S8, S10 | O2 and O3 | Dashboard review + second-engineer reproduction |

Slice 1 goes first because nothing has run live yet, and the control tool README says to expect
the API paths to need correcting. Adding 68 records before the 31 existing ones are proven live
would multiply the correction work.

## 9. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Live API paths wrong (all written from docs) | High | Slice 1 slips | Slice 1 is only this. `unknown` on failure keeps output honest |
| SP needs account + workspace admin (no read-only role) | Certain | Audit/insurer challenge on least privilege | State it in S3 docs. Code has no write path (test-enforced). Separate write credential never provisioned |
| Registry not ratified | High | Findings judged against a draft | Every finding carries `registry_version` and `ratified` flag. Dashboard shows "draft standard" |
| Runtime decision (C1) drags | Medium | Slices 3–4 blocked | Slices 1–2 don't depend on it |
| Vendor licence on reusing SAT check text | Unknown | Legal exposure | Reference ids only until Q8 is answered |
| Ownership of findings (CloudOps vs DE) unresolved | Medium | Findings unactioned | v1 shows findings. Routing is out of scope |

## 10. Decisions (this PRD)

- dbSAT is an epic in layer 4 plus phase-6 UI over the control tool. It is not a new product and not a fork of SAT.
- Slice 1 = the existing SEC records, live, one non-prod workspace. SBP import is slice 2.
- Secret scanning, permissions graph and alerting are out of v1.
- Self-declared inputs (SAT-style manual flags) assess as `procedural`, never `compliant`.
- 2026-09-27: S1's fixture baseline moves from 17/9/4/1/0 to 16/8/4/1/2 (compliant/deviation/prerequisite-gap/procedural/unknown).
  Two false greens were removed: SEC-15 (mounts, slice-1 Item 1) and SEC-08 account scope (identity sourcing, Item 3a) used to
  read `compliant` without being able to see the setting, and now read `unknown`, per the blueprint invariant `unknown` ≠ compliant.
  Source: `dspm\docs\specs\dbSatSlice1.md` § baseline. Verified by Manish's run, 135/135 tests. Scope unchanged.

## 11. Open questions

| # | Question | Owner |
|---|---|---|
| Q1 | ADR-0002: runtime and store. Delta + Databricks job + AI/BI dashboard (objective) vs SQLite + local UI (blueprint/ADR-0001)? | Daya → Manish |
| Q2 | Connector: does "managed MCP only" hold when admin settings need direct REST (C2)? | Daya |
| Q3 | Scan cadence: nightly (control tool design), or Mon/Wed/Fri (SAT default)? | Manish |
| Q4 | Evidence retention period for auditors/insurers (e.g. 365 days, to match SEC-03)? | Manish |
| Q5 | Severity scale: keep the registry's 4 levels (critical/high/medium/low), and how do SBP/SAT High/Medium/Low map onto them? | Manish |
| Q6 | "PAT-based": which SAT deployment was this based on? The current Azure docs use an Entra SP + client secret. Does it change the "why"? | Manish |
| Q7 | Where does the SBP v2.3 document live, and is v2.3 the version to pin? | Manish |
| Q8 | Legal: may we reference or copy SAT check ids/descriptions (Databricks licence) into our registry? | Manish (needs_human, legal) |
| Q9 | Which non-prod workspace is enrolled first, and is the SP the one from the Claude Code MCP setup (needs account-admin + UC grants added)? | Manish |
| Q10 | The registry lives in the control tool folder, outside `myAgents\`. Who is allowed to edit it for S1/S2 (Dino's write scope)? | Pradyuman → Manish |
| Q11 | Does C3 (posture + dashboard ahead of phases 1–2) need an ADR, or a roadmap re-sequence? | Pradyuman + Daya |
| ~~O7~~ | ~~(raised by Daya in `dbSatSlice1.md`) S1 baseline text becomes 16/8/4/1/2~~ — **Resolved 2026-09-27:** S1 updated, see § 10 | Nolan |

---

```
FROM AgentNolan → TO AgentPradyuman
Artifact:   program\prd\dbSat.md (stories S1–S10 in § 7; not filed on GitHub — unattended)
Needed:     Plan epic:dbSat into the roadmap as 4 slices; raise C1/C2 (ADR-0002) and C3 (sequencing) to Daya; file S1–S10 as issues when GitHub is available
Done when:  roadmap.md has dbSat slices with gates matching § 8, status.md lists Q1, Q8, Q9, Q10 as blockers, ADR-0002 request is with Daya
Open:       Q1 runtime/store (Daya); Q8 licence (Manish, legal); Q9 workspace + SP (Manish); Q10 registry write scope; Q11 phase order
```
