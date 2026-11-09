---
name: graphPurviewQuirks
description: Graph API quirks for Purview - delegated labels need /me path (beta), audit query is v1.0 with workload-scoped perms, httpx collapses ".."
type: reference
---

Checked against Microsoft Learn on 2026-09-24:
- **Sensitivity labels:** beta only. `GET /security/informationProtection/sensitivityLabels` is
  for **application** permission. Delegated access must use
  `/me/security/informationProtection/sensitivityLabels`, which returns the labels published to
  that user, not every label in the tenant.
- **Audit search** (`/security/auditLog/queries`, `/records`) is **v1.0** now. The permissions are
  split per workload: `AuditLogsQuery-{Entra,Exchange,SharePoint,OneDrive,Endpoint,CRM}.Read.All`.
  `AuditLogsQuery.Read.All` is the *broadest* option, not the default. The body field is
  `serviceFilter` (singular string).
- **alerts_v2:** `$filter` supports assignedTo, classification, determination, createdDateTime,
  lastUpdateDateTime, severity, serviceSource and status. `$orderby` is not documented. Delegated
  access needs Security Reader or a similar role. Purview sources are `microsoftDataLossPrevention`
  and `microsoftInsiderRiskManagement`.
- **eDiscovery cases:** v1.0. An eDiscovery Manager sees only their own cases.
- **httpx normalises dot-segments** (`httpx/_urlparse.py` `normalize_path`), so an ID containing `..`
  in a URL path escapes to the parent endpoint. Never allow `.` in path ID allow-lists.

**Why:** the first Purview draft got the label path and the audit version wrong, and its ID regex
allowed `..`.

**How to apply:** use these facts for Purview and any Graph security server (Defender next).
Re-check the "Other supported versions" section on Learn before assuming an API is beta-only.
Related: [[mcpSdkV2]], [[graphAppRegistrations]].
