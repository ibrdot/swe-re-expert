"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), os = require("node:os"), path = require("node:path");
const { execFileSync } = require("node:child_process");
const { lockfileDigest } = require("../distribution_manifest.cjs");
const { digest } = require("../../lib/distribution-artifact");
const root = fs.mkdtempSync(path.join(os.tmpdir(), "aas-lockfile-platform-"));
try {
  const git = args => execFileSync("git", args, { cwd: root, stdio: ["ignore", "pipe", "pipe"] });
  git(["init"]);
  git(["config", "core.autocrlf", "false"]);
  const original = '{\n  "lockfileVersion": 3\n}\n';
  fs.writeFileSync(path.join(root, "package-lock.json"), original);
  git(["add", "package-lock.json"]);
  git(["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "locked"]);
  assert.equal(lockfileDigest(root), digest(Buffer.from(original)));
  fs.writeFileSync(path.join(root, "package-lock.json"), original.replace(/\n/g, "\r\n"));
  assert.equal(lockfileDigest(root), digest(Buffer.from(original)), "checkout CRLF must not change committed provenance");
  fs.writeFileSync(path.join(root, "package-lock.json"), '{"changed":true}\n');
  git(["add", "package-lock.json"]);
  git(["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", "changed"]);
  assert.notEqual(lockfileDigest(root), digest(Buffer.from(original)), "changed committed lockfile must invalidate provenance");
} finally { fs.rmSync(root, { recursive: true, force: true }); }
const workflow = require("yaml").parse(fs.readFileSync(path.resolve(__dirname, "../../../.github/workflows/distribution-candidate.yml"), "utf8"));
const matrix = workflow.jobs.functional.strategy.matrix.include;
assert.deepEqual(matrix.map(entry => entry["job-id"]).sort(), ["linux-node-22", "linux-node-24", "windows-node-22", "windows-node-24"]);
for (const entry of matrix) {
  assert.match(entry["job-id"], /^(linux|macos|windows)-node-(22|24)$/);
  assert(entry["job-id"].endsWith(`-node-${String(entry.node).split(".")[0]}`));
  assert.equal(entry["job-id"].startsWith("windows"), entry.os.startsWith("windows"));
}
assert(workflow.jobs.functional.steps.find(step => step.name === "Install and exercise exact packed product").run.includes('${{ matrix.job-id }}'));
console.log("Cross-platform immutable lockfile and functional job contracts passed");
