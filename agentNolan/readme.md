# AgentNolan (agent) — product manager

A Claude Agent SDK agent that turns an objective in `..\program\objective.md` into a PRD
(`..\program\prd\<objective>.md`) with users, outcomes, scope, testable acceptance criteria,
release slices and open questions, then cuts it into stories and files them as GitHub issues.
Hands off to AgentPradyuman. Never designs, plans delivery or writes code.

**Status:** Authored, not verified (P11). `ANTHROPIC_API_KEY` is a placeholder — no model turn run.

## Files

| File | Purpose |
|---|---|
| `soul.md` | Attitude, tool-usage table, PRD workflow, needs_human list |
| `memory\MEMORY.md` + topic files | Persistent memory: product context, workstation constraints |
| `agent.py` | Runner: task as argument, interactive, or `--once` |
| `runs\session*.md` | Audit trail: prompts, output, permission decisions (P12) |

## Skills and plugins it uses

| From | What | For |
|---|---|---|
| `mattpocock-skills` plugin | `/grilling` | Interrogating the objective. (`grill-me`, `to-questionnaire`, `to-spec`, `to-tickets` are `disable-model-invocation: true` — user-only, the agent can't call them; found by CID 2026-09-27) |
| workspace skill | `tech-pdp-spec-writer` | The PRD in Contoso's PDP spec shape |
| workspace skill | `general-reasoning-council` | Prioritisation with a real trade-off |
| workspace skill | `create-documentation` | Runbook-style docs a story needs |
| `github` plugin (MCP) | issues, labels | Filing stories — each write approved by Manish; needs `GITHUB_PERSONAL_ACCESS_TOKEN` |

Loaded via `setting_sources=["user", "project"]` (user-scope plugins + `~/.claude/skills`).

## Guardrails (in `agent.py`)

- Read, Glob, Grep, WebFetch, WebSearch, Skill, Agent, TodoWrite run automatically.
- **No shell** — `Bash` and `PowerShell` are refused.
- Write/Edit only in `..\program\prd\`, `..\program\decisions.md` and `memory\` — `roadmap.md`
  and `status.md` are Pradyuman's, `objective.md` is Manish's (narrowed after CID review, 2026-09-27).
- Every other tool (including GitHub MCP writes) asks `y/N`; refused in `--once`.

## Run

```
python -m venv %USERPROFILE%\.venvs\agentNolan
%USERPROFILE%\.venvs\agentNolan\Scripts\python.exe -m pip install -r requirements.txt
%USERPROFILE%\.venvs\agentNolan\Scripts\python.exe agent.py "write the PRD for the active objective"
```

Needs `ANTHROPIC_API_KEY` with credit (or unset it to use the claude.ai org login). Model via
`AGENTNOLAN_MODEL` (default `claude-opus-5-5`). `GITHUB_PERSONAL_ACCESS_TOKEN` for the tracker.

## Verified / not

- Verified: `agent.py` imports; system prompt builds with soul + memory + hand-off protocol.
- Not verified: any model turn; GitHub MCP tool names; that `gate()` holds under the SDK.

## Known gaps

- `Read` is auto-allowed, so nothing stops the model reading a `.env` if one ever appears in the repo.
- `Agent` (subagents) is gated y/N because it's unverified whether subagent tool calls re-enter
  `gate()`; `/feature-dev`-style skills that spawn agents will prompt.
- Context cost: 12 user-scope plugins are loaded; `pr-review-toolkit` alone adds ~1.6k always-on
  tokens. Disable plugins this agent doesn't use if sessions get expensive.
