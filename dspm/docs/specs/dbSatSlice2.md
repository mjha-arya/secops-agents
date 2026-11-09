# dbSAT slice 2: one registry, two provenances

Status: **Proposed** (Daya, 2026-09-27). Epic dbSat, roadmap D2 (dbSat-2.1 to 2.6), PRD stories S1, S2, S9.
Layer 4 (posture). Builds on `dspm\docs\architecture.md` §4. Where this spec differs from §4, this spec wins
(the deltas are listed in §2.4).

Inputs read: `program\prd\dbSat.md` S1/S2, `program\roadmap.md` WS2, `program\decisions.md` O15/O23,
`controlTool\ctl\registry.py`, `ctl\models.py`, `ctl\cli.py` (`cmd_validate`, `cmd_controls`),
`ctl\collectors\*` prefixes, `registry\controlRegistry.yaml` (31 records, v0.5.0),
`databricksSecurityAnnex.md` Appendix B.

**Fixture baseline today:** 16 compliant · 7 deviation · 4 prerequisite-gap · 1 procedural · 3 unknown
(31 records, per `buildNotes\dbSatSlice1TurnC.md`). The PRD S1 criterion still says 16/8/4/1/2. That's stale,
and Nolan should fix it.

---

## 1. Where the merged registry lives

**Decision: extend the control tool's registry. No dspm-owned registry.** The registry is the contract
(blueprint layer 4). A dspm copy would give us two contracts that drift apart. `dspm\posture` keeps reading
run artifacts through the adapter, and it never loads YAML.

| File (all in `controlTool\registry\`) | Holds | Who writes it |
|---|---|---|
| `controlRegistry.yaml` | 31 SEC records. Each gains a `provenance:` block. SEC records that absorb an SBP list it there | **Manish commits.** Generated candidate only |
| `bestPracticeRegistry.yaml` (new, optional) | SBP-only records, `id: SBP-nn` | **Manish commits.** Generated candidate only |
| `sources.yaml` (new) | The documents a ref may cite: title, version, ratified, cloud | Manish |
| `satChecks.yaml` (new, optional) | The SAT check-id universe (ids only, pinned SAT version) plus `not-applicable-azure` reasons | Manish supplies the list (see M2) |

**How Dino's output reaches Manish.** No agent writes into `registry\`. The import script writes one
**candidate directory**, and Manish promotes it by hand:

```
controlTool\proposals\registry-<yyyymmdd>-<mode>\
  controlRegistry.yaml        full candidate; original bytes plus inserted lines only
  bestPracticeRegistry.yaml   (mode=sbp only)
  sources.yaml, exceptionRegister.yaml, workspaceInventory.yaml   byte-identical copies (except sources.yaml when new)
  registry.diff               unified diff against registry\ as it stands
  importNote.md               counts, merges, overrides, disagreements, defaulted severities, annex defects
```

- Manish runs `ctl.py --registry proposals\registry-… validate`, then the fixture run, then reads
  `registry.diff` and `importNote.md`. If it's accepted, **he** copies the files into `registry\` and commits.
- The script refuses to write if the output path resolves inside `registry\`. That refusal is tested.
- Add `controlTool\proposals\` to `.gitignore`. Candidates are review material, not history. The commit
  that promotes a candidate carries the history.

## 2. Record schema extension

### 2.1 Shape

```yaml
# sources.yaml
sources:
  SEC: {title: "Databricks Security Policy", version: "0.5", ratified: false, cloud: azure}
  SBP: {title: "Security Best Practices for Azure Databricks", version: "2.3", ratified: false, cloud: azure}
  SAT: {title: "Security Analysis Tool check catalogue", version: "TODO (M2)", ratified: false, cloud: azure}

# on every record, in either file
    provenance:
      sec: SEC-06                  # ^SEC-\d{2}$ or null
      sbp: [SBP-07, SBP-08]        # ^SBP-\d{2}$, may be []
      sat: []                      # SAT check ids, ids only; may be []
      sections: {SBP-07: "1.7", SBP-08: "1.8"}          # annex/vendor section per SBP ref
      disagreements: {SBP-08: "<one line, SEC value wins>"}   # optional
    clouds: [azure]                # optional; default [azure]
```

Model (`ctl\models.py`): a new frozen `Provenance(sec: str | None, sbp: tuple[str, ...], sat: tuple[str, ...],
sections: Mapping[str, str], disagreements: Mapping[str, str])`. `Control` gains `provenance: Provenance`
and `clouds: tuple[str, ...]`. It also gains derived `refs` = `(sec,) + sbp` with no nulls. PRD S1 talks about
"refs", and this is that. `Registry` gains `sources`, plus `ratified(control) -> bool`, which is true only if
every source the record cites is `ratified: true`.

### 2.2 Validate / loader rules

All of these live in `registry.load()` and raise `RegistryError` naming the record id. They are fatal and
never degrade.

| # | Rule | Test name (in `tests\test_registry_provenance.py`) |
|---|---|---|
| V1 | `provenance` is required on every record. **Transition (amended 2026-09-27, review ruling A1):** there's no env flag. The loader detects a **wholly legacy** registry: `sources.yaml` absent, `bestPracticeRegistry.yaml` absent, and no record has a `provenance` key. Only then does it synthesise `{sec: id}` for `SEC-nn` ids and set `legacy_synthesised`. If only part of the registry is legacy, loading fails. The branch is deleted in the commit after the item C candidate is promoted | `test_missing_provenance_rejected` (mixed registry), `test_legacy_registry_synthesises_sec` (wholly legacy), `test_partial_legacy_rejected` |
| V2 | `sec` is null or matches `^SEC-\d{2}$`. Every `sbp` matches `^SBP-\d{2}$`. At least one of `sec` or `sbp` is non-empty | `test_empty_provenance_rejected`, `test_bad_ref_format_rejected` |
| V3 | Identity: if `sec` is set, `id == sec`. If not, `sbp` has exactly one entry and `id == sbp[0]` | `test_id_must_match_provenance` |
| V4 | An SBP id is cited by **exactly one** record across both files. The same goes for a SAT id | `test_duplicate_sbp_across_files_rejected`, `test_duplicate_sat_rejected` |
| V5 | Every `sbp` entry has a `sections` entry. `disagreements` keys are a subset of `sbp` | `test_sections_required_per_sbp` |
| V6 | SBP-only records (`sec: null`) have `enforcement: observe` and a severity in {high, medium, low}. Vendor input never yields `critical` (M1) | `test_sbp_only_must_observe`, `test_sbp_only_not_critical` |
| V7 | `clouds == [azure]`. Anything else is rejected in v1 | `test_non_azure_cloud_rejected` |
| V8 | Every cited prefix (SEC/SBP/SAT) exists in `sources.yaml`. If `sources.yaml` is missing, loading fails, unless the registry is wholly legacy (V1) | `test_unknown_source_rejected` |
| V9 | `bestPracticeRegistry.yaml` is optional. If present, its records join one namespace. A duplicate `id` across files is rejected. Exceptions and `excludes` may cite SBP ids | `test_two_files_merge`, `test_duplicate_id_across_files_rejected` |
| V10 | Existing behaviour holds: manual-only detect means `is_procedural`, which is never `compliant`. The test is extended to an SBP-only manual record | `test_sbp_manual_is_procedural` |
| V11 | A merged record's `desired` is untouched by import. The SEC value stands | covered by the import tests (§3) |

Two more changes. `cmd_validate` prints a provenance line (`SEC n | SBP n | SAT n | merged n | SBP-only n`,
with ASCII separators because CLI output must survive cp1252; ruling A2).
Every finding and evidence file carries `refs`, `ratified` and `standard_versions`
(`{registry: "0.5.0", SEC: "0.5", SBP: "2.3"}`), as PRD line 103 requires. The `dspm\posture` adapter must
accept the new keys, and a test in `dspm\tests` loads a fixture run that has them.

### 2.3 Severity mapping (proposal; M1 decides, Q5)

| Source | Rule |
|---|---|
| Merged record | SEC severity wins. The vendor severity goes in `importNote.md` only if it differs |
| SBP-only record with a SAT check | SAT High→`high`, Medium→`medium`, Low→`low` |
| SBP-only record with no SAT severity | `medium`. Every defaulted record is listed in `importNote.md` under "severity defaulted" |
| Never | `critical` from vendor input. Only the policy assigns critical |

### 2.4 Deltas from architecture.md §4

- `refs` + a per-ref `provenance` list becomes one `provenance {sec, sbp, sat, sections, disagreements}`
  block, with `refs` derived. There's one place to cite and no count to keep in step.
- Ratification is per **source document version** (`sources.yaml`), not per ref. The dashboard's
  "draft standard" banner reads `Registry.ratified(control)`.
- `sat_checks` on the record plus `dspm\knowledge\satCoverage.yaml` becomes `provenance.sat` as the only
  mapping. `satChecks.yaml` holds just the universe, so two files can't disagree.
- SBP-nn numbering: architecture's `SBP-12 = PAT` example is illustrative and wrong. §3.1 fixes the rule.

## 3. The SBP import

### 3.1 Source and numbering

- **Input:** the Appendix B tables of `secopsCurrentProjects\databricks\databricksSecurityAnnex.md`,
  parsed from the markdown. This is the in-repo cross-reference until Q7/M2 gives the vendor document a
  location. Nothing is hand-typed into registry YAML.
- **SBP-nn is the ordinal in Appendix B order:** 1.1–1.14 → SBP-01..14 · 2.1–2.15 → SBP-15..29 ·
  3.1–3.12 → SBP-30..41 · 4.1–4.12 → SBP-42..53 · 5.1–5.15 → SBP-54..68. The section number is kept in
  `provenance.sections`.
- **Mapping rule:** a row whose Reference column cites exactly one `SEC-\d{2}` is merged into that SEC record.
  Rows with no SEC ref become an SBP-only record. A row with more than one SEC ref, or with a Position of P
  that still cites a SEC, **fails the import** unless `controlTool\tools\sbpImportOverrides.yaml` names the
  target. That file is knowledge (P9), and three entries ship with it (below).
- **Annex defect (goes into the import note, and the test pins the real rows):** the Summary table says
  P 27 · A 22 · B 9 · deviation 1 · unclaimed 9. The rows say **P 25 · A 26 · B 9 · deviation 1 · unclaimed 7**,
  and the "nine unclaimed" sentence lists seven. The script counts rows and never trusts the summary.

### 3.2 Merged into existing SEC records: 36 SBPs, 22 SEC records

| SEC | SBP (annex §) |
|---|---|
| SEC-01 | SBP-54 (5.1, **override**: cites SEC-01 + SEC-04, goes to SEC-01), SBP-55 (5.2) |
| SEC-02 | SBP-56 (5.3) |
| SEC-05 | SBP-05 (1.5) |
| SEC-06 | SBP-07 (1.7), SBP-08 (1.8) |
| SEC-07 | SBP-03 (1.3), SBP-04 (1.4) |
| SEC-08 | SBP-02 (1.2, **override**: Position P, reference "see SEC-08") |
| SEC-10 | SBP-13 (1.13, **override**: cites SEC-09 to SEC-13, goes to SEC-10, the Databricks secret mechanism. The others are listed as related) |
| SEC-14 | SBP-16 (2.2) |
| SEC-15 | SBP-18 (2.4) |
| SEC-16 | SBP-27 (2.13, disagreement: vendor asks for AES at rest, SEC-16 checks classification), SBP-45 (4.4), SBP-53 (4.12) |
| SEC-17 | SBP-47 (4.6) |
| SEC-18 | SBP-28 (2.14) |
| SEC-19 | SBP-49 (4.8) |
| SEC-20 | SBP-48 (4.7). One-way door, and nothing changes |
| SEC-21 | SBP-10 (1.10), SBP-12 (1.12) |
| SEC-22 | SBP-42 (4.1) |
| SEC-23 | SBP-33 (3.4), SBP-36 (3.7), SBP-38 (3.9), SBP-39 (3.10), SBP-40 (3.11) |
| SEC-24 | SBP-32 (3.3) |
| SEC-25 | SBP-61 (5.8) |
| SEC-26 | SBP-62 (5.9) |
| SEC-27 | SBP-37 (3.8), SBP-58 (5.5) |
| SEC-28 | SBP-65 (5.12) |
| SEC-29 | SBP-25 (2.11), SBP-26 (2.12) |
| SEC-31 | SBP-68 (5.15) |

These SEC records get no SBP: SEC-03, 04, 09, 11, 12, 13 and 30. That's expected, because they are policy
additions. Merging changes no `desired` and no detect spec, so their assessments can't move.

### 3.3 New SBP-only records: 32

**No new record can be served today with zero collector code.** Every existing target and assertion answers a
SEC question, and reusing one for a different vendor question is a false-green source. SEC-31's
`consumption/budgets` (Azure budgets) is not SBP 5.14 (Databricks account budgets). So **all 32 import at
`modality: manual` and assess `procedural`.** The table names the collector and target that could serve
each one later ("promotion", §6 backlog). "Routes today" means the target falls under an existing collector
prefix, so `validate` routing passes and only an assertion (plus a `ROUTES` entry) is missing.

| SBP (§) | Practice | Promotion path | Routes today? |
|---|---|---|---|
| SBP-19 (2.5) | Storage firewalls | `AzureCollector` · `storage-accounts/networkAcls` | yes. The owner is CloudOps (annex: landing-zone) |
| SBP-20 (2.6) | No anonymous read | `AzureCollector` · `storage-accounts/allowBlobPublicAccess` | yes (CloudOps) |
| SBP-21 (2.7) | Soft delete | `AzureCollector` · `storage-accounts/blobServices/deleteRetentionPolicy` | yes |
| SBP-22 (2.8) | Backup storage | `AzureCollector` · `storage-accounts/blobServices/versioning` (plus manual for vault backup) | yes, partial |
| SBP-15 (2.1) | Centralise on UC | `AccountCollector` · `metastore/assignment` (every governed workspace has a metastore) | yes |
| SBP-46 (4.5), SBP-66 (5.13) | Tags / cost tags | `UnityCatalogCollector` · `system.compute.clusters` custom_tags | yes |
| SBP-44 (4.3) | Catalog-workspace binding | workspace plane, `unity-catalog/bindings/` | no, it needs a prefix |
| SBP-09 (1.9) | Restrict cluster creation | workspace plane, `scim/entitlements` | no |
| SBP-11 (1.11) | SPs for admin/prod | `system.lakeflow.jobs` run_as (`UnityCatalogCollector`) | yes, if the table exists live |
| SBP-57 (5.4) | Git folders | `workspace-conf/` key (to be confirmed live) | yes, if a key exists |
| SBP-23, 24 (2.9, 2.10) | CMK services / storage | ARM `databricks-workspaces/encryption` | no. Also an open tier decision |
| SBP-30, 31 (3.1, 3.2) | No Public IP / VNet injection | ARM `databricks-workspaces/parameters` | no |
| SBP-41 (3.12) | Intra-VNet NSG rules | ARM `network-security-groups/` | no |
| SBP-59, 60, 63 (5.6, 5.7, 5.10) | IaC, CI/CD, DevSecOps | `DevOpsCollector` · `devops/pipelines` | yes, but the judgement is weak. Stays manual |
| SBP-01 (1.1) | MFA | `EntraCollector` · `entra/conditionalAccess/policies` | yes. Tenant-wide, outside Databricks scope |
| SBP-06 (1.6), 17 (2.3), 43 (4.2), 50 (4.9), 52 (4.11), 64 (5.11), 67 (5.14) | Least privilege, isolation model, isolate workloads, DR, ABAC, DQ monitoring, account budgets | manual (design or process evidence) | n/a |
| SBP-34 (3.5) | Network exfiltration (Azure Firewall) | manual. Firewall is its own workstream | n/a |
| SBP-14 (1.14), 29 (2.15), 51 (4.10) | Databricks One, Clean Rooms, Confidential Compute | manual, note "not claimed: no use case" | n/a |
| SBP-35 (3.6) | Isolate workspace networks | manual, note "**documented deviation**, annex §8". The import note drafts an exception entry for Manish. The script never writes it | n/a |

Every SBP-only record gets: `enforcement: observe`, `implement: {method: manual}`, `clouds: [azure]`, severity
per §2.3, `notes` = the annex position and reference, and `planes` taken from the promotion path's collector
(`azure`, `databricks-workspace` and so on), or `[]` for pure manual. `domain` is the Appendix B heading.

### 3.4 The script

`controlTool\tools\importSbp.py` has two modes and is deterministic (two runs produce byte-identical output):

- `--mode sec`: insert `provenance: {sec: SEC-nn, sbp: [], sat: []}` into all 31 records, and write `sources.yaml`.
- `--mode sbp`: `sec` mode, plus the §3.2 merges plus `bestPracticeRegistry.yaml` (§3.3).

**Format-preserving (P8):** `controlRegistry.yaml` is edited by line insertion after each record's
`severity:` line, anchored on `  - id: SEC-nn`. It is never `yaml.dump`-ed, because a dump would destroy the
comments. Test: every line of `registry.diff` for `controlRegistry.yaml` starts with `+`. The script also
re-loads its own candidate through `registry.load()` and exits non-zero if the candidate fails validation.

Fixture: `tests\fixtures\annexAppendixB.md` has 10 rows, one per case: single-SEC A, B, P with no SEC,
P citing SEC (override), multi-SEC (override), multi-SEC with **no** override (must fail), deviation,
unclaimed, a malformed row (must fail), and a duplicate § (must fail). A second test parses the **real** annex
and asserts 68 rows, the counts 25/26/9/1/7, the counts 36 merged and 32 new, and that SBP-01..68 are each
cited once.

## 4. O23 and O15 as concrete records

### 4.1 O23: SEC-01 target (goes in `--mode sec`, as the one detect change in it)

The candidate replaces the third SEC-01 detect spec (`SELECT 1 FROM system.access.audit LIMIT 1`) with:

```yaml
      - modality: api-read
        target: metastore/systemschemas          # AccountCollector ("metastore/" prefix)
        scope: per-metastore
        assertion: required-system-schemas-enabled
        expect: {required: [access, compute, query, billing]}   # M3, Manish 2026-09-27 (ruling A3)
```

- The `ROUTES` entry becomes `api/2.1/unity-catalog/metastores/{metastore_id}/systemschemas` (workspace host,
  following the slice-1 host-selection rule).
- Assertion: every required schema has `state == "ENABLE_COMPLETED"`. A required schema that's missing from
  the response counts as `deviation`. An empty `schemas` list, or a non-200 response, raises
  `IncompleteObservation`, which gives `unknown`.
- Tests: all enabled → compliant. One `DISABLE` → deviation. `schemas: []` → unknown. Missing key → unknown.
  Pagination token present → unknown (until paging is proven live).
- The fixture adds `metastore_systemschemas.json` with all four enabled. **SEC-01 stays compliant, and the
  baseline doesn't move.** If the fixture file is missing, SEC-01 goes to unknown (15/7/4/1/4). That means
  the item isn't done.

### 4.2 O15: SEC-16 curated scope (collector code, no registry shape change)

Add `scope_rule: curated` to SEC-16's `system.information_schema.column_tags` spec `expect`. The candidate
carries it in `--mode sec`. The `UnityCatalogCollector` resolves the curated schemas **before** judging:

1. First, schemas with tag `layer = curated`, from `system.information_schema.schema_tags`.
2. If **zero** schemas carry the `layer` tag anywhere in the metastore, fall back to schema names ending in
   `_curated` or `_gold`, and record `scope_method: name-suffix` in evidence.
3. If both are empty, raise `IncompleteObservation`, giving `unknown`. **An empty scope is not compliance.**
4. If any schema carries `layer` (even with a different value), there's no fallback. Tags are authoritative
   once they exist.

Then apply the existing rule to tables in the scope only. Evidence records `scope_method`, the schema list
and the table count.

Tests cover each of the four branches, plus: a truncated or failed `schema_tags` read → unknown (not a
fallback to suffix). Fixture: add one `layer=curated` schema containing an unclassified column, and one
`sales_gold` schema. The tag wins, so the gold schema is ignored. **SEC-16 stays deviation, and the baseline
doesn't move.**

## 5. Coverage command

`ctl.py coverage [--require-complete]` lives in `ctl\cli.py`, because the control tool owns the registry.
It prints counts and never a percentage:

```
dbSAT coverage — registry 0.5.x · SBP 2.3 (draft) · SAT <version|not loaded>
SBP   68 cited: merged 36 · own record 32 · uncited 0
      by detection: automated 36 · procedural 32
SAT   mapped-automated N · mapped-procedural N · not-applicable-azure N · gap N
      (satChecks.yaml missing → "SAT unknown: universe not loaded", exit 2)
```

- "Automated" means at least one non-manual detect spec. "Procedural" means manual only.
- `--require-complete` exits 1 if any SBP-01..68 is uncited (checked against the `sources.SBP` count,
  `configurations: 68`), or if any SAT id is in `gap`.
- Also: `ctl.py controls --provenance SEC|SBP|SAT` (dbSat-2.3). A record matches if it cites that source.
  A merged record appears under both SEC and SBP (PRD S1).
- Tests: synthetic registry plus a synthetic `satChecks.yaml` (ids `T-1`..`T-4`). There's one test per
  bucket, one for the missing universe giving exit 2, and a stdout test asserting no `%` character.

## 6. Build items (one Dino turn each, tests first)

Dino's write scope for these is `controlTool\ctl\`, `controlTool\tools\`, `controlTool\tests\`,
`controlTool\fixtures\` and `dspm\` (Q10). **Never `controlTool\registry\`.**

| # | Item | Tests first | Done when | Predicted fixture baseline |
|---|---|---|---|---|
| **A** | Model + loader + validate: `Provenance`, `sources.yaml`, V1–V10, two-file merge, legacy flag, validate provenance line | `test_registry_provenance.py` (V1–V10) | All pass. Existing suite passes under the legacy flag | **16/7/4/1/3**, because no record's detect or desired changes |
| **B** | `controls --provenance`, `coverage`, finding/evidence stamping (`refs`, `ratified`, `standard_versions`), and the adapter accepting the new keys | `test_coverage.py`, a stamping test, `dspm\tests` adapter test | §5 output is correct on synthetic input | **16/7/4/1/3**. Stamping adds keys and changes no status |
| **C** | `importSbp.py --mode sec`, including O23 (§4.1) and O15 (§4.2) collector code and fixtures | `test_import_sbp.py` (sec cases), SEC-01 and SEC-16 branch tests | The candidate validates. The diff is insert-only apart from the SEC-01 detect swap. **Manish promotes it; after that the V1 legacy branch is deleted** | **16/7/4/1/3**: SEC-01 stays compliant on the new target, and SEC-16 stays deviation on the curated scope. If either fixture is missing: 15/7/4/1/4 |
| **D** | `importSbp.py --mode sbp`, overrides, and the import note. **Code and tests may land now. The candidate is generated only after the D1 gate** (decision 2026-09-27, line 14) | `test_import_sbp.py` (10-row fixture plus real-annex test) | The candidate validates. `coverage --require-complete` passes the SBP half | **16/7/4/33/3** over 63 records: 32 new manual records are procedural, and the 36 merges change nothing |
| **E** | Turn-D carry-over: D-N1 (below) | 1 adapter test | as below | 16/7/4/1/3 |

Commands (Manish runs them, with the venv outside OneDrive):

```
cd "<repo-root>"
%USERPROFILE%\.venvs\agentDino\Scripts\python -m unittest discover -s tests -v
%USERPROFILE%\.venvs\agentDino\Scripts\python ctl.py validate
%USERPROFILE%\.venvs\agentDino\Scripts\python ctl.py run            # fixture; prints the five buckets
%USERPROFILE%\.venvs\agentDino\Scripts\python tools\importSbp.py --mode sec --out proposals\registry-<yyyymmdd>-sec
%USERPROFILE%\.venvs\agentDino\Scripts\python ctl.py --registry proposals\registry-<yyyymmdd>-sec validate
%USERPROFILE%\.venvs\agentDino\Scripts\python ctl.py --registry proposals\registry-<yyyymmdd>-sec run
%USERPROFILE%\.venvs\agentDino\Scripts\python ctl.py coverage
cd ..\..\..\myAgents && %USERPROFILE%\.venvs\agentDino\Scripts\python -m unittest discover -s dspm\tests -v
```

**Definition of done (slice 2):** A to E are reviewed clean (`/code-review`, plus `silent-failure-hunter` on
C and D); the sec candidate has been promoted by Manish; the sbp candidate has been promoted after the D1
gate; `coverage --require-complete` passes the SBP half; the SAT half has a universe loaded (M2) or reports
`unknown`, never `0 gap`; slice 1 has been re-run live on the merged registry (Manish); and the `dspm\readme.md`
status row is updated.

## 7. Carried items (so nothing is lost)

| Id | Item | Where it goes |
|---|---|---|
| D-N1 | `dspm\posture\adapter.py:149-150` matches evidence by `path.stem`, so `SEC-06.bak` or a `SEC-06\` folder is skipped silently. Fix: accept only `is_file()` with a `.json` suffix; anything else is stray and rejects the run. One test | Item E (Dino) |
| D-N2 | The evidence sha256 proves integrity, not authenticity. Anyone who edits findings.json and evidence together, then re-hashes, still passes. Options: (a) accept that as the limit; (b) a signed run manifest (key custody is needs_human) | **M4, Manish decides.** No patch until then |
| O2 | `ABSENCE_BASED_TARGETS` / `NOT_COLLECTABLE` → per-spec `visibility:` / `collectable:` registry fields | Daya proposal, next turn. Rides on the item C candidate if it's ready |
| O3 | SEC-23 network-policies detect spec | Daya proposal. Slice 2 candidate, second pass |
| O17 / O20 | Filter audit SQL by `workspace_id`, and metastore by `metastore_id` | Spec addendum after run #1 |
| O22 / O24 | SEC-24 IaC path; audit/query-history filters pushed into SQL | Sized from live run #1 |
| O21 | Roll-up ranking | Manish (open) |
| PRD | S1 baseline text is stale (16/8/4/1/2 → 16/7/4/1/3) | Nolan |

---

```
FROM AgentDaya → TO AgentDino (dbSat slice 2, turn A)
Artifact:   dspm\docs\specs\dbSatSlice2.md §2, §6 item A
Needed:     Provenance model + sources.yaml + loader/validate rules V1–V10 + two-file merge +
            legacy flag + validate provenance line, in controlTool\ctl\. No registry\ edits.
Done when:  tests\test_registry_provenance.py (V1–V10) written first and passing; full controlTool
            suite green under CTL_ALLOW_LEGACY_PROVENANCE=1; fixture run still 16/7/4/1/3;
            build note in dspm\docs\buildNotes\dbSatSlice2TurnA.md with the exact commands run.
Open:       If any existing test breaks without the legacy flag, stop and report — don't edit
            registry\ to fix it. Items B–E follow in order; D's candidate waits for the D1 gate.
```

```
FROM AgentDaya → TO Manish
Artifact:   dspm\docs\specs\dbSatSlice2.md
Needed:     M1 severity mapping (§2.3; Q5): vendor High/Med/Low → high/medium/low, no vendor
            critical, default medium. M2 (Q7 + SAT): location/pin of SBP v2.3 and the SAT check-id
            list for satChecks.yaml. M3 the SEC-01 required system-schema list (§4.1).
            M4 D-N2: signed run manifest or accept the limit. Plus confirm the three import
            overrides (SBP-54→SEC-01, SBP-02→SEC-08, SBP-13→SEC-10) and the annex Appendix B
            summary fix (rows say 25/26/9/1/7).
Done when:  Answers in program\decisions.md; the spec's status → Accepted.
Open:       Registry promotion is yours at items C and D — candidates land in
            controlTool\proposals\, never registry\.
```
