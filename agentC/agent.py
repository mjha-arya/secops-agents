"""AgentC: a Claude Agent SDK agent that builds certificate-expiry notification automation.

Usage:
  python agent.py                      interactive session
  python agent.py --phase 1            start or resume a phase from its checklist
  python agent.py "task"               free-form task
  python agent.py --once --phase 1     single turn, then exit; only read-only az commands run
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

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent.parent
WORKSTREAM = WORKSPACE / "certificateExpiryNotifications"
MEMORY_DIR = HERE / "memory"
RUNS_DIR = HERE / "runs"
READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "WebFetch", "WebSearch"]
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
WRITABLE = [WORKSTREAM, HERE, WORKSPACE / "CLAUDE.md"]

# Read-only Azure CLI calls run without asking, so discovery works in --once mode too.
AZ_PREFIX = re.compile(
    r'^"?(?:%ProgramFiles%|C:\\Program Files|/c/Program Files)[\\/]Microsoft SDKs[\\/]Azure[\\/]CLI2[\\/]'
    r'python\.exe"? -IBm azure\.cli (?P<args>.+)$',
    re.IGNORECASE,
)
SHELL_METACHARS = re.compile(r"[;&|<>`$\r\n]")
# Commands that end in list/show but can return secret values.
SENSITIVE = re.compile(r"secret|keys|appsettings|credential|connection-string|publishing|access-token", re.IGNORECASE)

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
        "This is an UNATTENDED run: only read-only az commands will run. Finish the file work, then list "
        "the exact commands Manish should run."
        if UNATTENDED
        else "This is an interactive run: read-only az commands run automatically; Manish approves every other shell command."
    )
    return (
        f"{soul}\n\n---\n\n## Session context\n- Workspace root: {WORKSPACE}\n- Workstream folder: {WORKSTREAM}\n"
        f"- Memory folder: {MEMORY_DIR}\n- {run_mode}\n\n## Memory index\n{memory_index}"
    )


def phase_prompt(number: str) -> str:
    matches = sorted((WORKSTREAM / "phases").glob(f"phase{number}*/task.md")) if number.isdigit() else []
    if len(matches) != 1:
        sys.exit(f"Expected one phases\\phase{number}*\\task.md, found {len(matches)}.")
    folder = matches[0].parent
    return (
        f"Run Phase {number}. Read {folder / 'task.md'} and {folder / 'checklist.md'}. Resume at the first "
        "unticked step, do only the steps marked AgentC, and stop at the next needs_human gate with a short "
        "summary of what you did and what Manish must do next."
    )


def is_read_only_az(command: str) -> bool:
    match = AZ_PREFIX.match(command.strip())
    if not match or SHELL_METACHARS.search(command):
        return False
    args = match.group("args")
    if SENSITIVE.search(args):
        return False
    words = []
    for token in args.split():
        if token.startswith("-"):
            break
        words.append(token)
    if words[:2] == ["bicep", "build"] or words[:3] == ["deployment", "group", "what-if"]:
        return True
    if words[:1] == ["rest"]:
        return re.search(r"--method\s+get\b", args, re.IGNORECASE) is not None
    return bool(words) and words[-1] in {"list", "show"}


def is_writable(target: Path) -> bool:
    return any(target == p or target.is_relative_to(p) for p in WRITABLE)


async def gate(tool_name: str, tool_input: dict, context: ToolPermissionContext):
    if tool_name in WRITE_TOOLS:
        target = Path(tool_input.get("file_path") or tool_input.get("notebook_path") or "").resolve()
        if is_writable(target):
            log(f"- write allowed: `{target}`")
            return PermissionResultAllow()
        log(f"- write denied (outside workstream): `{target}`")
        return PermissionResultDeny(message=f"Writes are limited to {WORKSTREAM}, {HERE} and CLAUDE.md.")

    detail = tool_input.get("command") or json.dumps(tool_input)[:400]
    if tool_name in SHELL_TOOLS and is_read_only_az(detail):
        log(f"- auto-allowed read-only az: `{detail}`")
        return PermissionResultAllow()
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
        model=os.environ.get("AGENTC_MODEL", "claude-opus-5-5"),
        cwd=str(WORKSPACE),
        setting_sources=["project"],
        allowed_tools=READ_ONLY_TOOLS,
        can_use_tool=gate,
    )
    args = [a for a in sys.argv[1:] if a != "--once"]
    if "--phase" in args:
        i = args.index("--phase")
        prompt = phase_prompt(args[i + 1] if i + 1 < len(args) else "")
        args = args[:i] + args[i + 2:]
        if args:
            prompt += "\n\nExtra instructions from Manish: " + " ".join(args)
    else:
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
