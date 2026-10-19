#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const crypto = require("node:crypto");
const { execFileSync } = require("node:child_process");
const { canonicalJson, sha256 } = require("../lib/aas-v1/canonical-json");
const { validatePackageVersion } = require("../lib/aas-v1/cache/identity");
const { CATALOG_ASSET_PATHS, CATALOG_MANIFEST_PATH } = require("../lib/aas-v1/cache/update");
const { validateRelativeAssetPath } = require("../lib/aas-v1/cache/scan");
const { loadBundledCatalog } = require("../lib/aas-v1/catalog");
function build(root, revision, output) {
  validatePackageVersion(revision);
  fs.mkdirSync(output, { recursive: true });
  if (fs.readdirSync(output).length) throw new Error("Catalog output must be empty");
  const sourceCommit = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim();
  const runtimeVersion = JSON.parse(fs.readFileSync(path.join(root, "package.json"))).version;
  const manifest = JSON.parse(fs.readFileSync(path.join(root, CATALOG_MANIFEST_PATH)));
  const index = JSON.parse(fs.readFileSync(path.join(root, "skills_index.json")));
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aas-catalog-build-"));
  const stage = path.join(temporary, "package");
  fs.mkdirSync(stage);
  const assets = [];
  const skillsRoot = fs.realpathSync(path.join(root, "skills"));
  function copy(source, relative, ancestry = new Set()) {
    const real = fs.realpathSync(source);
    if (relative.startsWith("skills/") && real !== skillsRoot && !real.startsWith(skillsRoot + path.sep)) throw new Error("Skill link leaves canonical source tree");
    const stat = fs.statSync(real);
    if (stat.isDirectory()) {
      if (ancestry.has(real)) throw new Error("Cyclic skill directory link");
      for (const name of fs.readdirSync(real).sort()) copy(path.join(real, name), `${relative}/${name}`, new Set([...ancestry, real]));
    } else {
      if (!stat.isFile() || stat.size > 32 * 1024 * 1024) throw new Error("Unsupported catalog file");
      const bytes = fs.readFileSync(real);
      const target = path.join(stage, relative);
      fs.mkdirSync(path.dirname(target), { recursive: true, mode: 0o755 });
      if (fs.existsSync(target)) return;
      fs.writeFileSync(target, bytes, { mode: 0o644, flag: "wx" });
      assets.push({ path: relative, size: bytes.length, sha256: sha256(bytes) });
    }
  }
  try {
    for (const file of [...CATALOG_ASSET_PATHS, "skills_index.json"]) copy(path.join(root, file), file);
    for (const entry of index) {
      validateRelativeAssetPath(entry.path);
      if (!entry.path.startsWith("skills/")) throw new Error("Unsupported catalog installation path");
      copy(path.join(root, entry.path), entry.path);
    }
    // Internal links become inert regular files in the data distribution.
    // Bind the file inventory to those actual normalized bytes as well.
    const contentPath = "data/aas-v1/skill-content-index.v1.json";
    const contentIndex = JSON.parse(fs.readFileSync(path.join(stage, contentPath)));
    const assetsByPath = new Map(assets.map(asset => [asset.path, asset]));
    for (const entry of index) {
      const content = contentIndex.entries[entry.id];
      if (!content?.files) continue;
      content.files = content.files.map(file => {
        if (file.type !== "symlink") return file;
        const actual = assetsByPath.get(`${entry.path}/${file.path}`);
        if (!actual) throw new Error("Materialized link has no verified asset");
        return { path: file.path, type: "file", size: actual.size, sha256: actual.sha256 };
      });
    }
    const normalizedIndex = Buffer.from(canonicalJson(contentIndex) + "\n");
    fs.writeFileSync(path.join(stage, contentPath), normalizedIndex);
    Object.assign(assetsByPath.get(contentPath), { size: normalizedIndex.length, sha256: sha256(normalizedIndex) });
    assets.sort((a,b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0);
    const release = { ...manifest, packageVersion: revision, assets,
      catalogDigest: sha256(canonicalJson({ digestVersion: 1, assets })),
      catalogRelease: { schemaVersion: 1, sourceCommit, minimumRuntime: runtimeVersion, runtimeMajor: Number(runtimeVersion.split(".")[0]) } };
    fs.writeFileSync(path.join(stage, CATALOG_MANIFEST_PATH), canonicalJson(release) + "\n");
    loadBundledCatalog({ root: stage });
    const tarball = path.join(output, "catalog.tgz");
    execFileSync(process.execPath, [path.join(__dirname, "run-python.js"), path.join(__dirname, "catalog_archive.py"), stage, tarball], { stdio: "inherit" });
    const integrity = `sha512-${crypto.createHash("sha512").update(fs.readFileSync(tarball)).digest("base64")}`;
    const descriptor = { schemaVersion: 1, revision, sourceCommit, minimumRuntime: release.catalogRelease.minimumRuntime, runtimeMajor: release.catalogRelease.runtimeMajor,
      catalogSchemaVersion: manifest.catalogSchemaVersion, catalogDigest: release.catalogDigest, integrity,
      skillsIndexDigest: sha256(fs.readFileSync(path.join(stage, "skills_index.json"))),
      ...(process.env.GITHUB_RUN_ID ? { provenance: { repository: process.env.GITHUB_REPOSITORY,
        workflow: ".github/workflows/catalog-distribution.yml", runId: process.env.GITHUB_RUN_ID, runAttempt: process.env.GITHUB_RUN_ATTEMPT } } : {}) };
    fs.writeFileSync(path.join(output, "catalog-release.json"), JSON.stringify(descriptor, null, 2) + "\n");
    return descriptor;
  } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
}
if (require.main === module) {
  try {
    const [revision, output] = process.argv.slice(2);
    if (!revision || !output) throw new Error("Usage: catalog_distribution.cjs REVISION EMPTY_OUTPUT_DIRECTORY");
    console.log(JSON.stringify(build(path.resolve(__dirname, "../.."), revision, path.resolve(output)), null, 2));
  } catch (error) { console.error(error.stack); process.exitCode = 1; }
}
module.exports = { build };
