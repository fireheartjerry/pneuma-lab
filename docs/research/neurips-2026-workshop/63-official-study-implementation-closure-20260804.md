# Official-study implementation closure — 2026-08-04

## Disposition

The implementation slice is complete locally. It is not a study result and it
does not authorize the official P0/Step-4B run. The two-L40S AWS qualification
passed as action-019 and remains a separate pre-experiment receipt.
The machine-readable current-state source is `docs/project-status.json`.

## Code now complete

- `cloud_production_run_spec` is the immutable, canonical run package. It
  binds the checkout commit, three role image digests, the registered Qwen
  revision and vLLM pin, SWE-bench-Live and tau2 pins, task-manifest/input
  bindings, roster/assignment inputs, named RNG seed digests, two-worker
  topology, Spot budget, output paths, analysis graph, and explicit official
  authorization references.
- `ProductionWorkerExecutor` uses the real OpenAI-compatible vLLM adapter and
  registered benchmark subprocess adapter in official mode. Local mode uses
  deterministic adapters through the same controller/worker flow and is
  labelled `local_mock_non_scientific`; it cannot produce official evidence.
- Raw per-worker output and worker evidence are separate schema-validated,
  digest-bound artifacts. They record worker identity, model/image/code/task
  bindings, canonical partition, output parity, timing, failure/OOM class, and
  immutable artifact digests.
- The three role recipes now package the production control-flow closure and
  its schemas, with an explicit build-time probe for the pinned base's
  `jsonschema`/Ed25519 verifier dependencies. The passed action-019 image is
  still qualification evidence; it is not silently relabelled as this future
  production image.
- `ProductionOrchestrator` plus `ProductionStateStore` provide the provider
  adapter contract, deterministic client-token idempotency boundary, restart
  recovery, successful-submission preservation across observation errors, and
  explicit teardown. No provider adapter is invoked by this slice.
- The Sigstore/drand/Node ceremony seam validates the registered policy,
  canonical manifest, signatures, beacon, and receipt; synthetic/IV authority
  is rejected for P0. It has no network or live-ceremony behavior.
- Roster-bound power validation now runs one explicit C120 or C160 tier,
  combines both digest-bound tier receipts, applies the registered
  largest-feasible rule (C160, then C120, otherwise formal
  `FEASIBILITY_NO_GO`), and exposes both finalization and `combine-tiers` CLI
  routes. No power grid was run here and no tier was selected.

## Still required before an authorized official launch

These are external/scientific actions, not missing local implementation:

1. Freeze and independently verify the real input/task/roster/assignment/
   packet/analysis graph and their code, image, license, contamination,
   reproducibility, and digest bindings.
2. Conduct the live registered Sigstore/drand/Node roster ceremony and retain
   its canonical receipt; then run both registered C120 and C160 power/type-I
   validations, combine their receipts, and accept only the exact rule's
   result or formal no-go.
3. Obtain fresh account/quota/credit/spend admission for the separately
   authorized action, plus the final immutable production image/SBOM and
   provider/teardown receipts. Qualification action-019 does not satisfy this
   authority.
4. Complete packet/assignment/task-block, detectability, leakage, blinding,
   and frozen-analysis checks, followed by the separately signed official
   P0/Step-4B authorization bound to the final run-spec digest and spend
   ledger.
5. Run the fresh hostile Step-14 review and release checks. Only after it
   passes may the authorized controller launch, observe, and tear down the
   real model/benchmark workload. Unblind, analyze, and promote claims remain
   later separately governed actions.

No AWS resource, image build/push, model run, benchmark/pilot workload, P0
grid, live ceremony, unblind, scientific analysis, or scientific receipt was
created by this implementation slice.
