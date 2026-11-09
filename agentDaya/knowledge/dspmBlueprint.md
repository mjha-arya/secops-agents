# DSPM Blueprint

The architecture AgentDaya builds to. Knowledge, not code (P9): change this file to change the
product's shape; the agent reads it at the start of every session and never contradicts it
silently — a deviation is an ADR in `dspm\docs\adr\`, with a name against it.

**What we are building:** a Data Security Posture Management platform for Contoso — find every
data store, know what's in it, know who can reach it, know what's wrong, prove it, and fix it
behind a human gate. Databricks first; the design is store-agnostic.

## The five layers

| # | Layer | Question it answers | v1 scope (Databricks-first) | Deterministic (code) | Judgement (model) |
|---|---|---|---|---|---|
| 1 | **Discover** | Where is the data? | Unity Catalog catalogs/schemas/tables/volumes via the Databricks managed MCP and `system.*` tables | Inventory sweep, diffing against last inventory | None |
| 2 | **Classify** | What is it? | Column/table classification: regex + checksum tier → UC tags / Purview SITs tier → Claude Batch API on *sampled* ambiguous values only | Tiers 1–2, sampling, schema of the result | Tier 3 only; structured output `{class, confidence, evidence}`; never a full-table scan |
| 3 | **Map access** | Who can reach it? | `information_schema.*_privileges`, groups, service principals, grants on external locations | Identity→asset graph build | Explaining a path, not computing it |
| 4 | **Posture** | What's wrong? | The **control tool** (`secopsCurrentProjects\databricks\controlTool\`) is this layer: registry → collectors → assess → adjudicate | Everything except adjudication | Adjudicator (existing) |
| 5 | **Remediate & prove** | Fix it, show it | Propose-only changes, human approval, apply with pre-image journal, per-finding evidence with SHA-256 | Apply, verify, evidence | Change narrative for the approver |

**Invariants inherited from the control tool, now platform-wide**
- `unknown` is never `compliant`; a collection failure is `unknown`.
- No single percentage of "compliance" or "coverage" — five buckets, always.
- Nothing writes to a data store without a stage-7 human approval and a tested rollback.
- One-way doors are unreachable by automation.
- Every finding carries its evidence, its method and the standard version it was judged against.

## Build order (phases and their gates)

| Phase | Ships | Gate to next |
|---|---|---|
| 0 | `dspm\` skeleton, this blueprint, ADR-0001 (stack), CI running `unittest` | Manish accepts the stack ADR |
| 1 | Layer 1 against one non-prod Databricks workspace via managed MCP | Inventory matches what the workspace admin sees |
| 2 | Layer 2 tiers 1–2 (deterministic) with the classification taxonomy in `dspm\knowledge\taxonomy.yaml` | Precision measured on a labelled sample, recorded |
| 3 | Layer 3 graph + layer 4 wired to the control tool's findings | One real finding traced asset → identity → control |
| 4 | Layer 2 tier 3 (Claude, Batch API, sampled) | Cost per 1k columns recorded; false-positive review done |
| 5 | Layer 5 propose → approve → apply → verify for one reversible control | Clean apply and working rollback, in non-prod |
| 6 | Dashboard (`dspm\ui\`) | Reads like a product, not a console |

Phases 1–3 deliver most of the value with zero writes. Nothing in phase 5 starts until the
control tool's own registry is ratified (see `memory\controlToolState.md`).

## Stack (defaults until ADR-0001 says otherwise)

- **Language:** Python 3.14, stdlib `unittest`, `pyyaml`; `httpx` for HTTP; no PowerShell (CLM).
- **Layout:** `dspm\` = `discover\` `classify\` `access\` `posture\` (thin adapter over the control
  tool, not a copy) `remediate\` `ui\` `knowledge\` `tests\` `docs\adr\`.
- **Store:** SQLite for v1 (inventory, graph, evidence); Postgres is an ADR away, not a rewrite.
- **Connector:** Databricks managed MCP only (UC functions, Genie, AI Search). Endpoint in
  `dspm\knowledge\connectors.yaml`; credentials never in the repo — OAuth on-behalf-of or an
  SP secret in `.env`, both `needs_human` to provision.
- **Model use:** Claude via the Anthropic SDK — Batch API for bulk classification, structured
  outputs, prompt caching on the taxonomy prompt. Default model per `claude-api` skill guidance;
  cheaper model for bulk tiers only when measured.
- **UI:** built with the `frontend-design` plugin; reads from the SQLite store; no write actions in v1.

## How the plugins are used (this is not optional)

| Plugin | Invoke as | When AgentDaya uses it | What it must produce |
|---|---|---|---|
| `feature-dev` | `/feature-dev` (agents: `code-explorer`, `code-architect`, `code-reviewer`) | Start of every new component or layer | Spec + plan in `dspm\docs\specs\<component>.md` before code |
| `code-review` | `/code-review` | Before every commit it proposes | Review notes; blocking findings fixed first |
| `pr-review-toolkit` | `/review-pr` (agents: `silent-failure-hunter`, `pr-test-analyzer`, `type-design-analyzer`, `code-simplifier`, `comment-analyzer`, `code-reviewer`) | Cross-file or cross-layer changes | Its reviewer agents' findings, recorded in the commit message |
| `security-guidance` | none — 5 hooks (SessionStart, UserPromptSubmit, PostToolUse, Stop, SubagentStop) | Always on while editing and at every stop | Its warnings addressed or explicitly waived in the PR note |
| `agent-sdk-dev` | `/new-sdk-app`, then agent `agent-sdk-verifier-py` | Any scanning/remediation agent inside the DSPM | Agents with the same gate/audit pattern as AgentDaya itself |
| `frontend-design` | `/frontend-design` | Phase 6 only | The dashboard |

All six are installed at **user scope** (`claude plugin install <name>@claude-plugins-official`) and
enabled in `~/.claude/settings.json`; `agent.py` loads them through `setting_sources=["user", "project"]`.

## Who does what

Nolan: PRD and stories (`program\prd\`). Pradyuman: roadmap, tracker, status (`program\`).
**Daya: spec + ADR per component, then the review gate.** **Dino: code + tests from the spec,
proposes the commit.** Manish: accepts ADRs and gates, pushes. Protocol: `program\readme.md`.

## Definition of done (every component)

Spec by Daya exists → Dino's tests exist and pass under `.venvs\agentDino` → `/code-review` clean
in Daya's review → security warnings addressed → ADR written if a default above changed →
`dspm\readme.md` status row updated → commit proposed, Manish pushes.
