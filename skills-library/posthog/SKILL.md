---
name: posthog
description: Use this connector skill whenever the user asks an agent to analyze or manage PostHog product analytics, feature flags, experiments, dashboards, surveys, data pipelines, AI observability, error tracking, or logs.
---

# PostHog

Use PostHog through the official `posthog` MCP server. The authorization may
cover a single project, several projects, or a whole organization, and exposes
the full PostHog read/write surface through the token-efficient MCP CLI mode.
When it covers more than one project, PostHog MCP defaults to the user's current
active project; `projects-get`, `switch-project`, and `switch-organization` are
available through the MCP CLI to inspect and change that context.
Provider credentials stay server-side; do not handle raw PostHog OAuth tokens.

## Discovery

Start from the live MCP tool descriptions:

```bash
connector-cli mcp list-servers
connector-cli mcp describe-server posthog
connector-cli mcp describe-tools posthog exec
```

Use only MCP tools returned by `describe-server`. Do not invent PostHog tool
parameters from upstream API documentation.

## Invocation

```bash
connector-cli mcp call-tool posthog exec --input '<json>'
```

`CONNECTOR_BASE_URL` must be available, and connector broker auth must come from the
runtime config file or the `SANDBOX_TOKEN` local fallback. Do not print or
persist `SANDBOX_TOKEN`.

## Key Rules

- Know which project you are querying. When the user names a project or the
  result depends on it, run `projects-get` first and state the active project;
  use `switch-project` only to reach a project the user asked for.
- Before any write operation (creating, updating, or deleting a feature flag,
  dashboard, experiment, insight, survey, or other project object), run
  `projects-get` to confirm the current active project and tell the user which
  project the change will land in. Switch with `switch-project` first if it is
  not the intended project.
- Use bounded time ranges and result sizes for HogQL, event, trace, and log
  queries.
- Prefer aggregate results. Only request person-level or raw event data when
  the user's question requires it.
- Read the live `exec` schema before use. Discover commands through the PostHog
  MCP CLI instead of inventing command names or arguments.
- Write operations are available. Make the intended change clear to the user
  and use the narrowest command that satisfies the request.
- Separate facts returned by PostHog from causal analysis. Label explanations
  of metric changes as inference unless the query evidence proves them.

## Workflows

**Metric diagnosis:** Confirm the project context and time range, inspect the
relevant event schema, then run the narrowest insight or HogQL query needed.
Compare against a prior period only when the user asks for a change analysis.

**AI observability:** Filter traces by a bounded time range and the relevant
model, provider, or application context. Summarize latency, errors, token usage,
and cost only from returned fields.

**Error and log investigation:** Start with aggregate issue or log counts, then
drill into a specific issue or trace. Avoid broad raw-log exports.

**Product management:** Inspect the current object before changing a feature
flag, experiment, dashboard, survey, workflow, or other project configuration.
After a write, read the object back and report the verified resulting state.
