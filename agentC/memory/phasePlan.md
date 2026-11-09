---
name: phasePlan
description: The order Manish chose for certificate sources, and what "done" means per phase
type: project
---

Decided on 2026-09-24:
1. **Defender TVM** (endpoint certificate inventory). Finish the existing Logic App: reconcile,
   validate, hand over, then verify against a real run.
2. **Azure Key Vault** certificates across subscriptions.
3. **Entra app registration** secrets and certificates.
4. **App Gateway / App Service** TLS bindings.

The agent is a **builder**: it authors and validates IaC, and a human deploys (P4).

**Why:** Manish's answer to the pre-build questions. Phase 1 already has most of the work done.

**How to apply:** don't start phase N+1 until phase N's readme says Verified, unless Manish says
so. Each new source should feed the same notification (one email, one format), not a new system.
Related: [[workstreamState]].
