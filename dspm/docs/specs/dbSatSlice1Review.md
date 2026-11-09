# Review — dbSAT slice 1, turn A (control tool items 1, 2, 5, 3a–3d)

- **Reviewer:** AgentDaya · **Builder:** AgentDino · **Decider:** Manish Jha · **Date:** 2026-09-27
- **Spec:** `dspm\docs\specs\dbSatSlice1.md` · **Build record:** `agentDino\runs\session20260927014145.md`
- **Evidence (Manish ran it, 2026-09-27):** red run against old `ctl\` = 35 failures + 10 errors;
  `fixtures\build_demo.py` regenerated (7 planes, 103 keys); full suite 135/135 OK; `ctl.py validate`
  consistent; `ctl.py run` = **16 / 8 / 4 / 1 / 2**, the number the spec predicted.
- **How reviewed:** every changed or new file read in full (no shell, no `git diff`, so this is a
  review of the files as they stand). `/code-review` (forked), `silent-failure-hunter` and
  `pr-test-analyzer` all ran. Their findings were checked against the code before they went in here.
  I've marked each finding either **confirmed** (I read the line) or **plausible** (in files outside
  the diff that I haven't read, or it depends on a live API shape).
- **Status:** fixture-verified. Nothing here has run live.

## Verdict

**Turn A is accepted as one combined commit.** Every spec item is built as specified, and the red and
green runs are real. I found no defect *introduced* by this change that yields a false green. Where
the diff opens a new failure path, it fails to `unknown`. No registry, `.env` or inventory file was touched.

The review did surface a **class of pre-existing live false greens**. The assertions were written
against the fixture's shape, not the API's. So the fixture is green, and a live run would be green
for the wrong reason. They don't block this commit, because turn A strictly improves things and
nothing runs live without Manish. **They do block trusting dbSat-1.9 (live run #1).** They're now
spec items 10–14 (spec § (e)), scheduled ahead of items 6–9.

## Per item

| # | Item | Verdict | Evidence / notes |
|---|---|---|---|
| 1 | Mounts placeholder → `unknown` | **Accept** | `base.py:58-63` `NOT_COLLECTABLE`; `base.py:150-152` checked first on every plane; the constant SELECT is gone; the `build_demo.py:277-279` skip is generic (better than per-target deletes). 4 spec tests + `test_uncollectable_targets_have_no_route_or_statement` |
| 2 | Visibility guard | **Accept** | `unity_catalog.py:38-65` probes once, first, and doesn't read the target when not proven; `_visibility_gap` `:87-102` uses `is not True` plus a non-empty `metastore_id`. The probe goes into discovery and assess ignores it (tested). Probe and guard use the same metastore host. Spec tests 1–7 plus 4 extra |
| 2 | "three GETs" | **Accept Dino's deviation** | My spec said three and named two. Two is correct. Spec fixed (changelog) |
| 5 | Shared mechanisms | **Accept** | Templating `base.py:176-181` raises before sending; the metastore host `config.py:127-130` is sorted by name; projection `:205-211` rejects null or missing; pagination `:213-229` fails the whole read on a bad page or at the cap; `IncompleteObservation` → `unknown` tested. The `_sql` fallback is deleted (`:269-273`, tested) |
| 3a | Identity sourcing | **Accept** | No route; `NOT_COLLECTABLE` reason; fixture entry gone; SEC-08 account scope `unknown` (tested in `FixtureBaseline`) |
| 3b | NCC | **Accept** | `account.py:26-47` matches the spec: missing `items` → raise; `[]` → not compliant; PE rules present → `IncompleteObservation`. Test `test_empty_items_is_not_compliant` is looser than spec (item 14) |
| 3c | Delta Sharing scope | **Accept** | Route and projection as specified; the metastore scope never falls back to the accounts host (`base.py:169-170`, tested). Token choice → item 13 (O10) |
| 3d | Exfil toggles | **Accept** | Only the string `"false"` closes a toggle; null, missing or odd values → `IncompleteObservation` (`workspace.py:109-121`). The route is built from `EXFIL_TOGGLES` at import (`workspace.py:24-25`): it fails safe (404 → `unknown`) if `workspace` isn't imported, but it's fragile. Item 13 adds a route-coverage test |
| — | Tests first | **Accept** | Red run 35F + 10E recorded by Manish. New names are reached through their module, so the red run fails per test, not on one import error |
| — | Style | **Accept** | Matches the existing code: dataclass/`Protocol` idiom, `#:` data comments, `# noqa` imports, `_one`-style `Observation` construction. `fake_http.FakeSession` raises on an unexpected call (good) |
| — | No registry / `.env` change | **Accept** | Only `ctl\`, `tests\`, `fixtures\`, `README.md` changed in CT |
| — | `dspm\readme.md` D1 row | **Fix (docs)** | Line 42 still says "tests written, **not run**… fixture not regenerated". Replace it with the evidence line above and "Daya review: accepted 2026-09-27". Dino, in turn B |
| — | security-guidance | **No warnings surfaced** this session. One security finding goes to item 13a: ARM or Graph bearer tokens can be sent to a Databricks workspace host (`config.py:86-87`, pre-existing) |

## Findings carried forward (all pre-existing unless marked; ranked)

| Sev | Where | Finding | Status | Goes to |
|---|---|---|---|---|
| Critical | `base.py:297-302` | `_rows_from_statement` reads only the first result chunk and ignores `manifest.truncated` and a missing schema. With visibility proven, a bad grant in chunk 2 → SEC-15 `compliant` (O8) | confirmed | Item 10 |
| Critical | `base.py:323-326` | The `column_tags` SQL can only return tables that already have a tag, and `count(*) > 0` is always true, so any row → 100% coverage → SEC-16 green | confirmed | Item 11 |
| Critical | `base.py:321-322` | SEC-15 reads table grants only. `ALL PRIVILEGES` on a catalog or schema is never seen (O12) | confirmed | Item 11 |
| Critical | `base.py:310-313, 330-335` | The audit / query-history / endpoint-usage SQL has `LIMIT` and no action filter. The event that matters can sit past the limit → SEC-08/19/25/28/30 absence checks green | confirmed | Item 11 |
| Critical | `unity_catalog.py:234, 242` | `allowlisted` and `via_ai_gateway` default to `True`, but the SQL never selects them → SEC-25 and SEC-28 always green live | confirmed | Item 12 |
| Critical | `workspace.py:59` | `lifetime_days` isn't in the token-management response (`creation_time` / `expiry_time` are). Default 0 → SEC-06 green live | confirmed | Item 12 |
| Critical | `base.py:297-302` | Statement Execution `JSON_ARRAY` returns every value as a string. `"false"` is truthy (SEC-16), and `spark_conf` iterates characters (SEC-14) | plausible (docs) | Item 10 |
| High | `workspace.py:153-162` | A live read never carries `_iac_declared`, so an empty allow-list → SEC-24 green | confirmed | Item 12, **O16 needs Manish** |
| High | `azure.py:59`, `entra.py:31` | `is_databricks_workspace_admin` and `account_admins` / `metastore_admins` aren't API fields → SEC-03 / SEC-07 green live | plausible (not read) | Item 12 (verify first) |
| High | `fixtures\build_demo.py:187` | An unmatched target defaults to `{"compliant": True}`, so a new control is green in demo and CI | confirmed | Item 12 |
| Medium | `config.py:86-87` | `host_for` checks scope before plane: per-workspace azure/sentinel reads go to the Databricks host with an ARM token (a wrong-audience token sent to a different host) | confirmed | Item 13a |
| Medium | `base.py:198, 170` | SEC-29 on the workspace host uses the `databricks-account` token (O10). Fails safe (401 → `unknown`) | confirmed, **new** | Item 13b |
| Medium | `base.py:271` | The SEC-08 audit spec (`per-account`) has no host → always `unknown` live (O11). Fails safe, but the signal is lost | confirmed, **new** | Item 13c |
| Medium | `unity_catalog.py:114` | `_system_schemas` expects `enabled_schemas`, but the SQL returns rows → SEC-01 false **red** | confirmed | Item 12 |
| Low | `config.py:110` | `databricks_url.startswith` on `None` crashes `build` | confirmed | Item 13 |
| Low | `base.py:310` | Per-workspace audit specs judge account-wide events (misattribution, never green) | confirmed | O17, slice 2 |

## Rulings on Dino's open items

| # | Ruling | Owner |
|---|---|---|
| **O8** chunked SQL results | **New spec item 10**, turn B, blocks 1.9. Follow `next_chunk_internal_link` (GET), refuse `truncated`, check `total_row_count`, and type values from the manifest | Dino |
| **O9** empty NCC list returned as `{}` | **No code now.** Today it goes `unknown`, which is the safe side. On run #1, Manish records the raw NCC body. If it's `{}`, a dbSat-1.10 item decides whether "200, no `items`, no `next_page_token`" counts as an empty list. That's a judgement about the API, and I make it with evidence, not before | Manish (run #1) → Daya |
| **O10** SEC-29 account token on the workspace host | **Spec item 13b**, turn B. Metastore-scope reads use the `unity-catalog` credential | Dino |
| **O11** UC per-account scope has no host | **Spec item 13c**, turn B. UC SQL for a non-workspace scope (`account`, `metastore`) runs on `hosts["metastore"]`. UC system tables are metastore-wide | Dino |
| **O12** SEC-15 skips catalog/schema privileges | **Spec item 11**, turn B, blocks 1.9. `UNION ALL` of the UC `*_privileges` views under the existing target key. Registry-neutral; renaming the target joins the O2 proposal. `ANY FILE` as a Hive privilege stays O5 (run #1) | Dino; O5 Daya |

**New open items**

- **O15 (Manish/Nolan):** which schemas are "curated" for SEC-16? Until someone answers, item 11 measures every
  non-system table. That's an honest red, never a green. SEC-16 is `blocked_by` serverless anyway.
- **O16 (Manish, needs_human):** SEC-24 on live has no IaC-declared list (it's an ADO cross-plane read, not built).
  - **Recommended option (c):** a world-open CIDR is a deviation without IaC evidence. Otherwise raise `IncompleteObservation` → `unknown`. The fixture then drops `_iac_declared` (rule 4), and the baseline moves to **16/7/4/1/3**.
  - **The cost:** the SEC-24 apply→verify demo loop stops confirming, because after the fix, verify reads `unknown`.
  - **Option (b):** keep `_iac_declared` in the fixture as a documented rule-4 exception. The baseline stays, but the fixture holds something a live read can't produce.
  - Item 12's SEC-24 part is on hold until you decide.
- **O17 (Daya, slice 2):** filter per-workspace audit SQL by `workspace_id`.

**Sequencing (for Pradyuman, Manish to confirm):**

- **Turn B** = items 10 → 11 → 12 → 13 → 14. False greens come first, per the spec's own rule.
- **Turn C** = items 6 → 7 → 8 → 9.
- dbSat-1.9 (live run #1) waits for turn B.

## Proposed commits

**Control-tool repo: one combined commit.** Dino interleaved the items within the same files, and
splitting them would mean hunk-staging (`git add -p`), which buys nothing. The body maps item → test.

```
dbSAT slice 1 turn A: close two false greens, correct four API paths

Spec: myAgents/dspm/docs/specs/dbSatSlice1.md (items 1, 2, 5, 3a-3d).
Review: myAgents/dspm/docs/specs/dbSatSlice1Review.md - accepted.

- Item 1: dbutils.fs.mounts placeholder removed; NOT_COLLECTABLE refuses it
  before any request -> SEC-15 per-workspace unknown
  (tests.test_false_green.MountsPlaceholder)
- Item 2: UC visibility probe (metastore_summary + SCIM Me) gates the
  absence-based information_schema reads; not proven -> unknown
  (insufficient-visibility), target not read (HiddenGrants)
- Item 5: {account_id} templating, deterministic metastore host,
  projections, fail-closed pagination, IncompleteObservation; _sql
  dict-order host fallback removed (tests.test_routes.SharedMechanisms)
- Item 3a: identity-sourcing has no documented read API -> NOT_COLLECTABLE,
  no guessed path (IdentitySourcing)
- Item 3b: NCC list on accounts/{account_id}/network-connectivity-configs,
  every page, real shape; PE rules present -> unknown until egress is
  observable (NetworkConnectivity)
- Item 3c: SEC-29 from metastore_summary on the workspace host, projected
  to delta_sharing_scope (DeltaSharingScope)
- Item 3d: SEC-18 keys built from EXFIL_TOGGLES; a null/missing toggle is
  unknown, not closed (ExfilToggles)
- fixtures/build_demo.py regenerated: 7 planes, 103 keys

Red run vs old ctl/: 35 failures + 10 errors. Suite 135/135. validate OK.
Fixture baseline 17/9/4/1/0 -> 16/8/4/1/2 (as spec predicted).
Reviewed: /code-review, silent-failure-hunter, pr-test-analyzer. No
introduced false green; pre-existing live false greens carried to spec
items 10-14. No registry, inventory, exception or .env change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

**myAgents repo: one commit.** This review, the spec addendum, Dino's run record and memory, and the
`dspm\readme.md` row (after Dino's fix above, or together with it if Manish edits line 42 by hand):

```
dbSat slice 1: turn A reviewed and accepted; spec items 10-14 added

- dspm/docs/specs/dbSatSlice1Review.md: per-item verdicts, O8-O12 rulings,
  new O15-O17, carried-forward live false greens
- dspm/docs/specs/dbSatSlice1.md: two-GET probe correction; section (e)
  items 10-14 (statement completeness/typing, absence-based SQL shape,
  fixture-shaped assertions, host/token selection, test strengthening)
- agentDino run record + memory for turn A

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

---

```
FROM AgentDaya → TO Manish (commit), then AgentDino (turn B)
Artifact:   dspm\docs\specs\dbSatSlice1Review.md; spec § (e) items 10–14
Needed:     Manish: commit turn A as proposed (control-tool + myAgents), decide O16, confirm
            1.9 waits on turn B. Dino: turn B = items 10 → 14, test first, then the
            dspm\readme.md line-42 fix.
Done when:  Both commits pushed; O16 answered; turn B red runs recorded and green; fixture
            baseline unchanged by items 10, 11, 13, 14 (item 12 per the O16 answer); my review of turn B clean.
Open:       O9 and O6 on run #1 (Manish); O15 curated schemas (Manish/Nolan); O16 SEC-24 (Manish).
```

---

# Turn B: items 10–14, plus two test-only fix turns

- **Reviewer:** AgentDaya · **Builder:** AgentDino · **Date:** 2026-09-27
- **Build record:** `dspm\docs\buildNotes\dbSatSlice1TurnB.md`
- **Evidence (Manish ran it, 2026-09-27):**
  - Red run against the committed `ctl\`: **42 failures + 3 errors**.
  - Fixtures regenerated.
  - Full suite **182/182 OK**.
  - `validate` consistent.
  - `run` = **16/7/4/1/3**. That is exactly what O16 option (c) predicts.
- **Uncommitted CT files:**
  - `ctl\collectors\{azure,base,entra,unity_catalog,workspace}.py`
  - `ctl\config.py`
  - `ctl\stages\plan.py`
  - `fixtures\build_demo.py`
  - `README.md`
  - `tests\{fake_http,test_false_green,test_routes}.py`
- **How reviewed:**
  - The first pass read every changed file and ran `/code-review`, `silent-failure-hunter` and `pr-test-analyzer`. It was cut short by an out-of-memory stop after spec § (f) had been written. That addendum is the record of that pass's findings.
  - This pass re-read `base.py` `_get` / `_sql` / `_statement_rows` / `_typed_*` (`base.py:204-398`) and `config.SCOPE_HOSTED_PLANES` (`config.py:58`), and confirmed the § (f) findings still stand.
- **Status:** fixture-verified. Nothing has run live.

## Verdict

**Turn B is accepted as one combined control-tool commit.**
- No introduced false green. Every new failure path fails to `unknown`.
- The baseline moved only as O16 decided.
- No registry, inventory, exception or `.env` change.

The two fix turns changed tests only. Both were correct:
- O16 governs the IaC comparison per workspace. SEC-24's per-account scope is a Sentinel rule-health spec, so `compliant` there is observed, not defaulted.
- The loop can't pass vacuously: it asserts that at least one scope exists.

**The remaining live false greens are spec item 15** (§ (f), pre-existing, confirmed). They block dbSat-1.9, so item 15 opens turn C.

## Per item

| # | Verdict | Evidence / notes |
|---|---|---|
| 10 | **Accept** | `base.py:321-358`: refuses `truncated`, an empty schema, a non-`JSON_ARRAY` format, a missing int `total_row_count` and `external_links`. Chunks are GET on the same host, path-only (`//` refused), and capped at `MAX_PAGES`. The count must match. `_typed_rows` refuses width mismatches and unnamed or untyped columns, and a conversion failure → `BackendError`. Test gaps → 15g |
| 11 | **Accept** | UNION ALL over the six views; tags start from `tables` with a `LEFT JOIN`. The LIMIT rule is at `base.py:308-310`. The `PRESENCE_PROBES` key equals the registry target text (`controlRegistry.yaml:45`), so the exemption matches. Side effect: SEC-17 lineage `LIMIT 100` now reads `unknown` on a busy metastore. That is the safe side, and it's tracked in O24 |
| 12 | **Accept, with SEC-01 held** | Required access for `allowlisted` / `via_ai_gateway`. The "verify first" results are recorded (ARM and Graph carry no such fields; both read `unknown` live, safe). SEC-06 lifetime is expiry minus creation, and -1 or missing counts as over. SEC-24 follows O16. `build_demo.py` raises on an unmatched target. **But** an empty `rows` list is still green for SEC-25/28 → **15a** |
| 13 | **Accept** | 13a `SCOPE_HOSTED_PLANES` = workspace + UC only. 13b: the `metastore` scope uses the UC credential (`base.py:208`). 13c: `account`/`metastore` SQL runs on `hosts["metastore"]` with no fallback (`base.py:282-285`). 13d: `build` survives a `None` URL. 13e is covered by `TargetCoverage`. Regression on SEC-20 → item 17 (fails safe) |
| 14 | **Accept, wording corrected** | The NCC assertion is exactly `prerequisite-gap`, and it names the bad NCC. Empty page 2, HTTP non-admin integration, probe failures and `scopes_for` derivation are all present. More hardening → 15g |
| — | Fix turns 1–2 | **Accept.** Test-only. `ctl\`, the registry and the fixture were untouched between them |
| — | `dspm\readme.md` | **Accept.** Dino updated the D1 row in turn B. Manish adds the evidence line when committing |
| — | security-guidance | No hook warnings surfaced. The one security point, a chunk or `nextLink` sending the token off-host, is closed for chunks (item 10) and specified for ARM/Graph (15f) |

## Rulings on Dino's held items

| Item | Ruling |
|---|---|
| **SEC-01 hold** | **Upheld. Dino was right to stop.** Raising `IncompleteObservation` would move the baseline, and the spec said to stop if that happened. The current behaviour is a false **red** (safe direction). The fix needs a new detect target, which is a registry change → **O23**, a Daya proposal together with O2, for Manish. Not a Dino item |
| **13a vs SEC-20** | **Accept 13a as built.** A 404 → `unknown` fails safe, and SEC-20 is a one-way door that is never planned. The workspace-host read is **item 17** (after turn C, doesn't block 1.9). Scope: a detection read only. Nothing about SEC-20 becomes plannable (P6) |
| **`total_row_count` required** | **Accepted, and the spec is amended** (changelog 2026-09-27). Without a count, "no `data_array`" can't be told apart from "rows not delivered". Databricks returns `total_row_count: 0` for an empty inline result, so a truly empty table still reads (verify on run #1: O4) |
| **Item-14 NCC wording** | **Dino's reading is correct.** SEC-23 is `blocked_by`, so assess reports `prerequisite-gap`. The spec wording was wrong and is fixed in § (e) and the changelog |
| O18 `artifact-allowlists` | → **item 16** (REST read). `UC_KNOWN_GAPS` pinning is accepted in the meantime; it reads `unknown` |
| O19 empty SEC-24 payload | → **item 18** (exclusion, no fallback). Unreachable while SEC-24 is `observe` |
| O20 second metastore | Slice 2 (Daya) |
| Pre-existing SFH list | SEC-21 JSON-string definition and ARM/Graph `nextLink` → 15c / 15f. SEC-14 → 15b, SEC-10 → 15d, SEC-13 → 15e. SEC-06 `{}` stays with O9 (run #1) |

## Proposed control-tool commit

Dino's message (build notes § "Proposed commit") is accepted, with the evidence and review lines filled in:

```
dbSAT slice 1 turn B: close latent live false greens (items 10-14)

Spec: myAgents/dspm/docs/specs/dbSatSlice1.md section (e); decision O16.
Review: myAgents/dspm/docs/specs/dbSatSlice1Review.md (Turn B) - accepted.

- Item 10: statement results read every chunk (GET, same host, path
  only), refuse truncated/no-schema/no-count/non-JSON_ARRAY/external-link
  results and count mismatches, and type values from the manifest
  (tests.test_routes.StatementResult)
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
- Item 14: exact NCC status (prerequisite-gap), empty page 2, HTTP
  non-admin integration, probe failures, scopes derived via scopes_for
- fixtures/build_demo.py regenerated
- FixtureBaseline: O16 unknowns asserted on per-workspace IP-list scopes
  only; SEC-24 account scope (Sentinel alert 5) asserted as observed
  compliant, its source proved from the registry's per-account event spec

Red run vs committed ctl/: 42 failures + 3 errors. Suite 182/182. validate OK.
Fixture baseline 16/8/4/1/2 -> 16/7/4/1/3 (O16 option c).
Reviewed: /code-review, silent-failure-hunter, pr-test-analyzer. No
introduced false green. Held: SEC-01 (O23, registry proposal), O18
artifact-allowlists (item 16). Remaining pre-existing live false greens
-> spec item 15 (turn C, blocks 1.9).
No registry, inventory, exception or .env change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

**myAgents commit:**

```
dbSat slice 1: turn B reviewed and accepted; turn C restated

- dspm/docs/specs/dbSatSlice1Review.md: Turn B verdicts, rulings on
  SEC-01 hold, 13a vs SEC-20, total_row_count, item-14 wording
- dspm/docs/buildNotes/dbSatSlice1TurnB.md, dspm/readme.md D1 row

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

(The § (f) addendum is already committed in `bc7a318`.)

## Turn C: the build contract (15 → 6 → 7 → 8 → 9)

Common to every item:
- Test first, and record the red run.
- Registry-neutral. No `.env`. No `--live`.
- Fixtures come only from `fixtures\build_demo.py`.
- **The baseline holds at 16/7/4/1/3. If it moves, stop and report.**

`PY="$USERPROFILE/.venvs/agentDino/Scripts/python.exe"`. CT = `secopsCurrentProjects/databricks/controlTool`.

One proposed CT commit per item, in this order. Item 9 is a myAgents commit.

### 15: remaining live false greens (spec § (f) item 15, verbatim contract)

| Sub | Module · function | Change | Test |
|---|---|---|---|
| 15a | `ctl\collectors\unity_catalog.py` `_library_installs`, `_gateway_usage` | `rows == []` → `IncompleteObservation("no rows - absence of installs/usage is not evidence")` | `LiveShapedAssertions`: empty rows → SEC-25 audit spec and SEC-28 `unknown` |
| 15a fx | `fixtures\build_demo.py` | `system.access.audit` +1 row `{"action_name": "installLibraries", "source": "pypi", "allowlisted": true, "principal": "svc-pdp-etl"}` | `FixtureBaseline` unchanged; SEC-08/19 unchanged |
| 15b | `ctl\collectors\workspace.py` `_spark_conf_keys` | substring match `"fs.azure.account.key" in k` | `spark.hadoop.fs.azure.account.key.x` → deviation |
| 15c | `workspace.py` `_cluster_policy_bypass` | null or missing `data_security_mode` = unsafe, reported `"<cluster> (unset)"` | null mode → deviation and names `(unset)` |
| 15d | `workspace.py` `_no_individual_acls` | GUID principal (regex `^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$`, case-insensitive) = individual; bare name = group | SP GUID → deviation; `data-engineers` → group |
| 15e | `workspace.py` `_no_cross_env_scopes` | `AZURE_KEYVAULT` without `keyvault_metadata.dns_name` → `IncompleteObservation` | → `unknown` |
| 15f | `ctl\collectors\base.py` `HttpBackend._get` (planes `azure`, `sentinel`, `entra`) | dict with `value` list and `nextLink` / `@odata.nextLink` → GET until none, return `{"value": all}`. Link must start with `config.host_for(plane, scope)`, else `BackendError`. Page without a `value` list → `BackendError`. `MAX_PAGES` → `BackendError` | `tests\test_routes.py::ArmGraphPaging`: two pages; foreign host; no `value`; cap |
| 15g | tests in place | pin `ABSENCE_BASED_TARGETS` (3); chunk-500 reason names the URL; `external_links` with `total=0`; row-width mismatch; self-link → exactly `MAX_PAGES` GETs then `BackendError`; chunk without `data_array`; `//host/x` refused; 13a asserts the `Authorization` header never reaches `azuredatabricks.net` with an ARM/Graph token; comment at `base.py:345-346` | same classes |
| 15h | `ctl\stages\plan.py` (joined `if` line break); `README.md` test count and the "every UC target has a SELECT" sentence | docs / style | n/a |

Command: `$PY -m unittest tests.test_false_green.LiveShapedAssertions tests.test_routes.ArmGraphPaging tests.test_routes.StatementResult -v`, then the full suite.

### 6: `CTL_ENV_FILE` + OneDrive secret guard. Contract: spec § (c) item 6

- **Where:** `ctl\cli.py` `_load_dotenv()` (line 36), `ctl\config.py` `build()`, `README.md`.
- **`_load_dotenv`:** returns the loaded path; it stays `setdefault`. `CTL_ENV_FILE` set but missing → `SystemExit` naming the path.
- **Guard:** `config.build` reads a module-level `cli.LOADED_ENV_FILE` (or takes it as a parameter; Dino picks one and says which). It appends the spec's exact `cfg.missing` message. Never print the value.
- **Tests:** `tests\test_auth_config.py::EnvFileHandling` (5 cases in the spec). Use `mock.patch.dict(os.environ, {"OneDrive": tmp})` with a temporary directory. No real OneDrive path.
- **Command:** `$PY -m unittest tests.test_auth_config.EnvFileHandling -v`

### 7: preflight computed `unknown` list + visibility line. Contract: spec § (c) item 7

- **Where:** `ctl\config.py` `PLANE_SETTINGS` (line 61) drops the hard-coded `affects` strings. Add a new `affected_controls(reg, plane) -> list[str]`: sorted control ids with ≥1 detect spec where `collectors.route(spec)` is a collector of that plane.
- **Use it in** `config.build` (line 163-169 message), `preflight_report` (line 220-244), **and `ctl\setup.py` lines 280 and 432-436**, which also read `affects`. Keep one source.
- **Visibility line:** `preflight_report` calls `HttpBackend(config=cfg).read("unity-catalog", "metastore", "uc/visibility")` only when the UC host and token resolve. It prints one of the three lines in the spec. The NO list comes from `ABSENCE_BASED_TARGETS`. It warns and never blocks. Any `BackendError` → `not checked: <reason>`.
- **Tests:** new `tests\test_preflight.py`. The ids are read from the registry, not hard-coded. It covers yes / NO / not-checked through `fake_http.FakeSession`, and asserts the session saw GETs only.
- **Command:** `$PY -m unittest tests.test_preflight -v`

### 8: `GuardedSession`, `requests.json`, 401/403/404/timeout, `setup --check`. Contract: spec § (c) item 8

- **Where:** `ctl\collectors\base.py` gets a new `GuardedSession`, wrapped in `HttpBackend.__post_init__`. `_fetch`, `_sql` and chunk GETs all go through it.
  - **POST** is allowed only to `…/api/2.0/sql/statements`, with a statement that starts with `SELECT` after strip/upper and contains no `;`.
  - **`request_log`** entries are `{method, url (query stripped), statement_head[:60] | None, status}`. No headers.
- **`ctl\orchestrator.py`** writes `runs\<id>\requests.json` when `getattr(backend, "request_log", None) is not None`. Fixture runs write nothing.
- **`ctl\setup.py` `run(check_only=True)`** (line 206) reports per plane "token acquired" or the named failure, plus the item-7 visibility line.
- **Tests** (`tests\test_http_backend.py`, new):
  - `RequestLogGuard`: full pipeline over `FakeSession` with a representative 200 per route, and every log entry is a GET or the allowlisted POST;
  - a test that `ctl\auth.py`'s only POST host is `login.microsoftonline.com`;
  - 403 on `token-management/tokens` → SEC-06 `unknown`, `evidence\SEC-06.json` error contains `403`, and the run reaches `report`;
  - 401 → same; 404 → `not-collected`; `requests.exceptions.Timeout` → `unknown` (`unexpected:`);
  - `setup --check` with a failing `databricks-account` token source → that plane is named, and the log has no non-GET;
  - write refusal: POST to another path, a `SELECT …; DROP` statement, and a non-SELECT all raise before send (`FakeSession` records nothing).
- **Command:** `$PY -m unittest tests.test_http_backend -v`

### 9: `dspm.posture` adapter. Contract: spec § (c) item 9 (interface verbatim)

- **Where (new files):**
  - `dspm\posture\__init__.py`
  - `dspm\posture\adapter.py`
  - `dspm\tests\__init__.py`
  - `dspm\tests\test_postureAdapter.py`
- **Loading `ctl`:** `load_ctl()` inserts `CTL_ROOT` into `sys.path`. Unset or invalid → `AdapterError`.
- **Interface:** `FindingRecord`, `RunRecord`, `read_run` and `verify_evidence` exactly as in the spec.
- **Hash:** the same as `ctl.stages.report.evidence_pack`. Import that function, or mirror it and add a test that compares the two on one record.
- **Tests:** the six in the spec. `setUpClass` runs `ctl.orchestrator.run_pipeline` on the fixture into `tempfile.mkdtemp()`, outside OneDrive via `%TEMP%`. Add one more: bucket counts equal the run's 16/7/4/1/3 roll-up, and `FindingRecord` has no percentage field.
- **Command** (myAgents root): `CTL_ROOT="<CT abs path>" $PY -m unittest discover -s dspm/tests -v`

### Turn C done when

- Every red run is recorded.
- The full CT suite is green: `$PY -m unittest discover -s tests -v`.
- `$PY ctl.py validate` exits 0.
- `$PY ctl.py run` = **16/7/4/1/3**.
- dspm adapter tests are green.
- The hand-back lists the commands and outputs.
- Then my review: `/code-review` and `silent-failure-hunter` first.

**dbSat-1.9 (live run #1, Manish only) waits for turn C.** Items 16–18 are turn D and don't block 1.9.

---

```
FROM AgentDaya → TO Manish (commit), then AgentDino (turn C)
Artifact:   dspm\docs\specs\dbSatSlice1Review.md § Turn B; spec § (e), § (f), § (c)
Needed:     Manish: commit turn B in CT with the message above (uncommitted files listed
            in § Turn B), then the myAgents commit; decide O21 (roll-up ranking) and O23
            (SEC-01 registry target) when ready. Dino: turn C = 15 → 6 → 7 → 8 → 9, as
            restated above, one proposed commit per item.
Done when:  Turn B pushed; turn C red runs recorded and green; baseline still 16/7/4/1/3;
            adapter tests green with CTL_ROOT; my review of turn C clean.
Open:       O21, O23 (Manish, ADR/registry). O4/O5/O6/O9 on run #1. O15 curated schemas.
            If the baseline moves in turn C, stop and report; do not tune the fixture.
```

---

# Turn C: items 15, 6, 7, 8, 9, plus fix turns C.1 and C.2

- **Reviewer:** AgentDaya · **Builder:** AgentDino · **Date:** 2026-09-27
- **Build record:** `dspm\docs\buildNotes\dbSatSlice1TurnC.md` (held items C1–C6)
- **Evidence (Manish ran it, 2026-09-27):**
  - Red run against the committed `ctl\`: **25 failures + 23 errors**. Tests-first is evidenced.
  - Fixture regenerated.
  - CT suite **239/239 OK** (after C.2).
  - `validate` consistent.
  - `run` = **16/7/4/1/3**. The baseline held.
  - dspm adapter tests OK with `CTL_ROOT` set.
- **How reviewed:** one reading pass, unattended.
  - Read: `adapter.py` in full; `base.GuardedSession`, `HttpBackend.__post_init__`/`_fetch`/`_get`/`_follow_next_links`; `cli._load_dotenv`/`onedrive_secret_file`; `config.affected_controls`/`build`/`visibility_line`; `orchestrator._write_request_log`; the adapter test list.
  - Grepped `ctl\` for every network call. The only ones outside `GuardedSession` are `auth.py:120` (token POST) and `stages\apply.py` (stage 8, the gated writer, out of scope).
  - **`/code-review`, `silent-failure-hunter` and `pr-test-analyzer` were not run this pass.** The commit message says "reviewed by reading", not the plugin names.
- **Registry / `.env` / inventory / exceptions:** untouched. No `--live`.
- **Status:** fixture-verified. Nothing has run live.

## Verdict

- **CT commit: accepted** as one combined commit (C1).
- **myAgents adapter commit: held for fix turn C.3** (finding F1, below). It is small and test-first, and it does not block the CT commit or the 1.9 prerequisites.
- No introduced false green in `ctl\`. Every new failure path ends in `unknown`, a refusal, or a loud `cfg.missing` line.

## Per item

| # | Verdict | Evidence / notes |
|---|---|---|
| 15a–e | **Accept** | Zero install/usage rows → `IncompleteObservation`. The fixture got one real install row, so SEC-25 is judged from a row and not from absence. The `spark.hadoop.` key, the unset access mode, the SP GUID and the KV scope without `dns_name` all fail to deviation or `unknown` as specced |
| 15f | **Accept, tightening confirmed** | `base.py:320` needs `link.startswith(host + "/")`, so both `host.evil.example` and `host@evil` are refused. Also refused: a page with no `value`, and hitting `MAX_PAGES`. A body with no link comes back unchanged. The token never leaves the plane host |
| 15g–h | **Accept** | The hardening tests are in place. README count 239, key count 103 |
| 6 | **Accept** | `CTL_ENV_FILE` set but missing → `SystemExit`, no fallback (`cli.py:58-62`). `setdefault` is kept. The guard uses `commonpath` on `normcase`d resolved paths, never reads the value, and appends the spec's text to `cfg.missing` (`config.py:195-201`), so preflight and `--live` refuse. Module state over a parameter: **accepted**, because a forgotten parameter would be a silently skipped guard. Low (F3): the guard depends on the `OneDrive*` env vars, so a context without them skips it |
| 7 | **Accept** | One source: `affected_controls` routes through `collectors.route` (`config.py:77-88`) and is used by build, preflight and `setup`. The visibility line uses the collector's own `_visibility_gap`. Any error becomes `not checked: …`, and the line never touches `cfg.missing`. The added no-token / no-host / placeholder short-circuit is **accepted** (no DNS-failing GETs). ASCII `->` is **accepted** (cp1252 stdout). Low (F2): `raw['metastore_id']` at `config.py:285` sits outside the `try`, so a malformed probe body raises `KeyError` in preflight. That is loud, not silent |
| 8 | **Accept** | `GuardedSession` has `get`/`post` only. A POST needs the path to end in `/api/2.0/sql/statements`, no query, a string statement, a `SELECT` prefix and no `;`. Anything else is refused **before** `call()`. The log stores method, query-stripped URL, a 60-char head and status, with no headers. A timeout leaves `status: None` and the exception propagates. The wrap is unconditional and never doubled. `requests.json` is written after discover and at finish, and not at all for a fixture run. `WITH …` CTEs are refused, which is the safe side |
| 9 | **Accept the design; C.3 before commit** | Whole-run rejection covers: a missing or unparseable artifact, a non-bucket status, an unknown control, an unmappable scope, a registry-version mismatch, a hash mismatch, and a hashed status that disagrees with `findings.json`. The status cross-check (C2.1) is the right call. **Gap F1:** omission is not detected (below) |
| C.1 | **Accept** | `cls.run` shadowed `TestCase.run`. Test-only rename |
| C.2 | **Accept** | Real `Registry` via `dataclasses.replace(load(), workspaces=…)`. No tolerance for a non-iterable registry was added to `ctl\`. That is correct |
| — | security-guidance | No hook warnings surfaced this session |

## New findings

| # | Sev | Where | Finding | Disposition |
|---|---|---|---|---|
| **F1** | **High** (false green by omission) | `adapter.py:174-221` | The adapter checks every finding it is given, but never checks that it was given all of them. `findings.json` is not hashed. A deviation deleted from it, or a scope a ctl bug never emitted, publishes a smaller run that still verifies, and every bucket still adds up because the counts come from the same file | **Fix turn C.3 (Dino), test first:** (a) the set of `(control, scope)` in `findings.json` must equal the union of `status_by_scope` keys across `evidence\*.json`, or `AdapterError`; (b) a duplicate `(control, scope)` → `AdapterError`; (c) an evidence file with no finding → `AdapterError`. Tests: drop one deviation from a copied run; duplicate one finding; add a stray evidence file. The baseline must not move |
| F2 | Low | `config.py:285` | `KeyError` possible outside the `try` | Turn D: move it inside the `try` → `not checked` |
| F3 | Low | `cli.py:84-93` | The OneDrive guard does nothing when no `OneDrive*` var is set | Turn D: also refuse when `CTL_ROOT`/the file resolves under a path segment starting `OneDrive` |

## Rulings on C1–C6

| Item | Ruling |
|---|---|
| **C1** commit granularity | **One combined CT commit, accepted**, with a body that maps each item to its tests (the turn A precedent). Staging with `git add -p` across shared hunks risks a commit that doesn't build, and that costs more than per-item history is worth |
| **C2** tightenings | **All accepted.** 15f `host + "/"`: correct. Adapter 1 (hashed status must match): required. 2 (registry version must match): required, because `desired` comes from the loaded registry. 3 (oldest `collected_at`): correct, since a finding is only as fresh as its stalest input. 4 (a failed visibility probe rejects the run): **upheld for slice 1.** The alternative, dropping metastore findings, is a partial publish. Run #1 consequence: a 403 on `metastore_summary` means no DSPM publication, while the CT run itself still stands |
| **C3** account-id over-inclusion | **Accept as built** (it errs toward `unknown`). Per-route precision → turn D, low |
| **C4** wizard writes `ROOT\.env` in OneDrive | **Spec gap, mine.** → **item 19 (turn D):** the wizard writes to `CTL_ENV_FILE` when it is set, and refuses to write `AZURE_CLIENT_SECRET` to a OneDrive path. **For 1.9:** Manish writes the env file by hand outside OneDrive and does not use the wizard for the secret |
| **C5** O21 | Still Manish's decision. Once he decides, I write the spec item and the predicted baseline row (SEC-24, and probably SEC-15, `unknown` → `deviation`). It does not block 1.9 |
| **C6** `_library_installs` has no `action_name` filter | Fails safe live (`unknown`). → with **O24**, turn D |

## Proposed commits

**Control-tool repo (accepted, commit now):**

```
dbSAT slice 1 turn C: last live false greens, env file guard, preflight, request log

Spec: myAgents/dspm/docs/specs/dbSatSlice1.md sections (c) items 6-8, (f) item 15.
Review: myAgents/dspm/docs/specs/dbSatSlice1Review.md (Turn C) - accepted.

- Item 15: SEC-25/28 zero rows -> unknown; SEC-14 spark.hadoop account key;
  SEC-21 unset access mode unsafe; SEC-10 SP GUID is individual; SEC-13 KV
  scope without dns_name unknown; ARM/Graph next links followed on the plane
  host only (host + "/"), capped (LiveShapedAssertions, ArmGraphPaging,
  StatementResult)
- Item 6: CTL_ENV_FILE (no fallback when missing); a client secret loaded
  from a OneDrive-synced file blocks preflight/--live (EnvFileHandling)
- Item 7: unknown lists computed from registry routing, one source for
  preflight and setup; UC VISIBILITY line, warning only (test_preflight)
- Item 8: GuardedSession (GET + single SELECT only, refused before send),
  runs/<id>/requests.json, 401/403/404/timeout -> unknown with the run
  completing, setup --check per plane (test_http_backend)
- Item 9 pair: per-account spec is one scope for many workspaces
- Test-only fixes: TestCase.run shadowing; real Registry in test_routes
- fixtures/build_demo.py regenerated (SEC-25 install row); README

Red run vs committed ctl/: 25 failures + 23 errors. Suite 239/239.
validate OK. Fixture baseline 16/7/4/1/3 unchanged.
Reviewed by reading (AgentDaya): no introduced false green. Follow-ups
F2/F3, C3, C4 (item 19), C6 -> turn D.
No registry, inventory, exception or .env change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

**myAgents repo, now (review and hand-back only):**

```
dbSat slice 1 turn C reviewed: CT accepted, adapter held for C.3

- dspm/docs/specs/dbSatSlice1Review.md: Turn C verdicts, rulings C1-C6,
  finding F1 (adapter omission check) -> fix turn C.3
- dspm/docs/buildNotes/dbSatSlice1TurnC.md

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

**myAgents repo, after C.3 is green (Dino's message, extended):**

```
dbSat slice 1 turn C: dspm.posture adapter (item 9)

- dspm/posture/adapter.py: FindingRecord/RunRecord from one ctl run;
  whole-run rejection (artifacts, buckets, registry, scope, evidence hash,
  hashed status, and completeness: findings == evidence scopes, no
  duplicates); writes nothing
- dspm/tests/test_postureAdapter.py: dbSat-1.7, 1.8, tamper, unmapped
  account, injected status, omitted/duplicate finding, 16/7/4/1/3
  roll-up, no percentage field
- dspm/readme.md D1 row, memory

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

## What remains for slice 1

1. **C.3** (Dino, then my re-review): F1 only.
2. **dbSat-1.9, live run #1 (Manish only).** Prerequisites:
   - Real `databricks_url` values in place of the `adb-0000…` placeholders (inventory proposal).
   - `DATABRICKS_ACCOUNT_ID` and the SQL warehouse setting.
   - The SP credential provisioned per `config.ACCESS_REQUIREMENTS`.
   - The env file hand-written **outside OneDrive**, with `CTL_ENV_FILE` pointing at it.
   - `preflight` clean; `setup --check` shows `token acquired` on every plane; the UC VISIBILITY line read.
   - Check O4/O5/O6/O9 on the run output and `requests.json`.
3. Turn D (items 16–19, F2, F3, C3, C6/O24) does not block 1.9.

**Slice 2 (merged SEC + SBP registry): ready to spec next turn.** It will be a registry proposal to Manish, not an edit. It folds in O20 (second metastore) and O23 (SEC-01 target), and it assumes O21 is still open unless Manish decides it first.

```
FROM AgentDaya → TO Manish (commit), then AgentDino (C.3)
Artifact:   dspm\docs\specs\dbSatSlice1Review.md § Turn C
Needed:     Manish: commit CT turn C with the message above; commit the myAgents review
            note (not the adapter). Dino: fix turn C.3 = F1 (completeness, duplicates,
            stray evidence), test first, baseline unchanged.
Done when:  CT turn C pushed; C.3 red run recorded, adapter suite green with CTL_ROOT,
            my re-review clean → adapter commit.
Open:       O21 (Manish). 1.9 prerequisites above (Manish/owners). Item 19 wizard spec
            and turn D list (Daya). Slice 2 spec next turn.
```

---

# Turn C.3: adapter completeness (F1) re-review

Scope: `dspm/posture/adapter.py` (`_check_complete`, :132-172, called at :267) and
`dspm/tests/test_postureAdapter.py` (:206-252). Already committed as 58437f4, flagged as
awaiting this review. Evidence: Manish ran 22/22 OK with `CTL_ROOT`, and 4 failures with
`_check_complete` no-oped. So each of the 4 new tests is load-bearing. Code read, not
re-run by me (unattended turn).

## Verdict: **accept. F1 closed. 58437f4 stands, no amend.**

- Duplicate `(control, scope)` → rejected, both named (:138-143). Test :222.
- A scope in the hashed evidence but missing from findings.json → rejected (:167-169). A
  control whose findings were all dropped → rejected (:151-156). Test :208 asserts the
  control and scope are both in the message.
- A scope in findings.json but not in the evidence → rejected (:170-172). An unreadable
  evidence folder → `AdapterError`, not an empty set (:144-147). Good, that is the
  false-green shape from memory `falseGreenSources`.
- A stray evidence file → rejected (:157-158). Test :236.
- The completeness check runs after every record has verified, so a whitewashed status is
  still caught first by `verify_evidence` (:262).

## Ruling on the extra rule: every registry control must have evidence (:159-162)

**Accepted, and it stays.** I checked it against `ctl/stages/assess.py:123-191`. For every
`reg.controls` entry, assess emits a `procedural` finding, an `unknown` finding ("no
observations collected"), or at least one finding per scope. So a control that is absent
from both findings.json and `evidence\` can only mean something was omitted. Without this
rule, deleting one control's finding *and* its evidence file would pass every other check.
The rule fails closed: the worst case is a wrongly rejected run, never a false green.
Condition: if ctl ever starts skipping controls (retired, disabled, or zero governed
scopes), the adapter must read that same filter from ctl. Deleting the rule is not the fix.

## Non-blocking (Turn D)

- **D-N1.** `adapter.py:149-150` matches files by `path.stem`. So `evidence/SEC-06.bak`, or
  a sub-folder called `SEC-06`, is skipped silently rather than rejected as stray. This is
  not a false green, because the real `SEC-06.json` is still verified. Fix: accept only
  `is_file()` with a `.json` suffix; anything else is stray. Add one test.
- **D-N2 (residual, not C.3).** The evidence sha256 proves integrity, not authenticity. If
  someone removes a scope from both findings.json and the evidence file and then re-hashes
  it, the run still passes. That is the limit of the current design. Carry it into the
  slice 2 spec as "signed run manifest or not" for Manish to decide. Do not patch it here.

```
FROM AgentDaya → TO Manish
Artifact:   dspm\docs\specs\dbSatSlice1Review.md § Turn C.3
Needed:     Nothing on the adapter: 58437f4 is reviewed and accepted as it is. Commit
            this review note.
Done when:  Review note committed; slice 1 left = dbSat-1.9 live run (Manish) + Turn D.
Open:       D-N1, D-N2 → Turn D list / slice 2 spec (Daya, next turn). O21 (Manish).
```
