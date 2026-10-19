#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { execFileSync } = require("node:child_process");
const MARKER = "data/distribution-snapshot.json";
function snapshot(root) {
  const raw = execFileSync("git", ["ls-files", "--stage", "-z"], { cwd: root, maxBuffer: 32 * 1024 * 1024 });
  const entries = raw.toString("utf8").split("\0").filter(Boolean).filter(entry => entry.split("\t")[1] !== MARKER);
  if (entries.some(entry => !/^[0-7]{6} [a-f0-9]{40} 0\t/.test(entry))) throw new Error("Unmerged or unsupported distribution index");
  return { schemaVersion: 1, version: JSON.parse(fs.readFileSync(path.join(root, "package.json"))).version,
    treeDigest: crypto.createHash("sha256").update(entries.join("\0") + "\0").digest("hex") };
}
function verify(root) {
  execFileSync("git", ["diff", "--exit-code"], { cwd: root, stdio: "pipe" });
  if (execFileSync("git", ["ls-files", "--others", "--exclude-standard"], { cwd: root, encoding: "utf8" }).trim())
    throw new Error("Untracked source files cannot enter a prepared distribution");
  const expected = snapshot(root);
  const actual = JSON.parse(fs.readFileSync(path.join(root, MARKER)));
  if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error("Unprepared development tree: run the protected release:prepare flow before packaging");
  return actual;
}
function seal(root) {
  const value = snapshot(root);
  fs.writeFileSync(path.join(root, MARKER), JSON.stringify(value) + "\n");
  return value;
}
if (require.main === module) {
  try {
    const mode = process.argv[2] || "verify";
    if (!["seal", "verify"].includes(mode)) throw new Error("Expected seal or verify");
    (mode === "seal" ? seal : verify)(path.resolve(__dirname, "../.."));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
module.exports = { snapshot, verify, seal, MARKER };
