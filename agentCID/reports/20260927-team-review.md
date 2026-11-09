# DSPM agent team — review 2026-09-27

**Provenance:** deterministic scores from `inspectAgents.py --all` (this date). The qualitative
half was written by the Claude Code session that built the agents, applying `knowledge\agentRubric.md`
by hand, because `ANTHROPIC_API_KEY` is a placeholder and AgentCID's model turn cannot run yet.
Treat it as a first review by the author, not an independent one — the independent review is the
first thing AgentCID should do once it can run.

| Agent | Deterministic | Qualitative (rubric §1–§8, /16) | Verdict |
|---|---|---|---|
| AgentDaya | 100% A | 14 | well-built & well-aimed |
| AgentDino | 100% A | 12 → 13 after fix | well-built, one aim corrected |
| AgentNolan | 100% A | 11 → 12 after fix | well-aimed, write scope was too wide |
| AgentPradyuman | 100% A | 12 → 13 after fix | well-aimed, write scope was too wide |

## TOP FIXES (blast radius first) — all applied this date by the owner

1. **Dino could edit Daya's specs.** Soul: *"The spec is the contract"* — but `PROTECTED` only
   covered `dspm\docs\adr`, so `dspm\docs\specs` was writable. A developer that can rewrite its own
   contract has no contract. Fix: `dspm\docs\specs` added to `PROTECTED` (`agentDino\agent.py`).
2. **Nolan, Pradyuman and Daya could all write anywhere in `program\`.** Souls: *"Your writes go
   to `program\` (mainly `program\prd\`)"* / *"`roadmap.md`, `status.md`, `decisions.md`"* — the
   runners allowed the whole folder, so Nolan could edit the roadmap, Pradyuman the PRD, either
   could edit Manish's `objective.md`. Fix: per-agent allow-lists — Nolan `prd\` + `decisions.md`;
   Pradyuman `roadmap.md`, `status.md`, `decisions.md`; Daya `decisions.md` only.
3. **`allowed_tools` shadows the permission callback** (SDK warning, all agents). Every tool in a
   list literal is auto-approved before `gate()` runs. Today no list contains a write or shell tool
   (G8 pass), so this is a standing rule to keep, not a defect: never add `Bash`/`Write` to an
   allow-list "for convenience".

## SCORECARD (0–2 per row; quotes are from the souls)

**AgentDaya** — §1 2 ("designs; AgentDino builds; you review") · §2 2 (MCP server cannot build
`--live`; `PROTECTED` registry/.env; write scope docs-only under `dspm`) · §3 2 (argv building,
validation, audit all in `dctMcp.py`) · §4 2 (two numbered loops, position-brief template) · §5 2
(three typed topics, each with *why*) · §6 2 (readme: "No model turn has completed yet — refused
for credit") · §7 1 (tools have triggers; context cost noted only in memory — 19k-char prompt is
heavy) · §8 1 (Read auto-allowed → could read `.env`; acknowledged in Known gaps).

**AgentDino** — §1 2 · §2 1→2 after fix 1 · §3 2 ("Tests first… a swallowed error is a defect";
`unknown`-on-error test pattern in memory) · §4 2 · §5 2 · §6 1 (readme honest; no Known gaps
section) · §7 2 (`/tdd`, `/implement`, `context7` each with a *when*) · §8 1 (same Read exposure,
not acknowledged).

**AgentNolan** — §1 2 ("Problem before solution… name the user and the outcome") · §2 1→2 after
fix 2 · §3 1 (all judgement, by design; nothing deterministic to separate — acceptable but the
PRD template could be a script-checked schema) · §4 2 (PRD section order fixed; `/grill-me` step)
· §5 2 · §6 1 (readme honest; no Known gaps) · §7 2 · §8 1.

**AgentPradyuman** — §1 2 ("Gates are evidence, not dates") · §2 1→2 after fix 2 · §3 1 (status
shape is prose-enforced; a `status.md` linter would be the mechanics half) · §4 2 (fixed status
shape: Blockers → Gate evidence → Next hand-offs) · §5 2 (standing-blockers memory with *why*) ·
§6 2 (readme honest; status.md itself leads with blockers) · §7 2 · §8 1.

## NOT ASSESSABLE YET

- **Any behaviour.** No agent has a `runs\session*.md`. Whether `gate()` actually refuses a
  write to another agent's folder under the SDK, whether the plugin skills appear in the Skill
  listing, whether GitHub MCP tool names match — all unverified until one real turn per agent.
  The single most valuable turn: `agentNolan --once` on a candidate objective, then re-inspect.
- **GitHub tracker path** — no `GITHUB_PERSONAL_ACCESS_TOKEN`; the fallback (mirror to files) is
  the only path exercised, and only on paper.

## Older agents (not part of the team, inspected for free)

agentC 96% and mcpServerCreator 97%: both fail R2 — their readmes never state what is verified.
Owner's call; not changed here.

## Follow-up — AgentCID's first real turn (same date, `20260927-agentDino-review.md`)

CID's own review of agentDino (Opus 5.5, $1.03, on the claude.ai login) found what the hand review
missed. All applied to the affected runners by the owner:

- **"Never push" was prose-only** — `commit-commands`' `commit-push-pr` skill pre-approves
  `Bash(git push:*)`, and `Skill` is auto-allowed. Now `disallowed_tools` bans `git push`/`gh pr
  create`/`git remote` at the harness, plus a `git push` deny in `gate()` (Daya, Dino, CID);
  Nolan/Pradyuman get `disallowed_tools=["Bash","PowerShell"]`.
- **`/implement`, `/grill-me`, `/to-spec`, `/to-tickets`, `/to-questionnaire` are user-only**
  (`disable-model-invocation: true`) — S8 false-passed on disk presence. Souls now use `/tdd`,
  `/codebase-design`, `/grilling`; `inspectAgents.py` excludes non-model-invocable skills.
- **Auto-allowed tools left no trail** — every runner now logs every `ToolUseBlock` to the
  transcript and `runs\toolCalls<date>.jsonl` (new check G11).
- **`Agent` may bypass `gate()` via subagents** — unverified, so `Agent` is now gated y/N everywhere.
- **`input()` could raise `EOFError` inside the permission callback** — caught, denies.
- **context7 returned injected-looking text** — Dino's soul now treats its output as untrusted data.
