"""AgentD: a Claude Agent SDK agent that investigates Microsoft Defender XDR alerts and incidents.

Usage:
  python agent.py "https://security.microsoft.com/alerts/xyz?tid=..."   investigate one alert/incident link
  python agent.py                                                       interactive session
  python agent.py --once "<link>"                                      single turn, then exit

AgentD is strictly read-only: it never writes back to Defender, Sentinel or Purview, and never
takes any containment or remediation action. See soul.md for the investigation workflow.
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

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
WORKSTREAM = WORKSPACE / "defenderAlertInvestigation"
MEMORY_DIR = HERE / "memory"
RUNS_DIR = HERE / "runs"
MCP_SERVER = HERE / "mcp" / "defenderMcp.py"
READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "WebFetch", "WebSearch"]
DEFENDER_TOOLS = [
    "mcp__defender__resolve_link",
    "mcp__defender__get_alert",
    "mcp__defender__get_incident",
    "mcp__defender__list_incident_alerts",
]
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
NO_SHELL = {"Bash", "PowerShell"}
WRITABLE = [WORKSTREAM, MEMORY_DIR, WORKSPACE / "CLAUDE.md"]

UNATTENDED = "--once" in sys.argv
RUNS_DIR.mkdir(exist_ok=True)
TRANSCRIPT = RUNS_DIR / f"session{datetime.now():%Y%m%d%H%M%S}.md"


def log(text: str) -> None:
    with open(TRANSCRIPT, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def build_system_prompt() -> str:
    soul = (HERE / "soul.md").read_text(encoding="utf-8")
    memory_index = (MEMORY_DIR / "MEMORY.md").read_text(encoding="utf-8")
    run_mode = (
        "This is an UNATTENDED run: single turn, then exit."
        if UNATTENDED
        else "This is an interactive run."
    )
    return (
        f"{soul}\n\n---\n\n## Session context\n- Workspace root: {WORKSPACE}\n"
        f"- Workstream folder: {WORKSTREAM}\n- Memory folder: {MEMORY_DIR}\n- {run_mode}\n"
        f"\n## Memory index\n{memory_index}"
    )


def is_writable(target: Path) -> bool:
    return any(target == p or target.is_relative_to(p) for p in WRITABLE)


async def gate(tool_name: str, tool_input: dict, context: ToolPermissionContext):
    if tool_name in NO_SHELL:
        log(f"- denied (AgentD is investigate-only, no shell): {tool_name}")
        return PermissionResultDeny(message="AgentD doesn't use shell commands. Use the defender MCP tools, Read, Glob, Grep or WebFetch instead.")
    if tool_name in WRITE_TOOLS:
        target = Path(tool_input.get("file_path") or tool_input.get("notebook_path") or "").resolve()
        if is_writable(target):
            log(f"- write allowed: `{target}`")
            return PermissionResultAllow()
        log(f"- write denied (outside workstream/memory): `{target}`")
        return PermissionResultDeny(message=f"Writes are limited to {WORKSTREAM}, {MEMORY_DIR} and CLAUDE.md.")
    detail = json.dumps(tool_input)[:400]
    if UNATTENDED:
        log(f"- denied (unattended) {tool_name}: `{detail}`")
        return PermissionResultDeny(message="Unattended run: this action needs a human.")
    answer = await asyncio.to_thread(input, f"\n[approve] {tool_name}: {detail}\nAllow? [y/N] ")
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
                    print(block.text)
                    log(block.text)
                elif isinstance(block, ToolUseBlock):
                    print(f"  > {block.name}")
        elif isinstance(msg, ResultMessage):
            cost = f"${msg.total_cost_usd:.2f}" if msg.total_cost_usd else "n/a"
            print(f"\n[turn done | cost {cost}]")
            log(f"\n_turn cost: {cost}_")


async def main() -> None:
    options = ClaudeAgentOptions(
        system_prompt={"type": "preset", "preset": "claude_code", "append": build_system_prompt()},
        model=os.environ.get("AGENTD_MODEL", "claude-opus-5-5"),
        cwd=str(WORKSPACE),
        setting_sources=["project"],
        mcp_servers={"defender": {"command": sys.executable, "args": [str(MCP_SERVER)]}},
        allowed_tools=READ_ONLY_TOOLS + DEFENDER_TOOLS,
        can_use_tool=gate,
    )
    args = [a for a in sys.argv[1:] if a != "--once"]
    prompt = " ".join(args) if args else await asyncio.to_thread(input, "Alert/incident link: ")
    if prompt.strip() and not prompt.strip().lower().startswith(("exit", "quit")):
        prompt = f"Investigate this Defender alert/incident: {prompt}"
    async with ClaudeSDKClient(options=options) as client:
        while prompt.strip() and prompt.strip().lower() not in {"exit", "quit"}:
            await run_turn(client, prompt)
            if UNATTENDED:
                break
            prompt = await asyncio.to_thread(input, "\nYou: ")
    print(f"Transcript: {TRANSCRIPT}")


if __name__ == "__main__":
    asyncio.run(main())
