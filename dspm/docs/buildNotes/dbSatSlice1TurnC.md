# dbSAT slice 1, turn C: hand-back (AgentDino → AgentDaya)

- **Date:** 2026-09-27
- **Contract:** `dspm\docs\specs\dbSatSlice1Review.md` § "Turn C" (15 → 6 → 7 → 8 → 9); spec
  `dbSatSlice1.md` § (c) items 6–9 and § (f) item 15
- **State:** code and tests are written but **not run**. This was an unattended turn and the
  shell was refused (one `ls` got through at the start; nothing was executed after that). The
  fixture has **not** been regenerated.
- **Reviewed:** `feature-dev:code-reviewer` read every changed file as it stands (no `git diff`).
  Its one high-confidence finding was the stale fixture, which is the known manual step (command 1
  below). It found no other defects and no baseline drift from the assertion changes.
  `/code-review` and `silent-failure-hunter` are still to run in Daya's review.
- **Registry / `.env`:** untouched. No `--live`.

## Fix turn C.1 (2026-09-27): `'Run' object is not callable`

- **Symptom (Manish's run):** both `test_http_backend` and `test_postureAdapter` errored on every
  test with `TypeError: 'Run' object is not callable` from `unittest/case.py __call__`.
- **Cause:** `setUpClass` stored the pipeline result as `cls.run`, shadowing `TestCase.run`, so
  unittest called the `Run` dataclass. Culprits: `test_http_backend.RequestLogGuard.setUpClass`
  (old line 117) and `test_postureAdapter.PostureAdapter.setUpClass` (line 47). The locals named
  `run` (old lines 102, 157, 166, 191) were harmless but renamed too, for consistency.
- **Fix:** `cls.run` / `self.run` / local `run` → `pipeline_run` in both files, plus a one-line
  comment at each `setUpClass`. `workspace_findings(run, …)` keeps its parameter name (a module
  function, not a TestCase). **Test-only; no `ctl\` or `dspm\posture\` change; baseline
  16/7/4/1/3 and the 239 / 18 counts unchanged.** Not run (shell refused).
- **CTL_ROOT:** the control-tool folder (the one containing `ctl\__init__.py`):
  `<repo-root>`
  — in Git Bash, `export CTL_ROOT="$CT"` using `$CT` from the commands below.

## Fix turn C.2 (2026-09-27): `'types.SimpleNamespace' object is not iterable`

- **Manish's run:** red run 25F + 23E; fixture regenerated; validate OK; run 16/7/4/1/3; dspm
  adapter OK with `CTL_ROOT`. CT suite: 3 errors, all at `config.affected_controls` (`for control
  in reg`), reached from `config.build`'s settings loop.
- **Cause:** item 7 made `build` iterate the registry's controls. Three older `test_routes` tests
  passed a `SimpleNamespace(governed_workspaces=...)` stub as `reg`:
  `HostAndTokenSelection.test_build_survives_a_workspace_without_url` and
  `SharedMechanisms.test_metastore_host_is_first_governed_workspace_by_name` /
  `test_no_governed_workspace_means_no_metastore_host` (via `_build`).
- **Fix (test-only):** a real `Registry` instead of the stub. New helpers in `test_routes.py`:
  `registry_with(*workspaces)` = `dataclasses.replace(load(), workspaces=...)` (the real
  controls, only the given workspaces) and `ws(name, url="")` = a real `registry.Workspace`. The
  no-URL case uses `databricks_url=""` (the dataclass default) instead of `None`; `build`'s
  `if not workspace.databricks_url` treats both the same. **No `ctl\` change** — no tolerance for
  a non-iterable registry. No other test passes a stub to `config.build` (checked with grep).
  Baseline 16/7/4/1/3 and the 239 count unchanged. Not run (shell refused).
- **Commands:** `"$PY" -m unittest tests.test_routes -v`, then `"$PY" -m unittest discover -s
  tests` (expect Ran 239 ... OK).

## Fix turn C.3 (2026-09-27): F1, completeness of `findings.json`

- **Contract:** `dbSatSlice1Review.md` § Turn C, finding F1 (a)–(c). Adapter files only; no `ctl\` change.
- **Change (`adapter.py`):** one new function, `_check_complete`, called after every record verifies and before `RunRecord` is built (one patch point, which is also how the red run is taken). With the hashed evidence as the reference:
    - (b) a second `(control, scope)` → `"<ctl> <scope>: duplicate finding in findings.json"`;
    - an `evidence\` file cited by no finding: if it is a registry control, `"<ctl> <scopes>: in the hashed evidence but missing from findings.json"`; otherwise `"stray evidence/<file>: ..."`;
    - per cited control, `status_by_scope` keys minus `findings.json` scopes → `"<ctl> <scope>: in the hashed evidence but missing from findings.json"`, and the reverse.
  - An unreadable `evidence\` folder is an `AdapterError`, never an empty list.
- **Tightening beyond F1 (please confirm):** every **registry control** must have an evidence file. Without it, dropping all of a control's findings **and** its `evidence\<ctl>.json` still publishes a smaller run. Safe on a real run: `ctl.stages.assess` emits at least one finding per registry control (procedural → `estate`, no observations → `estate unknown`), and `evidence_pack` writes one file per registry control.
- **Tests (4 new, 18 → 22):** `test_deleted_finding_rejects_the_run`, `test_duplicate_scope_rejects_the_run`, `test_stray_evidence_file_rejects_the_run` (F1's three), `test_control_dropped_with_its_evidence_rejects_the_run` (the tightening). Each asserts the control (and scope where there is one) in the message.
- **Expected red run:** the adapter is untracked, so there is no pre-C.3 copy in git. The red run patches `_check_complete` to a no-op (= the pre-C.3 behaviour): **4 failures, 0 errors** (`AdapterError not raised`), the other 18 pass.
- **Baseline:** no code path that changes a record; 16/7/4/1/3 is asserted by `test_record_count_and_buckets_match_the_run`.
- **State:** written, **not run** (unattended; shell refused). `/code-review` not run this turn.
- **Commands (Git Bash; `PY`, `CT`, `MY` as in "Commands for Manish" below):**

```bash
cd "$MY"
# red: completeness check disabled -> expect FAILED (failures=4)
CTL_ROOT="$CT" "$PY" -c "import sys, unittest; from unittest import mock; sys.path.insert(0, '.'); from dspm.posture import adapter; mock.patch.object(adapter, '_check_complete', lambda *a: None).start(); unittest.main(module='dspm.tests.test_postureAdapter', argv=['red'], exit=False)" 2>&1 | tail -5
# green
CTL_ROOT="$CT" "$PY" -m unittest discover -s dspm/tests -v   # expect: Ran 22 tests ... OK
```

```
FROM AgentDino → TO AgentDaya
Artifact:   dspm\posture\adapter.py (_check_complete), dspm\tests\test_postureAdapter.py (+4)
Needed:     Re-review of C.3 = F1 only; rule on the registry-control tightening.
Done when:  Manish's red run = 4 failures; green = Ran 22 ... OK with CTL_ROOT; your re-review
            clean → adapter commit (your extended message, test count 22).
Open:       Tightening: every registry control must have evidence (confirm or drop).
```

## Decisions carried in

| # | Handling |
|---|---|
| **O21** (a proven deviation outranks `unknown` in the roll-up) | **Noted, not implemented.** Items 6–9 don't touch the roll-up: the adapter maps findings one-to-one and never ranks them. Its test compares bucket counts against `ctl.stages.assess.summarise`, so both sides move together when O21 lands. Implementing O21 changes `summarise` and **moves the baseline** (SEC-24 goes `unknown` → `deviation`, and SEC-15 probably does too: it has a metastore deviation plus per-workspace `unknown` scopes). That needs its own spec item and a predicted row from Daya |
| **O23** (SEC-01 registry target) | Deferred to slice 2, as decided. `_system_schemas` is unchanged |

## What changed

### Item 15 (control tool): remaining live false greens

| Sub | Where | What |
|---|---|---|
| 15a | `unity_catalog._library_installs`, `_gateway_usage` | Zero rows now raises `IncompleteObservation("no rows - absence of installs/usage is not evidence")` |
| 15a fx | `fixtures\build_demo.py` | `system.access.audit` now carries one row: `installLibraries`, source `pypi`, allow-listed, principal `svc-pdp-etl`. SEC-08 and SEC-19 filter by action, so they are unaffected |
| 15b | `_spark_conf_keys` | Matches `"fs.azure.account.key" in k`, so it also catches `spark.hadoop.fs.azure.account.key.*` |
| 15c | `_cluster_policy_bypass` | A null or missing `data_security_mode` is unsafe and is reported as `"<cluster> (unset)"` |
| 15d | `workspace._is_individual` | A GUID principal (case-insensitive) counts as an individual. A bare name is still a group |
| 15e | `_no_cross_env_scopes` | An `AZURE_KEYVAULT` scope with no `dns_name` raises `IncompleteObservation`. Also tolerates `keyvault_metadata: null` |
| 15f | `base.HttpBackend._follow_next_links`, `LINK_PAGED_PLANES` | Follows ARM `nextLink` and Graph `@odata.nextLink` for azure, sentinel and entra. Returns `{"value": all}`. Refuses: an off-host link, a page with no `value`, and hitting `MAX_PAGES`. A body with no link is returned unchanged |
| 15g | tests in place, plus the comment at the chunk guard | See the test list below |
| 15h | `plan.py` line break; `README.md` | README: test count, the UC-coverage sentence (names the `artifact-allowlists` gap), and the fixture key count (it said 107; turn A made it 103) |

**Tightened beyond the spec (please confirm):** 15f requires the link to start with
`host + "/"`, not just `host`. Without the slash, `https://management.azure.com.evil.example/…`
would pass the check.

### Item 6: `CTL_ENV_FILE` and the OneDrive guard

- `cli._load_dotenv()` reads `CTL_ENV_FILE`, or falls back to `ROOT/.env`. It keeps `setdefault` and returns the path it loaded.
- If `CTL_ENV_FILE` is set but missing, it raises `SystemExit` naming the path, with no fallback.
- It records `cli.LOADED_ENV_FILE` and `cli.LOADED_ENV_KEYS` (keys with non-empty values).
- `cli.onedrive_secret_file()` does the path check using `commonpath` on `normcase`d resolved paths. It never reads a value.
- **Which option I picked:** `config.build` reads cli's module state (a lazy `from . import cli`). A parameter was the alternative, but every caller would have to remember to pass it, and a forgotten one is a silently skipped guard.
- The message is the spec's exact text. `README.md` documents `CTL_ENV_FILE` (names only).
- **Heads-up for Manish:** this tool lives in OneDrive. If today's `controlTool\.env` sets `AZURE_CLIENT_SECRET`, preflight and `--live` will refuse after this lands. That is intended. The fix is to move the file under `%USERPROFILE%` (outside OneDrive) and set `CTL_ENV_FILE`.

### Item 7: preflight computed list and visibility line

- **Settings list:**
  - `config.PLANE_SETTINGS` now maps a plane to setting names only.
  - `SETTING_PLANE` is new.
  - `affected_controls(reg, plane)` routes through `collectors.route`.
  - `setting_lines()` is shared by preflight and `setup --check`.
- **`ctl/setup.py`:**
  - The wizard prompts (old line 280) and `_check` (old 432-436) now use the computed list, so there is one source.
  - The unused `auth` import is gone.
- **`visibility_line(cfg, reg, session=)`:**
  - It judges with `unity_catalog._visibility_gap`, the same predicate the collector uses.
  - The NO list comes from `ABSENCE_BASED_TARGETS`.
  - Any `BackendError` becomes `not checked: <reason>`. Any other exception becomes `not checked: unexpected <Type>: …`, so it is reported, not swallowed.
  - **Added:** no token, no host, or a placeholder host (`adb-0000…`) gives `not checked` with no request. Without that, preflight on today's inventory would make DNS-failing GETs.
- **Deviation:** the lines use ASCII `->` where the spec has `→`. Python 3.14 on Windows still encodes redirected stdout as cp1252, and `→` would raise `UnicodeEncodeError` when preflight output goes to a file.
- `preflight_report(cfg, reg, *, session=None)` prints the line after SETTINGS. It never touches `cfg.missing`, so the exit code is unchanged.

### Item 8: `GuardedSession`, `requests.json`, HTTP failures, `setup --check`

- **`base.GuardedSession`:**
  - It has `get` and `post` and no other method.
  - A POST is allowed only when the path ends in `/api/2.0/sql/statements`, with **no query**, and with a string statement that starts with `SELECT` and contains no `;` (checked after strip and upper).
  - Anything else raises `BackendError("write refused: …")` before sending.
  - Every request is logged as `{method, url (query stripped), statement_head[:60] | None, status}`. `status` is `None` when no response came (for example, a timeout).
- `HttpBackend.__post_init__` always wraps its session (never double-wraps), and `backend.request_log` is the session's log.
- `orchestrator._write_request_log` writes `requests.json` after discover (before its check, so a halted run keeps the log) and again in `_finish`. Nothing is written when the backend has no `request_log`.
- **`setup._check`:**
  - It now calls `config.build` (the same mint-per-plane path a live run takes) and prints per plane: `token acquired`, or `FAILED - <reason>`.
  - Then settings (computed), then the visibility line.
  - `run(..., session=None)` exists for tests.
  - `auth.probe` is no longer used by setup (it's still tested directly).

### Item 9 (myAgents): the `dspm.posture` adapter

- **New files:** `dspm\posture\__init__.py`, `dspm\posture\adapter.py`, `dspm\tests\__init__.py`, `dspm\tests\test_postureAdapter.py`.
- The interface (`AdapterError`, `FindingRecord`, `RunRecord`, `read_run`, `verify_evidence`) is exactly as in the spec. `load_ctl()` raises on an unset or invalid `CTL_ROOT`, and when a different `ctl` is already imported.
- **Hash:** mirrored as a public `evidence_hash()`, because `evidence_pack` computes it inline and there is nothing to import. A test compares the two on a real `evidence_pack` output.
- **Choices the spec leaves open (please confirm):**
  1. **The status is cross-checked against the hashed evidence.** `verify_evidence` also requires `status_by_scope[scope] == record.status`. `findings.json` is not hashed, so without this check a deviation edited to `compliant` would publish. There's a test for it.
  2. **Registry version must match.** The evidence `standard` must equal the loaded registry's version, or the run is rejected, because `desired` comes from the loaded registry.
  3. **`collected_at` is the oldest** observation for the (check, scope) pair.
  4. **A failed visibility probe rejects the run.** With no `metastore_id`, metastore-scope findings can't be mapped, so the whole run is rejected. That follows the spec's rule, but on live it means a 403 on `metastore_summary` rejects the run. Flagging it in case Daya wants a different mapping.
- The CT-side pair test for 1.8 is `test_routes.SharedMechanisms.test_per_account_spec_is_one_scope_however_many_workspaces`.

## Tests added (57 CT + 18 dspm; CT suite 182 → 239 expected, README says 239)

| Item | Tests |
|---|---|
| 15 (20) | `LiveShapedAssertions` +8 (15a ×2, b, c, d ×2, e ×2); `FixtureBaseline.test_sec25_audit_scopes_are_judged_from_an_install_row`; `HiddenGrants.test_absence_based_targets_are_pinned`; `StatementResult` +3 (self-link cap, chunk without `data_array`, row width) plus in-place edits (chunk-500 names the URL; the `external_links` case uses `total=0`; `//host` refused); `ArmGraphPaging` 7; `HostAndTokenSelection` Authorization-header assertion |
| 6 (6) | `EnvFileHandling`: override loaded, override missing → `SystemExit`, env beats file, OneDrive secret → not ready and value never shown, secret outside → ready, OneDrive file without the secret → not flagged |
| 7 (11) | `test_preflight`: `ComputedUnknownList` 4, `VisibilityLine` 7 (yes / NO / not-checked / no token or host / placeholder / report doesn't block / `setup --check` shares the list) |
| 8 (19) | `test_http_backend`: `RequestLogGuard` 5, `HttpFailures` 4 (403, 401, 404, timeout), `WriteRefusal` 7, `TokenMinting` 2, `SetupCheck` 1 |
| 9 (1 CT + 18 dspm) | CT pair test above; `dspm\tests\test_postureAdapter.py` 18 |

## Expected red run (new tests against the committed `ctl\`)

- **Should FAIL:**
  - 15a–e: the 6 behaviour tests.
  - `ArmGraphPaging`: 6 of 7 (all but the single-page test).
  - `EnvFileHandling`: override loaded, override missing, OneDrive secret.
  - `test_preflight`: all 11 (the new names don't exist yet).
  - `test_http_backend`: `RequestLogGuard` (log and `requests.json`), the timeout test, `WriteRefusal`, `SetupCheck`.
  - `test_postureAdapter`: the whole file errors on import (no module yet).
- **May PASS (guards/hardening):**
  - The bare-group and Databricks-backed tests.
  - `FixtureBaseline.test_sec25…` (the old code gets compliant from zero rows).
  - The pinned targets.
  - The `StatementResult` hardening tests.
  - 403/401/404 → `unknown` (that behaviour already existed; 1.6 asks for proof).
  - `TokenMinting`, `test_fixture_run_writes_no_request_log`, the env-beats-file test, the two ready/not-flagged tests.
  - The per-account pair test.

## Commands for Manish (Git Bash; expected results)

```bash
PY="$USERPROFILE/.venvs/agentDino/Scripts/python.exe"
CT="<repo-root>"
MY="<repo-root>"
cd "$CT"

# 0. Red run: the new tests against the committed code (the tests stay in place)
git stash push -- ctl fixtures/build_demo.py README.md
"$PY" -m unittest tests.test_false_green tests.test_routes tests.test_auth_config tests.test_preflight tests.test_http_backend 2>&1 | tail -5
git stash pop
#    expect: failures/errors roughly as listed above; record the counts

# 1. Regenerate the fixture FIRST (the review's blocker)
"$PY" fixtures/build_demo.py          # expect: wrote fixtures\demo\observations.yaml: 7 planes, 103 observation keys

# 2. Per item
"$PY" -m unittest tests.test_false_green.LiveShapedAssertions tests.test_routes.ArmGraphPaging tests.test_routes.StatementResult -v   # item 15: OK
"$PY" -m unittest tests.test_auth_config.EnvFileHandling -v    # item 6: OK (11 tests)
"$PY" -m unittest tests.test_preflight -v                      # item 7: OK (11 tests)
"$PY" -m unittest tests.test_http_backend -v                   # item 8: OK (19 tests)

# 3. Whole control tool
"$PY" -m unittest discover -s tests -v    # expect: Ran 239 tests ... OK
"$PY" ctl.py validate                     # expect: exit 0, "registry is internally consistent"
"$PY" ctl.py run                          # expect: IN PLACE 16 / GAP 7 / BLOCKED 4 / MANUAL 1 / COULD NOT CHECK 3
#    If the row is not 16/7/4/1/3: STOP and report it (do not tune the fixture).

# 4. dspm adapter (myAgents)
cd "$MY"
CTL_ROOT="$CT" "$PY" -m unittest discover -s dspm/tests -v   # expect: Ran 18 tests ... OK
```

## Open items for Daya

| # | Item |
|---|---|
| C1 | **Commit granularity.** Items 15 and 8 both change `base.py`. Items 6 and 7 both change `config.py`, `test_auth_config.py` and `setup.py`. So "one CT commit per item" would need hunk staging (`git add -p`). I propose one combined CT commit, with a body that maps each item to its tests, as you accepted for turn A. Your call |
| C2 | Confirm the tightenings: the 15f `host + "/"` check; adapter choices 1–4 above |
| C3 | `DATABRICKS_ACCOUNT_ID` missing lists **every** databricks-account control (SEC-08/20/23/29). Only the NCC route (SEC-23) actually needs the id. The list is over-inclusive, which errs on the safe side, but it isn't precise. The per-plane rule is the spec's |
| C4 | `setup` (the wizard, not `--check`) still **writes** `ROOT/.env`, which is inside OneDrive. It ignores `CTL_ENV_FILE`. Item 6 only covered loading. Should the wizard write to `CTL_ENV_FILE` when it's set? That's a spec decision, so I didn't change it |
| C5 | O21: needs a spec item and a predicted baseline row (see above) |
| C6 | `_library_installs` counts every audit row as an install (it doesn't filter `action_name`). Live, any row without `allowlisted` → `unknown` (safe). A filtered statement belongs with O24 |

## Proposed commits

**Control-tool repo** (after the red and green runs; Manish adds the counts):

```
dbSAT slice 1 turn C: last live false greens, env file guard, preflight, request log

Spec: myAgents/dspm/docs/specs/dbSatSlice1.md sections (c) items 6-8, (f) item 15.
Review: myAgents/dspm/docs/specs/dbSatSlice1Review.md (Turn C) - pending.

- Item 15: SEC-25/28 zero rows -> unknown; SEC-14 spark.hadoop account key;
  SEC-21 unset access mode unsafe; SEC-10 SP GUID is individual; SEC-13 KV
  scope without dns_name unknown; ARM/Graph next links followed on the plane
  host only, capped (LiveShapedAssertions, ArmGraphPaging, StatementResult)
- Item 6: CTL_ENV_FILE (no fallback when missing); a client secret loaded
  from a OneDrive-synced file blocks preflight/--live (EnvFileHandling)
- Item 7: unknown lists computed from registry routing, one source for
  preflight and setup; UC VISIBILITY line, warning only (test_preflight)
- Item 8: GuardedSession (GET + single SELECT only, refused before send),
  runs/<id>/requests.json, 401/403/404/timeout -> unknown with the run
  completing, setup --check per plane (test_http_backend)
- Item 9 pair: per-account spec is one scope for many workspaces
- fixtures/build_demo.py regenerated (SEC-25 install row); README

Red run vs committed ctl/: <F> failures + <E> errors. Suite <N>/239. validate OK.
Fixture baseline 16/7/4/1/3 unchanged.
Reviewed: feature-dev:code-reviewer (stale-fixture finding = regeneration step).
No registry, inventory, exception or .env change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

**myAgents repo:**

```
dbSat slice 1 turn C: dspm.posture adapter (item 9) and turn C hand-back

- dspm/posture/adapter.py: FindingRecord/RunRecord from one ctl run;
  whole-run rejection (artifacts, buckets, registry, scope, evidence hash
  and hashed status); writes nothing
- dspm/tests/test_postureAdapter.py: dbSat-1.7, 1.8, tamper, unmapped
  account, injected status, 16/7/4/1/3 roll-up, no percentage field
- dspm/docs/buildNotes/dbSatSlice1TurnC.md, dspm/readme.md D1 row, memory

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

---

```
FROM AgentDino → TO AgentDaya
Artifact:   dspm\docs\buildNotes\dbSatSlice1TurnC.md; CT ctl\ tests\ fixtures\ README.md;
            dspm\posture\adapter.py, dspm\tests\test_postureAdapter.py
Needed:     Review gate for turn C (items 15, 6, 7, 8, 9): /code-review + silent-failure-hunter;
            rule on C1–C6.
Done when:  Manish's red run recorded; fixture regenerated; CT suite 239/239; validate 0;
            run = 16/7/4/1/3; dspm adapter 18/18 with CTL_ROOT; your review clean.
Open:       C1 commit granularity; C2 tightenings; C3 account-id over-inclusion; C4 setup
            wizard writes .env inside OneDrive; C5 O21 needs a spec item + predicted row;
            C6 SEC-25 audit action filter (with O24).
```
