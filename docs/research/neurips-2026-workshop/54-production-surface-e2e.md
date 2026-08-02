# 54 — Production execution-surface E2E contract

**Status:** implementation complete; external image E2E pending

The three role images share one immutable `python3 -m
pneuma_lab.cloud.production_runtime <role>` entrypoint. The `verify` protocol
is the Step 7B positive/wrong-hash probe. The bounded `e2e` protocol is a real
role hand-off:

1. `controller` reads the exact canonical harness and emits a `DISPATCHED`
   receipt containing the request digest.
2. `model-server` accepts only that controller receipt and emits a
   content-addressed `RESPONDED` receipt with bounded token IDs.
3. `benchmark-worker` accepts only that model receipt, recomputes its response
   digest, and emits a terminal `COMPLETE` receipt.

Every receipt binds the action ID, input-lock digest, harness digest, request
digest, role, and predecessor state. Wrong harness hashes, authority swaps,
request swaps, malformed predecessor receipts, response digest changes, and
invalid token payloads fail closed. The role receipts validate against
`schemas/cloud-production-role-receipt.schema.json`; the aggregate surface
uses `schemas/cloud-production-execution-surface.schema.json`.

The local development check is:

```text
python scripts/research/run_production_surface_e2e.py \
  --harness <canonical-harness.json> \
  --harness-sha256 <digest> \
  --output-dir <fresh-output> \
  --source-commit <40-hex-commit>
```

The admitted qualification must run the same chain in the built images under
network-none/read-only/no-new-privileges isolation, retain all role and
wrong-hash receipts, and fill the real image digests and controller privilege
gates. This adapter is infrastructure evidence only: it does not load a model,
execute a benchmark task, select a pilot rung, or establish a scientific
result.
