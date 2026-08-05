#!/usr/bin/env node
/* Verify one registered mainnet beacon with the pinned drand-client package. */

import crypto from "node:crypto";
import process from "node:process";

function option(name) {
  const index = process.argv.indexOf(`--${name}`);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`missing --${name}`);
  return process.argv[index + 1];
}

function canonical(value) {
  if (value === null || typeof value === "boolean" || typeof value === "number" || typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
}

async function main() {
  if (process.versions.node.split(".")[0] !== "22") throw new Error(`Node 22 required, got ${process.versions.node}`);
  const moduleRoot = option("module-root").replace(/\/$/, "");
  const expectedChain = option("chain");
  const expectedRound = Number(option("round"));
  const expectedPublicKey = option("public-key");
  const { HttpCachingChain, HttpChainClient, fetchBeacon } = await import(`${moduleRoot}/build/esm/index.mjs`);
  const options = { disableBeaconVerification: false, noCache: true, chainVerificationParams: { chainHash: expectedChain, publicKey: expectedPublicKey } };
  const chain = new HttpCachingChain("https://api.drand.sh", options);
  const client = new HttpChainClient(chain, options);
  const info = await chain.info();
  if (info.hash !== expectedChain || info.public_key !== expectedPublicKey || info.schemeID !== "pedersen-bls-chained" || info.period !== 30 || info.genesis_time !== 1595431050) throw new Error("drand chain parameters differ from the registered mainnet contract");
  const beacon = await fetchBeacon(client, expectedRound);
  if (beacon.round !== expectedRound || typeof beacon.randomness !== "string" || !/^[0-9a-f]{64}$/.test(beacon.randomness) || typeof beacon.signature !== "string" || typeof beacon.previous_signature !== "string") throw new Error("drand-client returned an incomplete chained beacon");
  const proof = { ...beacon, chain_info: info };
  const proofSha256 = crypto.createHash("sha256").update(Buffer.from(`${canonical(proof)}\n`)).digest("hex");
  process.stdout.write(`${JSON.stringify({ verified: true, chain_hash: expectedChain, round: expectedRound, randomness_hex: beacon.randomness, proof_sha256: proofSha256, beacon, chain_info: info })}\n`);
}

main().catch((error) => { console.error(error instanceof Error ? error.message : String(error)); process.exitCode = 78; });
