"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),os=require("node:os"),path=require("node:path");
const {execFileSync}=require("node:child_process");
const {parsePackageArchive}=require("../../lib/aas-v1/cache/archive");
const root=fs.mkdtempSync(path.join(os.tmpdir(),"aas-portable-archive-"));
try{
 const stage=path.join(root,"stage");fs.mkdirSync(stage);
 const relative="skills/example/references/"+"日本語".repeat(20)+"à.md";
 const target=path.join(stage,relative);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,"verified unicode content",{mode:0o755});
 const pack=output=>execFileSync(process.execPath,[path.resolve(__dirname,"../run-python.js"),path.resolve(__dirname,"../catalog_archive.py"),stage,output],{stdio:["ignore","pipe","pipe"]});
 const first=path.join(root,"first.tgz"),second=path.join(root,"second.tgz");pack(first);
 const parsed=parsePackageArchive(fs.readFileSync(first));assert.equal(parsed.entries.length,1);assert.equal(parsed.entries[0].path,"package/"+relative);assert.equal(parsed.entries[0].bytes.toString(),"verified unicode content");assert.equal(parsed.entries[0].mode,0o644);
 fs.utimesSync(target,new Date(),new Date());pack(second);assert.deepEqual(fs.readFileSync(first),fs.readFileSync(second),"timestamps and output names must not change archive identity");
 fs.symlinkSync(target,path.join(stage,"link"));assert.throws(()=>pack(path.join(root,"unsafe.tgz")),/regular files and directories/);
 assert.equal(fs.existsSync(path.join(root,"unsafe.tgz")),false);
 console.log("Portable Unicode PAX archive, deterministic bytes and inert file tests passed");
}finally{fs.rmSync(root,{recursive:true,force:true});}
