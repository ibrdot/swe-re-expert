const { spawnSync } = require("child_process");
const LICENSE_PATH = /^skills\/[a-z0-9]+(?:-[a-z0-9]+)*\/LICENSE$/u;
const MAX_LICENSE_BYTES = 64 * 1024;
function validLicenseText(bytes) {
  if (
    !Buffer.isBuffer(bytes) ||
    !bytes.length ||
    bytes.length > MAX_LICENSE_BYTES
  )
    return false;
  try {
    const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return (
      text.trim().length > 0 && !/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/u.test(text)
    );
  } catch {
    return false;
  }
}
function resolveLicenseContents(projectRoot, records) {
  const contents = new Map();
  for (const record of records)
    for (const side of ["old", "new"]) {
      const oid = record[`${side}_oid`];
      if (!LICENSE_PATH.test(record[`${side}_path`] || "") || contents.has(oid))
        continue;
      if (!/^[0-9a-f]{40}$/u.test(oid))
        throw new Error("Invalid license blob identity");
      const result = spawnSync("git", ["cat-file", "blob", oid], {
        cwd: projectRoot,
        maxBuffer: MAX_LICENSE_BYTES + 1,
        timeout: 10000,
      });
      if (result.error || result.status !== 0)
        throw new Error(`Unable to read bounded license blob ${oid}`);
      contents.set(oid, result.stdout);
    }
  return contents;
}
module.exports = {
  LICENSE_PATH,
  MAX_LICENSE_BYTES,
  validLicenseText,
  resolveLicenseContents,
};
