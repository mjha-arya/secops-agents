# dbSAT slice 1, turn B: hand-back (AgentDino → AgentDaya)

- **Date:** 2026-09-27
- **Contract:** `dspm\docs\specs\dbSatSlice1.md` § (e) items 10–14, plus decision O16
- **State:** code and tests are written but **not run**. This was an unattended turn, so the shell was refused and the fixture has not
  been regenerated.
- **Reviewed:** `feature-dev:code-reviewer` and `silent-failure-hunter` reviewed the files as they stand (no `git diff`
  was available). The one critical finding is fixed. Everything else is listed below.

## Changed (control tool)

| Item | Where | What |
|---|---|---|
| 10 | `ctl\collectors\base.py`: `_statement_rows`, `_typed_rows`, `_typed_value` | Refuses a result that is `truncated`, or has no schema, no `total_row_count`, a format other than `JSON_ARRAY`, or `external_links`. Follows `next_chunk_internal_link` by GET on the same host, and only when the link is a path. Stops at the `MAX_PAGES` cap. The row count must match. Every value is typed from its `type_name` |
| 11 | `base.SQL_STATEMENTS`, `_sql` | Grants: a `UNION ALL` over the 6 privilege views, adding a `securable` column. Tags: start from `information_schema.tables` with a `LEFT JOIN` to `column_tags`. The LIMIT rule applies, with `PRESENCE_PROBES` exempt |
| 12 | `unity_catalog._rows`, `_library_installs`, `_gateway_usage`; `workspace._token_lifetimes`, `_ip_list_matches_iac`; `azure._law_rbac`; `entra._admin_overlap`; `plan._sec24_payload`; `build_demo.py` | Keys are now read with required access. SEC-06 lifetime is expiry minus creation; an expiry of -1 or a missing expiry counts as over the limit. SEC-24 follows O16. The plan never proposes an empty allow-list. The generator raises on an unmatched target. `_iac_declared` is removed from the fixture |
| 13 | `config.host_for` + `SCOPE_HOSTED_PLANES`; `base._get` credential; `_sql` host; `config.build` | 13a: each plane uses its own plane host. 13b: metastore REST reads use the UC token. 13c: account and metastore SQL runs on the metastore host. 13d: a `None` URL no longer crashes the build |
| 13e / 14 | `tests\test_routes.py`: `TargetCoverage`, the NCC tests; `HiddenGrants` additions | Scopes are derived through `scopes_for`. `FakeSession` records headers |

**"Verify first" results (item 12):**
- An ARM role assignment carries no Databricks-admin field.
- No Graph response carries `account_admins` or `metastore_admins`.
- Neither target has a route today, so a live read sends a literal path and gets a 404.
- I checked these against the documented shapes from memory; context7 was not queried.

## Expected red run against the committed `ctl\`

**These should FAIL:**
- `StatementResult` (all)
- `AbsenceBasedSql`: the statement-shape tests and `test_result_at_its_limit_is_unknown`
- `HostAndTokenSelection` (all)
- `LiveShapedAssertions` (all except `test_world_open_without_iac_is_a_deviation` and
  `test_iac_comparison_still_applies_when_declared`)
- `FixtureBaseline.test_new_baseline`
- `test_empty_second_page_fails_the_whole_read`

**These may PASS on the old code (regression or strengthening guards):**
- `TargetCoverage.*`
- `test_mixed_nccs_are_not_compliant`
- `test_probe_returning_a_list_is_malformed`
- `test_scim_me_500_raises`

## Open items for Daya (not decided by me)

| # | Item |
|---|---|
| **SEC-01 (held: "stop and report")** | Item 12 says to raise when `enabled_schemas` can't be derived. It can't be: the probe returns only `ok`. Raising would move the baseline to **15/7/4/1/4**, so I left `_system_schemas` unchanged. Live, that gives a false **red**, not a green. Recommendation: route SEC-01 to `GET /api/2.1/unity-catalog/metastores/{id}/systemschemas`, which gives the state of every schema |
| **O18** | `artifact-allowlists` (SEC-25) is `api-read` on the UC plane, so it goes to `_sql`, is refused as non-SELECT, and ends up `unknown`. Item 14's coverage test can't hold for it; it is pinned as the only known gap in `TargetCoverage.UC_KNOWN_GAPS`. Options: add it to `NOT_COLLECTABLE` (baseline goes to 15/7/4/1/4), or build a REST read of `GET /api/2.1/unity-catalog/artifact-allowlists/{type}` |
| **Item 14 wording** | "Mixed NCCs → `deviation`" can't happen. SEC-23 is `blocked_by`, so assess reports `prerequisite-gap`. The test asserts that and names the bad NCC |
| **13a vs SEC-20** | `workspace/settings/compliance-security-profile` is a workspace API on the account plane. Under 13a as written it now goes to the accounts host, gets a 404 and is `unknown`. That fails safe, but it is a regression. Proposal: per-workspace reads on the account plane use the workspace host and the workspace token |
| **LIMIT side effect** | SEC-17 lineage (`LIMIT 100`) is a presence check, so a busy metastore now reads `unknown`. It's a candidate for `PRESENCE_PROBES` |
| **Tightened beyond spec** | Item 10 says to check `total_row_count` "if present". I made it **required**, and I also refuse a non-`JSON_ARRAY` or `external_links` result (silent-failure-hunter, critical). Without a count, zero rows looks the same as rows that were never delivered. Please confirm |
| **O19** | When `_sec24_payload` returns `{}`, `_payload_for` falls back to the registry payload, and SEC-24 has none. The result is an empty-payload change. It's unreachable today because SEC-24 is `observe`. It should be an exclusion |
| **O20** | The metastore host is the first governed workspace, so workspaces on a second metastore are never read. Filter by `metastore_id` in slice 2 |
| Pre-existing (silent-failure-hunter; not touched) | <ul><li>SEC-21: the policy `definition` is a JSON string live</li><li>SEC-14 misses `spark.hadoop.fs.azure.account.key`</li><li>SEC-21 passes a null `data_security_mode`</li><li>SEC-10 treats SP ACLs (no "@") as groups</li><li>SEC-13 treats a missing `dns_name` as no crossing</li><li>ARM/Graph `nextLink` is not followed</li><li>SEC-06 token list `{}` is the same question as O9</li></ul> |

## Fix turn: Manish's verification run (2026-09-27)

- **What Manish ran:**
  - Red run against the committed `ctl\`: 42 failures and 3 errors. The tests are real.
  - `build_demo.py` regenerated the fixture: 7 planes, 103 keys.
  - `validate` is consistent.
  - `run` gives **16/7/4/1/3**.
- **Full suite:** 1 failure, `FixtureBaseline.test_sec24_open_list_is_the_only_deviation_and_the_rest_unknown`. It reported `'compliant' != 'unknown'` for scope `account`.
- **Cause: a test defect, not a code defect.** The evidence:
  - `registry\controlRegistry.yaml` SEC-24 has two detect specs: `api-read ip-access-lists per-workspace` and `event SEC-04-alert-05-ip-acl-change per-account`.
  - `SentinelCollector._one` turns the event spec into rule health.
  - In the fixture, `sentinel.account.SEC-04-alert-05-ip-acl-change` is exists, enabled, with 0 failures.
  - So assess correctly returns `compliant` ("…: assertion satisfied").
  - O16 only governs the IaC comparison per workspace. My test applied it to every scope.
- **Fix, test only:**
  - The loop now covers the per-workspace scopes other than `analytics-prd`. It asserts that at least one such scope exists, so it can't pass vacuously.
  - A new test, `test_sec24_account_scope_is_the_observed_sentinel_rule`, asserts that the account scope is `compliant` and that the reason is not "no IaC-declared". It proves the source from the registry: SEC-24's only per-account detect spec is `event` / `SEC-04-alert-05-ip-acl-change`.
  - Second run (Manish): 182 tests, 1 failure. The test asserted the rule name in the reason, but assess only names a rule when a check is unsatisfied; a compliant reason is always "all checks satisfied". Fixed as above, test only.
- **No code change.** `ctl\`, the registry and the fixture are untouched. The baseline stays at 16/7/4/1/3. SEC-24 is still counted at its worst scope (`deviation`).
- **Still not run by me:** the shell was refused.

## Proposed commit (control-tool repo)

```
dbSAT slice 1 turn B: close latent live false greens (items 10-14)

Spec: myAgents/dspm/docs/specs/dbSatSlice1.md section (e); decision O16.

- Item 10: statement results read every chunk (GET, same host), refuse
  truncated/no-schema/no-count/non-inline results and count mismatches,
  and type values from the manifest (tests.test_routes.StatementResult)
- Item 11: SEC-15 grants UNION ALL six privilege views; SEC-16 starts from
  information_schema.tables so an untagged table is a row; a result at its
  LIMIT is unknown, presence probe exempt (AbsenceBasedSql)
- Item 12: required access for keys the API does not return
  (SEC-03/07/25/28); SEC-06 lifetime from creation/expiry, never-expiring
  is over; SEC-24 per O16 (internet-open -> deviation, else unknown); plan
  never proposes an empty allow-list; build_demo refuses an unmatched
  target (tests.test_false_green.LiveShapedAssertions)
- Item 13: non-Databricks planes use their plane host; metastore REST
  reads use the UC token; account/metastore SQL on the metastore host;
  build survives a missing URL (HostAndTokenSelection, TargetCoverage)
- Item 14: exact NCC status, empty page 2, HTTP non-admin integration,
  probe failures, scopes derived via scopes_for
- fixtures/build_demo.py regenerated
- FixtureBaseline: O16 unknowns asserted on per-workspace IP-list scopes
  only; SEC-24 account scope (Sentinel alert 5) asserted as observed
  compliant, its source proved from the registry's per-account event spec

Held for Daya: SEC-01 _system_schemas (would move the baseline), O18
artifact-allowlists. Fixture baseline 16/8/4/1/2 -> 16/7/4/1/3 (O16).
No registry, inventory, exception or .env change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

Before committing, Manish adds the red and green counts from the run. The `myAgents` commit carries `dspm\readme.md` and
this file.
