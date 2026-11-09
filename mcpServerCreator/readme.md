# MCP Server Creator (agent)

A Claude Agent SDK agent that designs and builds read-only MCP servers for SecOps, starting with
Purview and then Defender.

**Status:** Authored. The SDK import and options are validated. The first real run was building
`purviewMcp\`.

## Files

| File | Purpose |
|---|---|
| `soul.md` | Attitude, point of view and problem-solving steps. Appended to the Claude Code system prompt |
| `memory\MEMORY.md` + topic files | Persistent memory. The index is loaded every session, and the agent updates it |
| `agent.py` | Runner: interactive REPL, or `--once` for one unattended task |
| `runs\session*.md` | Audit trail: prompts, agent output and every permission decision (P12) |

## Guardrails (in `agent.py`)

- Read, Glob, Grep, WebFetch and WebSearch run automatically.
- Write and Edit are allowed **only inside `secopsAutomationOperations\`**.
- Shell and anything else asks you `y/N` each time. It is refused automatically in `--once` mode.
- The workspace `CLAUDE.md` is loaded through `setting_sources=["project"]`.

## Run

```
python -m venv %USERPROFILE%\.venvs\mcpServerCreator
%USERPROFILE%\.venvs\mcpServerCreator\Scripts\python.exe -m pip install -r requirements.txt
%USERPROFILE%\.venvs\mcpServerCreator\Scripts\python.exe agent.py
```

This needs `ANTHROPIC_API_KEY`. To change the model, set `MCP_CREATOR_MODEL` (the default is
`claude-opus-5-5`).
