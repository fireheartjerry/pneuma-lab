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
    p0-tasks.json
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

Task 2 is the baseline artifact slice. Task 3 amends these same 0.1.0
schemas/tests in place to the final eligibility, storage-policy, power-final,
selected-membership, assignment-proof, and keyed-audit contract listed below;
the Task-2 commit is green only for its baseline assertions, not those later
Task-3 additions.

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
  `task_id` with exact selected-schedule coverage; and append-only power-attempt
  identities are unique by power-authority ref, phase, generation, stage, and
  shard index while exactly one final report parents every attempt and closes
  as a completed selected chain, a roster-only terminal feasibility no-go, or a
  synthetic-only nondecisive validation failure;
- scientific builders remain byte-identical when the wall clock is monkeypatched;
- study-manifest sealing copies external task/roster, conditionally required
  qualification/ceremony/eligibility, assignment/provider, storage
  contract/evidence,
  power-grid/screen-topology,
  tokenizer/template/policy/pad-set, revision, and required-kind sources under
  the study root, requires three separately named commitment digests, and
  refuses any scientific record before that manifest exists;
- an `eligible_confirmation` manifest requires copied ceremony-policy and final
  eligibility refs with complete nested A–E ancestry; a `synthetic_fixture`
  requires both null and rejects every ceremony source/capability;
- the manifest's required root-independent `storage_policy_contract_ref`
  resolves to a closed contract; eligible confirmation also resolves signed
  measured evidence for the exact provider resource, while synthetic requires
  `local_test` with null evidence;
- the schedule loads assignment/provider assets only through `manifest_ref`,
  requires an existing completed power-final ArtifactRef, derives/stores the
  closed schedule authority, selected tier, and selected-membership digest, and
  schedules exactly that membership;
- failed/no-go power cannot schedule; confirmation requires roster-bound `GO`,
  synthetic requires completed `CONDITIONAL_ONLY`, and power finalization is
  therefore hash-ancestral to every prefix;
- assignment loads the schedule only through `schedule_ref`;
- prefix, assignment, and matching/allocation arrays are non-empty; assignment
  mode is a closed enum and every assignment/matching/allocation array has exact
  selected-schedule coverage;
- semantic ancestry verification reloads every typed parent and rejects a
  schema-valid but unrelated nested record; and
- no packet, analysis freeze, task block, projection, unblind, or analysis
  record can be written before a valid assignment ledger, while task blocks
  additionally require the sealed packet index and analysis freeze; and
- every power stage follows a closed power-authority blob, derives rather than
  trusts its authority/roster/tier fields, and rechecks the same exact grid and
  screen-topology ArtifactRefs, grid-derived RNG-contract digest,
  stage/phase-derived kernel, and screen-frozen shard count; and
- a persisted validation-stage power record is completed and can never be the
  target of `attempt_incomplete`; and
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
| `resampling_study_manifest` | `task_registry_ref`, `roster_ref`, required conditional `eligibility_manifest_ref` and `roster_ceremony_policy_ref` (ArtifactRefs for `eligible_confirmation`, null for `synthetic_fixture`), `assignment_program_ref`, `provider_lane_plan_ref`, required `storage_policy_contract_ref`, `power_grid_ref`, `power_screen_topology_ref`, `tokenizer_ref`, `packet_template_ref`, `packet_policy_ref`, `pad_unit_set_ref`, `source_revision_refs`, `commitment_scheme`, `roster_local_nonce_commitment_sha256`, `schedule_seed_commitment_sha256`, `assignment_master_key_commitment_sha256`, `required_document_kinds_ref` |
| `resampling_prefix_schedule` | `manifest_ref`, completed `power_final_ref`, closed `schedule_authority`, derived `selected_tier`, recomputable `selected_membership_sha256`, `schedule_seed`, `tasks` |
| `resampling_prefix_receipt` | `schedule_ref`, non-empty `task_receipts` |
| `resampling_assignment_ledger` | `manifest_ref`, `schedule_ref`, `prefix_index_ref`, `matching_program_ref`, `assignment_master_key_commitment_sha256`, `assignment_prefix_view_sha256`, closed `assignment_mode`, `matching_proof_refs`, non-empty `assignments`, `allocation_receipts`, `donor_match_receipts` |
| `resampling_packet_index` | `stage`; candidate: `assignment_ref`, `prefix_index_ref`, `tokenizer_ref`, `packet_template_ref`, `packet_policy_ref`, `pad_unit_set_ref`, `entries`; sealed: `candidate_ref`, the same six parent refs, `audit_gates` |
| `resampling_task_block` | every field of `TaskBlock`, with exactly four opaque `slot_outcomes` |
| `resampling_blinded_projection` | `schedule_ref`, `analysis_freeze_ref`, `task_block_refs`, recomputable `projection_candidate_sha256`, `rows`, `expected_task_count`, `complete` |
| `resampling_analysis_freeze` | `source_refs`, `config_ref`, `projection_schema_ref`, `packet_index_ref` |
| `resampling_analysis` | `analysis_freeze_ref`, `projection_ref`, `unblind_receipt_ref`, `config_ref`, `row_count`, `result`, `numeric_receipt` |
| `resampling_power_report` | `stage`, `authority_ref`, derived `decision_authority`, `phase`, `generation`, derived `roster_ref`, derived `tier_membership_sha256`, exact `grid_ref`, exact `screen_topology_ref`, grid-derived `rng_contract_sha256`, derived `kernel_id`, screen-frozen `shard_count`, and `parent_refs`; stage-specific numeric/topology/cell/count/interval/decision payload; `validation` is phase-discriminated and definitionally completed; final stores the selected/terminal kernel/count, additionally requires `all_attempt_refs`, and has a closed `finalization` `oneOf` (Gaussian completed chain, full-multiplier completed chain, roster-only `feasibility_no_go`, or synthetic-only `synthetic_validation_failed`) |
| `resampling_unblind_receipt` | every field of `UnblindReceipt` |
| `resampling_artifact_root` | `code_sha256`, `design_sha256`, `entries`, `root_sha256`, `required_document_kinds` |

`commitment_scheme` is the constant
`resampling-null-key-ceremony-v1`; the former generic
`seed_commitment_sha256` is forbidden. Schedule tasks, prefix task receipts,
ledger assignments, allocation receipts, donor-match receipts, and donor
candidate rows all have `minItems: 1`. Assignment mode is exactly
`synthetic_derangement` or `confirmation_lineage_matching`, and each
mode/algorithm pair is closed. `matching_proof_refs` is unique and empty iff
every donor receipt is the no-trigger N/A arm; otherwise semantic validation
requires exactly one ref per triggered matching stratum and every matched
receipt points to one of them. Array order and uniqueness constraints mirror the
frozen dataclasses. A schema cannot replace an ArtifactRef with a naked digest.
`task_assignment` is also a closed `oneOf`: `donor_match_kind == "matched"`
requires non-null distinct donor ID/lineage, while
`not_applicable_no_trigger` requires both donor fields null.

The study-manifest schema uses the referenced roster's closed `roster_kind` as
a semantic discriminator: `eligible_confirmation` requires a non-null
eligibility ArtifactRef and `synthetic_fixture` requires an explicit null.
Study sealing, not a later power command, is the only transaction that can copy
an eligibility source. The prefix-schedule schema likewise has closed
synthetic/roster-bound arms. Both require a completed final power ref;
roster-bound requires `GO` plus tier 120/160, while synthetic requires
`CONDITIONAL_ONLY` plus null tier. Their task sets and
`selected_membership_sha256` are recomputed from manifest-owned bytes and the
final report, never accepted from the caller.

The blinded-projection schema's row outcome is the closed `BlindedOutcome`
primitive: binary success/prefix-success, finite partial reward,
infrastructure-failure boolean, and four exact nonnegative resource counters.
It has `additionalProperties: false` and contains no ArtifactRef, path, opaque
source receipt, packet/grade ref, arm, donor, or key. Its
`projection_candidate_sha256` is a lowercase digest that semantic validation
must reproduce from the schedule and stripped authoritative task-block values;
the digest alone never replaces those typed parents. Every slot outcome's
`prefix_success` must equal the row-level prefix value reconstructed from the
same task block.

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
artifact-root walker. Schema validation is only the first layer:
`validate_record_ancestry` reloads every ArtifactRef that names a scientific
record, requires its exact record kind and digest, and verifies nested
manifest/schedule/prefix/assignment/packet/freeze/task coverage. A
schema-valid record from another chain cannot satisfy a parent field. The
analysis schema requires freeze/projection digests, counts,
estimands, Fisher p-values, simultaneous bounds, `q0`, `r95`, gates, verdict,
and ancestry.

The packet-index schema is a discriminated `oneOf`: a `candidate` document
contains complete pair receipts and encrypted/synthetic packet references; a
`sealed` document additionally contains all audit gates and parents the
candidate digest. Branch execution accepts only `stage == "sealed"`. The
power-report schema similarly discriminates `screen`, `shard`, `selection`,
`validation`, and `final`; no persisted simulator phase is an unvalidated ad
hoc JSON file. Its shared `authority_ref` selects a strict canonical
`application/vnd.pneuma.power-authority+json` two-arm blob. The
`synthetic_validation` arm contains only manifest/fixture-roster authority;
the `roster_bound_selection` arm additionally contains a base-eligibility
manifest ref that must byte-equal the study manifest's pre-sealed ref and
exactly binds its roster and nested tier/group membership. The synthetic
manifest field is null. The blob is recursively validated and followed but is
not a new scientific record kind. Every stage reloads it, recomputes the
displayed authority/roster/membership mirrors, and requires the same grid,
screen-topology, RNG-contract digest, derived kernel, and screen-frozen shard
count as its parents. A caller-selected string, seed, mode, kernel, post-screen
count, or naked digest has no authority. The screen arm is itself
phase-discriminated: Gaussian forbids `fallback_trigger_ref`; fallback requires
that ref to the latest same-authority completed failed Gaussian validation and
includes it in `parent_refs`. The final schema's reason/stage `oneOf` makes
`attempt_incomplete` incompatible with `terminal_stage = "validation"`; semantic
validation additionally rejects any such finalization that points to a
persisted validation record.

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


def validate_record_ancestry(
    value: Mapping[str, object],
    *,
    run_root: Path,
) -> None:
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
    qualification_receipt_sources: Sequence[Path],
    qualification_evidence_sources: Sequence[Path],
    qualification_universe_source: Path | None,
    roster_selection_program_source: Path | None,
    roster_precommit_source: Path | None,
    roster_anchor_source: Path | None,
    roster_reveal_source: Path | None,
    eligibility_manifest_source: Path | None,
    roster_ceremony_policy_source: Path | None,
    assignment_program_source: Path,
    provider_lane_plan_source: Path,
    storage_policy_contract_source: Path,
    storage_measurement_evidence_source: Path | None,
    power_grid_source: Path,
    power_screen_topology_source: Path,
    tokenizer_source: Path,
    packet_template_source: Path,
    packet_policy_source: Path,
    pad_unit_set_source: Path,
    source_revision_sources: Sequence[Path],
    required_document_kinds_source: Path,
    *,
    roster_ceremony_capability: "ConfirmationRosterCeremonyCapability | None",
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
before calling the existing atomic writer. It also calls
`validate_record_ancestry`, which reloads typed parents under the run root,
verifies nested selected-schedule coverage, and enforces:

```text
manifest -> power authority -> screen -> shards
-> phase-appropriate selection/validation -> completed power final
-> selected-membership schedule -> prefix receipt -> assignment
-> packet candidate -> packet sealed -> analysis freeze
-> task blocks -> ephemeral capability-minimal projection candidate
-> trusted ancestry-validated projection seal -> unblind -> analysis
-> artifact root
```

No packet or later branch-derived record exists without assignment; a task
block additionally requires the sealed packet index and analysis freeze. Power
reports form the typed pre-outcome prefix of that chain and never consume
endpoint bytes. A schedule cannot be written unless its referenced authority-
appropriate final is a completed chain.
Both write helpers resolve `path`
inside `run_root`, refuse any existing destination, and return the actual
root-relative digest/size/media-type/role reference. JSONL rows are materialized
once, checked for finite values, and canonically encoded before the atomic
publish. `seal_study_manifest` validates the external study template, requires
`resampling-null-key-ceremony-v1` plus the three separately labeled commitment
digests, copies
and references the exact task registry, roster/group manifest, conditional
qualification receipts/evidence and ceremony assets/policy, final eligibility,
revision receipts, assignment program, provider-lane plan, storage-policy
contract plus conditional measurement evidence, tokenizer receipt, packet
template, packet policy, neutral pad-unit set,
exact P0 grid, exact declared screen topology, and required-kind manifest under
`run_root`, and writes the first scientific root. For
`eligible_confirmation`, it requires the complete A–E sources, final
eligibility, policy, and consumed nominal ceremony capability; it proves their
external-log/future-beacon chain, resolvable qualification evidence,
pilot/tier/reserve derivation, and roster equality. For `synthetic_fixture`, it
rejects every ceremony source/capability and writes both conditional refs null.
Before copying, it parses the closed Task-3
task/roster/ceremony/eligibility/program/provider/storage grammars, normalizes strict
text and unordered source arrays into their specified canonical orders, and
writes compact canonical bytes; raw source order and formatting have no digest
authority. Assignment-program executable/text sources are rejected.
`storage_policy_contract_source` must use the roster-appropriate closed mode:
root-independent `local_test` with rejected evidence source for synthetic, or
measured `confirmation` whose exact signed evidence source is copied and
digest-matched for eligible confirmation. Revision
sources are non-empty, sorted by
normalized source name, and copied by content digest. It injects the one frozen
timestamp used by all descendants.
`seal_artifact_root` enumerates schema-valid scientific records under
`run_root`, then recursively walks every mapping/list in those records for the
schema's exact `$defs.artifact_ref` shape. It resolves and verifies every
referenced raw blob under the same root, including ciphertext packets,
snapshots, streams, grade output, and source bundles. It rejects dangling refs,
size/digest mismatches, two refs that claim different metadata for one path,
an unreferenced scientific root, and a raw file presented as a scientific
record. It reruns `validate_record_ancestry` for every scientific record and
reconstructs the final-selected schedule membership and exact coverage across
schedule, prefix, assignment, matching/allocation, packet, task, and analysis
descendants.
For a blinded projection it reconstructs the stripped opaque schedule/block
view from validated parents and recomputes `projection_candidate_sha256`. For a
power report it parses the authority blob under its closed media grammar,
rechecks manifest-owned eligibility/roster/tier ancestry, and proves authority,
grid, screen-topology, RNG-contract, derived-kernel, and screen-frozen
shard-count equality across the complete attempt. For a schedule it reloads the
completed power final and recomputes schedule authority, selected tier, selected
membership digest, and exact task set.
Manifest, schedule, prefix-index, assignment, projection, freeze,
analysis, and unblind kinds are singleton. Packet-index identity is
`(record_kind, stage)` and requires exactly one candidate plus one sealed
record. Task-block identity is `(record_kind, task_id)` and requires exactly one
block for every selected-schedule task. A non-final power-attempt identity is
`(power_authority_ref.sha256, phase, generation, stage, shard_index_or_null)`,
where
`phase` is `gaussian_approximation` or `full_multiplier_fallback` and generation
is a nonnegative append-only retry number. Duplicate identities are rejected,
including a same-generation screen that changes shard count; later immutable
generations may declare a new count and are retained. Every descendant derives
that attempt's count, RNG digest, and kernel from its screen. Exactly one final power report
per authority parents every attempted screen/shard/selection/validation record
and has a closed finalization arm: `completed_chain` names its selected
phase/generation and phase-appropriate downstream refs,
roster-only `feasibility_no_go` names the terminal failed attempt/stage and
reason, and synthetic-only `synthetic_validation_failed` records a nondecisive
conditional failure. Neither terminal arm may invent downstream refs. A
completed roster-bound validation with no passing tier uses
`power_or_type_i_gate_failed`; a completed synthetic validation failure uses
`synthetic_validation_gate_failed`. `attempt_incomplete` is valid only when a
required next stage never completed: a persisted validation record is completed
and can never be named or described by that reason. A Gaussian completed chain requires its worst-five
selection and approximation-validation receipt; a full-multiplier completed
chain instead requires its fallback trigger and full-grid
completeness/numeric/tier-validation receipt and forbids a Gaussian selection.
Only an authority-appropriate completed final may parent the singleton
schedule; failed final arms terminate before prefixes.
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

## Task 3: Power-gated schedule and four-slot assignment seals

**Files:**

- Create: `src/pneuma_lab/resampling_null/assignment.py`
- Create: `src/pneuma_lab/resampling_null/preflight.py`
- Create: `src/pneuma_lab/resampling_null/secrets.py`
- Create: `tests/resampling_null/test_assignment.py`
- Create: `tests/resampling_null/test_preflight.py`
- Modify: `src/pneuma_lab/resampling_null/types.py`
- Modify: `tests/resampling_null/test_types.py`
- Modify: `src/pneuma_lab/resampling_null/__init__.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `schemas/resampling-study-manifest.schema.json`
- Modify: `schemas/resampling-prefix-schedule.schema.json`
- Modify: `schemas/resampling-prefix-receipt.schema.json`
- Modify: `schemas/resampling-assignment-ledger.schema.json`
- Modify: `schemas/resampling-power-report.schema.json`
- Modify: `schemas/resampling-artifact-root.schema.json`
- Modify: `src/pneuma_lab/resampling_null/artifacts.py`
- Modify: `tests/resampling_null/test_artifacts.py`
- Modify: `tests/test_schema_loads.py`

### Task 3 execution slicing and review gates

Task 3 is not one implementation batch. Before any production edit, perform a
docs-authority gate: reconcile this plan, the design, the latest handoff, and
the append-only decision log; record the exact reviewed plan/design SHA-256
values. A later review edit invalidates those hashes and requires a refreshed
docs gate before implementation resumes.

Every slice also appends granular receipts to
`docs/research/neurips-2026-workshop/33-execution-journal.md`. That journal is
explicitly non-authoritative: it records execution evidence but cannot change
the handoff, project status, design, this plan, or the decision log. A conflict
stops the slice, records a deviation, and is resolved in the authoritative
document before work resumes.

At minimum, each slice journals:

1. opening authority/HEAD/worktree hashes, actor, intent, local and UTC time,
   exact cwd, inputs, owned files, and next gate;
2. every task command's exact argv, including read-only probes/searches,
   environment/version checks, tests, validators, file/status/hash inspection,
   and Git/remote operations; plus exit code, RED/GREEN role, compact
   stdout/stderr summary, complete stream SHA-256/byte count, and local raw-log
   path; a missed capture is an explicit deviation;
3. every file touched plus before/after content hashes and any dependency,
   lock, binary, interpreter, platform, or source provenance;
4. expected and actual RED, minimal implementation, GREEN, schema/static/full
   verification, deviations, and unresolved anomalies;
5. each reviewer, finding, disposition, repair hash, and rerun evidence; and
6. commit identity, exact push argv/result, remote/ref verification, and the
   next authorized gate.

Routine raw stdout/stderr is captured outside Git under the ignored
`build/research/neurips-2026-workshop/execution-journal/<event-id>/` directory.
Committed journal entries default to compact summaries plus hashes, byte
counts, paths, and retention state; raw routine pytest output is not committed.
Each event directory is an immutable, no-clobber slot. Allocation is serialized
under one atomic parent lock directory: acquire the lock with plain `mkdir`,
parse the last published journal ID and prove the proposed heading absent,
atomically reserve the exact event directory with plain `mkdir`, then release
the allocator lock before the task command begins. Failure to acquire the lock,
a stale lock, an unparsable/noncontiguous last ID, an existing heading/path, or
a failed reservation stops before task execution. `mkdir -p`, truncation or
reuse of an existing event path, silent ID selection, and overwrite are
forbidden. A stale allocator lock or collision is a journaled deviation and
requires explicit review; the wrapper never reuses or truncates a slot.

By default, one task command gets one event, one stdout stream, one stderr
stream, and one exit code. Timestamping, reservation, hashing, byte counting,
and receipt append mechanics do not turn several task commands into one task.
If a genuinely atomic multi-check gate must be aggregated, it is one explicit
script/process that records every component status and returns nonzero when any
component fails. A `set +e` brace block whose final successful command masks an
earlier failure is never authoritative fail-closed evidence.
All captured streams remain locally inspectable at least through
`2026-11-27`—90 days after the submission deadline—and are never
automatically deleted. Debugging, anomaly, and decisive-failure streams also
remain until the deviation is closed, if later. Cleanup requires explicit user
direction plus a journaled hash/path manifest; no earlier availability deadline
is valid unless the user explicitly approves it. Git promotion is explicit,
reviewed, and exceptional, and must record destination/digest/classification/
rationale while excluding secrets/private data.

Delivery uses a finite paired-receipt protocol. Commit **A** is the substantive
slice commit and includes every pre-commit journal receipt; push A. Before it
exists, **B** pre-records the exact planned `git commit` and `git push` argv.
B is journal-only and records A's immutable SHA, exact push result, remote/ref
observation, journal review, and next gate; then execute the pre-recorded B
commit/push mechanics. Those mechanics are exempt from an immediate in-band
result commit. The opening receipt of the next substantive A must record B's
actual SHA, push result, and fresh remote/ref verification before any slice
command runs. Final handoff must name a terminal pending B if there is no next
substantive A. Git content addressing is the evidence boundary; it does not
magically create an external immutable anchor or prove an unobserved remote
state. Commands whose only effect is appending the journal need not recursively
log themselves, but journal content, review, and delivery still follow this
A/B protocol.

Before the slice-1 RED, add the official PyPI stable versions verified on
2026-07-28, `ruff==0.15.22` and `mypy==2.3.0`, as exact pins in the `dev`
extra, then bootstrap with the separately reviewed uv executable and the
reviewed Python 3.12/Linux toolchain:

```console
uv lock --python 3.12
uv lock --check --python 3.12
uv sync --frozen --python 3.12 --extra dev
.venv/bin/python -m ruff --version
.venv/bin/python -m mypy --version
.venv/bin/python -c "from hashlib import sha256; from importlib.metadata import version; from pathlib import Path; import platform, sys; expected = (Path.cwd() / '.venv/bin/python').absolute(); observed = Path(sys.executable).absolute(); assert observed == expected, (observed, expected); assert version('ruff') == '0.15.22'; assert version('mypy') == '2.3.0'; assert sys.version_info[:2] == (3, 12); assert platform.system() == 'Linux'; digest = sha256(expected.read_bytes()).hexdigest(); assert len(digest) == 64; print(f'python_path={observed}\\npython_version={platform.python_version()}\\npython_sha256={digest}')"
```

The bootstrap receipt binds the `pyproject.toml` and `uv.lock` digests; uv and
the exact `.venv/bin/python` invocation path, version, and executable digest;
Linux platform identity; exact command
argv/stdout/stderr/exit codes; selected package artifact names/digests;
installed-distribution evidence; and both version outputs. Ruff and mypy are
invoked only as `.venv/bin/python -m` modules from this frozen project
environment. Every later Task-3 slice opening receipt rechecks the exact
bootstrap-bound interpreter path, version, and digest before its task command.
Ambient/global installations and unpinned `uvx` execution have no authority.
The commands above are shell-neutral; no slice assumes `pwsh` is installed.

Name every new focused test with its slice token `t3_s01` through `t3_s11`.
For each row, run the listed command before implementation and retain its
intended assertion failure, then run the identical command after the minimal
implementation and require it to pass. After every GREEN, run:

```console
.venv/bin/python -m ruff check src/pneuma_lab/resampling_null tests/resampling_null
.venv/bin/python -m mypy --ignore-missing-imports src/pneuma_lab/resampling_null
```

Slices 2, 7, and 11 additionally run the complete schema gate:

```console
.venv/bin/python -m pytest tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q
```

The table is the implementation order and exclusive editing schedule. Shared
hot files such as `assignment.py`, `preflight.py`, `artifacts.py`, and their
tests are edited sequentially, never by concurrent slice workers.
`pyproject.toml` and `uv.lock` are likewise sequential shared ownership: slice
1 pins the development tools and freezes their bootstrap; slice 6 later adds
the independent cryptography runtime pin and regenerates/reverifies the lock.

| slice | owned files for this slice | focused RED/GREEN command | intended small commit |
| --- | --- | --- | --- |
| 1 — types and tool bootstrap | `pyproject.toml`<br>`uv.lock`<br>`src/pneuma_lab/resampling_null/types.py`<br>`src/pneuma_lab/resampling_null/__init__.py`<br>`tests/resampling_null/test_types.py` | `.venv/bin/python -m pytest tests/resampling_null/test_types.py -q -k t3_s01` | `build(resampling-null): pin task 3 tools and types` |
| 2 — schema contracts | `schemas/resampling-study-manifest.schema.json`<br>`schemas/resampling-prefix-schedule.schema.json`<br>`schemas/resampling-prefix-receipt.schema.json`<br>`schemas/resampling-assignment-ledger.schema.json`<br>`schemas/resampling-power-report.schema.json`<br>`schemas/resampling-artifact-root.schema.json`<br>`src/pneuma_lab/resampling_null/artifacts.py`<br>`tests/resampling_null/test_artifacts.py`<br>`tests/test_schema_loads.py` | `.venv/bin/python -m pytest tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q -k t3_s02` | `feat(resampling-null): close task 3 schemas` |
| 3 — derivation core | `src/pneuma_lab/resampling_null/assignment.py`<br>`tests/resampling_null/test_assignment.py` | `.venv/bin/python -m pytest tests/resampling_null/test_assignment.py -q -k t3_s03` | `feat(resampling-null): add framed assignment derivations` |
| 4 — secret store | `src/pneuma_lab/resampling_null/secrets.py`<br>`src/pneuma_lab/resampling_null/assignment.py`<br>`src/pneuma_lab/resampling_null/__init__.py`<br>`tests/resampling_null/test_assignment.py` | `.venv/bin/python -m pytest tests/resampling_null/test_assignment.py -q -k t3_s04` | `feat(resampling-null): add purpose-bound secret store` |
| 5 — deterministic imports | `src/pneuma_lab/resampling_null/preflight.py`<br>`src/pneuma_lab/resampling_null/assignment.py`<br>`tests/resampling_null/test_preflight.py`<br>`tests/resampling_null/test_assignment.py` | `.venv/bin/python -m pytest tests/resampling_null/test_preflight.py tests/resampling_null/test_assignment.py -q -k t3_s05` | `feat(resampling-null): import deterministic assignment authority` |
| 6 — ceremony/signature capability | `src/pneuma_lab/resampling_null/preflight.py`<br>`src/pneuma_lab/resampling_null/assignment.py`<br>`pyproject.toml`<br>`uv.lock`<br>`tests/resampling_null/test_preflight.py`<br>`tests/resampling_null/test_assignment.py` | `.venv/bin/python -m pytest tests/resampling_null/test_preflight.py tests/resampling_null/test_assignment.py -q -k t3_s06` | `feat(resampling-null): validate signed preflight authority` |
| 7 — storage and power-final consumer schedule | `src/pneuma_lab/resampling_null/types.py`<br>`src/pneuma_lab/resampling_null/preflight.py`<br>`src/pneuma_lab/resampling_null/assignment.py`<br>`src/pneuma_lab/resampling_null/artifacts.py`<br>`schemas/resampling-prefix-schedule.schema.json`<br>`schemas/resampling-prefix-receipt.schema.json`<br>`schemas/resampling-power-report.schema.json`<br>`tests/resampling_null/test_preflight.py`<br>`tests/resampling_null/test_assignment.py`<br>`tests/resampling_null/test_artifacts.py` | `.venv/bin/python -m pytest tests/resampling_null/test_preflight.py tests/resampling_null/test_assignment.py tests/resampling_null/test_artifacts.py -q -k t3_s07` | `feat(resampling-null): gate schedules on storage and power` |
| 8 — allocation and prefix view | `src/pneuma_lab/resampling_null/assignment.py`<br>`tests/resampling_null/test_assignment.py` | `.venv/bin/python -m pytest tests/resampling_null/test_assignment.py -q -k t3_s08` | `feat(resampling-null): freeze allocation and prefix views` |
| 9 — synthetic path | `src/pneuma_lab/resampling_null/assignment.py`<br>`src/pneuma_lab/resampling_null/preflight.py`<br>`tests/resampling_null/test_assignment.py`<br>`tests/resampling_null/test_preflight.py` | `.venv/bin/python -m pytest tests/resampling_null/test_assignment.py tests/resampling_null/test_preflight.py -q -k t3_s09` | `feat(resampling-null): seal synthetic assignments` |
| 10 — confirmation path | `src/pneuma_lab/resampling_null/assignment.py`<br>`src/pneuma_lab/resampling_null/preflight.py`<br>`src/pneuma_lab/resampling_null/secrets.py`<br>`tests/resampling_null/test_assignment.py`<br>`tests/resampling_null/test_preflight.py` | `.venv/bin/python -m pytest tests/resampling_null/test_assignment.py tests/resampling_null/test_preflight.py -q -k t3_s10` | `feat(resampling-null): enforce confirmation assignment authority` |
| 11 — reconstruction and closure | `src/pneuma_lab/resampling_null/assignment.py`<br>`src/pneuma_lab/resampling_null/artifacts.py`<br>`src/pneuma_lab/resampling_null/__init__.py`<br>`schemas/resampling-assignment-ledger.schema.json`<br>`schemas/resampling-power-report.schema.json`<br>`schemas/resampling-artifact-root.schema.json`<br>`tests/resampling_null/test_assignment.py`<br>`tests/resampling_null/test_artifacts.py`<br>`tests/test_schema_loads.py` | `.venv/bin/python -m pytest tests/resampling_null/test_assignment.py tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q -k t3_s11` | `feat(resampling-null): close assignment reconstruction ancestry` |

Each slice receives spec and code-quality review before the next row starts; a
review repair repeats that slice's RED/GREEN/static/commit/review gate.
Confirmation remains unavailable in slice 10 unless a separately reviewed
scalable backend adapter has been pinned and implemented; the bounded local
solver is synthetic/test authority only.

Slice 6 adds the base runtime pin `cryptography==49.0.0`, regenerates
`uv.lock` with a separately reviewed uv toolchain for the project's exact
Python 3.12 constraint, and verifies that frozen lock on the target Linux
runtime before committing either file. The lock/installation gate is:

```console
uv lock --python 3.12
uv lock --check --python 3.12
uv sync --frozen --python 3.12 --extra dev
.venv/bin/python -c "from hashlib import sha256; from pathlib import Path; import cryptography, platform, sys; expected = (Path.cwd() / '.venv/bin/python').absolute(); observed = Path(sys.executable).absolute(); assert observed == expected, (observed, expected); assert cryptography.__version__ == '49.0.0'; assert sys.version_info[:2] == (3, 12); assert platform.system() == 'Linux'; digest = sha256(expected.read_bytes()).hexdigest(); assert len(digest) == 64; print(f'python_path={observed}\\npython_version={platform.python_version()}\\npython_sha256={digest}')"
```

The reviewed receipt binds the uv executable version/digest and complete
command output; an ambient unreviewed uv invocation is not authority. Slice
6's GREEN gate includes an actual
`Ed25519PublicKey.verify` path over canonical bytes plus valid, altered-payload,
altered-signature, and wrong-key vectors; parsing a signature-shaped hex string
is not verification. The recorded Windows cp311 abi3 wheel SHA-256
`e5dfc1e64de5677cec922ffa8da89c546d0415bf6efdf081842e5d44c84e1f0e`
is planning provenance only and cannot authorize the Python 3.12/Linux
environment. The reviewed implementation receipt must instead bind the exact
Linux artifacts selected by the regenerated lock and the frozen interpreter,
platform, and installed-distribution evidence.

Task 3 does **not** install or implement the official `drand-client`/Sigstore
Node dependency graph, a pinned Node runtime lock, or the nominal live ceremony
adapter. Those require their own reviewed adapter plan with exact Node/runtime
artifacts, package lock, offline verification KATs, and capability boundary.
Until that adapter is implemented and reviewed,
`ConfirmationPreflightRegistry.claim_roster_ceremony` remains unavailable and
fails closed for eligible confirmation. Synthetic fixtures, mocked signatures,
or test-only ceremony evidence cannot be relabeled, wrapped, or promoted into
an eligible-confirmation capability.

Task 3 owns only the completed-final **consumer** contract. Slices 2 and 11
freeze and close `resampling-power-report.schema.json`; slice 7 implements and
tests `require_schedulable_power_final` against test-only, hand-authored
complete authority chains. Task 3 creates no power attempt/final producer,
simulator, or production fixture. Task 8 remains the sole producer and
simulator of power reports.

### Step 1: Write failing assignment tests

Test:

- the exact frame hex, frame SHA-256, derived seed, schedule commitment, five
  HKDF subkeys, two bounded draws, and capability in design section 4.0 match
  their known-answer vectors;
- framed derivations distinguish the former colon collision
  `("a:b", "c") != ("a", "b:c")`, while both members of the former NUL
  collision `("a\0b", "c")` / `("a", "b\0c")` reject before framing;
- tags/identifiers reject non-NFC text, controls, format controls, private-use/
  unassigned code points, and lone surrogates before encoding;
- task-registry, qualification receipt/evidence/universe, ceremony policy,
  selection/precommit/Sigstore bundle/reveal/eligibility/roster,
  assignment-program,
  provider-lane, storage contract/evidence, build/backend/KAT, and
  verifier-feature imports reject unknown fields, noncanonical text, booleans
  where exact integers are required, and incomplete benchmark component lists;
  only declared semantic-set source arrays reorder to byte-identical copies;
- slice 6 pins `cryptography==49.0.0` in `pyproject.toml`, regenerates and
  verifies `uv.lock` for the reviewed Python 3.12/Linux runtime, and exercises
  actual Ed25519 verification of canonical bytes; a changed payload, signature,
  or public key rejects, and the Windows cp311 wheel hash cannot satisfy the
  Linux runtime receipt;
- no installed Node/drand/Sigstore lock or nominal live adapter exists in this
  core slice, so eligible-confirmation ceremony capability acquisition fails
  closed; synthetic, mock, or test-only evidence cannot be relabeled as live;
- the accepted/rejected qualification rows partition the registry and resolve
  exact task/base/image/gate evidence; naked/missing/alternate receipt bytes,
  post-precommit qualification/quota mutation, local/self timestamp, past or
  invalid beacon round, multiple study precommit, cross-study replay, seed
  grinding, invalid Sigstore/TSA/Rekor evidence, or forged beacon proof fails;
- pilots/tiers/reserves are accepted with exact disjointness/nesting/rank
  relations; roster IDs are exactly the supported-tier union, pilots/reserves
  never schedule, and for each benchmark/tier exactly `t` rows carry tier `t`
  with complete joint-group partitions summing to `t`; a 24-row fixture cannot
  claim C120/C160, and zero supported tiers stops before study seal;
- the assignment program is closed canonical JSON, never executable source, and
  freezes mode/algorithm, sorted cutpoints, verifier normalizer, backend receipt
  arm, CPython version, and `unicodedata.unidata_version`;
- normalizer and backend implementation refs each byte-equal one manifest
  `source_revision_ref`; their recomputed digests match the redundant pinned
  digests, and an unreferenced lookalike implementation fails;
- schedule derivation accepts only roles `prefix`, `slot-0..3`, and
  `execution-order-0..3`; execution order sorts by `(order_digest, ordinal)` on
  digest collision and maps rank exactly to the frozen provider-lane ordinal;
- every `U64` and `uniform_below.upper` check rejects booleans; `uniform_below`
  accepts only exact integers `1..2^64` and terminates at `upper == 2^64`;
- an exhaustive small-word analogue proves equal accepted preimage counts for
  every result, while the production 64-bit limit formula is exact;
- roster-local-nonce, schedule, and assignment-master commitments cannot substitute
  for one another; the wrong value/label/study/length or beacon-derived final
  roster seed fails before a draw;
- assignment master/subkeys never appear in argv values, environment, run-root
  bytes, records, logs, exception text, worker orders, or capability payloads;
- core code independently verifies each scoped secret master and derives only
  four assignment keys or only `K_unblind`; arbitrary provider/lookalike,
  subclassed, wrong-purpose, stale, swapped-file, or reused handles reject;
- roster input order cannot affect bytes or digest;
- `seal_prefix_schedule` has no assignment-program/provider-lane argument,
  loads both only through `manifest_ref`, requires a completed
  `power_final_ref`, and rejects a manifest commitment or referenced asset
  mismatch;
- the Task-3 `require_schedulable_power_final` consumer accepts only
  test-only, hand-authored, schema-valid complete chains for its focused tests;
  reloads the authority/grid/topology, every declared attempt, terminal arm,
  roster/tier membership, selected decision, and parent closure; rejects
  incomplete, orphaned, cross-authority, caller-mirrored, or post-final chains;
  and exposes no power-report producer/simulator API;
- an eligible-confirmation manifest contains the exact copied ceremony-policy
  and final eligibility refs whose nested A–E ancestry resolves; a synthetic
  manifest contains null for both and rejects every ceremony source/capability;
  fabricating/substituting a post-seal ceremony blob cannot create authority;
- roster-bound schedule sealing accepts only a completed `GO` final, derives
  tier 120/160 and exactly that manifest-pinned eligibility subset, and stores
  the final ref, closed authority, selected tier, and selected-membership
  digest;
- synthetic schedule sealing accepts only a completed `CONDITIONAL_ONLY` final
  with null tier and schedules the complete fixture roster; feasibility no-go,
  synthetic failure, incomplete, cross-authority, or unrelated finals reject;
- prefix, assignment, packet, task-block, projection, and analysis coverage is
  exact against selected schedule membership, never the unselected manifest
  superset;
- the manifest owns one root-independent closed storage contract; synthetic
  pins only `local_test`, confirmation pins signed resolvable evidence/resource/
  mount identity, and a naked digest, stale evidence, forged signer, or field
  mismatch rejects;
- prefix and assignment leases begin before seed verification, secret access,
  backend open, blob/raw writes, or destination creation; serialize the lease
  ID, generation, expiry, every ordered renewal, end freshness, a fsynced
  transaction-intent digest, and publication-commit freshness; hold one
  continuous lease through the scientific commit point; remeasure the identical
  resource/version/mount/policy at a confirmation-signed or closed-local-test
  non-releasing end; bind the exact fsynced prepared scientific bytes/path and
  final generation/expiry; publish and fsync the scientific parent before the
  registry atomically records a publication-commit proof, signs it for
  confirmation, consumes the lease, and attempts release;
  then install and fsync the distinct immutable
  `operational/storage-policy/{prefix,assignment}.json` receipt as the durable
  local acceptance marker embedding the exact intent and commit proof; failure
  before registry commit leaves no accepted output, and any quarantined
  owner-only assignment bytes remain inaccessible to untrusted observers and
  can never be promoted;
- local-test observations explicitly claim neither encryption nor ACL and
  cannot satisfy confirmation; lookalike/copied/replayed/second-use leases,
  begin/renewal/end/publication-commit swaps, renewal gaps/reordering, stale end
  or commit proofs, and cross-study/schedule/root replay reject; forced expiry,
  release, or resource/version/mount/policy swap after signed end and before
  scientific install, scientific-parent fsync, or the atomic registry commit
  can never return an accepted transaction; a crash before scientific install
  may discard or replace only a non-authoritative intent under lock, a crash
  after scientific install but before registry commit quarantines permanently,
  and a crash after registry commit may only deterministically finalize the
  proof-bound fixed receipt before acceptance;
- `seal_branch_assignment` has no schedule object or free mode/program argument,
  loads the schedule only through `schedule_ref`, reloads the manifest through
  that schedule, and rejects an incomplete or wrong-parent prefix index;
- prefix schedule contains no donor, packet, arm, key, or outcome field;
- every task gets four distinct seed streams, canonical slot ordinals `0..3`,
  and a separate permutation of execution order `0..3`;
- all 12 frozen table rows reconstruct exactly, and the orientation convention
  maps the lower/higher no-packet ordinals to NONE/RESAMPLE for bit 0 and
  RESAMPLE/NONE for bit 1;
- allocation and orientation use separate keys/messages and persist their
  rejection counters; global capabilities are unique and bind the manifest,
  schedule, and prefix digests;
- the prefix-view builder recomputes normalized counts/classes from the
  referenced verifier bytes, derives count/length bands from manifest-pinned
  cut points, and derives telecom fallback availability from the complete
  candidate graph; caller-supplied band/availability fields are rejected;
- changing `Y_0`, partial reward, resource counters, wall time, provider cost,
  snapshot/verifier/grade refs, finding text, or artifact names while keeping
  the allowlisted view fixed leaves donor candidates/mapping and arm draws
  byte-identical but changes prefix-bound capabilities;
- changing an allowlisted matching feature may change donor matching but never
  the 12-way or orientation draws;
- stratum constructors merge/sort duplicate components into collision-checked
  canonical JSON/digest, encode bands without leading zeros, use constant TAU
  issue-family rule tokens, and execute exact telecom cross-family-first then
  same-family fallback; reorder/collision/duplicate/leading-zero and premature
  same-family edges reject;
- a confirmation fixture returns the unique global constrained minimum, even
  when the first cyclic/greedy derangement is feasible but more expensive;
- candidate coverage, one-to-one permutation, different lineage, no self edge,
  no reciprocal two-cycle, exact stratum constraints, optimum status, objective
  vector, and HMAC-collision fallback to canonical donor ID are recomputed;
- an infeasible candidate graph, non-optimal/time-limited status, changed
  matching program/build/backend, bad KAT, forged runner signature, wrong
  image/argv/env, or incomplete transcript fails closed;
- exact matching problem, solution, confirmation proof, and synthetic proof
  blobs reject unknown fields, non-canonical ordering/JSON, booleans where
  integers are required, non-finite numbers, wrong digests, skipped tie trials,
  and incomplete cyclic-offset trials;
- matching problem, solution, invocation, and proof refs have exactly the
  `blobs/matching/{problem|solution|invocation|proof}/{sha256}.json`
  digest-derived paths; canonical identical CAS objects may preexist, crashes
  may leave unreachable blobs/operational receipt, retry is idempotent, GC
  removes only unreachable blobs, and ledger-last publication never exposes a
  partial graph;
- `synthetic_derangement` pairs only with
  `synthetic_cyclic_offset_v1`; it can never be relabeled as confirmation;
- `confirmation_lineage_matching` pairs only with
  `exact_constrained_min_cost_v1`;
- every triggered task has one matched donor receipt and every no-trigger task
  has only a `not_applicable_no_trigger` receipt with no donor, candidates,
  proof, or packet ref; N/A on a triggered task and donor/packet data on N/A
  both fail;
- assignments, allocation receipts, and donor receipts are non-empty, unique,
  and exactly selected-schedule-covering; matched receipts/permutation exactly cover only
  the triggered subset, while all tasks still receive allocations and
  capabilities;
- unkeyed artifact-root verification never opens a secret handle or backend
  session and checks bytes/refs/signatures, closed nested grammars, ancestry,
  coverage, and key-independent feasibility/objective only;
- triggered confirmation opens one tuple-bound multi-solve backend session with
  exact call order/count and signed invocation refs, then closes it; all-no-
  trigger confirmation and synthetic require `None`, and unexpected solve,
  copied/stale/reused/session-after-close mutations reject;
- `require_assignment_reconstruction` consumes one fresh assignment handle and,
  iff triggered confirmation, one fresh runner session; it rejects mutations to
  donor order/tie trials, mapping, allocation, orientation, capability, mode,
  digest, invocation, kind, coverage, or ancestry;
- `require_confirmation_assignment` wraps that reconstruction and additionally
  requires confirmation mode; `verify_result_bundle` sequences keyed
  reconstruction, both storage-attestation checks, and unkeyed root verification
  without serializing the provider or any key; and
- `write_record` refuses a packet, analysis freeze, task block, projection,
  unblind, or analysis record before the valid assignment parent exists.

### Step 2: Prove red

```console
.venv/bin/python -m pytest tests/resampling_null/test_types.py tests/resampling_null/test_preflight.py tests/resampling_null/test_assignment.py tests/resampling_null/test_artifacts.py -q
```

Expected: missing assignment module and pre-hardening schema/ancestry failures.

### Step 3: Implement the one canonical binary derivation contract

Never use Python's randomized `hash()`, formatted strings, delimiter
concatenation, canonical JSON, or modulo a raw digest directly. Implement
design section 4.0 byte for byte:

```python
@dataclass(frozen=True, slots=True)
class U64Field:
    value: int


@dataclass(frozen=True, slots=True)
class TextField:
    value: str


@dataclass(frozen=True, slots=True)
class BytesField:
    value: bytes


FrameField = U64Field | TextField | BytesField


@dataclass(frozen=True, slots=True)
class UniformDraw:
    value: int
    counter: int


class _AssignmentKeyBuffers:
    """Private mutable application-owned buffers; never returned or serialized."""

    __slots__ = ("donor", "allocation", "orientation", "capability")

    def __init__(self) -> None:
        self.donor = bytearray(32)
        self.allocation = bytearray(32)
        self.orientation = bytearray(32)
        self.capability = bytearray(32)

    def wipe(self) -> None:
        for buffer in (
            self.donor,
            self.allocation,
            self.orientation,
            self.capability,
        ):
            _wipe_bytearray(buffer)


class AssignmentSecretHandle:
    """Opaque registry-held, nominal, single-use assignment-purpose OS handle."""


class UnblindSecretHandle:
    """Opaque registry-held, nominal, single-use unblind-purpose OS handle."""


class AssignmentSecretStore:
    """Concrete trusted-controller keystore; no caller-supplied implementation."""

    def claim_assignment(
        self,
        manifest_ref: ArtifactRef,
        schedule_ref: ArtifactRef,
        *,
        run_root: Path,
    ) -> AssignmentSecretHandle:
        ...

    def claim_unblind(
        self,
        manifest_ref: ArtifactRef,
        schedule_ref: ArtifactRef,
        *,
        run_root: Path,
    ) -> UnblindSecretHandle:
        ...


def kdf_frame(tag: str, fields: Sequence[FrameField]) -> bytes:
    ...


def commitment_sha256(
    label: Literal[
        "roster-local-nonce",
        "schedule-seed",
        "assignment-master-key",
    ],
    study_id: str,
    value: U64Field | BytesField,
) -> str:
    ...


def derive_seed(schedule_seed: int, task_id: str, role: str) -> int:
    return int.from_bytes(
        hashlib.sha256(
            kdf_frame(
                "derive-seed-v1",
                [
                    U64Field(schedule_seed),
                    TextField(task_id),
                    TextField(role),
                ],
            )
        ).digest()[:8],
        "big",
    )


def uniform_below(
    key: bytearray,
    message_frame: bytes,
    upper: int,
) -> UniformDraw:
    if type(upper) is not int or not 1 <= upper <= 2**64:
        raise ValueError("upper must be an integer in [1, 2**64]")
    if type(key) is not bytearray or len(key) != 32:
        raise ValueError("key must be one private mutable 32-byte buffer")
    limit = (1 << 64) - ((1 << 64) % upper)
    for counter in range(1 << 64):
        digest = hmac.new(
            key,
            kdf_frame(
                "uniform-below-v1",
                [BytesField(message_frame), U64Field(counter)],
            ),
            hashlib.sha256,
        ).digest()
        value = int.from_bytes(digest[:8], "big")
        if value < limit:
            return UniformDraw(value=value % upper, counter=counter)
    raise RuntimeError("64-bit rejection counter exhausted")


def _wipe_bytearray(buffer: bytearray) -> None:
    for index in range(len(buffer)):
        buffer[index] = 0


def _read_exact_master_into(
    assignment_secret_handle: AssignmentSecretHandle | UnblindSecretHandle,
    destination: bytearray,
) -> None:
    """Use the handle's unbuffered readinto; reject a short read or any extra byte."""
    ...


def _derive_assignment_subkeys_into(
    assignment_master_key: memoryview,
    study_id: str,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    destination: _AssignmentKeyBuffers,
) -> None:
    ...


def _derive_unblind_subkey_into(
    assignment_master_key: memoryview,
    study_id: str,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    destination: bytearray,
) -> None:
    ...
```

`kdf_frame` uses the exact magic, type tags, unsigned big-endian widths, strict
NFC/Unicode `C*` rejection, and raw-digest decoding rules in the design.
`commitment_sha256` additionally enforces 32 bytes for roster/master keys and
`U64Field` for the schedule seed. HKDF is RFC 5869 SHA-256, with the exact
context and five exact labels in the design. Assignment-purpose code derives
and consumes only donor/allocation/orientation/capability inside the private
transaction scope; unblind-purpose code derives and consumes only `K_unblind`.
There is no public or frozen key wrapper, no key-returning API, and no exception
interpolates input or key bytes.

`AssignmentSecretStore` is one concrete final controller component bootstrapped
from trusted local configuration, not a `Protocol` and not a scientific
argument. It opens the owner-only secret unbuffered with no-follow semantics,
pins the OS file identity in a purpose-bound single-use nominal handle, and
never returns a subkey or commitment verdict. Inside the core transaction,
private code preallocates `bytearray(32)`, passes its memoryview to the
already-open handle's `readinto`, rejects any short read, attempts one further
one-byte `readinto`, and rejects any extra byte. It independently recomputes
the manifest commitment and derives only the purpose-appropriate keys into
private mutable buffers. One outer `finally` wipes every application-owned
master, subkey, one-byte overread, and transient mutable buffer before closing
the handle, whether validation, derivation, drawing, or publication succeeds
or fails. Tests retain private buffer references and assert all-zero contents
after success and after injected exceptions at every stage.

This is an application-buffer minimization guarantee, not a proof of process
memory erasure. Python's `hmac`/`hashlib`, allocator, interpreter, and OpenSSL
may create immutable or internal copies that Python cannot reliably locate or
scrub. The process never intentionally persists, logs, serializes, returns, or
places key material in argv/environment, and production isolation must treat
the trusted controller process boundary accordingly. Exact type, registry
membership, manifest/schedule binding, purpose, file identity, and one-use
state are checked in core; copied, subclassed, wrong-purpose, stale, or
second-use handles fail before a draw or ledger parse. Hostile Python already
executing inside the trusted controller process remains out of scope.

Pin all design known-answer vectors in tests. Also test the arithmetic proof:
for each valid `upper`, `limit` is divisible by `upper`, every residue has
`limit / upper` accepted 64-bit preimages, and `0 <= 2^64 - limit < upper`.
The small-word exhaustive fixture exercises actual rejection paths without
trying to enumerate `2^64` values.

### Step 4: Implement typed views, receipts, and authority-minimal transactions

Use these stable records:

```python
class TriggerReason(str, Enum):
    FIRST_ELIGIBLE_MUTATION = "first_eligible_mutation"
    FOURTH_TOOL_CALL = "fourth_tool_call"
    NO_INTERVENTION_OPPORTUNITY = "no_intervention_opportunity"


class AssignmentMode(str, Enum):
    SYNTHETIC = "synthetic_derangement"
    CONFIRMATION = "confirmation_lineage_matching"


class MatchingAlgorithm(str, Enum):
    SYNTHETIC = "synthetic_cyclic_offset_v1"
    CONFIRMATION = "exact_constrained_min_cost_v1"


@dataclass(frozen=True, slots=True)
class LocalTestStoragePolicyContract:
    record_kind: Literal["storage_policy_contract_v1"]
    schema_version: Literal["1"]
    mode: Literal["local_test"]
    test_only: Literal[True]
    storage_resource_id: None
    measurement_evidence_ref: None
    evidence_verifier_public_key_ed25519_hex: None
    registry_attestation_public_key_ed25519_hex: None
    max_measurement_age_seconds: None
    lease_kind: Literal["local_test_process_lock_v1"]
    encryption_at_rest: Literal[False]
    encryption_algorithm: None
    kms_key_version: None
    acl_enforced: Literal[False]
    acl_policy_sha256: None
    measurement_sha256: None


@dataclass(frozen=True, slots=True)
class ConfirmationStoragePolicyContract:
    record_kind: Literal["storage_policy_contract_v1"]
    schema_version: Literal["1"]
    mode: Literal["confirmation"]
    test_only: Literal[False]
    storage_resource_id: str
    measurement_evidence_ref: ArtifactRef
    evidence_verifier_public_key_ed25519_hex: str
    registry_attestation_public_key_ed25519_hex: str
    max_measurement_age_seconds: int
    lease_kind: Literal["provider_resource_lease_v1"]
    encryption_at_rest: Literal[True]
    encryption_algorithm: str
    kms_key_version: str
    acl_enforced: Literal[True]
    acl_policy_sha256: str
    measurement_sha256: str


StoragePolicyContract = (
    LocalTestStoragePolicyContract | ConfirmationStoragePolicyContract
)


@dataclass(frozen=True, slots=True)
class LocalTestStoragePolicyAttestation:
    record_kind: Literal["storage_policy_attestation_v1"]
    schema_version: Literal["1"]
    authority_ref: ArtifactRef
    transaction: Literal["prefix", "assignment"]
    manifest_sha256: str
    schedule_sha256: str | None
    observation: Literal["begin", "renewal", "end"]
    mode: Literal["local_test"]
    test_only: Literal[True]
    normalized_run_root_sha256: str
    lease_id: str
    lease_generation: int
    lease_expires_at_utc: str
    renewal_sequence: int
    storage_resource_id: None
    measurement_evidence_ref: None
    observed_at_utc: str
    resource_version: None
    mount_identity_sha256: str
    encryption_at_rest: Literal[False]
    encryption_algorithm: None
    kms_key_version: None
    acl_enforced: Literal[False]
    acl_policy_sha256: None
    measurement_sha256: None
    releases_lease: Literal[False]


@dataclass(frozen=True, slots=True)
class ConfirmationStoragePolicyAttestation:
    record_kind: Literal["storage_policy_attestation_v1"]
    schema_version: Literal["1"]
    authority_ref: ArtifactRef
    transaction: Literal["prefix", "assignment"]
    manifest_sha256: str
    schedule_sha256: str | None
    observation: Literal["begin", "renewal", "end"]
    mode: Literal["confirmation"]
    test_only: Literal[False]
    normalized_run_root_sha256: str
    lease_id: str
    lease_generation: int
    lease_expires_at_utc: str
    renewal_sequence: int
    storage_resource_id: str
    measurement_evidence_ref: ArtifactRef
    observed_at_utc: str
    resource_version: str
    mount_identity_sha256: str
    encryption_at_rest: Literal[True]
    encryption_algorithm: str
    kms_key_version: str
    acl_enforced: Literal[True]
    acl_policy_sha256: str
    measurement_sha256: str
    releases_lease: Literal[False]
    attestation_signature_ed25519_hex: str


StoragePolicyAttestation = (
    LocalTestStoragePolicyAttestation | ConfirmationStoragePolicyAttestation
)


@dataclass(frozen=True, slots=True)
class StorageTransactionIntent:
    record_kind: Literal["storage_transaction_intent_v1"]
    schema_version: Literal["1"]
    transaction: Literal["prefix", "assignment"]
    lease_id: str
    begin: StoragePolicyAttestation
    renewals: tuple[StoragePolicyAttestation, ...]
    end: StoragePolicyAttestation
    continuous_lease_held: Literal[True]
    fresh_at_end: Literal[True]
    end_releases_lease: Literal[False]
    prepared_scientific_relative_path: str
    prepared_scientific_sha256: str
    final_lease_generation: int
    final_lease_expires_at_utc: str


@dataclass(frozen=True, slots=True)
class LocalTestStoragePublicationCommit:
    record_kind: Literal["storage_publication_commit_v1"]
    schema_version: Literal["1"]
    authority_ref: ArtifactRef
    transaction: Literal["prefix", "assignment"]
    manifest_sha256: str
    schedule_sha256: str | None
    mode: Literal["local_test"]
    test_only: Literal[True]
    normalized_run_root_sha256: str
    lease_id: str
    lease_generation: int
    lease_expires_at_utc: str
    renewal_sequence: int
    committed_at_utc: str
    transaction_intent_sha256: str
    scientific_relative_path: str
    scientific_sha256: str
    storage_resource_id: None
    measurement_evidence_ref: None
    resource_version: None
    mount_identity_sha256: str
    encryption_at_rest: Literal[False]
    encryption_algorithm: None
    kms_key_version: None
    acl_enforced: Literal[False]
    acl_policy_sha256: None
    measurement_sha256: None
    registry_commit_id: str
    commit_recorded: Literal[True]
    lease_consumed: Literal[True]
    release_required: Literal[True]


@dataclass(frozen=True, slots=True)
class ConfirmationStoragePublicationCommit:
    record_kind: Literal["storage_publication_commit_v1"]
    schema_version: Literal["1"]
    authority_ref: ArtifactRef
    transaction: Literal["prefix", "assignment"]
    manifest_sha256: str
    schedule_sha256: str | None
    mode: Literal["confirmation"]
    test_only: Literal[False]
    normalized_run_root_sha256: str
    lease_id: str
    lease_generation: int
    lease_expires_at_utc: str
    renewal_sequence: int
    committed_at_utc: str
    transaction_intent_sha256: str
    scientific_relative_path: str
    scientific_sha256: str
    storage_resource_id: str
    measurement_evidence_ref: ArtifactRef
    resource_version: str
    mount_identity_sha256: str
    encryption_at_rest: Literal[True]
    encryption_algorithm: str
    kms_key_version: str
    acl_enforced: Literal[True]
    acl_policy_sha256: str
    measurement_sha256: str
    registry_commit_id: str
    commit_recorded: Literal[True]
    lease_consumed: Literal[True]
    release_required: Literal[True]
    attestation_signature_ed25519_hex: str


StoragePublicationCommit = (
    LocalTestStoragePublicationCommit | ConfirmationStoragePublicationCommit
)


@dataclass(frozen=True, slots=True)
class StoragePolicyReceipt:
    record_kind: Literal["storage_policy_receipt_v1"]
    schema_version: Literal["1"]
    transaction: Literal["prefix", "assignment"]
    intent: StorageTransactionIntent
    transaction_intent_sha256: str
    publication_commit: StoragePublicationCommit
    fresh_at_publication_commit: Literal[True]
    publication_commit_recorded: Literal[True]
    publication_commit_consumes_lease: Literal[True]
    fixed_receipt_is_acceptance_marker: Literal[True]


@dataclass(frozen=True, slots=True)
class LocalTestStorageLease:
    """Synthetic-only process lock; core creates and consumes it once."""


class ConfirmationRosterCeremonyCapability:
    """Opaque, nominal, single-use capability; no public constructor/subclass."""

    @property
    def source_sha256s(self) -> tuple[str, str, str, str, str, str, str]:
        ...


class ConfirmationStorageLease:
    """Opaque nominal live provider lease; no public constructor/subclassing."""


StoragePolicyLease = (
    LocalTestStorageLease | ConfirmationStorageLease
)


@dataclass(frozen=True, slots=True)
class ExactMatchingEdge:
    focal_task_id: str
    donor_task_id: str
    primary_cost: tuple[int, int, int]
    tie_hmac_sha256: str


@dataclass(frozen=True, slots=True)
class ExactMatchingConstraints:
    one_outgoing: Literal[True]
    one_incoming: Literal[True]
    forbid_self: Literal[True]
    forbid_same_lineage: Literal[True]
    forbid_two_cycle: Literal[True]


@dataclass(frozen=True, slots=True)
class ExactMatchingProblem:
    record_kind: Literal["exact_matching_problem_v1"]
    assignment_program_sha256: str
    backend_receipt_sha256: str
    assignment_prefix_view_sha256: str
    stratum_key: tuple[str, ...]
    focal_task_ids: tuple[str, ...]
    edges: tuple[ExactMatchingEdge, ...]
    fixed_edges: tuple[tuple[str, str], ...]
    constraints: ExactMatchingConstraints


@dataclass(frozen=True, slots=True)
class ExactMatchingSolution:
    record_kind: Literal["exact_matching_solution_v1"]
    problem_sha256: str
    backend_receipt_sha256: str
    status: Literal["OPTIMAL", "INFEASIBLE"]
    objective: tuple[int, int, int] | None
    donor_by_task: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class MatchingBackendInvocationReceipt:
    record_kind: Literal["exact_matching_invocation_receipt_v1"]
    schema_version: Literal["1"]
    backend_receipt_ref: ArtifactRef
    transaction_nonce_sha256: str
    sequence_index: int
    problem_ref: ArtifactRef
    solution_ref: ArtifactRef
    observed_container_image_digest: str
    observed_command_argv: tuple[str, ...]
    observed_environment: tuple[tuple[str, str], ...]
    observed_runtime_contract_sha256: str
    observed_single_threaded: Literal[True]
    observed_mip_gap_ppm: Literal[0]
    exit_code: Literal[0]
    stdout_sha256: str
    stderr_sha256: str
    runner_signature_ed25519_hex: str


@dataclass(frozen=True, slots=True)
class MatchingInvocationResult:
    solution: ExactMatchingSolution
    receipt: MatchingBackendInvocationReceipt


class ConfirmationMatchingBackendSession:
    """Opaque nominal one-transaction live runner; no public constructor."""

    @property
    def authority_ref(self) -> ArtifactRef:
        ...

    @property
    def backend_receipt_ref(self) -> ArtifactRef:
        ...

    def solve(self, problem: ExactMatchingProblem) -> MatchingInvocationResult:
        ...

    def close(self) -> tuple[MatchingBackendInvocationReceipt, ...]:
        ...


class ConfirmationPreflightRegistry:
    """Trusted controller bootstrap; never accepted as a scientific input."""

    def claim_roster_ceremony(
        self,
        *,
        qualification_universe_source: Path,
        selection_program_source: Path,
        precommit_source: Path,
        anchor_source: Path,
        reveal_source: Path,
        eligibility_source: Path,
        ceremony_policy_source: Path,
        study_id: str,
    ) -> ConfirmationRosterCeremonyCapability:
        ...

    def claim_storage(
        self,
        *,
        transaction: Literal["prefix", "assignment"],
        run_root: Path,
        manifest_ref: ArtifactRef,
        schedule_ref: ArtifactRef | None,
    ) -> ConfirmationStorageLease:
        ...

    def open_matching_backend(
        self,
        *,
        run_root: Path,
        manifest_ref: ArtifactRef,
        schedule_ref: ArtifactRef,
        prefix_index_ref: ArtifactRef,
    ) -> ConfirmationMatchingBackendSession:
        ...


@dataclass(frozen=True, slots=True)
class PrefixSchedule:
    study_id: str
    frozen_created_at: str
    manifest_ref: ArtifactRef
    power_final_ref: ArtifactRef
    schedule_authority: Literal[
        "synthetic_validation",
        "roster_bound_selection",
    ]
    selected_tier: Literal[120, 160] | None
    selected_membership_sha256: str
    schedule_seed: int
    tasks: tuple[TaskSchedule, ...]


@dataclass(frozen=True, slots=True)
class AssignmentPrefixTaskView:
    task_id: str
    benchmark: str
    stratum: str
    lineage: str
    sensitivity_groups: tuple[GroupLabel, ...]
    trigger_reason: TriggerReason
    verifier_component_class: str
    objective_finding_count: int
    normalized_report_token_count: int
    telecom_issue_family: str | None


@dataclass(frozen=True, slots=True)
class AssignmentPrefixView:
    study_id: str
    schedule_sha256: str
    tasks: tuple[AssignmentPrefixTaskView, ...]


@dataclass(frozen=True, slots=True)
class DonorCandidateReceipt:
    donor_task_id: str
    donor_lineage: str
    primary_cost: tuple[int, int, int]
    fallback_code: (
        Literal["cross_family_component_match_unavailable"] | None
    )
    tie_hmac_sha256: str


@dataclass(frozen=True, slots=True)
class MatchedDonorReceipt:
    kind: Literal["matched"]
    task_id: str
    donor_task_id: str
    task_lineage: str
    donor_lineage: str
    assignment_mode: AssignmentMode
    matching_algorithm: MatchingAlgorithm
    stratum_key: tuple[str, ...]
    assignment_prefix_view_sha256: str
    candidates: tuple[DonorCandidateReceipt, ...]
    chosen_primary_cost: tuple[int, int, int]
    matching_proof_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class NoTriggerDonorReceipt:
    kind: Literal["not_applicable_no_trigger"]
    task_id: str
    trigger_reason: Literal[TriggerReason.NO_INTERVENTION_OPPORTUNITY]
    assignment_prefix_view_sha256: str


DonorMatchReceipt = MatchedDonorReceipt | NoTriggerDonorReceipt


@dataclass(frozen=True, slots=True)
class TaskAssignment:
    task_id: str
    task_lineage: str
    donor_match_kind: Literal["matched", "not_applicable_no_trigger"]
    donor_task_id: str | None
    donor_lineage: str | None
    slot_arms: tuple[tuple[str, Arm], ...]
    schedule_sha256: str
    prefix_index_sha256: str


@dataclass(frozen=True, slots=True)
class AllocationReceipt:
    task_id: str
    slot_ids_by_ordinal: tuple[str, str, str, str]
    treatment_allocation_index: int
    allocation_rejection_counter: int
    no_packet_orientation_bit: int
    orientation_rejection_counter: int
    slot_capabilities: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class AssignmentLedger:
    study_id: str
    frozen_created_at: str
    manifest_ref: ArtifactRef
    schedule_ref: ArtifactRef
    prefix_index_ref: ArtifactRef
    matching_program_ref: ArtifactRef
    assignment_master_key_commitment_sha256: str
    assignment_prefix_view_sha256: str
    assignment_mode: AssignmentMode
    matching_proof_refs: tuple[ArtifactRef, ...]
    assignments: tuple[TaskAssignment, ...]
    allocation_receipts: tuple[AllocationReceipt, ...]
    donor_match_receipts: tuple[DonorMatchReceipt, ...]


@dataclass(frozen=True, slots=True)
class ScheduleSelection:
    schedule_authority: Literal[
        "synthetic_validation",
        "roster_bound_selection",
    ]
    selected_tier: Literal[120, 160] | None
    selected_task_ids: tuple[str, ...]


def require_schedulable_power_final(
    manifest_ref: ArtifactRef,
    power_final_ref: ArtifactRef,
    *,
    run_root: Path,
) -> ScheduleSelection:
    ...


def seal_prefix_schedule(
    manifest_ref: ArtifactRef,
    power_final_ref: ArtifactRef,
    *,
    schedule_seed_reveal: int,
    storage_policy_lease: StoragePolicyLease,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def seal_branch_assignment(
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    *,
    assignment_secret_handle: AssignmentSecretHandle,
    matching_backend_session: ConfirmationMatchingBackendSession | None,
    storage_policy_lease: StoragePolicyLease,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def require_assignment_reconstruction(
    ledger_ref: ArtifactRef,
    *,
    assignment_secret_handle: AssignmentSecretHandle,
    matching_backend_session: ConfirmationMatchingBackendSession | None,
    run_root: Path,
) -> AssignmentLedger:
    ...


def require_confirmation_assignment(
    ledger_ref: ArtifactRef,
    *,
    assignment_secret_handle: AssignmentSecretHandle,
    matching_backend_session: ConfirmationMatchingBackendSession | None,
    run_root: Path,
) -> AssignmentLedger:
    ...


def verify_result_bundle(
    receipt_path: Path,
    ledger_ref: ArtifactRef,
    *,
    assignment_secret_handle: AssignmentSecretHandle,
    matching_backend_session: ConfirmationMatchingBackendSession | None,
    required_document_kinds: Collection[str],
    run_root: Path,
) -> None:
    ...
```

`ConfirmationMatchingBackendSession` is a nominal live runner session, not a
structural solver seam or free scientific input. Only the trusted
`ConfirmationPreflightRegistry` can open it, after resolving the manifest
program/backend receipt, byte-checking the pinned provenance and KAT sources,
measuring the exact container image, command, environment, runtime,
single-thread and zero-gap settings, and running the pinned known-answer problem
to byte-equal expected output. The session is bound to the exact
manifest/schedule/prefix tuple and one transaction nonce. It permits the exact
algorithm-derived sequence of primary, tie-trial, and final solves across
strata, then closes once with a complete ordered transcript. A copied object,
subclass, matching-ref lookalike, stale session, unexpected problem/order/count,
solve after close, or second close rejects.

Every call launches the pinned container anew through the registry-held runner
and returns a closed invocation receipt binding nonce/index, input/output refs,
observed image/argv/environment, exit status, stdout/stderr digests, and an
Ed25519 signature verified against the backend-receipt public key. The
container digest plus the signed build-provenance binding is the executable
authority; source refs alone are not. These signed artifacts
are solver transcripts, not independently checkable optimality certificates.
The trust boundary is the pinned runner key, container runtime/OS, and honest
controller operator. Keyed reconstruction opens a fresh transaction/session and
requires the same canonical solutions and mapping; it never treats replay
through the original Python object as independent evidence.

Triggered confirmation requires exactly one authority-matched live backend
session for both sealing and each keyed reconstruction. All-no-trigger
confirmation requires `matching_backend_session is None` and empty proof refs.
Synthetic always requires `matching_backend_session is None`; it never ignores
a supplied session. The local core's bounded exhaustive solver is reachable
only through a test-only registry session and cannot satisfy an eligible
confirmation manifest. The zero-spend core contains no production confirmation
preflight/runner adapter: a separately reviewed benchmark-adapter plan must
implement and pin one before any eligible confirmation study manifest or prefix
is sealed. Supplying an object later cannot repair missing authority.

Every assignment seal or reconstruction consumes a fresh assignment-purpose
handle from the concrete `AssignmentSecretStore`; every unblind operation
consumes a distinct unblind-purpose handle. The core—not the store—verifies the
32-byte master commitment and derives the scoped subkeys. Without recomputing
`K_allocation`, `K_orientation`, and `K_capability` in that core context,
`require_confirmation_assignment` cannot claim to reconstruct a keyed ledger.

Every manifest-owned assignment input is parsed and canonically re-emitted
before it is copied. The task registry is the closed object
`{record_kind="resampling_task_registry_v1", schema_version="1", tasks=[...]}`;
each task has exactly `task_id`, `benchmark`, `stratum`, `lineage`, and
`groups`. The roster is the closed object
`{record_kind="resampling_roster_v1", schema_version="1", roster_kind,
supported_tiers, tasks}`. `supported_tiers` is exactly `[120]` or
`[120,160]`; a task row adds exactly `tiers`, a strictly increasing non-empty
subset. Roster IDs equal the union of supported tier IDs, never all qualified
tasks, pilots, reserves, or the unselected eligible suffix.

Eligible confirmation is imported only as this six-asset ceremony, copied to
the exact deterministic paths shown:

1. `inputs/roster/qualification.json` is
   `resampling_qualification_universe_v1` with exactly `schema_version`,
   `study_id`, `task_registry_sha256`, and `rows`. Each registry task appears
   exactly once with its registry metadata plus `qualification_status`,
   `qualification_receipt_ref`, and `rejection_reason_codes`; accepted has
   an empty reason array and rejected has a non-empty sorted array.
2. `inputs/roster/selection-program.json` is
   `resampling_roster_selection_program_v1` with exactly `schema_version`,
   `study_id`, `qualification_sha256`, `program_id =
   "neurips-roster-selection-v1"`, `supported_tiers`, `nested_tiers = true`,
   `rank_frame_tags`, and canonical `quota_rows`. Each quota row has exactly
   benchmark, encoded stratum key, pilot count, C120 count, nullable C160 count,
   and reserve count; C160 is non-null iff tier 160 is supported.
3. `inputs/roster/precommit.json` is `resampling_roster_precommit_v1` with
   exactly `schema_version`, `study_id`, qualification/program SHA-256s,
   `roster_local_nonce_commitment_sha256`,
   `schedule_seed_commitment_sha256`,
   `assignment_master_key_commitment_sha256`,
   `ceremony_policy_sha256`, `beacon_chain_hash`, and a strictly future
   exact-integer `beacon_round`. The first commitment binds the study ID and
   32-byte `roster_local_nonce`; it is not a commitment to already-known final
   roster randomness. This one precommit binds all three commitments before
   any external timestamp or beacon observation.
4. `inputs/roster/anchor.json` is the exact Sigstore bundle v0.3 for
   `inputs/roster/precommit.json`. Its verified message digest equals
   `precommit_sha256`; it contains exactly one RFC3161 timestamp and exactly one
   Rekor inclusion proof. The verified TSA `genTime` is the sole chronology
   time. Rekor `integratedTime` is recorded as bundle evidence but is never
   interpreted as the precommit time.
5. `inputs/roster/reveal.json` is `resampling_roster_seed_reveal_v1` with
   exactly `schema_version`, `study_id`, qualification/program/precommit/anchor
   SHA-256s, `roster_local_nonce_hex`, beacon
   chain/round/randomness/signature, and `roster_seed_hex`. The nonce and final
   seed hex values are exactly 64 lowercase characters. Import verifies the
   nonce commitment and authenticated future-beacon round, then recomputes the
   final seed as
   `SHA256(FRAME("roster-seed-v1", [BYTES(precommit_sha256),
   BYTES(roster_local_nonce), BYTES(beacon_chain_hash), U64(beacon_round),
   BYTES(beacon_randomness)]))`.
6. `inputs/roster/eligibility.json` is
   `resampling_eligibility_manifest_v1` with exactly `schema_version`,
   `study_id`, ArtifactRefs to the five prior deterministic paths,
   `supported_tiers`, `pilots`, `tiers`, `reserves`, and `roster_sha256`.
   Pilot/reserve rows have exactly encoded stratum key, zero-based rank, and
   task ID. `tiers` has exactly C120 and, only when supported, C160.

Every qualification ref resolves a content-addressed
`resampling_task_qualification_receipt_v1` closed object copied under
`inputs/roster/qualification-receipts/{sha256}.json`. It has exactly
`schema_version`, task/benchmark, `qualified`, immutable
`base_revision_ref`, immutable OCI image manifest/config/layer refs and
`linux/amd64` digest, plus ordered `gate_results`. A gate row has exactly the
benchmark-registered `gate_id`, `passed`, and a non-empty canonical array of
typed evidence ArtifactRefs. SWE requires the license/archive/image, hardened
adapter, three fresh base/gold pairs, registered-check coverage, and resource
admission gates; TAU requires immutable task/dependency/image, three replay,
off-policy fuzz, objective-component, leakage, and resource-admission gates.
Status and rejection codes are recomputed from this complete required gate set.
Study seal copies receipt/evidence sources to digest-derived paths, parses every
closed kind, follows every nested ref, and rejects a naked receipt digest,
missing evidence bytes, wrong task/base/image, or alternate receipt. The
qualification-universe digest therefore commits to resolvable qualification
evidence before the precommit.

`inputs/roster/ceremony-policy.json` is a seventh, manifest-conditional policy
asset rather than a ceremony result. Its closed
`resampling_roster_ceremony_policy_v1` grammar pins Sigstore bundle v0.3,
exactly one RFC3161 timestamp, exactly one Rekor inclusion proof, and drand
default mainnet: chain hash
`8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce`,
scheme `pedersen-bls-chained`, group hash
`176f93498eac9ca337150b46d21dd58673ea4e3581185f869672e59fa4cb390a`,
genesis Unix time `1595431050`, and period 30 seconds. The round-1 KAT
randomness is
`101297f1ca7dc44ef6088d94ad5fb7ba03455dc33d53ddb412bbc4564ed986ec`.

Beacon verification uses official `drand-client` 1.4.2. The policy pins package
tar SHA-256
`81de34afba38520b461152bf032cfb5139bb6ced205bf9f50bc8216fdc394eef`,
package integrity
`sha512-jeNJmrVplfgIA/GVndxxJ5mo8y63BS2pEdNhk1siU4pQ+z/BnxsqRnxjH9ag1ip887s12SEgo0MTZPbQNz27NA==`,
source commit `ef8c9260294f8699b5e8c27a6b764f8f0d768bea`, and extracted bundled
CJS SHA-256
`45cb65d533cc7e8527e9bba92df875c066511c3d6286adc7fcb293f0d03c7566`.
The package/source/bundled-CJS/KAT refs each byte-equal a manifest
`source_revision_ref`; BLS verification is never hand-implemented.

Precommit anchoring uses cosign v3.1.2 Windows x64 SHA-256
`fe4d621d7ae5e900ee62089837c00f996ae9acb82027d573d1d157b6ee875cb2`
and companion Sigstore JSON SHA-256
`e8d7ea5dd91902b0c23e68a08136d9c43b3573a4974fdbdc89ba5a6890a4ab8b`.
Before ceremony use, the adapter records the installed version/help output and
verifies the exact invocation against that installed build; remembered command
syntax is not authority. The cosign binary, companion JSON, exact argv, verified
bundle, certificate/identity policy, TSA trust material, and verification
receipt are pinned and copied. Chronology uses verified TSA `genTime`, never
Rekor `integratedTime`.

The target drand round's mainnet time must be at least 24 hours after verified
TSA `genTime`; selecting the round approximately 5,760 periods (48 hours)
after `genTime` is preferred. The selected target round and
`roster_local_nonce` are immutable after anchoring: no failure, delay, or
unfavorable randomness authorizes a replacement nonce, commitment set, or
round.
The `ConfirmationPreflightRegistry` verifies the whole policy and assets 1–6,
requires verified TSA chronology to precede the authenticated target round,
and mints one nominal capability bound to every source digest. Study seal
consumes that exact capability before copying. A self/local timestamp, absent
or duplicate RFC3161 timestamp, absent or duplicate Rekor proof, alternate
precommit, changed qualification/quota/commitment, target less than 24 hours
after `genTime`, invalid beacon proof, cross-study replay, replacement
nonce/round, or second capability use rejects. The timestamp plus future beacon
makes post-anchor grinding independently detectable. It still proves binding
and authority-relative order, not metaphysical chronology: a dishonest
TSA/drand authority, compromised controller, or hidden alternate study identity
is outside this code's proof.
Eligible confirmation remains unavailable until a reviewed nominal adapter
implements the pinned Sigstore/cosign and drand verifiers; no generic beacon,
timestamp, signature callback, or unverified HTTP response can mint the
ceremony capability. This core slice installs no official
`drand-client`/Sigstore Node dependency lock, pins no executable Node runtime,
and implements no nominal live adapter. A separate reviewed adapter plan must
provide all three plus their KAT/runtime receipts. Until then the registry
fails closed, and synthetic, mocked, or test-only evidence cannot be relabeled
as an eligible-confirmation ceremony.

Qualification accepted/rejected rows partition the registry. Pilots, every
supported tier, and reserves are accepted; pilots are disjoint from all tiers
and reserves; reserves are disjoint from all tiers; C120 is a subset of C160
when C160 exists; and no task/rank repeats. Import recomputes every HMAC ranking,
pilot/tier/reserve selection, derived roster bytes, and all equality/disjointness
relations. Zero supported tiers emits a typed pre-study eligibility no-go and
forbids an eligible-confirmation manifest; it never reaches Task 8.
For every supported tier `t` and each benchmark, exactly `t` roster rows contain
`t`; C120 IDs are nested in C160; every row has its complete registered joint
groups; and each registered group partition count sums to exactly `t`.

Task-registry, qualification, and roster rows are unique and strict-UTF-8 sorted
by `(benchmark, stratum, lineage, task_id)`; group labels use `language`,
`domain`, `issue_family`, then value bytes; tier IDs use registry order; pilot
and reserve rows use `(stratum_key, rank, task_id)`. These semantic-set arrays
are sorted before canonical serialization, so source reordering is
byte-invariant. Duplicate keys/items, unknown fields, non-NFC/section-4.0 text,
and a boolean/float where an exact non-negative integer is required reject.
Arrays whose order is scientific authority—tier nesting, pilot/reserve rank,
provider lanes, component kinds, and `stratum_key`—are validated rather than
silently resorted.

The assignment program is a closed canonical JSON object, never `.py`, a module
name, command, or executable bytes. Its exact keys are `record_kind =
"resampling_assignment_program_v1"`, `schema_version = "1"`,
`assignment_mode`, `matching_algorithm`,
`finding_count_band_upper_bounds`, `report_length_band_upper_bounds`,
`verifier_normalizer_contract`, `assignment_runtime_contract`,
`backend_receipt_ref`, and `stratum_keys`. Mode/algorithm pairs are the two
closed pairs above.
Cutpoints are strictly increasing exact non-negative integers. The runtime
contract has exactly `implementation = "CPython"`, full
`python_version`, and `unicodedata_unidata_version`; study seal and every
assignment/reconstruction entry point require exact equality with
`platform.python_version()` and `unicodedata.unidata_version`.
The normalizer contract has exactly `contract_id =
"assignment-verifier-normalizer-v1"`, `normalizer_source_ref`,
`normalizer_source_sha256`, `report_tokenizer_sha256`, and ordered
`benchmark_component_kinds`:
`{"SWE":["check_runner","failure_class"],
"TAU":["evaluator_component"]}`. `normalizer_source_ref` must byte-equal one
manifest `source_revision_ref`, its digest must equal
`normalizer_source_sha256`, and `report_tokenizer_sha256` must equal the
manifest `tokenizer_ref.sha256`. Backend receipt is null exactly for synthetic
and a closed ArtifactRef exactly for confirmation.

That confirmation backend ref resolves a closed canonical object with exactly
`record_kind = "exact_matching_backend_receipt_v1"`, `schema_version = "1"`,
`backend_id`, `backend_version`, `test_only`, `mechanism`,
`implementation_ref`, `implementation_sha256`, `container_image_digest`,
`build_provenance_ref`, `build_provenance_sha256`, `command_argv`,
`single_threaded = true`, `mip_gap_ppm = 0`,
`canonical_io_contract_id = "exact-matching-json-v1"`,
`assignment_runtime_contract_sha256`, `kat_problem_ref`,
`kat_expected_solution_ref`, `builder_attestation_public_key_ed25519_hex`,
`runner_attestation_public_key_ed25519_hex`, and
`environment`. `mechanism` is
`bounded_exhaustive_fixture` iff `test_only = true` and the image digest is
null; a schedulable confirmation backend requires `test_only = false`,
`containerized_confirmation`, and a lowercase `sha256:<64-hex>` image digest.
`command_argv` is a non-empty strict-text array copied exactly; `environment`
has exactly `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, and
`MKL_NUM_THREADS`, each string `"1"`. The implementation and runtime digests
are recomputed by following `implementation_ref` and requiring its raw digest
to equal `implementation_sha256`; implementation, build provenance, KAT
problem, and expected-solution refs each byte-equal one manifest
`source_revision_ref`.

The build provenance is closed
`exact_matching_build_provenance_v1` canonical JSON with exactly
`schema_version`, sorted complete `source_material_refs`, `build_recipe_ref`,
`builder_image_digest`, `build_command_argv`, `output_container_image_digest`,
`builder_attestation_public_key_ed25519_hex`, and
`builder_signature_ed25519_hex`. Every material/recipe ref byte-equals a
manifest source revision, the implementation ref is among the materials, the
provenance builder key must equal the independently pinned backend-receipt key,
the signature verifies the canonical object with its signature field omitted, and
the output digest equals the backend container digest. This is a
trusted-builder provenance claim, not a claim that arbitrary parties can
reproduce the image bit for bit. KAT refs resolve closed problem/solution
objects, and the live preflight must reproduce the exact expected canonical
solution. The session's authority/backend refs resolve this exact program and
receipt.

Each referenced verifier-feature blob is closed canonical JSON with exactly
`record_kind = "assignment_verifier_features_v1"`, `schema_version`, `task_id`,
`benchmark`, `source_verifier_ref`, `source_report_ref`, ordered `components`,
`objective_finding_count`, and `normalized_report_token_count`. A component has
exactly `kind`, strict text `value`, and positive exact-integer `count`; kind
order and complete required kind coverage come from the normalizer contract.
Trusted import/reconstruction reloads both typed source refs, reruns the
manifest-pinned normalizer and tokenizer, and byte-compares every derived
feature. Raw finding/report text remains only behind those refs; grades,
outcomes, precomputed bands, and raw refs inside the capability-minimal
`AssignmentPrefixView` are forbidden.

The provider-lane plan is the closed object
`{record_kind="provider_lane_plan_v2", schema_version="2", lanes, task_lanes}`.
`lanes` is a non-empty authoritative array of unique rows with exactly
zero-based contiguous `ordinal`, strict-text `lane_id`, closed `prefix_caps`
and `branch_caps`, closed aggregate `simulator_caps`, and exact
`subject_contract_ref`, `simulator_contract_ref`, `tool_parser_contract_ref`,
and `meter_contract_ref` ArtifactRefs.
`simulator_contract_ref` is null only for a lane whose selected tasks cannot
invoke a user simulator. The subject and simulator contracts pin the model,
tokenizer, template, tool schema, request/response grammar, seeded-call
attempt grammar, stateless-client attestation, aggregate and per-call
output/turn caps, exact nominal implementation type/build, and every
manifest-copied source-revision ref.
The meter contract pins the controller clock/watchdog source, cost units,
provider-event/settlement grammar, exact nominal implementation type/build,
and zero-cost synthetic closure. `prefix_caps` and
`branch_caps` carry exact primary-subject generated-token/model-call,
subject-issued tool-call, and total elapsed-wall ceilings; branch caps also
set `pending_prefix_calls_count_against_tool_cap = true`. Simulator
model/token counters are separately bounded by its contract and never consume
the primary-subject generated-token/model-call ceilings. Simulator latency
does consume the total elapsed-wall ceiling, and all subject plus simulator
costs enter the same provider-cost closure.

`task_lanes` is a canonical task-ID-sorted complete array whose rows have
exactly `task_id`, `prefix_lane_ordinal`, four
`lane_ordinals_by_execution_rank`, and exact `task_input_ref`,
`environment_contract_ref`, `grader_contract_ref`,
`verifier_contract_ref`, and `isolation_contract_ref` ArtifactRefs. Those
closed contracts bind the canonical executable task payload, environment
factory/build/type, snapshot/restore grammar, raw grade/verifier grammar,
runtime/container/source revisions, and distinct-instance/process/root plus
no-shared-writable-state isolation requirements. Study sealing follows,
copies, byte-verifies, and grammar-validates every nested ref and requires its
task ID/benchmark/revisions to equal the task registry and manifest. Schedule
loading repeats those checks. `run_prefix` rejects a supplied implementation
whose nominal type/build/qualification receipt differs from the selected
contract; a caller cannot choose task or environment semantics.

For each benchmark the assignment program also freezes one ordered
`stratum_key` JSON-string array:
SWE is `["benchmark","language","check_runner","failure_class",
"finding_count_band","report_length_band"]`; TAU is
`["benchmark","domain","evaluator_component_multiset",
"finding_count_band","report_length_band","issue_family_rule"]`. This array is
encoded directly, never joined with a delimiter or replaced by map iteration.

The field arrays do not leave their values implicit. SWE constructs values as
the literal `"SWE"`, strict normalized language/check-runner/failure-class
text, and canonical unsigned-decimal band indices (ASCII `0` or a nonzero digit
followed by digits; no sign or leading zero). TAU constructs literal `"TAU"`,
strict domain text, a component-multiset token, the same decimal bands, and one
constant rule token. To form the multiset, merge duplicate normalized
`(kind,value)` rows by exact integer sum, UTF-8 sort by `(kind,value)`, encode
compact canonical JSON as `[[kind,value,count],...]`, and use
`"sha256:" + SHA256(bytes)` as the stratum component while retaining the full
array in the verifier-feature blob for collision checking. The rule is exactly
`telecom_prefer_cross_family_else_same_family_v1` for telecom and
`not_applicable_v1` for airline; the actual issue-family value remains a
separate prefix-view feature and never becomes a stratum component.

TAU base edges require equality of domain, full collision-checked component
multiset, both bands, and rule, plus ordinary self/lineage exclusions. For a
telecom focal, pass one retains only surviving donors with a different actual
issue family. If that set is non-empty, same-family edges are forbidden. Only
when it is empty does pass two admit surviving same-family donors and attach
`cross_family_component_match_unavailable`. Airline uses the base edges once
and forbids that fallback code. Candidate-graph reconstruction repeats this
two-pass rule before optimization.

The storage-policy contract is a closed `mode`-discriminated canonical object.
`local_test` has `test_only = true`, `storage_resource_id = null`,
`measurement_evidence_ref = null`, `evidence_verifier_public_key… = null`,
`registry_attestation_public_key… = null`,
`max_measurement_age_seconds = null`, process-lock lease kind, both enforcement
booleans false, and null algorithm/KMS/ACL/measurement fields. It is legal only
for a synthetic fixture and makes no host-encryption or ACL claim.
`confirmation` has `test_only = false`, a non-empty immutable provider resource
ID, non-null evidence ref, separate exact 32-byte Ed25519 evidence-verifier and
registry-attestation public keys, positive exact measurement age,
provider-resource lease kind, both enforcement booleans true, and non-empty
encryption algorithm/KMS version plus lowercase raw-measurement and ACL-policy
SHA-256 digests. The two public keys must differ: evidence signatures never
authorize registry state, and registry signatures never authorize measurement
evidence. This arm is required for eligible confirmation. Run-root identity is
intentionally absent from this scientific contract so equivalent scratch roots
retain byte-identical scientific inputs.

The evidence ref resolves the separately copied deterministic
`inputs/storage/measurement-evidence.json` with media type
`application/vnd.pneuma.storage-measurement+json`. Its closed
`storage_measurement_evidence_v1` object has exactly `schema_version`,
`provider_kind`, `storage_resource_id`, `resource_version`,
`mount_identity_sha256`, `encryption_at_rest = true`,
`encryption_algorithm`, `kms_key_version`, `acl_enforced = true`,
`acl_policy_sha256`, canonical `measured_at_utc`, `verifier_identity`,
`verifier_public_key_ed25519_hex`, and `verifier_signature_ed25519_hex`.
The signature covers compact canonical bytes with its own field omitted.
Contract/evidence resource, encryption, KMS, ACL, and verifier-key fields must
match exactly; `measurement_sha256` equals `measurement_evidence_ref.sha256`.
Study seal copies this source only for confirmation and rejects a missing,
unknown-field, stale, bad-signature, mismatched, or local-test evidence source.

`seal_prefix_schedule` loads the task registry, roster, conditional eligibility
manifest, provider-lane mapping, and assignment program only through ArtifactRefs
inside the validated manifest. It accepts no free task list, eligibility ref,
program ref, provider-plan ref, authority, tier, membership, or claimed digest.
Its only Task-8 seam is `require_schedulable_power_final`, which reloads the
final and all attempts and returns only closed authority, selected tier, and
selected task IDs—never Task-8 internals or caller mirrors. Task 3 freezes and
validates this completed-final consumer contract, including test-only
hand-authored complete chains; it contains no attempt/final writer, simulator,
or production fixture. Task 8 is the sole power-report producer and simulator.
Roster-bound
requires a completed `GO` chain and derives exactly the C120/C160 rows selected
by its tier from the manifest-owned eligibility/roster. Synthetic requires a
completed `CONDITIONAL_ONLY` chain with null tier and derives the complete
fixture roster. Every failure/no-go/cross-authority arm rejects before a
schedule write.

Before checking the schedule-seed reveal, it consumes the exact nominal
`storage_policy_lease`. Confirmation accepts only a registry-held live lease
bound to the manifest, null schedule, pinned evidence/resource, and current
root; synthetic accepts only the exact local-test lease type. The core starts
the lease before destination creation or scientific/raw writes and obtains the
closed `begin` observation with lease ID, generation zero, expiry, and renewal
sequence zero. Inside that still-live lease it performs the selected-membership
check, schedule-seed verification, and deterministic schedule derivation
specified below. Only after all of those succeed does it write the exact
schedule bytes to a same-directory temporary file, fsync that file, and request
the mode-valid non-releasing `end` remeasurement while the same lease and
transaction lock remain live and unexpired. It renews only before that end as
needed. The end attestation carries `releases_lease = false`. The
`StorageTransactionIntent` serializes every strictly ordered renewal and proves
no gap: each renewal occurs before the preceding expiry, retains the same
lease/resource/version/mount/policy tuple, increments both generation and
renewal sequence by one, and extends the expiry. The end observation matches
the latest generation/sequence, is fresh before its expiry, and retains the
same evidence ref, manifest, null schedule, and normalized operational root.
The intent also binds the prepared scientific relative path and SHA-256, final
generation and expiry, and `end_releases_lease = false`. The core writes those
canonical intent bytes to
`operational/storage-policy/intents/prefix.json`, fsyncs the file and parent,
and records its SHA-256 before scientific install. This intent is operational
write-ahead state, not a receipt or acceptance marker.

After the non-releasing end, the core permits no further renewal. It first
proves the final expiry leaves enough bounded time for scientific install,
scientific-parent fsync, and the registry publication-commit call, or fails
before scientific install. It atomically installs the already-fsynced schedule
bytes at the scientific path and fsyncs the parent while the same lease and
transaction lock remain live. It then asks the trusted registry to recheck the
same lease, binding tuple, intent digest, exact scientific path/digest, and
current time. Before the unchanged final expiry, the registry prepares exactly
one canonical `StoragePublicationCommit`. It binds the registry commit ID/time,
intent digest, scientific path/digest, final
generation/expiry/renewal sequence, complete storage tuple,
`commit_recorded = true`, `lease_consumed = true`, and
`release_required = true`. The registry signs that canonical proof in
confirmation mode, then atomically writes the exact proof bytes, unique commit
ID, and `end_observed -> committed_consumed` state. Only after that durable
write may it respond or attempt provider/lock release. A release failure leaves
a committed, consumed, non-reusable lease with idempotent cleanup pending; it
does not mutate or erase the commit proof.

Only a durable registry commit proof authorizes construction of the final
receipt. The core embeds the exact intent and commit proof, recomputes their
cross-bindings, writes canonical receipt bytes to a same-directory temporary
file, fsyncs it, atomically installs it once at
`operational/storage-policy/prefix.json`, and fsyncs that parent. The final
receipt bytes are identical whether the original transaction or recovery
finalizes them. Durable local acceptance is exactly the conjunction of the
scientific file and this fixed validating receipt, whose nested signed commit
proof (or closed test-only local commit) and intent bind the recomputing
scientific digest. The fixed receipt is
immutable after install; the intent remains immutable audit/recovery evidence
outside scientific closure.

A crash before scientific install may leave a non-authoritative intent.
Replacement requires proof that the scientific path is absent and the registry
has no commit; recovery must atomically transition the old lease
`end_observed -> aborted_consumed`, invalidate its original handle, and attempt
release before a fresh lease may replace the intent. A crash after scientific
install but before registry commit leaves permanently quarantined bytes and
recovery is forbidden to manufacture or request a commit. A crash after
registry commit but before fixed-receipt fsync may only fetch the already
durable proof by its intent/lease binding and deterministically finalize the
same receipt; acceptance begins only when that receipt and exact science are
durable. A missing/invalid proof, intent mismatch, science mismatch, second
commit, or free-form recovery field rejects. Recovery may idempotently finish
abort/release cleanup but cannot alter the proof, intent, science, or final
receipt. Any failed begin/renewal/end/seed/selection before scientific install
leaves no schedule.

The selected membership digest used in that in-lease pre-write computation is
SHA-256 over compact canonical JSON with the exact keys `rows`,
`schedule_authority`, `schema_version`, and `selected_tier`.
Each row has exactly `benchmark`, ordered `groups`, and `task_id`; rows are
strict-UTF-8 sorted by `(benchmark, task_id)`. Authority is
`synthetic_validation` or `roster_bound_selection`; tier is JSON null for
synthetic and 120 or 160 for roster-bound. The schedule stores that recomputed
digest and the exact final ref.

Inside the live lease, after `begin` and before the temporary schedule write,
it verifies `schedule_seed_reveal` against the manifest's schedule commitment.
Tasks are sorted by strict UTF-8
`(benchmark, stratum, lineage, task_id)`; group labels are ordered
`language, domain, issue_family`, then by value bytes. Each task's `slots` array
is canonical ordinal order `0..3`. The only schedule derivation roles are
`prefix`, `slot-0`, `slot-1`, `slot-2`, `slot-3`,
`execution-order-0`, `execution-order-1`, `execution-order-2`, and
`execution-order-3`; any other/free role rejects. Slot seeds use their matching
slot role. Execution order retains the full raw SHA-256 digest of the
`derive-seed-v1` frame for each execution-order role, sorts by
`(order_digest_bytes, slot_ordinal)`, and assigns ranks `0..3`; ordinal is the
mandatory digest-collision fallback. `TaskSchedule.provider_lane` is the lane
ID at that task's frozen `prefix_lane_ordinal`; a branch slot with execution
rank `r` receives exactly the lane ID/ordinal at
`lane_ordinals_by_execution_rank[r]`. No hash-map, worker arrival, or provider availability
may remap it. The prefix schedule fixes its final-selected
membership, prefix/slot seeds, task order, execution order, hardware/provider
lane, and all referenced assets before prefixes; it contains no donor, packet,
arm, master key, or outcome.

Only after every common prefix and verifier artifact is frozen does
`seal_branch_assignment` load the schedule through `schedule_ref`, reload the
manifest through `schedule.manifest_ref`, load the prefix receipt through
`prefix_index_ref`, and prove:

- schedule IDs equal the final-derived selected membership and prefix-receipt
  IDs; the manifest roster may be a strict C160 superset of selected C120;
- every prefix task has one matching nested verifier receipt;
- all nested schedule, snapshot, verifier, and grade ArtifactRefs resolve under
  the same run root with the expected role/kind/digest;
- task/benchmark/stratum/lineage/group metadata match byte for byte; and
- no packet, task block, endpoint, or later scientific record already exists.

Before opening the assignment-purpose secret handle or backend session it
consumes an assignment-bound storage lease and obtains the mode-valid `begin`
observation. A prefix lease/receipt cannot replay. The core independently
verifies the master commitment, derives only the four assignment subkeys,
builds the allowlisted prefix view, solves donors for triggered tasks, draws
treatments for every task, zeroes buffers, and closes the backend session. It
may idempotently stage immutable content-addressed matching blobs: an existing
path is accepted only when canonical bytes and digest match exactly. It then
serializes every in-interval renewal, writes and fsyncs the exact ledger bytes
to a same-directory temporary file, requests the lease's mode-valid
non-releasing `end` remeasurement, and rejects a gap, changed lease ID, nonconsecutive
generation/renewal sequence, stale end, or any resource, version, mount,
evidence, encryption/KMS/ACL, manifest/schedule, or root change. It embeds that
closed lifecycle and the exact prepared ledger path/digest in a canonical
`StorageTransactionIntent`, writes it at
`operational/storage-policy/intents/assignment.json`, and fsyncs the file and
parent before scientific install. The intent path is not a receipt or
acceptance marker and may be replaced only before any ledger install.

After proving sufficient remaining final-lease lifetime for ledger install,
ledger-parent fsync, and registry commit—and forbidding every post-end
renewal—the core installs and fsyncs the ledger while the same lease and
transaction lock remain live. The registry rechecks the final tuple, current
time, intent digest, and exact ledger path/digest, then prepares exactly one
`StoragePublicationCommit`, signs it in confirmation mode, atomically stores
the proof while transitioning `end_observed -> committed_consumed` before the
final expiry, and only then attempts release. The proof records
`release_required = true`; any release failure leaves
a durable committed, consumed, non-reusable state with cleanup pending and
cannot mutate that proof.

The core constructs the unique final receipt from the exact intent and commit
proof, writes/fsyncs it at a same-directory temporary path, installs it once at
`operational/storage-policy/assignment.json`, and fsyncs that parent. The exact
ledger-plus-fixed-receipt pair is the only durable local acceptance predicate.
A crash after ledger install but before registry commit quarantines the ledger
and forbids recovery commit; a crash after durable registry commit may only
fetch the existing proof and deterministically finalize the same receipt.
Before scientific install, a retry may replace the non-authoritative intent and
safely reuse byte-identical unreachable CAS objects only after proving the
ledger path absent and atomically aborting/consuming the old uncommitted lease;
a later reachability GC may delete those blobs. Abort/release cleanup may be
retried idempotently but cannot alter or authorize the accepted pair. No branch
endpoint is an input.

`ConfirmationStorageLease` is an exact non-subclassable nominal type with a
private registry nonce, tuple binding, lease ID, and registry membership/state
check; it is not a `Protocol`. The trusted registry verifies the
manifest-pinned evidence signature and freshness, independently queries the
provider/OS for that immutable resource, locks or leases the resource/mount, and
signs begin, ordered renewal, and non-releasing end observations. Each
observation serializes the lease ID, registry-issued generation, expiry,
renewal sequence, complete binding tuple, provider measurement, and
`releases_lease = false`; observations never close the lease. The separate
publication-commit call accepts only the original nominal live handle after
end, the exact canonical transaction-intent bytes/digest, and the already
fsynced scientific path/digest. The registry independently rechecks tuple and
time, prepares the canonical proof and, in confirmation mode, its required
signature, then atomically stores those exact bytes, the unique commit ID, and
`live -> end_observed -> committed_consumed` state before responding or
attempting release. If and only if the scientific path is absent and no commit
exists, recovery may instead atomically change
`end_observed -> aborted_consumed` before release and fresh-intent replacement.
End and commit/abort each occur exactly once; no renewal follows end; no second
terminal transition is possible; and release failure leaves the lease consumed,
never reusable. Recovery can fetch an existing proof or abort an uncommitted
no-science intent by their closed bindings but cannot invoke commit. A
copied/subclassed/lookalike lease,
copied or reordered attestation, wrong tuple, expiry gap, stale/closed lease,
second use, or provider/mount/policy swap rejects. The honest-operator boundary
is explicit: the controller OS, provider control plane, registry signing key,
and process are trusted; branch workers and arbitrary callers are not. A
failure occurs before seed verification, secret-handle read, backend open, or
destination creation.

`registry_commit_id` is exactly 64 lowercase hex. Confirmation draws 32 bytes
from the registry CSPRNG and retries locally until its durable uniqueness index
is clear; `local_test` deterministically uses
`SHA256(b"local-test-storage-commit-v1\x00" || intent_digest_bytes)`. The
registry enforces uniqueness across all stored commit proofs and never frees an
ID when terminal cleanup state changes, so one ID cannot name two transactions.

Every confirmation storage attestation and publication-commit signature covers
the compact canonical object with its own
`attestation_signature_ed25519_hex` field omitted, using the exact public key
in `registry_attestation_public_key_ed25519_hex`, never the distinct evidence
verifier key. Extra/missing fields, alternate canonicalization, key-role reuse,
a local-test object with a signature field, or a confirmation object without a
valid signature rejects.

The two and only two operational receipts are the canonical receipt bytes
at `operational/storage-policy/prefix.json` and
`operational/storage-policy/assignment.json`. The prefix arm binds the exact
manifest and null schedule; the assignment arm binds that manifest and the
exact schedule, so neither receipt can replay across transaction, study, root,
or schedule. Each embeds one exact `StorageTransactionIntent` with its lease
ID, confirmation-signed or closed-local-test begin, ordered renewal, and
non-releasing end,
`continuous_lease_held = true`, `fresh_at_end = true`, prepared scientific
path/digest, and final generation/expiry. It also embeds the registry's
`StoragePublicationCommit`, whose confirmation arm is registry-signed and whose
closed test-only local arm is not. It byte-binds that intent digest, the same
scientific path/digest and final lease tuple, a unique commit ID/time,
`commit_recorded = true`, `lease_consumed = true`, and the immutable release
requirement. The outer receipt requires `fresh_at_publication_commit = true`,
`publication_commit_recorded = true`,
`publication_commit_consumes_lease = true`, and
`fixed_receipt_is_acceptance_marker = true`; these are verified consequences,
never caller claims. It records no key bytes, decrypted arm map, or packet
text.

The fixed receipt path remains absent until a durable registry commit proof
exists. Scientific install and parent fsync precede that atomic commit; the
complete fixed receipt is then installed once and its parent fsynced without
claiming that marker installation itself occurred before lease expiry. A
post-commit crash may deterministically finalize only the proof-bound receipt;
a pre-commit crash cannot. Only the exact scientific-plus-fixed-receipt pair is
locally accepted, and replacement after fixed-receipt install rejects.
Operational intents, nested commit proofs, receipts, registry lookup state, and
root identity are excluded from scientific artifact-root closure.
`local_test` explicitly records false enforcement and null measurement fields;
it is a synthetic-fixture-only process-lock arm and makes no encryption or ACL
claim.
Eligible confirmation requires the measured `confirmation` arm before either
transaction. Its protected plaintext `Path` view remains visible only to
trusted assignment, preparer, verification, and unblind processes and is never
copied into, mounted in, or shared with branch workers or the analysis author
before unblinding. No third storage-envelope receipt or post-hoc assertion can
repair a pre-commit failure. The persisted intent, confirmation-signed or
closed test-only commit proof, fixed receipt, canonical implementation, and
replay establish the declared ordering
only under the trusted OS, filesystem, clock, registry, and signing-key
boundary. They are not an external post-commit timestamp and do not prove facts
outside that boundary.

The schema-valid `resampling-prefix-receipt` document is the complete
prefix/verifier index: it nests one `FrozenVerifierReceipt` plus snapshot and
grade artifact references per scheduled task. Thus the CLI's
`--prefix-index` is not a thirteenth ad hoc record kind. The assignment
function verifies its digest and exact task coverage before creating any
`AllocationReceipt`.

### Step 5: Freeze allocation, prefix-view, and matching algorithms

The serialized 12-row table is exactly:

```text
0  N N R S       6  R N N S
1  N N S R       7  R N S N
2  N R N S       8  R S N N
3  N R S N       9  S N N R
4  N S N R      10  S N R N
5  N S R N      11  S R N N
```

Here `N` means `NO_PACKET`, and columns are slot ordinals, never execution
order. Draw the row with `K_allocation` and
`FRAME("allocation-v1", [TEXT(task_id)])`. For the two no-packet ordinals
`q0 < q1`, orientation bit 0 maps `q0/q1` to `NONE/RESAMPLE`; bit 1 reverses
them. Draw it with `K_orientation` and the `orientation-v1` frame. Persist both
rejection counters. Reconstruct `TaskAssignment.slot_arms` from the receipt and
reject any discrepancy.

Derive capabilities with `K_capability` and the exact design frame binding
study, manifest digest, schedule digest, prefix digest, task, slot, and arm.
Verify uniqueness within each task and globally across the ledger. Allocation
and orientation frames contain no prefix/view/donor field, so metamorphic
changes to excluded prefix data leave arm draws fixed; capabilities change
because they deliberately bind the prefix.

Serialize `assignments`, `allocation_receipts`, and `donor_match_receipts` in
the schedule's canonical task order. Within each allocation receipt,
`slot_ids_by_ordinal`, `slot_arms`, and `slot_capabilities` are all ordinal
`0..3`, never execution order or map insertion order. Candidate and proof
arrays use the explicit orders below; verification rejects a permutation even
when it describes the same mathematical mapping.

Build `AssignmentPrefixView` from this allowlist only:

```text
task_id, benchmark, stratum, lineage, registered group labels,
trigger reason, normalized verifier/checker or component class,
objective finding count, normalized report token count,
telecom issue family
```

Explicitly forbid `Y_0`, partial reward, success, resource counters, timing,
cost, provider event, every raw ArtifactRef, finding/packet text, endpoint data,
branch fields, precomputed count/length bands, and a claimed
cross-family-availability bit. Do not serialize then delete a denylist, and do
not accept an `AssignmentPrefixView` from the caller. The internal builder
reloads each typed verifier receipt, recomputes the normalized component class,
objective finding count, and normalized report token count from its referenced
bytes, and compares task metadata with the schedule.

The manifest-pinned assignment program contains two closed arrays of strictly
increasing non-negative integer cut points:
`finding_count_band_upper_bounds` and
`report_length_band_upper_bounds`. For a recomputed integer `x`, its band is
the zero-based index of the first upper bound strictly greater than `x`, or the
array length when none is greater. Booleans, negative counts, unsorted or
duplicate cut points, and caller-provided band labels fail closed. Candidate
construction derives those integer band indices afresh. Telecom
`cross_family_component_match_available` is not a task feature at all: for
each focal task it is recomputed from the complete canonical edge graph after
all other exact eligibility gates and before same-family fallback edges are
considered. A verifier repeats both derivations from parent bytes.

For local synthetic fixtures only, sort eligible triggered tasks by canonical
ID, order candidates with `K_donor`, and search cyclic offsets for the first
different-lineage, no-two-cycle permutation. Mark it only as:

```json
{
    "assignment_mode": "synthetic_derangement",
    "matching_algorithm": "synthetic_cyclic_offset_v1"
}
```

No-trigger tasks receive `not_applicable_no_trigger`, not a fictitious donor.
They still receive all allocation/capability receipts and later use the typed
no-intervention packet marker. Triggered synthetic strata with fewer than three
distinct eligible lineages fail closed.

Confirmation constructs the full ordered eligible edge set from the allowlisted
view, including the frozen telecom same-family fallback rule. It solves the
binary program:

```text
one outgoing and one incoming edge per triggered task
no self or same-lineage edge
no reciprocal two-cycle
all frozen stratum/component/band constraints exact
lexicographic integer objective:
  (same-family fallback count,
   total finding-count distance,
   total report-token-count distance)
```

The manifest-pinned matching program/backend runs single-threaded and must
return `OPTIMAL`. Solver interchange uses no opaque or backend-native file.
Problem and solution blobs are exact closed objects serialized with the Task-2
`canonical_json_bytes(value, indent=None)` function: sorted keys, compact
separators, strict UTF-8, no BOM, exactly one terminal LF, and `allow_nan =
False`. The verifier parses and reserializes every blob and requires byte
equality. Identifiers use section 4.0's strict NFC/Unicode rule; digests are
lowercase 64-hex; all costs are exact non-negative integers with booleans and
floats forbidden; unknown fields fail.

The exact `exact_matching_problem_v1` payload is:

```json
{
  "assignment_prefix_view_sha256": "<sha256>",
  "assignment_program_sha256": "<sha256>",
  "backend_receipt_sha256": "<sha256>",
  "constraints": {
    "forbid_same_lineage": true,
    "forbid_self": true,
    "forbid_two_cycle": true,
    "one_incoming": true,
    "one_outgoing": true
  },
  "edges": [
    {
      "donor_task_id": "<id>",
      "focal_task_id": "<id>",
      "primary_cost": [0, 0, 0],
      "tie_hmac_sha256": "<sha256>"
    }
  ],
  "fixed_edges": [["<focal-id>", "<donor-id>"]],
  "focal_task_ids": ["<id>"],
  "record_kind": "exact_matching_problem_v1",
  "stratum_key": ["<component>"]
}
```

`focal_task_ids` is the triggered stratum in canonical prefix-view order.
`edges` contains every and only eligible edge, grouped in focal order and then
ordered by `(raw tie-HMAC bytes, strict UTF-8 donor ID)`; the initial problem's
`fixed_edges` is empty. A constrained tie trial appends exactly one
`[focal, donor]` pair to the previously fixed prefix. `fixed_edges` is in focal
order, contains no duplicate focal/donor, and is enforced in addition to the
five constant-true constraints. The assignment-program and backend-receipt
digests must resolve through the solver's two authority refs and the manifest.

The exact `exact_matching_solution_v1` payload is:

```json
{
  "backend_receipt_sha256": "<sha256>",
  "donor_by_task": [["<focal-id>", "<donor-id>"]],
  "objective": [0, 0, 0],
  "problem_sha256": "<sha256>",
  "record_kind": "exact_matching_solution_v1",
  "status": "OPTIMAL"
}
```

For `OPTIMAL`, `objective` is the exact three-integer objective and
`donor_by_task` is a complete permutation in the problem's focal order. For
`INFEASIBLE`, `objective` is `null` and `donor_by_task` is empty. No other
status is representable. The verifier hashes the canonical problem, checks the
solution's problem/backend digests, independently validates feasibility and
objective, and reruns the authority-matched solver; a backend-native log is
neither an input nor proof.

Among primary-cost-optimal completions, iterate focal tasks canonically and try
candidates by:

```text
(
  HMAC-SHA256(
    K_donor,
    FRAME("donor-tie-v1", [TEXT(focal_id), TEXT(donor_id)]),
  ),
  canonical_donor_id,
)
```

Fix the first edge whose exact re-solve preserves the optimal objective and a
complete solution. The donor ID resolves an HMAC collision. Every attempted
candidate, including infeasible or higher-objective attempts, is retained.
The confirmation proof blob has exactly this closed shape:

```json
{
  "assignment_prefix_view_sha256": "<sha256>",
  "assignment_program_sha256": "<sha256>",
  "backend_receipt_sha256": "<sha256>",
  "donor_by_task": [["<focal-id>", "<donor-id>"]],
  "final_problem_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-problem+json", "relative_path": "<relative>", "role": "exact_matching_problem", "sha256": "<sha256>"},
  "final_solution_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-solution+json", "relative_path": "<relative>", "role": "exact_matching_solution", "sha256": "<sha256>"},
  "invocation_receipt_refs": [{"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-invocation+json", "relative_path": "<relative>", "role": "exact_matching_invocation", "sha256": "<sha256>"}],
  "primary_problem_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-problem+json", "relative_path": "<relative>", "role": "exact_matching_problem", "sha256": "<sha256>"},
  "primary_solution_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-solution+json", "relative_path": "<relative>", "role": "exact_matching_solution", "sha256": "<sha256>"},
  "proof_kind": "confirmation_exact_v1",
  "schema_version": "1",
  "stratum_key": ["<component>"],
  "tie_steps": [
    {
      "focal_task_id": "<id>",
      "ordered_candidates": [["<tie-sha256>", "<donor-id>"]],
      "selected_donor_task_id": "<id>",
      "trials": [
        {
          "donor_task_id": "<id>",
          "problem_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-problem+json", "relative_path": "<relative>", "role": "exact_matching_problem", "sha256": "<sha256>"},
          "solution_ref": {"byte_count": 1, "media_type": "application/vnd.pneuma.exact-matching-solution+json", "relative_path": "<relative>", "role": "exact_matching_solution", "sha256": "<sha256>"}
        }
      ]
    }
  ]
}
```

Every displayed ArtifactRef uses the existing closed ArtifactRef definition;
`1` is only an illustrative positive byte count. `invocation_receipt_refs` is
the exact solve order: primary, every trial in focal/candidate order, then
final. Each signed receipt's nonce/index/problem/solution fields must match that
position and the corresponding refs; no call may be absent or duplicated.
`stderr_sha256` is signed diagnostic metadata only, never evidence of
feasibility or optimality. `tie_steps`
has one row per focal in order. `ordered_candidates` is the complete
`(tie-HMAC, donor ID)` order after removing only donors already consumed by the
previous fixed-edge prefix; the verifier derives that removal, and the donor
receipt still carries the focal's full pre-fixing candidate set. `trials` is
exactly the resulting non-empty prefix through the first solution whose status
is `OPTIMAL` and objective equals the primary objective;
`selected_donor_task_id` is that last trial. Each trial problem contains prior
selected fixed edges plus its candidate. The final problem fixes the complete
selected mapping, and its `OPTIMAL` solution, the proof mapping, ledger
assignments, and donor receipts must agree byte for byte.

Synthetic mode also emits one auditable proof per triggered stratum; it cannot
borrow confirmation semantics. First order the stratum by
`(HMAC-SHA256(K_donor, FRAME("synthetic-order-v1",
[BYTES(view_sha256), TEXT(stratum_key_0), ..., TEXT(task_id)])), task_id)`.
For offsets `1..n-1`, map cycle position `i` to `(i + offset) mod n`, checking
same lineage before reciprocal two-cycle in canonical focal order, and select
the first valid offset. The closed proof is:

```json
{
  "assignment_prefix_view_sha256": "<sha256>",
  "assignment_program_sha256": "<sha256>",
  "canonical_focal_task_ids": ["<id>"],
  "cycle_order": [{"order_hmac_sha256": "<sha256>", "task_id": "<id>"}],
  "donor_by_task": [["<focal-id>", "<donor-id>"]],
  "invocation_receipt_refs": [],
  "offset_trials": [{"failure_code": null, "offset": 1, "valid": true}],
  "proof_kind": "synthetic_cyclic_offset_v1",
  "schema_version": "1",
  "selected_offset": 1,
  "stratum_key": ["<component>"]
}
```

`canonical_focal_task_ids` and `donor_by_task` use canonical focal order;
`cycle_order` uses the HMAC order above. `offset_trials` is exactly every
integer offset from 1 through `selected_offset`. `failure_code` is
`"same_lineage"` or `"reciprocal_two_cycle"` for an invalid offset and is
`null` exactly for the selected valid offset; an invalid offset reports the
first violation under the check order above. If no offset is valid, ledger
creation fails and no partial proof is published.

Both evidence arms are serialized with the same strict canonical-JSON contract.
Every problem is stored at
`blobs/matching/problem/{problem_sha256}.json`, every solution at
`blobs/matching/solution/{solution_sha256}.json`, every signed invocation at
`blobs/matching/invocation/{invocation_sha256}.json`, and every proof at
`blobs/matching/proof/{proof_sha256}.json`; the brace value is the lowercase
SHA-256 of the exact canonical bytes. Problems, solutions, invocations, and
proofs may be written idempotently before publication; a byte-identical existing
CAS object is accepted, while a mismatch rejects. The ledger is written last
and is the sole scientific publication/visibility point. A crash may leave
unreachable immutable blobs; they are not authority, are omitted from the later
artifact-root traversal, and may be removed by reachability GC.

Proofs use
`application/vnd.pneuma.assignment-matching-proof+json`. The ledger's ordered
`matching_proof_refs` is unique, may be empty only when every task is
no-trigger, and otherwise contains exactly one proof per triggered stratum in
canonical stratum order; every matched receipt names its stratum proof. Unkeyed
artifact-root verification parses the closed proof/problem/solution/invocation
grammars, verifies every runner signature, follows only ledger-reachable refs,
and requires their digest-derived paths and complete root-entry reachability.
It rejects a matching-role entry included in the sealed root but not reachable
from the ledger; it does not directory-glob or treat an unreachable on-disk CAS
orphan as published.
It checks ancestry, coverage, status grammar, permutation, self/same-lineage
edges, reciprocal two-cycles, fixed-edge consistency, and the claimed integer
objective from persisted public costs. It never opens a secret handle/backend
session, so it cannot claim keyed ordering or reconstruction.

`require_assignment_reconstruction` performs that stronger audit. It opens the
fresh purpose-bound secret handle once, independently verifies the commitment
and derives the four assignment subkeys, reconstructs the allowlisted view with
the pinned normalizer/tokenizer, and recomputes donor HMAC order, candidate or
offset trials, allocation, orientation, and capabilities. Triggered
confirmation also requires a fresh registry-opened backend session, reproduces
the canonical solve sequence, checks its signed invocations, then closes it;
all-no-trigger confirmation and every synthetic audit require no session. It
rejects `FEASIBLE`, timeout, nonzero gap, candidate omission, changed mapping or
objective, skipped candidate/offset, relaxed feature, cross-mode proof
relabeling, or any mismatch with the ledger and reachable proof graph.

Every selected-schedule task has exactly one donor receipt. `matched` is mandatory exactly
for triggered tasks and carries the complete non-empty candidate list plus
proof; `not_applicable_no_trigger` is mandatory exactly for no-trigger tasks
and forbids donor/candidate/cost/fallback/proof/packet fields. Modify
`TaskAssignment` so donor ID/lineage may be `None` only when its matching kind
is N/A: `matched` requires both non-null and distinct task/lineage, while
`not_applicable_no_trigger` requires both null. There is no inference from null
alone or from trigger text outside the typed receipt.
`require_confirmation_assignment` is only a thin wrapper around
`require_assignment_reconstruction`: it additionally requires confirmation
mode/algorithm and otherwise adds no second reconstruction path. The optional
`verify_result_bundle` orchestrator runs keyed reconstruction, verifies both
transaction-specific storage attestations, then runs unkeyed artifact-root
verification; it never serializes a handle, a subkey, or a reconstructed
clear mapping.

### Step 6: Harden the Task-2 schemas and ancestry writer

Make the schema table in Task 2 executable:

- replace manifest `seed_commitment_sha256` with the constant ceremony name and
  three named commitments;
- require the closed task-registry, roster, conditional eligibility,
  qualification/ceremony chain, assignment-program, provider-lane,
  storage-policy/evidence, runtime, normalizer, verifier-feature,
  build/backend/KAT, and invocation grammars and canonicalize only their
  explicitly semantic-set arrays before copying;
- remove schedule copies of assignment-program/provider-plan refs; those assets
  load only through `manifest_ref`;
- set `minItems: 1` on schedule tasks, prefix receipts, assignments,
  allocations, donor receipts, and matched candidate arrays;
- make `matching_proof_refs` a unique array, empty iff there are no triggered
  tasks and otherwise exactly one ref per triggered matching stratum;
- make assignment mode and matching algorithms enums;
- add closed matched/N/A donor-receipt `oneOf` definitions and forbid donor
  fields on N/A;
- reject precomputed band/fallback-availability fields from the prefix view,
  and parse every matching-proof/problem/solution/invocation blob against its
  closed canonical grammar while following its nested ArtifactRefs/signatures;
- require every normalizer/backend implementation ArtifactRef to byte-equal one
  manifest `source_revision_ref`, every matching ref path to equal its
  content-digest path, and every matching root entry to be ledger-reachable;
- validate the manifest-pinned storage contract/evidence and the two closed
  operational receipt arms before either scientific publication; each receipt
  embeds one fsynced `StorageTransactionIntent` binding the lease ID, begin,
  strictly ordered renewal, non-releasing end, consecutive generations,
  unexpired transitions, exact prepared scientific path/digest, and final
  generation/expiry; then embeds one mode-valid
  `StoragePublicationCommit` binding that exact intent and science with a fresh
  unique registry commit ID/time, durable consumed state, and required release
  cleanup; requires its registry signature for confirmation and its exact closed
  local-test arm only for synthetic tests; accepts only the exact
  scientific-plus-fixed-receipt pair, permits
  proof-only deterministic finalization after commit, forbids recovery commit
  before it, and keeps intents/receipts/root identity outside scientific
  closure;
- require manifest/schedule/prefix/program/key/view/proof ancestry in the
  assignment ledger; and
- make `validate_record_ancestry`, `write_record`, and artifact-root
  verification enforce nested record kinds/digests, exact selected-schedule/
  trigger coverage, the chronology from Task 2, and the unkeyed-only root audit;
  keyed ordering/allocation/capability reconstruction remains exclusively in
  `require_assignment_reconstruction`.

Do not create a thirteenth scientific record kind or schema. The operational
intent/commit/receipt types stay outside scientific closure, and the matching
solver transcript remains a referenced blob under the assignment ledger.

### Step 7: Prove green

```console
.venv/bin/python -m pytest tests/resampling_null/test_types.py tests/resampling_null/test_preflight.py tests/resampling_null/test_assignment.py tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q
```

Expected: pass.

### Step 8: Close Task 3 without an omnibus commit

```console
git diff --check
git status --short
```

Expected: both commands produce no output after the eleven reviewed slice
commits. Do not create a catch-all Task-3 commit. A closure repair reopens the
owning slice, repeats its focused RED/GREEN/static/review gate, and receives a
small scope-matched commit before this check repeats.

## Task 4: Token-exact REAL/SHAM packet construction

### DL-135 closure repair: packet audits must recompute, not reread claims

The original Task-4 signatures below are superseded where they permit
caller-supplied `VerifierFinding`, identifier-map, pad-unit, policy, template,
tokenizer, or focal-collision values to become a sealed audit result merely
because a receipt repeats them. Candidate publication may record such a
proposal, but triggered sealing fails closed until all of the following
normative repair is implemented:

1. A registered, manifest-pinned packet normalizer loads the focal and donor
   verifier ArtifactRefs from the sealed prefix index and emits compact
   canonical `packet_normalized_findings_v1` blobs. Each blob contains its
   exact source verifier ref, task ID, closed normalizer ID/version, and ordered
   typed atoms. Synthetic support is a named fixture implementation;
   confirmation remains unavailable until separately reviewed SWE and tau
   normalizer adapters exist. A structural caller-supplied normalizer is
   forbidden.
2. The identifier map is a compact canonical
   `packet_identifier_map_v1` blob with focal/donor task IDs and a UTF-8
   byte-ordered complete list of typed source/destination atoms. The audit
   reloads it, proves source coverage and one-to-one type preservation, applies
   it to the normalized donor bytes, and reproduces the normalized SHAM bytes.
3. `PacketPairReceipt` gains `normalized_donor_ref`; the existing
   `normalized_real_ref` and `normalized_sham_ref` name distinct canonical
   pre-template artifacts, never aliases of encrypted packet text. Packet
   construction loads these refs from `run_root`; it no longer accepts naked
   finding sequences as scientific authority.
4. Packet policy, pad units, and template are closed compact canonical blobs
   named `packet_policy_v1`, `packet_pad_units_v1`, and `packet_template_v1`.
   The builder and audit reload their exact referenced bytes. A pad set is an
   ordered list of nonempty neutral strings; a template fixes the record kind,
   exact field order, and canonical compact-JSON renderer. Caller values must
   byte-equal these parents or fail.
5. The tokenizer ref selects a closed internal registry entry. Synthetic
   `unicode_codepoint_fixture_v1` is permitted for fixtures. Confirmation must
   pin tokenizer JSON/model/config digests and a reviewed loader before use.
   Both builder and independent audit reconstruct the tokenizer from the ref
   and re-encode the persisted plaintext inside the trusted audit boundary;
   a bring-your-own tokenizer object is not audit authority.
6. True-focal signatures are derived exhaustively from the normalized focal
   artifact. The audit independently regenerates REAL and SHAM rows,
   truncation receipts, identifier rewrites, collision signatures, deterministic
   padding search, rendered bytes, token IDs/counts, field/severity multisets,
   and every receipt field, then requires byte equality with the candidate and
   referenced artifacts. It never promotes claimed booleans by inspection.
7. Production packet ciphertext verification occurs through a trusted
   decrypt-for-audit capability that returns plaintext only inside this
   transaction; synthetic fixtures may use ignored plaintext. The candidate
   process cannot mint the audit capability, and no branch starts until the
   independently reconstructed sealed index exists.

Until this repair is complete, `audit_and_seal_packet_index` may seal only an
all-no-trigger schedule, for which packet-specific gates are vacuous and exact
typed marker/roster/ancestry/config-byte closure is directly recomputable.
Triggered candidates are non-authoritative and must be rejected. This
restriction is a scientific boundary, not a missing unit test.

For Task 4, verification is one narrow behavior command and one source-static
command per reviewable slice, each hard-capped at 60 seconds. Broad suites,
coverage targets, and test-framework work are forbidden absent a concrete
shared-surface failure mode. Scientific manipulation/falsification experiments
remain separate research work and are not reduced by this software-test cap.

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
- candidate audit proves every triggered pair's focal/donor verifier reference
  belongs to the sealed prefix index and every tokenizer/pad/template ref
  matches its parent;
- a no-intervention task is selected-schedule-covered by a typed marker and has no packet
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
verifies exact selected-schedule coverage,
one focal/donor pair per triggered task, one typed no-intervention marker per
no-trigger task, assignment/prefix/verifier ancestry, token and
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

### DL-136 Task-5 authority amendment

The original Task-5 record sketch and protocol fragments below are historical
where they conflict with this amendment. They could dispatch a deterministic
fixture, but they could not prove schedule ancestry, provider use/cost,
earliest-trigger semantics, complete snapshots, verified content addressing,
or clone isolation. Implement the corrected authority in the following
reviewable slices:

1. **T5-S02A — execution authority:** upgrade the manifest-pinned
   `provider_lane_plan_v2` grammar and schedule loader; derive caps and exact
   subject/simulator/meter contracts from `schedule_ref`, never a naked caller
   value.
2. **T5-S02B — verified evidence primitives:** add exact provider-attempt and
   tool-boundary receipts, a read-after-write verified create-only CAS, the
   composite snapshot envelope, and the amended pre-release
   `resampling-prefix-receipt` v0.1.0 schema.
3. **T5-S02C — prefix engine:** implement the controller-owned subject,
   simulator, tool, cap, terminal, snapshot, clone-grade, and clone-verify
   transaction against closed synthetic adapters.
4. **T5-S02D — prefix publication:** independently reload every parent and raw
   artifact, verify exact selected-schedule coverage and chronology, and seal
   the prefix index before assignment or packet construction.

### DL-139 T5-S02C executable synthetic authority

DL-139 hardens DL-136--DL-138 for the prefix engine only. All historical Task-5
prose below is superseded where it permits confirmation execution, caller-owned
codecs or stores, logical clone identities, self-reported time/status/cost, or
prefix-index publication during S02C. T5-S02C is
`schedule_authority == "synthetic_validation"` only. It may execute exact local
deterministic fixture calls, but never a provider/model/network call, credential
use, spend, scientific experiment, branch, assignment, packet construction,
prefix-index seal, empirical result, or claim. Its only successful return is
one `prefix_candidate_receipt` ArtifactRef whose wrapper contains the validated
`FrozenPrefixReceipt` mapping. T5-S02D must independently reopen it and every reachable parent/raw blob, verify exact
selected-schedule coverage, order, caps, cost, and chronology, and alone seal a
`PrefixIndex`.

Implement S02C in four separately reviewable internal slices:

1. **S02C-a — contracts, source provenance, and idempotent CAS:** extend typed
   execution authority, close the synthetic program and raw-observation
   grammars, bind reviewed implementation-source bytes, and harden
   `ControllerArtifactStore` for verified idempotent reuse.
2. **S02C-b — initial restore and OS identities:** implement exact
   subprocess-backed fixture environments, controller-created/fstat-bound
   writable roots, pairwise process/root isolation, and the initial
   qualification receipt.
3. **S02C-c — provider/simulator/tool loop:** implement controller rendering,
   tokenization, dispatch/attempt evidence, clock/cap precedence, independently
   observed tool state, trigger selection, and zero-cost settlement.
4. **S02C-d — final snapshot and clone transactions:** build the composite
   snapshot, perform fresh grade/verifier restores, write the candidate receipt,
   close the store, construct a fresh resolver, and reload every referenced
   controller artifact before returning. Prefix publication remains S02D.

The only executable entry point is:

```python
def run_prefix(
    *,
    run_root: Path,
    schedule_ref: ArtifactRef,
    task_id: str,
) -> ArtifactRef:
    ...
```

There are no fixture arguments. The controller internally constructs exact
registered `@final` synthetic environment, subject, optional simulator, and a
fresh zero-position meter from verified descriptors plus sealed program bytes;
subclasses, structural substitutes, dynamic plugins, hidden caller
configuration, and confirmation types are unreachable. `run_prefix` constructs
the exact final `ControllerArtifactStore` itself. It accepts no fixture, store,
loader, parser, tokenizer, renderer, grader, verifier, event codec, settlement
codec, task script, cap, or contract value.
The tokenizer, request renderer, response/tool parser, grade/verifier codecs,
provider-event codec, and settlement codec are instantiated internally from a
closed in-module registry keyed by sealed typed contract descriptors; unknown
or duplicate keys reject. The store is closed exactly once after the complete
candidate graph is materialized. Only then does `run_prefix` construct the
exact final `ControllerArtifactResolver` and reload the canonical candidate
wrapper plus every reachable controller artifact, including idempotently reused
blobs, with independently supplied expected role/media/bytes before returning
the wrapper's `ArtifactRef`.

The internally constructed final fixtures have one minimal exact surface.
Subject and simulator expose only:

```python
invoke(
    *,
    request_bytes: bytes,
    dispatch_intent_sha256: str,
    subject_role: Literal["primary_subject", "user_simulator"],
    call_index: int,
    seed: int,
    model_contract_sha256: str,
    remaining_caps: CallContractCaps,
    absolute_deadline_ms: int,
) -> RawProviderObservation
```

The meter exposes only `read(*, label: str, program_sha256: str) -> int` and
must consume the next sealed trace row. The factory exposes only
`command(*, task_input_bytes: bytes, program_bytes: bytes) ->
tuple[str, ...]` and `bind(*, process: subprocess.Popen[bytes], ipc:
ControllerEnvironmentIPC, writable_root_fd: int, instance_ordinal: int) ->
SyntheticEnvironmentHandle`. The controller creates and fstats the root,
directly spawns and retains the real `subprocess.Popen`, owns both ends of the
IPC contract, and passes those controller-owned objects into `bind`; the
factory never spawns or supplies a PID/root identity. The handle's closed
operations are `start()`,
`snapshot() -> bytes`, `restore(snapshot_bytes)`, `visible_context() -> bytes`,
`append_assistant_turn(SubjectTurn)`,
`append_simulator_turn(SubjectTurn)`,
`execute_tool(ToolCall) -> (call_id, result_bytes)`, the four separate state
queries `mutation_committed()`,
`verifier_eligible()`, `episode_terminal()`, and `failure_kind()`,
`terminate(FailureKind, tuple[ToolCall, ...])`, `grade() -> bytes`,
`verify() -> bytes`, and `close()`. The two append methods cannot cross roles,
and terminate receives the exact controller-owned pending queue it must
preserve. No operation accepts a store/ref, supplies counters/time, or combines
execution with the independent state queries. Each constructed factory,
subject, simulator, and meter contains frozen `program_bytes` and
`program_sha256`; both must byte/digest-equal the resolved canonical synthetic
program before qualification, so exact type alone cannot hide caller-selected
state. The meter's sealed trace/program digest must match the same bytes.

`PrefixExecutionAuthority` additionally exposes exact
`schedule_authority`, the manifest `tokenizer_ref`, the complete ordered
`source_revision_refs`, and frozen/slotted typed implementation descriptors
for subject, optional simulator, parser, meter, environment factory, grader,
verifier, tokenizer, request renderer, provider-event codec, and settlement
codec. A descriptor contains exactly its purpose, fully-qualified
`nominal_type`, `build_id`, applicable request/response/snapshot/restore/raw-
evidence/event/settlement grammars, applicable `runtime_id` and
`container_digest`, and one explicit `implementation_source_ref`. The ref is a
manifest member and resolves the reviewed literal source bytes, not a prose
revision label. DL-140 defines the stable read and its deliberately limited
local-provenance interpretation. It is not execution attestation and cannot
authorize production, provider, model, network, confirmation, or a claim.

The selected `prefix_task_input_v1` contains exactly one required
`synthetic_execution_program_ref`; inline program alternatives are forbidden.
That ref has role `synthetic_execution_program`, media type
`application/json`, is copied and closed during manifest sealing, and resolves
a canonical `synthetic_prefix_program_v1`. It has exactly `record_kind`,
`schema_version`,
`expected_trigger_reason`, `tool_schema_ref`, one ordered
`provider_transcript`, ordered `tool_observations`, `grade_result`,
`verifier_result`, `failure_injection`, and `clock_trace`. Its tool-schema ref
must equal the selected subject/parser contract ref. The program pins all
response bytes, typed turns where conditionally required, tool behavior, raw
grade/verifier result bytes and decoded values, injected transport/parser/tool
failure point or exact `none`, and every named clock read. No caller script or
mutable iterator is accepted. A program expected to reach either branch
trigger must reference a canonical nonempty synthetic tool-schema object; an
empty schema, a response-named tool absent from it, or a trigger program with
no tool definition rejects before execution. `expected_trigger_reason` is
checked only after execution against the controller-derived trigger; it never
selects, advances, or overrides that trigger.

The provider fixture returns one closed value:

```python
class RawProviderCompletionKind(str, Enum):
    COMPLETED = "completed"
    TIMEOUT_NO_RESPONSE = "timeout_no_response"
    TIMEOUT_LATE_RESPONSE = "timeout_late_response"
    REFUSAL = "refusal"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_ERROR = "provider_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"


@dataclass(frozen=True, slots=True)
class RawProviderObservation:
    subject_role: Literal["primary_subject", "user_simulator"]
    call_index: int
    seed: int
    model_contract_sha256: str
    response_bytes: bytes | None
    typed_turn: SubjectTurn | None
    reported_output_token_ids: tuple[int, ...] | None
    reported_generated_tokens: int
    provider_event_bytes: bytes
    completion_kind: RawProviderCompletionKind
```

Role/index/seed/model digest must equal the published intent. Response bytes
and reported output IDs are both present or both absent; absent response
requires zero reported tokens and no typed turn. For every full response the
controller tokenizes the raw bytes and attempts the sealed parser. Parser
success requires a typed turn and byte-for-byte equality of the full exact
`SubjectTurn`, including text, ordered queue, generated count, and finish
reason; parser failure requires no typed turn. Reported token IDs/count must
equal controller reconstruction but never become authority. The controller
derives terminal attempt status from response presence, parser/refusal grammar,
validated transport event, and observed clock. The fixture's
`completion_kind` is only a consistency claim and cannot override those bytes.
The controller renders and tokenizes the request, writes request/input-token
bytes and `ProviderDispatchIntent`, and verifies them before invoking the
fixture.

The synthetic meter is a sealed named trace of exact `(label, uint64_ms)`
observations. Initial snapshot/restore qualification consumes no prefix time.
Immediately after it succeeds, exactly one `prefix_epoch` observation begins
the prefix. Subsequent labels and values must match the program in order with
no missing or extra read and must be monotonically nondecreasing. Computing
`absolute_deadline_ms = prefix_epoch + prefix_caps.wall_clock_ms` uses checked
uint64 arithmetic; overflow rejects the candidate. Before any provider,
simulator, or tool action, `now >= absolute_deadline_ms` forbids starting it.
An action completing at the deadline is on time; completion greater than the
deadline is late and terminates as `TIMEOUT`. Grade and verifier transactions
occur after the final prefix observation and consume no prefix wall allowance.
Controller counters use observed `max(0, completion - prefix_epoch)`. Remaining
allowance is always `max(0, cap - used)`; overshoot is preserved in `used`, so
`used + remaining == cap` is not required.

`FailureKind` adds exact `MODEL_CALL_CAP` and `TURN_CAP` members. The failure
mapping is closed: either role exhausting generated output is `TOKEN_CAP`;
either role exhausting its aggregate model-call ceiling is `MODEL_CALL_CAP`;
either role exhausting its aggregate turn ceiling is `TURN_CAP`; the primary
subject exhausting completed subject-issued tool calls is `TOOL_CAP`; a
deadline violation is `TIMEOUT`; validated refusal/parser/model/transport
failures map respectively to `REFUSAL`, `MALFORMED_ACTION`, `MODEL`, or
`INFRASTRUCTURE`. There is no retry. DL-140 defines the exact inclusive
pre-action cap and post-completion precedence; in particular, discrete-cap
equality never invalidates an admitted action or precedes its resulting
trigger. An initially clean terminal environment may return a natural
no-trigger candidate with zero provider attempts. Model calls count at
dispatch; generated tokens count every controller-tokenized received byte
sequence; turns count only parser-valid typed turns, including a parser-valid
refusal. Completion exactly at the deadline remains admissible for an observed
terminal state or trigger; if neither occurs, the next action is forbidden and
the controller terminates with `TIMEOUT`.

The controller owns one exact
`terminate(failure_kind, pending_queue)` transition for adverse nonterminal
state. It freezes the last verified environment state, sets
`episode_terminal = true`, preserves the actual non-`none` failure, clears
`branch_pending_calls`, and copies the known unexecuted queue in order to
`terminal_unexecuted_remainder`; an unknown queue yields an empty remainder.
Consequently an exact terminal remainder is legal for any adverse stop with a
known queue, not only malformed action. Natural clean termination requires
`FailureKind.NONE` and an empty remainder. A branch trigger requires nonterminal
state and an empty terminal remainder.

Initial restore qualification is reachable only through a new required
`CompositeSnapshotEnvelope.initial_restore_qualification_ref`; duplicating that
edge directly on the outer candidate is forbidden:

```python
@dataclass(frozen=True, slots=True)
class EnvironmentProcessIdentity:
    instance_ordinal: int
    writable_root_relative_path: str
    writable_root_st_dev: int
    writable_root_st_ino: int
    child_pid: int


@dataclass(frozen=True, slots=True)
class InitialRestoreQualificationReceipt:
    schedule_ref: ArtifactRef
    task_ref: ArtifactRef
    task_input_ref: ArtifactRef
    environment_contract_ref: ArtifactRef
    isolation_contract_ref: ArtifactRef
    initial_environment_snapshot_ref: ArtifactRef
    observed_resnapshot_sha256: str
    observed_resnapshot_byte_count: int
    visible_context_ref: ArtifactRef
    visible_sha256: str
    token_ids_ref: ArtifactRef
    token_ids_sha256: str
    branch_pending_calls: tuple[ToolCall, ...]
    terminal_unexecuted_remainder: tuple[ToolCall, ...]
    episode_terminal: bool
    failure_kind: FailureKind
    live_identity: EnvironmentProcessIdentity
    fresh_restore_identity: EnvironmentProcessIdentity
    verified: Literal[True]
```

It byte-binds the initial snapshot to the fresh observed resnapshot, repeats
and verifies visible/token digests, queues, terminal/failure state, and records
both controller-observed identities. The controller fresh-validates exact
resnapshot bytes, not digest/length alone. A verified qualification requires
`failure_kind is FailureKind.NONE`; a clean terminal state is allowed.
Qualification failure is pipeline-invalid and returns no candidate.

Every clone transaction uses:

```python
@dataclass(frozen=True, slots=True)
class SnapshotRestoreReceipt:
    purpose: Literal["grade", "verify"]
    schedule_ref: ArtifactRef
    task_ref: ArtifactRef
    task_input_ref: ArtifactRef
    environment_contract_ref: ArtifactRef
    isolation_contract_ref: ArtifactRef
    composite_snapshot_ref: ArtifactRef
    environment_snapshot_ref: ArtifactRef
    observed_resnapshot_sha256: str
    observed_resnapshot_byte_count: int
    branch_pending_calls: tuple[ToolCall, ...]
    terminal_unexecuted_remainder: tuple[ToolCall, ...]
    visible_context_ref: ArtifactRef
    visible_sha256: str
    token_ids_ref: ArtifactRef
    token_ids_sha256: str
    episode_terminal: bool
    failure_kind: FailureKind
    restored_identity: EnvironmentProcessIdentity
    verified: Literal[True]


@dataclass(frozen=True, slots=True)
class GradeExecutionReceipt:
    restore_receipt_ref: ArtifactRef
    grade_evidence_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class VerifierExecutionReceipt:
    restore_receipt_ref: ArtifactRef
    verifier_evidence_ref: ArtifactRef
```

The grade execution receipt parents the purpose-`grade`
`SnapshotRestoreReceipt` and direct raw grade evidence; the verifier execution
receipt parents the purpose-`verify` restore receipt and direct raw verifier
evidence. Every repeated ancestry/state field must equal the composite
snapshot. `EnvironmentProcessIdentity` is controller-created evidence, never a
fixture string: it contains an exact controller-assigned instance ordinal, a
controller-created root-confined writable-root path, root `fstat` device and
inode, and the real child PID observed by the controller from its own
`subprocess.Popen`. The ordinal, device, inode, and PID are exact nonnegative
integers, with PID positive; the root is one nonempty normalized relative path
confined under the controller-created environment-root directory. The
controller directly spawns each subprocess-backed fixture. The live,
initial-restore, grade, and verifier environments must remain pairwise
distinct by object, PID, and `(st_dev, st_ino)` through all checks; logical IDs
alone are invalid, and no process/root may exit or alias before its last
observation.

The exact tool fixture `execute_tool` returns only executed call ID and raw
result bytes. After it returns, the controller independently queries the
source-provenanced environment for mutation committed, verifier eligibility,
terminal state, and failure kind, and samples the meter for elapsed time. The
controller then builds the canonical tool-result and boundary records; a
fixture-returned boundary/counter/elapsed claim is forbidden. Tool-call/result
order and IDs must equal the parser-produced queue and sealed synthetic
program.

Synthetic provider events use compact canonical
`synthetic_provider_event_v1` JSON with exactly `schema_version`,
`subject_role`, `call_index`, `seed`, `model_contract_sha256`,
`dispatch_intent_sha256`, `completion_kind`, nullable `response_sha256`,
`observed_at_ms`, and `cost_microunits = 0`. After the attempt is stored, its
settlement uses compact canonical `synthetic_provider_settlement_v1` JSON with
exactly `schema_version`, the same role/index/seed,
`dispatch_intent_sha256`, `attempt_sha256`, `provider_event_sha256`,
`final = true`, `currency = "synthetic_microunit"`, and
`cost_microunits = 0`. This acyclic pair binds intent, event, attempt, finality,
and exact zero cost. Any nonempty attempt ledger requires
`AttemptBoundZeroCostClosure`; the zero-attempt closure is legal only when no
dispatch intent exists.

`ControllerArtifactStore.write` remains create-exclusive but treats `EEXIST`
as a verified idempotent-reuse path, never as permission to overwrite. It
independently reopens the existing role/digest path with no-follow flags and
verifies canonical role/media, path, regular-file identity, hash, length, and
exact bytes before returning the one exact `ArtifactRef`. Any mismatch,
unexpected collision, unsafe identity, or reopen/read/close failure rejects;
canonical role has exactly one DL-138 media type, so caller metadata cannot
invent an alternate media binding. The pre-existing blob is never unlinked.
The DL-138 post-create cleanup and
error aggregation remain mandatory only for a blob newly created by the
current call.

Prioritized RED tests for S02C are:

1. **P0 authority/source:** reject non-synthetic schedules; injected codecs,
   stores, scripts, subclasses, wrong exact types/builds, source-byte drift,
   unknown registry keys, empty trigger tool schema, or confirmation paths.
2. **P0 identity/restore:** reject logical or caller PID/root claims, aliased
   object/PID/inode across live/initial/grade/verifier environments, altered
   resnapshot/state/queue/visible/token bytes, missing initial-only snapshot
   edge, or grade/verifier purpose/ancestry cross-wire.
3. **P0 provider/status:** reject request-before-intent order, role/index/seed/
   model mismatch, reported-token drift, full parsed turn/text/queue mismatch,
   trusted completion kind, response/status nullability violations, retries,
   unbound/nonfinal/nonzero settlements, or zero-attempt closure after dispatch.
4. **P0 clock/caps/trigger:** reject missing/reordered/decreasing clock labels,
   uint64 deadline overflow, action start at deadline, completion-after-deadline
   acceptance, grade/verify time charged to prefix, equality-forced overshoot,
   wrong role-local model/turn/token/tool failure, or trigger chosen before
   failure/terminal/deadline.
5. **P0 terminal/tool:** accept clean initial terminal with zero attempts and
   preserve any known queue for every adverse stop; reject silent queue loss,
   forced `MALFORMED_ACTION`, environment-returned boundary claims, mismatched
   executed call IDs/results, or trigger before a completed observed boundary.
6. **P1 CAS/candidate boundary:** accept exact EEXIST reuse; reject same-path
   role/media/bytes/hash/length/identity mismatch without deleting the existing
   blob; preserve DL-138 cleanup for new creates; reject return before
   store-close/fresh-resolve of every reachable artifact; prove S02C emits no
   prefix index, assignment, packet, branch, provider/network/spend, or claim.

### DL-140 T5-S02C review-rejection repair

DL-140 hardens DL-139 where its first executable draft remained ambiguous or
wrong. It supersedes every conflicting S02C statement above or below, without
changing the no-confirmation/no-network/no-spend/no-publication boundary.

#### Inclusive caps and trigger precedence

Discrete model-call, parsed-turn, and completed-tool caps are inclusive maxima.
Immediately before an action that consumes one discrete dimension,
`used >= cap` blocks that next same-dimension action with
`MODEL_CALL_CAP`, `TURN_CAP`, or `TOOL_CAP`. An action admitted at
`used < cap` remains valid when its completion increments usage to exactly the
cap. There is no post-completion discrete-cap failure. Only generated-token and
wall-time dimensions can newly overshoot because the controller cannot know
their final usage before the call completes; equality is valid and only
`used > cap` fails.

After a provider observation, raw/typed consistency and explicit provider
failure are resolved first, followed by environment terminal state,
deadline/wall overshoot, token overshoot, and only then append/continuation.
After a completed tool, precedence is exact: explicit tool failure,
environment terminal state, deadline/wall overshoot, token overshoot, then the
earliest trigger predicate. Model/turn exhaustion is checked only before the
next model dispatch and cannot block already queued tool execution. Tool
exhaustion is checked only before the next tool execution. Thus completed tool
number four is valid at equality and yields `FOURTH_TOOL_CALL` when no earlier
failure, terminal state, deadline/token/wall overshoot, or eligible-mutation
trigger wins.

Required RED cases prove: model/turn equality accepts the current response but
blocks the next same-role dispatch; token/wall equality is valid while
overshoot terminates; tool number four triggers at a cap of four; a fifth tool
is blocked; queued tools still execute after model/turn equality; and explicit
failure, terminal state, or wall/token overshoot on boundary four prevents a
trigger.

#### Immutable candidate handoff

S02C never returns an in-memory `FrozenPrefixReceipt`. After runtime validation,
it stores compact canonical `application/json` bytes under role
`prefix_candidate_receipt`. The object has exactly
`record_kind = "frozen_prefix_candidate_v1"`, `schema_version = "1"`, and a
`receipt` JSON object containing the canonical field-for-field mapping emitted
from the exact runtime `FrozenPrefixReceipt`. That object must decode through
the same exact runtime mapping validator used by prefix artifacts; a parallel
weaker mapping grammar is forbidden. `run_prefix` closes the store, creates a
fresh resolver, reloads the wrapper and every recursively reachable raw/JSON
artifact, redecodes the wrapper, and returns only the wrapper `ArtifactRef`.

S02D exposes:

```python
def seal_prefix_index(
    *,
    run_root: Path,
    schedule_ref: ArtifactRef,
    candidate_refs: tuple[ArtifactRef, ...],
) -> ArtifactRef:
    ...
```

It accepts only unique `prefix_candidate_receipt` refs in exact selected-
schedule task order. It independently fresh-resolves and decodes every wrapper
and graph, checks one candidate per selected task, exact roster coverage/order,
schedule ancestry, chronology, caps, trigger, restore isolation, and settled
cost, embeds the decoded receipts into the `PrefixIndex`, and alone publishes
the index. A naked in-memory receipt, missing/extra/reordered candidate, or S02C
attempt to write an index rejects.

#### One controller-derived actor transcript

The synthetic program has one ordered `provider_transcript`; separate primary
and simulator arrays are forbidden. Each row includes its role, but role is
post-derivation consistency only. The environment handle adds the independent
controller query `simulator_context() -> bytes | None`. Before each model
dispatch the controller queries it: non-null context requires the optional
simulator actor and null context requires the primary subject. A non-null
context without a sealed simulator contract is pipeline-invalid. The
controller renders the derived actor's request, checks the next transcript row
role, intent identity, expected canonical request bytes/digest, and exact input
token IDs, then dispatches.

The state machine is:

1. query failure/terminal state and stop if present;
2. query simulator context and derive the actor;
3. apply only that actor's token/model/turn pre-dispatch allowances;
4. publish and verify request, tokens, seed, and intent;
5. invoke once and validate the full observation before any environment
   mutation;
6. for a simulator turn, require `tool_calls == ()`, append only through
   `append_simulator_turn`, then restart at step 1;
7. for a primary turn, append only through `append_assistant_turn`, execute its
   ordered tool queue under tool/wall checks and boundary precedence, then
   restart at step 1 when no trigger/termination occurs.

Simulator and primary role-local call indexes, model calls, parsed turns,
generated tokens, aggregate/per-call caps, and seeds remain separate. Simulator
tool calls are always pipeline-invalid. A transcript role never chooses the
actor, and either append method receiving the wrong derived role rejects.

#### No caller fixture state

The sole entry remains:

```python
def run_prefix(
    *,
    run_root: Path,
    schedule_ref: ArtifactRef,
    task_id: str,
) -> ArtifactRef:
    ...
```

After loading authority and program bytes, a closed internal registry constructs
the exact factory/handle binder, subject, optional simulator, fresh
zero-position meter, tokenizer, renderer, parser, grader, verifier,
provider-event codec, and settlement codec. There is no caller object or
configuration seam. Every constructed stateful fixture starts at transcript/
clock position zero and binds the same program bytes/digest.

#### Source provenance, not execution attestation

Every executable registry key is one exact:

```python
@dataclass(frozen=True, slots=True)
class ImplementationDescriptor:
    purpose: Literal[
        "environment",
        "subject",
        "simulator",
        "meter",
        "tokenizer",
        "request_renderer",
        "response_parser",
        "grader",
        "verifier",
        "provider_event_codec",
        "settlement_codec",
    ]
    nominal_type: str
    build_id: str
    request_grammar: str | None
    response_grammar: str | None
    snapshot_grammar: str | None
    restore_grammar: str | None
    evidence_grammar: str | None
    runtime_id: str | None
    container_digest: str | None
    implementation_source_ref: ArtifactRef
```

The internal registry is a closed one-to-one mapping from the full descriptor
value to one exact final constructor; duplicate, unknown, or nullable-required
fields reject. `implementation_source_ref` is role `source_revision`, is a
manifest member, and resolves literal reviewed source bytes. For each
descriptor the controller opens the ref and the registered local source path
through held root dirfds with `O_NOFOLLOW`, requires regular files, records
pre-read `fstat`, reads from the stable fd, records post-read `fstat`, and
requires unchanged device/inode/size/mtime plus exact ref byte/hash/length
equality. It repeats the local source read/identity comparison immediately
after the last use and before candidate return; any change after import or
either read fails.

This is cooperative-local source provenance under an explicit no-concurrent-
mutation assumption. It does not prove Python code-object identity, imported
bytecode identity, or deployed execution identity, and cannot authorize
confirmation, production, a provider/model/network call, an empirical result,
or a claim.

#### Controller-owned process and root lifecycle

The controller opens one operational environment-workspace directory through
held no-follow dirfds. For each live, initial-restore, grade, and verifier
instance it allocates a unique normalized child name by bounded deterministic
suffix search and `mkdirat` create-exclusive semantics. `EEXIST` means stale:
the controller never opens, mutates, cleans, or reuses that root and tries the
next suffix; exhaustion rejects. It opens/fstats each newly created root and
keeps its fd.

The internal factory supplies only sealed command/binding logic. The controller
directly creates the IPC endpoints, spawns and retains the real
`subprocess.Popen`, observes `Popen.pid`, and binds the exact handle to those
controller-owned resources. All four root fds, processes, and IPC ownership
remain live through the final pairwise `(st_dev, st_ino)`, PID, object-identity,
and `poll() is None` checks. Receipts record those last observed identities.

Only after the final observation and candidate fresh-resolution does cleanup
close every handle/IPC endpoint once, terminate each still-live process, wait,
and escalate to kill/wait only under the closed local cleanup policy. It then
fstats each still-held root fd, requires its receipt identity, removes only
controller-created contents through that fd, removes the exact child through
the held parent dirfd, and closes root/workspace fds. Success and failure both
attempt every cleanup; the primary error plus all close/terminate/wait/kill/
root-cleanup errors are preserved in an `ExceptionGroup`. A cleanup failure
aborts return. Stale pre-existing roots are never opened or cleanup targets,
and no mutable root is retried.

#### Closed program and provider truth table

`prefix_task_input_v1.synthetic_execution_program_ref` is required exactly
once. It has role `synthetic_execution_program`, media type
`application/json`, and is copied, recursively closed, and byte-validated
during manifest sealing. Inline programs and optional alternatives reject.
The referenced compact canonical object has exactly:

```text
record_kind = "synthetic_prefix_program_v1"
schema_version = "1"
task_id
expected_trigger_reason
tool_schema_ref
provider_transcript
tool_observations
grade_result
verifier_result
failure_injection
clock_trace
```

Each ordered provider row closes role/index/seed/model-contract digest,
`expected_request_ref` with canonical request bytes,
`expected_request_sha256` equal to that ref, exact ordered
`expected_input_token_ids`, nullable response-bytes ref, conditional exact
typed turn, conditional reported output IDs/count, canonical provider-event
bytes, and completion-kind claim. All nested refs are manifest-copied and
closed. `expected_trigger_reason` is checked only after execution against the
controller-derived result; it never chooses or overrides an actor, action,
failure, terminal state, or trigger.

Decoded provider event transport kind is exactly one of `response`,
`provider_error`, `infrastructure_error`, or `timeout_no_response`; it records
`observed_at_ms`, which must equal the controller meter's named completion read.
The table's observed time is that controller read, never an event/client clock
claim. The parser result is exactly `turn`, `refusal`, `malformed`, or
`not_applicable`. Before any environment mutation the controller applies this
complete truth table:

| observed time | response | transport | parser | derived attempt |
|---|---:|---|---|---|
| `> deadline` | present | `response`, `provider_error`, or `infrastructure_error` | validated from bytes | `TIMEOUT_LATE_RESPONSE` |
| `> deadline` | absent | `provider_error`, `infrastructure_error`, or `timeout_no_response` | `not_applicable` | `TIMEOUT_NO_RESPONSE` |
| `<= deadline` | absent | `provider_error` | `not_applicable` | `PROVIDER_ERROR` |
| `<= deadline` | absent | `infrastructure_error` | `not_applicable` | `INFRASTRUCTURE_ERROR` |
| `<= deadline` | present | `provider_error` | validated from bytes | `PROVIDER_ERROR` |
| `<= deadline` | present | `infrastructure_error` | validated from bytes | `INFRASTRUCTURE_ERROR` |
| `<= deadline` | present | `response` | `refusal` | `REFUSAL` |
| `<= deadline` | present | `response` | `malformed` | `MALFORMED_RESPONSE` |
| `<= deadline` | present | `response` | `turn` | `COMPLETED` |

Every unlisted combination is pipeline-invalid. In particular
`timeout_no_response` observed at or before the deadline is inconsistent;
`response` transport without response bytes is invalid; and transport-timeout
with response bytes is invalid. “Validated from bytes” means exactly
`turn`, `refusal`, or `malformed` as the parser derives, never
`not_applicable`. Equality at the deadline is on time. Time
greater than the deadline dominates on-time refusal/parser/transport status,
while retaining every response, partial output, token, and event byte.

Response presence requires output-token IDs and a count reconstructed exactly
by the controller; absence requires both null and zero. Parser `turn` or
`refusal` requires the exact typed turn; `malformed` or `not_applicable`
requires it null. Text, finish reason, ordered queue, token IDs/count, request
bytes, input tokens, role/index/seed/model, event, and completion-kind claim
must all match controller derivation. Any mismatch is pipeline-invalid before
append/tool mutation. A simulator typed turn must have an empty tool queue.

Additional P0 RED cases cover candidate-wrapper role/media/schema/runtime
decode and S02D ordering; actor derivation against misleading transcript roles;
simulator-tool rejection and interleaving/cap isolation; absence of any caller
fixture seam; source change and descriptor/registry drift without execution-
attestation claims; stale-root skip, direct Popen ownership, liveness/alias and
cleanup aggregation; every truth-table row/unlisted combination; exact-
deadline on-time behavior; late-byte retention; and raw/typed mismatch before
environment mutation.

The corrected prefix entry adds:

```python
@dataclass(frozen=True, slots=True)
class ProviderDispatchIntent:
    subject_role: Literal["primary_subject", "user_simulator"]
    call_index: int
    seed: int
    request_ref: ArtifactRef
    input_token_ids_ref: ArtifactRef
    model_contract_ref: ArtifactRef
    absolute_deadline_ms: int


class ProviderAttemptStatus(str, Enum):
    COMPLETED = "completed"
    TIMEOUT_NO_RESPONSE = "timeout_no_response"
    TIMEOUT_LATE_RESPONSE = "timeout_late_response"
    REFUSAL = "refusal"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_ERROR = "provider_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"


@dataclass(frozen=True, slots=True)
class ProviderCallAttemptReceipt:
    dispatch_intent_ref: ArtifactRef
    subject_role: Literal["primary_subject", "user_simulator"]
    call_index: int
    seed: int
    status: ProviderAttemptStatus
    request_ref: ArtifactRef
    input_token_ids_ref: ArtifactRef
    response_ref: ArtifactRef | None
    output_token_ids_ref: ArtifactRef | None
    model_contract_ref: ArtifactRef
    generated_tokens: int
    elapsed_ms: int
    provider_event_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class CompletedToolBoundaryReceipt:
    call_id: str
    tool_call_ref: ArtifactRef
    tool_result_ref: ArtifactRef
    mutation_committed: bool
    verifier_eligible_after: bool
    episode_terminal: bool
    failure_kind: FailureKind
    elapsed_ms: int


@dataclass(frozen=True, slots=True)
class FrozenPrefixReceipt:
    task_id: str
    schedule_sha256: str
    prefix_caps: PrefixCaps
    snapshot_ref: ArtifactRef
    visible_context_ref: ArtifactRef
    visible_sha256: str
    token_ids_ref: ArtifactRef
    token_ids_sha256: str
    branch_pending_calls: tuple[ToolCall, ...]
    terminal_unexecuted_remainder: tuple[ToolCall, ...]
    trigger_reason: TriggerReason
    terminal_failure_kind: FailureKind
    y0_grade: GradeReceipt
    grade_execution_receipt_ref: ArtifactRef
    verifier_receipt: FrozenVerifierReceipt
    verifier_execution_receipt_ref: ArtifactRef
    counters: ResourceCounters
    simulator_counters: ResourceCounters
    call_seeds: tuple[CallSeedReceipt, ...]
    provider_attempts_ref: ArtifactRef
    boundary_ledger_ref: ArtifactRef
    provider_cost_ref: ArtifactRef
```

`counters.generated_tokens` and `counters.model_calls` count only primary
subject calls; `counters.tool_calls` counts completed subject-issued tool
calls; `counters.wall_clock_ms` is total controller-observed elapsed time and
therefore includes simulator and tool latency. `simulator_counters` separately
records simulator tokens/calls and repeats the same total elapsed wall value;
its tool-call count is zero. A cap, timeout, malformed response, refusal,
model failure, or infrastructure failure before an eligible boundary retains
the task as `no_intervention_opportunity` with the corresponding
`terminal_failure_kind`; ordinary clean termination uses `FailureKind.NONE`.
Natural no-trigger stores the clone-derived `Y_0` and copies it four times.
Adverse no-trigger retains raw clone grade and verifier evidence for audit,
but the controller constructs scientific `y0_grade.success = 0` and
`partial_reward = 0.0`; all four downstream outcomes copy that forced zero.
Such outcomes are never silently retried.
The existing `y0_grade.artifact_ref` and
`verifier_receipt.verifier_artifact_ref` remain direct refs to closed raw
`grade_evidence` and `verifier_evidence` bytes so downstream outcome and packet
consumers retain their approved semantics. The separate required
`grade_execution_receipt_ref` and `verifier_execution_receipt_ref` edges make
the snapshot-bound restore instance/process/writable-root receipts reachable
for independent S02D reconstruction. Trigger state is cross-bound to the
composite snapshot: `NO_INTERVENTION_OPPORTUNITY` requires
`episode_terminal == True`, while `FIRST_ELIGIBLE_MUTATION` and
`FOURTH_TOOL_CALL` require `episode_terminal == False`.

The authoritative entry point is the exact DL-139 signature above.

It byte-verifies and loads `schedule_ref`, follows the manifest's
`provider_lane_plan_v2`, selects exactly one task/lane, and internally obtains
the root seed, caps, exact task input, environment/restore/grader/verifier/
parser/isolation contracts, and exact model/meter contracts. Synthetic
execution accepts only closed named fixture implementations and byte-equal
fixture task inputs. S02C rejects confirmation authority and every structural
bring-your-own protocol.

The controller supplies each primary/simulator call with the remaining
role-specific allowance and an absolute deadline. The call returns the closed
raw response/token/provider observation, not request bytes or an `ArtifactRef`;
the controller writes it, reads it back, recomputes bytes/hash/length, and
constructs the attempt receipt. Before invocation it immutably publishes a
`ProviderDispatchIntent` containing role, next consecutive role-local index,
seed, request/input-token refs, model contract, and absolute deadline. The
terminal `ProviderCallAttemptReceipt` separately parents that intent and is
published exactly once after completion or failure. The closed status union
represents completed, refusal, malformed, provider-error,
infrastructure-error, timeout-without-response, and timeout-with-late-response
attempts; response/output refs are conditionally null only when no bytes
arrived. Partial bytes and partial usage remain referenced. The controller
re-tokenizes request and every available output with the pinned tokenizer and
derives token counts; it never trusts a client count. A returned seed, role,
index, model contract, usage, or token stream that differs from dispatch or
controller reconstruction rejects. A response observed after the deadline is
a timeout outcome even if cancellation was delayed. The generic
`call-seed-v1` frame remains authoritative for both roles: its root seed was
already derived from the schedule seed, task ID, and prefix/slot role, and the
receipt is bound to the exact schedule digest. This supersedes the older
τ³-only `tau-user-call-seed-v1` prose.

The pinned controller parser, not the environment, reconstructs the exact
ordered tool-call queue from raw provider response bytes and byte-compares it
with the typed calls. Omission, insertion, reorder, duplicate call ID, parser
drift blocks the prefix index as pipeline-invalid. Under DL-139, any adverse
terminal stop with a known unexecuted remainder retains it exactly in
`terminal_unexecuted_remainder` with the actual failure kind;
`branch_pending_calls` must be empty. On a branchable trigger,
`terminal_unexecuted_remainder` is empty and `branch_pending_calls` stores the
exact executable remainder. Work is never silently discarded.
The exact synthetic environment's `execute_tool` returns only raw result bytes
and executed `call_id`; the controller separately queries edge-local
`mutation_committed`, state-after `verifier_eligible_after`, explicit
`episode_terminal`, and failure kind, and derives elapsed evidence from the
meter. The controller owns `mutation_has_returned` and the cumulative
completed-tool count. After each validated completed result it
updates those values, then applies DL-140's explicit-failure, terminal,
deadline/wall-overshoot, and token-overshoot precedence, then triggers at the
first remaining nonterminal boundary where
`(mutation_has_returned and verifier_eligible_after)` or
`completed_tool_calls == 4`. The controller freezes the unexecuted queue in
exact order. A terminal boundary cannot leave branch-pending calls.
`EnvironmentAdapter.episode_terminal`
separately decides clean text-only termination; model `finish_reason` alone is
never task-terminal authority.
Every completed tool boundary with `failure_kind != NONE` must set
`episode_terminal == True`, and every terminal boundary must be the final
ledger entry. A failed nonterminal boundary and any boundary after failure are
invalid evidence, even when the ledger is otherwise chronological.

Primary and simulator model-call counters increment at dispatch, including a
failed or timed-out attempt. Generated-token counters include every
controller-tokenized partial/complete output token received. Completed-tool
counters increment only after a validated result boundary; attempted calls and
unexecuted pending calls remain derivable from the provider and boundary
ledgers. The controller applies DL-140's inclusive discrete-cap checks only
before the next same-dimension action and checks total elapsed time before and
after each boundary. Terminal or explicit provider/tool failure observed within
the deadline wins; only token/wall overshoot can newly fail after completion,
and an otherwise valid trigger is then evaluated before any next-action
discrete exhaustion. Crossing the absolute deadline always yields `TIMEOUT`.
Aggregate simulator token/call ceilings are exact fields in
`simulator_caps`; per-call caps cannot replace them. `FailureKind` includes the
closed `REFUSAL`, `MODEL_CALL_CAP`, and `TURN_CAP` members.

The composite snapshot is canonical controller-owned bytes with exactly:
schema version; study/task/schedule/task-input/environment/isolation refs;
environment snapshot ref; branch-pending-call array;
terminal-unexecuted-remainder array; visible-context ref and digest;
exact token-ID ref and digest; boundary-ledger ref; provider-attempt-ledger
ref; primary/simulator counters and remaining quotas; cumulative mutation and
terminal/failure state; subject/simulator stateless-attestation refs; and
runtime/container/source-revision refs. Every duplicated outer receipt field
must be byte-equal to its envelope field. Environment restore must reproduce
the environment bytes, pending queue, visible digest, token IDs, terminal
state, and all interaction-dependent simulator transcript/state/RNG.
Before the first provider dispatch, the controller must already have a
verified initial environment snapshot and fresh-restore receipt. Failure to
start, snapshot, or restore the selected canonical task is a pipeline-invalid
qualification failure, not a randomized task outcome; no prefix index,
assignment, or packet may seal. After that gate, provider/simulator/tool
failures can always freeze the last verified state and remain fixed-denominator
adverse outcomes. Their raw clone grade/verifier evidence remains referenced,
but only natural no-trigger may use the clone grade as scientific `Y_0`;
adverse no-trigger uses the forced-zero rule above.
Subject and simulator clients must be certified stateless across calls; all
interaction-dependent simulator transcript/state/RNG lives in the environment
snapshot. Each grade and verifier transaction creates a new environment from
the factory, records a distinct instance/process/root identity plus restore
receipt, restores and byte-verifies the same composite snapshot, checks visible
digest and exact token IDs, then emits closed raw `GradeEvidence` or
`VerifierEvidence` containing no ArtifactRef. The controller alone stores that
evidence and constructs `GradeReceipt`/`FrozenVerifierReceipt`. Exact
synthetic factories must return distinct objects with disjoint writable roots;
confirmation additionally supplies the manifest-pinned no-shared-writable-
state qualification. Returning the live object, a singleton, or a reused root
rejects.

`ControllerArtifactStore` is a concrete final local component: root-confined,
no-follow, create-exclusive, file-and-parent-fsynced, and incapable of
overwrite. S02C permits no substitute backend. After close, the controller
constructs a new resolver from the run root/manifest rather than accepting a caller loader;
it reopens every artifact and requires an independently supplied expected
role and expected media type plus exact path/hash/length/bytes equality.
Controller media authority is purpose-bound: canonical JSON records use
`application/json`; raw provider response, tool result, environment snapshot,
grade evidence, and verifier evidence use `application/octet-stream`.
Media types are already-canonical lowercase `type/subtype` tokens with no
parameters or whitespace; callers are rejected rather than normalized.
After create-exclusive publication begins, any write, sync, close, reopen,
read, stat, identity, or byte-verification failure makes the transaction
abort: all still-owned descriptors receive one close attempt, the digest file
is unlinked, the role directory is fsynced, and the primary plus every cleanup
failure is retained. A close that raises relinquishes ownership before the
attempt because the descriptor may already have closed and been reused; cleanup
reopens the role directory when necessary and never double-closes an uncertain
descriptor. Provider-cost closure parents and reloads every dispatch intent,
terminal attempt, and pinned provider event/settlement grammar, reconciles
partial/late attempts, and derives exact non-negative microunits; it never
sums client claims. Prefix-index sealing fails until every dispatch has exactly
one terminal attempt and every attempt has one final settlement in the
immutable `CostClosure`. Assignment, packet construction, analysis, and
release cannot parent an unsettled prefix candidate. The
zero-spend synthetic path still emits a typed zero-attempt/zero-cost or
attempt-bound zero-cost closure rather than omitting it.

Prefix-index validation does not maintain a weaker mapping-only duplicate of
the execution contract. It decodes each task receipt into exact `ToolCall`,
`GradeReceipt`, `FrozenVerifierReceipt`, `PrefixCaps`, `ResourceCounters`,
`CallSeedReceipt`, and `FrozenPrefixReceipt` values and converts every runtime
type/value failure into `RecordValidationError`. Both the task receipt and its
nested verifier schedule digest must equal `payload.schedule_ref.sha256`.
The synthetic environment type has no simulator handle. Confirmation must
additionally prove process/network isolation: the environment worker can emit
a simulator context but cannot possess model-server credentials or reach the
simulator endpoint.

**Files:**

- Create: `src/pneuma_lab/resampling_null/controller.py`
- Create: `src/pneuma_lab/resampling_null/synthetic.py`
- Create: `tests/resampling_null/test_controller.py`
- Modify: `schemas/resampling-prefix-receipt.schema.json`
- Modify: `src/pneuma_lab/resampling_null/schedule.py`
- Modify: `src/pneuma_lab/resampling_null/artifacts.py`
- Modify: `src/pneuma_lab/resampling_null/types.py`
- Modify: `src/pneuma_lab/resampling_null/__init__.py`
- Modify: `tests/resampling_null/test_artifacts.py`
- Modify: `tests/resampling_null/test_assignment.py`
- Modify: `tests/test_schema_loads.py`

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
Reuse the `TriggerReason` enum introduced in Task 3; do not redeclare it.

```python
class FailureKind(str, Enum):
    NONE = "none"
    MODEL = "model"
    MALFORMED_ACTION = "malformed_action"
    TOKEN_CAP = "token_cap"
    TOOL_CAP = "tool_cap"
    TIMEOUT = "timeout"
    REFUSAL = "refusal"
    INFRASTRUCTURE = "infrastructure"


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
    prefix_caps: PrefixCaps
    snapshot_ref: ArtifactRef
    visible_context_ref: ArtifactRef
    visible_sha256: str
    token_ids_ref: ArtifactRef
    token_ids_sha256: str
    branch_pending_calls: tuple[ToolCall, ...]
    terminal_unexecuted_remainder: tuple[ToolCall, ...]
    trigger_reason: TriggerReason
    terminal_failure_kind: FailureKind
    y0_grade: GradeReceipt
    verifier_receipt: FrozenVerifierReceipt
    counters: ResourceCounters
    simulator_counters: ResourceCounters
    call_seeds: tuple[CallSeedReceipt, ...]
    provider_attempts_ref: ArtifactRef
    boundary_ledger_ref: ArtifactRef
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
    payload = kdf_frame(
        "call-seed-v1",
        [
            U64Field(slot_seed),
            TextField(subject_role),
            U64Field(call_index),
        ],
    )
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

    def episode_terminal(self, state: "RuntimeState") -> bool:
        ...

    def grade_restored(self, state: "RuntimeState") -> "RawGradeEvidence":
        ...

    def verify_restored(self, state: "RuntimeState") -> "RawVerifierEvidence":
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

def seal_prefix_index(
    receipts: Sequence["FrozenPrefixReceipt"],
    *,
    schedule_ref: ArtifactRef,
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
`seal_prefix_index` derives exact selected-task membership only by loading the
byte-verified `schedule_ref`; it accepts no caller roster/coverage argument,
verifies exact receipt coverage and order, and writes the single
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
git add schemas/resampling-prefix-receipt.schema.json src/pneuma_lab/resampling_null/types.py src/pneuma_lab/resampling_null/__init__.py src/pneuma_lab/resampling_null/schedule.py src/pneuma_lab/resampling_null/artifacts.py src/pneuma_lab/resampling_null/controller.py src/pneuma_lab/resampling_null/synthetic.py tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py tests/resampling_null/test_assignment.py tests/test_schema_loads.py
git commit -m "feat(resampling-null): run snapshot-paired blocks"
```

## Task 6: Pre-outcome analysis freeze, blinded projection, and gated unblinding

**Files:**

- Create: `src/pneuma_lab/resampling_null/freeze.py`
- Create: `src/pneuma_lab/resampling_null/projection_candidate.py`
- Create: `src/pneuma_lab/resampling_null/blinding.py`
- Create: `tests/resampling_null/test_freeze.py`
- Create: `tests/resampling_null/test_blinding.py`
- Modify: `schemas/resampling-blinded-projection.schema.json`
- Modify: `src/pneuma_lab/resampling_null/artifacts.py`
- Modify: `tests/resampling_null/test_artifacts.py`

### Step 1: Write failing freeze and blinding tests

Test:

- analysis freeze binds the exact analysis sources, config, projection schema,
  and already-sealed packet index;
- changing a source byte, config byte, projection-schema byte, or packet-index
  parent makes freeze verification fail;
- freeze refuses an unsealed or schema-invalid packet index;
- a task block cannot be accepted without the analysis-freeze parent;
- projection contains only opaque A/B/C/D capabilities;
- arm names, treatment names, packets, donor IDs, and master/subkey bytes are absent
  from serialized projection;
- projected outcomes use the closed primitive `BlindedOutcome` only and contain
  no ArtifactRef/path, packet/grade ref, opaque source receipt, arm, donor, key,
  or hidden source identity;
- the capability-minimal candidate builder accepts only stripped opaque
  schedule/block values, has no path/resolver/key/ledger/`Arm`/packet import,
  and produces identical bytes in a subprocess with no run-root mount;
- a candidate cannot be published directly: the trusted seal transaction
  reloads the clear ledger and every task-block parent, reconstructs the
  stripped view, rejects any candidate difference, and only then writes the
  schema-valid scientific projection;
- projection-candidate bytes are ephemeral and absent from the scientific root,
  while the sealed projection's recomputable candidate digest survives
  artifact-root verification;
- A/B/C/D follow preregistered slot order, not outcome or execution order;
- projection covers the complete selected schedule and acts as the pre-unblind
  artifact-completeness receipt;
- task order is deterministic;
- a permit with the wrong HMAC, ledger digest, projection digest, or freeze
  digest fails before the clear ledger is parsed, proven with a ledger-loader
  spy;
- permit issue and `unblind_projection` each consume a fresh nominal
  unblind-purpose handle, independently verify the master commitment, derive
  only `K_unblind`, and reject assignment-purpose/lookalike/reused handles
  before ledger parsing;
- current analysis-source mismatch blocks unblinding;
- first successful unblind appends a receipt;
- a second unblind cannot overwrite that receipt; and
- changing one projected outcome breaks its parent digest.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q
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
completed authority-appropriate power final
-> selected-membership schedule
-> prefixes and verifier receipts
-> assignment
-> packet build
-> packet audit/final packet index
-> analysis freeze
-> branches
-> ephemeral capability-minimal blinded-projection candidate
-> trusted ancestry-validated blinded-projection seal/completeness
-> unblind and analysis
-> artifact-root seal
```

### Step 4: Implement capability-separated projection and unblinding

```python
@dataclass(frozen=True, slots=True)
class BlindedResourceCounters:
    generated_tokens: int
    model_calls: int
    tool_calls: int
    wall_clock_ms: int


@dataclass(frozen=True, slots=True)
class BlindedOutcome:
    success: Literal[0, 1]
    prefix_success: Literal[0, 1]
    partial_reward: float
    infrastructure_failure: bool
    counters: BlindedResourceCounters


@dataclass(frozen=True, slots=True)
class BlindedSlot:
    label: Literal["A", "B", "C", "D"]
    slot_id: str
    outcome: BlindedOutcome


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


@dataclass(frozen=True, slots=True)
class OpaqueProjectionSlot:
    slot_ordinal: Literal[0, 1, 2, 3]
    slot_id: str
    outcome: BlindedOutcome


@dataclass(frozen=True, slots=True)
class OpaqueProjectionBlock:
    task_id: str
    benchmark: str
    stratum: str
    lineage: str
    sensitivity_groups: tuple[GroupLabel, ...]
    prefix_success: int
    triggered: bool
    slots: tuple[
        OpaqueProjectionSlot,
        OpaqueProjectionSlot,
        OpaqueProjectionSlot,
        OpaqueProjectionSlot,
    ]
    pipeline_valid: bool
    validity_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OpaqueProjectionSchedule:
    study_id: str
    schedule_sha256: str
    ordered_task_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BlindedProjectionCandidate:
    study_id: str
    schedule_sha256: str
    analysis_freeze_sha256: str
    rows: tuple[BlindedRow, ...]
    expected_task_count: int
    complete: Literal[True]


def build_blinded_projection_candidate(
    schedule: OpaqueProjectionSchedule,
    blocks: Sequence[OpaqueProjectionBlock],
    *,
    analysis_freeze_sha256: str,
) -> BlindedProjectionCandidate:
    ...


def seal_blinded_projection(
    block_refs: Sequence[ArtifactRef],
    schedule_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    candidate: BlindedProjectionCandidate,
    *,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


@dataclass(frozen=True, slots=True)
class UnblindPermit:
    study_id: str
    manifest_sha256: str
    schedule_sha256: str
    prefix_index_sha256: str
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


def issue_unblind_permit(
    *,
    unblind_secret_handle: UnblindSecretHandle,
    study_id: str,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    projection_ref: ArtifactRef,
    assignment_ledger_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    expected_task_count: int,
    run_root: Path,
) -> UnblindPermit:
    ...


def unblind_projection(
    projection_ref: ArtifactRef,
    assignment_ledger_ref: ArtifactRef,
    permit: UnblindPermit,
    analysis_freeze_ref: ArtifactRef,
    current: CurrentAnalysisInputs,
    *,
    unblind_secret_handle: UnblindSecretHandle,
    run_root: Path,
    receipt_path: Path,
) -> tuple[tuple["AnalysisRow", ...], ArtifactRef]:
    ...
```

`projection_candidate.py` contains only the closed stripped input/output types
through `BlindedProjectionCandidate` and
`build_blinded_projection_candidate`. The trusted
`seal_blinded_projection`, unblind types, and unblind transactions live in
`blinding.py`; the shared code block above shows the boundary's combined public
surface, not one module's imports.

`build_blinded_projection_candidate` is a capability-minimal pure builder. Its
module does not import `Path`, `ArtifactRef`, artifact loaders, assignment
records, `BranchOutcome`, `Arm`, secret handles, or packet types. It receives
only the stripped values above. `BlindedOutcome` is a closed analysis-visible
primitive containing binary success/prefix success, finite partial reward,
infrastructure-failure bit, and nonnegative generated-token/model-call/tool-call/
wall-clock counters. It has no ArtifactRef/path, packet/grade/source receipt,
arm, donor, key, or hidden source identity. The builder sorts by the schedule's
frozen task order, maps slot ordinals
`0..3` to A/B/C/D, requires every outcome's `prefix_success` to equal its
row-level prefix value, and returns a closed candidate. In the production test it
runs in an isolated subprocess with an empty allowlisted environment, an
unrelated empty working directory, canonical JSON on stdin/stdout, and no
run-root mount. Candidate bytes are held in controller memory or an operational
temporary location outside `run_root`; they are never a scientific record or a
referenced blob.

`seal_blinded_projection` is the trusted controller transaction. Before writing
anything it reloads the schedule and analysis freeze, reloads every original
task block, follows each block's assignment/packet/freeze/prefix ancestry through
the encrypted controller `Path`, verifies exact selected-schedule coverage, and constructs
the `OpaqueProjectionSchedule`, `OpaqueProjectionBlock`, and
`BlindedOutcome` values field by field from the authoritative outcome while
dropping its task/benchmark/opaque-arm/source ArtifactRef fields. It recomputes
the expected candidate and requires canonical byte equality with the supplied
candidate. Only then does it add the original task-block
ArtifactRefs, store `projection_candidate_sha256`, and atomically write the
schema-valid singleton scientific projection. Artifact-root verification
reconstructs and rehashes the candidate from the same parents. Persist neither
key material nor clear arm map in the projection.

Only an unblinding entry point may load both the projection and clear assignment
ledger. `issue_unblind_permit` consumes a fresh unblind-purpose handle from the
concrete secret store; core code reads the already-open owner-only 32-byte
master, independently verifies its manifest commitment/context, derives only
`K_unblind`, and zeroes both buffers before constructing `UnblindPermit`.
Compute its HMAC over `FRAME("unblind-permit-v1", ...)` binding study,
manifest, schedule, prefix, assignment ledger, projection, analysis freeze,
and expected task count. No public function accepts raw master/subkey bytes;
the master/subkey never enters the permit, argv value, environment, stdout,
log, worker, or scientific record. `unblind_projection` derives the public
manifest/schedule/prefix context from the sealed projection and task-block
parents, consumes a second independently verified unblind-purpose handle, and
internally recomputes the framed HMAC with a newly derived `K_unblind`. An
assignment-purpose handle, copied handle, or reuse rejects. It accepts no
`PermitVerifier` or other caller-
supplied verification callback. Verify that HMAC, projection completeness,
current sources/config/projection schema/sealed packet index against the
analysis freeze, and every parent digest before invoking the clear-ledger
loader or parsing slot-to-arm mappings.
Write the unblind receipt through the ancestry-bound atomic helper and refuse an
existing target.

### Step 5: Prove green

```powershell
python -m pytest tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q
```

Expected: pass.

### Step 6: Commit

```powershell
git add src/pneuma_lab/resampling_null/freeze.py src/pneuma_lab/resampling_null/projection_candidate.py src/pneuma_lab/resampling_null/blinding.py src/pneuma_lab/resampling_null/artifacts.py schemas/resampling-blinded-projection.schema.json tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py tests/resampling_null/test_artifacts.py
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
- analysis loads the manifest roster/eligibility and completed power final only
  through digest-valid ArtifactRefs, reconstructs the selected schedule,
  rejects missing/extra tasks or changed benchmark/group membership, and never
  accepts a free claimed roster/membership digest;
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
- Modify: `schemas/resampling-power-report.schema.json`
- Modify: `schemas/resampling-artifact-root.schema.json`
- Modify: `src/pneuma_lab/resampling_null/artifacts.py`
- Modify: `tests/resampling_null/test_artifacts.py`

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
- identical manifest/authority/grid/topology refs yield byte-identical counts
  from the grid's one exact public U64 RNG root;
- scalar analysis and batched P0 invoke the same sufficient-statistics gate
  kernel from `analysis.py`, conditional on nonstatistical admissibility;
- a roster manifest fixes each task's joint sensitivity-group membership,
  exact C120/C160 tier membership, and group counts;
- trigger allocation is a uniform exact-size subset of each benchmark roster
  and preserves joint-cell counts for leave-one-group gates;
- the closed synthetic power-authority blob accepts only a manifest-equal
  `synthetic_fixture` roster and forbids an eligibility ref;
- the closed roster-bound power-authority blob requires manifest-equal
  `eligible_confirmation` roster bytes plus the study manifest's already-copied
  base-eligibility manifest whose accepted set, nested tier membership, and
  group labels reproduce the roster;
- swapping either authority arm, changing any authority/manifest/eligibility/
  roster byte, or relabeling a synthetic roster as roster-bound fails before a
  screen;
- `seal_roster_bound_power_authority` accepts only `manifest_ref`; a fabricated
  alternate eligibility source/ref after study seal is structurally impossible
  and rejected if smuggled into blob bytes;
- no public config, simulator, finalizer, or CLI accepts a free
  `decision_authority` or roster ref; every stage derives both from
  `authority_ref`;
- every stage binds and rechecks the exact grid and screen-topology ArtifactRefs,
  and changing either ref/byte breaks the chain;
- every numeric `PowerConfig` field is reconstructed from the referenced grid
  and a caller-constructed config with one changed value is rejected;
- `PowerConfig` exposes no caller-settable numeric science fields; every
  producer reloads the closed grid and rejects a changed grid/RNG-contract
  digest;
- the grid contains exactly public RNG root `7640891576956012809` and the closed
  ordered frame/key/counter/domain/draw mapping; changing, reordering, or
  cherry-picking any contract field changes the recomputed digest and rejects;
  no producer accepts a seed/generator/counter, and
  changing or cherry-picking any root, authority kind, roster/grid science
  digest, draw domain, cell, replicate, validation, or multiplier counter
  breaks semantic validation;
- resealing identical authority-kind/scientific-roster/grid bytes under a
  different study ID, timestamp, relative path, manifest/authority ref, or
  topology produces identical per-draw vectors and merged scientific counts;
- screen/shard/selection/validation/final records persist the recomputed
  RNG-contract digest and stage/parent-phase-derived kernel ID, while a public
  `mode` or kernel parameter and any cross-phase relabel reject;
- a synthetic roster report is labeled conditional/non-decisive and cannot
  select a confirmation tier: its completed chain requires
  `selected_tier = None` and `decision = "CONDITIONAL_ONLY"`;
- a roster-bound completed chain requires `selected_tier` in `{120, 160}` and
  `decision = "GO"`, while every feasibility no-go requires
  `selected_tier = None` and `decision = "NO_GO"`;
- the Gaussian-max critical value is monotone and matches a known independent
  case;
- Gaussian-max handles correlation `-1` and `+1` analytically;
- the 96-point Gauss-Hermite, 128-point Gauss-Legendre, Gaussian-root, and
  Clopper-Pearson numeric receipts match frozen fixtures;
- separate one-sided Clopper-Pearson lower/upper tails are `0.05/729` and
  `0.05/2187`, never split in half;
- screen projection rejects a full run above 12 hours;
- every screen generation freezes a positive `shard_count`; shards derive it
  from the screen, cover exactly `0..count-1`, and reject a later count, while
  repartitioning requires an incremented immutable screen generation;
- different screen generation/count/worker partitions produce byte-identical
  merged cell counts, rescreening reproduces the same fixed draws, and
  shard/resume output is byte-identical to an uninterrupted run;
- failed screens remain immutable while later generations use distinct
  authority/phase/generation identities, and a full-multiplier fallback has a
  separate phase;
- Gaussian screens reject a fallback trigger; a fallback screen requires,
  reloads, and parents the latest completed failed Gaussian validation for the
  same authority/grid/topology, rejects an older/unrelated/passing trigger, and
  closes later Gaussian generations;
- validation-cell selection freezes exactly the five lowest unrounded
  alternative pass rates with deterministic tie-breaking;
- C160 power is no lower than C120 on a fixed easy cell; and
- a tiny test grid writes raw counts, intervals, numeric receipts, and verdict;
- every screen/shard/selection/validation/final output validates as a staged
  `resampling_power_report` with exact RNG/kernel/shard mirrors; and
- the one final report parents every failed/passing attempt and uses exactly
  one closed finalization arm; exhausted Gaussian-screen retries and exhausted
  full-multiplier-fallback screening emit roster-only `feasibility_no_go` or
  synthetic-only `synthetic_validation_failed`, according to the referenced
  authority, with no fabricated shard/selection/validation refs; and
- after that final is sealed, every later screen/shard/selection/validation or
  second-final write for the authority rejects;
- a completed roster-bound `NO_GO` validation uses
  `power_or_type_i_gate_failed`, while `attempt_incomplete` is rejected for a
  completed persisted validation and cannot name terminal stage `validation`;
  and
- a failed completed synthetic validation uses
  `synthetic_validation_gate_failed`, null tier, and
  `decision = "CONDITIONAL_ONLY"`; and
- a successful all-cell full-multiplier fallback validates complete
  cells/counts/numeric/tier receipts, finalizes without a Gaussian selection,
  and survives artifact sealing.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_power.py tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q
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
class SyntheticPowerAuthority:
    schema_version: Literal["1"]
    authority_kind: Literal["synthetic_validation"]
    manifest_ref: ArtifactRef
    roster_ref: ArtifactRef
    tier_membership_sha256: str


@dataclass(frozen=True, slots=True)
class RosterBoundPowerAuthority:
    schema_version: Literal["1"]
    authority_kind: Literal["roster_bound_selection"]
    manifest_ref: ArtifactRef
    eligibility_manifest_ref: ArtifactRef
    roster_ref: ArtifactRef
    tier_membership_sha256: str


PowerAuthority = SyntheticPowerAuthority | RosterBoundPowerAuthority


@dataclass(frozen=True, slots=True)
class PowerRngContract:
    contract_id: Literal["power-philox-v1"]
    bit_generator: Literal["numpy.random.Philox"]
    counter_fields: tuple[
        Literal["draw_domain"],
        Literal["phase"],
        Literal["cell_id"],
        Literal["replicate_index"],
        Literal["draw_kind"],
        Literal["draw_index"],
    ]
    counter_frame: Literal["power-rng-counter-v1"]
    draw_domains: tuple[
        Literal["screen"],
        Literal["grid"],
        Literal["validation"],
    ]
    draw_kinds: tuple[
        Literal["screen_trigger_partition"],
        Literal["screen_triggered_pattern"],
        Literal["screen_no_trigger_success"],
        Literal["grid_trigger_partition"],
        Literal["grid_triggered_pattern"],
        Literal["grid_no_trigger_success"],
        Literal["gaussian_validation_trigger_partition"],
        Literal["gaussian_validation_triggered_pattern"],
        Literal["gaussian_validation_no_trigger_success"],
        Literal["multiplier_rademacher"],
    ]
    integer_encoding: Literal["unsigned-big-endian"]
    key_fields: tuple[
        Literal["root_u64"],
        Literal["authority_kind"],
        Literal["tier_membership_sha256_raw32"],
        Literal["grid_content_sha256_raw32"],
    ]
    key_frame: Literal["power-rng-key-v1"]
    numpy_version: Literal["2.3.5"]
    root_u64: Literal[7640891576956012809]


@dataclass(frozen=True, slots=True)
class PowerGridSpec:
    schema_version: Literal["1"]
    benchmark_tiers: tuple[Literal[120], Literal[160]]
    p0_values: tuple[float, float, float]
    trigger_rates: tuple[float, float, float]
    latent_rhos: tuple[float, float, float]
    datasets_per_cell: int
    screen_datasets_per_cell: int
    max_projected_wall_seconds: int
    validation_cell_count: int
    validation_datasets_per_cell: int
    multiplier_draws: int
    target_effect: float
    target_power: float
    familywise_alpha: float
    gauss_hermite_order: int
    gauss_legendre_order: int
    probability_tolerance: float
    gaussian_root_tolerance: float
    gaussian_root_max_iterations: int
    clopper_pearson_tolerance: float
    clopper_pearson_max_iterations: int
    rng: PowerRngContract


def seal_synthetic_power_authority(
    manifest_ref: ArtifactRef,
    *,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def seal_roster_bound_power_authority(
    manifest_ref: ArtifactRef,
    *,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def load_power_authority(
    authority_ref: ArtifactRef,
    *,
    run_root: Path,
) -> PowerAuthority:
    ...


@dataclass(frozen=True, slots=True)
class PowerConfig:
    authority_ref: ArtifactRef
    grid_ref: ArtifactRef
    screen_topology_ref: ArtifactRef
    rng_contract_sha256: str


def _load_power_grid(
    grid_ref: ArtifactRef,
    *,
    run_root: Path,
) -> PowerGridSpec:
    ...


def load_power_config(
    authority_ref: ArtifactRef,
    grid_ref: ArtifactRef,
    screen_topology_ref: ArtifactRef,
    *,
    run_root: Path,
) -> PowerConfig:
    ...


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


def screen_power_grid(
    config: "PowerConfig",
    *,
    phase: PowerPhase,
    generation: int,
    shard_count: int,
    fallback_trigger_ref: ArtifactRef | None,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def simulate_power_shard(
    screen_ref: ArtifactRef,
    config: PowerConfig,
    *,
    shard_index: int,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def select_validation_cells(
    screen_ref: ArtifactRef,
    shard_refs: Sequence[ArtifactRef],
    config: PowerConfig,
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
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...


def validate_full_multiplier_fallback(
    screen_ref: ArtifactRef,
    shard_refs: Sequence[ArtifactRef],
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
    selected_kernel_id: Literal["power-final-gaussian-v1"]
    selected_shard_count: int
    selected_screen_ref: ArtifactRef
    selected_shard_refs: tuple[ArtifactRef, ...]
    selected_selection_ref: ArtifactRef
    selected_validation_ref: ArtifactRef
    selected_tier: Literal[120, 160] | None
    decision: Literal["GO", "CONDITIONAL_ONLY"]


@dataclass(frozen=True, slots=True)
class FullMultiplierCompletedChain:
    kind: Literal["completed_chain"]
    selected_phase: Literal["full_multiplier_fallback"]
    selected_generation: int
    selected_kernel_id: Literal["power-final-full-multiplier-v1"]
    selected_shard_count: int
    fallback_trigger_ref: ArtifactRef
    selected_screen_ref: ArtifactRef
    selected_shard_refs: tuple[ArtifactRef, ...]
    full_grid_validation_ref: ArtifactRef
    selected_tier: Literal[120, 160] | None
    decision: Literal["GO", "CONDITIONAL_ONLY"]


@dataclass(frozen=True, slots=True)
class FeasibilityNoGoFinalization:
    kind: Literal["feasibility_no_go"]
    terminal_attempt_ref: ArtifactRef
    terminal_stage: Literal["screen", "shard", "selection", "validation"]
    terminal_phase: PowerPhase
    terminal_kernel_id: Literal[
        "power-final-gaussian-v1",
        "power-final-full-multiplier-v1",
    ]
    terminal_shard_count: int
    reason: Literal[
        "gaussian_screen_exhausted",
        "full_multiplier_screen_exhausted",
        "numeric_fixture_failed",
        "runtime_bound_exceeded",
        "attempt_incomplete",
        "power_or_type_i_gate_failed",
    ]
    selected_tier: None
    decision: Literal["NO_GO"]


@dataclass(frozen=True, slots=True)
class SyntheticValidationFailedFinalization:
    kind: Literal["synthetic_validation_failed"]
    terminal_attempt_ref: ArtifactRef
    terminal_stage: Literal["screen", "shard", "selection", "validation"]
    terminal_phase: PowerPhase
    terminal_kernel_id: Literal[
        "power-final-gaussian-v1",
        "power-final-full-multiplier-v1",
    ]
    terminal_shard_count: int
    reason: Literal[
        "gaussian_screen_exhausted",
        "full_multiplier_screen_exhausted",
        "numeric_fixture_failed",
        "runtime_bound_exceeded",
        "attempt_incomplete",
        "synthetic_validation_gate_failed",
    ]
    selected_tier: None
    decision: Literal["CONDITIONAL_ONLY"]


PowerFinalization = (
    GaussianApproximationCompletedChain
    | FullMultiplierCompletedChain
    | FeasibilityNoGoFinalization
    | SyntheticValidationFailedFinalization
)


def finalize_power_report(
    all_attempt_refs: Sequence[ArtifactRef],
    *,
    config: PowerConfig,
    finalization: PowerFinalization,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    ...
```

Power-authority blobs use
`application/vnd.pneuma.power-authority+json`,
`canonical_json_bytes(value, indent=None)`, the shared closed ArtifactRef, and
exactly the two dataclass shapes above. They are referenced blobs, not a new
scientific record kind. `seal_synthetic_power_authority` reloads the manifest's
roster ref, requires a closed `roster_kind = "synthetic_fixture"` roster, and
recomputes its ordered tier/task/group membership digest. The digest preimage
has exactly the closed shape illustrated by
`{"rows":[{"benchmark":"SWE","groups":[{"kind":"language","value":"C"}],
"task_id":"swe-001","tiers":[120,160]}],"schema_version":"1"}`: rows are unique
and strict-UTF-8 sorted by `(benchmark, task_id)`, tiers are a strictly
increasing non-empty subset of `[120, 160]`, groups are unique in the frozen
kind/value order, and
`tier_membership_sha256 = SHA256(canonical_json_bytes(preimage, indent=None))`.
`seal_roster_bound_power_authority` accepts only `manifest_ref`, reloads the
manifest's required non-null base-commit eligibility ref, requires
`roster_kind = "eligible_confirmation"`, proves study/commitment/reveal/roster
derivation, and exactly reproduces its accepted set, nested C120/C160
membership, reserves, and joint group labels. Synthetic authority requires the
manifest field to be null. Both reject caller-provided eligibility/roster refs,
authority strings, or membership digests. `load_power_authority` parses/re-
serializes canonical bytes, repeats those proofs, and returns the discriminated
typed arm. A fabricated post-seal eligibility blob is unreachable.

`load_power_config` is the only public constructor. `PowerConfig` contains only
the three ArtifactRefs and recomputed RNG-contract digest; it exposes no
caller-settable numeric scientific values. Every report producer calls
`load_power_authority`, reloads and closes `PowerGridSpec` from the grid bytes,
reloads screen topology, requires both refs to equal the authority's study
manifest `power_grid_ref`/`power_screen_topology_ref`, and stores/rechecks their
exact refs. All tiers, nuisance values, counts, thresholds, tolerances, orders,
and RNG fields are reconstructed on every call; a caller-created config or grid
mirror with one changed value rejects. Its
`decision_authority`, `roster_ref`, and `tier_membership_sha256` report fields
are derived mirrors. No producer accepts them as parameters, and a downstream
stage rejects any mismatch with the authority, grid, topology, RNG contract, or
parent stage.

The grid's closed RNG object is exactly the `PowerRngContract` shape above,
including root `7640891576956012809`, NumPy `2.3.5`, frame labels, ordered
key/counter fields, ordered domains/draw kinds, and unsigned-big-endian
encoding; unknown fields or reordered arrays reject. `rng_contract_sha256`
hashes the complete compact canonical subobject, not only its root/version.
For every stochastic call derive the Philox key as the first 16 bytes of
`SHA256(FRAME("power-rng-key-v1", [U64(root), TEXT(authority_kind),
BYTES(tier_membership_digest), BYTES(grid_content_digest)]))` and interpret it
as an unsigned big-endian 128-bit integer. Both digests are decoded to their
raw 32 bytes before framing: membership is recomputed from the exact canonical
scientific roster payload and grid content from the exact closed canonical grid
bytes. Study ID, timestamp, manifest/authority ArtifactRef identity, relative
path, and topology metadata are absent. Derive the unsigned big-endian 256-bit
counter from the full SHA-256 of
`FRAME("power-rng-counter-v1", [TEXT(draw_domain), TEXT(phase),
TEXT(cell_id), U64(replicate), TEXT(draw_kind), U64(draw_index)])`.

Screen uses domain `screen`, the declared phase, each cell, and 200 replicate
ordinals. Production/fallback shards use domain `grid`, their screen's phase,
cell assignment `ordinal mod count`, and 20,000 replicate ordinals. Gaussian
validation uses domain `validation`, Gaussian phase, frozen cells, and 2,000
outer ordinals; fallback validation uses the corresponding fallback phase/full
cells. Generation/count/shard index are ancestry and execution routing only;
they never enter a scientific key or counter. Changing generation, count,
worker partition, study metadata, path, or topology while retaining identical
authority-kind/roster/grid bytes must reproduce byte-identical logical draws
and merged counts. Screen timing uses only the same fixed 200-dataset screen
draws and cannot refresh them on retry. Draw kinds are exactly the three screen, three grid, three
Gaussian-validation partition/pattern/no-trigger names:
`screen_trigger_partition`, `screen_triggered_pattern`,
`screen_no_trigger_success`, `grid_trigger_partition`,
`grid_triggered_pattern`, `grid_no_trigger_success`,
`gaussian_validation_trigger_partition`,
`gaussian_validation_triggered_pattern`,
`gaussian_validation_no_trigger_success`, plus
`multiplier_rademacher`. The first nine use canonical joint-group ordinal as
`draw_index`; multiplier weights use
`multiplier_ordinal * selected_task_count + canonical_task_ordinal`. Instantiate
a fresh `Generator(Philox(counter=..., key=...))` and make exactly one pinned
NumPy distribution call. Selection/final consume no random bytes. No public
seed, generator, counter, skip, or cherry-picked replicate API exists; abandoning
an attempt or resealing scientifically identical inputs cannot create a new
random experiment.

Kernel IDs are a closed lookup from `(stage, parent_screen.phase)`:
Gaussian screen/shard/selection/validation/final map respectively to
`power-screen-gaussian-v1`, `power-grid-gaussian-v1`,
`power-worst-five-selection-v1`,
`power-gaussian-vs-multiplier-validation-v1`, and
`power-final-gaussian-v1`; fallback screen/shard/validation/final map to
`power-screen-full-multiplier-v1`, `power-grid-full-multiplier-v1`,
`power-full-grid-validation-v1`, and `power-final-full-multiplier-v1`.
Fallback selection is forbidden. No public mode/kernel argument exists, and
every stage persists/rechecks the derived value.

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

The authority-derived roster ref is immutable and gives every task's benchmark,
tier membership, and joint set of language/domain/issue-family labels. The production grid
evaluates `n_b in {120, 160}` and 20,000 datasets per cell. For each benchmark,
set `m_b = gamma * n_b` exactly and choose a uniform size-`m_b` subset of its
frozen roster through deterministic multivariate-hypergeometric counts over the
joint group cells. Within each joint cell, draw triggered 16-pattern counts
from `Multinomial(m_cell, pi_trigger)`. For its nontrigger tasks draw
`U_cell ~ Binomial(n_cell - m_cell, p0)`, assign `U_cell` to `1111`, and assign
the remainder to `0000`. Aggregate those same joint-cell counts for benchmark
and every overlapping leave-one-group gate.

The committed synthetic roster validates machinery and performance only. Its
sealed synthetic authority blob derives
`decision_authority == "synthetic_validation"`; its final report must say
`CONDITIONAL_ONLY`, cannot select C120/C160, and cannot emit the study's
feasibility no-go. After the actual eligible registry freezes exact C120/C160
membership and all group labels, seal a new eligible-confirmation study
manifest that copies that exact eligibility blob and derived roster. The
roster-bound authority transaction then accepts only the study ref, reloads
eligibility through it, and runs the complete grid before any confirmation
prefix. Only that referenced authority may select a tier or emit
`FEASIBILITY_NO_GO`.

Before production, `screen_power_grid` runs exactly 200 datasets for every one
of the 729 alternative and 2,187 null cells on the declared CPU topology. It
must reproduce the committed numeric fixture digest, declare a positive
`shard_count`, and project the complete 20,000-dataset grid at `<= 43,200`
seconds. A failed screen permits vectorization/repartitioning and another
sealed screen under the same authority and phase with `generation += 1`; the
new generation may declare another count but never overwrites the failed
generation or permits a smaller scientific grid. If the bound still fails,
finalize
roster-bound authority as `feasibility_no_go`; finalize synthetic authority as
`synthetic_validation_failed` with the applicable nondecisive reason.

`fallback_trigger_ref` is phase-discriminated. Gaussian screens require it to
be null. A fallback screen requires it, reloads it as the maximal-generation
completed Gaussian `validation` for the same authority/grid/topology, proves
that the approximation gate failed, and writes the ref into the screen's
`parent_refs`. Sealing that fallback screen closes the Gaussian phase: no later
Gaussian screen generation is legal. An older, passing, unrelated, or
wrong-stage trigger fails before timing or simulation.

Production calls `evaluate_binary_gate_batch` from `analysis.py` over
read-only sufficient-statistics arrays; it does not create per-dataset row
objects or rerun a 99,999-draw loop per replicate. Exact content sign tails and
excess conditional-DP tails are precomputed/looked up from the observed binary
sufficient counts. Gaussian-max critical values are vectorized. The full
multiplier routine is used only in the frozen validation/fallback path.

Production partitions only by immutable ordered cell ID modulo the screen's
frozen count. `simulate_power_shard` accepts only `screen_ref` plus
`shard_index`; it derives phase, generation, kernel, RNG mapping, and count from
that screen. Each shard records its closed cell-ID set plus
config/code/numeric/RNG/kernel/count digests. Resume accepts a shard only when
all mirrors and raw replicate counts match; merge requires exactly indices
`0..shard_count-1` and rejects gaps, overlap, duplicates, or a later asserted
count. Repartitioning requires a new immutable screen generation and therefore
a new execution/attempt identity, but the scientific key, counter, draw domain,
logical draws, and merged logical counts remain byte-identical for the same
authority-kind/roster/grid bytes. It is never represented as an overwrite or
continuation of the prior attempt.

Every persisted phase is a schema-valid `resampling_power_report`: `screen`,
`shard`, `selection`, `validation`, or `final`. Each later stage parents the
earlier ArtifactRefs and rejects the wrong stage. The envelope records
the authority ref, authority-derived decision/roster/membership mirrors, exact
grid ref, exact screen-topology ref, RNG-contract digest, derived kernel ID,
screen-frozen `shard_count`, `phase`, and nonnegative `generation`; shards
additionally record a unique zero-based shard index. Final carries the common
RNG digest and selected/terminal kernel and count. A
full-multiplier fallback uses phase `full_multiplier_fallback`, never a
disguised extra Gaussian generation; its screen additionally parents the
phase-closing failed Gaussian validation. The single final record parents every
immutable attempt, including failures. Its closed `completed_chain` arm names
the selected passing phase/generation and phase-appropriate downstream refs. A
Gaussian chain requires the frozen worst-five selection and approximation
validation. A full-multiplier chain requires the failed-Gaussian trigger plus
`validate_full_multiplier_fallback`, which verifies full ordered-cell coverage,
raw counts, numeric receipts, and the tier decision directly and has no
Gaussian selection. That validator derives the trigger only through its screen;
the final arm rechecks and stores the same ref rather than accepting a later
trigger override. Its roster-only `feasibility_no_go` arm instead names the
terminal failed attempt/stage and frozen reason with
`selected_tier = None`, `decision = "NO_GO"`, and no nonexistent downstream
refs. Its synthetic-only `synthetic_validation_failed` arm similarly names the
terminal attempt/stage but requires `selected_tier = None`,
`decision = "CONDITIONAL_ONLY"`, and a nondecisive synthetic reason.
Finalization reloads the authority blob; a roster-bound completed chain requires
selected tier 120 or 160 and `GO`, while a synthetic completed chain requires
null tier and `CONDITIONAL_ONLY`. Cross-authority arms fail schema plus semantic
validation. Sealing the final closes the authority; no later attempt stage or
second final is writable.
Only an authority-appropriate completed final may become
`PrefixSchedule.power_final_ref`; failed arms end the run before any prefix.

`attempt_incomplete` is reserved for a terminal attempt whose required next
stage never produced a scientific record. A persisted schema-valid
`validation` record is completed, so neither final arm may pair that reason
with terminal stage `validation` or point it at a validation ref; an interrupted
validation names the last completed pre-validation stage. A completed
roster-bound validation whose decision is `NO_GO` because neither tier passes
the registered power/type-I gates must finalize at stage `validation` with
`reason = "power_or_type_i_gate_failed"`. A completed synthetic validation that
fails its registered approximation/machinery checks finalizes at stage
`validation` as `synthetic_validation_failed` with
`reason = "synthetic_validation_gate_failed"`.

For P0 only, use the two-dimensional Gaussian-max critical value derived from
the estimated contrast correlation. Select the five lowest-power alternative
cells before validation and rerun 2,000 outer datasets through the full
99,999-draw multiplier routine. Freeze and write that selection before
validation outputs. Every selected cell must have an absolute gate-pass-rate
difference at most 0.01 and both methods must choose the same roster tier. On
failure, run the full multiplier routine for every cell or emit the
authority-appropriate terminal arm: roster-bound `feasibility_no_go` or
nondecisive synthetic `synthetic_validation_failed`.

For the roster-bound run, the tier passes only if every Bonferroni
Clopper-Pearson lower bound across 729
alternative cells is at least 0.80 and every upper bound across 2,187 null cells
is at most 0.05. Choose C160 when it passes; otherwise choose C120 only when it
passes; otherwise emit `FEASIBILITY_NO_GO` with
`power_or_type_i_gate_failed`. Validation freezes the five cell IDs
with the lowest unrounded C160 alternative gate-pass rate, breaking ties by the
ordered manifest. On those cells, 2,000 datasets use the full registered
99,999-draw multiplier routine. Every absolute gate-pass-rate difference must
be `<= 0.01`, and replacing those five approximate rates with their full-
multiplier rates must leave the roster-tier decision unchanged. Otherwise,
screen the all-cell full-multiplier fallback against the same 12-hour bound and
either run it for every alternative/null cell or emit the
authority-appropriate terminal arm.

### Step 4: Prove the unit suite green

```powershell
python -m pytest tests/resampling_null/test_power.py tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q
```

Expected: pass using a tiny fixture grid; the 20,000 × full-grid run is not a
unit test.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/power.py src/pneuma_lab/resampling_null/artifacts.py schemas/resampling-power-report.schema.json schemas/resampling-artifact-root.schema.json tests/resampling_null/test_power.py tests/resampling_null/test_artifacts.py fixtures/resampling_null/p0-power-grid.json fixtures/resampling_null/p0-roster-synthetic.json
git commit -m "feat(resampling-null): add joint P0 simulator"
```

## Task 9: CLI and deterministic synthetic P0

**Files:**

- Create: `src/pneuma_lab/resampling_null/cli.py`
- Create: `src/pneuma_lab/resampling_null/__main__.py`
- Create: `tests/resampling_null/test_cli.py`
- Create: `fixtures/resampling_null/p0-study.json`
- Create: `fixtures/resampling_null/p0-tasks.json`
- Create: `fixtures/resampling_null/p0-local-topology.json`
- Create: `fixtures/resampling_null/p0-required-kinds.json`

### Step 1: Write failing CLI tests

Call `main(argv)` directly and test:

- `selftest`;
- `selftest --defer-artifact-root`, which creates no receipt and is accepted
  only when a later explicit seal is possible;
- `selftest --stop-after-study`, which creates only the manifest and copied
  inputs, plus `selftest --resume-after-power <final>
  --defer-artifact-root`, which requires that manifest's one completed power
  final and creates every selected-membership descendant;
- `study seal`;
- `schedule seal`;
- `synthetic prefixes`;
- `assignment seal`;
- `packets build`;
- `packets audit`;
- `analysis freeze`;
- `synthetic branches`;
- trusted `project seal`, including the isolated opaque-candidate subprocess;
- `analyze`;
- `power authority synthetic` and `power authority roster-bound`;
- `power screen`, `simulate`, `select-validation`, `validate`,
  `validate-fallback`, and `finalize`;
- `artifacts seal` and `artifacts verify`;
- refusal to overwrite any sealed artifact;
- artifact sealing enforces the per-kind identities above: singleton study
  records, candidate/sealed packet stages, selected-schedule-unique task blocks,
  append-only unique power-attempt identities, and exactly one final report
  parenting every attempt;
- every scientific command requires one global study root and rejects an output
  or scientific input outside it;
- power commands reject `--decision-authority` and `--roster`; they accept only
  an authority ref plus manifest-frozen grid and screen-topology refs;
- study seal rejects a missing eligibility source for eligible confirmation and
  any eligibility source for a synthetic fixture; roster-bound authority has no
  later eligibility-source/ref flag;
- schedule seal rejects a missing, failed, unrelated, or cross-authority power
  final and stores its derived selected membership;
- power commands reject `--seed`, `--mode`, `--kernel`, and any
  post-screen `--shard-count`; `power screen` alone requires/fixes the positive
  shard count for that generation, forbids `--fallback-trigger` for Gaussian,
  and requires it for fallback, while validation/finalization reject a repeated
  trigger override and derive it from the screen;
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
python -m pneuma_lab.resampling_null --run-root <dir> selftest [--defer-artifact-root]
python -m pneuma_lab.resampling_null --run-root <dir> selftest --stop-after-study
python -m pneuma_lab.resampling_null --run-root <dir> selftest --resume-after-power <final-ref> [--defer-artifact-root]
python -m pneuma_lab.resampling_null --run-root <dir> study seal --study-source <json> --tasks-source <json> --roster-source <json> [--eligibility-manifest-source <json>] --assignment-program-source <json> --provider-lane-plan-source <json> --storage-policy-contract-source <json> --power-grid-source <json> --power-screen-topology-source <json> --tokenizer-source <json> --packet-template-source <text> --packet-policy-source <json> --pad-unit-set-source <json> --revision-source <path> [--revision-source <path> ...] --required-kinds-source <json> --out study-manifest.json
python -m pneuma_lab.resampling_null --run-root <dir> power authority synthetic --study study-manifest.json --out power-authority.json
python -m pneuma_lab.resampling_null --run-root <dir> power authority roster-bound --study study-manifest.json --out power-authority.json
python -m pneuma_lab.resampling_null --run-root <dir> power screen --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --phase gaussian_approximation --generation <int> --shard-count <int> --out power-screen.json
python -m pneuma_lab.resampling_null --run-root <dir> power screen --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --phase full_multiplier_fallback --generation <int> --shard-count <int> --fallback-trigger <failed-gaussian-validation-ref> --out power-screen.json
python -m pneuma_lab.resampling_null --run-root <dir> power simulate --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --screen power-screen.json --shard-index <int> --out <relative-json>
python -m pneuma_lab.resampling_null --run-root <dir> power select-validation --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --screen power-screen.json --shard-prefix <relative-prefix> --out validation-selection.json
python -m pneuma_lab.resampling_null --run-root <dir> power validate --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --shard-prefix <relative-prefix> --selection validation-selection.json --out validation.json
python -m pneuma_lab.resampling_null --run-root <dir> power validate-fallback --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --screen power-screen.json --shard-prefix <relative-prefix> --out fallback-validation.json
python -m pneuma_lab.resampling_null --run-root <dir> power finalize --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --attempt-prefix <relative-directory> --completed-gaussian --selected-screen power-screen.json --selected-shard-prefix <relative-prefix> --selected-selection validation-selection.json --selected-validation validation.json --out p0-power-report.json
python -m pneuma_lab.resampling_null --run-root <dir> power finalize --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --attempt-prefix <relative-directory> --completed-full-multiplier --selected-screen power-screen.json --selected-shard-prefix <relative-prefix> --fallback-validation fallback-validation.json --out p0-power-report.json
python -m pneuma_lab.resampling_null --run-root <dir> power finalize --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --attempt-prefix <relative-directory> --feasibility-no-go --terminal-attempt <relative-json> --terminal-stage <screen|shard|selection|validation> --reason <closed-roster-reason> --out p0-power-report.json
python -m pneuma_lab.resampling_null --run-root <dir> power finalize --authority power-authority.json --grid-ref inputs/p0-power-grid.json --screen-topology-ref inputs/p0-power-screen-topology.json --attempt-prefix <relative-directory> --synthetic-validation-failed --terminal-attempt <relative-json> --terminal-stage <screen|shard|selection|validation> --reason <closed-synthetic-reason> --out p0-power-report.json
python -m pneuma_lab.resampling_null --run-root <dir> schedule seal --study study-manifest.json --power-final p0-power-report.json --schedule-seed-file <outside-root-path> --out prefix-schedule.json
python -m pneuma_lab.resampling_null --run-root <dir> synthetic prefixes --study study-manifest.json --schedule prefix-schedule.json --out prefix-index.json
python -m pneuma_lab.resampling_null --run-root <dir> assignment seal --schedule prefix-schedule.json --prefix-index prefix-index.json --assignment-key-file <outside-root-path> --out assignment-ledger.json
python -m pneuma_lab.resampling_null --run-root <dir> packets build --study study-manifest.json --assignment assignment-ledger.json --prefix-index prefix-index.json --out-candidate packet-candidate.json
python -m pneuma_lab.resampling_null --run-root <dir> packets audit --study study-manifest.json --candidate packet-candidate.json --schedule prefix-schedule.json --assignment assignment-ledger.json --prefix-index prefix-index.json --out-index packet-index.json
python -m pneuma_lab.resampling_null --run-root <dir> analysis freeze --source-root <path> --source <relative-path> --config <path> --projection-schema <path> --packet-index packet-index.json --out analysis-freeze.json
python -m pneuma_lab.resampling_null --run-root <dir> synthetic branches --study study-manifest.json --schedule prefix-schedule.json --assignment assignment-ledger.json --prefix-index prefix-index.json --packet-index packet-index.json --analysis-freeze analysis-freeze.json --out-prefix task-blocks
python -m pneuma_lab.resampling_null --run-root <dir> project seal --schedule prefix-schedule.json --analysis-freeze analysis-freeze.json --task-block-prefix task-blocks --out blinded-projection.json
python -m pneuma_lab.resampling_null --run-root <dir> analyze --study study-manifest.json --projection blinded-projection.json --assignment assignment-ledger.json --analysis-freeze analysis-freeze.json --source-root <path> --source <relative-path> --config <path> --projection-schema <path> --packet-index packet-index.json --assignment-key-file <outside-root-path> --unblind-receipt unblind-receipt.json --out analysis.json
python -m pneuma_lab.resampling_null --run-root <dir> artifacts seal --required-kinds <path> --out p0-core-receipt.json
python -m pneuma_lab.resampling_null --run-root <dir> artifacts verify --receipt p0-core-receipt.json --required-kinds <path>
```

`--run-root` is required once before every subcommand. Every scientific input
and output argument is a normalized root-relative POSIX name; external inputs
are explicitly named `*-source`, `--source-root`/`--source`, `--config`,
`--projection-schema`, or
`--required-kinds` and are copied/content-addressed into the root before use.
`study seal` creates the first schema-valid manifest and copies the task/roster
inputs plus the conditionally required eligibility source, exact power grid,
declared screen topology, tokenizer receipt, packet template, packet policy,
and pad-unit set used by descendants. `--eligibility-manifest-source` exists
only on this command: it is required for `eligible_confirmation` and rejected
for `synthetic_fixture`. Later
power commands receive their root-relative ArtifactRef paths through
`--grid-ref` and `--screen-topology-ref`; neither is a fresh external input.
The study source must contain the ceremony constant and three named commitment
digests. `schedule seal` first reloads the completed `--power-final`, derives
the closed schedule authority/tier/membership, then reads the public schedule-
seed reveal, verifies its commitment, and loads assignment/provider assets only
through the manifest; there is no override option. `assignment seal` loads only schedule
and prefix ArtifactRefs, verifies the 32-byte master-key commitment in memory,
and cannot select a ledger mode outside the manifest-pinned program.
`packets build` and `packets audit` load their four refs only
through the validated study manifest and reject any candidate that names
different metadata.

The CLI's `--run-root` is the owner-only, transparently encrypted controller
scientific root from Task 3, not a branch-worker workspace or shared analysis
mount. Trusted commands validate its canonical plaintext paths normally.
`synthetic branches` is the trusted preparer/orchestrator: it resolves the
ledger before process launch and gives each isolated worker only its one-slot
work order, never the controller root path, ledger path, or credentials.

`--source` is repeatable and relative to `--source-root`; the command sorts its
values before hashing. Both `analysis freeze` and `analyze` receive the same
current source/config/schema/sealed-packet inputs. `packets build` writes a
schema-valid candidate-stage index and referenced packet artifacts;
only `packets audit` may create a sealed-stage packet index. `synthetic
branches` refuses absent, schema-invalid, or digest-mismatched packet-index and
analysis-freeze parents. `project seal` is the trusted controller transaction:
it sends only stripped `OpaqueProjectionSchedule`/`OpaqueProjectionBlock`
canonical bytes to an isolated candidate subprocess with no run-root mount,
then reloads the original blocks and clear assignment ancestry itself,
reconstructs the stripped values, and seals only an exact candidate. It exposes
no CLI assignment or key option because those parents are resolved internally
under the trusted controller identity.
`analyze` verifies the current frozen sources, reloads the manifest roster and
eligibility only to reconstruct the power-final-selected schedule membership,
verifies that the assignment schedule descends from that manifest/final pair,
and requires exact selected row/task/group coverage. It then creates
an in-memory HMAC permit, consumes a fresh unblind-purpose handle—not a
caller-supplied verifier—in `unblind_projection`, internally recomputes the
`K_unblind` HMAC before clear-ledger parsing, unblinds only in memory, atomically
writes the unblind receipt and analysis, and refuses either existing target.

`power authority synthetic` derives its roster only from the study manifest and
requires the closed fixture marker plus null eligibility ref. `power authority
roster-bound` accepts only the study ref, reloads the already-copied eligibility
ref through it, then proves accepted-set/tier/group equality with the manifest
roster. The CLI exposes no later eligibility source/ref,
`--decision-authority`, or
`--roster`; every later power command takes the authority, grid, and topology
refs and rejects a mismatch with its parents. The grid supplies every numeric
science value and exact public RNG contract. `power screen` alone fixes the
positive shard count and derives its kernel. It forbids a fallback trigger for
Gaussian, while fallback requires and parents the latest same-authority failed
Gaussian validation and closes further Gaussian attempts. Later validation and
finalization derive that ref from the screen and reject a repeated trigger
flag. `power simulate` accepts only a passing digest-matched screen receipt,
derives count/phase/kernel/RNG from it,
and accepts only a zero-based shard index. The output records its exact closed
cell set.
`select-validation` refuses incomplete production coverage and freezes its
output before `validate` runs. `finalize` always returns one schema-valid power
report whose mutually exclusive CLI argument groups construct either
`GaussianApproximationCompletedChain`, `FullMultiplierCompletedChain`,
`FeasibilityNoGoFinalization`, or
`SyntheticValidationFailedFinalization`; every arm parents every attempt.
Synthetic authority ends `CONDITIONAL_ONLY` through a completed or
synthetic-failed arm; roster-bound authority selects a tier, executes the
registered full-multiplier fallback, or records `FEASIBILITY_NO_GO`. A
persisted validation cannot be finalized as `attempt_incomplete`. The CLI
cannot silently weaken the grid, select a seed/mode/kernel, repartition after a
screen, or cross authority arms. Only a completed final may be passed to
`schedule seal`.

`selftest` executes the complete chronology—study, synthetic authority/power
final, final-selected schedule, prefixes, assignment, packets, freeze, 24 task
blocks across two fake benchmarks, projection, analysis, and root—then reloads
and verifies
`p0-core-receipt.json`, and ends with:

- `CAUSAL_CONTENT`;
- zero invalid blocks;
- exact packet parity;
- four distinct slot seeds per block;
- exact snapshot restoration; and
- a stable, verified artifact-root digest with every required document kind.

With `--defer-artifact-root` alone, it performs the same upstream work but
deliberately omits only the final seal/verify. `--stop-after-study` creates only
the manifest and copied inputs; it cannot create a schedule because no power
final exists. `--resume-after-power <final-ref>` requires that root to contain
the same manifest, its one complete authority/power chain, no schedule or later
record, and a completed authority-appropriate final. It then creates the
selected schedule and every non-power descendant; optional
`--defer-artifact-root` leaves only the final seal/verify undone. The former
combined power-deferral form is rejected because “non-power upstream” past the
manifest no longer exists. All modes refuse a root that already contains a
receipt.

The schedule-seed and assignment-key file paths must resolve outside the run
root. The schedule seed becomes public in its sealed schedule. The assignment
master key must be exactly 32 bytes and is never copied; its bytes and derived
subkeys never enter argv values, environment, stdout/stderr, logs, tracebacks,
scientific/operational files, or workers. CLI failures return non-zero and one
JSON error object without traceback unless `--debug` is explicit; debug output
still redacts all key objects and values.

### Step 4: Prove green

```powershell
python -m pytest tests/resampling_null/test_cli.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/cli.py src/pneuma_lab/resampling_null/__main__.py tests/resampling_null/test_cli.py fixtures/resampling_null/p0-study.json fixtures/resampling_null/p0-tasks.json fixtures/resampling_null/p0-local-topology.json fixtures/resampling_null/p0-required-kinds.json
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
python -m pneuma_lab.resampling_null --run-root $canonicalRoot selftest --stop-after-study
```

This staged mode creates only the synthetic study manifest and its copied
inputs, including null `eligibility_manifest_ref`, exact power grid, and
topology. It creates no schedule, prefix, assignment, or other descendant:
those are downstream of a completed power final. No artifact may be added after
the eventual root seal.

### Step 3: Run the conditional synthetic P0 screen and complete grid

Use a fixed local topology receipt and a deterministic shard count chosen before
the screen. The example below uses 16 shards; changing it requires a new screen
receipt, not a reinterpretation of partial results. The staged selftest's study
seal has already copied the exact fixture grid and topology to
`inputs/p0-power-grid.json` and
`inputs/p0-power-screen-topology.json` and bound both refs in the manifest.

```powershell
$powerRoot = 'power'
$powerAuthority = "$powerRoot/power-authority.json"
$powerGridRef = 'inputs/p0-power-grid.json'
$screenTopologyRef = 'inputs/p0-power-screen-topology.json'
python -m pneuma_lab.resampling_null --run-root $canonicalRoot power authority synthetic --study study-manifest.json --out $powerAuthority
python -m pneuma_lab.resampling_null --run-root $canonicalRoot power screen --authority $powerAuthority --grid-ref $powerGridRef --screen-topology-ref $screenTopologyRef --phase gaussian_approximation --generation 0 --shard-count 16 --out "$powerRoot/screen.json"
0..15 | ForEach-Object {
    python -m pneuma_lab.resampling_null --run-root $canonicalRoot power simulate --authority $powerAuthority --grid-ref $powerGridRef --screen-topology-ref $screenTopologyRef --screen "$powerRoot/screen.json" --shard-index $_ --out "$powerRoot/shard-$_.json"
    if ($LASTEXITCODE -ne 0) { throw "power shard $_ failed" }
}
python -m pneuma_lab.resampling_null --run-root $canonicalRoot power select-validation --authority $powerAuthority --grid-ref $powerGridRef --screen-topology-ref $screenTopologyRef --screen "$powerRoot/screen.json" --shard-prefix "$powerRoot/shard-" --out "$powerRoot/validation-selection.json"
python -m pneuma_lab.resampling_null --run-root $canonicalRoot power validate --authority $powerAuthority --grid-ref $powerGridRef --screen-topology-ref $screenTopologyRef --shard-prefix "$powerRoot/shard-" --selection "$powerRoot/validation-selection.json" --out "$powerRoot/validation.json"
python -m pneuma_lab.resampling_null --run-root $canonicalRoot power finalize --authority $powerAuthority --grid-ref $powerGridRef --screen-topology-ref $screenTopologyRef --attempt-prefix "$powerRoot/" --completed-gaussian --selected-screen "$powerRoot/screen.json" --selected-shard-prefix "$powerRoot/shard-" --selected-selection "$powerRoot/validation-selection.json" --selected-validation "$powerRoot/validation.json" --out "$powerRoot/p0-power-report.json"
```

Expected: the screen reproduces numeric fixtures and projects `<= 12` hours;
all 20,000 datasets for every alternative/null cell and both tiers are present;
the five-cell multiplier validation is complete; and the final schema-valid
report states `CONDITIONAL_ONLY`. Resume only digest-matched completed shards.
It validates code/runtime but cannot start confirmation or select a tier. The
actual confirmation run uses a different eligible-confirmation root whose
`study seal` copied the base-eligibility manifest and derived roster before
power. `power authority roster-bound` then accepts only that study ref. No
literal eligibility, authority, roster, seed, mode, kernel, or post-screen count
argument can substitute for manifest/screen ancestry.

### Step 4: Resume from the completed final and build selected descendants

```powershell
python -m pneuma_lab.resampling_null --run-root $canonicalRoot selftest --resume-after-power "$powerRoot/p0-power-report.json" --defer-artifact-root
```

Expected: the command reloads the completed synthetic final, writes a prefix
schedule whose `power_final_ref` matches it, whose authority is
`synthetic_validation`, whose tier is null, and whose selected-membership
digest covers the full fixture roster. It then builds every prefix-through-
analysis descendant against that membership and leaves only artifact sealing
undone. A failed final, a different authority, or any pre-existing schedule
must fail before a write.

### Step 5: Run deterministic end-to-end verification twice outside the root

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

### Step 6: Update canonical status and seal the plan receipt

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

### Step 7: Run repository-wide verification

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

### Step 8: Record zero spend and implementation decision

Append:

- one decision-log entry naming the implemented hashes, passed tests, known
  limits, conditional-P0 status, canonical receipt digest, and next
  benchmark-adapter gate; and
- one spend-ledger entry with reservation, settled cost, and credit applied all
  `0.00`.

Do not claim benchmark validity, power sufficiency, or cloud readiness from the
synthetic P0.

### Step 9: Commit

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
