const assert = require("node:assert/strict");
const { trustedRun } = require("../distribution_fetch.cjs");
const expected = { repository: "owner/repo", commit: "a".repeat(40), tag: "v20.0.0" };
const run = { head_sha: expected.commit, repository: { full_name: expected.repository }, head_repository: { full_name: expected.repository }, path: ".github/workflows/distribution-candidate.yml", event: "push", head_branch: expected.tag, status: "completed", conclusion: "success", id: 42, run_attempt: 1 };
assert.equal(trustedRun(run, expected), true);
for (const override of [{head_sha: "b".repeat(40)}, {head_repository:{full_name:"attacker/repo"}}, {repository:{full_name:"attacker/repo"}}, {event:"pull_request"}, {path:".github/workflows/ci.yml"}, {head_branch:"main"}, {status:"in_progress"}, {conclusion:"skipped"}, {run_attempt:0}]) assert.equal(trustedRun({...run,...override}, expected), false);
console.log("Trusted distribution origin and completion tests passed");
