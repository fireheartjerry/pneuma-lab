# Pre-experiment closure readiness — 2026-08-02

**Disposition:** launch-blocked; pre-experiment verification only

**Source commit:** `63156f34537be4b83638f9af84fb6bae1e92b1d6`

The checkout was at the required base commit `e8cb882a85268c846bf344fc4e0f7a03776c9234`; the campaign added only the Terraform lockfile repair recorded in the source commit above. The private `infra/terraform/environments/aws-private.tfvars` file was present, ignored, and mode `600`. It was copied once from the user's local secure checkout into this dedicated VPS worktree before the campaign; its contents were never printed, hashed, staged, or edited.

This report is sanitized. Raw AWS responses, the saved plan, and temporary command logs remained inside a mode-0700 directory outside Git. No account IDs, ARNs, tokens, image references, bucket paths, or private variable values are recorded here.

## Completed before-experiment work

### Local reproducibility and focused gates

`uv sync --frozen --python 3.12 --extra dev` passed. The canonical status checker passed. Every test process below had a 60-second timeout and passed:

| Check | Result | stdout SHA-256 | stderr SHA-256 |
| --- | --- | --- | --- |
| `uv sync --frozen --python 3.12 --extra dev` | PASS | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `f446884590bda7f53d88ffb62ef641705af7ac7e660894ff4dfefb9f7accf75d` |
| `.venv/bin/python -m pneuma_lab.status --check` | PASS | `078f32ea9ec7b3bee0a7fb0cd54b184a179c2da796c01952f2adaafa97217aea` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Cloud architecture/account/pilot/admission/allocation/IaC/schema suite | PASS | `c4408bbda0a26d2761d58a258d0cdb05b86e89dc3bc948b8f0fe9dde430a1480` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `tests/resampling_null -m milestone -q` | PASS | `15d45ee89dd77c1573712d174e175e1369a0daf3ca0e6acdebef061ce046e96d` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Task 6 focused freeze/blinding/publication/state tests | PASS | `5603b3bdbd979d86e8c62be43291039331c1f18d392c470cba56f4eba489b84d` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Task 7 focused analysis/kernel-equivalence tests | PASS | `b2c6720453f06d35157bf6fc9703ffce184bf1d11bc189b38e5a9b17338d728b` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Task 8 focused power/authority/timing tests | PASS | `5952b218382e51f578768c0a348723d5418c12143cc6d5f49d527f1d1b978a79` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Task 9/10 focused artifact/CLI/branch/packet/release tests | PASS | `3d671003f3db5e1802f451e3671e4612726d7b6764553203c7954413f7eb3403` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Dual-worker admission, allocation, interruption, shard, reconciliation, throughput tests | PASS | `07c2eef926162e0090994bc913805aa08a8b2cbb5b21d2c933b937a10300713f` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Throughput/p10 contract tests | PASS | `83a1593c5b5783693fe3006d1f6597bcb4f3a5968f23b59481ee09a0477f910a` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `git diff --check` | PASS | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

The local compiler and fixtures fail closed for duplicate raw evidence, duplicate worker identity, non-L40S runtime metadata, altered tool/parity observations (the altered rung is rejected and the registered lower rung is selected), incorrect p10 derivation, duplicate work identifiers, partition overlap, and recovery-boundary mismatch. No GPU admission probe was run.

### Terraform

The first read-only init exposed a deterministic platform checksum omission in the committed AWS provider lockfile. The pinned provider version was not changed; one platform checksum was added and committed separately in `63156f34537be4b83638f9af84fb6bae1e92b1d6`. No Python/Ruff repair was needed.

Final Terraform checks:

| Command | Result | stdout SHA-256 | stderr SHA-256 |
| --- | --- | --- | --- |
| `terraform -chdir=infra/terraform init -input=false -lockfile=readonly` | PASS | `bb213aeed6080b9698415ec73b93f7e4364c46710afed0b78337e0f231aadf74` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `terraform -chdir=infra/terraform validate` | PASS | `2ff6f7b7b494d0f8d596def971d585d29ee3e06359aa4662e84c1988f7b74cbb` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `terraform -chdir=infra/terraform fmt -check` | PASS | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Saved plan with `-input=false -lock=false` and ignored private tfvars | PASS | `e56b83dc3fdc6961e521cead65924cbc47165d070245db849d42b367cce68a80` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Saved plan SHA-256: `7eb7e501b64ee0945e51978c7c30ed31f618a0812bb2486abb258ba5b1af20e9`.

The plan contains 35 hypothetical creates and 2 reads because no state was supplied; it is not an execution receipt. No `apply`, `destroy`, `import`, or provider mutation was run.

### Read-only AWS evidence

All queries targeted `us-east-1` and succeeded through the authenticated CLI. Raw responses were not copied into Git or this report.

| Observation | Result | raw stdout SHA-256 |
| --- | --- | --- |
| STS caller identity | PASS; identity present (sensitive fields withheld) | `34eb88e0bdea69c0559df2194aa817810a959283e89480ef7c3908f256ce76d3` |
| Running On-Demand G/VT quota | PASS; applied value 8 vCPUs | `87c50b0e185beb8ea51b484f7c394a6b52a7e7b14ec3375e869b21ed3e41c42f` |
| All G/VT Spot quota | PASS; applied value 16 vCPUs | `108d70494501f95656e54b6649387de9601a70eced286a6e58418ed6850e8c24` |
| `g6e.2xlarge` AZ offerings | PASS; 4 offerings | `a955a657417ef1d54e635bcd4596a247e44324a58958f7b6fc5975e5f0656c9f` |
| Linux/UNIX Spot price history | PASS; 23 observations, prices 2.0453–2.2421, 24-hour window | `08cb62b72a2c8fcc6b7bca52fd18d4995fb8de692788bea471dbeb6ca5ea7d77` |

The Spot window was `2026-08-01T22:26:29Z` through `2026-08-02T22:26:29Z` (window-file SHA-256 `83c4003f2094c27cb9fcd052bb62cb169714368b977155bf30038a2bd8a641e9`). Quota and offering observations do not prove current Spot capacity and do not authorize a launch.

## Remaining-blocker matrix

| Gate | State after this campaign | What remains |
| --- | --- | --- |
| Local contracts, schemas, compiler, partition, and recovery fixtures | Verified locally | Real provider semantics and two-worker receipts remain separate evidence. |
| AWS identity/quota/offering/price substrate | Fresh read-only evidence verified | Capacity at the intended start time and a launch-time receipt remain required. |
| Terraform L1 validation and saved L3 plan | Verified; plan-only | Deployment, image/runtime parity, teardown, and any resource mutation remain unauthorized. |
| Per-worker L40S admission | Missing | Two distinct real workers, distinct raw measurement evidence, and the frozen OOM/tool/parity/p10 receipt. |
| Canonical two-worker partition and interruption recovery | Local fixtures only | A real partition/recovery receipt over the two-worker route. |
| Step 14 hostile launch review | `launch_blocked` in canonical status | Real power/tier evidence and packet/assignment/detectability/unblind receipts are still absent. |
| Step 4B/P0/scientific lineage | Not run | Requires a fresh explicit authorization and run root. |
| Pilot, benchmark/model execution, unblind, official experiment | Not run | Each requires its own authorization and spend/authority gates. |

## Boundary statement

This is **not an experiment**. No GPU, model, benchmark, pilot, P0/Step 4B lineage, unblind, or official experiment ran. No cloud resource was created by this campaign, no cloud mutation was executed, and no spend was initiated. A Terraform plan's hypothetical creates are not resources. The canonical project status remains authoritative and scientifically gated.
