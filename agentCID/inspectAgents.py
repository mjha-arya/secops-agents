"""Deterministic inspection of Claude Agent SDK agents in this repo (the mechanics half of AgentCID, P1).

    python inspectAgents.py agentDaya agentDino          inspect named agents
    python inspectAgents.py --all                        every folder in the repo with an agent.py
    python inspectAgents.py --all --no-import            skip the venv import check (fast)

Writes reports/<date>-<agent>.md and .json per agent plus reports/<date>-summary.md. Every check is
a fact about the files: present/absent, resolves/doesn't, imports/doesn't. Judgement about whether
the soul is *good* is the model's job, not this script's. Read-only: nothing in an agent folder is
modified. Standard library only.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
HOME = Path.home()
REPORTS = HERE / "reports"
VENVS = HOME / ".venvs"
PLUGIN_CACHE = HOME / ".claude" / "plugins" / "cache"
USER_SKILLS = HOME / ".claude" / "skills"

REQUIRED_FILES = ["soul.md", "agent.py", "readme.md", "requirements.txt", "memory/MEMORY.md"]
SOUL_SECTIONS = {
    "S1 attitude section": r"^##\s+Attitude",
    "S2 method section": r"^##\s+(How we solve|Point of view)",
    "S3 needs_human section": r"^##\s+needs_human",
    "S4 hard-rules section": r"^##\s+Hard rules",
    "S5 memory section": r"^##\s+Memory",
}
SECRET = re.compile(
    r"sk-ant-[A-Za-z0-9\-_]{10,}|ghp_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY"
    r"|(?i:(client_secret|password))\s*[:=]\s*['\"][^'\"\s]{8,}"
)
FRONTMATTER_KEYS = ("name", "description", "type")
WRITE_TOOL_NAMES = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "PowerShell"}


# ----------------------------------------------------------------------------- discovery


def _frontmatter_name(p: Path) -> str | None:
    head = _read(p)[:400]
    m = re.search(r"^name:\s*[\"']?([A-Za-z0-9_\-]+)", head, re.M) if head.startswith("---") else None
    return m.group(1) if m else None


def _model_invocable(p: Path) -> bool:
    """A skill with disable-model-invocation: true is a user-only slash command; an SDK agent (the
    model) can never call it, however present it is on disk."""
    head = _read(p)[:800]
    return not re.search(r"^disable-model-invocation:\s*true", head, re.M | re.I)


def known_skills() -> set[str]:
    """Skill names a soul may invoke as /name: directory names and frontmatter names of every
    model-invocable SKILL.md under the user skills folder and the plugin cache (any depth -
    plugins differ), plus command stems."""
    names: set[str] = set()
    for root in (USER_SKILLS, PLUGIN_CACHE):
        if not root.is_dir():
            continue
        for p in root.rglob("SKILL.md"):
            if not _model_invocable(p):
                continue
            names.add(p.parent.name)
            if fm := _frontmatter_name(p):
                names.add(fm)
        names |= {p.stem for p in root.rglob("commands/*.md")}
    return names


def known_agents() -> set[str]:
    if not PLUGIN_CACHE.is_dir():
        return set()
    return {p.stem for p in PLUGIN_CACHE.glob("*/*/*/agents/*.md")}


def installed_plugins() -> set[str]:
    settings = HOME / ".claude" / "settings.json"
    if not settings.is_file():
        return set()
    try:
        enabled = json.loads(settings.read_text(encoding="utf-8")).get("enabledPlugins", {})
    except json.JSONDecodeError:
        return set()
    return {k.split("@", 1)[0] for k, v in enabled.items() if v}


# ----------------------------------------------------------------------------- checks


class Check:
    def __init__(self, cid: str, area: str, passed: bool | None, detail: str = ""):
        self.id, self.area, self.passed, self.detail = cid, area, passed, detail

    def as_dict(self) -> dict:
        return {"id": self.id, "area": self.area, "result": self.result, "detail": self.detail}

    @property
    def result(self) -> str:
        return {True: "pass", False: "FAIL", None: "info"}[self.passed]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""


def check_structure(agent: Path) -> list[Check]:
    out = []
    for rel in REQUIRED_FILES:
        out.append(Check(f"F {rel}", "structure", (agent / rel).is_file(), "" if (agent / rel).is_file() else "missing"))
    return out


def check_soul(agent: Path, skills: set[str], agents: set[str]) -> list[Check]:
    soul = _read(agent / "soul.md")
    out = []
    if not soul:
        return [Check("S0 soul readable", "soul", False, "soul.md missing or empty")]
    for cid, pattern in SOUL_SECTIONS.items():
        out.append(Check(cid, "soul", bool(re.search(pattern, soul, re.M | re.I))))
    out.append(Check("S6 cites automationPrinciples", "soul", "automationPrinciples" in soul))
    out.append(Check("S7 states what it never does", "soul", bool(re.search(r"\bnever\b", soul, re.I)),
                     "" if re.search(r"\bnever\b", soul, re.I) else "no explicit non-goals"))
    slash = sorted(set(re.findall(r"`/([a-z][a-z0-9-]+)`", soul)))
    unresolved = [s for s in slash if s not in skills]
    out.append(Check("S8 slash-skill references resolve", "soul", not unresolved if slash else None,
                     f"{len(slash)} referenced; unresolved: {unresolved}" if slash else "no slash skills referenced"))
    named_agents = sorted(a for a in agents if re.search(rf"`{re.escape(a)}`", soul))
    out.append(Check("S9 plugin agents referenced", "soul", None, ", ".join(named_agents) or "none"))
    return out


def _string_lists(tree: ast.AST) -> dict[str, tuple[str, list[str]]]:
    """Name -> (kind, strings) for module-level assignments of list/set literals of strings."""
    found = {}
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            val = node.value
            if isinstance(val, (ast.List, ast.Set)):
                strings = [e.value for e in val.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
                if strings:
                    found[node.targets[0].id] = ("list" if isinstance(val, ast.List) else "set", strings)
    return found


def check_runner(agent: Path) -> list[Check]:
    src = _read(agent / "agent.py")
    out = []
    if not src:
        return [Check("G0 agent.py readable", "guardrails", False, "agent.py missing")]
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [Check("G0 agent.py parses", "guardrails", False, f"SyntaxError line {e.lineno}")]
    out.append(Check("G0 agent.py parses", "guardrails", True))
    out.append(Check("G1 permission callback wired", "guardrails", "can_use_tool=" in src))
    shell_policy = ("denied" if re.search(r"NO_SHELL|doesn't use shell|no shell", src, re.I) else
                    "gated" if re.search(r'tool_name == "PowerShell"|approve\]', src) else None)
    out.append(Check("G2 explicit shell policy", "guardrails", shell_policy is not None, shell_policy or "no shell handling found"))
    out.append(Check("G3 unattended mode refuses", "guardrails", "UNATTENDED" in src and "PermissionResultDeny" in src))
    out.append(Check("G4 write allow-list enforced", "guardrails",
                     bool(re.search(r"WRITABLE|is_writable|is_relative_to\(", src))))
    out.append(Check("G5 model from environment", "guardrails", bool(re.search(r'os\.environ\.get\("[A-Z_]*MODEL"', src))))
    out.append(Check("G6 setting_sources declared", "guardrails", "setting_sources=" in src))
    out.append(Check("G7 transcript logged", "guardrails", "TRANSCRIPT" in src))
    lists = _string_lists(tree)
    leaks = {name: sorted(set(strings) & WRITE_TOOL_NAMES) for name, (kind, strings) in lists.items()
             if kind == "list" and set(strings) & WRITE_TOOL_NAMES}
    out.append(Check("G8 no write/shell tool auto-allowed", "guardrails", not leaks,
                     f"write or shell tools in allow-lists: {leaks}" if leaks else "allow-lists are read-only"))
    out.append(Check("G9 protected paths declared", "guardrails", None,
                     "PROTECTED present" if "PROTECTED" in src else "no PROTECTED list (fine if nothing sensitive is reachable)"))
    has_shell = shell_policy == "gated"
    push_blocked = bool(re.search(r"git\s+push", src)) and "disallowed_tools" in src
    out.append(Check("G10 push blocked in code, not prose", "guardrails", push_blocked if has_shell else None,
                     "disallowed_tools + gate deny" if push_blocked else ("no shell, n/a" if not has_shell else "no git push block found")))
    out.append(Check("G11 tool calls audited", "guardrails", "audit_tool_call" in src or "toolCalls" in src,
                     "" if ("audit_tool_call" in src or "toolCalls" in src) else "auto-allowed tools leave no trail"))
    utf8 = "stdout.reconfigure" in src
    out.append(Check("G12 stdout is UTF-8", "guardrails", utf8,
                     "" if utf8 else "cp1252 console: a non-Latin-1 character in model output crashes the runner mid-turn"))
    return out


def check_memory(agent: Path) -> list[Check]:
    mem = agent / "memory"
    index = _read(mem / "MEMORY.md")
    out = []
    if not index:
        return [Check("M1 memory index", "memory", False, "memory/MEMORY.md missing")]
    out.append(Check("M1 memory index", "memory", True))
    links = re.findall(r"\]\(([^)]+\.md)\)", index)
    missing = [l for l in links if not (mem / l).is_file()]
    out.append(Check("M2 index links resolve", "memory", not missing, f"{len(links)} links; missing: {missing}" if missing else f"{len(links)} links"))
    bad_fm = []
    topics = [p for p in mem.glob("*.md") if p.name != "MEMORY.md"]
    for p in topics:
        head = _read(p)[:600]
        # `type:` may sit at top level or nested under `metadata:` (the Claude Code memory format).
        if not head.startswith("---") or not all(re.search(rf"^\s*{k}:", head, re.M) for k in FRONTMATTER_KEYS):
            bad_fm.append(p.name)
    out.append(Check("M3 topic files have frontmatter", "memory", not bad_fm if topics else None,
                     f"missing name/description/type: {bad_fm}" if bad_fm else f"{len(topics)} topic files"))
    orphans = [p.name for p in topics if p.name not in links]
    out.append(Check("M4 no orphan topic files", "memory", not orphans, f"unlinked: {orphans}" if orphans else ""))
    return out


def check_readme(agent: Path) -> list[Check]:
    rd = _read(agent / "readme.md") or _read(agent / "README.md")
    return [
        Check("R1 status line", "honesty", bool(re.search(r"\*\*Status:?\*\*", rd))),
        Check("R2 verified / not verified stated", "honesty", bool(re.search(r"verified", rd, re.I))),
    ]


def check_secrets(agent: Path) -> list[Check]:
    hits = []
    for p in agent.rglob("*"):
        if p.is_file() and "runs" not in p.parts and "__pycache__" not in p.parts and p.suffix in {".md", ".py", ".txt", ".yaml", ".yml", ".json"}:
            for m in SECRET.finditer(_read(p)):
                hits.append(f"{p.relative_to(agent)}:{_read(p)[:m.start()].count(chr(10)) + 1}")
    return [Check("X1 no plaintext secrets", "secrets", not hits, "; ".join(hits[:5]))]


def check_runtime(agent: Path, do_import: bool) -> list[Check]:
    py = VENVS / agent.name / "Scripts" / "python.exe"
    if not do_import:
        return [Check("T1 imports under its venv", "runtime", None, "skipped (--no-import)")]
    if not py.is_file():
        return [Check("T1 imports under its venv", "runtime", None, f"no venv at {py.parent.parent}")]
    code = "import sys; sys.path.insert(0, '.'); import agent; agent.build_system_prompt(); print('ok')"
    try:
        r = subprocess.run([str(py), "-c", code], cwd=agent, capture_output=True, text=True, timeout=120,
                           env={**dict(__import__('os').environ), "PYTHONDONTWRITEBYTECODE": "1"})
    except subprocess.TimeoutExpired:
        return [Check("T1 imports under its venv", "runtime", False, "timeout")]
    ok = r.returncode == 0 and "ok" in r.stdout
    return [Check("T1 imports under its venv", "runtime", ok, "" if ok else (r.stderr.strip().splitlines() or ["?"])[-1][:160])]


def check_evidence(agent: Path) -> list[Check]:
    runs = agent / "runs"
    sessions = len(list(runs.glob("session*.md"))) if runs.is_dir() else 0
    calls = len(list(runs.glob("toolCalls*.jsonl"))) if runs.is_dir() else 0
    return [Check("E1 evidence of real runs", "evidence", None, f"{sessions} session transcripts, {calls} tool-call logs")]


# ----------------------------------------------------------------------------- report


def inspect(agent: Path, skills: set[str], agents: set[str], do_import: bool) -> dict:
    checks = (check_structure(agent) + check_soul(agent, skills, agents) + check_runner(agent)
              + check_memory(agent) + check_readme(agent) + check_secrets(agent)
              + check_runtime(agent, do_import) + check_evidence(agent))
    passed = sum(c.passed is True for c in checks)
    failed = sum(c.passed is False for c in checks)
    score = round(100 * passed / (passed + failed)) if passed + failed else 0
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"
    return {"agent": agent.name, "date": date.today().isoformat(), "score": score, "grade": grade,
            "passed": passed, "failed": failed, "checks": [c.as_dict() for c in checks]}


def render(result: dict) -> str:
    mark = {"pass": "pass", "FAIL": "**FAIL**", "info": "info"}
    lines = [f"# Inspection — {result['agent']} — {result['date']}", "",
             f"**Score {result['score']}% · grade {result['grade']}** ({result['passed']} pass, {result['failed']} fail; info rows not scored)", "",
             "| Check | Area | Result | Detail |", "|---|---|---|---|"]
    for c in result["checks"]:
        lines.append(f"| {c['id']} | {c['area']} | {mark[c['result']]} | {c['detail']} |")
    fails = [c for c in result["checks"] if c["result"] == "FAIL"]
    lines += ["", "## Recommendations (from failures)", ""]
    lines += [f"- {c['id']}: {c['detail'] or 'add it'}" for c in fails] or ["- none from the deterministic checks; qualitative review is the model's job"]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    do_import = "--no-import" not in argv
    names = [a for a in argv if not a.startswith("--")]
    if "--all" in argv or not names:
        targets = sorted(p.parent for p in REPO.glob("*/agent.py"))
    else:
        targets = [REPO / n for n in names]
    missing = [t for t in targets if not t.is_dir()]
    if missing:
        print("not found:", ", ".join(str(m) for m in missing), file=sys.stderr)
        return 2
    skills, agents = known_skills(), known_agents()
    REPORTS.mkdir(exist_ok=True)
    today = date.today().isoformat()
    summary = ["# Inspection summary — " + today, "", "| Agent | Score | Grade | Fails |", "|---|---|---|---|"]
    for t in targets:
        res = inspect(t, skills, agents, do_import)
        (REPORTS / f"{today}-{t.name}.md").write_text(render(res), encoding="utf-8")
        (REPORTS / f"{today}-{t.name}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        fails = ", ".join(c["id"].split(" ")[0] for c in res["checks"] if c["result"] == "FAIL") or "none"
        summary.append(f"| {t.name} | {res['score']}% | {res['grade']} | {fails} |")
        print(f"{t.name:18s} {res['score']:3d}%  {res['grade']}  fails: {fails}")
    (REPORTS / f"{today}-summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(f"\nreports: {REPORTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
