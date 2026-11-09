"""The dbSAT finding record, read from one control-tool run. Read-only.

Spec: dspm/docs/specs/dbSatSlice1.md § (c) item 9. The control tool is
imported, never copied (ADR-0002 F6): `load_ctl()` puts `CTL_ROOT` on the path.

A run is published whole or not at all. Anything that stops the run being read
faithfully - a missing or unparseable artifact, a status outside the five
buckets, an unknown control, an unmappable scope, evidence that does not verify
or that disagrees with findings.json, or a findings.json that is not the whole
of the hashed evidence (omitted, duplicated or stray) - raises AdapterError. There is no partial
result and no defaulted status: the caller records the run as failed.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BUCKETS = frozenset({"compliant", "deviation", "prerequisite-gap", "procedural", "unknown"})


class AdapterError(Exception):
    """The run cannot be read faithfully - reject it whole."""


@dataclass(frozen=True)
class FindingRecord:
    run_id: str
    check_id: str                  # ctl control id, e.g. "SEC-06"
    refs: tuple[str, ...]          # slice 1: (check_id,)  - provenance arrives in slice 2
    severity: str                  # critical | high | medium | low
    scope_type: str                # workspace | account | metastore | estate
    scope_id: str                  # workspace_id / DATABRICKS_ACCOUNT_ID / metastore_id; never "account"
    workspace: str | None          # inventory name when scope_type == workspace
    status: str                    # exactly one of the five buckets
    observed: Any
    desired: Any                   # control.desired from the registry snapshot
    reason: str
    method: tuple[dict, ...]       # from the evidence record's "method"
    registry_version: str
    evidence_path: str             # relative to the run dir
    evidence_sha256: str
    collected_at: str | None       # ISO-8601 UTC, from the observation; None for procedural/estate


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    estate: str                    # "live" if requests.json exists, else "fixture"
    registry_version: str
    account_id: str | None
    findings: tuple[FindingRecord, ...]


# ------------------------------------------------------------------ ctl


def load_ctl() -> Path:
    """Put the control tool on sys.path; return its root. Packaging is D3."""
    raw = os.environ.get("CTL_ROOT")
    if not raw:
        raise AdapterError("CTL_ROOT is not set - point it at the control tool folder")
    root = Path(raw).resolve()
    if not (root / "ctl" / "__init__.py").is_file():
        raise AdapterError(f"CTL_ROOT {root} has no ctl package")
    loaded = sys.modules.get("ctl")
    if loaded is not None and getattr(loaded, "__file__", None):
        if Path(loaded.__file__).resolve().parent.parent != root:
            raise AdapterError(f"CTL_ROOT {root} differs from the ctl already imported "
                               f"({Path(loaded.__file__).resolve().parent.parent})")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


# ------------------------------------------------------------------ evidence


def evidence_hash(record_without_sha256: dict[str, Any]) -> str:
    """The hash `ctl.stages.report.evidence_pack` stores. Mirrored, because
    there it is inline; tests compare the two on a real evidence file."""
    body = json.dumps(record_without_sha256, indent=2, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _ctl_scope(record: FindingRecord) -> str:
    return record.workspace if record.scope_type == "workspace" else record.scope_type


def verify_evidence(run_dir: Path, record: FindingRecord) -> bool:
    """True only if the evidence file hashes to its stored sha256, that hash is
    the record's, and the hashed status for this scope is the record's status."""
    try:
        evidence = json.loads((Path(run_dir) / record.evidence_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(evidence, dict):
        return False
    stored = evidence.pop("sha256", None)
    if not stored or evidence_hash(evidence) != stored or stored != record.evidence_sha256:
        return False
    statuses = evidence.get("status_by_scope")
    return isinstance(statuses, dict) and statuses.get(_ctl_scope(record)) == record.status


# ------------------------------------------------------------------ reading


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise AdapterError(f"missing artifact {path.name}") from None
    except (OSError, ValueError) as exc:
        raise AdapterError(f"unreadable artifact {path.name}: {exc}") from None


def _iso(epoch: Any) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(epoch)))
    except (TypeError, ValueError, OverflowError):
        raise AdapterError(f"observation collected_at {epoch!r} is not a timestamp") from None


def _check_complete(run_dir: Path, control_ids: list[str], records: list[FindingRecord],
                    evidence_by_control: dict[str, dict[str, Any]]) -> None:
    """findings.json is not hashed, so it cannot be trusted to be whole (F1).
    The hashed evidence is the reference: one file per registry control (ctl
    assess emits at least one finding for each), no other file, and its scopes
    equal to findings.json's for that control, each listed once."""
    listed: set[tuple[str, str]] = set()
    for record in records:
        key = (record.check_id, _ctl_scope(record))
        if key in listed:
            raise AdapterError(f"{key[0]} {key[1]}: duplicate finding in findings.json")
        listed.add(key)
    try:
        entries = sorted((run_dir / "evidence").iterdir())
    except OSError as exc:
        raise AdapterError(f"unreadable evidence folder: {exc}") from None
    for path in entries:
        if path.stem in evidence_by_control:
            continue
        if path.stem in control_ids:             # every finding of a control was dropped
            evidence = _load_json(path)
            statuses = evidence.get("status_by_scope") if isinstance(evidence, dict) else None
            scopes = ", ".join(sorted(statuses)) if isinstance(statuses, dict) else "?"
            raise AdapterError(f"{path.stem} {scopes}: in the hashed evidence but missing "
                               "from findings.json")
        raise AdapterError(f"stray evidence/{path.name}: no finding in findings.json "
                           f"cites {path.stem}")
    for control_id in control_ids:
        if control_id not in evidence_by_control:
            raise AdapterError(f"{control_id}: registry control has no finding and no "
                               "evidence in the run")
    for check_id, evidence in sorted(evidence_by_control.items()):
        statuses = evidence.get("status_by_scope")
        hashed = set(statuses) if isinstance(statuses, dict) else set()
        mine = {scope for control, scope in listed if control == check_id}
        for scope in sorted(hashed - mine):
            raise AdapterError(f"{check_id} {scope}: in the hashed evidence but missing "
                               "from findings.json")
        for scope in sorted(mine - hashed):
            raise AdapterError(f"{check_id} {scope}: in findings.json but not in the "
                               "hashed evidence")


def read_run(run_dir: Path, registry_dir: Path, *, account_id: str | None = None) -> RunRecord:
    """Every finding of one run as a FindingRecord, or AdapterError. Writes nothing."""
    load_ctl()
    registry = importlib.import_module("ctl.registry")
    run_dir = Path(run_dir)
    try:
        reg = registry.load(registry_dir)
    except registry.RegistryError as exc:
        raise AdapterError(f"registry {registry_dir}: {exc}") from None

    findings = _load_json(run_dir / "findings.json")
    state = _load_json(run_dir / "state.json")
    if not isinstance(findings, list) or not isinstance(state, dict) \
            or not isinstance(state.get("observations"), list):
        raise AdapterError("findings.json or state.json does not have the run's shape")
    observations = state["observations"]

    account_id = account_id or os.environ.get("DATABRICKS_ACCOUNT_ID") or None
    workspace_ids = {w.name: w.workspace_id for w in reg.governed_workspaces()}
    metastore_id = next((o.get("observed", {}).get("metastore_id")
                         for o in observations
                         if o.get("control") == "_visibility" and not o.get("error")
                         and isinstance(o.get("observed"), dict)), None)

    def scope_of(scope: str) -> tuple[str, str, str | None]:
        if scope in workspace_ids:
            if not workspace_ids[scope]:
                raise AdapterError(f"workspace {scope} has no workspace_id in the inventory")
            return "workspace", workspace_ids[scope], scope
        if scope in ("account", "estate"):
            if not account_id:
                raise AdapterError(f"{scope} scope needs an account id: pass account_id "
                                   "or set DATABRICKS_ACCOUNT_ID")
            return scope, account_id, None
        if scope == "metastore":
            if not metastore_id:
                raise AdapterError("metastore scope needs the metastore_id from the "
                                   "_visibility observation, and the run has none")
            return "metastore", str(metastore_id), None
        raise AdapterError(f"scope {scope!r} maps to no workspace, account or metastore")

    records: list[FindingRecord] = []
    evidence_cache: dict[str, dict[str, Any]] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            raise AdapterError("findings.json holds a non-object finding")
        check_id, scope, status = (finding.get("control"), finding.get("scope"),
                                   finding.get("status"))
        if status not in BUCKETS:
            raise AdapterError(f"{check_id} {scope}: status {status!r} is not one of the five buckets")
        control = reg.by_id(check_id) if isinstance(check_id, str) else None
        if control is None:
            raise AdapterError(f"finding cites {check_id!r}, which is not in the registry")
        if not isinstance(scope, str):
            raise AdapterError(f"{check_id}: finding has no scope")
        scope_type, scope_id, workspace = scope_of(scope)

        evidence_path = f"evidence/{check_id}.json"
        if check_id not in evidence_cache:
            evidence_cache[check_id] = _load_json(run_dir / evidence_path)
        evidence = evidence_cache[check_id]
        if not isinstance(evidence, dict) or not isinstance(evidence.get("method"), list):
            raise AdapterError(f"{evidence_path} does not have the evidence shape")
        if evidence.get("standard") != reg.version:
            raise AdapterError(f"{evidence_path} was judged against registry "
                               f"{evidence.get('standard')!r}, not {reg.version!r}")

        if scope == "estate":
            collected_at = None
        else:
            stamps = [o.get("collected_at") for o in observations
                      if o.get("control") == check_id and o.get("scope") == scope]
            if not stamps:
                raise AdapterError(f"{check_id} {scope}: no observation in state.json")
            # The oldest observation: the finding is only as fresh as that.
            collected_at = min(_iso(s) for s in stamps)

        record = FindingRecord(
            run_id=run_dir.name, check_id=check_id, refs=(check_id,),
            severity=str(finding.get("severity", control.severity)),
            scope_type=scope_type, scope_id=scope_id, workspace=workspace,
            status=status, observed=finding.get("observed"), desired=control.desired,
            reason=str(finding.get("reason", "")),
            method=tuple(evidence["method"]), registry_version=reg.version,
            evidence_path=evidence_path, evidence_sha256=str(evidence.get("sha256", "")),
            collected_at=collected_at,
        )
        if not verify_evidence(run_dir, record):
            raise AdapterError(f"{evidence_path} does not verify for {check_id} {scope} "
                               "(sha256 or hashed status mismatch)")
        records.append(record)

    _check_complete(run_dir, [c.id for c in reg.controls], records, evidence_cache)
    return RunRecord(
        run_id=run_dir.name,
        estate="live" if (run_dir / "requests.json").exists() else "fixture",
        registry_version=reg.version, account_id=account_id,
        findings=tuple(records),
    )
