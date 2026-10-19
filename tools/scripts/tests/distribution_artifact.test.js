const assert = require("node:assert/strict");
const fs = require("node:fs"), os = require("node:os"), path = require("node:path");
const { createManifest, verifyManifest } = require("../../lib/distribution-artifact");
const root = fs.mkdtempSync(path.join(os.tmpdir(), "aas-distribution-test-"));
try {
  fs.writeFileSync(path.join(root, "package.tgz"), "package");
  fs.writeFileSync(path.join(root, "site.tar"), "site");
  const provenance = { commit: "a".repeat(40), version: "20.0.0", runId: "12", runAttempt: "1", repository: "owner/repo", workflow: ".github/workflows/distribution-candidate.yml", lockfileDigest: "b".repeat(64) };
  const manifest = createManifest(root, provenance);
  assert(verifyManifest(root, manifest, provenance));
  assert.equal(manifest.toolchain.node, process.version);
  assert.throws(() => verifyManifest(root, { ...manifest, toolchain: undefined }, provenance), /toolchain/);
  for (const key of ["commit", "version", "runId", "runAttempt", "repository", "workflow", "lockfileDigest"])
    assert.throws(() => verifyManifest(root, manifest, { ...provenance, [key]: "invalid" }));
  assert.throws(() => verifyManifest(root, { ...manifest, artifacts: [] }, provenance), /Incomplete/);
  assert.throws(() => verifyManifest(root, { ...manifest, artifacts: [manifest.artifacts[0], manifest.artifacts[0]] }, provenance), /Duplicate/);
  fs.writeFileSync(path.join(root, "package.tgz"), "tampered");
  assert.throws(() => verifyManifest(root, manifest, provenance), /digest mismatch/);
  fs.rmSync(path.join(root, "package.tgz")); fs.symlinkSync(path.join(root, "site.tar"), path.join(root, "package.tgz"));
  assert.throws(() => verifyManifest(root, manifest, provenance), /Unsafe/);
} finally { fs.rmSync(root, { recursive: true, force: true }); }
console.log("distribution provenance and integrity tests passed");
