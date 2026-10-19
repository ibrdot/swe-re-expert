#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { updateCatalogRelease } = require("../lib/aas-v1/cache/catalog-release");
const { catalogStatus } = require("../lib/aas-v1/cache/status");
async function main(directory) {
  const descriptor = JSON.parse(fs.readFileSync(path.join(directory, "catalog-release.json")));
  const cacheRoot = fs.mkdtempSync(path.join(os.tmpdir(), "aas-catalog-proof-"));
  try {
    const result = await updateCatalogRelease({ cacheRoot, revision: descriptor.revision, integrity: descriptor.integrity,
      archive: path.join(directory, "catalog.tgz"), runtimeVersion: require("../../package.json").version });
    const status = await catalogStatus({ cacheRoot, packageVersion: descriptor.revision, catalogDigest: descriptor.catalogDigest, integrity: descriptor.integrity });
    if (status.status !== "verified" || result.catalogRelease.sourceCommit !== descriptor.sourceCommit)
      throw new Error("Independent catalog verification failed");
    console.log(JSON.stringify({ ...descriptor, verified: true }));
  } finally { fs.rmSync(cacheRoot, { recursive: true, force: true }); }
}
if (require.main === module) main(path.resolve(process.argv[2])).catch(error => { console.error(error); process.exitCode = 1; });
module.exports = { main };
