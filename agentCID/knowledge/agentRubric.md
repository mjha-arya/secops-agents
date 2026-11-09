# Agent quality rubric

What "good" means for an agent in this repo. `inspectAgents.py` measures the rows marked *deterministic*;
AgentCID judges the rest by reading. Score each qualitative row 0 (absent) · 1 (present, weak) ·
2 (present, strong) and always quote the line that earned the score.

## 1. Purpose and boundaries
| Row | How to judge | Deterministic? |
|---|---|---|
| One-sentence job the reader can repeat | First paragraph of `soul.md` says who it is, for whom, and what it hands back | no |
| Explicit non-goals ("never …") | Soul names what it will not do; runner enforces the same | partly (S7) |
| Fits the team | Its outputs are another agent's inputs per `program\readme.md`; no overlap with a sibling's writes | no |

## 2. Guardrails match the words
| Row | How to judge | Deterministic? |
|---|---|---|
| Every "never" in the soul has a mechanism in `agent.py` or an MCP server | e.g. "never pushes" → no push path; "no shell" → `NO_SHELL` deny | partly (G1–G9) |
| Write scope is an allow-list, and the list is the smallest that lets it do its job | `WRITABLE` vs what the soul says it produces | partly (G4) |
| Unattended mode is safe | `--once` refuses anything a human would otherwise approve | yes (G3) |
| Sensitive paths are denied by name, not by hope | `PROTECTED` for registries, `.env`, tool code | info (G9) |
| Least privilege stated honestly where the platform can't enforce it | e.g. "Read is auto-allowed, so it could read `.env`" written down | no |

## 3. Judgement vs mechanics (P1)
| Row | How to judge | Deterministic? |
|---|---|---|
| Deterministic work is in code (MCP server, scripts), not prompt instructions | Anything exact — argv building, parsing, validation — lives in `.py` | no |
| The model is used only where the answer depends on context | Soul says where judgement is needed and why | no |

## 4. Method (P2, P3, P5, P6)
| Row | How to judge | Deterministic? |
|---|---|---|
| Ordered steps, each with a reviewable artifact | "How we solve problems" is numbered and names files | partly (S2) |
| Discovery before action | Step 2 is "read what exists", with paths | no |
| `needs_human` is concrete | Triggers are specific situations, not "when unsure" | partly (S3) |
| Output format is fixed | A template block exists for the main deliverable (P13) | no |

## 5. Memory (P9)
| Row | How to judge | Deterministic? |
|---|---|---|
| Index + typed topic files, all linked | frontmatter `name/description/type`; no orphans | yes (M1–M4) |
| Memory holds only the non-obvious and reusable | No per-run results, no restating the readme; each has a *why* | no |
| Rule for when to save and when to delete | Soul's Memory section says both | partly (S5) |

## 6. Honesty and evidence (P11, P12)
| Row | How to judge | Deterministic? |
|---|---|---|
| Status line says authored / verified truthfully | readme `**Status:**` + a Verified/Not-verified section | yes (R1, R2) |
| Runs leave a trail | `runs\session*.md` and tool-call logs exist once it has run | info (E1) |
| Known gaps are written down | readme has a Known gaps section that isn't empty theatre | no |

## 7. Tools the agent claims to use
| Row | How to judge | Deterministic? |
|---|---|---|
| Every `/skill` and plugin agent named in the soul exists **and is model-invocable** | user skills + plugin cache, excluding `disable-model-invocation: true` (user-only slash commands the agent can never call) | yes (S8, S9) |
| Each tool has a *when*, not just a name | Soul's tool table has a trigger column | no |
| Context cost is acknowledged | Always-on token cost of heavy plugins noted somewhere | no |

## 8. Hygiene
| Row | How to judge | Deterministic? |
|---|---|---|
| No secrets anywhere | regex scan | yes (X1) |
| Imports under its own venv | `agent.build_system_prompt()` runs | yes (T1) |
| Workstation constraints recorded | CLM PowerShell, venv location, auth mode | no |

## Grading
Deterministic score from `inspectAgents.py` (pass ÷ (pass+fail)); qualitative score = sum of row scores ÷
max. Report both, never a blended single number — the two measure different things. An agent with
a 100% deterministic score and a weak soul is *well-built and badly aimed*; say exactly that.
