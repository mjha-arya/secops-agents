# dbSAT slice 2: review log (AgentDaya)

Slice 1's log is `dbSatSlice1Review.md`. This file starts with slice 2, one section per turn.

---

## Slice 2 / Turn A: provenance schema and loader rules V1–V10

- **Date:** 2026-09-27. **Reviewed:** Dino's hand-back `dspm\docs\buildNotes\dbSatSlice2TurnA.md`, plus
  `controlTool\ctl\registry.py` (read in full) and the provenance parts of `ctl\models.py` and `ctl\cli.py`.
  I read the test file's coverage from the build note and did not read it line by line.
- **Method:** a manual one-pass review. `/code-review` was **not** run: this is an unattended turn with the
  shell refused, so there was no `git diff`. It runs on the A.1 diff.
- **Evidence (Manish's runs):**
  - The red run against the committed `ctl` gave 42F+10E. The new tests are 41 OK.
  - Under the flag, the full suite is OK, `validate` prints `provenance: SEC 31 | SBP 0 | SAT 0` and the legacy
    line, and `run` gives 16/7/4/1/3.
  - Without the flag, `validate` **and** `fixtures\build_demo.py` fail with `SEC-01: a provenance block is
    required`.
  - I reproduced one more failure: the read-only `dct` MCP `validate` tool now dies with a raw traceback on the
    same error. So the operator tooling is broken too.

### Verdict: **changes requested, one small fix turn (A.1). Do not commit yet.**

The model and V2–V10 are right and strict in the right places. A merged-but-unratified record can't read as
ratified: `ratified()` returns False when `sources` is empty or when a source is missing. The one blocker is
the transition mechanism (A1). As built, committing it leaves the control tool's shipped registry
unloadable by `run`, `validate`, `build_demo.py` and the `dct` MCP until the item C candidate is promoted.
That's a working tool broken for a whole slice, fixed only by an env var every caller has to remember.

### Rulings

| # | Ruling |
|---|---|
| **A1** | **Not the intended transition. The contradiction was mine,** from "(tests only)" plus "stop if tests break". **Remove `CTL_ALLOW_LEGACY_PROVENANCE` entirely.** In its place, the loader detects a *wholly legacy* registry: `sources.yaml` absent, `bestPracticeRegistry.yaml` absent, and no record in the file has a `provenance` key. Only in that case does it synthesise `{sec: id}` and set `legacy_synthesised`. Anything partial is fatal: one block present, or `sources.yaml` present with a record missing its block. Why this is safe: legacy synthesis changes no status (the baseline holds at 16/7/4/1/3), and every legacy record reads `ratified: false` because `sources` is empty. So no false green is possible. The fail-closed property that V1 exists for, catching a *candidate* that dropped a block, is kept. There's also no env var that could be left set in production against a half-migrated registry. `build_demo.py`, `run`, `validate` and `dct` then work unchanged. No caller honours a flag, and none needs to. The branch is deleted in the commit after item C is promoted. Spec §2.2 V1/V8 and §6 C are amended to match |
| **A2** | **All five tightenings accepted.** Each one closes a silent-drop or a type-coercion path, and each fails closed. **One addition:** a `sections` key that isn't in `sbp` is rejected too, matching the `disagreements` rule. A stray section is a mis-keyed citation. **The ASCII `\|` separator is accepted.** The spec §2.2 now reads `\|` |
| **A3** | **Manish's decision stands: `[access, compute, query, billing]`.** I don't argue for `lakeflow`. SEC-01 is audit and telemetry coverage, and lakeflow (job/pipeline metadata) evidences no SEC-01 clause. If the SBP-11 promotion ever needs it (run_as), it's that record's detect spec, not SEC-01's. Spec §4.1 is amended to the four schemas, and the fixture goes to four enabled |
| **A4** | **The spec's path:** `controlTool\proposals\registry-<yyyymmdd>-<mode>\`. The `.gitignore` entry lands with item C |
| Nits (item B, not blocking) | `Provenance.sections`/`disagreements` are mutable `dict`s on a frozen dataclass. Wrap them in `MappingProxyType` when stamping starts serialising them. A `RegistryError` reaching the CLI prints a traceback, which is pre-existing. Catching it in `main()` → one-line message, exit 2, is worth doing in B |

### A.1 brief (Dino, before item B)

1. `registry.py`: delete `LEGACY_PROVENANCE_ENV` and the env read. Add a `_wholly_legacy(root, raw_controls)`
   predicate: no `sources.yaml`, no `bestPracticeRegistry.yaml`, and no raw record containing the key
   `provenance`. Pass its result as `legacy` into `_build_control` and `_load_sources`. Reject stray
   `sections` keys.
2. `cli.py`: change the legacy line to `legacy provenance synthesised for N record(s) (pre-slice-2 registry) -
   not a promotable registry`.
3. Tests:
   - Replace the env-flag set/clear in `test_registry_provenance.py` with fixture registries: wholly legacy
     → synthesised; legacy record plus `sources.yaml` → rejected; one block present plus one missing →
     rejected.
   - Add `test_stray_section_rejected`.
   - Add a test that the real `registry\` loads with **no** env var and gives `legacy_synthesised` = 31.
4. Done when:
   - The full control-tool suite is OK with no env var set.
   - `ctl.py validate` (no env var) exits 0 and prints `SEC 31 | SBP 0 | SAT 0` and the legacy line.
   - `ctl.py run` gives 16/7/4/1/3.
   - `python fixtures\build_demo.py` succeeds.
   - The `dspm\tests` suite is OK.
   - `grep -r CTL_ALLOW_LEGACY_PROVENANCE` over the control tool and `dspm` returns nothing.
   - `/code-review` in my review of A.1 comes back clean.
5. **Then item B** as spec §6 describes, with no change to its scope. It covers `controls --provenance`,
   `coverage`, stamping `refs`/`ratified`/`standard_versions` on findings and evidence, and the `dspm\posture`
   adapter accepting the new keys, with a `dspm\tests` fixture run carrying them. Add the two nits above.
   `build_demo.py` needs no fix of its own once A.1 lands. If B's stamping changes the fixture run shape,
   regenerate it with `build_demo.py` and record the command. The baseline stays 16/7/4/1/3.

### Control-tool commit message (for A + A.1 together, one commit; Manish commits after A.1 passes)

```
dbSAT slice 2 item A: provenance block, sources.yaml, two-file registry

Provenance(sec, sbp, sat, sections, disagreements) on every record, with
refs derived. Loader rules V1-V10 from dbSatSlice2.md section 2.2, all
fatal: provenance required, ref formats, id matches provenance, SBP/SAT ids
cited once across both files, a section per SBP (and none stray), SBP-only
records observe-only and never critical, clouds [azure], cited sources
declared in sources.yaml. bestPracticeRegistry.yaml joins one namespace.
Registry.ratified(control) is per source-document version; validate prints
the provenance counts.

Transition: a wholly pre-slice-2 registry (no sources.yaml, no
bestPracticeRegistry.yaml, no provenance key anywhere) loads with
{sec: id} synthesised and every record unratified; any partial migration is
fatal. No env flag. The branch is deleted after the item C candidate is
promoted.

Tests: tests/test_registry_provenance.py. Full suite green with no env var.
Registry untouched; fixture baseline unchanged (16/7/4/1/3).
Reviewed: AgentDaya slice 2 turn A (changes requested -> A.1), /code-review on A.1.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

```
FROM AgentDaya → TO AgentDino (dbSat slice 2, turn A.1 then B)
Artifact:   dspm\docs\specs\dbSatSlice2Review.md "Slice 2 / Turn A"; spec dbSatSlice2.md §2.2 V1/V8, §4.1 (amended)
Needed:     A.1: replace the env flag with wholly-legacy auto-detect, reject stray sections, retarget the tests.
            Then item B per spec §6 plus the two nits
Done when:  The A.1 list in the review is met with no env var; build_demo.py runs; 16/7/4/1/3
Open:       none. A3 = four schemas, A4 = spec path, for item C
```

```
FROM AgentDaya → TO Manish
Artifact:   dspm\docs\specs\dbSatSlice2Review.md; spec amendments in dbSatSlice2.md (V1/V8, §2.2 line, §4.1)
Needed:     Don't commit item A yet. Commit A + A.1 together with the message above once Dino's A.1
            passes your run. Nothing to decide: A3 applied your decision, and A1 is a spec fix of mine
Done when:  A.1 commands green with no env var; you commit the control tool; I re-review the diff with /code-review
Open:       The myAgents repo has spec/review doc changes from this turn to commit alongside
```
