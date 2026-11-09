"""AgentDino: a Claude Agent SDK agent that develops the DSPM from AgentDaya's specs.

Usage:
  python agent.py "implement issue #12 (discover: inventory sweep)"   one task, then interactive follow-ups
  python agent.py                                                     interactive session
  python agent.py --once "<task>"                                     single turn, then exit; shell refused

AgentDino writes code and tests under dspm/ using the installed plugins (feature-dev, code-review,
pr-review-toolkit, security-guidance, mattpocock-skills, commit-commands, context7). Shell commands
are gated y/N in interactive runs and refused unattended. It never pushes, never touches dspm/docs/adr,
the control tool's registry or .env. See soul.md and ../program/readme.md.
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
BLUEPRINT = REPO / "agentDaya" / "knowledge" / "dspmBlueprint.md"
PROGRAM_DIR = REPO / "program"
MEMORY_DIR = HERE / "memory"
RUNS_DIR = HERE / "runs"

READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "WebFetch", "WebSearch"]
# Skill runs plugin skills (/tdd, /implement, /code-review, /commit); Agent runs reviewer agents.
PLUGIN_TOOLS = ["Skill", "TodoWrite"]  # Agent is gated: unverified whether subagent calls re-enter gate()
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
# Decision 2026-09-27 (program/decisions.md): dbSAT reuses the control tool as a package, so Dino
# may change its code, tests and fixtures - with tests - but never its registry or .env.
WRITABLE = [DSPM_DIR, MEMORY_DIR, CONTROL_TOOL / "ctl", CONTROL_TOOL / "tests", CONTROL_TOOL / "fixtures",
            CONTROL_TOOL / "ctl.py", CONTROL_TOOL / "README.md"]
# Specs and ADRs are Daya's (the spec is the contract Dino builds to, so Dino can't edit it);
# the control tool's registry and .env are a human's.
PROTECTED = [DSPM_DIR / "docs" / "specs", DSPM_DIR / "docs" / "adr", CONTROL_TOOL / "registry",
             CONTROL_TOOL / ".env"]

UNATTENDED = "--once" in sys.argv
FLAGS = {"--once", "--claudeai"}
if "--claudeai" in sys.argv:
    # Bill this run to the claude.ai org login instead of the API key: the CLI falls back to the
    # login whenever no key is present in the process environment.
    os.environ.pop("ANTHROPIC_API_KEY", None)
RUNS_DIR.mkdir(exist_ok=True)
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
    protocol = (PROGRAM_DIR / "readme.md").read_text(encoding="utf-8")
    blueprint = BLUEPRINT.read_text(encoding="utf-8")
    memory_index = (MEMORY_DIR / "MEMORY.md").read_text(encoding="utf-8")
    run_mode = (
        "This is an UNATTENDED run: single turn, then exit. Shell commands are refused - finish "
        "the file work, then list the exact test commands Manish should run."
        if UNATTENDED
        else "This is an interactive run: Manish approves each shell command."
    )
    return (
        f"{soul}\n\n---\n\n## Session context\n- Repo root (git): {REPO}\n- DSPM code: {DSPM_DIR}\n"
        f"- Control tool (read-only for you): {CONTROL_TOOL}\n- Program folder: {PROGRAM_DIR}\n"
        f"- Memory folder: {MEMORY_DIR}\n- {run_mode}\n\n## Memory index\n{memory_index}\n\n---\n\n"
        f"{protocol}\n\n---\n\n{blueprint}"
    )


def _under(target: Path, roots: list[Path]) -> bool:
    return any(target == p or target.is_relative_to(p) for p in roots)


async def gate(tool_name: str, tool_input: dict, context: ToolPermissionContext):
    if tool_name == "PowerShell":
        log("- denied: PowerShell (ConstrainedLanguage on this estate)")
        return PermissionResultDeny(message="PowerShell runs in ConstrainedLanguage mode here. Use Bash with Python.")
    if tool_name in WRITE_TOOLS:
        target = Path(tool_input.get("file_path") or tool_input.get("notebook_path") or "").resolve()
        if _under(target, PROTECTED):
            log(f"- write denied (protected): `{target}`")
            return PermissionResultDeny(message="Specs and ADRs are AgentDaya's; the control tool's registry and .env are changed by a human. Hand the question back in your packet.")
        if _under(target, WRITABLE):
            log(f"- write allowed: `{target}`")
            return PermissionResultAllow()
        log(f"- write denied (outside dspm/memory): `{target}`")
        return PermissionResultDeny(message=f"Writes are limited to {DSPM_DIR} and {MEMORY_DIR}.")
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
    options = ClaudeAgentOptions(
        system_prompt={"type": "preset", "preset": "claude_code", "append": build_system_prompt()},
        model=os.environ.get("AGENTDINO_MODEL", "claude-opus-5-5"),
        cwd=str(REPO),
        # Harness-enforced before any prompt or gate: nobody pushes, and PowerShell is CLM here.
        disallowed_tools=["PowerShell", "Bash(git push:*)", "Bash(gh pr create:*)", "Bash(git remote:*)"],
        # "user" loads ~/.claude/settings.json, where the plugins are enabled at user scope.
        setting_sources=["user", "project"],
        allowed_tools=READ_ONLY_TOOLS + PLUGIN_TOOLS,
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
