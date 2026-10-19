const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const { seal, verify } = require("../distribution_snapshot.cjs");
const root = fs.mkdtempSync(path.join(os.tmpdir(), "aas-snapshot-"));
const git = (...args) => execFileSync("git", args, { cwd: root, stdio: "pipe" });
try {
  git("init");
  fs.mkdirSync(path.join(root, "data"));
  fs.writeFileSync(path.join(root, "package.json"), '{"version":"20.0.0"}');
  fs.writeFileSync(path.join(root, "source.js"), "original");
  git("add", ".");
  seal(root);
  git("add", ".");
  assert.equal(verify(root).version, "20.0.0");
  fs.writeFileSync(path.join(root, "source.js"), "changed");
  assert.throws(() => verify(root));
  git("add", ".");
  assert.throws(() => verify(root), /Unprepared/);
  seal(root);
  git("add", ".");
  assert.doesNotThrow(() => verify(root));
  git("update-index", "--chmod=+x", "source.js");
  assert.throws(() => verify(root));
} finally { fs.rmSync(root, { recursive: true, force: true }); }
console.log("Distribution snapshot rejects unstaged, staged, and mode drift");
