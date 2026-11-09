# dbSAT — Azure connection model

- **Owner:** AgentDaya · **Decider:** Manish Jha · **Date:** 2026-09-27
- **Status:** Authored, not verified. No grant listed here has been tested with a real token. `ctl.py setup --check` and `ctl.py preflight` are the tests of record.
- **Scope:** everything a dbSAT scan of **one non-prod Azure Databricks workspace and its account** depends on in Azure, Entra ID and Databricks.
- **Related:** runtime per ADR-0002; flow per `architecture.md`. Variable names come from `controlTool\ctl\config.py` and `ctl\auth.py`, so they match the code.
- **Contains no secret values.** Variable *names* only (SEC-09 applies to us).

## 1. Planes at a glance

| Plane | Endpoint | Token audience (Entra) | Needed for | Tier |
|---|---|---|---|---|
| Entra token service | `https://login.microsoftonline.com/<tenant>/oauth2/v2.0/token` | — | every token | **core** |
| Databricks account | `https://accounts.azuredatabricks.net/api/2.0/accounts/<account-id>/…` | `00000000-0000-0000-0000-000000000000` (Azure Databricks first-party app) | SEC-08, 23, 29; account-scoped SBP | **core** |
| Databricks workspace | `https://adb-<workspace-id>.<n>.azuredatabricks.net/api/2.0/…` | same | SEC-02, 05, 06, 10, 13, 18, 19, 20, 21, 24, 27, 28 | **core** |
| Unity Catalog / system tables | same workspace host, `POST /api/2.0/sql/statements` (SELECT only) on a SQL warehouse | same | 15 detect specs: SEC-01, 08, 14, 15, 16, 17, 19, 21, 22, 25, 28, 30 | **core** |
| Azure Resource Manager | `https://management.azure.com` | `https://management.azure.com` | SEC-01, 03, 14, 23, 31 | **core** |
| Sentinel / Log Analytics | `https://management.azure.com` | same as ARM | SEC-01, 03, 04 and every `event` detect | extended |
| Microsoft Graph | `https://graph.microsoft.com/v1.0` | `https://graph.microsoft.com` | SEC-07, 08 (part), 12 | extended |
| Azure DevOps | `https://dev.azure.com/<org>` | `00000000-0000-0000-0000-000000000000` | SEC-09, 11, 12, 24 (IaC list) | extended |

**Core** is what "every security configuration of an enrolled workspace and its account" needs,
and it's the slice-1 ask. **Extended** planes are SEC controls that live outside Databricks.
Leaving them out is safe: their checks report `unknown`, never `compliant`. They can be granted
later without any design change.

## 2. Identity

**One Entra ID app registration + service principal per environment.** The working name is
**`dbsat-scanner-nonprod`**.

| Item | Value / rule |
|---|---|
| Type | Entra application (single tenant) + its enterprise-app service principal |
| Credential | **Client secret**, max 180-day expiry, rotation owner named at provisioning. Federated credential / managed identity is the prod upgrade (ADR-0002 option D) |
| Where the secret lives | Job: **Key Vault-backed Databricks secret scope** `dbsat`, key `azure-client-secret`, in a non-prod Key Vault with RBAC + firewall (SEC-10 applies to us). Local: see § 6. **Never** in the repo, the registry, the inventory, the bundle YAML or a OneDrive-synced file |
| Human alternative (local only) | `CTL_AUTH_MODE=azcli` uses the engineer's own `az login` and PIM roles. Good for a first look, but results reflect *that person's* visibility, and the run records `source=azcli` |
| Write identity | **None.** `DATABRICKS_WRITE_TOKEN` is never provisioned for dbSAT. Job-mode preflight fails if it's present |
| Existing SP? | Q9: the SP from the Claude Code MCP setup can be reused if Manish prefers. It still needs every grant in § 3, and then it has two purposes. A dedicated SP is recommended so its audit trail means one thing |

## 3. Roles per plane: exact grants

**The honest caveat, stated first:** Databricks has no read-only admin role. Reading
workspace-conf, token management, IP access lists and cluster policies needs **workspace admin**.
Reading account settings and NCCs needs **account admin**. Seeing *every* grant and storage
credential needs **metastore admin**. So the scanner is an admin that only issues reads. That's
enforced by our code (`HttpBackend` has no write method, the request-log guard, no write token),
**not by platform RBAC**. On Azure/ARM, Graph and ADO, read-only roles do exist, and we use only
those.

| # | Plane | Grant | Where it's granted | Who can grant | Without it |
|---|---|---|---|---|---|
| G1 | Databricks account | Add SP to the account (by Entra **application id**) → role **Account admin** | Account console → User management → Service principals | An existing account admin | Account-scope checks (SEC-08, 23, 29) → `unknown`. The visibility guard can't confirm account-level truth |
| G2 | Databricks workspace | Assign the SP to the workspace → member of **`admins`** (workspace admin). Entitlement **Databricks SQL access** | Account console → Workspaces → Permissions; or workspace Settings → Identity and access | Account admin or workspace admin | Every workspace-conf, token, IP ACL, cluster-policy, secret-ACL, serving check → `unknown` (403) |
| G3 | SQL warehouse | **CAN USE** on one warehouse (smallest serverless or classic Pro/2X-Small, auto-stop 10 min). Its HTTP path → `DATABRICKS_SQL_HTTP_PATH` | Workspace → SQL Warehouses → Permissions | Workspace admin | All 15 SQL detect specs → `unknown` |
| G4 | Unity Catalog system schemas | System schemas **enabled** on the metastore: `access`, `compute`, `query`, `serving`, `billing`. Then `USE CATALOG` on `system`, `USE SCHEMA` + `SELECT` on `system.access`, `system.compute`, `system.query`, `system.serving` | Enable: account admin (system schemas API). Grant: metastore admin | Account admin + metastore admin | SQL checks → `unknown` (error, not empty) |
| G5 | Unity Catalog visibility | **Metastore admin** (put the SP in the group that is metastore admin, or make it the admin in non-prod) | Account console → Catalog → metastore → Metastore admin | Account admin | `information_schema` returns **only what the SP can see**, silently. The visibility guard forces SEC-14/15/16 to `unknown (insufficient-visibility)`. Without G5 those checks can never be green, **by design** |
| G6 | Azure subscription | **Reader** on the subscription holding the workspace, its managed resource group, its VNet, storage accounts and Key Vaults. Set `AZURE_SUBSCRIPTION_ID` | Azure portal → Subscription → Access control (IAM) | Owner / User Access Administrator (PIM) | SEC-01 diag settings, SEC-14 shared key, SEC-23 private endpoints, SEC-31 policy/budgets → `unknown` |
| G7 *(ext)* | Log Analytics / Sentinel | **Log Analytics Reader** + **Microsoft Sentinel Reader** on the central LAW. Set `AZURE_LOG_ANALYTICS_RESOURCE_ID` | LAW → IAM | Owner / UAA | SEC-03, 04, and every `event` detect → `unknown` |
| G8 *(ext)* | Microsoft Graph | Application permissions `Directory.Read.All`, `Application.Read.All`, `AccessReview.Read.All`, `Policy.Read.All` + **admin consent** | App registration → API permissions | Privileged Role Admin / Global Admin | SEC-07, 12 and part of SEC-08 → `unknown` |
| G9 *(ext)* | Azure DevOps | SP added to the org (Basic or Stakeholder), **Read** on Code and Build, Advanced Security read. Set `ADO_ORG` | ADO org settings → Users; project permissions | ADO org admin | SEC-09, 11, 12 (part), 24 IaC comparison → `unknown` |

**Slice-1 minimum = G1–G6.** Ask for G7–G9 separately, since each needs a different approver.

**Job-runtime grants** (scheduled mode only, ADR-0002). These are writes, but only to dbSAT's own
objects:

| # | Grant | Why |
|---|---|---|
| J1 | Catalog `<catalog>` (non-prod) with schema `dbsat` **owned by the SP**. `USE CATALOG` on the catalog. Grant `SELECT` on `dbsat` to group `secops-readers` | The Delta tables and views live here. No write anywhere else |
| J2 | Volume `<catalog>.dbsat.runs` (managed), owned by the SP | Evidence JSON, byte-for-byte |
| J3 | Secret scope `dbsat` (Key Vault-backed). The SP gets **READ** on the scope. The Key Vault has the SP as **Key Vault Secrets User** on that vault only | The job reads its own secret |
| J4 | Job cluster: `run_as` = SP, a cluster policy the SP **CAN USE** that satisfies SEC-21. If standard access mode, the wheel's volume path goes on the UC artifact allowlist (SEC-25) | Dogfooding: dbSAT's compute has to pass dbSAT |
| J5 | Dashboard: published by the SP or a SecOps owner, shared with `secops-readers` (and CloudOps), with **viewer credentials** | Readers see only what their SELECT grants allow |

Deploying the bundle (creating the job, schema, volume and dashboard) is **Manish, `needs_human`**.

## 4. Environment variables Manish provides for the non-prod workspace

Names are exactly as the code reads them today, unless marked *proposed* (read by no code yet;
Dino adds them in D1/D3).

| Variable | Required | Secret? | Value source | Read by |
|---|---|---|---|---|
| `CTL_AUTH_MODE` | yes | no | `spn` (job and SP local runs) or `azcli` (engineer-local) | `ctl\config.py` → `auth.detect` |
| `AZURE_TENANT_ID` | yes (spn) | no | Entra tenant id | `ctl\auth.py` |
| `AZURE_CLIENT_ID` | yes (spn) | no | App registration's application (client) id | `ctl\auth.py` |
| `AZURE_CLIENT_SECRET` | yes (spn) | **yes** | Job: secret scope `dbsat/azure-client-secret`. Local: env file outside OneDrive (§ 6) | `ctl\auth.py` |
| `DATABRICKS_ACCOUNT_ID` | yes | no | Account console → account id (GUID) | `ctl\config.py` |
| `DATABRICKS_SQL_HTTP_PATH` | yes | no | `/sql/1.0/warehouses/<warehouse-id>` of the G3 warehouse | `ctl\collectors\base.py` |
| `AZURE_SUBSCRIPTION_ID` | yes | no | Subscription holding the workspace | `ctl\config.py` |
| `AZURE_LOG_ANALYTICS_RESOURCE_ID` | extended | no | Full ARM id of the central LAW | `ctl\config.py` |
| `ADO_ORG` | extended | no | ADO organisation name | `ctl\config.py` |
| `CTL_ENV_FILE` | *proposed*, local | no | Path to an env file **outside OneDrive**, e.g. `%USERPROFILE%\.dbsat\nonprod.env` | `ctl\cli.py` (today it hard-codes `controlTool\.env`) |
| `CTL_RUNS_ROOT` | *proposed*, job | no | `/Volumes/<catalog>/dbsat/runs` | `ctl\orchestrator.Run.root` |

**Not an env var, but required:** the enrolled workspace's `databricks_url` and `workspace_id` in
`registry\workspaceInventory.yaml` (committed, not secret). For slice 1, that means **one real
non-prod row** and the other three rows set to `governed: false` (or removed). `preflight` refuses
a live run while any governed row is an `adb-0000…` placeholder. That's a reviewed inventory
change, so Manish edits it.

**Must NOT be set** for dbSAT: `DATABRICKS_WRITE_TOKEN`, `ANTHROPIC_API_KEY`, and the static
escape hatches (`DATABRICKS_TOKEN`, `DATABRICKS_ACCOUNT_TOKEN`, `AZURE_ARM_TOKEN`,
`AZURE_GRAPH_TOKEN`, `ADO_TOKEN`). Static tokens expire hourly and bypass the SP's audit identity.
`DATABRICKS_MCP_URL` / `DATABRICKS_MCP_TOKEN` (`dspm\knowledge\connectors.yaml`) aren't used by dbSAT.

**Non-secret dbSAT settings** go in `dspm\knowledge\dbsat.yaml` (*proposed*, P9), not env:
results catalog, schema `dbsat`, volume `runs`, secret scope name, cadence, retention days.

## 5. Network and egress

| From | To (FQDN, 443/TCP) | Notes |
|---|---|---|
| Runner (workstation or job cluster) | `login.microsoftonline.com` | token minting |
| | `accounts.azuredatabricks.net` | account API. If the **account** has an IP access list, the runner's egress IP must be on it |
| | `adb-<id>.<n>.azuredatabricks.net` | workspace API + Statement Execution. If the workspace has **IP access lists (SEC-24)**, the runner's egress IP must be allowed, or every workspace check returns 403 → `unknown`. If **front-end Private Link** is on with public access disabled, the workstation needs the private DNS zone + VPN/ExpressRoute path |
| | `management.azure.com` | ARM |
| | *(ext)* `graph.microsoft.com`, `dev.azure.com` | only if G8/G9 |
| Job cluster only | package source | Prefer the wheel + deps from the UC volume (no PyPI egress). DBR ships `requests` and `PyYAML`. Confirm on first deploy |

- **Job cluster egress** leaves through the workspace's VNet-injected subnets. If that path goes through **Azure Firewall**, the FQDNs above need application rules in the non-prod firewall. Raise them through the existing `/add-firewall-rule` workflow (`azureFirewall\nonProdFirewall`). The job cluster to its own workspace control plane is normal Databricks traffic. Account API, ARM and login are the likely new rules.
- **Not needed:** `api.anthropic.com` (no model in the scheduled path), inbound connectivity of any kind, or any storage-account data-plane endpoint. dbSAT reads *configuration*, never table data. Statement Execution returns system-table metadata only.

## 6. Secrets handling

| Where | Rule |
|---|---|
| Repo, registry, inventory, bundle YAML, specs, this doc | Names only. A value found in any of them means rotate immediately |
| Job | `dspm.posture.job` calls `dbutils.secrets.get("dbsat", "azure-client-secret")` into the process environment at start. Databricks redacts the value in output. It's never logged, never written to the run artifact, and `SpnTokenSource` already avoids echoing it on failure |
| Local, SP mode | **Not** `controlTool\.env`, because that folder is **OneDrive-synced**, so a secret written there leaves the machine. Use `CTL_ENV_FILE=%USERPROFILE%\.dbsat\nonprod.env` (outside OneDrive, user-only ACL) once Dino adds the override. Until then, set the variables in the process environment for the session, or use `azcli` mode |
| Local, azcli mode | No secret on disk. Uses PIM. Record that the results reflect the engineer's visibility |
| Rotation | 180-day max. Expiry is tracked by whoever provisions the SP. SEC-12 will flag the password credential. That's expected, stays visible, and is resolved by option D in prod |
| Tokens | Minted per audience at run time, cached in memory, never written to disk |

## 7. What a scan can and cannot see with less privilege

The rule: **less privilege gives more `unknown`, never more `compliant`**. The visibility guard
(`architecture.md` § 6) exists because one plane, UC `information_schema`, degrades silently
instead of erroring.

| Grants held | Sees | Can't see → reports |
|---|---|---|
| G1–G6 (slice-1 minimum) | All workspace-conf toggles, tokens, IP ACLs, cluster policies, secret scopes/ACLs, serving endpoints, CSP state, account identity sourcing, NCCs, metastore sharing scope, every grant and storage credential, system tables, ARM config | Sentinel, Graph and ADO checks → `unknown` |
| G2 + G3 + G4 + G6, no account admin (G1) | Workspace-level and ARM checks | SEC-08/23/29 and account-scoped SBP → `unknown`. Visibility guard can't confirm account context → absence-based UC checks `unknown` |
| G1–G4 + G6, no metastore admin (G5) | Everything except full UC visibility | SEC-14 credentials, SEC-15 grants, SEC-16 tag coverage → **`unknown (insufficient-visibility)`**. Without the guard these would be **false greens**, because `information_schema` hides what you can't see |
| Workspace **user** instead of admin (no G2 admin) | Cluster list, own objects, some serving metadata | workspace-conf, token management, IP ACLs, cluster policies → 403 → `unknown` |
| No SQL warehouse (G3) | All REST checks | Every `sql` modality check → `unknown` ("DATABRICKS_SQL_HTTP_PATH is not set") |
| `azcli` as an engineer | Whatever that person's active PIM roles allow | Run marked `source=azcli`. Not valid as scheduled evidence |
| Reader on the managed RG only, not the subscription | Managed-RG resources | Customer VNet, private endpoints, storage, Key Vault outside it → `unknown` |

**Never visible to dbSAT, at any privilege:**
- data content;
- OneNote/Teams secret sweeps (SEC-09 manual part → `procedural`);
- model/dataset provenance (SEC-26 → `procedural`);
- permitted reads leaving the platform (SEC-30 is signal only);
- SBP practices with no API → `procedural`.

## 8. Setup order (for the second engineer, O3)

1. Manish provisions G1–G6 plus the SP secret. **needs_human.**
2. Edit `workspaceInventory.yaml`: one real non-prod row, the other rows `governed: false`. Manish reviews and commits.
3. Set the § 4 variables (local: env file outside OneDrive, or the session env).
4. `python ctl.py setup --check`: a token per audience, and the missing grant named per plane.
5. `python ctl.py preflight`: must print "configuration complete". Every missing item is named along with the checks it turns `unknown`.
6. `python ctl.py run --live`: **Manish runs it.** Read-only, artifacts in `runs\`.
7. Scheduled mode (D3): Manish creates the secret scope, catalog/schema, and J1–J5, then runs `databricks bundle deploy`, and unpauses the job.

Every question a second engineer has to ask goes into the changelog below, along with the fix (S10).

## Changelog

| Date | Change | Why |
|---|---|---|
| 2026-09-27 | First version | ADR-0002, PRD S3 |
