# SecOps Agents

> **A team of Claude Agent SDK agents for security operations. They investigate, build and inspect, and none of them holds more privilege than its job needs.**

Eight agents built for a Microsoft + Databricks security estate: Defender XDR investigation, certificate-expiry automation, read-only MCP servers, a full product team (PM → program → architect → developer) for a DSPM platform, and an **inspector that audits the other agents**.

Every agent follows the same pattern: a `soul.md` (character, method, hard "never"s), persistent memory, a permission gate in code, and an audit trail of every tool call.

## The agents

| Agent | Role | Privilege boundary |
|---|---|---|
| [**agentD**](agentD/) | Investigates Microsoft Defender XDR alerts and incidents from a `security.microsoft.com` link, then writes a findings report | **Investigate-only.** Reads through a read-only Graph MCP server it ships with. No write, no shell, no containment |
| [**agentC**](agentC/) | Builds certificate-expiry automation (Defender TVM, Key Vault, Entra app secrets, App Gateway/App Service TLS) | Writes IaC. **A human deploys it** |
| [**mcpServerCreator**](mcpServerCreator/) | Designs and builds read-only MCP servers for SecOps tooling (Purview, Defender) | Writes only inside its workspace. Shell needs `y/N` and is refused when unattended |
| [**agentCID**](agentCID/) | **Inspector of agents.** A deterministic scorer (guardrails wired, secrets, memory integrity, readme honesty) plus a rubric-judged review | Reports only. **Never edits another agent** |
| [**agentNolan**](agentNolan/) | Product manager: objective → PRD with testable acceptance criteria → GitHub issues | No shell, no code |
| [**agentPradyuman**](agentPradyuman/) | Program manager: PRD → roadmap, milestones and a blockers-first status | Gates are evidence, not dates |
| [**agentDaya**](agentDaya/) | Architect and review gate for the DSPM. Writes specs and ADRs and reviews every build | Gated shell. Never pushes or applies |
| [**agentDino**](agentDino/) | Developer: implements specs as tested Python, one issue at a time | Gated shell. Never pushes |

## The flagship workload: DSPM, built by agents

[`dspm/`](dspm/) is a Data Security Posture Management platform (Databricks-first) built **by the agent team above**, with a human approving every ADR and commit:

```
 objective.md ─► agentNolan (PRD) ─► agentPradyuman (roadmap) ─► agentDaya (spec + ADR)
                                                                     │        ▲
                                                                     ▼        │ review
                                                                agentDino (TDD build)
```

Five layers: **discover → classify → access graph → posture → remediate** (propose → approve → apply → verify → evidence).

## Design principles

- **Least privilege in code, not in the prompt.** Permission callbacks in `agent.py` allow-list tools. Writes are path-scoped. Shell is `y/N`-gated and refused in unattended mode.
- **Read-only MCP servers.** Agents reach Microsoft Graph and Databricks only through tools that cannot mutate.
- **Honest status.** Every readme says *Authored* or *Verified*, and never claims a run that didn't happen.
- **Agents audit agents.** `agentCID/inspectAgents.py` scores every agent deterministically with no model and no key.

## Stack

Claude Agent SDK (Python) · Model Context Protocol · Microsoft Graph Security API · Defender XDR · Entra ID · Azure Key Vault · Databricks (Unity Catalog, system tables) · Bicep/IaC

## Status

| Area | State |
|---|---|
| agentCID deterministic inspector | **Verified**: first run over all 8 agents |
| agentD, agentC, mcpServerCreator | Authored; SDK import and permission gates tested |
| DSPM | Phase 0 to 1 (skeleton, blueprint, posture adapter with tests) |

> Tenant IDs, workspace hosts and org names are replaced with placeholders (`contoso.com`, `00000000-…`).

---
Part of a wider body of work on **secure, provable AI agents**. See the [Constitution of Agents](https://github.com/mjha-arya/constitution-of-agents) and the [profile](https://github.com/mjha-arya).
