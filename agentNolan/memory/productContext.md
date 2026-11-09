---
name: productContext
description: Users, existing assets and blueprint mapping that every Databricks-security PRD starts from
type: project
---

- **Users:** Contoso SecOps — three engineers and a manager (Manish is one of the engineers and
  the product owner); auditors/insurers/LPs who ask them for evidence; CloudOps as Databricks
  platform owner and Data Engineering as workload owner (per Technology's platform standard
  v0.14, still being ratified — ownership was disputed at the 25 Aug 2026 meeting).
- **What already exists** (check before writing "build"): the Databricks Security Policy v0.5
  (31 controls SEC-01..31); the **control tool** (`secopsCurrentProjects\databricks\controlTool\`,
  registry-driven detect pipeline, fixture-verified only); `agentDaya\mcp\dctMcp.py` (read-only
  MCP over it); the vendor's *Security Best Practices for Azure Databricks* v2.3 with 68
  configurations and its SAT; Purview for classification/labels; the DSPM skeleton `dspm\`.
- **Objective → blueprint mapping** (`agentDaya\knowledge\dspmBlueprint.md`): "SAT equivalent" =
  layer 4 (posture) — an epic over the control tool, not a new scanner; "security-config console
  / MCP" = layers 4–5 + UI, seeded by `dctMcp.py`; "access-model standard with alerts" = layers
  3–4 with Sentinel for the event modality.
- **Why:** every candidate objective so far was 40–60% already built; PRDs that ignore this
  produce duplicate systems. **How to apply:** the Discover step names the overlap with paths
  before any story is written. Related: [[workstationConstraints]].
