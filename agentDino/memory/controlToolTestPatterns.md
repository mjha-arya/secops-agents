---
name: controlToolTestPatterns
description: Test patterns and traps in the control tool (fixture regeneration, red runs, fake HTTP, host fallback)
metadata:
  type: feedback
---

- **Generated fixture = a manual step in unattended turns.** `fixtures\demo\observations.yaml` comes
  from `fixtures\build_demo.py` and must never be hand-edited. With the shell refused, the YAML stays
  stale, so the first command in the hand-off is `python fixtures/build_demo.py`. Fixture-based tests
  and the baseline assertion fail until it has run.
- **Red run, one failure per test.** Reach a name the fix adds through its module
  (`base.NOT_COLLECTABLE`), not a top-level `from … import`. The old code then gives an
  AttributeError in the one test that uses the name, instead of an import error for the whole file.
- **`tests\fake_http.py`** is the shared no-network session: it records every request, and a URL
  it doesn't know raises. Assert `session.requests == []` to prove a refused target sends nothing.
  Watch for one trap: a wrong URL raises inside `Collector._one`, which turns it into `unknown`. So a
  test that only asserts "unknown" can pass on the old code for the wrong reason. Also assert
  something about the reason (for example, the toggle name).
- **`Config.host_for` falls back from scope to plane.** For the `metastore` scope that fallback lands
  on the accounts host, which is wrong. `HttpBackend._url` special-cases it. Remember this when you
  add a new scope.
- **A `blocked_by` control never reports `deviation`.** `assess` turns any failure into
  `prerequisite-gap` (SEC-04/07/16/20/23). If a spec asks for `deviation` on one of those, the spec is
  wrong: assert `prerequisite-gap` and raise it with Daya.
- **Statement Execution JSON_ARRAY returns every value as a string.** Build fake bodies with
  `type_name` on each column and a `total_row_count` (required since turn B), or `_sql` refuses them.
  The helper for this is `test_routes.statement()`.
- **Collector `_one` catches everything.** For a UC absence target, a test that calls `_one`
  directly gets `insufficient-visibility` unless it first sets `_visibility_gap`
  (`test_routes.uc_finding` does this through a real probe).
- **One control, many detect specs, many scopes.** A control yields one finding per scope, and
  every spec contributes one. SEC-24 has an `event` spec at `per-account` scope (a Sentinel rule),
  so its `account` finding is rule health and correctly comes out `compliant`. Before writing
  "every other scope is X", read every detect spec in the registry. This happened in turn B: the
  test was wrong and the code was right.
- **Keep per-item tests independent of later items.** An item-6 test that called the item-7
  `preflight_report(session=)` would break a per-item commit, and without a session it would
  make real DNS calls to the inventory's URLs. Test the item's own seam (`cfg.missing`).
- **Nothing may reach the network or `az` in tests.** `config.build` → `auth.detect` runs
  `az account show` when no SPN env is set. Always patch `auth.detect` (and `requests.Session`
  when code builds its own `HttpBackend`). Patch `cli.LOADED_ENV_FILE`/`LOADED_ENV_KEYS` too:
  they are module state, and they leak across tests.
- **Red-run-safe setUp:** patching an attribute the fix adds needs `create=True`, or every test
  in the class errors in setUp instead of failing on its own.
- **Unattended write scope:** Edit works on control-tool files. Write was refused outside `dspm\` and
  `memory\` in slice 1, but in slice 2 turn A it **did** create `controlTool\tests\*.py`. Try Write
  first. Hand-back notes still go in `dspm\docs\buildNotes\`.
- **Add a new mandatory registry rule last in `_build_control`.** `test_safety` has negative tests
  that build raw records with no new field and `assertRaises(RegistryError)`. If the new check runs
  first, those tests still pass, but for the wrong reason. Also: a new mandatory field on
  `registry\` breaks every `load(ROOT / "registry")` test until Manish promotes a candidate.
  Transition flags exist for exactly this, so say so in the hand-back.
- **Print ASCII only in CLI output.** Python 3.14 on Windows still encodes redirected stdout
  as cp1252, so a `→` in preflight output crashes when it is piped to a file.
- **Never name a TestCase attribute after a TestCase method.** `cls.run = run_pipeline(...)` in
  `setUpClass` shadows `TestCase.run`; every test then errors with `'Run' object is not
  callable`. Use `cls.pipeline_run`. Same for `cls.debug`, `cls.id`, `cls.skipTest`. Cost a
  whole fix turn in turn C because nothing was run before hand-off.
- **Duck-typed stubs break when production grows a new use.** Before making a function read
  more of an argument (item 7: `config.build` began iterating `reg`), grep tests for
  `SimpleNamespace` passed to it. Fix the stub (a real `Registry` via
  `test_routes.registry_with(ws(...))`), never add tolerance for impossible inputs in `ctl\`.
- **Untracked code has no git red run.** Put a fix to untracked code (the dspm adapter before its
  first commit) behind one function, so the red run can patch that function to a no-op
  (`mock.patch.object(adapter, "_check_complete", ...)`). C.3 did this.
- **Checking that each item verifies does not check that nothing is missing.** When one file is
  unhashed (`findings.json`), reconcile it against the hashed one (evidence `status_by_scope`)
  in both directions, and reject duplicates. This was Daya's F1 in turn C.
- **Why:** these came up while building dbSAT slice 1, turns A–C (2026-09-27). A reviewer caught the
  host fallback. **How to apply:** use these on every control-tool item. Related: [[buildContext]],
  [[workstationConstraints]].
