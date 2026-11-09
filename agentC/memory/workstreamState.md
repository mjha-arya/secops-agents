---
name: workstreamState
description: Where the certificate workstream stood when this agent was created, including the doc conflicts to resolve first
type: project
---

As of 2026-09-24:
- `bicep\main.bicep` (Logic App `la-sop-prd-cert-expiry-notifications`) is **authored, never
  deployed**. It reuses app registration `app-cert-expiry-logicapp-defender-test`
  (appId `00000000-0000-0000-0000-000000000000`, `Vulnerability.Read.All` consented).
- **The docs disagree on the target.** `readme.md` and `discovery\findings20260708.md` say
  `prod-loganalytics01-rg` in `Microsoft Azure CSP: Production` (`88fa1206-...`). `bicep\deploy.md`
  and `main.bicep` say `rg-ne-sop-prd-default` in `Sop-Production` (`b27e80cb-...`). `deploy.md`
  also implies the old Logic App `defender_certificate_notifications` was deleted, while the
  readme says it was to be disabled.
- The old secret (hint `PNK`) was exposed in the old Logic App's run history. Check whether it was
  rotated.
- Open risk: the token audience is `api.securitycenter.microsoft.com` but the data call uses
  `api.security.microsoft.com`. Unproven in this tenant.

**Why:** these conflicts would make the first run build on a wrong assumption.

**How to apply:** the first Phase 1 run resolves these with live read-only checks, records the
answer in a new discovery file, then updates this memory.
