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
    resampling-task-block.schema.json
    resampling-analysis.schema.json

src/pneuma_lab/resampling_null/
    __init__.py
    __main__.py
    types.py
    artifacts.py
    assignment.py
    packets.py
    controller.py
    synthetic.py
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
    test_blinding.py
    test_analysis.py
    test_power.py
    test_cli.py

fixtures/resampling_null/
    p0-study.json
    p0-tasks.jsonl
    p0-power-grid.json
```

## Task 1: Core records and invariants

**Files:**

- Create: `src/pneuma_lab/resampling_null/__init__.py`
- Create: `src/pneuma_lab/resampling_null/types.py`
- Create: `tests/resampling_null/test_types.py`

### Step 1: Write the failing tests

Cover:

- canonical arm order is `REAL, SHAM, NONE, RESAMPLE`;
- `SHAM_PACKET_ONLY` is the verdict name; `APPARATUS_ONLY` is absent;
- four slot seeds are pairwise distinct;
- binary endpoints reject booleans, floats, and integers outside `{0, 1}`;
- resource counters reject negative or non-finite values;
- SHA-256 fields require exactly 64 lowercase hexadecimal characters;
- frozen records reject mutation; and
- infrastructure failure forces `success == 0`.

Start with this public shape:

```python
from dataclasses import dataclass
from enum import Enum


class Arm(str, Enum):
    REAL = "REAL"
    SHAM = "SHAM"
    NONE = "NONE"
    RESAMPLE = "RESAMPLE"


class Verdict(str, Enum):
    CAUSAL_CONTENT = "CAUSAL_CONTENT"
    SHAM_PACKET_ONLY = "SHAM_PACKET_ONLY"
    RESAMPLING_CONSISTENT = "RESAMPLING_CONSISTENT"
    HARMFUL_OR_MISDIRECTING = "HARMFUL_OR_MISDIRECTING"
    UNRESOLVED_RESAMPLING = "UNRESOLVED_RESAMPLING"
    PIPELINE_INVALID = "PIPELINE_INVALID"
    FEASIBILITY_NO_GO = "FEASIBILITY_NO_GO"


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    benchmark: str
    stratum: str
    lineage: str


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
class BranchOutcome:
    task_id: str
    benchmark: str
    opaque_arm_id: str
    success: int
    prefix_success: int
    partial_reward: float
    infrastructure_failure: bool
    counters: ResourceCounters
    artifact_sha256: str
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
Export only the stable record types from `__init__.py`.

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
- Create: `schemas/resampling-task-block.schema.json`
- Create: `schemas/resampling-analysis.schema.json`
- Create: `src/pneuma_lab/resampling_null/artifacts.py`
- Create: `tests/resampling_null/test_artifacts.py`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Modify: `tests/test_schema_loads.py`

### Step 1: Write failing contract tests

Test:

- a new `RESAMPLING_SCHEMA_FILES` tuple registers exactly the three schemas;
- all three use Draft 2020-12, `additionalProperties: false`,
  `x-pneuma-schema-kind: "resampling-study"`, and version `0.1.0`;
- unknown record kinds, unknown properties, duplicate JSON keys, `NaN`, and
  malformed digests fail closed;
- canonical digest is byte-identical across mapping insertion order;
- changing one nested outcome invalidates its recorded digest link;
- JSON and JSONL writes publish no partial output after serialization failure;
  and
- resampling schemas do not enter `INPUT_SCHEMA_FILES` or
  `OUTPUT_SCHEMA_FILES`.

Use record kinds:

```text
resampling_study_manifest
resampling_task_block
resampling_analysis
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
    "resampling-task-block.schema.json",
    "resampling-analysis.schema.json",
)
```

Include it in `ALL_SCHEMA_FILES` and `__all__`. Increment the expected count in
`tests/test_schema_loads.py` without changing frame counts.

Every record schema must require:

```json
{
    "record_kind": "one of the three constants",
    "schema_version": "0.1.0",
    "study_id": "non-empty stable identifier",
    "created_at": "UTC RFC3339 string",
    "provenance": {
        "design_sha256": "64 lowercase hex",
        "code_sha256": "64 lowercase hex"
    }
}
```

The task-block schema additionally requires the task/prefix/snapshot receipts,
four distinct slot receipts, packet audit, four outcomes, validity events, and
parent-manifest digest. The analysis schema requires configuration digest,
opaque projection digest, counts, both estimands, sharp p-values, simultaneous
bounds, `q0`, `r95`, gates, verdict, and artifact ancestry.

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
    "resampling_task_block": "resampling-task-block.schema.json",
    "resampling_analysis": "resampling-analysis.schema.json",
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


def write_record(path: Path, value: Mapping[str, object]) -> str:
    ...


def verify_digest_link(
    child: Mapping[str, object],
    field: str,
    parent: Mapping[str, object],
) -> None:
    ...
```

`load_record` decodes UTF-8 without BOM and uses an `object_pairs_hook` that
raises on duplicate keys. `validate_record` uses
`Draft202012Validator.iter_errors`, sorts errors deterministically, and rejects
non-finite numbers before schema validation. `write_record` validates fully
before calling the existing atomic writer.

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
- confirmation freeze rejects `assignment_mode == "synthetic_derangement"`.

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


def arm_capability(secret: bytes, task_id: str, arm: Arm) -> str:
    payload = f"resampling-null:v1:{task_id}\0{arm.value}".encode()
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()
```

Implement two distinct transactions:

```python
def seal_prefix_schedule(
    tasks: Sequence[TaskSpec],
    *,
    study_seed: int,
    secret: bytes,
) -> "PrefixSchedule":
    ...


def seal_branch_assignment(
    schedule: "PrefixSchedule",
    verifier_receipts: Sequence["FrozenVerifierReceipt"],
    *,
    secret: bytes,
) -> "AssignmentLedger":
    ...
```

The prefix schedule fixes roster, prefix/slot seeds, task order, and provider
lane before prefixes; it contains no donor or treatment. Only after all common
prefixes and verifier artifacts are frozen does `seal_branch_assignment`
validate their complete digest set, materialize the donor map, and draw
treatments. No branch endpoint is an input.

Precompute the 12 lexicographically ordered assignments of
`("REAL", "SHAM", "NO_PACKET", "NO_PACKET")` to four slots. Draw one with
`uniform_below(..., 12)`, then orient NONE/Z with a domain-separated
`uniform_below(..., 2)` call. Sort tasks by
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

### Step 1: Write failing packet tests

Cover:

- REAL and SHAM use identical field order, field count, severity multiset, and
  formatting;
- injected tokenizer reports equal token counts, while token IDs may differ;
- donor identifiers are replaced by type-preserving focal-safe aliases;
- SHAM evidence that collides with a true focal finding blocks the pair;
- impossible exact padding raises `PacketInvalid`;
- no packet contains donor task, lineage, arm, or capability identifiers;
- findings are never silently truncated;
- neutral padding cannot introduce executable instructions or identifiers; and
- repeated audit runs are byte-identical.

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


@dataclass(frozen=True, slots=True)
class VerifierFinding:
    component: str
    code: str
    severity: str
    evidence: str


@dataclass(frozen=True, slots=True)
class PacketPair:
    real_text: str
    sham_text: str
    real_token_ids: tuple[int, ...]
    sham_token_ids: tuple[int, ...]
    audit: Mapping[str, object]


def build_packet_pair(
    real: Sequence[VerifierFinding],
    donor: Sequence[VerifierFinding],
    *,
    tokenizer: Tokenizer,
    identifier_map: Mapping[str, str],
    true_focal_signatures: frozenset[str],
    neutral_pad_units: Sequence[str],
) -> PacketPair:
    ...
```

Serialize both packets through one template. Search deterministic combinations
of frozen neutral pad units by dynamic programming over tokenizer-length
deltas; do not mutate semantic fields. Validate exact subject-token count,
schema/field parity, severity parity, collision absence, and identifier
redaction before returning.

### Step 4: Prove green

```powershell
python -m pytest tests/resampling_null/test_packets.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/packets.py tests/resampling_null/test_packets.py
git commit -m "feat(resampling-null): build audited verifier packets"
```

## Task 5: Two-stage snapshot-paired synthetic controller

**Files:**

- Create: `src/pneuma_lab/resampling_null/controller.py`
- Create: `src/pneuma_lab/resampling_null/synthetic.py`
- Create: `tests/resampling_null/test_controller.py`

### Step 1: Write failing controller tests

Prove:

- the common prefix executes exactly once;
- a trigger can occur only after a completed tool boundary;
- all task prefixes/verifier artifacts can be sealed before any branch starts;
- each arm restores into a fresh environment instance;
- all four pre-branch visible-state digests and tokenized contexts are equal;
- all four continuation seed streams are distinct;
- arm labels follow the sealed slot allocation, never run order or outcome;
- REAL/SHAM receive their matched packets and NONE/RESAMPLE receive no message;
- all arms receive identical caps;
- a no-trigger terminal task runs no branches and emits four copies of `Y_0`;
- timeout, cap, malformed action, and arm-specific infrastructure failure become
  adverse zero;
- an arm-blind outage receipt created before any endpoint is readable may rerun
  the whole block once with identical snapshot, slots, seeds, and allocation;
- an incomplete full-block rerun emits four zeros and never deletes the task;
- no failed arm can change seed, task, slot, or sample ID on retry; and
- mutable state from one branch cannot leak into another.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_controller.py -q
```

Expected: import failure.

### Step 3: Add narrow execution protocols

```python
class SnapshotEnvironment(Protocol):
    def run_prefix(self, seed: int, caps: "PrefixCaps") -> "PrefixResult":
        ...

    def snapshot(self) -> bytes:
        ...

    def restore(self, payload: bytes) -> None:
        ...

    def visible_digest(self) -> str:
        ...

    def grade(self) -> tuple[int, float]:
        ...


class BranchSubject(Protocol):
    def continue_branch(
        self,
        *,
        context: tuple[Mapping[str, object], ...],
        packet: str | None,
        seed: int,
        caps: "BranchCaps",
    ) -> "BranchTrace":
        ...


def run_prefix(
    spec: TaskSpec,
    schedule: "TaskSchedule",
    *,
    environment_factory: Callable[[], SnapshotEnvironment],
    subject: BranchSubject,
    prefix_caps: "PrefixCaps",
) -> "FrozenPrefix":
    ...


def run_task_branches(
    frozen_prefix: "FrozenPrefix",
    assignment: "TaskAssignment",
    *,
    environment_factory: Callable[[], SnapshotEnvironment],
    subject: BranchSubject,
    packet_pair: PacketPair,
    branch_caps: "BranchCaps",
) -> dict[str, object]:
    ...
```

`run_prefix` runs one prefix, scores a disposable clone, runs the verifier on a
different disposable clone, and seals the snapshot/context/verifier receipt.
The orchestrator must finish all `run_prefix` calls before Task 3 materializes
the branch assignment and Task 4 constructs packets.

`run_task_branches` creates a fresh environment for every slot. It verifies the
restored visible digest and exact tokenized context before the subject can act.
It emits one schema-valid `resampling_task_block` and never reruns a single
arm.

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
git add src/pneuma_lab/resampling_null/controller.py src/pneuma_lab/resampling_null/synthetic.py tests/resampling_null/test_controller.py
git commit -m "feat(resampling-null): run snapshot-paired blocks"
```

## Task 6: Blinded projection and hash-gated unblinding

**Files:**

- Create: `src/pneuma_lab/resampling_null/blinding.py`
- Create: `tests/resampling_null/test_blinding.py`

### Step 1: Write failing blinding tests

Test:

- projection contains only opaque A/B/C/D capabilities;
- arm names, treatment names, packets, donor IDs, and secret bytes are absent
  from serialized projection;
- task order is deterministic;
- wrong secret fails;
- analysis-source digest mismatch blocks unblinding;
- first successful unblind appends a receipt;
- a second unblind cannot overwrite that receipt; and
- changing one projected outcome breaks its parent digest.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_blinding.py -q
```

Expected: import failure.

### Step 3: Implement

```python
def project_blinded(
    blocks: Sequence[Mapping[str, object]],
    ledger: "AssignmentLedger",
) -> dict[str, object]:
    ...


def unblind_projection(
    projection: Mapping[str, object],
    *,
    secret: bytes,
    expected_analysis_sha256: str,
    observed_analysis_sha256: str,
    receipt_path: Path,
) -> tuple[tuple["AnalysisRow", ...], dict[str, object]]:
    ...
```

Resolve arm identities only from HMAC capabilities. Persist neither plaintext
secret nor clear arm map in the projection. Write the receipt through the
ancestry-bound atomic artifact helper and refuse an existing target.

### Step 4: Prove green

```powershell
python -m pytest tests/resampling_null/test_blinding.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/blinding.py tests/resampling_null/test_blinding.py
git commit -m "feat(resampling-null): enforce blinded projection"
```

## Task 7: Registered sharp tests, average-effect bounds, and verdicts

**Files:**

- Create: `src/pneuma_lab/resampling_null/analysis.py`
- Create: `tests/resampling_null/test_analysis.py`

### Step 1: Write failing hand-calculation tests

Separate tests for:

- equal benchmark weighting versus naive row pooling;
- `content`, `excess`, `sham_packet`, `continuation`, `total`, and `null`
  contrasts;
- exact R/S swap tail for a two-task sharp-content fixture;
- exact one-of-three REAL reassignment tail for a sharp-excess fixture;
- add-one Monte Carlo p-value and recorded Monte Carlo SE;
- global 12-way allocation max-T Fisher p-value, labeled sharp-null only;
- multiplier covariance, critical value, and simultaneous lower bounds against a
  hand-computed small matrix;
- zero/non-finite SE blocks a positive claim;
- `q0` and exact equal-roster binomial `r95`;
- unequal-roster weighted-convolution `r95`;
- point screen is `>= 0.05` and resolution screen is `> r95`;
- benchmark-specific sensitivities use task units;
- every leave-one-language/domain estimate renormalizes within its benchmark and
  applies the executable `>= -0.05` rule;
- one fixture for every verdict; and
- `PIPELINE_INVALID` and `UNRESOLVED_RESAMPLING` take precedence over a
  positive estimate.

### Step 2: Prove red

```powershell
python -m pytest tests/resampling_null/test_analysis.py -q
```

Expected: import failure.

### Step 3: Implement the frozen API

```python
@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    alpha: float = 0.05
    delta_star: float = 0.05
    sharp_draws: int = 999_999
    multiplier_draws: int = 99_999


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


def multiplier_lower_bounds(
    rows: Sequence["AnalysisRow"],
    *,
    draws: int,
    seed: int,
) -> "SimultaneousBounds":
    ...


def resampling_resolution(
    rows: Sequence["AnalysisRow"],
) -> "ResolutionResult":
    ...


def analyze(
    rows: Sequence["AnalysisRow"],
    config: AnalysisConfig,
    *,
    seed: int,
) -> "AnalysisResult":
    ...
```

Use `numpy.random.Generator(numpy.random.Philox(seed))` with domain-separated
seeds. Enumerate small exact supports; otherwise sample the actual conditional
assignment mechanism. For average bounds, implement the design's
benchmark-stratified task-cluster Rademacher multiplier formula exactly. Label
those bounds `average_effect_asymptotic`, never `exact`.

For equal benchmark roster size and `m` NONE/Z-discordant tasks, compute:

```text
r95 = quantile_0.95(|2K - m| / (2n)), K ~ Binomial(m, 1/2)
```

Use integer dynamic programming for unequal task weights. `classify_verdict`
applies gates in this order:

1. pipeline validity/no-interference;
2. finite/positive standard errors;
3. harmful or misdirecting effect;
4. resampling resolution and `delta_star`;
5. both sharp p-values;
6. both simultaneous lower bounds;
7. per-benchmark non-negativity and every renormalized leave-one-stratum
   estimate `>= -0.05`;
8. `CAUSAL_CONTENT`;
9. `SHAM_PACKET_ONLY`;
10. `RESAMPLING_CONSISTENT`;
11. `FEASIBILITY_NO_GO`.

Record NumPy version, seeds, draw counts, enumeration/sample mode, Monte Carlo
error, weights, and every gate value.

### Step 4: Prove green

```powershell
python -m pytest tests/resampling_null/test_analysis.py -q
```

Expected: pass.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/analysis.py tests/resampling_null/test_analysis.py
git commit -m "feat(resampling-null): implement registered inference"
```

## Task 8: Frozen-grid P0 power and type-I simulator

**Files:**

- Create: `src/pneuma_lab/resampling_null/power.py`
- Create: `tests/resampling_null/test_power.py`
- Create: `fixtures/resampling_null/p0-power-grid.json`

### Step 1: Write failing simulator tests

Test:

- nuisance grid is exactly
  `p0={.10,.40,.70}`, `gamma={.60,.75,.90}`,
  `rho={0,.40,.80}`;
- cross-benchmark alternative has 729 ordered cells;
- the three null families have 2,187 ordered cells;
- all generated probabilities stay in `[.10,.95]`;
- four-variate pattern probabilities are non-negative, sum to one, and recover
  requested marginals/correlation within frozen tolerance;
- no-trigger patterns are `(B,B,B,B)` and remain in the denominator;
- triggered alternative has expected ITT effects `(0.15, 0.15)`;
- boundary A has both nulls, B has content null, C has excess null;
- exactly `gamma * n_b` tasks are triggered;
- triggered counts use `Multinomial(gamma * n_b, pi_trigger)`;
- no-trigger `1111` count uses
  `Binomial((1-gamma) * n_b, p0)`, with the remainder `0000`;
- identical configuration/seed yields byte-identical counts;
- every replicate invokes shared statistical gate functions from `analysis.py`,
  conditional on nonstatistical admissibility;
- the Gaussian-max critical value is monotone and matches a known independent
  case;
- Clopper-Pearson tails are `0.05/729` and `0.05/2187`;
- C160 power is no lower than C120 on a fixed easy cell; and
- a tiny test grid writes raw counts, intervals, numeric receipts, and verdict.

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
with frozen Gauss-Hermite nodes/weights and emit a normalization/marginal error
receipt. Reject a cell if any error exceeds the frozen tolerance; never clip a
negative probability silently.

Expose:

```python
@dataclass(frozen=True, slots=True)
class Nuisance:
    p0: float
    trigger_rate: float
    rho: float


def bernoulli_pattern_probabilities(
    marginals: tuple[float, float, float, float],
    rho: float,
) -> tuple[float, ...]:
    ...


def gaussian_max_critical(correlation: float, alpha: float) -> float:
    ...


def clopper_pearson(
    successes: int,
    trials: int,
    *,
    alpha: float,
) -> tuple[float, float]:
    ...


def simulate_power_grid(
    config: "PowerConfig",
    *,
    seed: int,
) -> dict[str, object]:
    ...
```

Use `numpy.random.Philox` and deterministic cell/replicate counter mapping.
Implement exact-binomial interval inversion with a bounded bisection over the
binomial tail; do not add SciPy merely for beta quantiles.

The production grid evaluates `n_b in {120, 160}` and 20,000 datasets per cell.
For each benchmark, set `m_b = gamma * n_b` exactly. Draw triggered pattern
counts as `Multinomial(m_b, pi_trigger)`. For the other tasks draw
`U_b ~ Binomial(n_b - m_b, p0)`, assign `U_b` to `1111`, and assign the
remainder to `0000`.

For P0 only, use the two-dimensional Gaussian-max critical value derived from
the estimated contrast correlation. Select the five lowest-power alternative
cells before validation and rerun 2,000 outer datasets through the full
99,999-draw multiplier routine. Freeze and write that selection before
validation outputs. Every selected cell must have an absolute gate-pass-rate
difference at most 0.01 and both methods must choose the same roster tier. On
failure, run the full multiplier routine for every cell or emit
`FEASIBILITY_NO_GO`.

The tier passes only if every Bonferroni Clopper-Pearson lower bound across 729
alternative cells is at least 0.80 and every upper bound across 2,187 null cells
is at most 0.05. Otherwise emit `FEASIBILITY_NO_GO`.

### Step 4: Prove the unit suite green

```powershell
python -m pytest tests/resampling_null/test_power.py -q
```

Expected: pass using a tiny fixture grid; the 20,000 × full-grid run is not a
unit test.

### Step 5: Commit

```powershell
git add src/pneuma_lab/resampling_null/power.py tests/resampling_null/test_power.py fixtures/resampling_null/p0-power-grid.json
git commit -m "feat(resampling-null): add joint P0 simulator"
```

## Task 9: CLI and deterministic synthetic P0

**Files:**

- Create: `src/pneuma_lab/resampling_null/cli.py`
- Create: `src/pneuma_lab/resampling_null/__main__.py`
- Create: `tests/resampling_null/test_cli.py`
- Create: `fixtures/resampling_null/p0-study.json`
- Create: `fixtures/resampling_null/p0-tasks.jsonl`

### Step 1: Write failing CLI tests

Call `main(argv)` directly and test:

- `selftest`;
- `schedule seal`;
- `synthetic prefixes`;
- `assignment seal`;
- `synthetic branches`;
- `project`;
- `analyze`;
- `power simulate`;
- refusal to overwrite any sealed artifact;
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
python -m pneuma_lab.resampling_null selftest --out <dir>
python -m pneuma_lab.resampling_null schedule seal --study <json> --tasks <jsonl> --secret-file <path> --out <json>
python -m pneuma_lab.resampling_null synthetic prefixes --study <json> --schedule <json> --out <dir>
python -m pneuma_lab.resampling_null assignment seal --schedule <json> --verifier-index <json> --secret-file <path> --out <json>
python -m pneuma_lab.resampling_null synthetic branches --study <json> --schedule <json> --assignment <json> --prefix-root <dir> --out <dir>
python -m pneuma_lab.resampling_null project --run-root <dir> --assignment <json> --out <json>
python -m pneuma_lab.resampling_null analyze --projection <json> --secret-file <path> --analysis-source <path> --out <json>
python -m pneuma_lab.resampling_null power simulate --grid <json> --out <json>
```

`selftest` executes the four schedule/prefix/assignment/branch phases with
separate sealed artifacts, runs 24 task blocks across two fake benchmarks, and
ends with:

- `CAUSAL_CONTENT`;
- zero invalid blocks;
- exact packet parity;
- four distinct slot seeds per block;
- exact snapshot restoration; and
- a stable artifact-root digest.

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
git add src/pneuma_lab/resampling_null/cli.py src/pneuma_lab/resampling_null/__main__.py tests/resampling_null/test_cli.py fixtures/resampling_null/p0-study.json fixtures/resampling_null/p0-tasks.jsonl
git commit -m "feat(resampling-null): expose deterministic P0 CLI"
```

## Task 10: Full local verification and plan receipt

**Files:**

- Modify: `docs/research/neurips-2026-workshop/15-decision-log.md`
- Modify: `docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md`
- Create under ignored build root:
  `build/research/neurips-2026-workshop/p0-core-receipt.json`

### Step 1: Run focused verification

```powershell
python -m pytest tests/resampling_null -q
python -m pytest tests/test_schema_loads.py tests/test_validate.py -q
```

Expected: all pass.

### Step 2: Run deterministic end-to-end verification twice

```powershell
python -m pneuma_lab.resampling_null selftest --out build/research/neurips-2026-workshop/p0-core-a
python -m pneuma_lab.resampling_null selftest --out build/research/neurips-2026-workshop/p0-core-b
$hashA = (Get-FileHash -LiteralPath 'build/research/neurips-2026-workshop/p0-core-a/artifact-root.json' -Algorithm SHA256).Hash
$hashB = (Get-FileHash -LiteralPath 'build/research/neurips-2026-workshop/p0-core-b/artifact-root.json' -Algorithm SHA256).Hash
if ($hashA -ne $hashB) { throw 'P0 determinism failure' }
```

Expected: identical hashes.

### Step 3: Run repository-wide verification

```powershell
python -m pneuma_lab.status --check
python -m pytest tests/ -q
git diff --check
git status --short
```

Expected: status checker passes, full default suite passes, whitespace check is
clean, and only intended branch changes remain.

### Step 4: Record zero spend and implementation decision

Append:

- one decision-log entry naming the implemented hashes, passed tests, known
  limits, and next benchmark-adapter gate; and
- one spend-ledger entry with reservation, settled cost, and credit applied all
  `0.00`.

Do not claim benchmark validity, power sufficiency, or cloud readiness from the
synthetic P0.

### Step 5: Commit

```powershell
git add docs/research/neurips-2026-workshop/15-decision-log.md docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md
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
