# dbSAT slice 2, turn A: hand-back (AgentDino → AgentDaya)

- **Date:** 2026-09-27
- **Contract:** `dspm\docs\specs\dbSatSlice2.md` §2.1–2.2, §6 **item A**, and the spec's turn-A packet
  ("Provenance model + sources.yaml + loader/validate rules V1–V10 + two-file merge + legacy flag +
  validate provenance line"). Decisions read: `program\decisions.md` tail (Q5 severity, source docs,
  SEC-01 schemas, D-N2 deferred, three overrides accepted).
- **State:** code and tests **written, not run**. Unattended turn, shell refused. No fixture change,
  so no fixture regeneration is needed for this item.
- **Reviewed:** `feature-dev:code-reviewer` traced every new test by hand against the new code: no
  mismatches. Its one code finding (sources.yaml `cloud` unchecked) is fixed, with a test. Its other
  finding is the legacy-flag point in "Open" below. `/code-review` is still to run in your review.
- **Registry / `.env` / `proposals\`:** untouched. Nothing is written to `registry\`. No `--live`.

## Scope: what this turn built, and what it didn't

| Asked | Done? | Why |
|---|---|---|
| Item A (model, loader, V1–V10, two files, legacy flag, validate line) | **Yes** | The spec's turn-A packet |
| Item B (`coverage`, `controls --provenance`, stamping, adapter keys) | **No** | The spec's packet names item A only for turn A: "Items B–E follow in order." B is next turn |
| O23 (SEC-01 target) / O15 (SEC-16 curated scope) | **No** | Spec §4 and §6 put both in **item C**, produced by `importSbp.py --mode sec` together with collector code. A hand-written candidate would contradict "the script writes one candidate directory" and "nothing is hand-typed into registry YAML". So no `proposals\` directory was written this turn |

## What changed (control tool)

| File | Change |
|---|---|
| `ctl\models.py` | New frozen `Provenance(sec, sbp, sat, sections, disagreements)` with `refs` and `cited_sources()`. `Control` gains `provenance`, `clouds` (default `("azure",)`) and a derived `refs` |
| `ctl\registry.py` | `Source` dataclass. `Registry.sources`, `Registry.legacy_synthesised`, `Registry.ratified(control)`. `_provenance` (V1–V3, V5), `_clouds` (V7), and the V6 check at the end of `_build_control`, placed after the older checks so the existing `_build_control` tests still fail for their own reason. `load()` merges `bestPracticeRegistry.yaml` (V9) and checks V4 (SBP/SAT cited once, across files) and V8 (`sources.yaml`) |
| `ctl\cli.py` | `provenance_line()`. `validate` prints it, plus a legacy-flag line when records were synthesised. `_promote` now uses `dataclasses.replace`, so a promoted registry keeps `sources` |
| `tests\test_registry_provenance.py` (new) | 41 tests covering every spec-named test (V1–V10) and the tightenings below. Each test sets or clears the flag itself |

**Tightenings beyond the spec's wording** (each one fatal, each one tested; your call to keep them):
1. Unknown keys in `provenance` are rejected. A misspelt `sbps:` would otherwise drop citations silently.
2. `sections` and `disagreements` values must be quoted strings. Unquoted `1.10` is the float `1.1`, which
   would turn §1.10 into §1.1.
3. `sources.yaml` checks: `title`/`version` must be strings, `ratified` must be a real boolean (the string
   `"false"` is truthy), and `cloud` must be `azure` (V7 applied per document).
4. A `bestPracticeRegistry.yaml` that is present but declares no controls is rejected, the same as
   `controlRegistry.yaml`.
5. An SBP id listed twice inside one record is rejected (V4 "exactly once").

**Deviation:** the validate line is `provenance: SEC n | SBP n | SAT n | merged n | SBP-only n`, with ASCII
`|` in place of the spec's `·`. The rest of `validate` output is ASCII, and my memory records a cp1252 crash
from non-ASCII CLI output. If you want `·`, it's a one-character change plus the test.

## Commands for Manish (Git Bash; expected results)

```bash
PY="$USERPROFILE/.venvs/agentDino/Scripts/python.exe"
CT="<repo-root>"
MY="<repo-root>"
cd "$CT"

# 0. Red run: the new tests against the committed ctl\ (the test file is untracked, so it stays)
git stash push -- ctl
"$PY" -m unittest tests.test_registry_provenance 2>&1 | tail -3
git stash pop
#    expect: FAILED, with nearly all 41 failing or erroring. Only test_best_practice_file_is_optional,
#    test_policy_record_may_still_be_critical and the V6 "high/medium/low load" test can pass on old code.
#    Record the counts.

# 1. The new tests
"$PY" -m unittest tests.test_registry_provenance -v          # expect: Ran 41 tests ... OK

# 2. Whole control tool: under the legacy flag (spec item A "done when")
export CTL_ALLOW_LEGACY_PROVENANCE=1
"$PY" -m unittest discover -s tests -v    # expect: previous count + 41, OK
"$PY" ctl.py validate                     # expect: exit 0, "registry is internally consistent",
                                          #   "provenance: SEC 31 | SBP 0 | SAT 0 | merged 0 | SBP-only 0",
                                          #   "legacy provenance synthesised for 31 record(s) ..."
"$PY" ctl.py run                          # expect: IN PLACE 16 / GAP 7 / BLOCKED 4 / MANUAL 1 / COULD NOT CHECK 3
#    If the row is not 16/7/4/1/3: STOP and report it (do not tune anything).

# 3. dspm adapter (still under the flag: it loads registry\)
cd "$MY"
CTL_ROOT="$CT" "$PY" -m unittest discover -s dspm/tests -v   # expect: same count as turn C.3, OK
unset CTL_ALLOW_LEGACY_PROVENANCE

# 4. Without the flag (the V1 check itself)
cd "$CT"
"$PY" ctl.py validate    # expect: RegistryError "SEC-01: a provenance block is required", non-zero exit
```

## Open for Daya

| # | Item |
|---|---|
| A1 | **The spec contradicts itself on the flag.** V1/V8 make every load of today's `registry\` fail without `CTL_ALLOW_LEGACY_PROVENANCE=1` (no provenance blocks, no `sources.yaml`). But the turn-A packet says "If any existing test breaks without the legacy flag, stop and report." Every existing test that loads `registry\` (test_assess, test_auth_config, test_false_green, test_http_backend, test_preflight, test_routes, test_safety, and dspm test_postureAdapter) **will** error without the flag, by V1's design, until the item C candidate is promoted. I built to the V1–V8 table and item A's "done when" (suite green *under* the flag), and I'm reporting the breakage as you asked. Also note that `ctl.py run`/`validate` on the shipped registry now need the flag too. That goes beyond "tests only" until promotion. Rule: keep this, or have the tests set the flag themselves? |
| A2 | Confirm the five tightenings and the ASCII separator above |
| A3 | **M3 list mismatch for item C.** Spec §4.1 `expect.required` is `[access, compute, billing, lakeflow, query]`. Manish's decision (2026-09-27) is `system.access, compute, query, billing`, which has no `lakeflow`. Item C will build the decision's four unless you amend §4.1 |
| A4 | **Candidate path for item C.** Spec §1 says `controlTool\proposals\registry-<yyyymmdd>-<mode>\`. This turn's brief said `proposals\<date>-slice2\`. I'll follow the spec unless you change it. Adding `proposals/` to `.gitignore` also waits for item C |
| A5 | Commit: one control-tool commit for item A (message below). The control tool is its own repo |

## Proposed commit (control tool repo; Manish commits)

```
dbSAT slice 2 item A: provenance block, sources.yaml, two-file registry

Provenance(sec, sbp, sat, sections, disagreements) on every record, with
refs derived. Loader rules V1-V10 from dbSatSlice2.md section 2.2, all fatal:
provenance required (CTL_ALLOW_LEGACY_PROVENANCE=1 synthesises {sec: id}
until the item C candidate is promoted), ref formats, id matches provenance,
SBP/SAT ids cited once across both files, a section per SBP, SBP-only
records observe-only and never critical, clouds [azure], cited sources
declared in sources.yaml. bestPracticeRegistry.yaml joins one namespace.
Registry.ratified(control) is per source-document version. `validate`
prints the provenance counts.

Tests: tests/test_registry_provenance.py (41). Existing suite runs under
the legacy flag. Registry untouched; fixture baseline unchanged (16/7/4/1/3).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

```
FROM AgentDino → TO AgentDaya
Artifact:   dspm\docs\buildNotes\dbSatSlice2TurnA.md; controlTool ctl\models.py, ctl\registry.py,
            ctl\cli.py, tests\test_registry_provenance.py (uncommitted)
Needed:     Review gate for slice 2 item A, plus rulings on A1 (legacy flag vs "stop if tests
            break without it"), A2 (tightenings, ASCII line), A3 (SEC-01 schema list), A4
            (candidate path)
Done when:  Manish's commands 0-4 give the expected results (41 new tests OK; suite OK under the
            flag; run = 16/7/4/1/3); /code-review is clean; A1-A4 are answered
Open:       Items B-E not started. O23/O15 are item C (script-generated candidate), so no
            proposals\ directory was written this turn
```
