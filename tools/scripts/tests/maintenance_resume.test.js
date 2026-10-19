const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { runBatch } = require("../merge_batch.cjs");
(async () => {
  const store = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), "aas-resume-"));
  const repo = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), "aas-resume-repo-"));
  const merged = new Set([3]);
  const attempted = [];
  let failed = true, protectedChecks = 0;
  const batchDependencies = {
    readRepositorySlug: () => "owner/repo",
    ensureTrustedMain: () => "a".repeat(40),
    assertEffectiveMainProtection: () => protectedChecks++,
    assertEvaluatorCompatible: () => {},
    loadPullRequestDetails: (_root,_repo,id) => ({ baseRefName: "main", state: merged.has(id) ? "MERGED" : "OPEN", mergeCommit: {oid:"b".repeat(40)} }),
    runCommand: (_cmd,args) => assert.deepEqual(args, ["merge-base", "--is-ancestor", "b".repeat(40), "a".repeat(40)]),
    mergePullRequest: async (_root,_repo,id) => {
      attempted.push(id);
      if (id === 1 && failed) throw new Error("PR conflict");
      merged.add(id); return { prNumber: id, merged: true };
    },
  };
  try {
    const options = { stateDir: store, batchDependencies };
    const first = await runBatch(repo, [1,2,3], options);
    assert.deepEqual(first.map(r=>r.status), ["blocked","merged","already-merged"]);
    failed = false;
    const second = await runBatch(repo, [1,2,3], options);
    assert.deepEqual(second.map(r=>r.status), ["merged","already-merged","already-merged"]);
    assert.deepEqual(attempted,[1,2,1]);
    assert.equal(protectedChecks,2);
    const journal = JSON.parse(fs.readFileSync(path.join(store,fs.readdirSync(store).find(n=>n.startsWith("batch.")))));
    assert.equal(journal.attempts.length,2);
    assert.equal(journal.attempts[0].success,false);
    assert.equal(journal.attempts[1].success,true);
  } finally { fs.rmSync(store,{recursive:true,force:true}); fs.rmSync(repo,{recursive:true,force:true}); }
})().catch(error=>{console.error(error);process.exitCode=1});
