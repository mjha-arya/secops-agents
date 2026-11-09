---
name: falseGreenSources
description: Known ways the control tool/dbSAT can report compliant when it could not actually see — check for these in every review of a collector or assertion
metadata:
  type: project
---

Found 2026-09-27 while writing ADR-0002 / `dspm\docs\architecture.md` § 6–7.

1. **UC `information_schema` is privilege-filtered.** A non-metastore-admin gets *fewer rows*, not
   an error. Any assertion concluding from absence of rows (`_grant_hygiene`, storage credentials,
   tag coverage) turns partial visibility into `compliant`. Fix designed: preflight visibility
   guard → `unknown (insufficient-visibility)`.
2. **`dbutils.fs.mounts` placeholder** in `ctl\collectors\base.SQL_STATEMENTS` returns
   `'/databricks-datasets'`, which `_mounts` filters out, so SEC-15 mounts reads `compliant: True`
   on a live run. Must raise `NotCollected` until a real method exists. Blocking for `--live`.

3. **workspace-conf `null` = unset = platform default.** `_exfil_toggles` stringifies `None` to
   `"None"` ≠ `"true"` → compliant, but results-download/export default to *enabled*. Only an
   explicit `"false"` is closed; `null` → `unknown`. Applies to every workspace-conf read.
4. **Truncated lists.** A paginated list read without following `next_page_token` hides the bad
   item on page 2. Any "no offender in list" assertion needs full pagination or `unknown`.
5. **Half the evidence.** NCC responses carry private-endpoint rules but not egress restriction;
   an assertion must not go green on the half it can see.
6. **No API ≠ route it anyway.** AIM identity-sourcing state had no documented read API
   (2026-09-27) → `NOT_COLLECTABLE`, and its fixture entry deleted (fixtures only hold what a live
   read can produce).
Fixes are specced in `dspm\docs\specs\dbSatSlice1.md` items 1, 2, 3a–3d (accepted 2026-09-27).

Found in the turn-A review (2026-09-27), specced as items 10–14:
7. **Fixture-shaped assertions: the biggest class.** Assertions read keys that only the fixture has
   (`lifetime_days`, `_iac_declared`, `allowlisted`, `via_ai_gateway`), using `.get(k, <passing
   default>)`. The fixture is green and live is green without any evidence. Tests can't catch this,
   because the fixture was built to match the assertion. Ask: "is every key this reads in the
   *documented* response or the SELECT list?"
8. **SQL results:** only the first chunk is read, `truncated` is ignored, `JSON_ARRAY` values are
   all strings (`"false"` is truthy), and `LIMIT n` feeds absence checks. An aggregate like
   `count(*) > 0 … GROUP BY` can only ever see the positive rows.
9. **`build_demo.py` fallback `{"compliant": True}`**: a new control is green in CI by default.

Found in the turn-C review (2026-09-27), F1:
10. **Omission, in consumers.** A reader that checks every record it is *given* (hash, status,
    scope) but never checks that it was given *all* of them publishes a smaller run that still
    verifies. The bucket counts still add up, because they come from the same unhashed file.
    Every reader of `findings.json` must reconcile it against the hashed `evidence\*.json`
    scopes. Ask: "if a row vanished, would anything notice?"

**Recurring review pattern:** `silent-failure-hunter` finds these, and Dino's own pass didn't. Run it
over the *assertion functions*, not only the diff.

**Why:** a false green is the DSPM's worst defect. Neither of these shows up in fixture runs.
**How to apply:** in every review, ask "can this assertion return compliant from an empty or
filtered read?" A `compliant` that derives from absence needs a proven-visibility precondition.
Related: [[controlToolState]].
