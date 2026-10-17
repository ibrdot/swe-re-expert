---
name: sentry
description: Use this connector skill whenever the user asks an agent to work with Sentry organizations, projects, issues, error triage, exception investigation, issue status changes, or production incident summaries.
---

# Sentry

Use Sentry through the official `sentry` MCP server. Provider credentials stay server-side; do not handle raw Sentry OAuth tokens.

## Discovery

Start from the live MCP tool descriptions:

```bash
connector-cli mcp list-servers
connector-cli mcp describe-server sentry
connector-cli mcp describe-tools sentry <tool-name>
```

Use only MCP tools returned by `describe-server`. Do not invent Sentry API parameters from upstream docs.

## Invocation

```bash
connector-cli mcp call-tool sentry <tool-name> --input '<json>'
```

`APP_SERVER_URL` must be available, and connector broker auth must come from the runtime config file or the `SANDBOX_TOKEN` local fallback. Do not print or persist `SANDBOX_TOKEN`.

## Key Rules

- Use exact Sentry organization slugs and issue IDs. If the organization slug is unknown, discover organizations with the tools exposed by the MCP server first.
- Resolve projects before filtering issue or event queries by project.
- Keep provider facts separate from incident analysis. Label root-cause or ownership statements as inference unless verified from issue metadata, stack frames, or linked code.
- Before write operations such as status or assignment changes, confirm the target issue and intended change.
- Do not claim a write succeeded until the MCP tool result confirms it.

## Workflows

**Issue triage:** List issues with the narrowest project, environment, query, and time filters available. Summarize title, status, project, counts, user impact, last seen time, and permalink when the MCP result includes them.

**Issue deep dive:** Start with a precise issue lookup, then connect the returned project, culprit, metadata, timestamps, and status to the user's question. Separate confirmed Sentry data from likely cause.

**Status updates:** Make the smallest requested change. Prefer resolving or reopening a single verified issue ID over broad issue-list mutations.
