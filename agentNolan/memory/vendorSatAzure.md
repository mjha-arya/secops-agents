---
name: vendorSatAzure
description: How the vendor Databricks SAT actually runs on Azure (identity, jobs, results, dashboards) — the bar dbSAT is measured against
metadata:
  type: reference
---

Fetched from the SAT docs 2026-09-27 (v0.8.0):
- **Identity:** Entra app reg as Databricks SP with Account Admin, Workspace Admin (each workspace) and metastore admin, plus
  Reader on the subscription. Client secret, not PAT, in the current Azure docs. The objective's "PAT-based" claim is questionable.
- **Jobs:** "SAT Initializer Notebook" (once) and "SAT Driver Notebook" (default Mon/Wed/Fri, ~10 min/workspace). Secrets Scanner is optional.
- **Results and UI:** Delta tables in a `security_analysis` schema (or a UC catalog/schema you choose). DBSQL dashboards: Assessment Results, Executive, Secret Scanner.
- **Checks:** 65+ in `configs/security_best_practices.csv`, High/Medium/Low. Some are self-declared by notebook (e.g. `sso_enabled`), so they aren't observed.
- The GitHub README and the blog don't contain these details. The useful pages are `…github.io/security-analysis-tool/docs/installation/standard/azure/`,
  `/docs/usage/` and `/docs/functionality/`.

**How to apply:** use this to ground any SAT-comparison story. Treat self-declared checks as `procedural`. Related: [[productContext]].
