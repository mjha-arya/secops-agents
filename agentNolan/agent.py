"""AgentNolan: a Claude Agent SDK agent that acts as product manager for the Databricks security programme.

Usage:
  python agent.py "write the PRD for the active objective"   one task, then interactive follow-ups
  python agent.py                                            interactive session
  python agent.py --once "<task>"                            single turn, then exit

AgentNolan turns program/objective.md into a PRD under program/prd/ and cuts it into stories. It has
no shell tool, writes only to program/ and its own memory/, and any GitHub issue write is approved by
Manish interactively (refused unattended). See soul.md and ../program/readme.md.
"""
import asyncio
import json
import os
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
REPO = HERE.parent  # myAgents - the git repo root
PROGRAM_DIR = REPO / "program"
MEMORY_DIR = HERE / "memory"
RUNS_DIR = HERE / "runs"
READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "WebFetch", "WebSearch"]
# Skill runs plugin and workspace skills (/grill-me, /to-spec, tech-pdp-spec-writer, ...).
PLUGIN_TOOLS = ["Skill", "TodoWrite"]  # Agent is gated: unverified whether subagent calls re-enter gate()
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
NO_SHELL = {"Bash", "PowerShell"}
# Nolan owns the PRDs and may append decisions; roadmap.md and status.md are Pradyuman's,
# objective.md is Manish's.
WRITABLE = [PROGRAM_DIR / "prd", PROGRAM_DIR / "decisions.md", MEMORY_DIR]

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
    memory_index = (MEMORY_DIR / "MEMORY.md").read_text(encoding="utf-8")
    run_mode = (
        "This is an UNATTENDED run: single turn, then exit. GitHub writes are refused - put the "
        "stories in the PRD instead and say so."
        if UNATTENDED
        else "This is an interactive run: Manish approves each GitHub write."
    )
    return (
        f"{soul}\n\n---\n\n## Session context\n- Repo root (git): {REPO}\n- Program folder: {PROGRAM_DIR}\n"
        f"- Memory folder: {MEMORY_DIR}\n- {run_mode}\n\n## Memory index\n{memory_index}\n\n---\n\n{protocol}"
    )


def _under(target: Path, roots: list[Path]) -> bool:
    return any(target == p or target.is_relative_to(p) for p in roots)


async def gate(tool_name: str, tool_input: dict, context: ToolPermissionContext):
    if tool_name in NO_SHELL:
        log(f"- denied (AgentNolan has no shell): {tool_name}")
        return PermissionResultDeny(message="AgentNolan doesn't use shell commands. List the command for Manish instead.")
    if tool_name in WRITE_TOOLS:
        target = Path(tool_input.get("file_path") or tool_input.get("notebook_path") or "").resolve()
        if _under(target, WRITABLE):
            log(f"- write allowed: `{target}`")
            return PermissionResultAllow()
        log(f"- write denied (outside program/memory): `{target}`")
        return PermissionResultDeny(message=f"Writes are limited to {PROGRAM_DIR / 'prd'}, {PROGRAM_DIR / 'decisions.md'} and {MEMORY_DIR}. Roadmap and status are Pradyuman's, objective.md is Manish's, architecture Daya's, code Dino's.")
    detail = json.dumps(tool_input)[:400]
    if UNATTENDED:
        log(f"- denied (unattended) {tool_name}: `{detail}`")
        return PermissionResultDeny(message="Unattended run: this action needs a human. Record it in the PRD and say so.")
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
        model=os.environ.get("AGENTNOLAN_MODEL", "claude-opus-5-5"),
        cwd=str(REPO),
        # Harness-enforced before any prompt or gate: no shell at all for this agent.
        disallowed_tools=["Bash", "PowerShell"],
        # "user" loads ~/.claude/settings.json: the plugins (mattpocock-skills, github, ...) and the
        # workspace skills (tech-pdp-spec-writer, general-reasoning-council, create-documentation).
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
