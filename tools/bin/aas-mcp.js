#!/usr/bin/env node
"use strict";

const path = require("node:path");
const { createVerifiedCatalogResolver } = require("../lib/aas-v1/cache/resolver");
const { compatible } = require("../lib/aas-v1/cache/catalog-release");
const { McpServer, runStdio } = require("../lib/aas-v1/mcp");

function parseArgs(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i], value = argv[i + 1];
    if (key === "--cache-root" && !options.cacheRoot && typeof value === "string" && path.isAbsolute(value) && !value.includes("\0")) options.cacheRoot = value;
    else if (key === "--catalog-digest" && !options.catalogDigest && /^sha256-[a-f0-9]{64}$/.test(value || "")) options.catalogDigest = value;
    else throw new Error("invalid MCP startup arguments");
  }
  if (options.catalogDigest && !options.cacheRoot) throw new Error("Pinned catalog requires a cache root");
  return options;
}

async function main() {
  const root = path.resolve(__dirname, "../..");
  const { cacheRoot, catalogDigest } = parseArgs(process.argv.slice(2));
  const catalogResolver = createVerifiedCatalogResolver({ cacheRoot, bundledRoot: root });
  if (!catalogDigest) return runStdio(new McpServer({ root, catalogResolver }));
  const catalog = await catalogResolver(catalogDigest);
  if (!catalog || (catalog.catalogRelease && !compatible(catalog.catalogRelease, require(path.join(root, "package.json")).version)))
    throw new Error("Pinned catalog unavailable or incompatible");
  runStdio(new McpServer({ root: catalog.sourceRoot || root, catalog, catalogResolver }));
}
if (require.main === module) main().catch(() => {
  process.stderr.write("AAS MCP startup failed (details redacted)\n");
  process.exitCode = 1;
});
module.exports = { parseArgs, main };
