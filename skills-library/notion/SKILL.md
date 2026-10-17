---
name: notion
description: Use this connector skill whenever the user asks an agent to work with Notion pages, shared page content, block trees, notes, docs, or page creation through the official Notion MCP server.
---

# Notion

Use Notion through `connector-cli mcp`. Provider credentials stay server-side; do not handle raw Notion OAuth tokens.

## Discovery

Start from the live MCP tool descriptions instead of an action catalog:

```bash
connector-cli mcp describe-server notion
connector-cli mcp describe-tools notion <tool-name>
```

Use only tools returned by `describe-server`. Before calling a tool for the first time in a task, inspect its schema with `describe-tools`.

## Invocation

```bash
connector-cli mcp call-tool notion <tool-name> --input '<json>'
```

`APP_SERVER_URL` must be available, and connector broker auth must come from the runtime config file or the `SANDBOX_TOKEN` local fallback. Do not print or persist `SANDBOX_TOKEN`.

## Key Rules

- Search or list with the MCP tools before asking the user for page IDs when title or context is enough to locate the page.
- A Notion page's properties are not its body content. Read metadata and body/content with the distinct tools exposed by the MCP server.
- Notion OAuth does not grant access to the whole workspace. Results are limited to content visible to the connected Notion connection.
- Before write operations such as creating pages, appending blocks, or moving a page to trash, ask only when the target parent/page or required input is missing.
- Do not claim a write succeeded until the MCP tool result confirms it.

## Workflows

**Find and read a page:** Describe the Notion server, choose the search/read tools it exposes, search with a narrow title query, then read metadata and content with the returned page/block identifiers.

**Create a page:** Resolve the parent page or data source first. Build the smallest schema-valid input for the selected MCP tool, then append body content only when requested.

**Append content:** Read current children first when placement matters. Use ordering or position parameters only when the MCP tool schema exposes them and the user specifies insertion order.
