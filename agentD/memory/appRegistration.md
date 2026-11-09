---
name: appRegistration
description: AgentD reuses the shared Graph app; it needs two new application permissions plus a secret/cert before it can make a real call
type: project
---

**Decision (2026-09-24, Manish):** AgentD reuses the existing shared app registration
**"SecOps - Microsoft Graph Access"** (`00000000-0000-0000-0000-000000000000`, single-tenant,
public client flows off) rather than getting its own dedicated app. This was an explicit
least-privilege trade-off, made with the finding below in hand - don't re-litigate it without a new
reason, but don't forget the finding either.

**Finding, confirmed live via `az ad app permission list --id e76afe68-...`:** this app currently
holds only `Channel.ReadBasic.All`, `ChannelMember.Read.All`, `Group.Read.All`, `Sites.Read.All`,
`Team.ReadBasic.All`, `User.Read.All` (all application) plus the default delegated `User.Read`. It
has **zero** security/Defender scopes today, despite `mcpServerCreator/memory/graphAppRegistrations.md`
claiming AppLocker and certificate-expiry use it - that claim is wrong: AppLocker uses its own
delegated interactive flow, and certificate-expiry uses a separate dedicated app
(`app-cert-expiry-logicapp-defender-test`, `00000000-0000-0000-0000-000000000000`). That memory file
has been corrected.

**What's needed before AgentD can do a real investigation (needs_human - Manish or a Privileged Role
Admin):**
1. Add **application** permissions `SecurityAlert.Read.All` and `SecurityIncident.Read.All` to
   `00000000-0000-0000-0000-000000000000`, then **grant admin consent**. This widens what that
   shared identity can read tenant-wide (every Defender/Sentinel/Purview alert), so anyone else
   already using this app inherits that read access too - that was the explicit trade-off accepted
   above.
2. **Provision a credential.** No client secret or certificate for this app is referenced anywhere
   in this workspace - it isn't clear one currently exists. Prefer a certificate (`SECOPS_GRAPH_CERT_PATH`
   + `SECOPS_GRAPH_CERT_THUMBPRINT`, PEM kept outside OneDrive, e.g. `%USERPROFILE%\.secopsMcp\`)
   over a plaintext client secret (`SECOPS_GRAPH_CLIENT_SECRET`) - see `../mcp/graphAuth.py`.
3. `python ../mcp/graphAuth.py` (its `check()` path) confirms the credential works, but **not** that
   the two new permissions are consented - that only shows up as a 403 on the first real
   `get_alert`/`get_incident` call, which is the actual verification step (P11).

**How to apply:** until step 1 and 2 are done, every AgentD Graph call will fail. That's an expected,
documented gap (see `../readme.md` Status), not a bug to route around.
