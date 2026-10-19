"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const policyPath = path.join(__dirname, "../config/maintenance-policy.json");

function loadPolicy() {
  const bytes = fs.readFileSync(policyPath);
  const policy = JSON.parse(bytes);
  if (policy.schemaVersion !== 1 || policy.fallback !== "full")
    throw new Error("Unsupported maintenance policy");
  return { policy, digest: crypto.createHash("sha256").update(bytes).digest("hex") };
}

// Only positively identified leaves may select a narrow lane. Shared libraries,
// generators, instructions, manifests, dependency locks and unknown paths are full.
function classifyPath(file, policy) {
  if (typeof file !== "string" || /[\\\x00-\x1f\x7f]/.test(file)
      || file.startsWith("/") || file.split("/").some(p => !p || p === "." || p === "..")) return "full";
  if (/(^|\/)(AGENTS|SKILL)\.md$/.test(file) && !file.startsWith("skills/")) return "full";
  if (file.startsWith("skills/")) {
    const root = file.split("/")[1];
    return policy.operationalSkills.includes(root) ? "full" : "catalog";
  }
  if (policy.editorialFiles.includes(file)
      || (file.endsWith(".md") && policy.editorialPrefixes.some(p => file.startsWith(p)))) return "editorial";
  if (policy.runtimePrefixes.some(p => file.startsWith(p))) return "runtime";
  if (policy.webPrefixes.some(p => file.startsWith(p))) return "web";
  return "full";
}

function classifyImpact(records, loaded = loadPolicy()) {
  const { policy, digest } = loaded;
  const components = new Set();
  const paths = [];
  if (!Array.isArray(records) || !records.length) components.add("full");
  for (const record of records || []) {
    if (!["A", "M", "D", "R", "C"].includes(record.status)) components.add("full");
    const sides = record.status === "C" || record.status === "A" ? ["new"]
      : record.status === "D" ? ["old"] : ["old", "new"];
    for (const side of sides) {
      const file = record[`${side}_path`];
      const mode = record[`${side}_mode`];
      // Type changes and executable/link modes must never narrow the checks.
      if (mode !== "100644") components.add("full");
      paths.push(file);
      components.add(classifyPath(file, policy));
    }
  }
  const profile = components.has("full") || components.size !== 1 ? "full" : [...components][0];
  return { schemaVersion: 1, profile, policyDigest: digest, paths: [...new Set(paths)].sort() };
}

function checkPlan(profile) {
  if (!["editorial", "catalog", "runtime", "web", "full", "distribution"].includes(profile)) throw new Error("Unknown impact profile");
  if (profile === "distribution") return ["distribution:verify", "validate", "validate:references", "security:docs", "plugin-compat:check", "bundles:check", "check:aas-v1-catalog"];
  if (profile === "editorial") return ["documentation", "security:docs"];
  const checks = ["validate", "check:warning-budget", "security:docs", "source-credits", "preview", "validate:references", "check:aas-v1-catalog"];
  if (profile === "catalog") return checks;
  if (profile === "runtime") return [...checks, "test:aas-v1", "package-tests"];
  if (profile === "web") return [...checks, "web"];
  return [...checks, "test", "web"];
}

function verifyResults(plan, results) {
  if (!Array.isArray(results) || results.length !== plan.length) throw new Error("Incomplete validation receipt");
  for (let i = 0; i < plan.length; i++) {
    if (results[i].check !== plan[i] || results[i].exitCode !== 0 || results[i].skipped)
      throw new Error(`Required check did not pass: ${plan[i]}`);
  }
  return true;
}

module.exports = { loadPolicy, classifyPath, classifyImpact, checkPlan, verifyResults };
