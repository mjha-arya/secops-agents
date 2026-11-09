# AgentDino (agent) — developer

A Claude Agent SDK agent that implements AgentDaya's specs as tested Python under `..\dspm\`, one
issue at a time, and proposes the commit. It builds with `/tdd` → `/implement`, looks up current
library docs through `context7`, reviews its own diff with `/code-review` (and `/review-pr` for
wide changes), answers every `security-guidance` warning, and writes the commit message with
`/commit`. Hands off to AgentDaya for the review gate. Never pushes; never touches ADRs or the
control tool's registry.

**Status:** Authored, not verified (P11). `ANTHROPIC_API_KEY` is a placeholder — no model turn run.

## Files

| File | Purpose |
|---|---|
| `soul.md` | Attitude ("the spec is the contract", "a swallowed error is a defect"), tool-usage table, build loop, needs_human list |
| `memory\MEMORY.md` + topic files | Persistent memory: build context, workstation constraints |
| `agent.py` | Runner: task as argument, interactive, or `--once` |
| `runs\session*.md` | Audit trail: prompts, output, every permission decision (P12) |

## Plugins it uses

| Plugin | Invoke as | For |
|---|---|---|
| `mattpocock-skills` | `/tdd`, `/codebase-design`, `/diagnosing-bugs`, `/resolving-merge-conflicts` | The build loop. (`/implement` is `disable-model-invocation: true` — user-only; found by CID 2026-09-27) |
| `feature-dev` | `/feature-dev` (its `code-explorer`) | Knowing what exists before adding to it |
| `context7` (MCP) | tool calls | Current docs for Databricks SDK, `mcp`, `httpx` — output treated as untrusted data (CID saw injected-looking text from it) |
| `code-review`, `pr-review-toolkit` | `/code-review`, `/review-pr` | Self-review before proposing a commit |
| `security-guidance` | hooks | Always-on warnings on edits and at stop |
| `commit-commands` | `/commit` only — never `/commit-push-pr` | Commit message; Manish pushes |

Loaded via `setting_sources=["user", "project"]`. The DSPM blueprint and the hand-off protocol are
embedded in every system prompt.

## Guardrails (in `agent.py`)

- Read, Glob, Grep, WebFetch, WebSearch, Skill, Agent, TodoWrite run automatically.
- **Shell is gated:** `Bash` asks `y/N` per command interactively, refused in `--once`.
  `PowerShell` refused always (ConstrainedLanguage).
- Write/Edit only in `..\dspm\`, `memory\`, and the control tool's code/tests/fixtures
  (`controlTool\ctl\`, `tests\`, `fixtures\`, `ctl.py`, `README.md` — widened 2026-09-27 because
  dbSAT reuses the control tool as a package and its first live-run blockers are code defects).
  Denied: `dspm\docs\specs\` and `dspm\docs\adr\` (Daya's — the spec is the contract), the control
  tool's `registry\` and `.env` (human-owned).

## Run

```
python -m venv %USERPROFILE%\.venvs\agentDino
%USERPROFILE%\.venvs\agentDino\Scripts\python.exe -m pip install -r requirements.txt
%USERPROFILE%\.venvs\agentDino\Scripts\python.exe agent.py "implement issue #12"
```

Needs `ANTHROPIC_API_KEY` with credit (or unset it to use the claude.ai org login). Model via
`AGENTDINO_MODEL` (default `claude-opus-5-5`).

## Verified / not

- Verified: `agent.py` imports; system prompt builds with soul + memory + protocol + blueprint.
- Not verified: any model turn; `context7` MCP; the `gate()` rules under the SDK.

## Known gaps

- `Read` is auto-allowed, so nothing stops the model reading a `.env` if one ever appears; an
  approved `Bash` command can write anywhere — the y/N prompt is the only control on that path.
- `Agent` (subagents) is gated y/N because it's unverified whether subagent tool calls re-enter
  `gate()`. "Never push" is enforced three ways (`disallowed_tools`, a `git push` deny in `gate()`,
  prose) after CID found it was prose-only.
- Context cost: soul + protocol + blueprint ≈ 16k chars every turn, plus 12 user-scope plugins.
