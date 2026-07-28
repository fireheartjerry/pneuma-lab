# Resampling Null Zero-Spend Core Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` to implement this plan, and apply
> `superpowers:test-driven-development` to every production change.

**Goal:** Build the benchmark-independent, zero-spend P0 core for sealed
four-slot assignment, snapshot-paired synthetic execution, audited verifier
packets, blinded artifacts, registered inference, and joint power/type-I
simulation.

**Architecture:** Add an isolated `pneuma_lab.resampling_null` package. The
scientific core depends on small protocols for models, environments, and
tokenizers; deterministic synthetic implementations exercise the entire
pipeline locally. Every persisted record is schema-validated, canonical,
atomic, and hash-linked. This plan deliberately excludes SWE-bench-Live, τ³,
vLLM, cloud SDKs, and provider provisioning.

**Tech stack:** Python 3.12, stdlib, existing `numpy>=2.0` and
`jsonschema>=4.20`, pytest. Reuse
`pneuma_lab.foundation.artifacts`; add no GPU, benchmark, cloud, SciPy, or API
dependency.

---

## Frozen public surface

```text
schemas/
    resampling-study-manifest.schema.json
    resampling-prefix-schedule.schema.json
    resampling-prefix-receipt.schema.json
    resampling-assignment-ledger.schema.json
    resampling-packet-index.schema.json
    resampling-task-block.schema.json
    resampling-blinded-projection.schema.json
    resampling-analysis-freeze.schema.json
    resampling-analysis.schema.json
    resampling-power-report.schema.json
    resampling-unblind-receipt.schema.json
    resampling-artifact-root.schema.json

src/pneuma_lab/resampling_null/
    __init__.py
    __main__.py
    types.py
    artifacts.py
    assignment.py
    packets.py
    controller.py
    synthetic.py
    freeze.py
    blinding.py
    analysis.py
    power.py
    cli.py

tests/resampling_null/
    test_types.py
    test_artifacts.py
    test_assignment.py
    test_packets.py
    test_controller.py
    test_freeze.py
    test_blinding.py
    test_analysis.py
    test_power.py
    test_cli.py

fixtures/resampling_null/
    p0-study.json
    p0-tasks.jsonl
    p0-power-grid.json
    p0-roster-synthetic.json
    p0-local-topology.json
    p0-required-kinds.json
```

## Task 1: Core records and invariants

**Files:**

- Create: `src/pneuma_lab/resampling_null/__init__.py`
- Create: `src/pneuma_lab/resampling_null/types.py`
- Create: `tests/resampling_null/test_types.py`

### Step 1: Write the failing tests

Cover:

- canonical arm order is `REAL, SHAM, NONE, RESAMPLE`;
- pre-orientation treatment order is `REAL, SHAM, NO_PACKET`;
- `SHAM_PACKET_ONLY` is the verdict name; `APPARATUS_ONLY` is absent;
- four slot seeds are pairwise distinct;
- binary endpoints reject booleans, floats, and integers outside `{0, 1}`;
- resource counters reject negative or non-finite values;
- SHA-256 fields require exactly 64 lowercase hexadecimal characters;
- frozen records reject mutation; and
- infrastructure failure forces `success == 0`.
- `TaskSchedule` binds exactly four unique slots to one task and prefix seed;
- task sensitivity labels are immutable, use registered language/domain/
  issue-family kinds, and cannot contain duplicate kinds;
- `FrozenVerifierReceipt` carries only schedule-bound artifact references and a
  count, never finding text or the not-yet-created prefix-index digest; and
- `TaskAssignment` maps every slot exactly once, contains two no-packet
  orientations, and validates all ancestry digests.

Start with this public shape:

```python
from dataclasses import dataclass
from enum import Enum


class Arm(str, Enum):
    REAL = "REAL"
    SHAM = "SHAM"
    NONE = "NONE"
    RESAMPLE = "RESAMPLE"


class Treatment(str, Enum):
    REAL = "REAL"
    SHAM = "SHAM"
    NO_PACKET = "NO_PACKET"


class Verdict(str, Enum):
    CAUSAL_CONTENT = "CAUSAL_CONTENT"
    SHAM_PACKET_ONLY = "SHAM_PACKET_ONLY"
    RESAMPLING_CONSISTENT = "RESAMPLING_CONSISTENT"
    HARMFUL_OR_MISDIRECTING = "HARMFUL_OR_MISDIRECTING"
    UNRESOLVED_RESAMPLING = "UNRESOLVED_RESAMPLING"
    PIPELINE_INVALID = "PIPELINE_INVALID"
    FEASIBILITY_NO_GO = "FEASIBILITY_NO_GO"


class GroupKind(str, Enum):
    LANGUAGE = "language"
    DOMAIN = "domain"
    ISSUE_FAMILY = "issue_family"


@dataclass(frozen=True, slots=True)
class GroupLabel:
    kind: GroupKind
    value: str


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    benchmark: str
    stratum: str
    lineage: str
    sensitivity_groups: tuple[GroupLabel, ...]


@dataclass(frozen=True, slots=True)
class BranchSlot:
    slot_id: str
    seed: int
    execution_order: int
    hardware_lane: int


@dataclass(frozen=True, slots=True)
class ResourceCounters:
    generated_tokens: int
    model_calls: int
    tool_calls: int
    wall_clock_ms: int


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    role: str
    relative_path: str
    sha256: str
    byte_count: int
    media_type: str


@dataclass(frozen=True, slots=True)
class BranchOutcome:
    task_id: str
    benchmark: str
    opaque_arm_id: str
    success: int
    prefix_success: int
    partial_reward: float
    infrastructure_failure: bool
    counters: ResourceCounters
    artifact_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class BranchSlotSet:
    slots: tuple[BranchSlot, BranchSlot, BranchSlot, BranchSlot]


@dataclass(frozen=True, slots=True)
class TaskSchedule:
    task: TaskSpec
    prefix_seed: int
    slots: BranchSlotSet
    provider_lane: str


@dataclass(frozen=True, slots=True)
class FrozenVerifierReceipt:
    task_id: str
    schedule_sha256: str
    snapshot_ref: ArtifactRef
    verifier_artifact_ref: ArtifactRef
    finding_count: int


@dataclass(frozen=True, slots=True)
class TaskAssignment:
    task_id: str
    task_lineage: str
    donor_task_id: str
    donor_lineage: str
    slot_arms: tuple[tuple[str, Arm], ...]
    schedule_sha256: str
    prefix_index_sha256: str
```

### Step 2: Prove the test is red

```powershell
python -m pytest tests/resampling_null/test_types.py -q
```

Expected: collection fails with `ModuleNotFoundError` for
`pneuma_lab.resampling_null`.

### Step 3: Implement the minimum invariants

Use `__post_init__` checks. Treat `bool` as invalid even though it subclasses
`int`. Require non-empty identifiers, finite partial reward, seed in
`[0, 2**64)`, and unique slot IDs/order values at the aggregate-record boundary.
`TaskSpec.sensitivity_groups` is a non-empty tuple with unique `GroupKind`
values, so τ³ can carry both domain and issue family while SWE carries language;
reject mutable containers.
`TaskAssignment` requires four unique slot IDs, every `Arm` exactly once, and
distinct task/donor IDs and lineages. Export only the stable record types from
`__init__.py`. `ArtifactRef.relative_path` must be normalized POSIX-relative,
must not contain `..`, a drive, or a leading slash, and must carry a valid
digest/nonnegative byte count. Reject mutable stand-ins for every tuple-typed
field, including the outer `BranchSlotSet.slots` and
`TaskAssignment.slot_arms` containers; a frozen dataclass containing a caller's
list is not immutable. `BranchOutcome` carries the full endpoint artifact
reference, never a bare digest. `FrozenVerifierReceipt.schedule_sha256` and
snapshot/verifier references bind it to inputs that already exist; it must not
refer to the aggregate prefix receipt that is sealed only after all task
receipts exist.

### Step 4: Prove the test is green

```powershell
python -m pytest tests/resampling_null/test_types.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/__init__.py src/pneuma_lab/resampling_null/types.py tests/resampling_null/test_types.py
git commit -m "feat(resampling-null): define core records"
```

## Task 2: JSON Schemas and canonical artifact IO

**Files:**

- Create: `schemas/resampling-study-manifest.schema.json`
- Create: `schemas/resampling-prefix-schedule.schema.json`
- Create: `schemas/resampling-prefix-receipt.schema.json`
- Create: `schemas/resampling-assignment-ledger.schema.json`
- Create: `schemas/resampling-packet-index.schema.json`
- Create: `schemas/resampling-task-block.schema.json`
- Create: `schemas/resampling-blinded-projection.schema.json`
- Create: `schemas/resampling-analysis-freeze.schema.json`
- Create: `schemas/resampling-analysis.schema.json`
- Create: `schemas/resampling-power-report.schema.json`
- Create: `schemas/resampling-unblind-receipt.schema.json`
- Create: `schemas/resampling-artifact-root.schema.json`
- Create: `src/pneuma_lab/resampling_null/artifacts.py`
- Create: `tests/resampling_null/test_artifacts.py`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `tests/test_schema_loads.py`

### Step 1: Write failing contract tests

Test:

- a new `RESAMPLING_SCHEMA_FILES` tuple registers exactly the twelve schemas;
- all twelve use Draft 2020-12, `additionalProperties: false`,
  `x-pneuma-schema-kind: "resampling-study"`, and version `0.1.0`;
- unknown record kinds, unknown properties, duplicate JSON keys, `NaN`, and
  malformed digests fail closed;
- packet-index `stage` is exactly `candidate` or `sealed`, power-report `stage`
  is exactly `screen`, `shard`, `selection`, `validation`, or `final`, and each
  stage has a closed `oneOf` payload;
- canonical digest is byte-identical across mapping insertion order;
- changing one nested outcome invalidates its recorded digest link;
- JSON and JSONL writes publish no partial output after serialization failure;
- the artifact root excludes its own receipt, sorts entries by relative path,
  rejects missing/extra required document kinds, and detects any byte change;
- artifact-root sealing recursively follows every nested `artifact_ref`, rejects
  dangling or conflicting references, and detects a changed raw
  snapshot/packet/grade byte;
- manifest, schedule, prefix-index, assignment, projection, freeze, analysis,
  and unblind kinds are singleton; packet-index identities are exactly one
  candidate and one sealed record; task-block identities are unique by
  `task_id` with exact roster coverage; and append-only power-attempt
  identities are unique by authority, phase, generation, stage, and shard
  index while exactly one final report parents every attempt and closes as
  either a completed selected chain or a terminal feasibility no-go;
- scientific builders remain byte-identical when the wall clock is monkeypatched;
- study-manifest sealing copies external task/roster, assignment/provider,
  tokenizer/template/policy/pad-set, revision, and required-kind sources under
  the study root and refuses any scientific record before that manifest exists;
  and
- resampling schemas do not enter `INPUT_SCHEMA_FILES` or
  `OUTPUT_SCHEMA_FILES`.

Use record kinds:

```text
resampling_study_manifest
resampling_prefix_schedule
resampling_prefix_receipt
resampling_assignment_ledger
resampling_packet_index
resampling_task_block
resampling_blinded_projection
resampling_analysis_freeze
resampling_analysis
resampling_power_report
resampling_unblind_receipt
resampling_artifact_root
```

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q
```

Expected: missing bucket and missing schemas.

### Step 3: Add the schemas and registry bucket

Add:

```python
RESAMPLING_SCHEMA_FILES = (
    "resampling-study-manifest.schema.json",
    "resampling-prefix-schedule.schema.json",
    "resampling-prefix-receipt.schema.json",
    "resampling-assignment-ledger.schema.json",
    "resampling-packet-index.schema.json",
    "resampling-task-block.schema.json",
    "resampling-blinded-projection.schema.json",
    "resampling-analysis-freeze.schema.json",
    "resampling-analysis.schema.json",
    "resampling-power-report.schema.json",
    "resampling-unblind-receipt.schema.json",
    "resampling-artifact-root.schema.json",
)
```

Include it in `ALL_SCHEMA_FILES` and `__all__`. Increment the expected count in
`tests/test_schema_loads.py` without changing frame counts.

Every record schema must require:

```json
{
    "record_kind": "one of the twelve constants",
    "schema_version": "0.1.0",
    "study_id": "non-empty stable identifier",
    "frozen_created_at": "the manifest-injected frozen UTC RFC3339 string",
    "provenance": {
        "design_sha256": "64 lowercase hex",
        "code_sha256": "64 lowercase hex"
    }
}
```

Every schema has one closed `payload` with these required keys (stage-specific
`oneOf` arms may add only the keys named here):

| record kind | required payload keys |
| --- | --- |
| `resampling_study_manifest` | `task_registry_ref`, `roster_ref`, `assignment_program_ref`, `provider_lane_plan_ref`, `tokenizer_ref`, `packet_template_ref`, `packet_policy_ref`, `pad_unit_set_ref`, `source_revision_refs`, `seed_commitment_sha256`, `required_document_kinds_ref` |
| `resampling_prefix_schedule` | `manifest_ref`, `assignment_program_ref`, `provider_lane_plan_ref`, `study_seed`, `tasks` |
| `resampling_prefix_receipt` | `schedule_ref`, `task_receipts` |
| `resampling_assignment_ledger` | `schedule_ref`, `prefix_index_ref`, `assignment_mode`, `assignments`, `allocation_receipts` |
| `resampling_packet_index` | `stage`; candidate: `assignment_ref`, `prefix_index_ref`, `tokenizer_ref`, `packet_template_ref`, `packet_policy_ref`, `pad_unit_set_ref`, `entries`; sealed: `candidate_ref`, the same six parent refs, `audit_gates` |
| `resampling_task_block` | every field of `TaskBlock`, with exactly four opaque `slot_outcomes` |
| `resampling_blinded_projection` | `schedule_ref`, `analysis_freeze_ref`, `task_block_refs`, `rows`, `expected_task_count`, `complete` |
| `resampling_analysis_freeze` | `source_refs`, `config_ref`, `projection_schema_ref`, `packet_index_ref` |
| `resampling_analysis` | `analysis_freeze_ref`, `projection_ref`, `unblind_receipt_ref`, `config_ref`, `row_count`, `result`, `numeric_receipt` |
| `resampling_power_report` | `stage`, `decision_authority`, `phase`, `generation`, `roster_ref`, `grid_ref`, `parent_refs`; stage-specific numeric/topology/cell/count/interval/decision payload; `validation` is phase-discriminated; final additionally requires `all_attempt_refs` and a closed `finalization` `oneOf` (Gaussian completed chain, full-multiplier completed chain, or `feasibility_no_go`) |
| `resampling_unblind_receipt` | every field of `UnblindReceipt` |
| `resampling_artifact_root` | `code_sha256`, `design_sha256`, `entries`, `root_sha256`, `required_document_kinds` |

Array order and uniqueness constraints mirror the frozen dataclasses. A schema
cannot replace an ArtifactRef with a naked digest.

Every referenced blob uses one shared `$defs.artifact_ref` with a
root-relative POSIX name, SHA-256, byte size, and media type. Absolute paths are
forbidden. Schedule, prefix, assignment, packet, projection, freeze, power,
unblind, and artifact-root schemas require their exact parent digests. The task
block has closed triggered/no-trigger `oneOf` arms. A triggered block embeds
every chronological attempt with all terminal receipts completed in that
attempt—including superseded and partial attempts—plus four outcome-source
terminal receipts, four execution receipts, the selected attempt index,
optional outage receipt, validity-event refs, a sealed packet-index ref (the
packet-audit parent), four outcomes, and parent refs. A no-trigger block embeds
none of the branch-only receipts and
carries four copied `Y_0` outcomes. Because attempt, terminal, execution, and
outage receipts carry snapshot, provider-event, provider-cost, adverse-event,
and grade refs, the task block exposes the complete raw-blob closure to the
artifact-root walker. The analysis schema requires freeze/projection digests, counts,
estimands, Fisher p-values, simultaneous bounds, `q0`, `r95`, gates, verdict,
and ancestry.

The packet-index schema is a discriminated `oneOf`: a `candidate` document
contains complete pair receipts and encrypted/synthetic packet references; a
`sealed` document additionally contains all audit gates and parents the
candidate digest. Branch execution accepts only `stage == "sealed"`. The
power-report schema similarly discriminates `screen`, `shard`, `selection`,
`validation`, and `final`; no persisted simulator phase is an unvalidated ad
hoc JSON file.

All scientific builders receive `frozen_created_at` explicitly from the study
manifest. Unit tests monkeypatch the wall clock to raise if any scientific
builder reads it. Operational timestamps are separate and excluded from the
scientific artifact-root digest.

### Step 4: Implement artifact helpers

Reuse:

```python
from pneuma_lab.foundation.artifacts import (
    canonical_json_bytes,
    write_atomic_json,
    write_atomic_jsonl,
)
```

Implement this stable surface:

```python
SCHEMA_BY_KIND = {
    "resampling_study_manifest": "resampling-study-manifest.schema.json",
    "resampling_prefix_schedule": "resampling-prefix-schedule.schema.json",
    "resampling_prefix_receipt": "resampling-prefix-receipt.schema.json",
    "resampling_assignment_ledger": "resampling-assignment-ledger.schema.json",
    "resampling_packet_index": "resampling-packet-index.schema.json",
    "resampling_task_block": "resampling-task-block.schema.json",
    "resampling_blinded_projection": "resampling-blinded-projection.schema.json",
    "resampling_analysis_freeze": "resampling-analysis-freeze.schema.json",
    "resampling_analysis": "resampling-analysis.schema.json",
    "resampling_power_report": "resampling-power-report.schema.json",
    "resampling_unblind_receipt": "resampling-unblind-receipt.schema.json",
    "resampling_artifact_root": "resampling-artifact-root.schema.json",
}


class RecordValidationError(ValueError):
    pass


def canonical_digest(value: Mapping[str, object]) -> str:
    return hashlib.sha256(
        canonical_json_bytes(dict(value), indent=None)
    ).hexdigest()


def validate_record(value: Mapping[str, object]) -> dict[str, object]:
    ...


def load_record(path: Path) -> dict[str, object]:
    ...


def write_record(
    path: Path,
    value: Mapping[str, object],
    *,
    run_root: Path,
    role: str,
) -> ArtifactRef:
    ...


def write_jsonl_artifact(
    path: Path,
    rows: Iterable[Mapping[str, object]],
    *,
    run_root: Path,
    role: str,
) -> ArtifactRef:
    ...


def seal_study_manifest(
    study_source: Path,
    tasks_source: Path,
    roster_source: Path,
    assignment_program_source: Path,
    provider_lane_plan_source: Path,
    tokenizer_source: Path,
    packet_template_source: Path,
    packet_policy_source: Path,
    pad_unit_set_source: Path,
    source_revision_sources: Sequence[Path],
    required_document_kinds_source: Path,
    *,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def verify_digest_link(
    child: Mapping[str, object],
    field: str,
    parent: Mapping[str, object],
) -> None:
    ...


@dataclass(frozen=True, slots=True)
class ArtifactEntry:
    relative_path: str
    sha256: str
    byte_count: int
    entry_kind: Literal["scientific_record", "referenced_blob"]
    document_kind: str | None
    role: str
    media_type: str


def seal_artifact_root(
    run_root: Path,
    required_document_kinds: Collection[str],
    out: Path,
    *,
    study_id: str,
    frozen_created_at: str,
    provenance: Mapping[str, str],
) -> ArtifactRef:
    ...


def verify_artifact_root(
    receipt_path: Path,
    run_root: Path,
    *,
    required_document_kinds: Collection[str],
) -> None:
    ...
```

`load_record` decodes UTF-8 without BOM and uses an `object_pairs_hook` that
raises on duplicate keys. `validate_record` uses
`Draft202012Validator.iter_errors`, sorts errors deterministically, and rejects
non-finite numbers before schema validation. `write_record` validates fully
before calling the existing atomic writer. Both write helpers resolve `path`
inside `run_root`, refuse any existing destination, and return the actual
root-relative digest/size/media-type/role reference. JSONL rows are materialized
once, checked for finite values, and canonically encoded before the atomic
publish. `seal_study_manifest` validates the external study template, copies
and references the exact task registry, roster/group manifest, revision
receipts, assignment program, provider-lane plan, tokenizer receipt, packet
template, packet policy, neutral pad-unit set, and required-kind manifest under
`run_root`, and writes the first
scientific root. Revision sources are non-empty, sorted by normalized source
name, and copied by content digest. It injects the one frozen timestamp used by
all descendants.
`seal_artifact_root` enumerates schema-valid scientific records under
`run_root`, then recursively walks every mapping/list in those records for the
schema's exact `$defs.artifact_ref` shape. It resolves and verifies every
referenced raw blob under the same root, including ciphertext packets,
snapshots, streams, grade output, and source bundles. It rejects dangling refs,
size/digest mismatches, two refs that claim different metadata for one path,
an unreferenced scientific root, and a raw file presented as a scientific
record. Manifest, schedule, prefix-index, assignment, projection, freeze,
analysis, and unblind kinds are singleton. Packet-index identity is
`(record_kind, stage)` and requires exactly one candidate plus one sealed
record. Task-block identity is `(record_kind, task_id)` and requires exactly one
block for every manifest-roster task. A non-final power-attempt identity is
`(decision_authority, phase, generation, stage, shard_index_or_null)`, where
`phase` is `gaussian_approximation` or `full_multiplier_fallback` and generation
is a nonnegative append-only retry number. Duplicate identities are rejected,
but later immutable generations are retained. Exactly one final power report
per authority parents every attempted screen/shard/selection/validation record
and has a closed finalization arm: `completed_chain` names its selected
phase/generation and phase-appropriate downstream refs, while
`feasibility_no_go` names the terminal failed attempt/stage and reason with no
fictitious downstream refs. A Gaussian completed chain requires its worst-five
selection and approximation-validation receipt; a full-multiplier completed
chain instead requires its fallback trigger and full-grid
completeness/numeric/tier-validation receipt and forbids a Gaussian selection.
It
sorts the union of scientific and raw `ArtifactEntry` values by relative POSIX
path and computes:

```text
root_sha256 = sha256(canonical_json(sorted(entries)))
```

The receipt itself is excluded from `entries` and from `root_sha256`; `out`
must be exactly `run_root / "p0-core-receipt.json"`. Verification reloads every
entry, checks bytes/media metadata and document-kind coverage, recursively
recomputes the reference closure, recomputes the root, and rejects an unlisted
scientific record or referenced blob. Operational receipts are explicitly
excluded by document kind and must live under a declared operational subtree
outside the scientific closure. The required-kind manifest lists the eleven
upstream scientific
record kinds and deliberately excludes `resampling_artifact_root`, whose
presence is established by validating the receipt itself.

### Step 5: Prove green

```powershell
python -m pytest tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q
```

Expected: pass.

### Step 6: Commit

```powershell
git add schemas/resampling-*.schema.json src/pneuma_lab/schemas/__init__.py src/pneuma_lab/resampling_null/artifacts.py tests/test_schema_loads.py tests/resampling_null/test_artifacts.py
git commit -m "feat(resampling-null): add artifact contracts"
```

## Task 3: Two-stage schedule and four-slot assignment seals

**Files:**

- Create: `src/pneuma_lab/resampling_null/assignment.py`
- Create: `tests/resampling_null/test_assignment.py`

### Step 1: Write failing assignment tests

Test:

- roster input order cannot affect bytes or digest;
- identical roster, study seed, and secret produce identical output;
- domain-separated prefix, slot, donor, order, and capability values differ;
- prefix schedule contains no donor, packet, arm, or outcome field;
- branch assignment cannot be materialized before every frozen prefix/verifier
  receipt is present and digest-valid;
- every task gets four distinct seed streams and a permutation of execution
  order `0..3`;
- the treatment multiset is exactly `{REAL, SHAM, NO_PACKET, NO_PACKET}`;
- the two no-packet slots receive NONE/RESAMPLE by a separate fair-bit draw;
- all 12 treatment allocations and both no-packet orientations are reachable
  across a deterministic seed sweep;
- donor has a different task and lineage, with no reciprocal pair;
- strata with fewer than three distinct eligible lineages fail closed;
- capability IDs contain no arm spelling and change with the secret; and
- the ledger records the 12-way treatment index and separate no-packet coin;
  and
- `require_confirmation_assignment` rejects any mode other than
  `confirmation_lineage_matching` or any ancestry mismatch.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_assignment.py -q
```

Expected: import failure.

### Step 3: Implement unbiased digest-bound draws

Never use Python's randomized `hash()` or modulo a digest directly. Implement:

```python
def derive_seed(study_seed: int, task_id: str, role: str) -> int:
    payload = f"resampling-null:v1:{study_seed}:{task_id}:{role}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def uniform_below(key: bytes, message: bytes, upper: int) -> int:
    if upper <= 0:
        raise ValueError("upper must be positive")
    limit = (1 << 64) - ((1 << 64) % upper)
    counter = 0
    while True:
        digest = hmac.new(
            key,
            message + counter.to_bytes(8, "big"),
            hashlib.sha256,
        ).digest()
        value = int.from_bytes(digest[:8], "big")
        if value < limit:
            return value % upper
        counter += 1


def arm_capability(
    secret: bytes,
    study_id: str,
    task_id: str,
    slot_id: str,
    arm: Arm,
) -> str:
    payload = (
        f"resampling-null:capability:v1:{study_id}\0"
        f"{task_id}\0{slot_id}\0{arm.value}"
    ).encode()
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def require_confirmation_assignment(
    ledger: "AssignmentLedger",
    *,
    expected_schedule_sha256: str,
    expected_prefix_index_sha256: str,
) -> None:
    ...
```

Implement two distinct transactions:

```python
@dataclass(frozen=True, slots=True)
class PrefixSchedule:
    study_id: str
    frozen_created_at: str
    manifest_ref: ArtifactRef
    assignment_program_ref: ArtifactRef
    provider_lane_plan_ref: ArtifactRef
    study_seed: int
    tasks: tuple[TaskSchedule, ...]


@dataclass(frozen=True, slots=True)
class AllocationReceipt:
    task_id: str
    treatment_allocation_index: int
    no_packet_orientation_bit: int
    slot_capabilities: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class AssignmentLedger:
    study_id: str
    frozen_created_at: str
    schedule_sha256: str
    prefix_index_sha256: str
    assignment_mode: str
    assignments: tuple[TaskAssignment, ...]
    allocation_receipts: tuple[AllocationReceipt, ...]


def seal_prefix_schedule(
    manifest_ref: ArtifactRef,
    assignment_program_ref: ArtifactRef,
    provider_lane_plan_ref: ArtifactRef,
    *,
    study_seed: int,
    run_root: Path,
) -> "PrefixSchedule":
    ...


def seal_branch_assignment(
    schedule: "PrefixSchedule",
    *,
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    run_root: Path,
    secret: bytes,
) -> "AssignmentLedger":
    ...
```

`seal_prefix_schedule` loads the task registry and roster only through the
validated manifest, and loads the provider-lane mapping and assignment program
through their ArtifactRefs; it accepts no free task list or claimed parent
digest. The prefix schedule fixes roster, prefix/slot seeds, task order, and
provider lane before prefixes; it contains no donor or treatment. Only after all common
prefixes and verifier artifacts are frozen does `seal_branch_assignment`
load the schema-valid prefix index through `prefix_index_ref`, validate its
schedule parent and exact roster coverage, derive all verifier receipts
internally, materialize the donor map, and draw
treatments. No branch endpoint is an input.

The schema-valid `resampling-prefix-receipt` document is the complete
prefix/verifier index: it nests one `FrozenVerifierReceipt` plus snapshot and
grade artifact references per scheduled task. Thus the CLI's
`--prefix-index` is not a thirteenth ad hoc record kind. The assignment
function verifies its digest and exact task coverage before creating any
`AllocationReceipt`.

Precompute the 12 lexicographically ordered assignments of
`(Treatment.REAL, Treatment.SHAM, Treatment.NO_PACKET,
Treatment.NO_PACKET)` to four slots. Draw one with
`uniform_below(..., 12)`, then orient NONE/Z with a domain-separated
`uniform_below(..., 2)` call. Persist both the treatment-allocation index and
orientation bit before emitting the post-orientation `Arm` map. Sort tasks by
`(benchmark, stratum, lineage, task_id)`.

Within each stratum, deterministically order candidates by an HMAC key and
search cyclic offsets for the first complete donor map with different task,
different lineage, and no reciprocal edge. Fail if none exists. Mark this
local implementation:

```json
{"assignment_mode": "synthetic_derangement"}
```

Both sealed records link to their parent digest. Benchmark adapters must later
produce and validate their own
`confirmation_lineage_matching` ledger.

### Step 4: Prove green

```powershell
python -m pytest tests/resampling_null/test_assignment.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/assignment.py tests/resampling_null/test_assignment.py
git commit -m "feat(resampling-null): seal four-slot assignments"
```

## Task 4: Token-exact REAL/SHAM packet construction

**Files:**

- Create: `src/pneuma_lab/resampling_null/packets.py`
- Create: `tests/resampling_null/test_packets.py`
- Modify: `src/pneuma_lab/resampling_null/types.py`
- Modify: `src/pneuma_lab/resampling_null/__init__.py`

### Step 1: Write failing packet tests

Cover:

- REAL and SHAM use identical field order, field count, severity multiset, and
  formatting;
- injected tokenizer reports equal token counts, while token IDs may differ;
- donor identifiers are replaced by type-preserving focal-safe aliases;
- SHAM evidence that collides with a true focal finding blocks the pair;
- impossible exact padding raises `PacketInvalid`;
- no packet contains donor task, lineage, arm, or capability identifiers;
- every bounded truncation emits original/retained digests, token counts, rule,
  and omitted count;
- an identifier map whose source/destination kinds differ fails;
- packet ancestry binds focal/donor verifier, assignment, identifier-map, and
  tokenizer digests;
- candidate audit proves every focal/donor verifier reference belongs to the
  sealed prefix index and every tokenizer/pad/template ref matches its parent;
- a no-intervention task is roster-covered by a typed marker and has no packet
  artifacts;
- neutral padding cannot introduce executable instructions or identifiers; and
- repeated audit runs and the sealed packet index are byte-identical.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_packets.py -q
```

Expected: import failure.

### Step 3: Implement the injected protocols and records

```python
class Tokenizer(Protocol):
    def encode(self, text: str) -> tuple[int, ...]:
        ...


class IdentifierKind(str, Enum):
    REPOSITORY_FILE = "repository_file"
    SYMBOL = "symbol"
    TEST_CHECK = "test_check"
    DATABASE_ENTITY = "database_entity"
    POLICY_ACTION = "policy_action"
    TASK_RECORD = "task_record"


@dataclass(frozen=True, slots=True)
class IdentifierAtom:
    entity_id: str
    kind: IdentifierKind


@dataclass(frozen=True, slots=True)
class LiteralAtom:
    text: str


PacketAtom = IdentifierAtom | LiteralAtom


@dataclass(frozen=True, slots=True)
class VerifierFinding:
    finding_id: str
    component: str
    code: str
    severity: str
    atoms: tuple[PacketAtom, ...]


@dataclass(frozen=True, slots=True)
class BoundedFinding:
    finding_id: str
    atoms: tuple[PacketAtom, ...]
    original_sha256: str
    retained_sha256: str
    original_chars: int
    retained_chars: int
    original_tokens: int
    retained_tokens: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class PacketPolicy:
    max_findings: int
    max_evidence_tokens: int
    normalizer_version: str


@dataclass(frozen=True, slots=True)
class TruncationReceipt:
    finding_id: str
    original_sha256: str
    retained_sha256: str
    original_chars: int
    retained_chars: int
    original_tokens: int
    retained_tokens: int
    omitted_atom_count: int
    rule: str


class PacketArtifactStore(Protocol):
    def put_text(
        self,
        relative_path: str,
        text: str,
        *,
        role: Literal["private_guidance"],
    ) -> ArtifactRef:
        ...


@dataclass(frozen=True, slots=True)
class PaddingSearchReceipt:
    pad_unit_set_sha256: str
    target_token_count: int
    states_explored: int
    selected_unit_counts: tuple[tuple[str, int], ...]
    search_algorithm: Literal["exact_dynamic_program_v1"]


@dataclass(frozen=True, slots=True)
class PacketPairReceipt:
    task_id: str
    donor_task_id: str
    prefix_index_sha256: str
    real_ref: ArtifactRef
    sham_ref: ArtifactRef
    real_token_count: int
    sham_token_count: int
    focal_verifier_ref: ArtifactRef
    donor_verifier_ref: ArtifactRef
    assignment_ref: ArtifactRef
    identifier_map_ref: ArtifactRef
    tokenizer_ref: ArtifactRef
    packet_template_ref: ArtifactRef
    normalized_real_ref: ArtifactRef
    normalized_sham_ref: ArtifactRef
    packet_policy_ref: ArtifactRef
    pad_unit_set_ref: ArtifactRef
    padding_search: PaddingSearchReceipt
    field_order: tuple[str, ...]
    severity_multiset: tuple[str, ...]
    schema_parity: Literal[True]
    field_parity: Literal[True]
    severity_parity: Literal[True]
    focal_collision_count: Literal[0]
    rewrite_expected: int
    rewrite_completed: int
    unmapped_identifiers: tuple[str, ...]
    donor_literal_collisions: tuple[str, ...]
    truncation_receipts: tuple[TruncationReceipt, ...]


@dataclass(frozen=True, slots=True)
class NoInterventionPacketMarker:
    task_id: str
    prefix_index_sha256: str
    trigger_reason: Literal["no_intervention_opportunity"]


def build_packet_pair(
    real: Sequence[VerifierFinding],
    donor: Sequence[VerifierFinding],
    *,
    tokenizer: Tokenizer,
    policy: PacketPolicy,
    identifier_map: Mapping[IdentifierAtom, IdentifierAtom],
    true_focal_signatures: frozenset[str],
    neutral_pad_units: Sequence[str],
    artifact_store: PacketArtifactStore,
    real_relative_path: str,
    sham_relative_path: str,
    task_id: str,
    donor_task_id: str,
    prefix_index_sha256: str,
    focal_verifier_ref: ArtifactRef,
    donor_verifier_ref: ArtifactRef,
    assignment_ref: ArtifactRef,
    identifier_map_ref: ArtifactRef,
    tokenizer_ref: ArtifactRef,
    packet_template_ref: ArtifactRef,
    packet_policy_ref: ArtifactRef,
    pad_unit_set_ref: ArtifactRef,
) -> PacketPairReceipt:
    ...


def write_packet_candidate(
    entries: Sequence[PacketPairReceipt | NoInterventionPacketMarker],
    *,
    assignment_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    tokenizer_ref: ArtifactRef,
    packet_template_ref: ArtifactRef,
    packet_policy_ref: ArtifactRef,
    pad_unit_set_ref: ArtifactRef,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def audit_and_seal_packet_index(
    candidate_ref: ArtifactRef,
    *,
    expected_task_ids: Collection[str],
    assignment_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    tokenizer_ref: ArtifactRef,
    packet_template_ref: ArtifactRef,
    packet_policy_ref: ArtifactRef,
    pad_unit_set_ref: ArtifactRef,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...
```

Normalize and truncate both reports through one bounded deterministic policy
before templating; normalization must turn every recognized identifier into an
`IdentifierAtom`, audit literal atoms for leaked donor identifiers, truncate
only at atom boundaries, and record every omission. Require every replacement
to preserve `IdentifierKind`. Search
deterministic combinations of frozen neutral pad units by dynamic programming
over tokenizer-length deltas; do not mutate retained semantic fields. Validate
exact subject-token count, schema/field parity, severity parity, completed
rewrites, zero unmapped identifiers, zero donor-literal collisions, focal
collision absence, and ancestry before returning. Persist packet texts through
their encrypted/synthetic artifact references; do not embed them in the packet
index. The production `PacketArtifactStore` must encrypt bytes before writing;
the synthetic store may write fixture plaintext under ignored `build/`.

Packet construction emits pair receipts, then `write_packet_candidate` writes a
schema-valid `resampling_packet_index` with `stage == "candidate"`; candidate
packet bytes remain encrypted in production. A separate
`audit_and_seal_packet_index` transaction loads that immutable parent and
verifies exact roster coverage,
one focal/donor pair per task, assignment/prefix/verifier ancestry, token and
schema parity, all rewrite/truncation audits, and referenced artifact bytes. It
loads the sealed prefix index and derives the allowed focal/donor verifier refs
from it; naked claimed digests are insufficient. It also verifies the exact
tokenizer, packet-template, identifier-map, pad-unit-set, normalized-finding,
policy, padding-search, collision, field-order, and severity-multiset receipts.
Every no-intervention marker must correspond to a scheduled prefix whose
trigger reason is `NO_INTERVENTION_OPPORTUNITY`, and such a task must reference
no packet bytes. It
then atomically writes a second schema-valid packet index with
`stage == "sealed"` and a candidate parent digest. No branch may start from a
candidate or an unaudited index.

### Step 4: Prove green

```powershell
python -m pytest tests/resampling_null/test_packets.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/types.py src/pneuma_lab/resampling_null/__init__.py src/pneuma_lab/resampling_null/packets.py tests/resampling_null/test_packets.py
git commit -m "feat(resampling-null): build audited verifier packets"
```

## Task 5: Two-stage snapshot-paired synthetic controller

**Files:**

- Create: `src/pneuma_lab/resampling_null/controller.py`
- Create: `src/pneuma_lab/resampling_null/synthetic.py`
- Create: `tests/resampling_null/test_controller.py`
- Modify: `src/pneuma_lab/resampling_null/types.py`
- Modify: `src/pneuma_lab/resampling_null/__init__.py`

### Step 1: Write failing controller tests

Prove:

- the common prefix executes exactly once;
- a trigger can occur only after a completed tool boundary;
- all task prefixes/verifier artifacts can be sealed before any branch starts;
- queued multi-tool outputs cannot overshoot the first eligible trigger because
  the controller checks after each completed tool result;
- each arm restores into a fresh environment instance;
- all four pre-branch visible-state digests and tokenized contexts are equal;
- packet text enters only `SubjectContext.private_guidance`, never environment
  state or the simulated user's visible context;
- all four continuation seed streams are distinct;
- every subject and simulator call seed is domain-separated from its slot root,
  indexed, persisted, and reproducible;
- τ³ simulator execution goes through an explicit controller-owned seeded
  protocol in both the prefix and branch loops; the environment cannot call an
  unseeded simulator internally;
- arm labels follow the sealed slot allocation, never run order or outcome;
- REAL/SHAM receive their matched packets and NONE/RESAMPLE receive no message;
- a serialized worker order contains no arm name, donor ID/lineage, packet-pair
  receipt, clear ledger, or other slot;
- all arms receive identical caps;
- a no-trigger terminal task runs no branches and emits four copies of `Y_0`;
- timeout, cap, malformed action, and arm-specific infrastructure failure become
  adverse zero;
- an arm-blind outage receipt created before any endpoint is readable may rerun
  the whole block once with identical snapshot, slots, seeds, and allocation;
- an incomplete full-block rerun emits four zeros and never deletes the task;
- mutating the deepest final-snapshot, provider-event, provider-cost, or grade
  blob reachable only through an embedded slot/outage receipt breaks task-block
  and artifact-root verification;
- mutating a final snapshot from a superseded first attempt or from a completed
  slot inside an incomplete second attempt also breaks verification;
- no rerun API accepts a graded receipt or any readable endpoint;
- restored pending prefix tool calls execute before the first packet-visible
  model call and count against the post-trigger tool-call/wall-clock caps;
- the one permitted full-block rerun cannot change any seed, task, slot, or
  sample ID; and
- mutable state from one branch cannot leak into another.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_controller.py -q
```

Expected: import failure.

### Step 3: Add one controller-owned stepping engine

Extend `types.py` with the exact frozen/slotted records below. Tuple fields
reject mutable containers. The prefix receipt stores only immutable
snapshot/context/verifier references, trigger reason, pending tool calls,
`Y_0`, and parent schedule digest; it does not embed mutable adapter objects.

```python
class FailureKind(str, Enum):
    NONE = "none"
    MODEL = "model"
    MALFORMED_ACTION = "malformed_action"
    TOKEN_CAP = "token_cap"
    TOOL_CAP = "tool_cap"
    TIMEOUT = "timeout"
    INFRASTRUCTURE = "infrastructure"


class TriggerReason(str, Enum):
    FIRST_ELIGIBLE_MUTATION = "first_eligible_mutation"
    FOURTH_TOOL_CALL = "fourth_tool_call"
    NO_INTERVENTION_OPPORTUNITY = "no_intervention_opportunity"


@dataclass(frozen=True, slots=True)
class ContextMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ToolCall:
    call_id: str
    name: str
    canonical_arguments_json: str


@dataclass(frozen=True, slots=True)
class SubjectContext:
    messages: tuple[ContextMessage, ...]
    private_guidance: str | None


@dataclass(frozen=True, slots=True)
class PrefixCaps:
    generated_tokens: int
    model_calls: int
    tool_calls: int
    wall_clock_ms: int


@dataclass(frozen=True, slots=True)
class BranchCaps:
    generated_tokens: int
    model_calls: int
    tool_calls: int
    wall_clock_ms: int
    pending_prefix_calls_count_against_tool_cap: Literal[True]


@dataclass(frozen=True, slots=True)
class GradeReceipt:
    success: int
    partial_reward: float
    infrastructure_failure: bool
    artifact_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class CallSeedReceipt:
    subject_role: Literal["primary_subject", "user_simulator"]
    call_index: int
    seed: int


@dataclass(frozen=True, slots=True)
class FrozenPrefixReceipt:
    task_id: str
    schedule_sha256: str
    snapshot_ref: ArtifactRef
    visible_context_ref: ArtifactRef
    visible_sha256: str
    token_ids_sha256: str
    pending_tool_calls: tuple[ToolCall, ...]
    trigger_reason: TriggerReason
    y0_grade: GradeReceipt
    verifier_receipt: FrozenVerifierReceipt
    counters: ResourceCounters
    call_seeds: tuple[CallSeedReceipt, ...]
    provider_cost_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class PrefixIndex:
    study_id: str
    frozen_created_at: str
    schedule_ref: ArtifactRef
    task_receipts: tuple[FrozenPrefixReceipt, ...]


@dataclass(frozen=True, slots=True)
class OutageReceipt:
    task_id: str
    provider_event_ref: ArtifactRef
    first_attempt: "AttemptReceipt"
    detected_before_endpoint_readable: Literal[True]
    work_order_sha256s: tuple[str, str, str, str]
    rerun_index: Literal[1]


@dataclass(frozen=True, slots=True)
class SubjectTurn:
    text: str
    tool_calls: tuple["ToolCall", ...]
    generated_tokens: int
    finish_reason: str | None


@dataclass(frozen=True, slots=True)
class ToolBoundary:
    tool_call_count: int
    completed: bool
    mutated: bool
    verifier_eligible: bool
    failure_kind: "FailureKind"


def derive_call_seed(
    slot_seed: int,
    subject_role: Literal["primary_subject", "user_simulator"],
    call_index: int,
) -> int:
    payload = (
        f"resampling-null:call-seed:v1:{slot_seed}:"
        f"{subject_role}:{call_index}"
    ).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


class Subject(Protocol):
    def generate(
        self,
        context: "SubjectContext",
        *,
        seed: int,
        call_index: int,
        caps: "PrefixCaps | BranchCaps",
    ) -> SubjectTurn:
        ...


class UserSimulator(Protocol):
    def generate(
        self,
        context: "SubjectContext",
        *,
        seed: int,
        call_index: int,
        caps: "PrefixCaps | BranchCaps",
    ) -> SubjectTurn:
        ...


class EnvironmentAdapter(Protocol):
    def start(self, schedule: TaskSchedule) -> "RuntimeState":
        ...

    def visible_context(self, state: "RuntimeState") -> "SubjectContext":
        ...

    def append_assistant(
        self,
        state: "RuntimeState",
        turn: SubjectTurn,
    ) -> tuple["ToolCall", ...]:
        ...

    def execute_tool(
        self,
        state: "RuntimeState",
        call: "ToolCall",
    ) -> ToolBoundary:
        ...

    def snapshot(
        self,
        state: "RuntimeState",
        pending: tuple["ToolCall", ...],
    ) -> bytes:
        ...

    def restore(
        self,
        snapshot: bytes,
    ) -> tuple["RuntimeState", tuple["ToolCall", ...]]:
        ...

    def context_token_ids(self, context: "SubjectContext") -> tuple[int, ...]:
        ...

    def visible_digest(self, state: "RuntimeState") -> str:
        ...

    def simulator_context(
        self,
        state: "RuntimeState",
    ) -> "SubjectContext | None":
        ...

    def append_simulator_turn(
        self,
        state: "RuntimeState",
        turn: SubjectTurn,
    ) -> None:
        ...

    def grade_clone(self, snapshot: bytes) -> "GradeReceipt":
        ...

    def verify_clone(self, snapshot: bytes) -> FrozenVerifierReceipt:
        ...


class BinaryArtifactStore(Protocol):
    def put_bytes(
        self,
        relative_path: str,
        value: bytes,
        *,
        media_type: str,
        role: str,
    ) -> ArtifactRef:
        ...


class ArtifactLoader(Protocol):
    def read_bytes(self, ref: ArtifactRef) -> bytes:
        ...


@dataclass(frozen=True, slots=True)
class OpaqueSlotIdentity:
    slot_id: str
    opaque_capability_id: str
    seed: int
    execution_order: int
    hardware_lane: int


@dataclass(frozen=True, slots=True)
class OpaqueSlotWorkOrder:
    study_id: str
    task_id: str
    benchmark: str
    slot: OpaqueSlotIdentity
    snapshot_ref: ArtifactRef
    private_guidance_ref: ArtifactRef | None
    prefix_visible_sha256: str
    packet_index_sha256: str
    analysis_freeze_sha256: str
    branch_caps: "BranchCaps"


@dataclass(frozen=True, slots=True)
class UnscoredSlotReceipt:
    slot_id: str
    opaque_capability_id: str
    pre_injection_visible_sha256: str
    pre_injection_token_ids_sha256: str
    final_snapshot_ref: ArtifactRef
    counters: ResourceCounters
    call_seeds: tuple[CallSeedReceipt, ...]
    failure_kind: FailureKind
    provider_cost_ref: ArtifactRef
    endpoint_readable: Literal[False]


@dataclass(frozen=True, slots=True)
class AttemptReceipt:
    attempt_index: Literal[0, 1]
    attempt_ref: ArtifactRef
    work_order_sha256s: tuple[str, str, str, str]
    terminal_receipts: tuple[UnscoredSlotReceipt, ...]
    complete: bool
    endpoint_readable: Literal[False]


@dataclass(frozen=True, slots=True)
class FailedSlotReceipt:
    slot_id: str
    opaque_capability_id: str
    failed_attempt_ref: ArtifactRef
    adverse_event_ref: ArtifactRef
    provider_cost_ref: ArtifactRef
    failure_kind: Literal[FailureKind.INFRASTRUCTURE]
    endpoint_readable: Literal[False]


@dataclass(frozen=True, slots=True)
class SlotExecutionReceipt:
    source_receipt_sha256: str
    source_kind: Literal["graded_unscored", "failed_second_attempt"]
    grade_receipt: GradeReceipt | None
    outcome: BranchOutcome


TerminalSlotReceipt = UnscoredSlotReceipt | FailedSlotReceipt


@dataclass(frozen=True, slots=True)
class TaskBlock:
    study_id: str
    task_id: str
    benchmark: str
    stratum: str
    sensitivity_groups: tuple[GroupLabel, ...]
    frozen_created_at: str
    triggered: bool
    prefix_success: int
    slot_outcomes: tuple[
        BranchOutcome,
        BranchOutcome,
        BranchOutcome,
        BranchOutcome,
    ]
    schedule_ref: ArtifactRef
    prefix_index_ref: ArtifactRef
    assignment_ref: ArtifactRef
    packet_index_ref: ArtifactRef
    analysis_freeze_ref: ArtifactRef
    attempts: tuple[AttemptReceipt, ...] | None
    selected_attempt_index: int | None
    terminal_slot_receipts: tuple[
        TerminalSlotReceipt,
        TerminalSlotReceipt,
        TerminalSlotReceipt,
        TerminalSlotReceipt,
    ] | None
    execution_receipts: tuple[
        SlotExecutionReceipt,
        SlotExecutionReceipt,
        SlotExecutionReceipt,
        SlotExecutionReceipt,
    ] | None
    outage_receipt: OutageReceipt | None
    validity_event_refs: tuple[ArtifactRef, ...]
    pipeline_valid: bool
    validity_codes: tuple[str, ...]


def run_prefix(
    schedule: "TaskSchedule",
    *,
    environment: EnvironmentAdapter,
    subject: Subject,
    user_simulator: UserSimulator | None,
    prefix_caps: "PrefixCaps",
    artifact_store: BinaryArtifactStore,
) -> "FrozenPrefixReceipt":
    ...


def seal_prefix_index(
    receipts: Sequence["FrozenPrefixReceipt"],
    *,
    schedule_ref: ArtifactRef,
    expected_task_ids: Collection[str],
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def prepare_opaque_work_orders(
    frozen_prefix: "FrozenPrefixReceipt",
    assignment: "TaskAssignment",
    *,
    packet_pair: PacketPairReceipt,
    packet_index_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    branch_caps: "BranchCaps",
) -> tuple[
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
]:
    ...


def prepare_no_intervention_slots(
    frozen_prefix: "FrozenPrefixReceipt",
    assignment: "TaskAssignment",
) -> tuple[
    OpaqueSlotIdentity,
    OpaqueSlotIdentity,
    OpaqueSlotIdentity,
    OpaqueSlotIdentity,
]:
    ...


def run_opaque_slot(
    work_order: OpaqueSlotWorkOrder,
    *,
    environment_factory: Callable[[], EnvironmentAdapter],
    subject: Subject,
    user_simulator: UserSimulator | None,
    artifact_loader: ArtifactLoader,
) -> UnscoredSlotReceipt:
    ...


def seal_unscored_attempt(
    work_orders: Sequence[OpaqueSlotWorkOrder],
    receipts: Sequence[UnscoredSlotReceipt],
    *,
    attempt_index: Literal[0, 1],
    run_root: Path,
    out: Path,
) -> AttemptReceipt:
    ...


def authorize_full_block_rerun(
    work_orders: Sequence[OpaqueSlotWorkOrder],
    first_attempt: AttemptReceipt,
    outage: OutageReceipt,
    *,
    run_root: Path,
) -> tuple[
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
]:
    ...


def grade_opaque_slot(
    work_order: OpaqueSlotWorkOrder,
    unscored: UnscoredSlotReceipt,
    *,
    environment_factory: Callable[[], EnvironmentAdapter],
    artifact_loader: ArtifactLoader,
) -> SlotExecutionReceipt:
    ...


def finalize_failed_second_attempt(
    work_orders: Sequence[OpaqueSlotWorkOrder],
    *,
    first_attempt: AttemptReceipt,
    failed_second_attempt: AttemptReceipt,
    outage: OutageReceipt,
    adverse_event_ref: ArtifactRef,
    provider_cost_refs: tuple[
        ArtifactRef,
        ArtifactRef,
        ArtifactRef,
        ArtifactRef,
    ],
    run_root: Path,
) -> tuple[
    tuple[
        FailedSlotReceipt,
        FailedSlotReceipt,
        FailedSlotReceipt,
        FailedSlotReceipt,
    ],
    tuple[
        SlotExecutionReceipt,
        SlotExecutionReceipt,
        SlotExecutionReceipt,
        SlotExecutionReceipt,
    ],
]:
    ...


def seal_task_block(
    frozen_prefix: "FrozenPrefixReceipt",
    work_orders: Sequence[OpaqueSlotWorkOrder],
    attempts: Sequence[AttemptReceipt],
    terminal_receipts: Sequence[TerminalSlotReceipt],
    receipts: Sequence[SlotExecutionReceipt],
    *,
    selected_attempt_index: Literal[0, 1],
    outage_receipt: OutageReceipt | None,
    validity_event_refs: Sequence[ArtifactRef],
    assignment_ref: ArtifactRef,
    packet_index_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def seal_no_intervention_block(
    frozen_prefix: "FrozenPrefixReceipt",
    slots: Sequence[OpaqueSlotIdentity],
    *,
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    assignment_ref: ArtifactRef,
    packet_index_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...
```

The controller, not the adapter or subject, owns the loop: ask the subject for
one turn, append it, execute queued tool calls one at a time, and inspect the
returned `ToolBoundary` after every completed result. When
`EnvironmentAdapter.simulator_context` returns a context, the controller calls
the explicit `UserSimulator` with
`derive_call_seed(root_seed, "user_simulator", call_index)`, persists that
receipt, and applies the returned turn through `append_simulator_turn`; an
adapter may never invoke a simulator itself. The primary subject uses the same
controller-owned seed/receipt path with role `primary_subject`. `run_prefix`
stops at the
first registered eligible boundary, snapshots both runtime state and pending
calls, records exact visible-context token IDs, scores a disposable clone, runs
the verifier on another disposable clone, and returns a frozen task receipt
whose raw artifacts are already content-addressed. After every task is present,
`seal_prefix_index` verifies exact roster coverage and writes the single
schema-valid `resampling-prefix-receipt` index.
The orchestrator must finish all `run_prefix` calls before Task 3 materializes
the branch assignment and Task 4 constructs packets.

Only the trusted preparer sees clear `TaskAssignment` and `PacketPairReceipt`.
It resolves each arm to one opaque capability and, when applicable, a generic
opaque packet artifact reference; artifact roles/names must not encode REAL,
SHAM, donor, or lineage. The four serialized `OpaqueSlotWorkOrder` values are
launched in isolated workers. A worker receives exactly one order and its
artifact-read capability—it cannot import/read the clear ledger, packet-pair
receipt, donor map, or another slot.

`run_opaque_slot` creates a fresh environment, restores the snapshot, and
verifies the visible digest and exact tokenized context before the subject can
act. It first executes the restored pending prefix tool calls in their frozen
order. They consume branch tool-call and wall-clock quotas, but no new subject
generation occurs until all finish. Only then can the optional packet become
visible on the first post-trigger model call through
`SubjectContext.private_guidance`.
The preparer/attempt sealer verifies the four post-pending, pre-injection
visible digests and token-ID digests are identical; any mismatch invalidates the
whole block.

Every primary-subject and τ³ user-simulator call receives
`derive_call_seed(root_seed, role, call_index)`: `root_seed` is the scheduled
prefix seed in `run_prefix` and the slot seed in `run_opaque_slot`. The prefix
receipt or worker receipt persists the ordered `CallSeedReceipt` sequence; no
adapter/model may choose its own seed. The two roles and all call indices are
separate streams.

`run_opaque_slot` stops at an unscored terminal snapshot and returns
`endpoint_readable == False`; it never grades. The arm-blind controller seals
each completed slot into an `AttemptReceipt`. A complete attempt embeds exactly
four terminal receipts; an outage-interrupted attempt embeds the exact
zero-to-three receipts completed before interruption and sets `complete ==
False`. Only an `OutageReceipt` that itself embeds that first attempt and whose
provider event, identical four work-order digests, and literal pre-endpoint
flag validate may call `authorize_full_block_rerun`. That function accepts no
`SlotExecutionReceipt` and returns the byte-identical four work orders once.
After a complete chosen attempt is sealed,
`grade_opaque_slot` may produce outcomes. If the second attempt is incomplete,
`finalize_failed_second_attempt` verifies both attempt refs, the original
outage, exact four work-order digests, and endpoint unreadability, then creates
four `FailedSlotReceipt` values and four adverse-zero
`SlotExecutionReceipt` values without invoking a grader. No graded receipt is
accepted by any rerun API.

`seal_task_block` accepts only opaque work orders, the four embedded terminal
receipts, four execution receipts, every attempt in chronological order, the
selected attempt index, an optional embedded outage receipt, validity-event
refs, and scientific parent references. It verifies exact slot/source/attempt
coverage and emits one schema-valid `TaskBlock`. Every superseded or partial
attempt remains embedded, so its completed-slot snapshots, counters, call
seeds, and cost refs remain visible; the outcome-source receipts additionally
expose grade/provider/adverse-event refs to recursive artifact sealing.
For
`TriggerReason.NO_INTERVENTION_OPPORTUNITY`,
`prepare_no_intervention_slots` emits only four opaque identities and
`seal_no_intervention_block` copies `Y_0` to all four outcomes without launching
a worker or reading a packet. The sealed packet index must cover that task with
a typed no-intervention marker rather than a packet pair.

`synthetic.py` supplies a finite-state tool environment, deterministic
snapshot/restore, a whitespace-independent fake tokenizer, and a scripted
subject whose REAL response uses applicable evidence, whose SHAM response sees
only structure, and whose two no-packet outcomes vary by distinct slot seed.

### Step 4: Prove green

```powershell
python -m pytest tests/resampling_null/test_controller.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/types.py src/pneuma_lab/resampling_null/__init__.py src/pneuma_lab/resampling_null/controller.py src/pneuma_lab/resampling_null/synthetic.py tests/resampling_null/test_controller.py
git commit -m "feat(resampling-null): run snapshot-paired blocks"
```

## Task 6: Pre-outcome analysis freeze, blinded projection, and gated unblinding

**Files:**

- Create: `src/pneuma_lab/resampling_null/freeze.py`
- Create: `src/pneuma_lab/resampling_null/blinding.py`
- Create: `tests/resampling_null/test_freeze.py`
- Create: `tests/resampling_null/test_blinding.py`

### Step 1: Write failing freeze and blinding tests

Test:

- analysis freeze binds the exact analysis sources, config, projection schema,
  and already-sealed packet index;
- changing a source byte, config byte, projection-schema byte, or packet-index
  parent makes freeze verification fail;
- freeze refuses an unsealed or schema-invalid packet index;
- a task block cannot be accepted without the analysis-freeze parent;
- projection contains only opaque A/B/C/D capabilities;
- arm names, treatment names, packets, donor IDs, and secret bytes are absent
  from serialized projection;
- projection is constructible in a process that has no ledger, secret, `Arm`,
  or packet capability;
- A/B/C/D follow preregistered slot order, not outcome or execution order;
- projection covers the complete frozen roster and acts as the pre-unblind
  artifact-completeness receipt;
- task order is deterministic;
- a permit with the wrong HMAC, ledger digest, projection digest, or freeze
  digest fails before the clear ledger is parsed;
- current analysis-source mismatch blocks unblinding;
- first successful unblind appends a receipt;
- a second unblind cannot overwrite that receipt; and
- changing one projected outcome breaks its parent digest.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py -q
```

Expected: import failure.

### Step 3: Implement the freeze boundary

```python
@dataclass(frozen=True, slots=True)
class AnalysisFreeze:
    study_id: str
    source_refs: tuple[ArtifactRef, ...]
    config_ref: ArtifactRef
    projection_schema_ref: ArtifactRef
    packet_index_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class CurrentAnalysisInputs:
    source_root: Path
    source_paths: tuple[Path, ...]
    config_path: Path
    projection_schema_path: Path
    packet_index_ref: ArtifactRef


def freeze_analysis(
    source_paths: Sequence[Path],
    source_root: Path,
    config_path: Path,
    projection_schema_path: Path,
    packet_index_ref: ArtifactRef,
    run_root: Path,
    out: Path,
    *,
    study_id: str,
    frozen_created_at: str,
    provenance: Mapping[str, str],
) -> ArtifactRef:
    ...


def verify_analysis_freeze(
    freeze_ref: ArtifactRef,
    current: CurrentAnalysisInputs,
    *,
    run_root: Path,
) -> None:
    ...
```

Resolve every source path under `source_root`, sort by its relative POSIX name,
and copy the exact bytes plus config/projection schema into an immutable,
generically named source-snapshot subtree under `run_root`. The freeze stores
ArtifactRefs to those copies plus the original relative names/digests; it never
points outside the study root. Reject duplicate/escaping paths and an output
nested under the source root. The packet index must already validate as
`resampling_packet_index` with `stage == "sealed"`. Verification checks both
the copied artifacts and the caller's current sources/config/schema/packet ref.
A branch task block must parent this freeze and the same packet index. Hash
ancestry, rather than a wall-clock comparison, establishes this irreversible
chronology:

```text
schedule
-> prefixes and verifier receipts
-> assignment
-> packet build
-> packet audit/final packet index
-> analysis freeze
-> branches
-> blinded projection/completeness
-> unblind and analysis
-> artifact-root seal
```

### Step 4: Implement capability-separated projection and unblinding

```python
@dataclass(frozen=True, slots=True)
class BlindedSlot:
    label: Literal["A", "B", "C", "D"]
    slot_id: str
    outcome: BranchOutcome


@dataclass(frozen=True, slots=True)
class BlindedRow:
    task_id: str
    benchmark: str
    stratum: str
    lineage: str
    sensitivity_groups: tuple[GroupLabel, ...]
    prefix_success: int
    triggered: bool
    slots: tuple[BlindedSlot, BlindedSlot, BlindedSlot, BlindedSlot]
    pipeline_valid: bool
    validity_codes: tuple[str, ...]


def project_blinded(
    block_refs: Sequence[ArtifactRef],
    schedule_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


@dataclass(frozen=True, slots=True)
class UnblindPermit:
    study_id: str
    projection_sha256: str
    assignment_ledger_sha256: str
    analysis_freeze_sha256: str
    expected_task_count: int
    capability_hmac: str


@dataclass(frozen=True, slots=True)
class UnblindReceipt:
    study_id: str
    projection_ref: ArtifactRef
    assignment_ledger_ref: ArtifactRef
    analysis_freeze_ref: ArtifactRef
    expected_task_count: int
    permit_hmac_sha256: str


class PermitVerifier(Protocol):
    def verify(
        self,
        permit: UnblindPermit,
        *,
        projection_ref: ArtifactRef,
        assignment_ledger_ref: ArtifactRef,
        analysis_freeze_ref: ArtifactRef,
    ) -> None:
        ...


def issue_unblind_permit(
    *,
    secret: bytes,
    study_id: str,
    projection_ref: ArtifactRef,
    assignment_ledger_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    expected_task_count: int,
) -> UnblindPermit:
    ...


def unblind_projection(
    projection_ref: ArtifactRef,
    assignment_ledger_ref: ArtifactRef,
    permit: UnblindPermit,
    permit_verifier: PermitVerifier,
    analysis_freeze_ref: ArtifactRef,
    current: CurrentAnalysisInputs,
    *,
    run_root: Path,
    receipt_path: Path,
) -> tuple[tuple["AnalysisRow", ...], ArtifactRef]:
    ...
```

`project_blinded` has no ledger/secret parameter and its module does not import
`Arm` or packet types. It loads only opaque task-block refs plus the prefix
schedule and maps each task's frozen slot order to A/B/C/D. It verifies complete
task coverage and all block parents, then writes the schema-valid projection.
Persist neither plaintext secret nor clear arm map in that projection.

Only an unblinding entry point may load both the projection and clear assignment
ledger. The caller constructs `UnblindPermit` from the secret file and the four
frozen values; the clear secret never enters the permit, argv, stdout, or a
scientific record. A secret-backed `PermitVerifier` independently recomputes
the domain-separated HMAC. Verify that HMAC, projection completeness, current
sources/config/projection schema/sealed packet index against the analysis
freeze, and every parent digest before parsing slot-to-arm mappings.
Write the unblind receipt through the ancestry-bound atomic helper and refuse an
existing target.

### Step 5: Prove green

```powershell
python -m pytest tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py -q
```

Expected: pass.

### Step 6: Commit

```powershell
git add src/pneuma_lab/resampling_null/freeze.py src/pneuma_lab/resampling_null/blinding.py tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py
git commit -m "feat(resampling-null): freeze analysis and enforce blinding"
```

## Task 7: Registered sharp tests, average-effect bounds, and verdicts

**Files:**

- Modify: `src/pneuma_lab/resampling_null/types.py`
- Modify: `src/pneuma_lab/resampling_null/__init__.py`
- Create: `src/pneuma_lab/resampling_null/analysis.py`
- Create: `tests/resampling_null/test_analysis.py`

### Step 1: Write failing hand-calculation tests

Separate tests for:

- equal benchmark weighting versus naive row pooling;
- `content`, `excess`, `sham_packet`, `continuation`, `total`, and `null`
  contrasts;
- exact R/S swap tail for a two-task sharp-content fixture;
- exact one-of-three REAL reassignment tail for a sharp-excess fixture;
- dynamic-program exact mode and integer-scaled Fisher tail comparisons;
- add-one Monte Carlo p-value and recorded Monte Carlo SE;
- global 12-way allocation max-T Fisher p-value, labeled sharp-null only;
- multiplier covariance, critical value, and simultaneous lower bounds against a
  hand-computed small matrix;
- zero/non-finite SE blocks a positive claim;
- maximum pairwise equal-benchmark-weighted infrastructure-failure-rate gap is
  executable at `<= 0.02`;
- the frozen secondary family is exactly sham-packet, continuation, and total,
  with three-way max-t lower bounds and Holm-adjusted one-sided multiplier
  p-values;
- the conservative multiplier quantile uses the frozen no-interpolation order
  statistic;
- `q0` and exact equal-roster binomial `r95`;
- unequal-roster weighted-convolution `r95`;
- point screen is `>= 0.05` and resolution screen is `> r95`;
- benchmark-specific sensitivities use task units;
- every registered sensitivity group (language, domain, or issue family)
  renormalizes within its benchmark and applies the executable `>= -0.05` rule;
- analysis loads the roster through a digest-valid `ArtifactRef`, rejects
  missing/extra tasks or changed benchmark/group membership, and never accepts
  a free claimed roster digest;
- row and vectorized sufficient-statistics kernels produce identical gates on
  the same binary fixture;
- one fixture for every verdict; and
- `FEASIBILITY_NO_GO` cannot be returned by outcome classification;
- `PIPELINE_INVALID`, harm, causal, sham-only, unresolved, and
  resampling-consistent follow the frozen precedence below.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_analysis.py -q
```

Expected: import failure.

### Step 3: Implement the frozen API

```python
@dataclass(frozen=True, slots=True)
class AnalysisRow:
    task_id: str
    benchmark: str
    stratum: str
    lineage: str
    sensitivity_groups: tuple[GroupLabel, ...]
    triggered: bool
    prefix: int
    real: int
    sham: int
    none: int
    resample: int
    real_infrastructure_failure: bool
    sham_infrastructure_failure: bool
    none_infrastructure_failure: bool
    resample_infrastructure_failure: bool
    pipeline_valid: bool
    invalid_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RandomizationResult:
    statistic: float
    p_value: float
    mode: Literal[
        "enumerated_exact",
        "dynamic_program_exact",
        "add_one_monte_carlo",
    ]
    support_size: int | None
    draws: int | None
    monte_carlo_se: float | None


@dataclass(frozen=True, slots=True)
class ContrastResult:
    estimate: float
    standard_error: float
    simultaneous_lower: float
    simultaneous_upper: float
    randomization: RandomizationResult | None


@dataclass(frozen=True, slots=True)
class SimultaneousBounds:
    family_name: Literal["co_primary", "secondary_three"]
    contrast_names: tuple[str, ...]
    estimates: tuple[float, ...]
    standard_errors: tuple[float, ...]
    lowers: tuple[float, ...]
    uppers: tuple[float, ...]
    critical_value: float
    method: Literal["task_cluster_rademacher_max_t"]
    draws: int
    seed: int
    quantile_order_1_based: int


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    q0: float
    r95: float
    discordant_task_count: int
    mode: Literal[
        "equal_roster_exact_binomial",
        "unequal_roster_exact_weighted_convolution",
    ]


@dataclass(frozen=True, slots=True)
class BenchmarkEstimate:
    benchmark: str
    content: float
    excess: float


@dataclass(frozen=True, slots=True)
class LeaveOneEstimate:
    benchmark: str
    group_kind: GroupKind
    group_value: str
    content: float
    excess: float


@dataclass(frozen=True, slots=True)
class SecondaryFamilyResult:
    contrast_names: tuple[
        Literal["sham_packet"],
        Literal["continuation"],
        Literal["total"],
    ]
    raw_one_sided_p: tuple[float, float, float]
    holm_adjusted_p: tuple[float, float, float]
    bounds: SimultaneousBounds


@dataclass(frozen=True, slots=True)
class BinarySufficientStatistics:
    roster_ref: ArtifactRef
    benchmark_group_pattern_counts: tuple[
        tuple[str, tuple[GroupLabel, ...], tuple[int, ...]],
        ...,
    ]
    arm_failure_counts: tuple[tuple[str, tuple[int, int, int, int]], ...]
    pipeline_invalid_count: int


@dataclass(frozen=True, slots=True)
class BinarySufficientStatisticsBatch:
    roster_ref: ArtifactRef
    group_manifest: tuple[tuple[str, GroupLabel | None], ...]
    pattern_counts: npt.NDArray[np.int64]
    arm_failure_counts: npt.NDArray[np.int64]
    pipeline_invalid_counts: npt.NDArray[np.int64]


@dataclass(frozen=True, slots=True)
class GateBatchResult:
    causal_pass: npt.NDArray[np.bool_]
    content_estimate: npt.NDArray[np.float64]
    excess_estimate: npt.NDArray[np.float64]
    content_sharp_p: npt.NDArray[np.float64]
    excess_sharp_p: npt.NDArray[np.float64]
    primary_lowers: npt.NDArray[np.float64]
    r95: npt.NDArray[np.float64]
    differential_failure_gap: npt.NDArray[np.float64]
    all_benchmark_nonnegative: npt.NDArray[np.bool_]
    all_leave_one_nonnegative: npt.NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class GateResult:
    code: str
    passed: bool
    observed: float | bool | str | None
    comparator: str
    threshold: float | bool | str | None


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    content: ContrastResult
    excess: ContrastResult
    sham_packet: ContrastResult
    continuation: float
    total: float
    null: float
    omnibus_sharp: RandomizationResult
    primary_bounds: SimultaneousBounds
    secondary_family: SecondaryFamilyResult
    resolution: ResolutionResult
    differential_failure_gap: float
    benchmark_estimates: tuple[BenchmarkEstimate, ...]
    leave_one_out: tuple[LeaveOneEstimate, ...]
    gates: tuple[GateResult, ...]
    verdict: Verdict
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    alpha: float = 0.05
    delta_star: float = 0.05
    sharp_draws: int = 999_999
    multiplier_draws: int = 99_999
    max_differential_failure_gap: float = 0.02


def task_contrasts(row: "AnalysisRow") -> dict[str, float]:
    no_feedback = (row.none + row.resample) / 2.0
    return {
        "content": row.real - row.sham,
        "excess": row.real - no_feedback,
        "sham_packet": row.sham - no_feedback,
        "continuation": no_feedback - row.prefix,
        "total": row.real - row.prefix,
        "null": row.resample - row.none,
    }


def sharp_content_pvalue(
    rows: Sequence["AnalysisRow"],
    *,
    draws: int,
    seed: int,
) -> "RandomizationResult":
    ...


def sharp_excess_pvalue(
    rows: Sequence["AnalysisRow"],
    *,
    draws: int,
    seed: int,
) -> "RandomizationResult":
    ...


def omnibus_sharp_pvalue(
    rows: Sequence["AnalysisRow"],
    *,
    draws: int,
    seed: int,
) -> "RandomizationResult":
    ...


def conservative_multiplier_quantile(
    draws: Sequence[float],
    *,
    alpha: float,
) -> tuple[float, int]:
    ...


def multiplier_lower_bounds(
    rows: Sequence["AnalysisRow"],
    *,
    contrast_names: tuple[str, ...],
    family_name: Literal["co_primary", "secondary_three"],
    draws: int,
    seed: int,
) -> "SimultaneousBounds":
    ...


def resampling_resolution(
    rows: Sequence["AnalysisRow"],
) -> "ResolutionResult":
    ...


def rows_to_binary_sufficient_statistics(
    rows: Sequence[AnalysisRow],
    *,
    roster_ref: ArtifactRef,
) -> BinarySufficientStatistics:
    ...


def evaluate_binary_gate_kernel(
    statistics: BinarySufficientStatistics,
    config: AnalysisConfig,
    *,
    critical_value: float,
) -> tuple[GateResult, ...]:
    ...


def evaluate_binary_gate_batch(
    statistics: "BinarySufficientStatisticsBatch",
    config: AnalysisConfig,
    *,
    critical_values: npt.NDArray[np.float64],
) -> "GateBatchResult":
    ...


def analyze(
    rows: Sequence["AnalysisRow"],
    config: AnalysisConfig,
    *,
    seed: int,
    roster_ref: ArtifactRef,
    run_root: Path,
) -> "AnalysisResult":
    ...
```

Use `numpy.random.Generator(numpy.random.Philox(seed))` with domain-separated
seeds. Enumerate small exact supports; otherwise sample the actual conditional
assignment mechanism. For average bounds, implement the design's
benchmark-stratified task-cluster Rademacher multiplier formula exactly. Label
those bounds `average_effect_asymptotic`, never `exact`.

Before computing statistics, `analyze` loads and verifies `roster_ref` inside
`run_root`, then requires exact row coverage and exact benchmark plus
sensitivity-group membership for every task. `rows_to_binary_sufficient_statistics`
receives that verified ref; no caller-supplied digest or row-only pseudo-roster
is accepted. Primary fields are exact binary integers; booleans/floats are
rejected.
For each arm `a`, define its equal-benchmark-weighted infrastructure-failure
rate as:

```text
f_a = 1/2 * [mean_i failure_SWE,i,a + mean_i failure_TAU,i,a]
failure_gap = max_(a,a') |f_a - f_a'|
```

The differential-failure gate passes iff `failure_gap <= 0.02`. Individual
model/infrastructure failures remain adverse zeros in ITT; a gap above the
threshold makes the pipeline invalid.

The sharp-content Fisher test conditions on which two slots received REAL and
SHAM and enumerates/swaps those two labels. The sharp-excess test conditions on
the SHAM slot and chooses REAL uniformly among the other three slots. The
omnibus sharp null uses the full 12-way studentized max-T allocation. Call a
result `enumerated_exact` only when its full conditional support is enumerated;
otherwise use exactly 999,999 draws and the add-one p-value
`(1 + exceedances) / (1 + draws)`. The weak-average two-contrast bound uses
99,999 task-cluster Rademacher draws and is explicitly asymptotic/
Neyman-conservative.

Dynamic programming over the complete conditional support is
`dynamic_program_exact`, not Monte Carlo. Fisher statistics are compared as
integer numerators after multiplying by
`lcm(2*n_b for every benchmark b)`; floating-point tail comparisons are
forbidden. The omnibus `RandomizationResult` is always persisted.

The registered secondary family is exactly
`(sham_packet, continuation, total)`. Reuse the same 99,999 task-cluster
Rademacher draws to compute marginal one-sided add-one multiplier p-values,
Holm-adjust those three p-values, and construct a separate three-contrast
single-step max-t 95% lower-bound family. `L_sham` is the sham component of that
simultaneous bound; Holm applies to its p-value, not to the bound.

For either multiplier family, sort all `B` max statistics and take the
1-based order
`min(B, ceil((B + 1) * (1 - alpha)))`, with no interpolation. Persist that
index and critical value.

For equal benchmark roster size and `m` NONE/Z-discordant tasks, compute:

```text
r95 = quantile_0.95(|2K - m| / (2n)), K ~ Binomial(m, 1/2)
```

Use integer dynamic programming for unequal task weights. The executable
positive gate is exactly:

```python
causal = (
    content.randomization.p_value <= 0.05
    and excess.randomization.p_value <= 0.05
    and content.simultaneous_lower > 0.0
    and excess.simultaneous_lower > 0.0
    and content.estimate >= 0.05
    and excess.estimate >= 0.05
    and content.estimate > r95
    and excess.estimate > r95
    and all_benchmark_content_and_excess >= 0.0
    and all_leave_one_out_registered_groups >= -0.05
    and differential_failure_gap <= 0.02
)
```

`BinarySufficientStatistics` uses the canonical 16-pattern order over
`(R,S,N,Z)` bits. It carries an overall count per benchmark plus a count for
every registered group membership; overlapping τ³ domain/issue-family labels
are intentional. `rows_to_binary_sufficient_statistics` and
`evaluate_binary_gate_kernel` are the sole implementation of point,
sharp-test, covariance, resolution, benchmark, leave-one-group, and
differential-failure gates. `analyze()` calls them. Task 8 calls the same
vectorized batch kernel over read-only NumPy arrays; it may not duplicate gate
formulas or instantiate millions of row objects. Tests require scalar/batch
bit-for-bit agreement.

`classify_verdict` is exhaustive and applies this precedence:

1. `PIPELINE_INVALID` if any registered packet, snapshot, assignment,
   no-interference, grader, or differential-failure gate fails.
2. `HARMFUL_OR_MISDIRECTING` if either co-primary estimate is `<= -0.05`
   and its finite simultaneous upper bound is `< 0`.
3. `CAUSAL_CONTENT` if the exact positive gate above passes.
4. `SHAM_PACKET_ONLY` if causal fails, sham packet is `>= 0.05` and `> r95`,
   its three-family Holm-adjusted one-sided p-value is `<= 0.05`, its
   three-family simultaneous `L_sham` is `> 0`, and content fails at least one
   registered content gate: finite SE, sharp p, lower bound, materiality,
   `r95`, benchmark non-negativity, or any leave-one-group sensitivity.
5. `UNRESOLVED_RESAMPLING` if no earlier outcome verdict applies and either
   primary standard error is non-finite/non-positive, either co-primary point
   estimate is `< 0.05`, or either co-primary estimate is `<= r95`.
6. `RESAMPLING_CONSISTENT` for the valid, finite, materially resolved remainder
   that does not clear the registered causal controls.

`FEASIBILITY_NO_GO` belongs only to pre-outcome roster/power/runtime
evaluation. The outcome classifier has no branch that can emit it.

Record NumPy version, seeds, draw counts, enumeration/sample mode, Monte Carlo
error, weights, and every gate value.

### Step 4: Prove green

```powershell
python -m pytest tests/resampling_null/test_analysis.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/types.py src/pneuma_lab/resampling_null/__init__.py src/pneuma_lab/resampling_null/analysis.py tests/resampling_null/test_analysis.py
git commit -m "feat(resampling-null): implement registered inference"
```

## Task 8: Frozen-grid P0 power and type-I simulator

**Files:**

- Create: `src/pneuma_lab/resampling_null/power.py`
- Create: `tests/resampling_null/test_power.py`
- Create: `fixtures/resampling_null/p0-power-grid.json`
- Create: `fixtures/resampling_null/p0-roster-synthetic.json`

### Step 1: Write failing simulator tests

Test:

- nuisance grid is exactly
  `p0={.10,.40,.70}`, `gamma={.60,.75,.90}`,
  `rho={0,.40,.80}`;
- cross-benchmark alternative has 729 ordered cells;
- the three null families have 2,187 ordered cells;
- all generated probabilities stay in `[.10,.95]`;
- four-variate pattern probabilities are non-negative, sum to one, and recover
  requested marginals within frozen tolerance; `rho` remains the latent
  Gaussian correlation and is never mislabeled as Bernoulli correlation;
- no-trigger patterns are `(B,B,B,B)` and remain in the denominator;
- triggered alternative has expected ITT effects `(0.15, 0.15)`;
- boundary A has both nulls, B has content null, C has excess null;
- exactly `gamma * n_b` tasks are triggered;
- triggered counts use `Multinomial(gamma * n_b, pi_trigger)`;
- no-trigger `1111` count uses
  `Binomial((1-gamma) * n_b, p0)`, with the remainder `0000`;
- identical configuration/seed yields byte-identical counts;
- scalar analysis and batched P0 invoke the same sufficient-statistics gate
  kernel from `analysis.py`, conditional on nonstatistical admissibility;
- a roster manifest fixes each task's joint sensitivity-group membership,
  exact C120/C160 tier membership, and group counts;
- trigger allocation is a uniform exact-size subset of each benchmark roster
  and preserves joint-cell counts for leave-one-group gates;
- a synthetic roster report is labeled conditional/non-decisive and cannot
  select a confirmation tier;
- the Gaussian-max critical value is monotone and matches a known independent
  case;
- Gaussian-max handles correlation `-1` and `+1` analytically;
- the 96-point Gauss-Hermite, 128-point Gauss-Legendre, Gaussian-root, and
  Clopper-Pearson numeric receipts match frozen fixtures;
- separate one-sided Clopper-Pearson lower/upper tails are `0.05/729` and
  `0.05/2187`, never split in half;
- screen projection rejects a full run above 12 hours;
- shard/resume output is byte-identical to an unsharded tiny run;
- failed screens remain immutable while later generations use distinct
  authority/phase/generation identities, and a full-multiplier fallback has a
  separate phase;
- validation-cell selection freezes exactly the five lowest unrounded
  alternative pass rates with deterministic tie-breaking;
- C160 power is no lower than C120 on a fixed easy cell; and
- a tiny test grid writes raw counts, intervals, numeric receipts, and verdict.
- every screen/shard/selection/validation/final output validates as a staged
  `resampling_power_report`; and
- the one final report parents every failed/passing attempt and uses exactly
  one closed finalization arm; exhausted Gaussian-screen retries and exhausted
  full-multiplier-fallback screening both emit `feasibility_no_go` with no
  fabricated shard/selection/validation refs; and
- a successful all-cell full-multiplier fallback validates complete
  cells/counts/numeric/tier receipts, finalizes without a Gaussian selection,
  and survives artifact sealing.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_power.py -q
```

Expected: import failure.

### Step 3: Implement deterministic Bernoulli-pattern probabilities

Use the equicorrelated one-factor representation:

```text
X_a = sqrt(rho) * F + sqrt(1-rho) * epsilon_a
Y_a = 1[X_a <= NormalDist().inv_cdf(p_a)]
```

For `rho == 0`, use the product Bernoulli table. Otherwise integrate over `F`
with exactly 96-point Gauss-Hermite nodes/weights and emit a
normalization/marginal error receipt. Reject a cell if the probability sum or
any recovered marginal differs by more than `1e-10`; never clip a negative
probability silently. `rho` is the latent-normal equicorrelation.

Expose:

```python
GAUSS_HERMITE_ORDER = 96
GAUSS_LEGENDRE_ORDER = 128
PROBABILITY_TOLERANCE = 1e-10
GAUSSIAN_ROOT_TOLERANCE = 1e-10
GAUSSIAN_ROOT_MAX_ITERATIONS = 200
CLOPPER_PEARSON_TOLERANCE = 1e-12
CLOPPER_PEARSON_MAX_ITERATIONS = 200


@dataclass(frozen=True, slots=True)
class Nuisance:
    p0: float
    trigger_rate: float
    rho: float


PowerPhase = Literal[
    "gaussian_approximation",
    "full_multiplier_fallback",
]


@dataclass(frozen=True, slots=True)
class PowerConfig:
    roster_ref: ArtifactRef
    decision_authority: Literal[
        "synthetic_validation",
        "roster_bound_selection",
    ]
    benchmark_tiers: tuple[int, int] = (120, 160)
    datasets_per_cell: int = 20_000
    screen_datasets_per_cell: int = 200
    max_projected_wall_seconds: int = 43_200
    validation_cell_count: int = 5
    validation_datasets_per_cell: int = 2_000
    multiplier_draws: int = 99_999
    target_effect: float = 0.15
    target_power: float = 0.80
    familywise_alpha: float = 0.05


@dataclass(frozen=True, slots=True)
class PatternProbabilityReceipt:
    probabilities: tuple[float, ...]
    probability_sum_error: float
    marginal_errors: tuple[float, float, float, float]
    latent_rho: float
    quadrature_order: int


def bernoulli_pattern_probabilities(
    marginals: tuple[float, float, float, float],
    rho: float,
) -> PatternProbabilityReceipt:
    ...


def bivariate_normal_cdf_equal_threshold(
    threshold: float,
    rho: float,
) -> float:
    ...


def gaussian_max_critical(correlation: float, alpha: float) -> float:
    ...


def clopper_pearson_lower(
    successes: int,
    trials: int,
    *,
    tail_probability: float,
) -> float:
    ...


def clopper_pearson_upper(
    successes: int,
    trials: int,
    *,
    tail_probability: float,
) -> float:
    ...


def simulate_power_grid(
    config: "PowerConfig",
    *,
    seed: int,
    phase: PowerPhase,
    generation: int,
    mode: Literal["screen", "production", "full_multiplier"],
    shard_index: int,
    shard_count: int,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def select_validation_cells(
    screen_ref: ArtifactRef,
    shard_refs: Sequence[ArtifactRef],
    *,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def validate_gaussian_approximation(
    shard_refs: Sequence[ArtifactRef],
    frozen_selection_ref: ArtifactRef,
    config: PowerConfig,
    *,
    seed: int,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def validate_full_multiplier_fallback(
    screen_ref: ArtifactRef,
    shard_refs: Sequence[ArtifactRef],
    fallback_trigger_ref: ArtifactRef,
    config: PowerConfig,
    *,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


@dataclass(frozen=True, slots=True)
class GaussianApproximationCompletedChain:
    kind: Literal["completed_chain"]
    selected_phase: Literal["gaussian_approximation"]
    selected_generation: int
    selected_screen_ref: ArtifactRef
    selected_shard_refs: tuple[ArtifactRef, ...]
    selected_selection_ref: ArtifactRef
    selected_validation_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class FullMultiplierCompletedChain:
    kind: Literal["completed_chain"]
    selected_phase: Literal["full_multiplier_fallback"]
    selected_generation: int
    fallback_trigger_ref: ArtifactRef
    selected_screen_ref: ArtifactRef
    selected_shard_refs: tuple[ArtifactRef, ...]
    full_grid_validation_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class FeasibilityNoGoFinalization:
    kind: Literal["feasibility_no_go"]
    terminal_attempt_ref: ArtifactRef
    terminal_stage: Literal["screen", "shard", "selection", "validation"]
    reason: Literal[
        "gaussian_screen_exhausted",
        "full_multiplier_screen_exhausted",
        "numeric_fixture_failed",
        "runtime_bound_exceeded",
        "attempt_incomplete",
    ]


PowerFinalization = (
    GaussianApproximationCompletedChain
    | FullMultiplierCompletedChain
    | FeasibilityNoGoFinalization
)


def finalize_power_report(
    all_attempt_refs: Sequence[ArtifactRef],
    *,
    finalization: PowerFinalization,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...
```

Use `numpy.random.Philox` and deterministic cell/replicate counter mapping.
Implement exact-binomial interval inversion with a bounded bisection over the
binomial tail; do not add SciPy merely for beta quantiles. Compute
`Phi_2(c,c;rho)` through Plackett's correlation integral with exactly 128-point
Gauss-Legendre quadrature. Solve its Gaussian-max root by bisection with
tolerance `1e-10` and at most 200 iterations. Invert Clopper-Pearson tails by
bisection with tolerance `1e-12` and at most 200 iterations. The lower and upper
functions each receive the full registered one-sided tail probability; never
halve it. For Gaussian-max correlation `+1`, return
`NormalDist().inv_cdf(1-alpha)` analytically; for `-1`, return
`NormalDist().inv_cdf(1-alpha/2)`. Reject correlations outside `[-1,1]` except
for a `1e-12` numerical-boundary tolerance. Every report binds
these constants, NumPy version, ordered cell manifest, source/config digests,
and numeric-fixture digest.

The roster ref is immutable and gives every task's benchmark, tier membership,
and joint set of language/domain/issue-family labels. The production grid
evaluates `n_b in {120, 160}` and 20,000 datasets per cell. For each benchmark,
set `m_b = gamma * n_b` exactly and choose a uniform size-`m_b` subset of its
frozen roster through deterministic multivariate-hypergeometric counts over the
joint group cells. Within each joint cell, draw triggered 16-pattern counts
from `Multinomial(m_cell, pi_trigger)`. For its nontrigger tasks draw
`U_cell ~ Binomial(n_cell - m_cell, p0)`, assign `U_cell` to `1111`, and assign
the remainder to `0000`. Aggregate those same joint-cell counts for benchmark
and every overlapping leave-one-group gate.

The committed synthetic roster validates machinery and performance only and
sets `decision_authority == "synthetic_validation"`. Its final report must say
`CONDITIONAL_ONLY`; it cannot select C120/C160 or emit the study's feasibility
no-go. After the actual eligible registry freezes exact C120/C160 membership and
all group labels, rerun the complete grid with
`decision_authority == "roster_bound_selection"` before any confirmation
outcome. Only that report may select a tier or emit `FEASIBILITY_NO_GO`.

Before production, `mode="screen"` runs exactly 200 datasets for every one of
the 729 alternative and 2,187 null cells on the declared CPU topology. It must
reproduce the committed numeric fixture digest and project the complete
20,000-dataset grid at `<= 43,200` seconds. A failed screen permits
vectorization/partitioning and another sealed screen under the same authority
and phase with `generation += 1`; it never overwrites the failed generation or
permits a smaller grid. If the bound still fails, finalize
`FEASIBILITY_NO_GO`.

Production calls `evaluate_binary_gate_batch` from `analysis.py` over
read-only sufficient-statistics arrays; it does not create per-dataset row
objects or rerun a 99,999-draw loop per replicate. Exact content sign tails and
excess conditional-DP tails are precomputed/looked up from the observed binary
sufficient counts. Gaussian-max critical values are vectorized. The full
multiplier routine is used only in the frozen validation/fallback path.

Production partitions only by the immutable ordered cell ID. Each shard records
its closed cell-ID set plus config/code/numeric digests. Resume accepts a shard
only when all digests and raw replicate counts match; merge rejects gaps,
overlap, or duplicates. A sharded and unsharded tiny fixture must have the same
canonical report bytes.

Every persisted phase is a schema-valid `resampling_power_report`: `screen`,
`shard`, `selection`, `validation`, or `final`. Each later stage parents the
earlier ArtifactRefs and rejects the wrong stage. The envelope records
decision authority, `phase`, and nonnegative `generation`; shards additionally
record a unique zero-based shard index. A full-multiplier fallback uses phase
`full_multiplier_fallback`, never a disguised extra Gaussian generation. The
single final record parents every immutable attempt, including failures. Its
closed `completed_chain` arm names the selected passing phase/generation and
phase-appropriate downstream refs. A Gaussian chain requires the frozen
worst-five selection and approximation validation. A full-multiplier chain
requires the failed-Gaussian trigger plus
`validate_full_multiplier_fallback`, which verifies full ordered-cell coverage,
raw counts, numeric receipts, and the tier decision directly and has no
Gaussian selection. Its `feasibility_no_go` arm instead names the terminal
failed attempt/stage and frozen reason and forbids downstream refs that do not
exist.

For P0 only, use the two-dimensional Gaussian-max critical value derived from
the estimated contrast correlation. Select the five lowest-power alternative
cells before validation and rerun 2,000 outer datasets through the full
99,999-draw multiplier routine. Freeze and write that selection before
validation outputs. Every selected cell must have an absolute gate-pass-rate
difference at most 0.01 and both methods must choose the same roster tier. On
failure, run the full multiplier routine for every cell or emit
`FEASIBILITY_NO_GO`.

For the roster-bound run, the tier passes only if every Bonferroni
Clopper-Pearson lower bound across 729
alternative cells is at least 0.80 and every upper bound across 2,187 null cells
is at most 0.05. Choose C160 when it passes; otherwise choose C120 only when it
passes; otherwise emit `FEASIBILITY_NO_GO`. Validation freezes the five cell IDs
with the lowest unrounded C160 alternative gate-pass rate, breaking ties by the
ordered manifest. On those cells, 2,000 datasets use the full registered
99,999-draw multiplier routine. Every absolute gate-pass-rate difference must
be `<= 0.01`, and replacing those five approximate rates with their full-
multiplier rates must leave the roster-tier decision unchanged. Otherwise,
screen the all-cell full-multiplier fallback against the same 12-hour bound and
either run it for every alternative/null cell or emit `FEASIBILITY_NO_GO`.

### Step 4: Prove the unit suite green

```powershell
python -m pytest tests/resampling_null/test_power.py -q
```

Expected: pass using a tiny fixture grid; the 20,000 × full-grid run is not a
unit test.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/power.py tests/resampling_null/test_power.py fixtures/resampling_null/p0-power-grid.json fixtures/resampling_null/p0-roster-synthetic.json
git commit -m "feat(resampling-null): add joint P0 simulator"
```

## Task 9: CLI and deterministic synthetic P0

**Files:**

- Create: `src/pneuma_lab/resampling_null/cli.py`
- Create: `src/pneuma_lab/resampling_null/__main__.py`
- Create: `tests/resampling_null/test_cli.py`
- Create: `fixtures/resampling_null/p0-study.json`
- Create: `fixtures/resampling_null/p0-tasks.jsonl`
- Create: `fixtures/resampling_null/p0-local-topology.json`
- Create: `fixtures/resampling_null/p0-required-kinds.json`

### Step 1: Write failing CLI tests

Call `main(argv)` directly and test:

- `selftest`;
- `selftest --defer-artifact-root`, which creates no receipt and is accepted
  only when a later explicit seal is possible;
- `selftest --defer-power --defer-artifact-root`, which omits the complete
  power chain so exactly one later canonical power report can be added;
- `study seal`;
- `schedule seal`;
- `synthetic prefixes`;
- `assignment seal`;
- `packets build`;
- `packets audit`;
- `analysis freeze`;
- `synthetic branches`;
- `project`;
- `analyze`;
- `power screen`, `simulate`, `select-validation`, `validate`,
  `validate-fallback`, and `finalize`;
- `artifacts seal` and `artifacts verify`;
- refusal to overwrite any sealed artifact;
- artifact sealing enforces the per-kind identities above: singleton study
  records, candidate/sealed packet stages, roster-unique task blocks,
  append-only unique power-attempt identities, and exactly one final report
  parenting every attempt;
- every scientific command requires one global study root and rejects an output
  or scientific input outside it;
- JSON stdout contains status, digest, and output path;
- no command accepts an arm name where an opaque capability is required; and
- two self-tests produce identical scientific artifacts.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_cli.py -q
```

Expected: import failure.

### Step 3: Implement the exact command surface

```text
python -m pneuma_lab.resampling_null --run-root <dir> selftest [--defer-artifact-root] [--defer-power]
python -m pneuma_lab.resampling_null --run-root <dir> study seal --study-source <json> --tasks-source <jsonl> --roster-source <json> --assignment-program-source <path> --provider-lane-plan-source <json> --tokenizer-source <json> --packet-template-source <text> --packet-policy-source <json> --pad-unit-set-source <json> --revision-source <path> [--revision-source <path> ...] --required-kinds-source <json> --out study-manifest.json
python -m pneuma_lab.resampling_null --run-root <dir> schedule seal --study study-manifest.json --assignment-program <relative-file> --provider-lane-plan <relative-json> --out prefix-schedule.json
python -m pneuma_lab.resampling_null --run-root <dir> synthetic prefixes --study study-manifest.json --schedule prefix-schedule.json --out prefix-index.json
python -m pneuma_lab.resampling_null --run-root <dir> assignment seal --schedule prefix-schedule.json --prefix-index prefix-index.json --secret-file <path> --out assignment-ledger.json
python -m pneuma_lab.resampling_null --run-root <dir> packets build --study study-manifest.json --assignment assignment-ledger.json --prefix-index prefix-index.json --out-candidate packet-candidate.json
python -m pneuma_lab.resampling_null --run-root <dir> packets audit --study study-manifest.json --candidate packet-candidate.json --schedule prefix-schedule.json --assignment assignment-ledger.json --prefix-index prefix-index.json --out-index packet-index.json
python -m pneuma_lab.resampling_null --run-root <dir> analysis freeze --source-root <path> --source <relative-path> --config <path> --projection-schema <path> --packet-index packet-index.json --out analysis-freeze.json
python -m pneuma_lab.resampling_null --run-root <dir> synthetic branches --study study-manifest.json --schedule prefix-schedule.json --assignment assignment-ledger.json --prefix-index prefix-index.json --packet-index packet-index.json --analysis-freeze analysis-freeze.json --out-prefix task-blocks
python -m pneuma_lab.resampling_null --run-root <dir> project --schedule prefix-schedule.json --analysis-freeze analysis-freeze.json --task-block-prefix task-blocks --out blinded-projection.json
python -m pneuma_lab.resampling_null --run-root <dir> analyze --study study-manifest.json --projection blinded-projection.json --assignment assignment-ledger.json --analysis-freeze analysis-freeze.json --source-root <path> --source <relative-path> --config <path> --projection-schema <path> --packet-index packet-index.json --secret-file <path> --unblind-receipt unblind-receipt.json --out analysis.json
python -m pneuma_lab.resampling_null --run-root <dir> power screen --grid <path> --roster <relative-json> --decision-authority <synthetic_validation|roster_bound_selection> --phase <gaussian_approximation|full_multiplier_fallback> --generation <int> --topology <path> --out power-screen.json
python -m pneuma_lab.resampling_null --run-root <dir> power simulate --grid <path> --roster <relative-json> --screen power-screen.json --mode <production|full_multiplier> --shard-index <int> --shard-count <int> --out <relative-json>
python -m pneuma_lab.resampling_null --run-root <dir> power select-validation --screen power-screen.json --shard-prefix <relative-prefix> --out validation-selection.json
python -m pneuma_lab.resampling_null --run-root <dir> power validate --grid <path> --roster <relative-json> --shard-prefix <relative-prefix> --selection validation-selection.json --out validation.json
python -m pneuma_lab.resampling_null --run-root <dir> power validate-fallback --grid <path> --roster <relative-json> --screen power-screen.json --shard-prefix <relative-prefix> --fallback-trigger <relative-json> --out fallback-validation.json
python -m pneuma_lab.resampling_null --run-root <dir> power finalize --attempt-prefix <relative-directory> --completed-gaussian --selected-screen power-screen.json --selected-shard-prefix <relative-prefix> --selected-selection validation-selection.json --selected-validation validation.json --out p0-power-report.json
python -m pneuma_lab.resampling_null --run-root <dir> power finalize --attempt-prefix <relative-directory> --completed-full-multiplier --fallback-trigger <relative-json> --selected-screen power-screen.json --selected-shard-prefix <relative-prefix> --fallback-validation fallback-validation.json --out p0-power-report.json
python -m pneuma_lab.resampling_null --run-root <dir> power finalize --attempt-prefix <relative-directory> --feasibility-no-go --terminal-attempt <relative-json> --terminal-stage <screen|shard|selection|validation> --reason <closed-reason> --out p0-power-report.json
python -m pneuma_lab.resampling_null --run-root <dir> artifacts seal --required-kinds <path> --out p0-core-receipt.json
python -m pneuma_lab.resampling_null --run-root <dir> artifacts verify --receipt p0-core-receipt.json --required-kinds <path>
```

`--run-root` is required once before every subcommand. Every scientific input
and output argument is a normalized root-relative POSIX name; external inputs
are explicitly named `*-source`, `--source-root`/`--source`, `--config`,
`--projection-schema`, `--grid`, `--topology`, or `--required-kinds` and are
copied/content-addressed into the root before use. `study seal` creates the
first schema-valid manifest and copies the task/roster inputs plus the exact
tokenizer receipt, packet template, packet policy, and pad-unit set used by all
packet commands. `packets build` and `packets audit` load those four refs only
through the validated study manifest and reject any candidate that names
different metadata.

`--source` is repeatable and relative to `--source-root`; the command sorts its
values before hashing. Both `analysis freeze` and `analyze` receive the same
current source/config/schema/sealed-packet inputs. `packets build` writes a
schema-valid candidate-stage index and referenced packet artifacts;
only `packets audit` may create a sealed-stage packet index. `synthetic
branches` refuses absent, schema-invalid, or digest-mismatched packet-index and
analysis-freeze parents. `project` has no assignment or secret option.
`analyze` verifies the current frozen sources, loads the roster ref only through
the validated study manifest, verifies that the assignment schedule descends
from that manifest, and requires exact row/task/group coverage. It then creates
an in-memory HMAC permit, unblinds only in memory, atomically writes the unblind
receipt and analysis, and refuses either existing target.

`power simulate` accepts only a passing, digest-matched screen receipt. Shard
indexing is zero-based and the output records its exact closed cell set.
`select-validation` refuses incomplete production coverage and freezes its
output before `validate` runs. `finalize` always returns one schema-valid power
report whose mutually exclusive CLI argument groups construct either
`GaussianApproximationCompletedChain`, `FullMultiplierCompletedChain`, or
`FeasibilityNoGoFinalization`; every arm parents every attempt. Synthetic
authority ends `CONDITIONAL_ONLY`; roster-bound authority selects a tier,
executes the registered full-multiplier fallback, or records
`FEASIBILITY_NO_GO`. It cannot silently weaken the grid.

`selftest` executes the complete chronology with separate sealed artifacts,
runs 24 task blocks across two fake benchmarks, seals, reloads, and verifies
`p0-core-receipt.json`, and ends with:

- `CAUSAL_CONTENT`;
- zero invalid blocks;
- exact packet parity;
- four distinct slot seeds per block;
- exact snapshot restoration; and
- a stable, verified artifact-root digest with every required document kind.

With `--defer-artifact-root` alone, it performs the same upstream work but
deliberately omits only the final seal/verify. `--defer-power` is accepted only
together with `--defer-artifact-root`; it omits the entire power
screen/shard/selection/validation/final chain while still creating every other
required singleton scientific record. This is the canonical-bootstrap mode:
the explicit Task-10 power commands then create the root's only authoritative
power chain before one immutable artifact seal. Both modes refuse a root that
already contains a receipt.

Secrets are read from a file, never an argument or stdout. CLI failures return
non-zero and one JSON error object without traceback unless `--debug` is
explicit.

### Step 4: Prove green

```powershell
python -m pytest tests/resampling_null/test_cli.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/cli.py src/pneuma_lab/resampling_null/__main__.py tests/resampling_null/test_cli.py fixtures/resampling_null/p0-study.json fixtures/resampling_null/p0-tasks.jsonl fixtures/resampling_null/p0-local-topology.json fixtures/resampling_null/p0-required-kinds.json
git commit -m "feat(resampling-null): expose deterministic P0 CLI"
```

## Task 10: Full local verification and plan receipt

**Files:**

- Modify: `docs/project-status.json`
- Modify: `docs/research/neurips-2026-workshop/15-decision-log.md`
- Modify: `docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md`
- Create under ignored build root:
  `build/research/neurips-2026-workshop/p0-canonical/power/p0-power-report.json`
- Create under ignored build root:
  `build/research/neurips-2026-workshop/p0-canonical/p0-core-receipt.json`

### Step 1: Run focused verification

```powershell
python -m pytest tests/resampling_null -q
python -m pytest tests/test_schema_loads.py tests/test_validate.py -q
```

Expected: all pass.

### Step 2: Build one isolated result-of-record root

Keep determinism probes outside the canonical root. Start the one canonical
root without sealing it yet:

```powershell
$canonicalRoot = 'build/research/neurips-2026-workshop/p0-canonical'
python -m pneuma_lab.resampling_null --run-root $canonicalRoot selftest --defer-power --defer-artifact-root
```

The combined defer mode is permitted only for this orchestrated finalization
path; it creates every non-power upstream schema-valid record and exits nonzero
on any failed non-power gate. It creates no power-stage record. No artifact may
be added after the eventual root seal.

### Step 3: Run the conditional synthetic P0 screen and complete grid

Use a fixed local topology receipt and a deterministic shard count chosen before
the screen. The example below uses 16 shards; changing it requires a new screen
receipt, not a reinterpretation of partial results.

```powershell
$powerRoot = 'power'
python -m pneuma_lab.resampling_null --run-root $canonicalRoot power screen --grid fixtures/resampling_null/p0-power-grid.json --roster inputs/p0-roster-synthetic.json --decision-authority synthetic_validation --phase gaussian_approximation --generation 0 --topology fixtures/resampling_null/p0-local-topology.json --out "$powerRoot/screen.json"
0..15 | ForEach-Object {
    python -m pneuma_lab.resampling_null --run-root $canonicalRoot power simulate --grid fixtures/resampling_null/p0-power-grid.json --roster inputs/p0-roster-synthetic.json --screen "$powerRoot/screen.json" --mode production --shard-index $_ --shard-count 16 --out "$powerRoot/shard-$_.json"
    if ($LASTEXITCODE -ne 0) { throw "power shard $_ failed" }
}
python -m pneuma_lab.resampling_null --run-root $canonicalRoot power select-validation --screen "$powerRoot/screen.json" --shard-prefix "$powerRoot/shard-" --out "$powerRoot/validation-selection.json"
python -m pneuma_lab.resampling_null --run-root $canonicalRoot power validate --grid fixtures/resampling_null/p0-power-grid.json --roster inputs/p0-roster-synthetic.json --shard-prefix "$powerRoot/shard-" --selection "$powerRoot/validation-selection.json" --out "$powerRoot/validation.json"
python -m pneuma_lab.resampling_null --run-root $canonicalRoot power finalize --attempt-prefix "$powerRoot/" --completed-gaussian --selected-screen "$powerRoot/screen.json" --selected-shard-prefix "$powerRoot/shard-" --selected-selection "$powerRoot/validation-selection.json" --selected-validation "$powerRoot/validation.json" --out "$powerRoot/p0-power-report.json"
```

Expected: the screen reproduces numeric fixtures and projects `<= 12` hours;
all 20,000 datasets for every alternative/null cell and both tiers are present;
the five-cell multiplier validation is complete; and the final schema-valid
report states `CONDITIONAL_ONLY`. Resume only digest-matched completed shards.
It validates code/runtime but cannot start confirmation or select a tier. The
same full command sequence reruns later with the actual frozen roster and
`roster_bound_selection`.

### Step 4: Run deterministic end-to-end verification twice outside the root

```powershell
$scratchA = 'build/research/neurips-2026-workshop-scratch/p0-core-a'
$scratchB = 'build/research/neurips-2026-workshop-scratch/p0-core-b'
python -m pneuma_lab.resampling_null --run-root $scratchA selftest
python -m pneuma_lab.resampling_null --run-root $scratchB selftest
$hashA = (Get-FileHash -LiteralPath "$scratchA/p0-core-receipt.json" -Algorithm SHA256).Hash
$hashB = (Get-FileHash -LiteralPath "$scratchB/p0-core-receipt.json" -Algorithm SHA256).Hash
if ($hashA -ne $hashB) { throw 'P0 determinism failure' }
python -m pneuma_lab.resampling_null --run-root $scratchA artifacts verify --receipt p0-core-receipt.json --required-kinds fixtures/resampling_null/p0-required-kinds.json
python -m pneuma_lab.resampling_null --run-root $scratchB artifacts verify --receipt p0-core-receipt.json --required-kinds fixtures/resampling_null/p0-required-kinds.json
```

Expected: identical receipt bytes; both reload and verify every listed byte and
required document kind.

The scratch roots are never nested beneath or copied into the canonical root.

### Step 5: Update canonical status and seal the plan receipt

Update `docs/project-status.json` to state only what is now true:

- the benchmark-independent resampling-null core is implemented and locally
  verified;
- the full synthetic P0 report path and `CONDITIONAL_ONLY` status;
- benchmark adapters, model execution, and confirmation remain unrun;
- cloud credits remain unverified and spend remains zero; and
- no training or provider action is authorized.

Then seal and immediately reload the canonical receipt:

```powershell
python -m pneuma_lab.resampling_null --run-root $canonicalRoot artifacts seal --required-kinds fixtures/resampling_null/p0-required-kinds.json --out p0-core-receipt.json
python -m pneuma_lab.resampling_null --run-root $canonicalRoot artifacts verify --receipt p0-core-receipt.json --required-kinds fixtures/resampling_null/p0-required-kinds.json
```

Expected: the receipt exists at the promised path, excludes itself from its
entry set, covers the power report and every required synthetic document kind,
and its `root_sha256` recomputes exactly.

The canonical root contains exactly one result-of-record study, exactly one
conditional power chain and authoritative final report, and no nested artifact
root or duplicate singleton scientific record kind.

### Step 6: Run repository-wide verification

```powershell
python -m pneuma_lab.status --check
python -m pytest tests/ -q
git diff --check
git status --short
```

Expected: status checker passes, the full default suite has no new failure
relative to the recorded pre-implementation baseline (target: all pass after
reconstructing any reproducible ignored historical receipts), whitespace check
is clean, and only intended branch changes remain. A pre-existing missing
ignored artifact may be recorded as a baseline exception; a regression in
tracked code is a stop.

### Step 7: Record zero spend and implementation decision

Append:

- one decision-log entry naming the implemented hashes, passed tests, known
  limits, conditional-P0 status, canonical receipt digest, and next
  benchmark-adapter gate; and
- one spend-ledger entry with reservation, settled cost, and credit applied all
  `0.00`.

Do not claim benchmark validity, power sufficiency, or cloud readiness from the
synthetic P0.

### Step 8: Commit

```powershell
git add docs/project-status.json docs/research/neurips-2026-workshop/15-decision-log.md docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md
git commit -m "docs(resampling-null): record zero-spend core verification"
```

## Stop conditions

Stop this plan and record a local feasibility no-go if:

- any contract requires importing the retired placebo statistics or EvalPlus
  grader;
- the assignment cannot make the two no-packet treatments exchangeable over
  IID slots;
- REAL/SHAM token parity requires semantic truncation;
- snapshot restoration differs in any arm-visible byte;
- blinded projection leaks treatment identity;
- sharp-null code is reused or labeled as an exact weak-average interval;
- P0 duplicates, instead of calling, production gate logic; or
- the full default repository suite regresses.

This plan authorizes only local, zero-spend implementation. It creates no model
training authorization and no provider action manifest.
