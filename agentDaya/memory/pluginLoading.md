---
name: pluginLoading
description: How the six Claude Code plugins reach AgentDaya through the Agent SDK, their exact component names, and their context cost
type: reference
---

- **Install is a CLI action, not an SDK one:** `claude plugin install <name>@claude-plugins-official`
  installs at user scope and flips `enabledPlugins` in `~/.claude/settings.json`. Done 2026-09-26 for
  `feature-dev`, `code-review`, `pr-review-toolkit`, `security-guidance`, `agent-sdk-dev`,
  `frontend-design`.
- **The SDK's `plugins=` option only takes `{"type": "local", "path": ...}`** (claude-agent-sdk
  0.2.160, `SdkPluginConfig`). Marketplace-installed plugins are picked up instead via
  `setting_sources=["user", "project"]` — agentD/mcpServerCreator use `["project"]` only, which is
  why they see no plugins. The Skill tool must be in `allowed_tools` to invoke plugin skills, and
  the Agent tool to run plugin agents.
- **Exact component names** (from `claude plugin details`):
  `/feature-dev` (+ agents code-explorer, code-architect, code-reviewer) · `/code-review` ·
  `/review-pr` (+ agents silent-failure-hunter, pr-test-analyzer, type-design-analyzer,
  code-simplifier, comment-analyzer, code-reviewer) · `security-guidance` = 5 hooks, no skill ·
  `/new-sdk-app` (+ agents agent-sdk-verifier-py/-ts) · `/frontend-design`.
- **Context cost:** pr-review-toolkit adds ~1.6k always-on tokens per session (its six agent
  descriptions); the others ~200 or less; security-guidance ~0 (harness-only). Invocations cost
  ~1–2.3k each. Acceptable for an architect session; disable pr-review-toolkit
  (`claude plugin disable`) if a session is purely operator work.
- **Why it matters:** the blueprint's "plugins are not optional" table depends on this loading
  path being right. If a plugin skill is missing from the session, check user settings first, not
  the soul. Related: [[controlToolState]], [[workstationConstraints]].
