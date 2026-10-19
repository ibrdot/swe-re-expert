"use strict";
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { privateStore, signReceipt, verifyReceipt } = require("./maintenance-review-receipt");

// State is advisory for scheduling. Only authenticated review receipts can
// authorize review reuse; neither a prior green check nor a saved merge result
// replaces a fresh GitHub lookup and current protection enforcement.
function openStore(directory, repository) {
  const root = privateStore(directory, repository);
  function filename(name) {
    if (!/^[a-z0-9][a-z0-9.-]*$/.test(name)) throw new Error("Invalid state key");
    return path.join(root, name);
  }
  function read(name) {
    const file = filename(name);
    let descriptor;
    try {
      descriptor = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
      const stat = fs.fstatSync(descriptor);
      if (!stat.isFile() || stat.nlink !== 1 || (stat.mode & 0o077)
          || (process.getuid && stat.uid !== process.getuid()) || stat.size > 4 * 1024 * 1024)
        throw new Error("Unsafe maintenance state file");
      return fs.readFileSync(descriptor);
    } catch (error) {
      if (error.code === "ENOENT") return null;
      throw error;
    } finally { if (descriptor !== undefined) fs.closeSync(descriptor); }
  }
  function write(name, bytes) {
    const temporary = filename(`${name}.${crypto.randomBytes(12).toString("hex")}`);
    try {
      fs.writeFileSync(temporary, bytes, { mode: 0o600, flag: "wx" });
      fs.renameSync(temporary, filename(name));
    } finally { fs.rmSync(temporary, { force: true }); }
  }
  let key = read("review.key");
  if (!key) {
    try { fs.writeFileSync(filename("review.key"), crypto.randomBytes(32), { mode: 0o600, flag: "wx" }); }
    catch (error) { if (error.code !== "EEXIST") throw error; }
    key = read("review.key");
  }
  if (key.length !== 32) throw new Error("Invalid private review key");
  return {
    saveReview(review) {
      write(`review.${review.fingerprint.digest}.json`, JSON.stringify(signReceipt(review, key)));
    },
    reuseReview(fingerprint, head) {
      const bytes = read(`review.${fingerprint.digest}.json`);
      return bytes ? verifyReceipt(JSON.parse(bytes), fingerprint, key, head) : null;
    },
    readEvidence(id) {
      const bytes = read(`evidence.${id}.json`);
      if (!bytes) return null;
      const signed = JSON.parse(bytes);
      if (signed.kind !== "deterministic-evidence" || signed.id !== id || !/^[a-f0-9]{64}$/.test(signed.mac || "")) throw new Error("Invalid cached evidence");
      const body = JSON.stringify({ kind: signed.kind, id: signed.id, result: signed.result });
      const mac = crypto.createHmac("sha256", key).update(body).digest();
      if (!crypto.timingSafeEqual(mac, Buffer.from(signed.mac, "hex"))) throw new Error("Cached evidence authentication failed");
      return signed.result;
    },
    writeEvidence(id, result) {
      const payload = { kind: "deterministic-evidence", id, result };
      write(`evidence.${id}.json`, JSON.stringify({ ...payload, mac: crypto.createHmac("sha256", key).update(JSON.stringify(payload)).digest("hex") }));
    },
    readBatch(id) { const bytes = read(`batch.${id}.json`); return bytes ? JSON.parse(bytes) : null; },
    writeBatch(id, state) { write(`batch.${id}.json`, JSON.stringify(state, null, 2) + "\n"); },
  };
}
module.exports = { openStore };
