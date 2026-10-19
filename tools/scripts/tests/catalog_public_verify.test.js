"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),os=require("node:os"),path=require("node:path"),crypto=require("node:crypto");
const {execFileSync}=require("node:child_process");
const {activeCatalogProof}=require("../catalog_public_verify.cjs");
const {withPublishedInputs}=require("../published_bridge_inputs.cjs");
const {sha256}=require("../../lib/aas-v1/canonical-json");
(async()=>{
 const root=fs.mkdtempSync(path.join(os.tmpdir(),"aas-public-proof-"));
 try {
  const commit="a".repeat(40),index=Buffer.from('[{"id":"example","path":"skills/example"}]'),sitemap=Buffer.from('<urlset/>');
  const manifest={catalogDigest:"sha256-"+"b".repeat(64),catalogRelease:{schemaVersion:1,sourceCommit:commit,runtimeMajor:19,minimumRuntime:"19.10.0"}};
  fs.mkdirSync(path.join(root,"package/data/aas-v1"),{recursive:true});
  fs.writeFileSync(path.join(root,"package/skills_index.json"),index);
  fs.writeFileSync(path.join(root,"package/data/aas-v1/catalog-manifest.v1.json"),JSON.stringify(manifest));
  execFileSync("tar",["-czf",path.join(root,"catalog.tgz"),"-C",root,"package"]);
  const archive=fs.readFileSync(path.join(root,"catalog.tgz"));
  const descriptor={revision:"2026.10.18",sourceCommit:commit,catalogDigest:manifest.catalogDigest,skillsIndexDigest:sha256(index),sitemapDigest:sha256(sitemap),pluginCount:2,integrity:"sha512-"+crypto.createHash("sha512").update(archive).digest("base64"),provenance:{repository:"ibrdot/swe-re-expert",workflow:".github/workflows/catalog-distribution.yml",runId:123,runAttempt:1}};
  let conclusion="success",liveSitemap=sitemap;
  const deps={fetch:async url=>url.endsWith("catalog-release.json")?{ok:true,text:async()=>JSON.stringify(descriptor)}:{ok:true,arrayBuffer:async()=>liveSitemap},fetchReleaseBytes:async()=>archive,gh:args=>{
   if(args[0]==="release")return JSON.stringify(descriptor);
   const endpoint=args[1];let result;
   if(endpoint.includes("git/ref"))result={object:{type:"commit",sha:commit}};
   else if(endpoint.includes("releases/tags"))result={draft:false,published_at:"2026-10-18"};
   else if(endpoint.endsWith("branches/main"))result={protected:true,commit:{sha:commit}};
   else if(endpoint.includes("compare/"))result={merge_base_commit:{sha:commit},status:"identical"};
   else result={head_sha:commit,path:descriptor.provenance.workflow,event:"workflow_dispatch",head_branch:"main",repository:{full_name:descriptor.provenance.repository},head_repository:{full_name:descriptor.provenance.repository},status:"completed",conclusion,run_attempt:1};
   return JSON.stringify(result);
  }};
  const shell = "<!doctype html><html>app</html>";
  const html = text => ({ok:true,status:200,headers:{get:()=>"text/html; charset=utf-8"},text:async()=>text});
  assert.equal(await activeCatalogProof("19.10.1",{fetch:async()=>html(shell)}),null);
  await assert.rejects(activeCatalogProof("19.10.1",{fetch:async url=>html(url.endsWith(".json")?"unexpected":shell)}),/Unexpected HTML/);
  await assert.rejects(activeCatalogProof("19.10.1",{fetch:async()=>({ok:true,status:200,headers:{get:()=>"application/json"},text:async()=>shell})}),/JSON|Unexpected token/);
  const proof=await activeCatalogProof("19.10.0",deps);assert.equal(proof.skills.length,1);
  conclusion="failure";await assert.rejects(activeCatalogProof("19.10.0",deps),/trusted run/);conclusion="success";
  liveSitemap=Buffer.from("changed");await assert.rejects(activeCatalogProof("19.10.0",deps),/sitemap differs/);liveSitemap=sitemap;
  await assert.rejects(activeCatalogProof("19.9.0",deps),/compatibility/);
  let captured;
  await withPublishedInputs({},options=>{captured=options.skillsIndexPath;assert.deepEqual(fs.readFileSync(captured),index)},{repository:"ibrdot/ibrdot.github.io",proof:async()=>proof});
  assert.equal(fs.existsSync(captured),false);
  await withPublishedInputs({},options=>assert.equal(options.skillsIndexPath,undefined),{repository:"local",proof:async()=>{throw Error("network forbidden")}});
  console.log("Published catalog provenance, sitemap integrity and bridge input regressions passed");
 }finally{fs.rmSync(root,{recursive:true,force:true})}
})().catch(error=>{console.error(error);process.exitCode=1});
