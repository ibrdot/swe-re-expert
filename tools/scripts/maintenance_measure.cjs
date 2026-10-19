#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const { execFileSync } = require("node:child_process");
function summarize(runs, scope) {
  if (!runs.length || !["editorial", "catalog", "runtime-release", "catalog-release", "full"].includes(scope)) throw new Error("An explicit comparable scope and nonempty runs are required");
  const observations = runs.map(({run,jobs}) => {
    if (run.status !== "completed" || !jobs.length || jobs.some(job=>job.status !== "completed")) throw new Error("Incomplete cycle cannot be measured as complete");
    const start = Date.parse(run.created_at), end = Math.max(...jobs.map(job=>Date.parse(job.completed_at)));
    if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) throw new Error("Invalid run timing");
    return { id: run.id, workflow: run.path, commit: run.head_sha, conclusion: run.conclusion,
      createdAt: run.created_at, completedAt: new Date(end).toISOString(), elapsedMs: end-start,
      firstJobWaitMs: Math.max(0,Math.min(...jobs.map(job=>Date.parse(job.started_at)))-start),
      runnerMs: jobs.reduce((sum,job)=>sum+Math.max(0,Date.parse(job.completed_at)-Date.parse(job.started_at)),0) };
  });
  const startedAt=Math.min(...observations.map(run=>Date.parse(run.createdAt)));
  const completedAt=Math.max(...observations.map(run=>Date.parse(run.completedAt)));
  return {schemaVersion:1,scope,measurement:"observed-github-workflow-cycle",startedAt:new Date(startedAt).toISOString(),completedAt:new Date(completedAt).toISOString(),elapsedMs:completedAt-startedAt,
    successful:observations.every(run=>run.conclusion==="success"),runs:observations,
    agentInterventions:null,limitations:["Starts at the first supplied workflow creation, not unrecorded human triage.","Runner time includes overlapping jobs; it is not wall-clock time.","Different changes and queue conditions make historical comparisons observational."]};
}
function compare(current, baseline) {
  if(current.scope!==baseline.scope || current.measurement!==baseline.measurement || !current.successful || !baseline.successful || !(baseline.elapsedMs>0)) throw new Error("Incomparable or unsuccessful cycle");
  return {baselineElapsedMs:baseline.elapsedMs,currentElapsedMs:current.elapsedMs,savedMs:baseline.elapsedMs-current.elapsedMs,reductionPercent:100*(1-current.elapsedMs/baseline.elapsedMs),sampleSize:{before:1,after:1},controlled:false};
}
function main(argv) {
  const options={};
  for(let i=0;i<argv.length;i+=2){if(!["--runs","--scope","--output","--baseline"].includes(argv[i])||!argv[i+1])throw new Error("Expected --runs IDS --scope SCOPE --output FILE [--baseline FILE]");options[argv[i].slice(2)]=argv[i+1];}
  if(!options.runs||!options.output||!options.scope)throw new Error("Runs, scope and output required");
  const ids=options.runs.split(",");if(ids.some(id=>!/^\d+$/.test(id))||new Set(ids).size!==ids.length)throw new Error("Invalid run IDs");
  const gh=args=>JSON.parse(execFileSync("gh",args,{encoding:"utf8",maxBuffer:32*1024*1024}));
  const data=ids.map(id=>({run:gh(["api",`repos/ibrdot/swe-re-expert/actions/runs/${id}`]),jobs:gh(["api","--paginate","--slurp",`repos/ibrdot/swe-re-expert/actions/runs/${id}/jobs?per_page=100`]).flatMap(page=>page.jobs)}));
  const report=summarize(data,options.scope);
  if(options.baseline)report.comparison=compare(report,JSON.parse(fs.readFileSync(options.baseline)));
  fs.writeFileSync(options.output,JSON.stringify({...report,raw:data},null,2)+"\n");
  console.log(JSON.stringify(report,null,2));
}
if(require.main===module){try{main(process.argv.slice(2));}catch(error){console.error(error.message);process.exitCode=1;}}
module.exports={summarize,compare};
