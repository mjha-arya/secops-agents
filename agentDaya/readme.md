# AgentDaya (agent)

A Claude Agent SDK agent with two jobs:

1. **Technical lead / architect of the DSPM** — Contoso's Data Security Posture Management
   platform, built from scratch in `..\dspm\`, Databricks-first. It designs to
   `knowledge\dspmBlueprint.md` (five layers, build order, stack defaults), writes the spec and ADR
   for each component, hands the build to **AgentDino**, and is the review gate for what Dino
   built (`/code-review`, `/review-pr`, `security-guidance`). Requirements come from AgentNolan,
   the plan from AgentPradyuman (see `..\program\readme.md`). Manish approves every ADR and every
   commit; the agent never pushes.
2. **Read-only operator of the Databricks Control Tool** (`secopsCurrentProjects\databricks\controlTool\`),
   which is the DSPM's posture layer. It runs `ctl.py` through a local MCP server that cannot build
   `--live`, `--live-agent`, `--approve-all` or `--promote`, explains the 31-control position, and
   drafts registry/exception/inventory changes to `proposals\` for a human to ratify.

**Status:** Authored; **first real model turn completed 2026-09-27** on the workspace-scoped
`ANTHROPIC_API_KEY` (phase 0: wrote `dspm\docs\adr\0001-stack.md`). The write gate held live:
the ADR write was allowed, an attempted edit of `dspm\readme.md` was denied as Dino's. Every tool
call was audited. The final reply was lost to a cp1252 console crash, since fixed (P11: runner and
gate verified; architect judgement still to be reviewed by AgentCID).

## Files

| File | Purpose |
|---|---|
| `soul.md` | Both roles, the plugin-usage table ("the plugins are your team"), the architect loop and the operator loop |
| `knowledge\dspmBlueprint.md` | **Architecture of record.** Five layers, phases and gates, stack defaults, how each plugin is used, definition of done. Embedded in every system prompt; deviations need an ADR |
| `memory\MEMORY.md` + topic files | Control tool state, plugin loading facts, workstation constraints |
| `mcp\dctMcp.py` | Read-only MCP server (stdio) over `ctl.py`: `validate`, `list_controls`, `explain_control`, `run_pipeline`, `position`, `drift`, `preflight`, `list_runs`, `read_run_artifact`, `read_evidence`, `registry_file` |
| `agent.py` | Runner: task as argument, interactive, or `--once` |
| `proposals\` | Drafted registry / exception / inventory changes for human review |
| `runs\session*.md` + `runs\toolCalls*.jsonl` | Audit trail: prompts, output, every permission decision and every `ctl.py` invocation (P12) |
| `..\dspm\` | The product. `readme.md` phase table, `docs\adr\`, `docs\specs\`, one folder per layer, `knowledge\connectors.yaml` |

## The plugins (installed at user scope)

| Plugin | Invoke as | Used for |
|---|---|---|
| `feature-dev` | `/feature-dev` | Spec + plan for every new component, before code |
| `code-review` | `/code-review` | Every proposed commit |
| `pr-review-toolkit` | `/review-pr` or its agents (`silent-failure-hunter`, `pr-test-analyzer`, …) via the Agent tool | Cross-layer changes |
| `security-guidance` | hooks only (SessionStart, UserPromptSubmit, PostToolUse, Stop, SubagentStop) | Always on; warnings fixed or waived in the PR note |
| `agent-sdk-dev` | `/new-sdk-app`, agent `agent-sdk-verifier-py` | Any agent inside the DSPM |
| `frontend-design` | `/frontend-design` | Phase 6 dashboard |

Installed with `claude plugin install <name>@claude-plugins-official`; loaded by `agent.py` via
`setting_sources=["user", "project"]` (the SDK's own `plugins=` option is local-path only). See
`memory\pluginLoading.md`.

## Guardrails (in `agent.py` and `mcp\dctMcp.py`)

- Read, Glob, Grep, WebFetch, WebSearch, Skill, Agent, TodoWrite and the eleven `dct` tools run
  automatically.
- **Shell is gated:** `Bash` asks `y/N` per command in interactive runs and is refused in `--once`.
  `PowerShell` is refused always (ConstrainedLanguage on this estate).
- Write/Edit allowed **only** in `..\dspm\docs\`, `..\dspm\knowledge\`, `..\program\decisions.md`,
  `proposals\`, `memory\` and `knowledge\` (program scope narrowed after CID review, 2026-09-27). Code under `..\dspm\` is denied with "Dino writes the
  code — write the spec"; the control tool's `registry\`, `.env`, `ctl\` and `ctl.py` are denied
  with a "write a proposal" message.
- The MCP server refuses `--live`, `--live-agent`, `--approve-all`, `--promote`; strips
  `DATABRICKS_WRITE_TOKEN` from the child environment. Without those flags `ctl.py` always uses the
  recorded fixture estate.
- **Databricks managed MCP** is a config slot: attached only when `DATABRICKS_MCP_URL` and
  `DATABRICKS_MCP_TOKEN` are both set (`..\dspm\knowledge\connectors.yaml`). Provisioning them is
  needs_human.
- `run_pipeline`, `position`, `drift` each write a `controlTool\runs\<timestamp>\` folder, as the CLI does.

## Run

```
python -m venv %USERPROFILE%\.venvs\agentDaya
%USERPROFILE%\.venvs\agentDaya\Scripts\python.exe -m pip install -r requirements.txt

%USERPROFILE%\.venvs\agentDaya\Scripts\python.exe agent.py "phase 0: write ADR-0001"
%USERPROFILE%\.venvs\agentDaya\Scripts\python.exe agent.py --once "where are we on SEC-24?"
```

Needs an auth source with credit: `ANTHROPIC_API_KEY`, or unset it so the CLI uses the claude.ai
org login (the CLI warns that the key takes precedence). Model via `AGENTDAYA_MODEL` (default
`claude-opus-5-5`).

## Verified (2026-09-26, no model turn)

- `agent.py` imports under `.venvs\agentDaya`; system prompt builds with soul + memory index +
  blueprint embedded (~16k chars); write scope, MCP slot and tool allow-list as documented
- All eleven `dct` tools return against the fixture estate; refusal paths for malformed ids, path
  traversal and each forbidden flag raise `ToolError`; over stdio `tools/list` returns exactly the
  eleven tools the runner allow-lists
- Six plugins installed and enabled in `~/.claude/settings.json`; component names confirmed with
  `claude plugin details`
- SDK connected to the CLI and reached the API on a `--once` run (refused for credit, not for wiring)

**Not verified:** any model turn; that the plugin skills appear in the agent's Skill listing at
runtime (expected via user settings, unproven); the `gate()` rules under the SDK; anything live.

## Known gaps

- `Read` is auto-allowed, so the runner can't stop the model reading `controlTool\.env` if one is
  created (same exposure as agentD). None exists today.
- `pr-review-toolkit` adds ~1.6k always-on tokens per session; disable it for operator-only work.
- Nothing in `dspm\` exists beyond the skeleton, readme and `connectors.yaml`. ADR-0001 is the
  first architect task.
