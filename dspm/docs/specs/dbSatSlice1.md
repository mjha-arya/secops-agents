# Spec — dbSAT slice 1: live read-only scan

- **Owner:** AgentDaya · **Builder:** AgentDino · **Decider:** Manish Jha · **Date:** 2026-09-27
- **Status:** Authored, not verified. Nothing in this spec has run live. Every "correct path" below
  comes from vendor documentation, and dbSat-1.9 (run #1) is what verifies it.
- **Roadmap:** `program\roadmap.md` § Epic dbSat, WS1, items dbSat-1.1 → 1.9 (D1 milestone)
- **Stories:** PRD `program\prd\dbSat.md` S3, S4, S5
- **Decisions of record:** ADR-0002 (Proposed); `dspm\docs\architecture.md` § 2, 6, 7;
  `dspm\docs\azureConnectionModel.md`; `program\decisions.md` 2026-09-27 (Q10 write scope, Q9)
- **Write scope (Q10, Manish, 2026-09-27):** Dino may change `controlTool\ctl\`, `tests\`,
  `fixtures\`, `ctl.py` and `README.md`, with tests. `registry\` and `.env` stay human-owned.
- **Registry-neutral:** this slice makes **no change** to `controlRegistry.yaml`,
  `exceptionRegister.yaml` or `workspaceInventory.yaml`. Any fix that seems to need one is written
  up as an open item for a Daya proposal instead.
- **Two repos:** the control tool is its own git repo, so its commits are proposed separately from
  `myAgents` (the adapter, item 9).

## Q11: does C3 need an ADR? (answer)

No. dbSAT *is* blueprint layer 4, and the blueprint already puts "layer 4 wired to the control
tool's findings" in phase 3. Running it as parallel D-milestones changes no blueprint default and
closes no phase gate. D3 still doesn't close M3, because there's no layer 3. dbSAT does change four
defaults (store, connector, dashboard surface, Python floor), and ADR-0002 already covers all four.
The AI/BI dashboard is dbSAT's own surface. It is not the phase-6 DSPM UI, which stays in phase 6
under ADR-0002 decision 3. So C3 is a sequencing decision. Pradyuman records it in `decisions.md`
and removes "provisional" from the roadmap placement. The one condition: no D3/D4 build (store,
job, dashboard) starts before Manish accepts ADR-0001 and ADR-0002. If that ever slips, *that*
needs an ADR. Slice 1 is unaffected: apart from the read-only adapter (item 9), it is corrections
and tests inside the control tool.

## Rules that apply to every item

1. **Test first.** Each item names the failing test Dino writes before the fix. Against today's
   code that test must fail, and fail for the stated reason. Dino records the red run in the
   hand-back.
2. **`unknown` on failure, never `compliant`.** A new failure path either raises `NotCollected` /
   `BackendError` or makes the assertion raise. Both already become `unknown` in
   `Collector._one` → `assess`. No new `except` swallows anything to a default value.
3. **Fixtures are generated.** `fixtures\demo\observations.yaml` is the output of
   `fixtures\build_demo.py`. Edit the generator, then regenerate it. Never hand-edit the YAML. Both
   files are committed together.
4. **Fixtures may only hold what a live read can produce.** If a target has no live read method,
   its fixture entry is deleted, not kept as a convenience.
5. **Python 3.12-compatible** (ADR-0002 F10). No 3.13+ syntax or stdlib.
6. **No network in tests.** `HttpBackend` tests use a fake session object. Nothing mints a real
   token.

## Baseline effect (read before starting)

Today's fixture baseline is 17 compliant · 9 deviation · 4 prerequisite-gap · 1 procedural ·
0 unknown. Items 1 and 3a make two recorded "greens" honest, so the baseline moves:

| After | compliant | deviation | prerequisite-gap | procedural | unknown | Why |
|---|---|---|---|---|---|---|
| Item 1 (mounts) | 17 | 8 | 4 | 1 | 1 | SEC-15's per-workspace scopes go `unknown`; `unknown` is the worst scope, so the control rolls up there |
| Item 3a (identity sourcing) | 16 | 8 | 4 | 1 | 2 | SEC-08's account scope goes `unknown` |

These are the numbers the design predicts. Dino confirms them with the real run and records them.
If a row comes out different, **stop and report it**. Don't adjust fixtures to hit the number.
PRD S1's "equals the current baseline" criterion then refers to the new baseline. Nolan updates
the PRD, and I flag it in the hand-off.

---

## (a) False-green defects: first, before anything else

### Item 1: `dbutils.fs.mounts` placeholder (SEC-15). Blocks the live run.

**Defect.** `ctl\collectors\base.py` `SQL_STATEMENTS["dbutils.fs.mounts"]` is
`SELECT '/databricks-datasets' AS mountPoint`, a constant. On a live run `HttpBackend._sql`
executes it and gets one fake row. `ctl\collectors\unity_catalog.py` `_mounts` then filters out
`/databricks-datasets` and returns `compliant: True`. So SEC-15 per-workspace goes green without
anything being read.

**Required behaviour**
- Delete the `dbutils.fs.mounts` key from `SQL_STATEMENTS`.
- Add a module-level `NOT_COLLECTABLE: dict[str, str]` in `ctl\collectors\base.py` (target → reason),
  with entry `"dbutils.fs.mounts": "no read-only REST/SQL method; needs a notebook or job context
  (dbutils) - not built"`.
- `HttpBackend.read` checks `NOT_COLLECTABLE` **first**, for every plane, and raises
  `NotCollected(f"{target}: {reason}")`. The finding becomes `unknown` with that reason.
- `build_demo.py`: delete the `dbutils.fs.mounts` branch (line ~124) and every per-workspace
  entry, then regenerate.
- `_mounts` itself is left alone. It becomes reachable again only when a real method exists.

**Failing tests first** (`tests\test_false_green.py`, class `MountsPlaceholder`):
1. `test_live_mounts_read_is_not_collected`: build an `HttpBackend` with a stub config and a fake
   session. `read("unity-catalog", "analytics-dev", "dbutils.fs.mounts")` raises `NotCollected`,
   **and the fake session records zero requests**.
2. `test_sec15_workspace_scope_unknown_on_fixture`: run discover + assess on the demo fixture.
   Every SEC-15 finding whose scope is a workspace name has `status == "unknown"`, and no SEC-15
   finding is `compliant`.
3. `test_no_constant_select`: every value in `SQL_STATEMENTS` contains `" FROM system."`. This is
   the guard against another placeholder slipping in.
4. `test_fixture_holds_no_uncollectable_target`: no target in the loaded fixture is a key of
   `NOT_COLLECTABLE`.

**Done when:** tests 1–4 pass, the full suite passes, and the new baseline row matches the table
above.

### Item 2: hidden UC grants via privilege-filtered `information_schema` (SEC-14, 15, 16)

**Defect.** `system.information_schema.*` returns only the rows the caller is allowed to see. An
SP that isn't metastore admin gets *fewer rows*, not an error. Three assertions in
`ctl\collectors\unity_catalog.py` treat "no bad row" as proof:
- `_storage_credentials` (SEC-14): with no rows it returns `compliant: True`.
- `_grant_hygiene` (SEC-15): with no rows it returns `compliant: True`.
- `_classification` (SEC-16): with no rows it returns `compliant: False`. But if the SP can see
  only the tagged tables, it goes green.

**Required behaviour: a visibility guard in the collector. `assess` stays pure and unchanged.**
- In `ctl\collectors\unity_catalog.py`, add:
  - `VISIBILITY_TARGET = "uc/visibility"`
  - `ABSENCE_BASED_TARGETS = frozenset({"system.information_schema.storage_credentials",
    "system.information_schema.table_privileges", "system.information_schema.column_tags"})`

  This list is code for now, because moving it into the registry would be a registry change. See
  open item O2.
- `UnityCatalogCollector.collect(reg)` overrides the base:
  1. Read `backend.read("unity-catalog", "metastore", VISIBILITY_TARGET)` **once per run**,
     before any other target.
  2. The probe result counts as *proven* only if it is a dict with `metastore_admin is True`
     (identity check, not truthiness) and a non-empty `metastore_id`.
  3. For every spec whose target is in `ABSENCE_BASED_TARGETS`, if visibility isn't proven
     (probe raised, returned something malformed, or `metastore_admin` isn't `True`), emit an
     `Observation` **without reading the target**, with
     `error = "insufficient-visibility: <probe detail>"`. `assess` already turns that into
     `unknown` with reason `collection failed: insufficient-visibility: …`.
  4. Every other target behaves as today.
  5. The probe result goes into discovery as one `Observation` (control `"_visibility"`, plane
     `unity-catalog`, scope `metastore`, target `VISIBILITY_TARGET`). That way it lands in
     `state.json` for the audit trail. `assess` ignores controls that aren't in the registry, and
     a test proves it.
- `HttpBackend.read`, for `target == VISIBILITY_TARGET`, runs `_visibility()`. It makes two GETs
  on the governed workspace host that `Config.host_for("unity-catalog", "metastore")` resolves to
  (see item 5):
  1. `GET /api/2.1/unity-catalog/metastore_summary` → `metastore_id`, `owner`
     ([docs](https://docs.databricks.com/api/azure/workspace/metastores/summary))
  2. `GET /api/2.0/preview/scim/v2/Me` → the caller's `userName` / `applicationId` and `groups[].display`
  3. Return `{"metastore_id", "owner", "principal", "groups", "metastore_admin":
     owner == principal-applicationId or owner in group display names}`.

  Any non-2xx response raises `BackendError`, so the guard stays closed.
- Fixture: `build_demo.py` adds `unity-catalog.metastore."uc/visibility"` with
  `metastore_admin: true`, a synthetic `metastore_id` and `owner`. With that, the baseline is
  unchanged by this item.

**Failing tests first** (`tests\test_false_green.py`, class `HiddenGrants`):
1. `test_non_admin_empty_privileges_is_unknown`: fixture copy with `metastore_admin: false` and
   `table_privileges.rows: []`. SEC-15 metastore finding is `unknown`, reason contains
   `insufficient-visibility`. Also assert the backend was **not** asked for `table_privileges`.
2. `test_non_admin_storage_credentials_unknown`: same for SEC-14 (metastore scope).
3. `test_non_admin_partial_tags_unknown`: `column_tags` rows all tagged, non-admin → SEC-16 `unknown`.
4. `test_probe_failure_closes_guard`: the probe target is missing from the fixture (so it raises
   `NotCollected`) → all three are `unknown`.
5. `test_truthy_non_bool_does_not_open_guard`: `metastore_admin: "yes"` → `unknown`.
6. `test_admin_path_unchanged`: `metastore_admin: true` → SEC-15 is still a `deviation` (the
   ANY FILE row), the same as today.
7. `test_visibility_http_probe`: a fake session returns a summary with `owner` equal to the SP's
   application id → `metastore_admin is True`. Owner equal to another group → `False`. Only GETs
   are issued.

Tests 1–5 must fail against today's code: SEC-15/14 come back `compliant` and SEC-16 comes back
`deviation`/`compliant`.

**Done when:** tests 1–7 pass, the suite passes, and preflight shows the visibility line (item 7).

---

## (b) The four wrong API paths

These are all in `ctl\collectors\base.ROUTES` and the routing around it. Today each one resolves
to `unknown` or to a false **red**, never to a false green. Item 3a is the exception to "just fix
the path", because no read API has been found for it.

Two shared mechanisms come first (item 5 below). Items 3a–3d depend on them.

### Item 3a: `account/settings/identity-sourcing` (SEC-08)
- **Today:** `ROUTES` → `api/2.0/accounts/settings`. That has no account id and names no documented
  endpoint.
- **Correct:** **no documented read API was found** for the Automatic Identity Management state
  (checked 2026-09-27: [AIM docs](https://learn.microsoft.com/en-us/azure/databricks/admin/users-groups/automatic-identity-management/)
  describe the account console → Security → User provisioning only; the
  [account API index](https://docs.databricks.com/api/azure/account/introduction) lists no
  identity-sourcing setting). Inventing a path would be guessing.
- **Required:**
  - Remove the `ROUTES` entry.
  - Add the target to `NOT_COLLECTABLE` with reason `"no documented read API for AIM state
    (checked 2026-09-27); verify in account console"`.
  - SEC-08's account scope becomes `unknown`. That's honest.
- **Fixture:** delete `account/settings/identity-sourcing` from `build_demo.py` (line ~99), in line
  with rule 4.
- **Test:** `tests\test_routes.py::IdentitySourcing::test_not_collected_without_request`, the same
  shape as Item 1 test 1. Plus the baseline row.
- **Follow-up (open O1):** on run #1, Manish checks whether the account settings-v2 metadata
  listing exposes an AIM setting. If it does, a dbSat-1.10 item adds the route.

### Item 3b: `account/network-connectivity-configurations` (SEC-23)
- **Today:** there's no `ROUTES` entry, so the literal target is sent to the accounts host as a
  path. That's a 404, which becomes `unknown`.
- **Correct:** `GET /api/2.0/accounts/{account_id}/network-connectivity-configs`, paginated by
  `next_page_token` ([docs](https://docs.databricks.com/api/azure/account/networkconnectivity/listnetworkconnectivityconfigurations)).
  Response: `{"items": [{"name", "network_connectivity_config_id", "region", "egress_config":
  {"default_rules": {…}, "target_rules": {"azure_private_endpoint_rules": [ … ]}}}],
  "next_page_token"}`.
- **Required:**
  - Add the route with the `{account_id}` template (item 5).
  - Follow every page. A page failure fails the whole read, never returns a partial list, because
    a missing page could hide a bad NCC.
  - Rewrite `ctl\collectors\account.py` `_ncc_posture` for the real shape:
    - Configs come from `raw["items"]`. A missing `items` key raises, so the result is `unknown`.
      An empty list stays `compliant: False` ("no NCC configured").
    - Private endpoints come from `egress_config.target_rules.azure_private_endpoint_rules`,
      counting only rules that are not `deactivated`.
    - **Egress restriction isn't in the NCC response.** Serverless egress restriction lives in
      account network policies, which is a different endpoint and would need a new detect spec,
      i.e. a registry change.
    - So when NCCs exist and all have private-endpoint rules, the assertion **raises**
      `IncompleteObservation("egress restriction not observable from NCC; needs network-policies
      read (open O3)")`, which gives `unknown`. It never returns `compliant: True` on half the
      evidence.
- **Fixture:** `build_demo.py` line ~102 returns `{"items": []}` in place of
  `{"network_connectivity_configs": []}`. SEC-23 stays `prerequisite-gap`, so the baseline doesn't
  change.
- **Tests** (`tests\test_routes.py::NetworkConnectivity`):
  - URL contains the account id.
  - Two-page fake response → both pages read.
  - Second page 500 → `BackendError`.
  - Old key `network_connectivity_configs` → `unknown`.
  - `items: []` → `compliant False`.
  - NCC with PE rules → `unknown` (egress unobservable), never `compliant`.

### Item 3c: `metastore/delta-sharing-scope` (SEC-29)
- **Today:** the path is `api/2.1/unity-catalog/metastores` (a list), sent to the **accounts** host.
  Scope `metastore` has no host, so `Config.host_for` falls through to `hosts["databricks-account"]`.
  Even with the right host, the list response has many keys, so `assess._value` compares the
  whole dict with `INTERNAL`. That's a false **red**.
- **Correct:** `GET /api/2.1/unity-catalog/metastore_summary` on the **workspace** host, which
  returns the current metastore, including `delta_sharing_scope` (`INTERNAL` |
  `INTERNAL_AND_EXTERNAL`) ([docs](https://docs.databricks.com/api/azure/workspace/metastores/summary)).
- **Required:**
  - Route to `api/2.1/unity-catalog/metastore_summary`.
  - Add a `"metastore"` host (item 5).
  - Add a projection (item 5), `"metastore/delta-sharing-scope": "delta_sharing_scope"`, so the
    backend returns `{"delta_sharing_scope": <value>}`. A missing or null field raises
    `BackendError` → `unknown`.
- **Fixture:** already `{delta_sharing_scope: INTERNAL}`. No change.
- **Tests** (`tests\test_routes.py::DeltaSharingScope`):
  - Request goes to the workspace host, not `accounts.azuredatabricks.net`.
  - A full summary payload projects to `INTERNAL` → `compliant`.
  - `INTERNAL_AND_EXTERNAL` → `deviation`.
  - Field absent → `unknown`.

### Item 3d: `workspace-conf/exfiltration-toggles` (SEC-18)
- **Today:** no `ROUTES` entry. The literal target goes out as a path, gets a 404 and becomes
  `unknown`.
- **Correct:** `GET /api/2.0/workspace-conf?keys=enableResultsDownloading,enableNotebookTableClipboard,enableExportNotebook,enableDbfsFileBrowser`
  ([docs](https://docs.databricks.com/api/azure/workspace/workspaceconf/getstatus)). The response
  is a flat `{key: "true" | "false" | null}`.
- **Required:**
  - Add the route, built from `workspace.EXFIL_TOGGLES` so the two can't drift.
  - Fix a **third false green** found while writing this spec: `_exfil_toggles` does
    `str(raw.get(t, "unset"))`, so a `null` (never set = platform default, and for results
    download and notebook export the default is *enabled*) becomes `"None"`, which isn't `"true"`,
    so the result is `compliant`.
  - New rule: a toggle is closed only when its value is the string `"false"`. If any toggle is
    `None`, missing, or anything other than `"true"`/`"false"`, the assertion **raises**
    `IncompleteObservation("unset toggles: [...] - platform default not asserted")` → `unknown`.
    The code doesn't guess defaults.
- **Fixture:** the values are already explicit. No change.
- **Tests** (`tests\test_routes.py::ExfilToggles`):
  - The URL's `keys=` equals `EXFIL_TOGGLES`, in order.
  - All `"false"` → `compliant`.
  - One `"true"` → `deviation`.
  - One `null` → `unknown` (**fails today**, when it comes back `compliant`).
  - Key missing → `unknown`.

### Item 5: shared routing mechanisms (build before 3b–3d)

All of these go in `ctl\collectors\base.py` and `ctl\config.py`. They are data plus one function
each, and don't need a new abstraction.

- **Account-id templating:** `HttpBackend._get` formats `{account_id}` in the route from
  `config.settings["DATABRICKS_ACCOUNT_ID"]`. If the value is missing, raise `BackendError` naming
  the variable.
- **Metastore host:** `config.build` sets `cfg.hosts["metastore"]` to the URL of the first governed
  workspace **sorted by name**, so it's deterministic. That replaces today's dict-order fallback in
  `_sql`, and the fallback is deleted. With no governed workspace, no key is set, so the request
  raises `BackendError`.
- **Projections:** `PROJECTIONS: dict[str, str]` (target → response field). `_get` returns
  `{field: body[field]}`. A missing or `None` field raises `BackendError`.
- **Pagination:** `PAGINATED: dict[str, str]` (target → list key). `_get` follows `next_page_token`
  (`page_token=` query) and concatenates, with a hard cap of 50 pages. Hitting the cap raises
  `BackendError`. Only NCC uses this in slice 1. See open O4 for the other list endpoints.
- **`IncompleteObservation(Exception)`** in `ctl\collectors\base.py`. An assertion raises it, and
  `_one` already maps it to `assertion-failed: …` → `unknown`. Add a test that confirms this
  mapping.

**Tests** (`tests\test_routes.py::SharedMechanisms`): templating, missing account id, metastore
host determinism (two workspaces in reverse order), projection hit/miss, pagination cap, and
`IncompleteObservation` → `unknown`.

---

## (c) Interfaces: posture adapter, `CTL_ENV_FILE`, preflight visibility

### Item 6: `CTL_ENV_FILE` override (dbSat-1.2 / connection model § 6)

`ctl\cli.py` `_load_dotenv()`:
- Path = `os.environ["CTL_ENV_FILE"]` if set, else `ROOT / ".env"` (today's behaviour).
- If `CTL_ENV_FILE` is set and the file doesn't exist, raise `SystemExit` naming the path. There is
  **no silent fallback** to `ROOT / ".env"`.
- Existing values still win (`setdefault`). Keep that.
- **OneDrive guard:** if the file that actually got loaded sets `AZURE_CLIENT_SECRET` and its
  resolved path sits under `%OneDrive%`, `%OneDriveCommercial%` or `%OneDriveConsumer%` (whichever
  are set), record it. `config.build` then appends to `cfg.missing`: `"AZURE_CLIENT_SECRET loaded
  from a OneDrive-synced file <path> - move it outside OneDrive and set CTL_ENV_FILE"`. So preflight
  and `--live` refuse. The value is never printed.
- `README.md`: document `CTL_ENV_FILE` in the live-setup section. Names only, no values.

**Tests** (`tests\test_auth_config.py::EnvFileHandling`, extend):
- override is loaded;
- override missing → `SystemExit`;
- env var beats file;
- secret under a fake `OneDrive` root (via `mock.patch.dict(os.environ)`) → `cfg.ready is False`
  and the message names the path but not the value;
- secret outside OneDrive → ready (given the other settings).

### Item 7: preflight (dbSat-1.3) and the visibility check

`ctl\config.py` `preflight_report` / `cmd_preflight`:
- **Missing env var → non-zero, named, with the checks that would go `unknown`.** Replace the
  hard-coded `affects` strings in `PLANE_SETTINGS` with a computed list:
  - for each missing setting's plane, take the sorted control ids that have at least one detect
    spec routed (via `collectors.route`) to a collector of that plane;
  - print `! DATABRICKS_ACCOUNT_ID  MISSING  → unknown: SEC-08, SEC-23, …`.

  Exit code stays 1 while `cfg.missing` is non-empty.
- **Visibility check:** when the unity-catalog token and host resolve, preflight calls
  `HttpBackend(config=cfg).read("unity-catalog", "metastore", "uc/visibility")` (two GETs, item 2)
  and prints one line:
  - `UC VISIBILITY  metastore admin: yes` (metastore id shown), or
  - `UC VISIBILITY  metastore admin: NO → unknown (insufficient-visibility): SEC-14, SEC-15, SEC-16`
    (computed from `ABSENCE_BASED_TARGETS`), or
  - `UC VISIBILITY  not checked: <reason>`.

  **This is a warning, not a blocker.** A non-admin run is allowed, and its output is honest by
  construction. Preflight never *decides* visibility for the run: the collector re-probes every
  run (item 2), because preflight state can go stale.
- Preflight makes no call other than token minting and those two GETs. The request-log guard
  (item 8) covers it.

**Tests** (`tests\test_preflight.py`):
- env without `DATABRICKS_ACCOUNT_ID` → exit 1, output names it and lists `SEC-08`, `SEC-23`,
  `SEC-29` (computed; the assertion reads the registry, it doesn't hard-code the ids);
- visibility yes/NO/not-checked lines via fake session;
- no non-GET issued.

### Item 8: `HttpBackend` tests + request-log guard + 403 → `unknown` (dbSat-1.4, 1.5, 1.6)

- **Guarded session.** `HttpBackend.__post_init__` wraps the session in `GuardedSession`
  (`ctl\collectors\base.py`). It exposes only `get(url, …)` and `post(url, json, …)`.
  - `post` is allowed only for `…/api/2.0/sql/statements`, with `json["statement"]` that, stripped
    and upper-cased, starts with `SELECT` **and contains no `;`**.
  - Anything else raises `BackendError("write refused: …")` **before** the request is sent.
  - Every request is appended to `request_log` as `{method, url_without_query_secrets, statement
    head (first 60 chars) | None, status}`. No headers and no tokens.
- **Artifact:** `orchestrator` writes `runs\<id>\requests.json` from `backend.request_log` when the
  backend has one. Fixture runs write nothing.
- **Guard over the whole live run (S4):** `tests\test_http_backend.py::RequestLogGuard` runs the
  full pipeline with `HttpBackend` over a fake session that answers every route with a
  representative 200 body. It then asserts every logged request is either a GET or the allowlisted
  SQL POST, and that the Entra token POST isn't on this session (`ctl\auth.py` owns that, and a
  test asserts its only POST host is `login.microsoftonline.com`).
- **403 (S4, 1.6):** fake session returns 403 for `token-management/tokens`. Assert:
  - SEC-06 on that workspace is `unknown`;
  - the evidence file `evidence\SEC-06.json` observation error contains `403`;
  - the run reaches `report` (all stages ok).

  Also: 401 → same; 404 → `not-collected`; a timeout or `requests` exception → `unknown`
  (`unexpected:`), with the run completing.
- **`setup --check` (1.4):** `ctl\setup.py` `run(check_only=True)` reports, per plane, "token
  acquired" or the named failure, plus the visibility line from item 7. It never calls anything
  but token minting and GETs. Test: fake token source failing for `databricks-account` → that plane
  is named; the request log has no non-GET.

### Item 9: the `dspm.posture` adapter (read-only, no store in slice 1)

**Module:** `dspm\posture\adapter.py` (+ `dspm\posture\__init__.py`). It imports `ctl` and never
copies a module (ADR-0002 F6). Slice 1 needs **no store**: `FindingStore`, SQLite and Delta are D3.
Its purpose here is to be the single definition of the dbSAT finding record, and to prove
dbSat-1.7 on real run artifacts.

**Finding `ctl` on the path:** `CTL_ROOT` env var (path to `controlTool\`), inserted into
`sys.path` by `adapter.load_ctl()`. If it's unset or the path is invalid, raise
`AdapterError("CTL_ROOT …")`. Packaging (`pyproject.toml`) is D3.

**Interface**

```python
class AdapterError(Exception): ...            # the run cannot be read faithfully - reject it whole

@dataclass(frozen=True)
class FindingRecord:
    run_id: str
    check_id: str                  # ctl control id, e.g. "SEC-06"
    refs: tuple[str, ...]          # slice 1: (check_id,)  - provenance arrives in slice 2
    severity: str                  # critical | high | medium | low
    scope_type: str                # workspace | account | metastore | estate
    scope_id: str                  # workspace_id / DATABRICKS_ACCOUNT_ID / metastore_id; never "account"
    workspace: str | None          # inventory name when scope_type == workspace
    status: str                    # exactly one of the five buckets
    observed: Any
    desired: Any                   # control.desired from the registry snapshot
    reason: str
    method: tuple[dict, ...]       # from the evidence record's "method"
    registry_version: str
    evidence_path: str             # relative to the run dir
    evidence_sha256: str
    collected_at: str | None       # ISO-8601 UTC, from the observation; None for procedural/estate

@dataclass(frozen=True)
class RunRecord:
    run_id: str
    estate: str                    # "live" if requests.json exists, else "fixture"
    registry_version: str
    account_id: str | None
    findings: tuple[FindingRecord, ...]

def read_run(run_dir: Path, registry_dir: Path, *, account_id: str | None = None) -> RunRecord: ...
def verify_evidence(run_dir: Path, record: FindingRecord) -> bool: ...
```

**Behaviour**
- Reads `findings.json`, `state.json` and `evidence\<check>.json` from `run_dir`, and the registry
  through `ctl.registry.load(registry_dir)`.
- **Scope mapping:**
  - workspace name → inventory `workspace_id`;
  - `account` → `account_id` (argument, else `DATABRICKS_ACCOUNT_ID`);
  - `metastore` → `metastore_id` from the `_visibility` observation in `state.json`;
  - `estate` (procedural / no observations) → `scope_type "estate"`, `scope_id` = account id.

  This extends `architecture.md` § 5 by one scope type. I'll edit the doc once Dino's build lands.
- **Reject the whole run (`AdapterError`), never publish part of it, when:**
  - any artifact file is missing or unparseable;
  - a status falls outside the five buckets;
  - a finding cites a control that isn't in the registry;
  - a scope can't be mapped (for example, account scope with no account id);
  - an evidence file is missing;
  - `verify_evidence` is false for any record.
- `verify_evidence` recomputes `sha256(json.dumps(record_without_sha256, indent=2, sort_keys=True,
  default=str))`, the same way `ctl.stages.report.evidence_pack` does, and compares it with the
  stored `sha256`.
- **An adapter error never turns into findings:** it doesn't return an empty record set and doesn't
  default any status. The caller (D3's job) records the run as failed.
- It writes nothing, anywhere.

**Tests** (`dspm\tests\test_postureAdapter.py`, fixture run produced in `setUpClass` by
`ctl.orchestrator.run_pipeline` into a temp dir):
- **dbSat-1.7:** every record with `status == "deviation"` has non-empty `check_id`, `refs`,
  `severity`, `scope_id`, `observed`, `desired`, `method`, `registry_version` and
  `evidence_sha256`, and `workspace` for workspace scope.
- **dbSat-1.8 (S5):** per-account checks produce exactly one record per (check, run) with
  `scope_type "account"` and `scope_id == account_id`, never one per workspace. Pair it with a
  control-tool test that `Collector.scopes_for` returns `["account"]` once for `per-account`
  specs when two workspaces are governed.
- Tampering: flip one byte in an evidence file → `AdapterError`.
- An unmapped account scope → `AdapterError`.
- A status of `"green"` injected into `findings.json` → `AdapterError`.
- Record count equals the finding count, and the bucket counts equal the run's roll-up (no loss,
  no percentage field anywhere in `FindingRecord`).

---

## (d) Definition of done and test commands, per item

Venv: `%USERPROFILE%\.venvs\agentDino` (never inside OneDrive). In Git Bash:
`PY="$USERPROFILE/.venvs/agentDino/Scripts/python.exe"`. CT = the control tool folder:
`cd "…/secopsCurrentProjects/databricks/controlTool"`.

| # | Item | Roadmap | Done when | Command |
|---|---|---|---|---|
| 1 | Mounts placeholder → `unknown` | (a) / 1.10 pre-empt | red run recorded; `MountsPlaceholder` green; baseline 17/8/4/1/1 | CT: `$PY -m unittest tests.test_false_green.MountsPlaceholder -v` |
| 2 | Visibility guard | (a) | red run recorded; `HiddenGrants` 1–7 green; baseline unchanged by this item | CT: `$PY -m unittest tests.test_false_green.HiddenGrants -v` |
| 5 | Shared routing mechanisms | (b) | `SharedMechanisms` green; `_sql` dict-order fallback deleted | CT: `$PY -m unittest tests.test_routes.SharedMechanisms -v` |
| 3a | Identity sourcing → `NOT_COLLECTABLE` | (b) | test green; fixture entry deleted; baseline 16/8/4/1/2 | CT: `$PY -m unittest tests.test_routes.IdentitySourcing -v` |
| 3b | NCC path, pagination, real shape | (b) | test green; SEC-23 still `prerequisite-gap` on fixture | CT: `$PY -m unittest tests.test_routes.NetworkConnectivity -v` |
| 3c | Metastore summary on workspace host + projection | (b) | test green | CT: `$PY -m unittest tests.test_routes.DeltaSharingScope -v` |
| 3d | Exfil toggles route + null → `unknown` | (b) | test green (null case red first) | CT: `$PY -m unittest tests.test_routes.ExfilToggles -v` |
| 6 | `CTL_ENV_FILE` + OneDrive secret guard | 1.2 support | extended `EnvFileHandling` green; README section | CT: `$PY -m unittest tests.test_auth_config.EnvFileHandling -v` |
| 7 | Preflight: computed unknown list + visibility line | 1.3 | `test_preflight` green | CT: `$PY -m unittest tests.test_preflight -v` |
| 8 | Guarded session, `requests.json`, 403/401/404/timeout, `setup --check` | 1.4, 1.5, 1.6 | `test_http_backend` green; `RequestLogGuard` covers a full pipeline | CT: `$PY -m unittest tests.test_http_backend -v` |
| 9 | Posture adapter | 1.7, 1.8 | `test_postureAdapter` green with `CTL_ROOT` set | myAgents: `CTL_ROOT="…/controlTool" $PY -m unittest discover -s dspm/tests -v` |
| — | Whole slice | 1.1 gate for 1.9 | **all** of: full CT suite green (87 existing + new); `validate` exits 0; fixture run prints the new baseline; `/code-review` + `silent-failure-hunter` clean in Daya's review; security-guidance warnings closed | CT: `$PY -m unittest discover -s tests -v` · `$PY ctl.py validate` · `$PY ctl.py run` |
| 1.9 | Live run #1 | **Manish** | preflight "configuration complete" (visibility line recorded); `run --live` completes; `requests.json` has GET + SELECT only; every failing collector opens one dbSat-1.10.n item | Manish only: `$PY ctl.py preflight` then `$PY ctl.py run --live`. Agents never run `--live` |

**Order:** 1 → 2 → 5 → 3a–3d → 6 → 7 → 8 → 9. Items 1 and 2 come first because they are false
greens. Item 5 comes before 3b–3d because they depend on it. Each item is one proposed commit in
the control-tool repo (item 9 is in `myAgents`). The commit message names the item and the
red→green test.

## Open items (not for Dino to decide)

| # | Item | Owner |
|---|---|---|
| O1 | Is there a read API for AIM state? Check settings-v2 metadata on run #1; if yes → dbSat-1.10 route | Manish (run #1) → Daya |
| O2 | Move `ABSENCE_BASED_TARGETS` and `NOT_COLLECTABLE` into the registry as a per-spec `visibility:` / `collectable:` field. That's a registry change → Daya proposal in slice 2 | Daya → Manish |
| O3 | SEC-23 egress restriction needs a network-policies detect spec (registry change) → proposal in slice 2. Until then SEC-23 account scope with NCCs present = `unknown` | Daya → Manish |
| O4 | Other list endpoints (`token-management/tokens`, `policies/clusters/list`, `serving-endpoints`, …) may paginate. A truncated list is a false-green risk. Audit them from run #1's `requests.json` | Daya review of 1.9 |
| O5 | `ANY FILE` is a Hive-metastore privilege and may never appear in UC `table_privileges`. That makes SEC-15's check partly structurally blind. Confirm on run #1 before trusting a green | Daya review of 1.9 |
| O6 | Is metastore owner = metastore admin as the probe assumes, including when admin is a group of groups (nested)? Verify on run #1; nested membership → `metastore_admin: false` → `unknown` (safe side) | Manish (run #1) |
| O7 | PRD S1 baseline text becomes 16/8/4/1/2 after this slice | Nolan |
| O9 | Empty NCC list may come back as `{}` (→ `unknown` today). Record the raw body on run #1; Daya decides in a 1.10 item | Manish (run #1) → Daya |
| O15 | Which schemas are "curated" for SEC-16? Until answered, item 11 measures all non-system tables | Manish / Nolan |
| O16 | SEC-24 live has no IaC-declared list. Option (c), recommended: world-open → deviation, otherwise `unknown`; baseline → 16/7/4/1/3; the SEC-24 verify demo stops confirming. Option (b): keep `_iac_declared` in the fixture as a documented rule-4 exception | **Manish** |
| O17 | Per-workspace audit SQL judges account-wide events. Filter by `workspace_id` (slice 2) | Daya |
| O18 | `artifact-allowlists` has no read method (it's refused as non-SELECT, so `unknown`) → item 16 | Dino (turn D) |
| O19 | A builder returning `{}` falls back to the empty registry payload → item 18 | Dino (turn D) |
| O20 | The metastore host is the first governed workspace, so a second metastore is never read. Filter by `metastore_id` (slice 2) | Daya |
| O21 | The roll-up ranks `unknown` above `deviation`, so SEC-24's proven analytics-prd deviation shows as `unknown` at control level. Should a proven deviation outrank `unknown` in the roll-up? This is an assess-semantics change → ADR | Daya → **Manish** |
| O22 | SEC-24 IaC path (when the ADO read exists): read `enableIpAccessLists` (lists aren't enforced unless `"true"`); `_sec24_payload` must not write `_iac_declared`, or verify confirms itself | Daya (slice 2) |
| O23 | SEC-01: the probe SQL can't yield `enabled_schemas` (a false red, and the fixture breaks rule 4). Proposal: a new registry target read from `GET /api/2.1/unity-catalog/metastores/{metastore_id}/systemschemas`. That's a registry change → a Daya proposal with O2 | Daya → **Manish** |
| O24 | `system.access.audit` / `query.history` (`LIMIT 500`, unfiltered) will read `unknown` on any busy metastore: SEC-08/19/25/30 lose their signal. Push action and row-threshold filters into the SQL. SEC-17 lineage needs prod-table awareness (after O15). Size it from run #1 | Daya (1.10) |

---

## (e) Addendum from the turn-A review (turn B, before 1.9)

Source: `dbSatSlice1Review.md`. These are pre-existing false greens that a live run would publish.
The fixture couldn't show them because the assertions were written against the fixture's shape.
Same rules as above: test first, registry-neutral, fixtures generated.
**Baseline must not move for items 10, 11, 13, 14.** Item 12 moves it only as O16 decides. If it
moves anywhere else, stop and report.

**Order:** 10 → 11 → 12 → 13 → 14, then turn C = 6 → 7 → 8 → 9.

### Item 10: Statement result completeness and typing (O8)
`ctl\collectors\base.py` `_sql` / `_rows_from_statement`:
- `manifest.truncated is True` → `BackendError("statement result truncated")`.
- `manifest.schema.columns` missing or empty → `BackendError`.
- Follow `result.next_chunk_internal_link` with **GET** on the same host (it's a path from
  `GET /api/2.0/sql/statements/{id}/result/chunks/{n}`, [docs](https://docs.databricks.com/api/azure/workspace/statementexecution/getstatementresultchunkn)).
  Concatenate `data_array` and stop when there's no link. The cap is `MAX_PAGES`, and hitting it or
  any chunk failure → `BackendError`. Never return a partial set.
- If `manifest.total_row_count` is present and ≠ the rows collected → `BackendError`.
- Type each value from the column's `type_name`:
  - `BOOLEAN` → bool (`"true"`/`"false"` only);
  - `INT`/`LONG`/`SHORT`/`BYTE` → int;
  - `FLOAT`/`DOUBLE`/`DECIMAL` → float;
  - `MAP`/`STRUCT`/`ARRAY` → `json.loads`;
  - `null` → `None`;
  - other types stay strings.
  A conversion failure → `BackendError`.
- **Tests** (`tests\test_routes.py::StatementResult`):
  - truncated → SEC-15 `unknown`;
  - two chunks with the `ALL PRIVILEGES` row in chunk 2 (admin proven) → SEC-15 `deviation`, and every chunk request is a GET;
  - chunk 500 → `unknown`;
  - row-count mismatch → `BackendError`;
  - `BOOLEAN "false"` → `False`;
  - a `MAP` string → dict;
  - no schema → `BackendError`.

### Item 11: Absence-based SQL must be able to see the bad row (O12)
`SQL_STATEMENTS` only. The target keys stay the same, so the registry is untouched; renaming joins O2.
- `system.information_schema.table_privileges`: `UNION ALL` of `catalog_privileges`,
  `schema_privileges`, `table_privileges`, `volume_privileges`, `external_location_privileges` and
  `metastore_privileges`, projected to `grantee, privilege_type, securable`.
  - Add a comment saying the key name is historical.
  - `ANY FILE` as a Hive privilege stays O5.
- `system.information_schema.column_tags`: start from `system.information_schema.tables`,
  excluding `table_catalog = 'system'` and `table_schema = 'information_schema'`, with a `LEFT JOIN`
  to `column_tags`. Output `table, count(ct.tag_name) > 0 AS has_classification_tag`, so an untagged
  table appears as a row. Curated-schema filtering waits for O15.
- **LIMIT rule:** in `_sql`, if the statement ends in `LIMIT n` and exactly `n` rows come back →
  `BackendError("result hit LIMIT n - may be incomplete")`. The one exemption is
  `PRESENCE_PROBES = frozenset({"SELECT 1 FROM system.access.audit LIMIT 1"})`, whose question is
  whether any row exists at all.
- **Tests:**
  - statement text contains each privilege view (a string test);
  - a table with no tags row appears (a statement-shape test over a fake result);
  - 500 rows with `LIMIT 500` → `unknown`;
  - the presence probe with 1 row → not an error.

### Item 12: Assertions must read only what the live API returns
- **Rule:**
  - An assertion never uses `.get(key, <value that passes>)` for a key the live response or SQL
    doesn't guarantee. It uses required access (`KeyError` → `assertion-failed` → `unknown`) or raises
    `IncompleteObservation`.
  - `_rows` raises on a dict with no `rows` key.
- `_library_installs` / `_gateway_usage`: use required access for `allowlisted` / `via_ai_gateway`.
  The SQL doesn't select them, so live results go `unknown` until the statement can produce them.
  The fixture keeps them (they're columns a future statement can return), so the baseline is unchanged.
- `_token_lifetimes` (SEC-06):
  - lifetime = `(expiry_time - creation_time)` in days, both epoch-ms from `token_infos`
    ([docs](https://docs.databricks.com/api/azure/workspace/tokenmanagement/list));
  - `expiry_time` of -1 or missing = never expires = over the limit;
  - `creation_time` missing → `IncompleteObservation`;
  - the fixture's `lifetime_days` is replaced by the real fields, keeping 45 / 120 / 60 days.
- `_system_schemas` (SEC-01): judge the rows the statement actually returns. If
  `enabled_schemas` can't be derived from that statement, raise `IncompleteObservation` instead of a
  false red. The fixture moves to the live shape; the baseline must hold. If it can't, stop and report.
- `azure.py` (`is_databricks_workspace_admin`) and `entra.py` (`account_admins` / `metastore_admins`):
  **verify first** against the documented response. Apply the rule if the key isn't a real field,
  and record what you found.
- `_ip_list_matches_iac` (SEC-24): **on hold until Manish answers O16.**
- `build_demo.py:187`: the fallback raises `SystemExit(f"no fixture rule for {target}")` instead of
  returning compliant. Test: `build()` completes, and no value carries the "defaulted to compliant" note.

### Item 13: Host and token selection
- **13a:** `Config.host_for` uses the scope host only for `databricks-workspace` and
  `unity-catalog`. Every other plane uses its plane host. Test: an azure read at scope `pdp-prd`
  goes to `management.azure.com`, and the ARM token never goes to an `azuredatabricks.net` host.
- **13b (O10):** a `metastore`-scope REST read uses the `unity-catalog` credential. Test: the SEC-29
  request carries the UC token.
- **13c (O11):** `_sql` for scope `account` or `metastore` uses `hosts["metastore"]`. Test: the SEC-08
  audit spec reaches the statement endpoint on the metastore host.
- **13d:** `config.build` doesn't crash on a missing `databricks_url` (`config.py:110`); the
  missing entry is still recorded.
- **13e:** every `api-read` target that a Databricks collector handles is in `ROUTES` or in
  `NOT_COLLECTABLE`. This catches the `workspace.py` import-time route drifting.

### Item 14: Test strengthening (from `pr-test-analyzer`)
- `test_empty_items_is_not_compliant` → assert `status == "prerequisite-gap"` exactly.
- Mixed NCCs (one active PE, one without) → `deviation`.
- Integration: `UnityCatalogCollector(HttpBackend(fake: owner = another group)).collect(reg)` →
  SEC-14/15/16 `unknown`, and there's no `sql/statements` POST for any `ABSENCE_BASED_TARGETS`
  statement.
- Probe failures:
  - SCIM `Me` 500 → `BackendError`;
  - the probe returns a list → `unknown` with `malformed`.
- Pagination: page 2 returns 200 `{}` → `BackendError`.
- The guard's not-read assertion extended to `storage_credentials` and `column_tags`.
- Every spec `UnityCatalogCollector.handles()`, whatever its modality, is in `SQL_STATEMENTS` or
  in `NOT_COLLECTABLE`.
- `test_routes` derives scopes through `collector.scopes_for(spec, reg.governed_workspaces())`
  instead of hand-picking them.

---

## (f) Addendum from the turn-B review (items 15–18)

Source: `dbSatSlice1Review.md` § Turn B. Same rules: test first, registry-neutral, fixtures
generated. **Baseline must hold at 16/7/4/1/3 for every item here.** If it moves, stop and report.

**Order:** turn C = **15 → 6 → 7 → 8 → 9** (15 blocks 1.9: live false greens). Items 16–18 fail
safe today (`unknown`, or unreachable), so they **don't block 1.9**. Turn D builds them after turn C,
or they fold into dbSat-1.10.

### Item 15: remaining live false greens (from turn-B `silent-failure-hunter`)
- **15a (SEC-25 audit, SEC-28): an empty read is not evidence.** `unity_catalog._library_installs`
  and `_gateway_usage`: zero rows → `IncompleteObservation("no rows - absence of installs/usage is
  not evidence")`. The statements don't select `allowlisted` / `via_ai_gateway` yet, so a live read
  can never be compliant.
  - Fixture: `system.access.audit` gains one row, `{"action_name": "installLibraries",
    "source": "pypi", "allowlisted": true, "principal": "svc-pdp-etl"}`. That keeps SEC-25
    compliant. SEC-08 and SEC-19 filter by action, so they're unaffected.
- **15b (SEC-14):** `_spark_conf_keys` matches `"fs.azure.account.key" in k`, so it also catches
  `spark.hadoop.fs.azure.account.key.*`.
- **15c (SEC-21/22):** `_cluster_policy_bypass` counts a null or missing `data_security_mode` as
  unsafe (the legacy default is no-isolation shared), reported as `"<cluster> (unset)"`.
- **15d (SEC-10):** `_no_individual_acls` also counts a principal that is a GUID (a service
  principal's application id) as individual. Live group names carry no `group:` prefix, so a bare
  name stays a group.
- **15e (SEC-13):** `_no_cross_env_scopes`: an `AZURE_KEYVAULT` scope with no
  `keyvault_metadata.dns_name` → `IncompleteObservation`.
- **15f (ARM / Graph paging, O4 in part):** `HttpBackend._get`, for planes `azure`, `sentinel` and
  `entra`:
  - If a response is a dict with a `value` list and a `nextLink` (ARM) or `@odata.nextLink`
    (Graph), follow it by GET until there is none, and return `{"value": <all items>}`.
  - The link must start with `config.host_for(plane, scope)`. Otherwise → `BackendError`, because a
    link to another host would carry the token there.
  - A page without a `value` list → `BackendError`. `MAX_PAGES` reached → `BackendError`.
- **15g test hardening (turn-B `pr-test-analyzer`):**
  - Pin `ABSENCE_BASED_TARGETS` to its three members.
  - The chunk-500 test asserts the reason names the failed request, not only `unknown`.
  - The `external_links` subcase uses `total=0`, so that branch decides the result.
  - Row-width mismatch → `BackendError`.
  - A chunk link that points to itself → `BackendError` after exactly `MAX_PAGES` chunk GETs.
  - A 200 chunk without `data_array` → `BackendError`.
  - A `//host/x` link is refused.
  - 13a asserts the `Authorization` header: the ARM/Graph token never reaches an
    `azuredatabricks.net` URL.
  - Fix the comment at `base.py:346`: the host prefix keeps requests on the host; the guard rejects
    malformed links.
- **15h nits:**
  - `plan.py:213`: restore the line break in the joined `if`.
  - README: the test count (it says 87) and "every Unity Catalog target has a SELECT statement"
    (false for `artifact-allowlists`, item 16).
- **Tests:** `tests\test_false_green.py::LiveShapedAssertions` (15a–e),
  `tests\test_routes.py::ArmGraphPaging` (15f: two pages, a foreign-host link, a page with no
  `value`, the cap), plus the 15g edits in place.

### Item 16: `artifact-allowlists` REST read (O18; SEC-25). After turn C
- `base.ARTIFACT_ALLOWLIST_TYPES = ("LIBRARY_JAR", "LIBRARY_MAVEN", "INIT_SCRIPT")`.
- `HttpBackend.read`: for target `artifact-allowlists`, call `_artifact_allowlists(scope)`, which
  issues one GET per type, `api/2.1/unity-catalog/artifact-allowlists/{type}`
  ([docs](https://docs.databricks.com/api/azure/workspace/artifactallowlists/get)). Each goes to the
  metastore host with the `unity-catalog` token. It returns `{"allowlists": {type: body}}`, and any
  failure fails the whole read.
- `_artifact_allowlists` assertion: `raw["allowlists"]` (required access). A type counts as present
  only when `body.get("artifact_matchers")` is a non-empty list. A missing key means empty, which
  means not present (a red, never a green).
- Fixture moves to the live shape. `TargetCoverage.UC_KNOWN_GAPS` becomes empty. Baseline holds.

### Item 17: `databricks-account` plane at a workspace scope (13a vs SEC-20). After turn C
- Add `databricks-account` to `config.SCOPE_HOSTED_PLANES`: a workspace-name scope resolves to that
  workspace's host, and `account` still resolves to the accounts host.
- Credential: at a workspace scope, `databricks-account` uses the `databricks-workspace` token.
- **Detection read only.** SEC-20 stays a one-way door and unplannable. Its live value shape
  (`compliance_security_profile_workspace.is_enabled`) against `desired: "enabled"` gives a false
  *red*, and it's `blocked_by` anyway. That is not in scope here.
- Test: the SEC-20 read at `pdp-prd` goes to the workspace host with the workspace token and never
  to the accounts host.

### Item 18: no fallback payload for a builder control (O19). After turn C
- `plan._payload_for`: when a `PAYLOAD_BUILDERS` control has no usable observation, or its builder
  returns `{}`, the finding becomes an `Exclusion(reason="no IaC evidence to re-apply (O16)")`.
  There's no `Change`, and no fallback to `control.implement.payload`.
- Test: SEC-24 with enforcement patched to `enforce` in a copied registry → plan has the exclusion
  and zero SEC-24 changes.

## Changelog

| Date | Change | Why |
|---|---|---|
| 2026-09-27 | First version | dbSat-1.1; Q10 decision; ADR-0002 |
| 2026-09-27 | Probe is two GETs, not three (items 2, 7). Added O9, O15–O17 and § (e) items 10–14 | Turn-A review (`dbSatSlice1Review.md`): spec named two endpoints; review found pre-existing live false greens |
| 2026-09-27 | Item 10: `total_row_count` is **required**, and a non-`JSON_ARRAY` or `external_links` result is refused. Item 14: mixed NCCs → `prerequisite-gap` (SEC-23 is `blocked_by`), not `deviation`. Item 12 SEC-01 is held; it moves to O23. Added § (f) items 15–18 and O18–O24 | Turn-B review: accepted Dino's stricter reading; the spec wording on items 10 and 14 was wrong |

---

```
FROM AgentDaya → TO AgentDino
Artifact:   dspm\docs\specs\dbSatSlice1.md  (roadmap dbSat-1.1 → 1.8; 1.9 is Manish's)
Needed:     Build items 1 → 2 → 5 → 3a–3d → 6 → 7 → 8 → 9, test first, one proposed commit per
            item (control-tool repo; item 9 in myAgents). No registry, inventory, exception or
            .env edits. No --live.
Done when:  Every item's red run is recorded and its tests are green; full control-tool suite green;
            `ctl.py validate` exits 0; fixture run shows 16/8/4/1/2; dspm adapter tests green;
            hand-back lists the commands run and their output, for my /code-review +
            silent-failure-hunter pass.
Open:       If any baseline row differs from the spec's table, stop and report it — don't tune the
            fixture. O1–O7 are not yours to decide; raise anything new as needs_human in the
            hand-back.
```
