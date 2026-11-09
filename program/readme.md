# Program workspace — how the four agents hand off

One objective at a time flows through four agents. Each reads the artifact before it, writes the
one it owns, and ends its turn with a hand-off packet. Manish sets the objective and accepts every
gate. No agent skips a stage; unknowns become open questions, never assumptions.

```
Manish        objective.md            what we are trying to achieve, and why now
  ↓
AgentNolan    prd\<objective>.md      problem, users, outcomes, stories with acceptance criteria
  ↓                                   → GitHub issues labelled story, epic:<name>
AgentPradyuman roadmap.md, status.md   milestones = blueprint phases, workstreams, gates, RAID
  ↓                                   → GitHub milestones + project board
AgentDaya     dspm\docs\specs\, adr\   component spec + ADR per deviation; the review gate later
  ↓
AgentDino     dspm\<layer>\            code + tests for one issue at a time; proposes the commit
  ↓
AgentDaya     review                   /code-review, /review-pr, security-guidance warnings closed
  ↓
AgentPradyuman status.md               gate evidence rolled up; blockers at the top
  ↓
Manish        accepts the gate, commits/pushes, sets the next objective
```

## Files in this folder

| File | Owner | Contents |
|---|---|---|
| `objective.md` | Manish | The current objective; candidates below it. One active at a time |
| `prd\<objective>.md` | Nolan | The PRD (Contoso PDP spec shape via `tech-pdp-spec-writer`) |
| `roadmap.md` | Pradyuman | Milestones mapped to `agentDaya\knowledge\dspmBlueprint.md` phases, workstreams, dependencies |
| `status.md` | Pradyuman | Current position: blockers first, then gate evidence, then next hand-offs |
| `decisions.md` | any agent, append-only | Program-level decisions with date, owner, reason. Architecture decisions go to `dspm\docs\adr\` instead |

## Tracker

GitHub Issues, Milestones and Projects on **github.com/mjha-arya/MyAgents**, through the `github`
plugin's MCP server. Labels: `story` (Nolan), `task` (Pradyuman/Daya), `bug` (Dino), `epic:<name>`,
`needs_human`. One milestone per blueprint phase. The MCP needs `GITHUB_PERSONAL_ACCESS_TOKEN` (or
`GITHUB_TOKEN`) in the environment — provisioning it is needs_human; until then agents write the
same content to the files here and say so.

## Hand-off packet (end of every agent turn, and the body of every issue)

```
FROM <agent> → TO <agent>
Artifact:   <repo path or issue #>
Needed:     <one line — the decision, design or build being asked for>
Done when:  <testable condition>
Open:       <questions the next agent must answer or escalate>
```

## Quality of the agents themselves

**AgentCID** (`..\agentCID\`) inspects the four agents — not the product. Run it before an agent's
first real turn and after any change to a soul or runner: `python agentCID\inspectAgents.py --all` for
the deterministic score, then AgentCID for the qualitative review. Its reports land in
`agentCID\reports\`; fixes are made by the agent's owner, never by CID.

## Rules

- **Read before write.** Each agent reads the artifact upstream of it, in full, every turn.
- **The blueprint wins.** A PRD or roadmap that contradicts `dspmBlueprint.md` is an ADR request
  to Daya, not a silent change.
- **Gates are evidence, not dates.** A phase closes when its blueprint gate condition is shown,
  never because the calendar says so.
- **Nobody pushes.** Agents propose commits; Manish pushes.
- **Objectives become epics.** "Build a Databricks SAT equivalent" is an epic across blueprint
  layer 4; "a security-configuration console / MCP for Databricks" is an epic across layers 4–5
  and the UI. Neither starts a second product.
