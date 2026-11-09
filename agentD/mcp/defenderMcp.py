"""Read-only Microsoft Defender XDR alert/incident MCP server (stdio) backed by Microsoft Graph.

Covers whatever serviceSource the tenant's alerts_v2 records carry (Defender for Endpoint,
Identity, Office, Cloud Apps, and Sentinel-synced alerts) - unlike purviewMcp.py, this server does
not restrict to a single source.
"""
import sys

sys.dont_write_bytecode = True  # the repo lives in OneDrive; keep __pycache__ out of it

import asyncio
import json
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

from graphAuth import AuthError, get_token

GRAPH = "https://graph.microsoft.com"
RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"
# No '.', so httpx can't collapse a dot-segment out of the intended path.
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,127}$")
MAX_PAGES = 4
# Output name -> path into an alert evidence object. Allow-list, so an unexpected payload shape
# stays out. Extend this as real evidence payloads are seen (see readme.md "Known gaps").
EVIDENCE_FIELDS = {
    "deviceName": ("deviceDnsName",),
    "upn": ("userAccount", "userPrincipalName"),
    "accountName": ("userAccount", "accountName"),
    "domainName": ("userAccount", "domainName"),
    "ipAddress": ("ipAddress",),
    "countryCode": ("countryLetterCode",),
    "fileName": ("fileDetails", "fileName"),
    "filePath": ("fileDetails", "filePath"),
    "sha256": ("fileDetails", "sha256"),
    "sha1": ("fileDetails", "sha1"),
    "url": ("url",),
    "processCommandLine": ("processCommandLine",),
    "parentProcessCommandLine": ("parentProcessCommandLine",),
    "registryKey": ("registryKey",),
    "registryValue": ("registryValue",),
    "mailSubject": ("subject",),
    "sender": ("p1Sender", "emailAddress"),
    "recipient": ("recipientEmailAddress",),
    "cloudAppName": ("appName",),
}
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)

mcp = MCPServer(
    "defender",
    instructions=(
        "Read-only Microsoft Defender XDR alert and incident data for Contoso SecOps, via "
        "Microsoft Graph. There are no write tools here - this server cannot change alert state, "
        "comment, classify or take any containment action. The data is sensitive; quote only what "
        "the investigation needs."
    ),
)


def _audit(tool: str, args: dict, outcome: str) -> None:
    # Arguments and outcome only; alert/evidence content is sensitive and stays out of the log.
    RUNS_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    line = {"ts": now.isoformat(), "tool": tool, "args": args, "outcome": outcome}
    with open(RUNS_DIR / f"toolCalls{now:%Y%m%d}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


@contextmanager
def _audited(tool: str, args: dict):
    """Audit every call, including failures. Set out["outcome"] inside the block."""
    out = {"outcome": "ok"}
    try:
        yield out
    except ToolError as e:
        _audit(tool, args, f"error: {e}")
        raise
    except Exception as e:
        _audit(tool, args, f"crash: {type(e).__name__}")
        raise
    else:
        _audit(tool, args, out["outcome"])


def _check(value: str, name: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise ToolError(f"{name} has an unexpected format.")
    return value


def _clip(value: str | None, limit: int) -> str | None:
    return value if not value or len(value) <= limit else value[:limit] + "..."


def _dig(obj, path: tuple) -> object:
    for key in path:
        obj = obj.get(key) if isinstance(obj, dict) else None
    return obj


async def _graph(method: str, path: str, **kwargs) -> dict:
    try:
        token = await asyncio.to_thread(get_token)
    except AuthError as e:
        raise ToolError(str(e)) from e
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "secops-agentD-defenderMcp/0.1"}
    try:
        async with httpx.AsyncClient(base_url=GRAPH, timeout=60) as client:
            for attempt in range(2):
                r = await client.request(method, path, headers=headers, **kwargs)
                if attempt or r.status_code not in (429, 503, 504):
                    break
                retry_after = r.headers.get("Retry-After", "5")
                await asyncio.sleep(min(int(retry_after) if retry_after.isdigit() else 5, 10))
    except httpx.HTTPError as e:
        raise ToolError(f"Network error calling Graph: {type(e).__name__}") from e
    if r.status_code >= 400:
        try:
            err = r.json().get("error", {})
        except ValueError:
            err = {}
        detail = f"{err.get('code', '')}: {err.get('message', '')}" if err else r.text[:300]
        raise ToolError(f"Graph {r.status_code} on {path.split('?')[0]}: {_clip(detail, 500)}")
    return r.json() if r.content else {}


async def _collect(path: str, want: int, params: dict | None = None) -> tuple[list[dict], bool]:
    """Follow @odata.nextLink until `want` items or MAX_PAGES. Returns (items, more_available)."""
    items: list[dict] = []
    url: str | None = path
    for _ in range(MAX_PAGES):
        data = await _graph("GET", url, params=params)
        items.extend(data.get("value", []))
        url, params = data.get("@odata.nextLink"), None
        if not url or len(items) >= want:
            break
        if not url.startswith(GRAPH + "/"):
            raise ToolError("Graph returned a nextLink to an unexpected host; stopped.")
    return items[:want], bool(url) or len(items) > want


def _alert_users(a: dict) -> list[str]:
    upns = (_dig(e, ("userAccount", "userPrincipalName")) for e in a.get("evidence") or [])
    return list(dict.fromkeys(u for u in upns if u))


def _alert_summary(a: dict) -> dict:
    return {
        "id": a.get("id"),
        "title": a.get("title"),
        "severity": a.get("severity"),
        "status": a.get("status"),
        "category": a.get("category"),
        "serviceSource": a.get("serviceSource"),
        "detectionSource": a.get("detectionSource"),
        "created": a.get("createdDateTime"),
        "lastUpdated": a.get("lastUpdateDateTime"),
        "assignedTo": a.get("assignedTo"),
        "classification": a.get("classification"),
        "determination": a.get("determination"),
        "incidentId": a.get("incidentId"),
        "users": _alert_users(a),
        "portalUrl": a.get("alertWebUrl"),
    }


def _evidence_summary(e: dict) -> dict:
    out = {"type": (e.get("@odata.type") or "").rsplit(".", 1)[-1], "roles": e.get("roles") or []}
    for name, path in EVIDENCE_FIELDS.items():
        value = _dig(e, path)
        if value not in (None, "", []):
            out[name] = value
    return out


@mcp.tool(annotations=READ_ONLY)
def resolve_link(url: str) -> dict:
    """Parse a security.microsoft.com alert or incident URL into its kind and ID. No Graph call.
    Also accepts a bare alert/incident ID if you already have one."""
    with _audited("resolve_link", {"url": _clip(url, 200)}) as out:
        candidate = url.strip()
        if candidate.lower().startswith("http"):
            segments = [s for s in urlparse(candidate).path.split("/") if s]
            kind_by_segment = {"alerts": "alert", "alert": "alert", "incidents": "incident", "incident": "incident"}
            matches = [(kind_by_segment[s.lower()], segments[i + 1]) for i, s in enumerate(segments)
                       if s.lower() in kind_by_segment and i + 1 < len(segments)]
            if not matches:
                raise ToolError("Couldn't find /alerts/<id> or /incidents/<id> in that URL.")
            kind, raw_id = matches[0]
            entity_id = unquote(raw_id)
        else:
            kind, entity_id = "alert", candidate  # bare ID with no URL: assume alert, caller can override
        entity_id = _check(entity_id, "resolved id")
        out["outcome"] = f"{kind} {entity_id}"
        return {"kind": kind, "id": entity_id}


@mcp.tool(annotations=READ_ONLY)
async def get_alert(alert_id: str) -> dict:
    """Get one Defender alert (any source) with description, MITRE techniques and trimmed evidence."""
    with _audited("get_alert", {"alert_id": alert_id}) as out:
        _check(alert_id, "alert_id")
        a = await _graph("GET", f"/v1.0/security/alerts_v2/{alert_id}")
        evidence = a.get("evidence") or []
        out["outcome"] = f"ok, {len(evidence)} evidence"
        return {
            **_alert_summary(a),
            "description": _clip(a.get("description"), 2000),
            "recommendedActions": _clip(a.get("recommendedActions"), 2000),
            "mitreTechniques": a.get("mitreTechniques") or [],
            "firstActivity": a.get("firstActivityDateTime"),
            "lastActivity": a.get("lastActivityDateTime"),
            "resolved": a.get("resolvedDateTime"),
            "incidentUrl": a.get("incidentWebUrl"),
            "evidence": [_evidence_summary(e) for e in evidence[:50]],
            "evidenceTruncated": len(evidence) > 50,
        }


@mcp.tool(annotations=READ_ONLY)
async def get_incident(incident_id: str) -> dict:
    """Get one Defender incident: severity, status, classification, tags and summary.
    Call list_incident_alerts separately to see the alerts inside it."""
    with _audited("get_incident", {"incident_id": incident_id}) as out:
        _check(incident_id, "incident_id")
        i = await _graph("GET", f"/v1.0/security/incidents/{incident_id}")
        out["outcome"] = "ok"
        return {
            "id": i.get("id"),
            "displayName": i.get("displayName"),
            "severity": i.get("severity"),
            "status": i.get("status"),
            "classification": i.get("classification"),
            "determination": i.get("determination"),
            "assignedTo": i.get("assignedTo"),
            "tags": i.get("tags") or [],
            "summary": _clip(i.get("summary"), 2000),
            "created": i.get("createdDateTime"),
            "lastUpdated": i.get("lastUpdateDateTime"),
            "portalUrl": i.get("incidentWebUrl"),
            "alertCount": len(i.get("alerts") or []),
        }


@mcp.tool(annotations=READ_ONLY)
async def list_incident_alerts(incident_id: str, top: int = 50) -> dict:
    """List the alerts inside a Defender incident (summary fields only). top: 1-100."""
    top = max(1, min(top, 100))
    with _audited("list_incident_alerts", {"incident_id": incident_id, "top": top}) as out:
        _check(incident_id, "incident_id")
        # incident_id is validated above and only ever appears inside a quoted OData literal.
        items, more = await _collect(
            "/v1.0/security/alerts_v2",
            top,
            params={"$filter": f"incidentId eq '{incident_id}'", "$top": top},
        )
        alerts = [_alert_summary(a) for a in items]
        out["outcome"] = f"{len(alerts)} alerts"
        return {"alerts": alerts, "more": more}


if __name__ == "__main__":
    mcp.run()
