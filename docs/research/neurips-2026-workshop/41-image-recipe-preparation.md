# 41 — Image Recipe Preparation

**Status:** Step 7A implementation complete; real image verification pending

Three role-separated recipes exist for controller, model server, and benchmark
worker. Their bases use syntactically pinned but intentionally invalid fixture
registries; their dependency locks are likewise fixtures. This permits static
pin-discipline and manifest-substitution tests without retrieving a single byte.

No real base receipt, dependency lock, OCI image digest, build, comparison,
SBOM, ECR action, or external input retrieval exists. Step 7B remains blocked
on Step 5B and a separate hash-bound authorization for material local/network
build action.
