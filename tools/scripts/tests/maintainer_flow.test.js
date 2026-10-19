const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const yaml = require("yaml");
const {
  classifyChangeRecords,
  classifyPathPolicy,
} = require("../../lib/workflow-contract");
const {
  validLicenseText,
  MAX_LICENSE_BYTES,
} = require("../../lib/skill-license");
const { localCheckCommands, runLocalChecks } = require("../pr_preflight.cjs");
const {
  prepareBatch,
  parseArgs,
  isSkillContentRecord,
  assertEvaluatorCompatible,
} = require("../merge_batch.cjs");
const batch = require("../canonical_batch.cjs");
const {
  buildPlan,
  comparePlan,
  workflowProof,
  parseArgs: releaseArgs,
  verifyRelease,
} = require("../release_inspect.cjs");
const { buildDossier } = require("../maintainer_dossier.cjs");
const sha = "1".repeat(40),
  oid = "2".repeat(40),
  now = Date.now();
const record = {
  status: "A",
  old_path: null,
  new_path: "skills/example/LICENSE",
  old_mode: "000000",
  new_mode: "100644",
  old_oid: "0".repeat(40),
  new_oid: oid,
  new_size: 12,
};
assert.equal(
  isSkillContentRecord(record),
  true,
  "license-only changes still need the semantic review lane",
);
assert.equal(
  isSkillContentRecord({ new_path: "skills/example/scripts/check.py" }),
  true,
);
const contents = new Map([[oid, Buffer.from("MIT License\n")]]);
const classify = (patch = {}, options = {}) =>
  classifyChangeRecords([{ ...record, ...patch }], {
    licenseContents: contents,
    ...options,
  });
assert.equal(classify().approvalSafe, true);
assert.equal(classify().requiresHumanReview, true);
assert.equal(
  classify({}, { licenseContents: undefined }).approvalSafe,
  false,
  "missing bytes cannot authorize a license",
);
for (const patch of [
  { new_mode: "100755" },
  { new_mode: "120000" },
  { new_mode: "160000" },
  { new_size: MAX_LICENSE_BYTES + 1 },
  { new_path: "skills/example/scripts/LICENSE" },
  { new_path: "skills/example/LICENSE.sh" },
  { new_path: "skills/example/../LICENSE" },
  { new_path: "LICENSE" },
]) {
  assert.equal(classify(patch).approvalSafe, false, JSON.stringify(patch));
}
for (const bytes of [
  Buffer.from([0xff]),
  Buffer.from("\0MIT"),
  Buffer.from(""),
  Buffer.from(" \n"),
  Buffer.alloc(MAX_LICENSE_BYTES + 1, 65),
])
  assert.equal(validLicenseText(bytes), false);
assert.equal(
  classifyPathPolicy("skills/example/LICENSE").kind,
  "skill_support",
);
assert.equal(
  classifyPathPolicy("skills/example/LICENSE.txt").approvalSafe,
  false,
  "no broad extension/path expansion",
);
assert.equal(
  classifyChangeRecords(
    [
      {
        ...record,
        status: "R",
        old_path: "skills/example/LICENSE",
        old_mode: "100644",
        old_oid: oid,
        old_size: 12,
        new_path: "tools/LICENSE",
      },
    ],
    { licenseContents: contents },
  ).approvalSafe,
  false,
);
const commands = localCheckCommands(
  { requiresReferencesValidation: true },
  "base",
  "head",
);
assert.deepEqual(
  commands.map((row) => row[0]),
  [
    "validate",
    "validate:references",
    "security:docs",
    "check:readme-credits",
    "test",
  ],
);
assert.deepEqual(commands[3][1], ["--base", "base", "--head", "head"]);
let calls = 0;
const previewFixture = () => ({
  root: "/tmp/preview",
  cleanup() {},
  preparation: {
    script: "prepare-test-preview",
    exitCode: 0,
    output: "fixture",
  },
});
const checks = runLocalChecks(
  "/tmp",
  { requiresReferencesValidation: false },
  "base",
  "head",
  () => ({ status: ++calls === 1 ? 1 : 0, stdout: "observed" }),
  previewFixture,
);
assert.equal(checks.length, 5);
assert.equal(checks[0].exitCode, 1);
assert.equal(
  checks.at(-1).exitCode,
  0,
  "a failure does not hide subsequent checks",
);
let cleaned = false;
const blocked = runLocalChecks(
  "/tmp",
  { requiresReferencesValidation: false },
  "base",
  "head",
  () => ({ status: 0 }),
  () => ({
    root: null,
    cleanup() {
      cleaned = true;
    },
    preparation: { script: "prepare-test-preview", exitCode: 1 },
  }),
);
assert.equal(blocked.at(-1).skipped, true);
assert.equal(cleaned, true, "failed preview is still cleaned up");
assert.doesNotThrow(() =>
  assertEvaluatorCompatible("/tmp", sha, oid, () => "skills/example/SKILL.md"),
);
assert.throws(
  () =>
    assertEvaluatorCompatible(
      "/tmp",
      sha,
      oid,
      () => "tools/lib/workflow-contract.js",
    ),
  /contract changed/,
);
const events = [];
const deps = {
  load: (_, __, n) => ({ number: n, headRefOid: sha }),
  approve: (_, __, pr, options) => {
    events.push(pr.number);
    assert.equal(options.evaluatorOid, oid);
    return { approvedRuns: [] };
  },
};
const prepared = prepareBatch(
  "/tmp",
  "owner/repo",
  [1, 2],
  { dryRun: true, evaluatorOid: oid },
  deps,
);
assert.deepEqual(events, [1, 2]);
assert.ok(prepared.every((pr) => !pr.merged));
assert.equal(parseArgs(["--prepare-only"]).prepareOnly, true);
assert.throws(
  () =>
    prepareBatch(
      "/tmp",
      "owner/repo",
      [3],
      {},
      { ...deps, load: () => ({ mergeable: "CONFLICTING" }) },
    ),
  /conflicts/,
);
const lease = {
  id: 1,
  environment: "aas-maintainer-batch",
  creator: { login: "owner" },
  created_at: new Date(now).toISOString(),
  state: "in_progress",
  payload: {
    schemaVersion: 1,
    batchId: "12345678-1234-1234-1234-123456789012",
    baseSha: sha,
    expiresAt: new Date(now + 1000).toISOString(),
  },
};
assert.equal(batch.classifyLeases([lease], "owner/repo", now).active.length, 1);
assert.equal(
  batch.classifyLeases([lease], "owner/repo", now + 2000).expired.length,
  1,
);
for (const patch of [
  { creator: { login: "attacker" } },
  {
    payload: {
      ...lease.payload,
      expiresAt: new Date(now + 7200000).toISOString(),
    },
  },
  { payload: { ...lease.payload, baseSha: "bad" } },
])
  assert.equal(batch.validLease({ ...lease, ...patch }, "owner/repo"), false);
assert.equal(
  batch.decide({
    currentSha: sha,
    expectedSha: oid,
    leases: { active: [], expired: [] },
  }).reason,
  "superseded-main",
);
assert.equal(
  batch.decide({
    currentSha: sha,
    expectedSha: sha,
    leases: { active: [lease], expired: [] },
  }).shouldRun,
  false,
);
assert.equal(
  batch.decide({
    currentSha: sha,
    expectedSha: sha,
    leases: { active: [], expired: [lease] },
    recovery: true,
  }).shouldRun,
  true,
);
assert.equal(
  batch.decide({
    currentSha: sha,
    expectedSha: sha,
    leases: { active: [], expired: [] },
    recovery: true,
  }).shouldRun,
  false,
);
const ancient = {
  ...lease,
  created_at: new Date(now - 7200000).toISOString(),
  payload: {
    ...lease.payload,
    expiresAt: new Date(now - 7100000).toISOString(),
  },
};
const oldRows = batch.readLeases("owner/repo", (_, endpoint) =>
  endpoint.startsWith("deployments?") ? [ancient] : [{ state: "in_progress" }],
);
assert.equal(
  batch.classifyLeases(oldRows, "owner/repo").expired.length,
  1,
  "an old latest interrupted lease remains recoverable",
);
const requests = [];
let failDispatch = true;
assert.throws(
  () =>
    batch.finishBatch("owner/repo", 1, true, (_, endpoint, data) => {
      requests.push([endpoint, data]);
      if (endpoint.includes("dispatches") && failDispatch)
        throw new Error("dispatch failed");
    }),
  /dispatch failed/,
);
assert.equal(
  requests.at(-1)[1].state,
  "in_progress",
  "failed dispatch restores recoverable lease",
);
let plan = buildPlan("v1", "HEAD", {
  resolve: (ref) => (ref === "v1" ? sha : oid),
  git: (args) =>
    args[0] === "diff"
      ? "skills/old/references/guide.md\nskills/new/SKILL.md"
      : args[0] === "log"
        ? `${oid}\tA Person\ta@example.invalid\tfeat: skill (#42)`
        : "",
  snapshot: () => '{"version":"2.0.0"}',
  skillPaths: (ref) =>
    ref === sha
      ? ["skills/old/SKILL.md", "skills/removed/SKILL.md"]
      : ["skills/old/SKILL.md", "skills/new/SKILL.md"],
});
assert.deepEqual(plan.added, ["new"]);
assert.deepEqual(plan.removed, ["removed"]);
assert.deepEqual(plan.updated, ["old"]);
assert.equal(plan.catalogTotal, 2);
assert.deepEqual(plan.prs, [42]);
assert.equal(comparePlan(plan, { ...plan, headSha: sha }), false);
assert.equal(comparePlan(plan, JSON.parse(JSON.stringify(plan))), true);
const runs = [
  {
    id: 1,
    path: ".github/workflows/ci.yml",
    head_sha: sha,
    status: "completed",
    conclusion: "success",
  },
];
assert.equal(workflowProof(runs, ".github/workflows/ci.yml", sha).runId, 1);
assert.throws(
  () =>
    workflowProof(
      [...runs, { ...runs[0], id: 2, conclusion: "failure" }],
      runs[0].path,
      sha,
    ),
  /failed/,
);
assert.throws(() => workflowProof(runs, runs[0].path, oid), /missing/);
assert.throws(
  () => workflowProof(runs, runs[0].path, sha, "v1.0.0"),
  /missing/,
);
assert.throws(() => releaseArgs(["--unknown"]), /Unknown/);
assert.throws(() => releaseArgs(["--version"]), /Missing/);
assert.throws(() => buildDossier([]), /Select/);
const root = path.resolve(__dirname, "../../..");
const ci = yaml.parse(
  fs.readFileSync(path.join(root, ".github/workflows/ci.yml"), "utf8"),
);
const mainSteps = ci.jobs["main-validation-and-sync"].steps;
assert.ok(mainSteps.some(step => (step.run || "").includes("maintenance_validate.cjs")));
assert.ok(!mainSteps.some(step => ["batch_guard", "publication_guard", "canonical_pr"].includes(step.id)));
const checkout = ci.jobs["artifact-preview"].steps[0];
assert.equal(checkout.with["fetch-depth"], 1);
assert.match(checkout.if, /!=/);
const canonicalCheckout = ci.jobs["artifact-preview"].steps[1];
assert.equal(canonicalCheckout.with["fetch-depth"], 0);
assert.match(canonicalCheckout.if, /==/);
assert.equal(checkout.with["sparse-checkout-cone-mode"], false);
assert.equal(fs.existsSync(path.join(root, ".github/workflows/maintainer-batch-recovery.yml")), false,
  "retired canonical leases must not keep dispatching full main checks");
console.log("maintainer flow regressions passed");
