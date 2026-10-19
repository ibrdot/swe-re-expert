"use strict";
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const https = require("node:https");
const { canonicalJson } = require("../canonical-json");
const { parsePackageArchive } = require("./archive");
const { validatePackageVersion, cacheError } = require("./identity");
const { validateRelativeAssetPath } = require("./scan");
const { verifySri, CATALOG_MANIFEST_PATH, CATALOG_ASSET_PATHS } = require("./update");
const { promoteCatalogDirectory } = require("./promote");
const { loadBundledCatalog } = require("../catalog");
const LIMITS = Object.freeze({ maxFiles: 20000, maxEntries: 40000, maxFileBytes: 32 * 1024 * 1024, maxTotalBytes: 256 * 1024 * 1024, maxDepth: 32 });
function compatible(release, runtimeVersion) {
  if (release?.schemaVersion !== 1 || !Number.isSafeInteger(release.runtimeMajor)
      || typeof release.minimumRuntime !== "string") return false;
  const parse = value => /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.exec(value);
  const actual = parse(runtimeVersion), minimum = parse(release.minimumRuntime);
  if (!actual || !minimum || Number(minimum[1]) < 19 || (Number(minimum[1]) === 19 && Number(minimum[2]) < 10)
      || Number(actual[1]) !== release.runtimeMajor || Number(minimum[1]) !== release.runtimeMajor) return false;
  for (let i = 1; i <= 3; i++) { if (+actual[i] !== +minimum[i]) return +actual[i] > +minimum[i]; }
  return true;
}
function fetchReleaseBytes(url, maximumBytes, redirects = 0) {
  const parsed = new URL(url);
  if (parsed.protocol !== "https:" || parsed.username || parsed.password
      || !["github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"].includes(parsed.hostname)
      || parsed.port || redirects > 3) return Promise.reject(new Error("Untrusted catalog download origin"));
  return new Promise((resolve, reject) => {
    const request = https.get(parsed, { timeout: 15000, headers: { "user-agent": "aas-catalog-release-v1" } }, response => {
      if ([301,302,303,307,308].includes(response.statusCode)) {
        response.resume();
        try { resolve(fetchReleaseBytes(new URL(response.headers.location, parsed).href, maximumBytes, redirects + 1)); }
        catch (error) { reject(error); }
        return;
      }
      if (response.statusCode !== 200) { response.resume(); reject(new Error(`Catalog download returned ${response.statusCode}`)); return; }
      const chunks = []; let size = 0;
      response.on("data", bytes => { size += bytes.length; if (size > maximumBytes) response.destroy(new Error("Catalog download limit exceeded")); else chunks.push(bytes); });
      response.on("error", reject);
      response.on("end", () => resolve(Buffer.concat(chunks)));
    });
    request.on("timeout", () => request.destroy(new Error("Catalog download timed out")));
    request.on("error", reject);
  });
}
async function updateCatalogRelease({ cacheRoot, revision, integrity, archive, runtimeVersion, fetcher = fetchReleaseBytes }) {
  validatePackageVersion(revision);
  if (archive) {
    const stat = fs.lstatSync(archive);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 64 * 1024 * 1024) throw new Error("Unsafe catalog archive");
  }
  const bytes = archive ? fs.readFileSync(archive) : await fetcher(`https://github.com/ibrdot/swe-re-expert/releases/download/catalog-v${revision}/catalog.tgz`, 64 * 1024 * 1024);
  if (bytes.length > 64 * 1024 * 1024) throw new Error("Catalog archive limit exceeded");
  verifySri(bytes, integrity);
  const parsed = parsePackageArchive(bytes, { limits: { maxEntries: 40000, maxExpandedTotalBytes: LIMITS.maxTotalBytes } });
  const entries = new Map(parsed.entries.map(entry => [entry.path.replace(/^package\//, ""), entry]));
  const control = entries.get(CATALOG_MANIFEST_PATH);
  if (!control) throw new Error("Catalog manifest missing");
  const manifest = JSON.parse(control.bytes);
  if (manifest.packageVersion !== revision || !compatible(manifest.catalogRelease, runtimeVersion)
      || !/^[a-f0-9]{40}$/.test(manifest.catalogRelease.sourceCommit || ""))
    throw cacheError("AAS_CATALOG_RELEASE_INCOMPATIBLE", "catalog revision or runtime compatibility mismatch");
  const paths = manifest.assets.map(asset => validateRelativeAssetPath(asset.path));
  if (new Set(paths).size !== paths.length || ![...CATALOG_ASSET_PATHS, "skills_index.json"].every(file => paths.includes(file))
      || paths.some(file => !CATALOG_ASSET_PATHS.includes(file) && file !== "skills_index.json" && !file.startsWith("skills/")))
    throw new Error("Independent catalog asset allowlist invalid");
  if (entries.size !== paths.length + 1 || [...entries.keys()].some(file => file !== CATALOG_MANIFEST_PATH && !paths.includes(file)))
    throw new Error("Independent catalog contains undeclared files");
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aas-catalog-release-"));
  try {
    for (const [file, entry] of entries) {
      validateRelativeAssetPath(file);
      if (!entry.path.startsWith("package/")) throw new Error("Catalog archive root invalid");
      const output = path.join(temporary, file);
      fs.mkdirSync(path.dirname(output), { recursive: true, mode: 0o700 });
      fs.writeFileSync(output, entry.bytes, { mode: 0o600, flag: "wx" });
    }
    const catalog = loadBundledCatalog({ root: temporary });
    const index = JSON.parse(fs.readFileSync(path.join(temporary, "skills_index.json")));
    if (!Array.isArray(index) || new Set(index.map(entry => entry.id)).size !== index.length
        || canonicalJson(index.map(entry => entry.id).sort()) !== canonicalJson(catalog.skills.map(entry => entry.id).sort()))
      throw new Error("Catalog installation index disagrees with verified catalog");
    for (const entry of index) {
      validateRelativeAssetPath(entry.path);
      if (!entry.path.startsWith("skills/") || !paths.includes(`${entry.path}/SKILL.md`)
          || catalog.skills.find(skill => skill.id === entry.id)?.untrustedContentPath !== `${entry.path}/SKILL.md`)
        throw new Error("Catalog installation index is not confined to verified skill trees");
    }
    const promoted = await promoteCatalogDirectory({ cacheRoot, sourceDir: temporary, allowlist: paths,
      controlPaths: [CATALOG_MANIFEST_PATH], limits: LIMITS,
      identity: { schemaVersion: 1, package: manifest.package, version: revision, integrity, catalogDigest: catalog.digest } });
    return { ok: true, status: promoted.status, identity: { package: promoted.identity.package, version: promoted.identity.version, catalogDigest: promoted.identity.catalogDigest, integrity: promoted.identity.integrity }, catalogRelease: manifest.catalogRelease };
  } finally { fs.rmSync(temporary, { recursive: true, force: true }); }
}
module.exports = { compatible, fetchReleaseBytes, updateCatalogRelease, CATALOG_RELEASE_LIMITS: LIMITS };
