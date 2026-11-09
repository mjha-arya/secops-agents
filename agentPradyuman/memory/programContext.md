---
name: programContext
description: The delivery loop, standing blockers and the phase-5 dependency for the Databricks security programme
type: project
---

- **The loop** (2026-09-26): Manish → Nolan (PRD) → Pradyuman (plan) → Daya (spec/ADR) → Dino
  (code) → Daya (review) → Pradyuman (status) → Manish (gate). Run separately, hand-off through
  `program\`. Chosen so every step is human-visible before any orchestration is automated.
- **Standing blockers (updated 2026-09-27):** GitHub MCP rejects the token header (tracker writes
  mirror to files); no live Databricks read yet (placeholder inventory rows, no SP credential);
  ADR-0001/0002 unaccepted; CI host undecided. Objective is set (dbSat) and agents now run turns.
- **Phase 5 (Act) is gated on the control tool's registry being ratified** — all 31 controls sit
  at `enforcement: observe`; promotion is a reviewed YAML change with a name against it. Don't
  schedule remediation work ahead of that.
- **Dino's write scope (Q10, 2026-09-27):** `dspm\` + memory, plus the control tool's `ctl\`,
  `tests\`, `fixtures\`, `ctl.py`, `README.md`. `registry\` and `.env` stay human-owned — any item
  touching them goes to Manish as a Daya proposal. The control tool is a separate git repo, so
  every turn proposes two commits.
- **Sequencing lesson (2026-09-27):** fixture-green ≠ live-green. Daya's review of turn A found
  assertions written against the fixture's shape. Put a review turn between every build turn and
  the first live run, and check a live run's done-when against which spec items produce it.
- **Why:** these have been true since the team was formed; a plan that doesn't lead with them is
  fiction. **How to apply:** copy the current blocker list into `status.md` at the top of every
  turn and check whether each has cleared. Related: [[workstationConstraints]].
