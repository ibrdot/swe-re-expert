const assert = require("node:assert/strict");
const { classifyImpact, checkPlan, verifyResults } = require("../../lib/maintenance-impact");
const change = (file, extra = {}) => ({ status: "M", old_path: file, new_path: file, old_mode: "100644", new_mode: "100644", ...extra });
for (const [file, expected] of [
  ["CHANGELOG.md", "editorial"], ["docs/users/getting-started.md", "editorial"],
  ["skills/example/SKILL.md", "catalog"], ["skills/example/references/api.md", "catalog"],
  ["AGENTS.md", "full"], ["docs/users/AGENTS.md", "full"],
  ["skills/antigravity-maintainer-batch-release/SKILL.md", "full"],
  ["tools/lib/aas-v1/cli/main.js", "runtime"], ["tools/lib/workflow-contract.js", "full"],
  ["apps/web-app/src/App.tsx", "web"], ["apps/web-app/package-lock.json", "full"],
  ["package.json", "full"], [".github/workflows/ci.yml", "full"], ["unknown.md", "full"],
  ["docs/users/../../AGENTS.md", "full"],
]) assert.equal(classifyImpact([change(file)]).profile, expected, file);
assert.equal(classifyImpact([]).profile, "full");
assert.equal(classifyImpact([change("CHANGELOG.md", { new_mode: "120000" })]).profile, "full");
assert.equal(classifyImpact([change("CHANGELOG.md", { status: "T" })]).profile, "full");
assert.equal(classifyImpact([change("CHANGELOG.md"), change("tools/bin/aas.js")]).profile, "full");
assert.equal(classifyImpact([change("AGENTS.md", { status: "R", new_path: "CHANGELOG.md" })]).profile, "full");
assert.equal(classifyImpact([change("AGENTS.md", { status: "C", new_path: "skills/example/SKILL.md" })]).profile, "catalog");
assert(!checkPlan("editorial").includes("test"));
assert(!checkPlan("catalog").includes("test:aas-v1"));
assert(checkPlan("full").includes("test"));
const plan = checkPlan("editorial");
assert(verifyResults(plan, plan.map(check => ({ check, exitCode: 0 }))));
assert.throws(() => verifyResults(plan, []), /Incomplete/);
assert.throws(() => verifyResults(plan, plan.map(check => ({ check, exitCode: 0, skipped: true }))), /did not pass/);
assert.throws(() => verifyResults(plan, plan.map(check => ({ check, exitCode: 1 }))), /did not pass/);
console.log("maintenance impact negative and coverage checks passed");
const fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const { spawnSync } = require('node:child_process');
const fixture = fs.mkdtempSync(path.join(os.tmpdir(), 'aas-impact-snapshot-'));
try {
  const git = args => {
    const result = spawnSync('git', args, {cwd: fixture, encoding: 'utf8'});
    assert.equal(result.status, 0, result.stderr);
    return result.stdout.trim();
  };
  git(['init', '-q']); git(['config', 'user.name', 'Fixture']); git(['config', 'user.email', 'fixture@example.invalid']);
  fs.writeFileSync(path.join(fixture, 'CHANGELOG.md'), '# Example\n');
  git(['add', '.']); git(['commit', '-qm', 'fixture']);
  const head = git(['rev-parse', 'HEAD']);
  fs.appendFileSync(path.join(fixture, 'CHANGELOG.md'), 'uncommitted\n');
  const result = spawnSync(process.execPath, [path.resolve(__dirname, '../maintenance_validate.cjs'), '--repo', fixture, '--base', head, '--head', head], {encoding: 'utf8'});
  assert.equal(result.status, 1);
  assert.match(result.stderr, /clean immutable source checkout/);
} finally { fs.rmSync(fixture, {recursive: true, force: true}); }
