"""Read-only MCP server (stdio) over the Databricks Control Tool command line.

Every tool shells out to ctl.py with an argument vector built here from validated inputs. The
four flags that can reach a real system or spend money - --live, --live-agent, --approve-all,
--promote - are never constructed, and are refused if they ever appear, so this server cannot
start a live read, call the paid model path, approve a change or raise a control's enforcement,
whatever the calling agent asks for. ctl.py with no such flags uses the recorded fixture estate.
"""
import sys

sys.dont_write_bytecode = True  # the repo lives in OneDrive; keep __pycache__ out of it

import json
import os
import re
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent.parent  # secopsAutomationOperations
CONTROL_TOOL = WORKSPACE / "secopsCurrentProjects" / "databricks" / "controlTool"
CTL = CONTROL_TOOL / "ctl.py"
RUNS = CONTROL_TOOL / "runs"
REGISTRY = CONTROL_TOOL / "registry"
AUDIT_DIR = HERE.parent / "runs"

CONTROL_ID = re.compile(r"^SEC-\d{2}$")
RUN_ID = re.compile(r"^\d{8}-\d{6}$")
DOMAIN = re.compile(r"^[a-z][a-z\-]{0,60}$")
FORBIDDEN_FLAGS = {"--live", "--live-agent", "--approve-all", "--promote"}
TIMEOUT_SECONDS = 300
CLIP = 60_000

Stage = Literal["discover", "assess", "adjudicate", "plan", "simulate", "approve", "apply", "verify", "report"]
Artifact = Literal["run", "registry.snapshot", "state", "findings", "adjudication", "plan",
                   "simulation", "approval", "applied", "verification", "position"]
RegistryFile = Literal["controlRegistry", "exceptionRegister", "workspaceInventory"]

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
# run_pipeline writes a runs/<timestamp>/ folder of fixture-derived artifacts; it changes no system.
LOCAL_WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)

mcp = MCPServer(
    "dct",
    instructions=(
        "Read-only access to the Databricks Control Tool for Contoso SecOps. Runs ctl.py against "
        "the recorded fixture estate and reads its run artifacts and registry files. There are no "
        "write tools: this server cannot run --live, approve a change, promote a control or edit "
        "the registry. Findings describe security posture; quote only what the question needs."
    ),
)


def _audit(tool: str, args: dict, outcome: str) -> None:
    AUDIT_DIR.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc)
    line = {"ts": now.isoformat(), "tool": tool, "args": args, "outcome": outcome}
    with open(AUDIT_DIR / f"toolCalls{now:%Y%m%d}.jsonl", "a", encoding="utf-8") as f:
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


def _check(value: str, pattern: re.Pattern, name: str) -> str:
    if not pattern.fullmatch(value):
        raise ToolError(f"{name} has an unexpected format: {value!r}")
    return value


def _clip(text: str) -> tuple[str, bool]:
    if len(text) <= CLIP:
        return text, False
    return text[:CLIP] + "\n...[truncated]", True


def _ctl(*argv: str) -> dict:
    argv = [str(a) for a in argv]
    if FORBIDDEN_FLAGS & set(argv):
        raise ToolError("refused: that flag can reach a real system or spend money; a human runs it.")
    if not CTL.is_file():
        raise ToolError(f"ctl.py not found at {CTL}")
    env = {k: v for k, v in os.environ.items() if k != "DATABRICKS_WRITE_TOKEN"}
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        p = subprocess.run(
            [sys.executable, str(CTL), *argv],
            cwd=CONTROL_TOOL, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as e:
        raise ToolError(f"ctl.py {' '.join(argv)} exceeded {TIMEOUT_SECONDS}s") from e
    output, truncated = _clip((p.stdout + p.stderr).strip())
    return {"command": "ctl.py " + " ".join(argv), "exitCode": p.returncode,
            "output": output, "truncated": truncated}


@mcp.tool(annotations=READ_ONLY)
def validate() -> dict:
    """Check the control registry and collector routing: 31 controls, detect-spec routing,
    one-way doors, procedural controls, prerequisites and the enforcement counts."""
    with _audited("validate", {}) as out:
        res = _ctl("validate")
        out["outcome"] = f"exit {res['exitCode']}"
        return res


@mcp.tool(annotations=READ_ONLY)
def list_controls(domain: str | None = None) -> dict:
    """List the registry as a table (id, severity, complexity, enforcement, reversible, title).
    domain: optional substring of a domain name, e.g. 'secrets' or 'identity'."""
    with _audited("list_controls", {"domain": domain}) as out:
        argv = ["controls"]
        if domain:
            argv += ["--domain", _check(domain.lower(), DOMAIN, "domain")]
        res = _ctl(*argv)
        out["outcome"] = f"exit {res['exitCode']}"
        return res


@mcp.tool(annotations=READ_ONLY)
def explain_control(control_id: str) -> dict:
    """One control end to end: how it is detected, the desired state, how it would be
    implemented, rollback, dependencies, and whether it is a one-way door or procedural."""
    control_id = control_id.strip().upper()
    with _audited("explain_control", {"control_id": control_id}) as out:
        _check(control_id, CONTROL_ID, "control_id")
        res = _ctl("explain", control_id)
        out["outcome"] = f"exit {res['exitCode']}"
        return res


@mcp.tool(annotations=LOCAL_WRITE)
def run_pipeline(stop_after: Stage = "report") -> dict:
    """Run the pipeline against the RECORDED FIXTURE ESTATE (never the live tenant) and write a
    new runs/<timestamp>/ folder. Stages 1-6 are read-only; with no approver it stops before
    apply regardless of stop_after. Prefer list_runs + read_run_artifact when a recent run exists."""
    with _audited("run_pipeline", {"stop_after": stop_after}) as out:
        res = _ctl("run", "--stop-after", stop_after)
        m = re.search(r"^artifacts:\s*(.+?)\s*$", res["output"], re.M)
        res["runId"] = Path(m.group(1)).name if m else None
        res["backend"] = "fixtures (recorded demo estate) - not the live tenant"
        out["outcome"] = f"exit {res['exitCode']}, run {res['runId']}"
        return res


@mcp.tool(annotations=READ_ONLY)
def position() -> dict:
    """The five-bucket control position (compliant / deviation / prerequisite-gap / procedural /
    unknown) from a fresh discover+assess pass over the fixture estate. No percentage, by design.
    Like the CLI, this writes a runs/<timestamp>/ folder; prefer read_run_artifact when one exists."""
    with _audited("position", {}) as out:
        res = _ctl("position")
        out["outcome"] = f"exit {res['exitCode']}"
        return res


@mcp.tool(annotations=READ_ONLY)
def drift() -> dict:
    """Only what changed outside the pipeline: settings edited in the console versus what the
    registry or IaC declares. Like the CLI, this writes a runs/<timestamp>/ folder."""
    with _audited("drift", {}) as out:
        res = _ctl("drift")
        out["outcome"] = f"exit {res['exitCode']}"
        return res


@mcp.tool(annotations=READ_ONLY)
def preflight() -> dict:
    """What a LIVE run would need: endpoints, credentials per plane, settings, placeholder
    workspace ids, and the access to request for the service principal. Exit 1 means not ready."""
    with _audited("preflight", {}) as out:
        res = _ctl("preflight")
        res["ready"] = res["exitCode"] == 0
        out["outcome"] = "ready" if res["ready"] else "not ready"
        return res


@mcp.tool(annotations=READ_ONLY)
def list_runs(limit: int = 10) -> dict:
    """Most recent control-tool runs, newest first, with the artifacts each one produced
    (which tells you how far the pipeline got). limit: 1-50."""
    limit = max(1, min(limit, 50))
    with _audited("list_runs", {"limit": limit}) as out:
        if not RUNS.is_dir():
            out["outcome"] = "no runs folder"
            return {"runs": []}
        dirs = sorted((d for d in RUNS.iterdir() if d.is_dir() and RUN_ID.fullmatch(d.name)),
                      key=lambda d: d.name, reverse=True)[:limit]
        runs = []
        for d in dirs:
            artifacts = sorted(p.stem for p in d.glob("*.json"))
            if (d / "position.txt").is_file():
                artifacts.append("position")
            evidence = d / "evidence"
            runs.append({
                "runId": d.name,
                "artifacts": artifacts,
                "evidenceFiles": len(list(evidence.glob("SEC-*.json"))) if evidence.is_dir() else 0,
            })
        out["outcome"] = f"{len(runs)} runs"
        return {"runs": runs}


@mcp.tool(annotations=READ_ONLY)
def read_run_artifact(run_id: str, artifact: Artifact) -> dict:
    """Read one artifact from a run: findings, adjudication, plan (with its excluded list),
    simulation, state, the position text, and so on. run_id is like 20260926-183834."""
    with _audited("read_run_artifact", {"run_id": run_id, "artifact": artifact}) as out:
        _check(run_id, RUN_ID, "run_id")
        name = "position.txt" if artifact == "position" else f"{artifact}.json"
        path = RUNS / run_id / name
        if not path.is_file():
            raise ToolError(f"{name} does not exist in run {run_id}; the pipeline may have "
                            "stopped before that stage.")
        text = path.read_text(encoding="utf-8")
        clipped, truncated = _clip(text)
        content = clipped if (truncated or artifact == "position") else json.loads(text)
        out["outcome"] = f"{len(text)} chars" + (" (truncated)" if truncated else "")
        return {"runId": run_id, "artifact": artifact, "truncated": truncated, "content": content}


@mcp.tool(annotations=READ_ONLY)
def read_evidence(run_id: str, control_id: str) -> dict:
    """The per-control evidence record from a run: method, observation, standard version,
    timestamp and SHA-256 - the DDQ/audit output for one control."""
    control_id = control_id.strip().upper()
    with _audited("read_evidence", {"run_id": run_id, "control_id": control_id}) as out:
        _check(run_id, RUN_ID, "run_id")
        _check(control_id, CONTROL_ID, "control_id")
        path = RUNS / run_id / "evidence" / f"{control_id}.json"
        if not path.is_file():
            raise ToolError(f"no evidence for {control_id} in run {run_id}")
        out["outcome"] = "ok"
        return {"runId": run_id, "controlId": control_id, "content": json.loads(path.read_text(encoding="utf-8"))}


@mcp.tool(annotations=READ_ONLY)
def registry_file(name: RegistryFile) -> dict:
    """The text of one registry file, read-only: controlRegistry (the 31 records),
    exceptionRegister (approved deviations with expiry) or workspaceInventory (the governed
    estate). Use it to quote exact records in a proposal. This server cannot write them."""
    with _audited("registry_file", {"name": name}) as out:
        path = REGISTRY / f"{name}.yaml"
        if not path.is_file():
            raise ToolError(f"{path.name} not found")
        text = path.read_text(encoding="utf-8")
        clipped, truncated = _clip(text)
        out["outcome"] = f"{len(text)} chars" + (" (truncated)" if truncated else "")
        return {"file": str(path), "truncated": truncated, "content": clipped}


if __name__ == "__main__":
    mcp.run()
