# AgentPradyuman (agent) — program manager

A Claude Agent SDK agent that turns AgentNolan's PRD into a delivery plan: `..\program\roadmap.md`
(milestones = DSPM blueprint phases, each with its gate), workstreams, dependencies and RAID;
GitHub milestones/issues/project via the `github` plugin; a living status page via
`/project-artifact`; and `..\program\status.md` that always leads with blockers. Writes the
hand-off packets to AgentDaya (design) and AgentDino (build). Never writes requirements,
architecture or code.

**Status:** Authored, not verified (P11). `ANTHROPIC_API_KEY` is a placeholder — no model turn run.

## Files

| File | Purpose |
|---|---|
| `soul.md` | Attitude ("gates are evidence, not dates"), tool-usage table, planning workflow, needs_human list |
| `memory\MEMORY.md` + topic files | Persistent memory: program context, workstation constraints |
| `agent.py` | Runner: task as argument, interactive, or `--once` |
| `runs\session*.md` | Audit trail: prompts, output, permission decisions (P12) |

## Skills and plugins it uses

| From | What | For |
|---|---|---|
| `project-artifact` plugin | `/project-artifact` | Living status page: overview, success criteria, workstream sequence |
| `github` plugin (MCP) | milestones, issues, projects | The tracker — each write approved by Manish; needs `GITHUB_PERSONAL_ACCESS_TOKEN` |
| workspace skill | `DYUAQ` | Play back + questions before planning |
| workspace skill | `next-steps-please` | Deciding the next hand-offs |
| `claude-md-management` plugin | audit/capture | Keeping the repo maps (CLAUDE.md, readmes) current — the "stale map" rule |

## Guardrails (in `agent.py`)

- Read, Glob, Grep, WebFetch, WebSearch, Skill, Agent, TodoWrite run automatically.
- **No shell** — `Bash` and `PowerShell` are refused.
- Write/Edit only in `..\program\roadmap.md`, `status.md`, `decisions.md` and `memory\` — PRDs
  are Nolan's, `objective.md` is Manish's (narrowed after CID review, 2026-09-27).
- Every other tool (including GitHub MCP writes) asks `y/N`; refused in `--once`.

## Run

```
python -m venv %USERPROFILE%\.venvs\agentPradyuman
%USERPROFILE%\.venvs\agentPradyuman\Scripts\python.exe -m pip install -r requirements.txt
%USERPROFILE%\.venvs\agentPradyuman\Scripts\python.exe agent.py "plan the delivery for the active PRD"
```

Needs `ANTHROPIC_API_KEY` with credit (or unset it to use the claude.ai org login). Model via
`AGENTPRADYUMAN_MODEL` (default `claude-opus-5-5`). `GITHUB_PERSONAL_ACCESS_TOKEN` for the tracker.

## Verified / not

- Verified: `agent.py` imports; system prompt builds with soul + memory + hand-off protocol.
- Not verified: any model turn; GitHub MCP tool names; that `gate()` holds under the SDK.

## Known gaps

- `Read` is auto-allowed, so nothing stops the model reading a `.env` if one ever appears in the repo.
- `Agent` (subagents) is gated y/N because it's unverified whether subagent tool calls re-enter `gate()`.
- Context cost: 12 user-scope plugins loaded; `pr-review-toolkit` adds ~1.6k always-on tokens this
  agent never uses — a candidate to disable for program-only sessions.
