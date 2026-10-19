"use strict";
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
// Only the dedicated legacy deployment invokes automatic public input resolution.
// Local generation and library callers remain deterministic and offline.
async function withPublishedInputs(options, operation, dependencies = {}) {
  if ((dependencies.repository ?? process.env.GITHUB_REPOSITORY) !== "ibrdot/ibrdot.github.io"
      || options.sitemapPath || options.skillsIndexPath) return operation(options);
  const proof = await (dependencies.proof || require("./catalog_public_verify.cjs").activeCatalogProof)(require("../../package.json").version);
  if (!proof) return operation(options);
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "aas-published-bridge-"));
  try {
    const sitemapPath=path.join(temporary,"sitemap.xml"),skillsIndexPath=path.join(temporary,"skills_index.json");
    fs.writeFileSync(sitemapPath,proof.sitemapBytes);fs.writeFileSync(skillsIndexPath,proof.skillsIndexBytes);
    return await operation({...options,sitemapPath,skillsIndexPath});
  } finally { fs.rmSync(temporary,{recursive:true,force:true}); }
}
module.exports={withPublishedInputs};
