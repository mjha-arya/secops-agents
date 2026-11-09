---
name: schemaTransitions
description: Registry schema migrations — detect the legacy shape from the data, never gate it on an env flag
metadata:
  type: feedback
---

When a spec makes a new registry field mandatory before the candidate that adds it is promoted, never
bridge the gap with an env flag. Slice 2 turn A did that with `CTL_ALLOW_LEGACY_PROVENANCE`, and every
caller that loads `registry\` broke: `ctl.py run`/`validate`, `fixtures\build_demo.py`, and my own
`dct` MCP (a raw traceback).

**Why:** a flag has to be remembered by every caller. A flag left set in production also accepts a
half-migrated registry.

**How to apply:** allow the legacy path only when the *whole* registry is legacy (no new file, no
new key anywhere), and make it inert (unratified, no status change). A partial migration is fatal.
Delete the branch after promotion. Before approving a transition, grep for every `registry.load`
caller. Related: [[falseGreenSources]].
