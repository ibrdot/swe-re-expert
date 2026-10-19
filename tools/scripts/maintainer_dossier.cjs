#!/usr/bin/env node
// Builds review material only; never edits the protected exception ledger or approves runs.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { spawnSync } = require("node:child_process");
const { parseRawDiff } = require("../lib/git-raw-diff");
const { resolveBlobSizes } = require("../lib/git-blob-sizes");
const { resolveLicenseContents } = require("../lib/skill-license");
const { classifyChangeRecords } = require("../lib/workflow-contract");
const ROOT = path.resolve(__dirname, "../..");
function execute(command, args) {
  const r = spawnSync(command, args, {
    cwd: ROOT,
    encoding: "utf8",
    timeout: 60000,
    maxBuffer: 32 * 1024 * 1024,
  });
  if (r.error || r.status !== 0) throw new Error(r.stderr || String(r.error));
  return r.stdout;
}
function buildDossier(
  prs,
  repo = "ibrdot/swe-re-expert",
  run = execute,
) {
  if (
    !Array.isArray(prs) ||
    !prs.length ||
    prs.length > 20 ||
    prs.some((n) => !Number.isSafeInteger(n) || n < 1)
  )
    throw new Error("Select 1–20 exact PR numbers");
  return {
    schemaVersion: 1,
    repository: repo,
    reviewed: false,
    authority:
      "Review material only; exact-head semantic review and protected gates still required",
    prs: prs.map((number) => {
      const pr = JSON.parse(
        run("gh", ["api", `repos/${repo}/pulls/${number}`]),
      );
      const head = pr.head.sha,
        base = pr.base.sha;
      if (
        !/^[0-9a-f]{40}$/u.test(head) ||
        !/^[0-9a-f]{40}$/u.test(base) ||
        pr.base.ref !== "main"
      )
        throw new Error("Invalid immutable PR identity");
      run("git", ["fetch", "--no-tags", "origin", `pull/${number}/head`]);
      if (run("git", ["rev-parse", "FETCH_HEAD"]).trim() !== head)
        throw new Error("PR head changed while collecting dossier");
      run("git", ["fetch", "--no-tags", "origin", base]);
      const mergeBase = run("git", ["merge-base", base, head]).trim();
      const records = parseRawDiff(
        Buffer.from(
          run("git", [
            "diff",
            "--raw",
            "--no-abbrev",
            "-z",
            "-M",
            mergeBase,
            head,
            "--",
          ]),
        ),
        { allowEmpty: true },
      );
      const policy = classifyChangeRecords(records, {
        blobSizes: resolveBlobSizes(ROOT, records),
        licenseContents: resolveLicenseContents(ROOT, records),
      });
      const files = run("git", ["ls-tree", "-r", "-l", head, "--", "skills"])
        .trim()
        .split("\n")
        .filter(Boolean)
        .map((line) => {
          const match = line.match(
            /^(\d+) (\w+) ([a-f0-9]+)\s+(\d+|-)\t(.+)$/u,
          );
          if (!match) throw new Error("Malformed Git tree");
          return {
            mode: match[1],
            type: match[2],
            oid: match[3],
            size: match[4] === "-" ? null : Number(match[4]),
            path: match[5],
          };
        });
      const roots = [
        ...new Set(
          files
            .filter(
              (f) =>
                f.path.endsWith("/SKILL.md") &&
                records.some((record) =>
                  [record.new_path, record.old_path].some((p) =>
                    p?.startsWith(f.path.slice(0, -8)),
                  ),
                ),
            )
            .map((f) => f.path.slice(0, -9)),
        ),
      ];
      const skills = roots.map((root) => ({
        root,
        tree: run("git", ["rev-parse", `${head}:${root}`]).trim(),
        files: files
          .filter((f) => f.path.startsWith(root + "/"))
          .map((file) => {
            if (
              file.type !== "blob" ||
              file.mode !== "100644" ||
              file.size > 1024 * 1024
            )
              return { ...file, readable: false };
            const bytes = spawnSync("git", ["cat-file", "blob", file.oid], {
              cwd: ROOT,
              maxBuffer: 1024 * 1024,
            }).stdout;
            return {
              ...file,
              sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
            };
          }),
      }));
      const current = JSON.parse(
        run("gh", ["api", `repos/${repo}/pulls/${number}`]),
      );
      if (current.head.sha !== head || current.base.sha !== base)
        throw new Error("PR changed while collecting dossier");
      return {
        number,
        head,
        base,
        headRepository: pr.head.repo.full_name,
        skills,
        policy,
        reviewed: false,
      };
    }),
  };
}
if (require.main === module) {
  try {
    const args = process.argv.slice(2);
    const at = args.indexOf("--prs");
    const prs = (args[at + 1] || "").split(",").map(Number);
    if (at < 0) throw new Error("Expected --prs");
    const report = buildDossier(prs);
    const output = JSON.stringify(report, null, 2) + "\n";
    const out = args.indexOf("--output");
    if (out >= 0) fs.writeFileSync(args[out + 1], output, { mode: 0o600 });
    else process.stdout.write(output);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
module.exports = { buildDossier };
