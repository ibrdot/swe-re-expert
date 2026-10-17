---
name: linear
description: Use this connector skill whenever the user asks an agent to work with Linear issues, teams, projects, cycles, workflow states, labels, comments, assignments, or engineering planning through the connector. Use it for Linear workflows that need to inspect assigned work, create or update issues, connect code changes to Linear tickets, or summarize project execution status.
---

# Linear

Use the Linear connector through the configured MCP server or `connector-cli`. Provider credentials stay server-side; do not handle raw Linear OAuth tokens.

## Skill Boundary

This skill is installed into agent runtime prompts outside the source repository. Keep it self-contained and do not link to repository-local materials, source paths, or private maintenance notes.

If auth boundaries, action keys, or Linear workspace/account behavior changes, update this prompt with the user-facing rules agents need at runtime. Keep implementation-only notes out of this public skill.

## Tool Selection

Use `connector-cli` directly for documented Linear connector actions. Start with the action the task needs; do not run `command -v`, `which`, `env`, or similar executable/config probes before normal invocations. If the first direct invocation fails because `connector-cli`, `CONNECTOR_BASE_URL`, or runtime auth config is missing, diagnose PATH/config once with the smallest relevant check. Use Linear MCP tools only when the user explicitly asks for MCP or no documented `connector-cli` action covers the task.

## Invocation

```bash
connector-cli provider invoke linear.viewer.get --input '{}'
connector-cli provider invoke linear.issue.update --input-file input.json
```

`CONNECTOR_BASE_URL` must be available, and connector broker auth must come from the runtime config file or the `SANDBOX_TOKEN` local fallback. Assume the runtime config is already present and invoke first; only inspect status or environment after a missing-config or auth error. Do not print or persist `SANDBOX_TOKEN`.

Start with `connector-cli provider list` when routing across Providers. Use `connector-cli provider explain linear` for Linear boundaries and `connector-cli provider actions linear` for the lightweight complete index. Load a long-tail action schema only with `connector-cli provider action explain <full-action-key>`.

## Progressive Action Discovery

Common actions are injected below this skill from the current Provider catalog as compact executable signatures. Use those signatures directly when they match the task. For a long-tail action, run `connector-cli provider actions <provider>`, then load exactly one schema with `connector-cli provider action explain <full-action-key>`. Never guess, infer, or invent an action key or parameter. Treat terminal `action_not_found` as final for the confirmed catalog version and do not refresh or retry it automatically.

## Result Handling

`connector-cli` outputs JSON with the provider payload under `.data`. For simple field extraction, filtering, or list formatting, pipe results to `jq` instead of writing a temporary Python script. Use Python only when the transformation is too complex for a small `jq` expression.

**Tip:** When you know which fields you need, pipe to `jq` directly to avoid processing large JSON outputs.

For multiline Markdown inputs such as issue descriptions or comments, do not put `\n` inside shell strings passed through `jq --arg`; shells usually pass that as a literal backslash-n. Write the body with a heredoc to a temporary file, then use `jq --rawfile` so newlines are real before JSON encoding.

Common compact examples:

```bash
connector-cli provider invoke linear.viewer.get --input '{}' \
  | jq '.data | {id, name, email}'

viewer_id="$(connector-cli provider invoke linear.viewer.get --input '{}' | jq -r '.data.id')"
connector-cli provider invoke linear.issue.list --input "{\"assigneeId\":\"${viewer_id}\",\"first\":50}" \
  | jq '.data | {count: (.nodes | length), issues: [.nodes[] | {identifier, title, state: .state.name, url}]}'

connector-cli provider invoke linear.issue.search --input '{"first":20,"query":"sandbox"}' \
  | jq '.data | {count: (.nodes | length), issues: [.nodes[] | {identifier, title, state: .state.name, assignee: .assignee.name, url}]}'
```

## Issue Filter DSL

`linear.issue.list` and `linear.issue.search` accept a structured `filter` object for common Linear issue filters. Each key uses `<field path>.<operator>` and maps to the nested Linear GraphQL `IssueFilter` shape. For example, `"creator.email.eq": "user@example.com"` becomes `creator: { email: { eq: "user@example.com" } }`, and `"createdAt.gte": "2026-05-01T00:00:00Z"` becomes `createdAt: { gte: "2026-05-01T00:00:00Z" }`.

Common filter keys include `creator.email.eq`, `creator.id.eq`, `creator.isMe.eq`, `assignee.email.eq`, `subscribers.email.eq`, `state.name.eq`, `team.key.eqIgnoreCase`, `project.name.containsIgnoreCase`, `cycle.name.containsIgnoreCase`, `labels.name.eq`, `priority.lte`, `estimate.gte`, `dueDate.lte`, `createdAt.gte`, `updatedAt.gte`, `parent.title.containsIgnoreCase`, `hasBlockingRelations.eq`, `title.containsIgnoreCase`, and `description.containsIgnoreCase`. Unsupported filter keys are rejected before the provider call.

```bash
connector-cli provider invoke linear.issue.list --input '{"first":50,"filter":{"creator.email.eq":"user@example.com","createdAt.gte":"2026-05-01T00:00:00Z"}}'
connector-cli provider invoke linear.issue.search --input '{"first":50,"query":"sandbox","filter":{"creator.isMe.eq":true,"hasBlockingRelations.eq":true}}'
```

## Key Rules

- Use exact Linear identifiers: issue identifiers like `MAX-123`, team keys, and provider UUIDs.
- `teamId`, `assigneeId`, `stateId`, `projectId`, `labelId`, and creator/subscriber user IDs are provider UUIDs — not display names or team keys. Resolve them before use (see ID Resolution).
- Keep implementation facts separate from planning interpretation. If a status is inferred from comments or workflow state, label it as an inference.
- Do not claim a write succeeded until the connector or MCP response confirms it.

## ID Resolution

Resolve display names to provider IDs before creating or updating issues:

| Need | Action | Depends on |
|---|---|---|
| teamId | `team.list` | — |
| stateId | `workflow_state.list` | teamId |
| assigneeId | `user.list` | — |
| labelIds | `label.list` | — |
| projectId | `project.list` | — |
| cycleId | `cycle.list` | — |

`workflow_state.list` requires `teamId` — resolve the team first if you don't have it yet.

## Workflows

**Efficient issue listing example:**
```bash
# List assigned issues with compact output
connector-cli provider invoke linear.issue.list \
  --input '{"filter":{"assignee.email.eq":"user@example.com"},"first":20}' \
  | jq -r '.data.nodes[] | "\(.identifier): \(.title) [\(.state.name)]"'
```

**Issue triage / assigned work:** Identify the target user, team, project, cycle, or state. Group results by state or priority. Highlight blockers, stale issues, and ambiguous ownership separately from normal in-progress work.

**Issue deep dive:** Start with identifier, title, state, assignee, and URL. Summarize description, latest comments, and dependencies. Flag missing reproduction steps, unclear requirements, or blockers.

**Creating issues:** Use a short action-oriented title. Include context, user impact, acceptance criteria, and technical notes. Attach team, project, cycle, labels, assignee, and priority only when provided or clearly implied.

**Updating issues:** Make the smallest update that satisfies the request. Do not rewrite titles or descriptions broadly unless asked.

**Planning summaries:** Separate committed work from candidate work. Note stale or blocked items. Include identifiers and URLs so the user can jump to each issue.
