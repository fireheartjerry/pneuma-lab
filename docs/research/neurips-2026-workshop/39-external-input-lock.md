# 39 — External Input-Lock Contract

**Status:** Step 5A implementation complete; external verification pending

The local-only input-lock contract comprises `cloud-input-lock` and an
explicitly `unpromoted` `cloud-experiment-manifest`. It records model,
tokenizer, benchmark, verifier, license, contamination, and OCI-base evidence
as immutable revisions, receipt references, and `linux/amd64@sha256:` digests.
Mutable branches, tags, malformed digests, missing licenses, and promotion of a
fixture manifest fail closed.

`pneuma_lab.cloud.inputs.build_retrieval_plan` derives its targets entirely
from these immutable values and performs no network lookup. The accompanying
tests use synthetic receipts only. They do not retrieve or validate a model,
dataset, tokenizer, container layer, license, or contamination record.

Consequently this completes the Step 5A implementation contract, not Step 5B:
no real input is locked, `G-ROSTER` remains open, no experiment manifest is
promoted, and no provider or paid action is authorized.
