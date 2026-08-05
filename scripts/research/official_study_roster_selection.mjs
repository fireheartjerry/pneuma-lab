#!/usr/bin/env node
/*
 * Frozen Node 22 selection program for the registered confirmation universe.
 *
 * The program deliberately requires a separate, manifest-shaped metadata file
 * for task identity, lineage, strata, groups, tiers, rejects, and reserves.
 * The qualification selection receipts do not contain those fields, so this
 * program refuses to guess them.  It emits no output file on any failure.
 */

import crypto from "node:crypto";
import fs from "node:fs";

const STUDY = "neurips-2026-resampling-null";
const CHAIN = "8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce";
const TARGET_ROUND = 6355105;
const CLOSURE_SHA256 = "a887370640d2c6e9514e350c476e786d1040e6bcf3799422dee6c60b70944209";
const SWE_SHA256 = "e6b4a052426f234daf7f1473d91ae3a861bd1dc5e270160936f4bc6015574071";
const TAU_SHA256 = "a6c3e8fc16becbd87ad468f6cd8d3279ae76ac049f15ab804146dcfa1f80a12e";
const FRAME_MAGIC = Buffer.from("pneuma-resampling-null-frame-v1\0", "utf8");

function fail(message) {
  throw new Error(`MISSING_REGISTERED_ROSTER_FIELDS: ${message}`);
}

function read(path) {
  const bytes = fs.readFileSync(path);
  return { bytes, value: JSON.parse(bytes.toString("utf8")) };
}

function sha(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex");
}

function canonical(value) {
  if (value === null || typeof value === "boolean" || typeof value === "number" || typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  fail("non-JSON value in canonical input");
}

function canonicalBytes(value) {
  return Buffer.from(`${canonical(value)}\n`, "utf8");
}

function frame(tag, fields) {
  const tagBytes = Buffer.from(tag, "utf8");
  const chunks = [FRAME_MAGIC, u32(tagBytes.length), tagBytes, u32(fields.length)];
  for (const field of fields) {
    if (field.kind === "bytes") chunks.push(Buffer.from([0x03]), u32(field.value.length), field.value);
    else if (field.kind === "text") { const value = Buffer.from(field.value, "utf8"); chunks.push(Buffer.from([0x02]), u32(value.length), value); }
    else if (field.kind === "u64") { const value = Buffer.alloc(8); value.writeBigUInt64BE(BigInt(field.value)); chunks.push(Buffer.from([0x01]), u32(8), value); }
    else fail("unknown frame field kind");
  }
  return Buffer.concat(chunks);
}

function u32(value) {
  const result = Buffer.alloc(4);
  result.writeUInt32BE(value);
  return result;
}

function text(value) { return { kind: "text", value }; }
function bytes(value) { return { kind: "bytes", value }; }
function u64(value) { return { kind: "u64", value }; }

function sortedUniqueStrings(value, field) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item.length === 0)) fail(`${field} must be non-empty strings`);
  const result = [...new Set(value)].sort();
  if (result.length !== value.length || result.some((item, index) => item !== value[index])) fail(`${field} must be sorted and unique`);
  return result;
}

function args() {
  const result = {};
  for (let index = 2; index < process.argv.length; index += 2) {
    const key = process.argv[index];
    if (!key?.startsWith("--") || index + 1 >= process.argv.length) fail("arguments must be --name value pairs");
    result[key.slice(2)] = process.argv[index + 1];
  }
  for (const key of ["closure", "swe", "tau", "metadata", "precommit", "private", "beacon", "timestamp", "output"]) if (!result[key]) fail(`missing --${key}`);
  return result;
}

function main() {
  const options = args();
  if (process.versions.node.split(".")[0] !== "22") fail(`Node 22 required, got ${process.versions.node}`);
  const closure = read(options.closure);
  const swe = read(options.swe);
  const tau = read(options.tau);
  const metadata = read(options.metadata).value;
  const precommit = read(options.precommit).value;
  const privateMaterial = read(options.private).value;
  const beacon = read(options.beacon).value;
  if (sha(closure.bytes) !== CLOSURE_SHA256 || sha(swe.bytes) !== SWE_SHA256 || sha(tau.bytes) !== TAU_SHA256) fail("qualification source digest differs from the frozen precommit universe");
  if (precommit.study_id !== STUDY || precommit.beacon_chain_hash !== CHAIN || precommit.beacon_round !== TARGET_ROUND) fail("precommit identity or target round differs");
  if (sha(canonicalBytes(precommit)) !== "0ec4db0d333efd5062684088859a4506aebb3f9a6a6a1ee992e9b771d20c20b3") fail("precommit bytes differ from the signed artifact");
  if (privateMaterial.study_id !== STUDY || typeof privateMaterial.precommit_sha256 !== "string") fail("private reveal is not bound to the frozen precommit");
  if (sha(canonicalBytes(precommit)) !== privateMaterial.precommit_sha256) fail("private reveal precommit digest differs");
  if (beacon.verified !== true || beacon.chain_hash !== CHAIN || beacon.round !== TARGET_ROUND || !/^[0-9a-f]{64}$/.test(beacon.randomness_hex) || !/^[0-9a-f]{64}$/.test(beacon.proof_sha256)) fail("drand proof is not cryptographically verified for the frozen future round");
  const metadataTasks = metadata?.tasks;
  if (!Array.isArray(metadataTasks) || !metadata?.record_kind || metadata.record_kind !== "resampling_roster_metadata_v1") fail("metadata must be a registered roster metadata manifest");
  const sourceRows = [...(swe.value.rows ?? []).map((row) => ({ source: "SWE", key: `swe:${row.instance_id}`, row })), ...(tau.value.rows ?? []).map((row) => ({ source: "TAU", key: `tau2:${row.domain}:${row.task_id}`, row }))];
  if (sourceRows.length !== 193) fail(`expected 193 selected C120 rows, found ${sourceRows.length}`);
  const rowsById = new Map(metadataTasks.map((row) => [row.task_id, row]));
  if (rowsById.size !== metadataTasks.length) fail("metadata task IDs must be unique");
  const selected = sourceRows.map(({ key }) => rowsById.get(key));
  if (selected.some((row) => !row)) fail("metadata does not provide exact identity/lineage for every selected row");
  for (const row of selected) {
    if (typeof row.benchmark !== "string" || typeof row.stratum !== "string" || typeof row.lineage !== "string" || !Array.isArray(row.groups) || !Array.isArray(row.tiers)) fail("metadata omits benchmark, stratum, lineage, groups, or tiers");
    if (row.tiers.some((tier) => tier !== 120 && tier !== 160) || !row.tiers.includes(120)) fail("metadata tier membership is not registered and nested");
  }
  const accepted = sortedUniqueStrings(selected.map((row) => row.task_id), "accepted_task_ids");
  const rejected = sortedUniqueStrings(metadata.rejected_task_ids ?? [], "rejected_task_ids");
  const reserves = sortedUniqueStrings(metadata.reserves ?? [], "reserves");
  if (new Set([...accepted, ...rejected, ...reserves]).size !== accepted.length + rejected.length + reserves.length) fail("accepted, rejected, and reserves overlap");
  const precommitPayload = { study_id: STUDY, qualification_universe_sha256: precommit.qualification_universe_sha256, roster_local_nonce_commitment_sha256: precommit.roster_local_nonce_commitment_sha256, schedule_seed_commitment_sha256: precommit.schedule_seed_commitment_sha256, assignment_master_key_commitment_sha256: precommit.assignment_master_key_commitment_sha256 };
  const precommitDigest = sha(canonicalBytes(precommitPayload));
  const nonce = Buffer.from(privateMaterial.roster_local_nonce_hex, "hex");
  const randomness = Buffer.from(beacon.randomness_hex, "hex");
  if (nonce.length !== 32 || randomness.length !== 32) fail("nonce/randomness must be 32 bytes");
  const rosterSeed = sha(frame("roster-seed-v1", [bytes(Buffer.from(precommitDigest, "hex")), bytes(nonce), bytes(Buffer.from(CHAIN, "hex")), u64(TARGET_ROUND), bytes(randomness)]));
  const tierMembership = { "120": selected.filter((row) => row.tiers.includes(120)).map((row) => row.task_id).sort(), "160": selected.filter((row) => row.tiers.includes(160)).map((row) => row.task_id).sort() };
  const groupLabels = Object.fromEntries(selected.map((row) => [row.task_id, row.groups]));
  const output = { record_kind: "resampling_eligibility_manifest_v1", schema_version: "1", study_id: STUDY, precommit: precommitPayload, precommit_sha256: precommitDigest, timestamp_receipt: { precommit_sha256: precommitDigest, timestamp: options.timestamp }, beacon_receipt: { chain_hash: CHAIN, round: TARGET_ROUND, randomness_hex: beacon.randomness_hex }, roster_local_nonce_hex: nonce.toString("hex"), roster_seed_sha256: rosterSeed, accepted_task_ids: accepted, rejected_task_ids: rejected, tier_membership: tierMembership, group_labels: groupLabels, reserves };
  const outputBytes = canonicalBytes(output);
  const destination = options.output;
  const descriptor = fs.openSync(destination, "wx", 0o644);
  try { fs.writeFileSync(descriptor, outputBytes); fs.fsyncSync(descriptor); } finally { fs.closeSync(descriptor); }
  process.stdout.write(JSON.stringify({ output_sha256: sha(outputBytes), accepted: accepted.length, c120: tierMembership["120"].length, c160: tierMembership["160"].length }));
}

try { main(); } catch (error) { console.error(error instanceof Error ? error.message : String(error)); process.exitCode = 78; }
