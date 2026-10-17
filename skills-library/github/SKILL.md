---
name: github
description: Use this connector skill whenever the user asks an agent to work with GitHub repositories, issues, pull requests, code review, CI failures, release branches, or repo maintenance through the connector. Use it for GitHub workflows that need to inspect repository state, create or update issues and PRs, review changes, or summarize CI and review status.
---

# GitHub

Use the GitHub connector through `connector-cli`. Raw GitHub OAuth tokens must not reach the sandbox; credentials stay server-side.

## Skill Boundary

This skill is installed into agent runtime prompts outside the source repository. Keep it self-contained and do not link to repository-local materials, source paths, or private maintenance notes.

If auth boundaries, action keys, or GitHub account selection behavior changes, update this prompt with the user-facing rules agents need at runtime. Keep implementation-only notes out of this public skill.

## Tool Selection

Use `connector-cli` directly for documented GitHub connector actions. Start with the action the task needs; do not run `command -v`, `which`, `env`, or similar executable/config probes before normal invocations. If the first direct invocation fails because `connector-cli`, `CONNECTOR_BASE_URL`, or runtime auth config is missing, diagnose PATH/config once with the smallest relevant check. Use the GitHub CLI (`gh`) only when the user explicitly asks for it or no connector action covers the task. Do not assume `GH_TOKEN` exists unless the environment confirms it.

## Native Git Setup

Prefer connector actions for GitHub reads and writes when a local checkout or native Git operation is not required.

Before running GitHub HTTPS commands such as `git clone`, `git fetch`, `git pull`, or `git push`, check whether Git already uses the connector credential helper:

```bash
git config --global --get credential.https://github.com.helper
git config --global --get credential.https://github.com.useHttpPath
```

Treat setup as complete only when the helper is exactly `!connector-cli github credential-helper` and `useHttpPath` is `true`. In connector-enabled sandbox runtimes where the connector runtime config is the intended GitHub auth source, if either value is missing or different, run:

```bash
connector-cli github setup-git
```

This setup is a routine preflight for native GitHub HTTPS Git operations in that runtime. Do not ask the user for confirmation before running it there. Outside connector-enabled sandbox runtimes, diagnose the Git configuration and ask before changing global Git credential settings. Keep the normal path low-noise: a brief note before first setup is enough, and explain details only if setup or credential resolution fails. Do not use `git credential fill`, inspect credential stores, print credentials, or persist credential material.

## Invocation

```bash
connector-cli provider invoke github.issue.create --input '{"repo":"org/repo","title":"Bug"}'
connector-cli provider invoke github.repository_contents.get --input '{"repo":"org/repo","path":"README.md","ref":"main"}'
connector-cli provider invoke github.issue.create --input-file input.json
```

`CONNECTOR_BASE_URL` must be available, and connector broker auth must come from the runtime config file or the `SANDBOX_TOKEN` local fallback. Assume the runtime config is already present and invoke first; only inspect status or environment after a missing-config or auth error. Do not print or persist `SANDBOX_TOKEN`.

Start with `connector-cli provider list` when routing across Providers. Use `connector-cli provider explain github` for GitHub boundaries and `connector-cli provider actions github` for the lightweight complete index. Load a long-tail action schema only with `connector-cli provider action explain <full-action-key>`.

## Progressive Action Discovery

Common actions are injected below this skill from the current Provider catalog as compact executable signatures. Use those signatures directly when they match the task. For a long-tail action, run `connector-cli provider actions <provider>`, then load exactly one schema with `connector-cli provider action explain <full-action-key>`. Never guess, infer, or invent an action key or parameter. Treat terminal `action_not_found` as final for the confirmed catalog version and do not refresh or retry it automatically.

## Result Handling

`connector-cli` outputs JSON with the provider payload under `.data`. For simple field extraction, filtering, or list formatting, pipe results to `jq` instead of writing a temporary Python script. Use Python only when the transformation is too complex for a small `jq` expression.

**Tip:** When you know which fields you need, pipe to `jq` directly to avoid processing large JSON outputs.

Common compact examples:

```bash
connector-cli provider invoke github.user.get --input '{}' \
  | jq '.data | {login, name, url: .html_url}'

connector-cli provider invoke github.issue.search --input '{"q":"is:pr author:YOUR_LOGIN archived:false","per_page":20}' \
  | jq '.data | {total_count, prs: [.items[] | {number, title, state, url: .html_url}]}'

connector-cli provider invoke github.issue.search --input '{"q":"is:issue assignee:YOUR_LOGIN state:open archived:false","per_page":20}' \
  | jq '.data | {total_count, issues: [.items[] | {number, title, state, url: .html_url}]}'
```

## Key Rules

- Use only params listed by `provider action explain`. Do not construct GitHub API URLs directly.
- Repositories use `owner/name` format. Issue and PR numbers are exact numeric GitHub numbers.
- `repository_contents.get` returns `content` as base64 — decode it before displaying to the user or passing to another action.
- Before write operations (file upsert, PR merge, workflow dispatch), confirm the target repo, ref, and user intent explicitly.
- Treat `pull_request.merge` and `workflow.dispatch` as high-risk — state the target ref and confirm before invoking.
- Do not claim a write succeeded until the provider response confirms it.

## Workflows

**Efficient data extraction example:**
```bash
# Get PR details with only needed fields
connector-cli provider invoke github.pull_request.get --input '{"repo":"org/repo","pull_number":123}' \
  | jq '.data | {number, title, state, mergeable, head: .head.ref, base: .base.ref}'
```

**Issue / PR triage:** Fetch title, state, author, labels, assignees, and URL. For PRs also include branch names, review decisions, mergeability, and failing checks. Separate verified provider data from inference.

**Code lookup:** Use exact refs (branch, tag, or commit SHA) when provided. Prefer `repository_contents.get` and `repository_tree.get` before falling back to external tooling. Remember to decode base64 `content` before use.

**Repository discovery:** For user-facing questions like "which repos can I access?", call `user_installations.list` first, then call `user_installation_repositories.list` with the selected `installation_id`. These actions expose only GitHub installations enabled in the connector; installed-but-not-enabled accounts are managed from connector settings, not agent discovery. Use `installation_repositories.list` only for background or installation-token diagnostics. Verify default branch, visibility, and archive state before acting.

**CI investigation:** List failing checks or workflow runs first. Quote only the smallest useful error fragment. Connect each failure to a likely path or command before recommending a fix.
