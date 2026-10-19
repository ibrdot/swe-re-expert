#!/usr/bin/env node
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { parseRawDiff } = require("../lib/git-raw-diff");
const { classifyImpact, checkPlan, verifyResults } = require("../lib/maintenance-impact");
const { resolveCommandInvocation } = require("./release_workflow");

function git(root, args) {
  const r = spawnSync("git", args, { cwd: root, maxBuffer: 32 * 1024 * 1024 });
  if (r.error || r.status !== 0) throw new Error(r.error?.message || r.stderr.toString());
  return r.stdout;
}
function planFor(root, base, head) {
  const resolve = ref => {
    const sha = git(root, ["rev-parse", "--verify", "--end-of-options", `${ref}^{commit}`]).toString().trim();
    if (!/^[a-f0-9]{40}$/.test(sha)) throw new Error("Invalid commit identity");
    return sha;
  };
  const baseSha = resolve(base), headSha = resolve(head);
  const records = parseRawDiff(git(root, ["diff", "--raw", "--no-abbrev", "-z", "-M", `${baseSha}...${headSha}`]), { allowEmpty: true });
  let impact = classifyImpact(records);
  // An exact prepared snapshot has already converged in the protected release
  // PR. The immutable tag candidate owns full distribution/platform execution.
  if (fs.existsSync(path.join(root, "data/distribution-snapshot.json"))
      && git(root, ["rev-parse", "HEAD"]).toString().trim() === headSha) {
    try { require("./distribution_snapshot.cjs").verify(root); impact = { ...impact, profile: "distribution" }; }
    catch { /* development snapshots intentionally fail this proof */ }
  }
  return { ...impact, baseSha, headSha, checks: checkPlan(impact.profile) };
}
function commandsFor(check, root, plan = {}) {
  if (check === "source-credits") return [["npm", ["run", "check:readme-credits", "--", "--base", plan.baseSha, "--head", plan.headSha]]];
  if (check === "documentation") return [["node", ["tools/scripts/run-python.js", "tools/scripts/tests/test_documentation_consistency.py"]]];
  if (check === "preview") return ["plugin-compat:sync", "index", "bundles:sync", "sync:metadata", "catalog", "build:aas-v1-catalog", "sync:web-assets"].map(s => ["npm", ["run", s]]);
  if (check === "web") return ["app:install", "app:test:coverage", "app:build"].map(s => ["npm", ["run", s]]);
  if (check === "package-tests") return fs.readdirSync(path.join(root, "tools/scripts/tests"))
    .filter(f => /^(installer_.*|npm_package_contents)\.test\.js$/.test(f)).sort()
    .map(f => ["node", [`tools/scripts/tests/${f}`]]);
  return [["npm", ["run", check]]];
}
function executePlan(root, plan, execute = spawnSync) {
  const results = [];
  for (const check of plan.checks) {
    const started = Date.now();
    let exitCode = 0;
    const commands = commandsFor(check, root, plan);
    if (!commands.length) throw new Error(`Empty required check: ${check}`);
    for (const [command, args] of commands) {
      const invocation = resolveCommandInvocation(command, args);
      const r = execute(invocation.command, invocation.args, { cwd: root, stdio: "inherit", shell: false });
      if (r.error || r.status !== 0) { exitCode = r.status || 1; break; }
    }
    results.push({ check, exitCode, elapsedMs: Date.now() - started });
    if (exitCode) break;
  }
  let passed = false;
  try { passed = verifyResults(plan.checks, results); } catch { /* retain incomplete evidence */ }
  return { ...plan, results, passed };
}
function main(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--plan") options.plan = true;
    else if (["--repo", "--base", "--head", "--output"].includes(argv[i]) && argv[i + 1]) options[argv[i++].slice(2)] = argv[i];
    else throw new Error(`Unknown or incomplete option: ${argv[i]}`);
  }
  if (!options.base || !options.head) throw new Error("Exact --base and --head are required");
  const root = path.resolve(options.repo || process.cwd());
  const plan = planFor(root, options.base, options.head);
  if (!options.plan && git(root, ["rev-parse", "HEAD"]).toString().trim() !== plan.headSha)
    throw new Error("Validation checkout must equal the requested head");
  if (!options.plan && git(root, ["status", "--porcelain", "--untracked-files=normal"]).toString().trim())
    throw new Error("Validation requires a clean immutable source checkout");
  const receipt = options.plan ? plan : executePlan(root, plan);
  const json = JSON.stringify(receipt, null, 2) + "\n";
  if (options.output) { fs.mkdirSync(path.dirname(path.resolve(options.output)), { recursive: true }); fs.writeFileSync(options.output, json); }
  process.stdout.write(json);
  if (!options.plan && !receipt.passed) process.exitCode = 1;
}
module.exports = { planFor, commandsFor, executePlan };
if (require.main === module) { try { main(process.argv.slice(2)); } catch (e) { console.error(e.message); process.exitCode = 1; } }
