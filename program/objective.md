# Objective

## Active — set 2026-09-27 by Manish

```
Objective:    dbSAT (working name) - a new version of the Databricks Security Analysis Tool for
              Azure: every security configuration of an enrolled workspace and its account is
              scanned against one registry of checks, deviations are shown by severity on a
              dashboard, and the tool's architecture and every Azure dependency it needs are
              written down clearly enough that a new engineer can stand it up.
Why now:      The Databricks Security Policy is being ratified; the vendor SAT is AWS-first,
              unsupported (no SLA), notebook-based and checks the vendor's list, not ours. We need
              the assessment to be ours, continuous and evidence-backed.
Users:        SecOps engineers (weekly), CloudOps as platform owner, auditors/insurers who ask
              for evidence. Later: Data Engineering when a finding is theirs to fix.
Success:      1. One non-prod workspace scanned end to end with zero manual steps after setup;
                 every finding traceable to a check id, a severity and the observed value.
              2. The dashboard answers "what is wrong, how bad, since when" without a query.
              3. The architecture and Azure connection model let a second engineer reproduce
                 the setup from the docs alone.
Constraints:  Azure only. Observe-only - the scanner never changes a setting. One registry
              carrying both provenances: the 31 policy controls (SEC-nn) and the vendor SAT
              best practices (SBP-nn / SAT check ids). unknown is never compliant; no single
              percentage. Python; venvs outside OneDrive; no PowerShell. Credentials never in
              the repo. Runtime decision (hybrid: Python package runnable locally and as a
              Databricks job, Delta results, AI/BI dashboard) is proposed - Daya confirms or
              overturns it in ADR-0002.
Not this:     Not a remediation tool. Not AWS/GCP. Not a fork of the vendor SAT's notebooks.
              Not a second scanner beside the control tool - the control tool is the seed of
              layer 4.
Sources:      https://www.databricks.com/blog/announcing-security-analysis-tool-sat
              https://github.com/databricks-industry-solutions/security-analysis-tool
              Databricks Security Policy v0.5 (SEC-01..31); Security Best Practices for Azure
              Databricks v2.3 (68 configurations); secopsCurrentProjects\databricks\controlTool
Target:       Manish will provide a non-prod workspace + service principal for the first live
              scan (env vars only; Daya's connection model names the exact variables first).
```

Template:

```
Objective:    <one sentence — what exists at the end that doesn't now>
Why now:      <the pressure — audit, incident, standard being ratified, cost>
Users:        <who touches it weekly>
Success:      <2–3 observable outcomes, not features>
Constraints:  <Databricks-first; no writes without a human gate; Python; ...>
Not this:     <what it deliberately isn't>
```

## Candidates

1. **A Databricks SAT equivalent** — continuous, evidence-backed assessment of every Databricks
   security configuration against our own 31-control policy, not the vendor's generic checklist.
   Maps to blueprint layer 4; the control tool is the starting point.
2. **Security-configuration console + MCP for Databricks** — a chat surface where an engineer asks
   "how should X be configured for SEC-nn?" and gets the required state, the current state, the
   drift and the exact change, backed by an MCP server exposing the same tools to any agent.
   Maps to layers 4–5 and the UI; `agentDaya\mcp\dctMcp.py` is the seed.
3. **Access-model standard implementation with alerts** — when the access standard is ratified,
   implement its controls in Databricks and alert on every deviation. Layer 3 + layer 4 events.
