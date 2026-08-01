# 39 — External Input-Lock Contract

**Status:** Step 5A implementation complete; external verification pending

The local-only input-lock contract comprises `cloud-input-lock` and an
explicitly `unpromoted` `cloud-experiment-manifest`. It records model,
tokenizer, benchmark, verifier, license, contamination, and OCI-base evidence
as immutable revisions, complete per-file hashed inventories (including each
inventory manifest), receipt references, and `linux/amd64@sha256:` digests.
Mutable branches, tags, malformed digests, missing licenses, and promotion of a
fixture manifest fail closed.

`pneuma_lab.cloud.inputs.build_retrieval_plan` derives model, tokenizer,
benchmark, dataset, verifier, and container targets entirely from immutable
values and performs no network lookup. The executable Step 5B audit plan then
enumerates every inventory-listed artifact, while `verify_input_receipts`
resolves every referenced receipt beneath one root and checks its actual bytes
against the declared digest, rejecting escapes, symlinks, conflicts, and drift.
The accompanying tests still use synthetic receipts only. They do not retrieve
or validate a real model, dataset, tokenizer, container layer, license, or
contamination record.

Consequently this completes the Step 5A implementation contract, not Step 5B:
no real input is locked, `G-ROSTER` remains open, no experiment manifest is
promoted, and no provider or paid action is authorized.

## Step 5B

The authorized retrieval and hash-verification workflow that would satisfy the
"Lock external inputs" exit gate is implemented in
`src/pneuma_lab/cloud/retrieval.py` and documented in
`51-step5b-retrieval-and-qualification.md`. It is unexecuted: the committed
authorization record is an unsigned candidate, so `require_authorized` refuses
and no byte has been retrieved. The committed candidate is bound to the synthetic fixture lock, so it
demonstrates the document shape rather than requesting a real retrieval. That
document also records the G-ROSTER evaluation (DL-163): both tiers are
`FEASIBILITY_NO_GO`, and the C/C++ shortfalls are provisional pending the
base-commit admissibility enumeration.
