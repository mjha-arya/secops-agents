"""MCP Server Creator: a Claude Agent SDK agent that designs and builds SecOps MCP servers.

Usage:
  python agent.py                      interactive session
  python agent.py "build the Defender MCP"
  python agent.py --once "task"        single task, then exit; shell commands are refused
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
MEMORY_DIR = HERE / "memory"
RUNS_DIR = HERE / "runs"
READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "WebFetch", "WebSearch"]
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

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
        "This is an UNATTENDED run: shell commands will be refused. Finish the file work, then list the "
        "exact verification commands Manish should run."
        if UNATTENDED
        else "This is an interactive run: Manish approves each shell command."
    )
    return (
        f"{soul}\n\n---\n\n## Session context\n- Workspace root: {WORKSPACE}\n"
        f"- Memory folder: {MEMORY_DIR}\n- {run_mode}\n\n## Memory index\n{memory_index}"
    )


async def gate(tool_name: str, tool_input: dict, context: ToolPermissionContext):
    if tool_name in WRITE_TOOLS:
        target = Path(tool_input.get("file_path") or tool_input.get("notebook_path") or "").resolve()
        if target.is_relative_to(WORKSPACE):
            log(f"- write allowed: `{target}`")
            return PermissionResultAllow()
        log(f"- write denied (outside workspace): `{target}`")
        return PermissionResultDeny(message=f"Writes are limited to {WORKSPACE}.")

    detail = tool_input.get("command") or json.dumps(tool_input)[:400]
    if UNATTENDED:
        log(f"- denied (unattended) {tool_name}: `{detail}`")
        return PermissionResultDeny(message="Unattended run: list this command for Manish to run instead.")
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
        model=os.environ.get("MCP_CREATOR_MODEL", "claude-opus-5-5"),
        cwd=str(WORKSPACE),
        setting_sources=["project"],
        allowed_tools=READ_ONLY_TOOLS,
        can_use_tool=gate,
    )
    args = [a for a in sys.argv[1:] if a != "--once"]
    prompt = " ".join(args) or await asyncio.to_thread(input, "You: ")
    async with ClaudeSDKClient(options=options) as client:
        while prompt.strip() and prompt.strip().lower() not in {"exit", "quit"}:
            await run_turn(client, prompt)
            if UNATTENDED:
                break
            prompt = await asyncio.to_thread(input, "\nYou: ")
    print(f"Transcript: {TRANSCRIPT}")


if __name__ == "__main__":
    asyncio.run(main())
