#!/usr/bin/env node
"use strict";
const { execFileSync } = require("node:child_process");
const { fetchReleaseBytes, compatible } = require("../lib/aas-v1/cache/catalog-release");
const { parsePackageArchive } = require("../lib/aas-v1/cache/archive");
const { verifySri } = require("../lib/aas-v1/cache/update");
const { canonicalJson, sha256 } = require("../lib/aas-v1/canonical-json");
const REPOSITORY = "ibrdot/swe-re-expert";
async function activeCatalogProof(runtimeVersion, dependencies = {}) {
  const fetch = dependencies.fetch || globalThis.fetch;
  const response = await fetch("https://github.com/ibrdot/swe-re-expert/catalog-release.json", { redirect: "error", signal: AbortSignal.timeout(30000) });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Live catalog descriptor returned ${response.status}`);
  const text = await response.text();
  if (Buffer.byteLength(text) > 128 * 1024) throw new Error("Oversized catalog descriptor");
  // Static SPA hosts may serve the exact app shell with HTTP 200 for a missing
  // optional descriptor. Only that byte-identical HTML response is absence;
  // malformed JSON and unrelated HTML remain failures. Callers still verify
  // the embedded runtime catalog and sitemap when this returns null.
  if (/^text\/html(?:;|$)/i.test(response.headers?.get("content-type") || "")) {
    const home = await fetch("https://github.com/ibrdot/swe-re-expert/", { redirect: "error", signal: AbortSignal.timeout(30000) });
    const homeText = home.ok ? await home.text() : "";
    if (!home.ok || !/^text\/html(?:;|$)/i.test(home.headers?.get("content-type") || "")
        || Buffer.byteLength(homeText) > 128 * 1024 || homeText !== text)
      throw new Error("Unexpected HTML catalog descriptor");
    return null;
  }
  const descriptor = JSON.parse(text);
  const gh = dependencies.gh || (args => execFileSync("gh", args, { encoding: "utf8", maxBuffer: 2 * 1024 * 1024 }));
  const api = endpoint => JSON.parse(gh(["api", `repos/${REPOSITORY}/${endpoint}`]));
  require("../lib/aas-v1/cache/identity").validatePackageVersion(descriptor.revision);
  const tag = `catalog-v${descriptor.revision}`;
  const published = JSON.parse(gh(["release", "download", tag, "--repo", REPOSITORY, "--pattern", "catalog-release.json", "--output", "-"]));
  if (canonicalJson(published) !== canonicalJson(descriptor)) throw new Error("Live catalog descriptor differs from published immutable release");
  if (!/^[a-f0-9]{40}$/.test(descriptor.sourceCommit || "")) throw new Error("Invalid catalog source commit");
  const tagRef = api(`git/ref/tags/${tag}`).object;
  const commit = tagRef.type === "tag" ? api(`git/tags/${tagRef.sha}`).object.sha : tagRef.sha;
  const release = api(`releases/tags/${tag}`);
  if (commit !== descriptor.sourceCommit || release.draft || !release.published_at) throw new Error("Catalog tag/release provenance mismatch");
  const main = api("branches/main");
  const comparison = api(`compare/${commit}...${main.commit.sha}`);
  if (!main.protected || comparison.merge_base_commit?.sha !== commit || !["ahead","identical"].includes(comparison.status)) throw new Error("Catalog source is not protected-main ancestry");
  const provenance = descriptor.provenance;
  if (!provenance || provenance.repository !== REPOSITORY || provenance.workflow !== ".github/workflows/catalog-distribution.yml" || !/^\d+$/.test(String(provenance.runId))) throw new Error("Catalog workflow provenance missing");
  const run = api(`actions/runs/${provenance.runId}`);
  if (run.head_sha !== commit || run.path !== provenance.workflow || run.event !== "workflow_dispatch" || run.head_branch !== "main"
      || run.repository?.full_name !== REPOSITORY || run.head_repository?.full_name !== REPOSITORY || run.status !== "completed" || run.conclusion !== "success" || run.run_attempt !== Number(provenance.runAttempt))
    throw new Error("Catalog distribution workflow is not a complete trusted run");
  const archive = await (dependencies.fetchReleaseBytes || fetchReleaseBytes)(`https://github.com/${REPOSITORY}/releases/download/${tag}/catalog.tgz`,64*1024*1024);
  verifySri(archive, descriptor.integrity);
  const selected = parsePackageArchive(archive, { selectPaths: ["package/skills_index.json","package/data/aas-v1/catalog-manifest.v1.json"], limits: {maxEntries:40000,maxExpandedTotalBytes:256*1024*1024} });
  const files = new Map(selected.entries.map(entry => [entry.path,entry.bytes]));
  const manifest = JSON.parse(files.get("package/data/aas-v1/catalog-manifest.v1.json"));
  const indexBytes = files.get("package/skills_index.json");
  if (!compatible(manifest.catalogRelease,runtimeVersion) || manifest.catalogRelease.sourceCommit !== commit
      || manifest.catalogDigest !== descriptor.catalogDigest || sha256(indexBytes) !== descriptor.skillsIndexDigest)
    throw new Error("Published catalog identity or runtime compatibility mismatch");
  const sitemapResponse = await fetch("https://github.com/ibrdot/swe-re-expert/sitemap.xml", { redirect: "error", signal: AbortSignal.timeout(30000) });
  if (!sitemapResponse.ok) throw new Error("Live sitemap unavailable");
  const sitemapBytes = Buffer.from(await sitemapResponse.arrayBuffer());
  if (sitemapBytes.length > 4*1024*1024 || sha256(sitemapBytes) !== descriptor.sitemapDigest) throw new Error("Live sitemap differs from published catalog");
  if (!Number.isSafeInteger(descriptor.pluginCount) || descriptor.pluginCount < 1) throw new Error("Invalid published plugin count");
  return { sitemapBytes, descriptor, skills: JSON.parse(indexBytes), skillsIndexBytes: indexBytes };
}
if(require.main===module) activeCatalogProof(process.argv[2]).then(result=>{
  if(!result) throw new Error("No independent catalog deployed");
  console.log(JSON.stringify({verified:true,...result.descriptor,skillCount:result.skills.length},null,2));
}).catch(error=>{console.error(error.message);process.exitCode=1});
module.exports={activeCatalogProof};
