"""AgentDaya: the DSPM's technical lead, and the read-only operator of the Databricks Control Tool.

Usage:
  python agent.py "phase 0: write ADR-0001"       one task, then interactive follow-ups
  python agent.py                                 interactive session
  python agent.py --once "<task>"                 single turn, then exit; shell is refused

Two jobs, one agent. As architect it specs the DSPM (dspm/docs/specs, dspm/docs/adr) and reviews
what AgentDino builds, using the installed Claude Code plugins (feature-dev, code-review,
pr-review-toolkit, security-guidance). As operator it reaches ctl.py only through a local MCP
server that builds allow-listed, read-only argument vectors. Shell commands are gated y/N in
interactive runs and refused unattended. Writes are limited to dspm/docs, dspm/knowledge,
program/, proposals/, memory/ and knowledge/ - the code under dspm/ is Dino's. It never applies a
change to a real system, never promotes a control and never edits the registry. See soul.md.
"""
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolPermissionContext,
    ToolUseBlock,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252; model output is UTF-8

HERE = Path(__file__).resolve().parent
REPO = HERE.parent  # myAgents - the git repo root; dspm/ lives here
WORKSPACE = REPO.parent  # secopsAutomationOperations
CONTROL_TOOL = WORKSPACE / "secopsCurrentProjects" / "databricks" / "controlTool"
DSPM_DIR = REPO / "dspm"
KNOWLEDGE_DIR = HERE / "knowledge"
MEMORY_DIR = HERE / "memory"
PROPOSALS_DIR = HERE / "proposals"
RUNS_DIR = HERE / "runs"
MCP_SERVER = HERE / "mcp" / "dctMcp.py"

READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "WebFetch", "WebSearch"]
# Skill runs plugin commands (/feature-dev, /code-review, ...); Agent runs plugin reviewer agents.
PLUGIN_TOOLS = ["Skill", "TodoWrite"]  # Agent is gated: unverified whether subagent calls re-enter gate()
DCT_TOOLS = [
    f"mcp__dct__{name}" for name in (
        "validate", "list_controls", "explain_control", "run_pipeline", "position", "drift",
        "preflight", "list_runs", "read_run_artifact", "read_evidence", "registry_file",
    )
]
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
PROGRAM_DIR = REPO / "program"
# Daya writes specs, ADRs and knowledge; AgentDino writes the code under dspm/.
WRITABLE = [DSPM_DIR / "docs", DSPM_DIR / "knowledge", PROGRAM_DIR / "decisions.md", PROPOSALS_DIR, MEMORY_DIR, KNOWLEDGE_DIR]
# The registry is the contract; a human commits changes to it. The tool's code and .env are not
# this agent's to touch either.
PROTECTED = [CONTROL_TOOL / "registry", CONTROL_TOOL / ".env", CONTROL_TOOL / "ctl", CONTROL_TOOL / "ctl.py"]

UNATTENDED = "--once" in sys.argv
FLAGS = {"--once", "--claudeai"}
if "--claudeai" in sys.argv:
    # Bill this run to the claude.ai org login instead of the API key: the CLI falls back to the
    # login whenever no key is present in the process environment.
    os.environ.pop("ANTHROPIC_API_KEY", None)
for d in (RUNS_DIR, PROPOSALS_DIR, DSPM_DIR):
    d.mkdir(exist_ok=True)
TRANSCRIPT = RUNS_DIR / f"session{datetime.now():%Y%m%d%H%M%S}.md"


def log(text: str) -> None:
    with open(TRANSCRIPT, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def audit_tool_call(name: str, tool_input) -> None:
    """Every tool call, including auto-allowed ones that never reach gate(), leaves a trail (P12)."""
    summary = json.dumps(tool_input, default=str)[:400]
    log(f"- tool {name}: `{summary}`")
    with open(RUNS_DIR / f"toolCalls{datetime.now():%Y%m%d}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), "tool": name, "input": summary}) + "\n")


def build_system_prompt() -> str:
    soul = (HERE / "soul.md").read_text(encoding="utf-8")
    blueprint = (KNOWLEDGE_DIR / "dspmBlueprint.md").read_text(encoding="utf-8")
    memory_index = (MEMORY_DIR / "MEMORY.md").read_text(encoding="utf-8")
    run_mode = (
        "This is an UNATTENDED run: single turn, then exit. Shell commands are refused - finish "
        "the file work, then list the exact verification commands Manish should run."
        if UNATTENDED
        else "This is an interactive run: Manish approves each shell command."
    )
    protocol = (PROGRAM_DIR / "readme.md").read_text(encoding="utf-8")
    return (
        f"{soul}\n\n---\n\n## Session context\n- Repo root (git): {REPO}\n- DSPM code (Dino writes it): {DSPM_DIR}\n"
        f"- Control tool: {CONTROL_TOOL}\n- Program folder: {PROGRAM_DIR}\n- Proposals folder: {PROPOSALS_DIR}\n"
        f"- Memory folder: {MEMORY_DIR}\n- Knowledge folder: {KNOWLEDGE_DIR}\n- {run_mode}\n"
        f"\n## Memory index\n{memory_index}\n\n---\n\n{protocol}\n\n---\n\n{blueprint}"
    )


def _under(target: Path, roots: list[Path]) -> bool:
    return any(target == p or target.is_relative_to(p) for p in roots)


async def gate(tool_name: str, tool_input: dict, context: ToolPermissionContext):
    if tool_name == "PowerShell":
        log("- denied: PowerShell (ConstrainedLanguage on this estate)")
        return PermissionResultDeny(message="PowerShell runs in ConstrainedLanguage mode here. Use Bash with Python, not PowerShell.")
    if tool_name in WRITE_TOOLS:
        target = Path(tool_input.get("file_path") or tool_input.get("notebook_path") or "").resolve()
        if _under(target, PROTECTED):
            log(f"- write denied (registry/tool code is human-owned): `{target}`")
            return PermissionResultDeny(message="The registry, .env and the control tool's code are changed by a human in a reviewed change. Write a proposal under proposals/ instead.")
        if _under(target, WRITABLE):
            log(f"- write allowed: `{target}`")
            return PermissionResultAllow()
        if _under(target, [DSPM_DIR]):
            log(f"- write denied (code is Dino's): `{target}`")
            return PermissionResultDeny(message="AgentDino writes the code under dspm/. Write the spec in dspm/docs/specs and hand it off.")
        log(f"- write denied (outside dspm docs/program/proposals/memory/knowledge): `{target}`")
        return PermissionResultDeny(message=f"Writes are limited to {DSPM_DIR / 'docs'}, {DSPM_DIR / 'knowledge'}, {PROGRAM_DIR / 'decisions.md'}, {PROPOSALS_DIR}, {MEMORY_DIR} and {KNOWLEDGE_DIR}. PRDs are Nolan's; roadmap and status are Pradyuman's.")
    if tool_name == "Bash" and re.search(r"\bgit\s+push\b|\bgh\s+pr\s+create\b|\bgit\s+remote\b", tool_input.get("command") or ""):
        log(f"- denied (Manish pushes): `{tool_input.get('command')}`")
        return PermissionResultDeny(message="Manish pushes. Propose the commit and stop.")
    detail = tool_input.get("command") or json.dumps(tool_input)[:400]
    if UNATTENDED:
        log(f"- denied (unattended) {tool_name}: `{detail}`")
        return PermissionResultDeny(message="Unattended run: list this command for Manish to run instead.")
    try:
        answer = await asyncio.to_thread(input, f"\n[approve] {tool_name}: {detail}\nAllow? [y/N] ")
    except EOFError:
        log(f"- denied (no interactive stdin) {tool_name}: `{detail}`")
        return PermissionResultDeny(message="No interactive approver available: this action needs a human.")
    approved = answer.strip().lower() == "y"
    log(f"- {'approved' if approved else 'declined'} {tool_name}: `{detail}`")
    if approved:
        return PermissionResultAllow()
    return PermissionResultDeny(message="Manish declined this action. Ask before trying an alternative.")


def mcp_servers() -> dict:
    servers = {"dct": {"command": sys.executable, "args": [str(MCP_SERVER)]}}
    # Databricks managed MCP is a config slot (dspm/knowledge/connectors.yaml): attached only when
    # both variables are present, so a fixture-only session never carries a live connector.
    url, token = os.environ.get("DATABRICKS_MCP_URL"), os.environ.get("DATABRICKS_MCP_TOKEN")
    if url and token:
        servers["databricks"] = {"type": "http", "url": url, "headers": {"Authorization": f"Bearer {token}"}}
    return servers


async def run_turn(client: ClaudeSDKClient, prompt: str) -> None:
    log(f"\n## Manish\n{prompt}\n\n## Agent")
    await client.query(prompt)
    async for msg in client.receive_response():
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    log(block.text)  # log first: the transcript must survive a console that can't render the text
                    print(block.text)
                elif isinstance(block, ToolUseBlock):
                    print(f"  > {block.name}")
                    audit_tool_call(block.name, block.input)
        elif isinstance(msg, ResultMessage):
            cost = f"${msg.total_cost_usd:.2f}" if msg.total_cost_usd else "n/a"
            print(f"\n[turn done | cost {cost}]")
            log(f"\n_turn cost: {cost}_")


async def main() -> None:
    servers = mcp_servers()
    options = ClaudeAgentOptions(
        system_prompt={"type": "preset", "preset": "claude_code", "append": build_system_prompt()},
        model=os.environ.get("AGENTDAYA_MODEL", "claude-opus-5-5"),
        cwd=str(REPO),
        # Harness-enforced before any prompt or gate: nobody pushes, and PowerShell is CLM here.
        disallowed_tools=["PowerShell", "Bash(git push:*)", "Bash(gh pr create:*)", "Bash(git remote:*)"],
        # "user" loads ~/.claude/settings.json, where the six plugins are enabled at user scope.
        setting_sources=["user", "project"],
        mcp_servers=servers,
        allowed_tools=READ_ONLY_TOOLS + PLUGIN_TOOLS + DCT_TOOLS
        + ([f"mcp__databricks__*"] if "databricks" in servers else []),
        can_use_tool=gate,
    )
    args = [a for a in sys.argv[1:] if a not in FLAGS]
    log(f"_auth: {'claude.ai login' if 'ANTHROPIC_API_KEY' not in os.environ else 'API key'}_")
    prompt = " ".join(args) if args else await asyncio.to_thread(input, "You: ")
    async with ClaudeSDKClient(options=options) as client:
        while prompt.strip() and prompt.strip().lower() not in {"exit", "quit"}:
            await run_turn(client, prompt)
            if UNATTENDED:
                break
            prompt = await asyncio.to_thread(input, "\nYou: ")
    print(f"Transcript: {TRANSCRIPT}")


if __name__ == "__main__":
    asyncio.run(main())
