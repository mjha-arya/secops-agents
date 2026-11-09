# AgentCID (agent) — inspector of agents

Scores how good another agent in this repo is, in two halves that are never blended:

1. **Deterministic** — `inspectAgents.py` (stdlib only, no model, no key): required files, soul
   sections, guardrails wired in `agent.py` (permission callback, shell policy, unattended
   refusal, write allow-list, no write/shell tool auto-allowed), memory integrity (index links,
   frontmatter, orphans), readme honesty (status + verified), plaintext-secret scan, every
   `/skill` the soul names exists on this machine, import under the agent's own venv, evidence of
   real runs. Writes `reports\<date>-<agent>.md|json` and a summary.
2. **Qualitative** — the Claude Agent SDK agent judges against `knowledge\agentRubric.md`: do the
   guardrails match the soul's "never"s, is judgement separated from mechanics, is `needs_human`
   concrete, does memory hold only the non-obvious, is the readme honest. Uses
   `agent-sdk-verifier-py`, `/code-review`, `/review-pr` agents, `claude-md-management`,
   `contoso-skill-reviewer`. Reports only; **never edits another agent**.

**Status:** Authored. Deterministic half verified — first run 2026-09-27 over all eight agents
(see Verified). Qualitative half not verified: `ANTHROPIC_API_KEY` is a placeholder, no model turn.

## Files

| File | Purpose |
|---|---|
| `inspectAgents.py` | The deterministic inspector. `python inspectAgents.py --all` or named agents; `--no-import` to skip venv checks |
| `knowledge\agentRubric.md` | What "good" means — 8 sections, each row marked deterministic or judged |
| `soul.md` | Attitude ("the soul is a claim; the runner is the truth"), tool table, method, report format |
| `memory\MEMORY.md` + topic files | Persistent memory: inspection approach and limits, workstation constraints |
| `agent.py` | Runner: task as argument, interactive, or `--once` |
| `reports\` | Inspection output, dated; tracked in git so scores have history |
| `runs\` | Audit trail of CID's own sessions (gitignored) |

## Guardrails (in `agent.py`)

- Read, Glob, Grep, WebFetch, WebSearch, Skill, Agent, TodoWrite run automatically.
- **Shell is gated:** `Bash` asks `y/N` per command interactively (mainly `python inspectAgents.py`);
  refused in `--once`, where the latest `reports\*.json` are the facts. `PowerShell` refused always.
- Write/Edit only in `reports\` and `memory\`. Any attempt to edit another agent is refused with
  "put the fix in the report".

## Run

```
python -m venv %USERPROFILE%\.venvs\agentCID
%USERPROFILE%\.venvs\agentCID\Scripts\python.exe -m pip install -r requirements.txt

REM deterministic, works today, no key needed
%USERPROFILE%\.venvs\agentCID\Scripts\python.exe inspectAgents.py --all

REM qualitative review (needs a funded auth source)
%USERPROFILE%\.venvs\agentCID\Scripts\python.exe agent.py "review agentDaya and agentDino"
```

Model via `AGENTCID_MODEL` (default `claude-opus-5-5`).

## Verified (2026-09-27)

- `inspectAgents.py --all` ran over agentC, agentD, agentCID, agentDaya, agentDino, agentNolan,
  agentPradyuman, mcpServerCreator; reports written; import checks executed with each target's venv.
- It found real defects on its first run, including in itself: the script was named `inspect.py`
  and shadowed the stdlib module, breaking CID's own runner import (renamed); two souls
  referenced a slash-skill the machine doesn't have (S8).
- `agent.py` imports under `.venvs\agentCID`; rubric and agent list embedded in the prompt.

**Not verified:** any model turn; the qualitative half; that the `gate()` refuses an edit to
another agent under the SDK (asserted by reading the code).

## Known gaps

- `inspectAgents.py` proves guardrails are *wired*, not that they *hold* — that needs a real run
  per agent (see `memory\inspectionApproach.md`).
- G8 relies on the repo convention list = auto-allowed, set = gated. An agent that breaks the
  convention scores wrongly; read before trusting.
- `AgentScan` integration is a documented step for Manish (`ascan scan` over a tool-call log),
  not a tool CID calls.
