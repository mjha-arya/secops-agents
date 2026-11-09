---
name: graphAppRegistrations
description: The existing "SecOps - Microsoft Graph Access" app is app-only with public client off; each MCP server needs its own app
type: project
---

Found on 2026-09-24: **"SecOps - Microsoft Graph Access"** (appId
`00000000-0000-0000-0000-000000000000`, single-tenant). It holds six application (Role)
permissions plus one delegated scope, and public-client flows are off.

**Correction (2026-09-24):** the six permissions are `Channel.ReadBasic.All`,
`ChannelMember.Read.All`, `Group.Read.All`, `Sites.Read.All`, `Team.ReadBasic.All`,
`User.Read.All` - Teams/SharePoint/directory scopes, not security ones, confirmed live via
`az ad app permission list`. This memory previously claimed AppLocker health and certificate
expiry use this app; that was wrong. AppLocker uses its own delegated interactive sign-in
(`DeviceManagementConfiguration.Read.All`), and certificate expiry uses a separate dedicated app
(`app-cert-expiry-logicapp-defender-test`, `00000000-0000-0000-0000-000000000000`). No script in
this workspace was found referencing a client secret or certificate for `e76afe68-...`, so it's
unclear one currently exists - see `agents\agentD\memory\appRegistration.md`, which reuses this app
for Defender alert access and documents the needs_human steps.

**Why:** adding delegated Purview scopes to it would widen the blast radius of a shared identity.
That breaks least privilege.

**How to apply:** each MCP server gets its own app registration. For the local MVP, the app should
be a public client ("Mobile and desktop" redirect `http://localhost`, public client flows allowed)
with delegated read-only scopes only. Creating the app and granting consent is **needs_human**.
Manish or a Global/Privileged Role Admin does it. Discover existing apps with
`az ad app list` (call the CLI through its python.exe, not az.cmd).
