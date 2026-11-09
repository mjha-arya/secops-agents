---
name: inspectionApproach
description: Limits of inspectAgents.py, and the weaknesses that recur across this repo's agents as of the first inspection
type: project
---

- **`inspectAgents.py` sees files, not behaviour.** It proves a guardrail is *wired* (`can_use_tool=`,
  `UNATTENDED`, `WRITABLE`), not that it *works* under the SDK — that needs an attempted write
  in a real run. Until an agent has `runs\session*.md`, rubric §2's "guardrails match the words"
  is verified by reading the code path, and the report must say so.
- **`allowed_tools` shadows `can_use_tool`.** The SDK warns that any whole-tool entry in
  `allowed_tools` is auto-approved before the callback runs (seen 2026-09-26 on agentDaya). So
  G8 — no write/shell tool in a *list* literal — is the single most important deterministic
  check: a `"Bash"` or `"Write"` in an allow-list silently disables the gate for it.
- **Repo convention worth knowing:** list literals = auto-allowed tools, set literals = gated or
  denied tools (`WRITE_TOOLS`, `NO_SHELL`). `inspectAgents.py` relies on that distinction; an agent
  that breaks the convention will score wrongly — check by reading before trusting G8.
- **Plugins lay skills out differently.** `mattpocock-skills` nests them by category
  (`skills/engineering/tdd/SKILL.md`); a flat `skills/*/SKILL.md` glob reported four real skills as
  missing (false S8 fails on agentDino and agentNolan, 2026-09-27). Discovery now walks every
  `SKILL.md` recursively and also takes the frontmatter `name:`. When S8 fails, confirm with
  `claude plugin details <plugin>` before calling the soul wrong.
- **S8 can now false-*pass*.** A plugin's disk tree can hold more skills than it exposes:
  mattpocock-skills 1.2.3 has 38 `SKILL.md` files, but the harness lists only 11, and
  `implement`/`grill-me` are not among them (2026-09-27, agentDino review). The harness skill listing
  is the truth. Compare every soul-named skill against it, not against the disk.
- **Skill `allowed-tools` frontmatter is a possible hole in the gate.** `commit-commands`'
  `commit-push-pr` pre-approves `Bash(git push:*)`. With `Skill` auto-allowed, a soul's "never push"
  needs `disallowed_tools`, not just prose. Whether the SDK honours skill `allowed-tools` ahead of
  `can_use_tool` has not been verified yet.
- **The inspector inspected itself and failed:** its first name, `inspect.py`, shadowed the stdlib
  `inspect` module and broke its own runner import (T1). Renamed to `inspectAgents.py`. Never name
  a script after a stdlib module.
- **First live proof the gate pattern holds (2026-09-27, agentDaya):** under the SDK, `gate()`
  allowed a Write inside `WRITABLE` and denied an Edit outside it, and `audit_tool_call` logged
  every call. Rubric §2 "guardrails match the words" can now be scored from transcripts for any
  agent with a `runs\session*.md`. Still unverified: subagent calls, skill `allowed-tools`.
- **Console encoding is a runner defect, not a model one:** a `→` in the model's reply crashed
  `print()` on the cp1252 console and lost the final text (fixed: `stdout.reconfigure(utf-8)`, log
  before print; check G12). Always read the transcript, not the console, for what an agent said.
- **Recurring weakness (2026-09-27, first inspection):** every agent's readme is honest that no
  model turn has run; none has behavioural evidence. The whole team is *authored*, not *verified*.
- **Why:** the first inspection had to be run without any agent ever having executed a turn, so
  the rubric's behavioural rows were all "not assessable yet". **How to apply:** when a `runs\`
  folder appears for an agent, re-inspect it first — that is where the real findings will be.
  Related: [[workstationConstraints]].
