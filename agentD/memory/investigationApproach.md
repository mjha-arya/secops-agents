---
name: investigationApproach
description: Reusable, non-obvious learnings from real Defender investigations - empty until the first real run
type: project
---

No investigations have run yet (blocked on [[appRegistration]]). Once real alerts have been
investigated, record things here like:

- A detection name or rule that's routinely a false positive for a specific known-good app or
  script, and why.
- A host or account naming convention that helps tell "known service account" from "unexpected
  actor" at a glance.
- Evidence-shape gotchas: an `@odata.type` or field Graph actually returns that
  `mcp\defenderMcp.py`'s `EVIDENCE_FIELDS` allow-list doesn't cover yet (propose adding it, per P9).
- A tenant-specific pattern in how alerts cluster into incidents.

Don't record individual investigation verdicts here - those belong in each investigation's own
`defenderAlertInvestigation\investigations\<...>\findings.md`. This file is for what generalises
across investigations.
