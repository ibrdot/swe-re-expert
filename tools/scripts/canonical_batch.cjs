#!/usr/bin/env node
// Coordination is a bounded deployment lease, never authority to approve or merge.
const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const crypto = require("node:crypto");
const ENVIRONMENT = "aas-maintainer-batch";
const TTL_MS = 60 * 60 * 1000;
function api(repo, endpoint, data, execute = spawnSync) {
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/u.test(repo))
    throw new Error("Invalid repository");
  const args = ["api", `repos/${repo}/${endpoint}`];
  if (data !== undefined) args.push("-X", "POST", "--input", "-");
  const result = execute("gh", args, {
    input: data === undefined ? undefined : JSON.stringify(data),
    encoding: "utf8",
    timeout: 30000,
    maxBuffer: 4 * 1024 * 1024,
  });
  if (result.error || result.status !== 0)
    throw new Error(`Batch API ${endpoint}: ${result.stderr || result.error}`);
  return result.stdout.trim() ? JSON.parse(result.stdout) : null;
}
function validLease(deployment, repo) {
  const payload = deployment?.payload;
  const created = Date.parse(deployment?.created_at);
  const expires = Date.parse(payload?.expiresAt);
  return (
    deployment?.environment === ENVIRONMENT &&
    deployment?.creator?.login?.toLowerCase() ===
      repo.split("/")[0].toLowerCase() &&
    payload?.schemaVersion === 1 &&
    /^[0-9a-f]{40}$/u.test(payload.baseSha || "") &&
    /^[0-9a-f-]{36}$/u.test(payload.batchId || "") &&
    Number.isFinite(created) &&
    Number.isFinite(expires) &&
    expires > created &&
    expires - created <= TTL_MS + 10000
  );
}
function classifyLeases(rows, repo, now = Date.now()) {
  const leases = rows.filter(
    (row) =>
      validLease(row, repo) &&
      ["pending", "queued", "in_progress"].includes(row.state),
  );
  return {
    active: leases.filter((row) => Date.parse(row.payload.expiresAt) > now),
    expired: leases.filter((row) => Date.parse(row.payload.expiresAt) <= now),
  };
}
function readLeases(repo, request = api) {
  const rows = [];
  for (let page = 1; page <= 10; page++) {
    const part = request(
      repo,
      `deployments?environment=${ENVIRONMENT}&per_page=100&page=${page}`,
    );
    if (!Array.isArray(part)) throw new Error("Invalid deployment history");
    rows.push(...part);
    if (
      part.length < 100 ||
      part.some(
        (row) => Date.parse(row.created_at) < Date.now() - TTL_MS - 10000,
      )
    )
      break;
    if (page === 10)
      throw new Error("Too many deployments within the active lease window");
  }
  const eligible = rows.filter((row) => validLease(row, repo));
  // Keep the latest lease even after an arbitrarily long outage. A newer
  // completed batch already dispatched convergence for every older source commit.
  const candidates = eligible.filter(
    (row, index) =>
      index === 0 || Date.parse(row.created_at) >= Date.now() - TTL_MS - 10000,
  );
  return candidates.map((row) => ({
    ...row,
    state:
      request(repo, `deployments/${row.id}/statuses?per_page=1`)[0]?.state ||
      "pending",
  }));
}
function dispatch(repo, request = api) {
  request(repo, "actions/workflows/ci.yml/dispatches", { ref: "main" });
}
function beginBatch(repo, baseSha, prs, request = api) {
  if (classifyLeases(readLeases(repo, request), repo).active.length)
    throw new Error("Another maintainer batch is active");
  const deployment = request(repo, "deployments", {
    ref: baseSha,
    task: "aas-maintainer-batch",
    auto_merge: false,
    required_contexts: [],
    environment: ENVIRONMENT,
    transient_environment: true,
    production_environment: false,
    payload: {
      schemaVersion: 1,
      batchId: crypto.randomUUID(),
      baseSha,
      prs,
      expiresAt: new Date(Date.now() + TTL_MS).toISOString(),
    },
  });
  if (!Number.isSafeInteger(deployment?.id))
    throw new Error("Batch lease was not created");
  request(repo, `deployments/${deployment.id}/statuses`, {
    state: "in_progress",
    auto_inactive: false,
    description:
      "Source batch active; canonical convergence deferred for at most one hour",
  });
  return deployment.id;
}
function assertBatch(repo, id, request = api) {
  const { active } = classifyLeases(readLeases(repo, request), repo);
  if (active.length !== 1 || active[0].id !== id)
    throw new Error(
      "Batch lease expired or competing batch detected; restart from current main",
    );
}
function finishBatch(repo, id, success, request = api) {
  request(repo, `deployments/${id}/statuses`, {
    state: success ? "success" : "failure",
    auto_inactive: false,
    description: "Source batch ended; dispatching protected main convergence",
  });
  try {
    dispatch(repo, request);
  } catch (error) {
    request(repo, `deployments/${id}/statuses`, {
      state: "in_progress",
      auto_inactive: false,
      description:
        "Convergence dispatch failed; bounded lease recovery remains pending",
    });
    throw error;
  }
}
function decide({ currentSha, expectedSha, leases, recovery = false }) {
  if (expectedSha !== currentSha)
    return { shouldRun: false, reason: "superseded-main" };
  if (leases.active.length) return { shouldRun: false, reason: "active-batch" };
  if (recovery && !leases.expired.length)
    return { shouldRun: false, reason: "no-expired-batch" };
  return {
    shouldRun: true,
    reason: recovery ? "expired-batch-recovery" : "current-main",
  };
}
function main() {
  const repo = process.env.GITHUB_REPOSITORY;
  const command = process.argv[2];
  const rows = readLeases(repo);
  const leases = classifyLeases(rows, repo);
  const currentSha = api(repo, "commits/main").sha;
  const decision = decide({
    currentSha,
    expectedSha: command === "recover" ? currentSha : process.env.GITHUB_SHA,
    leases,
    recovery: command === "recover",
  });
  if (command === "recover" && decision.shouldRun) {
    // Dispatch before closing: a failed dispatch leaves an expired lease for the next recovery run.
    dispatch(repo);
    for (const row of leases.expired)
      api(repo, `deployments/${row.id}/statuses`, {
        state: "failure",
        auto_inactive: false,
        description: "Expired batch recovered through protected main CI",
      });
  } else if (command !== "check" && command !== "recover")
    throw new Error("Expected check or recover");
  if (process.env.GITHUB_OUTPUT)
    fs.appendFileSync(
      process.env.GITHUB_OUTPUT,
      `should_run=${decision.shouldRun}\nreason=${decision.reason}\n`,
    );
  console.log(JSON.stringify(decision));
}
if (require.main === module) main();
module.exports = {
  api,
  beginBatch,
  assertBatch,
  finishBatch,
  classifyLeases,
  validLease,
  decide,
  readLeases,
};
