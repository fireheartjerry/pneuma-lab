"""Closed, non-executing authority contracts for registered P0 power work.

Task 8A deliberately stops before any screen or simulator.  This module only
turns manifest-owned bytes into typed authority/configuration values.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Literal, cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes, write_atomic_bytes

from .artifacts import _load_direct_scientific_parent, _read_ref, _ref_mapping, _artifact_ref_for_path, _prepare_destination
from .assignment import BytesField, U64Field, commitment_sha256, kdf_frame
from .authority_refs import closed_mapping, decode_artifact_ref
from .errors import RecordValidationError
from .json_io import load_json_bytes
from .types import ArtifactRef


POWER_AUTHORITY_MEDIA_TYPE = "application/vnd.pneuma.power-authority+json"
_AUTHORITY_COMMON_FIELDS = frozenset(
    {"schema_version", "authority_kind", "manifest_ref", "roster_ref", "tier_membership_sha256"}
)
_RNG_FIELDS = (
    "bit_generator", "contract_id", "counter_fields", "counter_frame",
    "draw_domains", "draw_kinds", "integer_encoding", "key_fields",
    "key_frame", "numpy_version", "root_u64",
)
_RNG_CONTRACT: dict[str, object] = {
    "bit_generator": "numpy.random.Philox",
    "contract_id": "power-philox-v1",
    "counter_fields": ["draw_domain", "phase", "cell_id", "replicate_index", "draw_kind", "draw_index"],
    "counter_frame": "power-rng-counter-v1",
    "draw_domains": ["screen", "grid", "validation"],
    "draw_kinds": [
        "screen_trigger_partition", "screen_triggered_pattern", "screen_no_trigger_success",
        "grid_trigger_partition", "grid_triggered_pattern", "grid_no_trigger_success",
        "gaussian_validation_trigger_partition", "gaussian_validation_triggered_pattern",
        "gaussian_validation_no_trigger_success", "multiplier_rademacher",
    ],
    "integer_encoding": "unsigned-big-endian",
    "key_fields": ["root_u64", "authority_kind", "tier_membership_sha256_raw32", "grid_content_sha256_raw32"],
    "key_frame": "power-rng-key-v1",
    "numpy_version": "2.3.5",
    "root_u64": 7640891576956012809,
}
RNG_CONTRACT_SHA256 = hashlib.sha256(canonical_json_bytes(_RNG_CONTRACT, indent=None)).hexdigest()


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
    counter_fields: tuple[str, ...]
    counter_frame: Literal["power-rng-counter-v1"]
    draw_domains: tuple[str, ...]
    draw_kinds: tuple[str, ...]
    integer_encoding: Literal["unsigned-big-endian"]
    key_fields: tuple[str, ...]
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


@dataclass(frozen=True, slots=True)
class PowerConfig:
    authority_ref: ArtifactRef
    grid_ref: ArtifactRef
    screen_topology_ref: ArtifactRef
    rng_contract_sha256: str


def _strict_sha256(value: object, *, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise RecordValidationError(f"{field} must be a lowercase SHA-256 digest")
    return cast(str, value)


def _manifest(ref: ArtifactRef, *, run_root: Path) -> Mapping[str, object]:
    document = _load_direct_scientific_parent(
        _ref_mapping(ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest"
    )
    payload = document.value["payload"]
    if not isinstance(payload, Mapping):
        raise RecordValidationError("study manifest payload must be an object")
    return payload


def _manifest_study_id(ref: ArtifactRef, *, run_root: Path) -> str:
    document = _load_direct_scientific_parent(
        _ref_mapping(ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest"
    )
    study_id = document.value["study_id"]
    if type(study_id) is not str or not study_id:
        raise RecordValidationError("study manifest has invalid study_id")
    return study_id


def _manifest_frozen_created_at(ref: ArtifactRef, *, run_root: Path) -> str:
    document = _load_direct_scientific_parent(
        _ref_mapping(ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest"
    )
    value = document.value["frozen_created_at"]
    if type(value) is not str or not value:
        raise RecordValidationError("study manifest has invalid frozen_created_at")
    return value


def _manifest_ref(payload: Mapping[str, object], name: str) -> ArtifactRef:
    return decode_artifact_ref(payload.get(name), field=f"manifest {name}")


def _load_roster(ref: ArtifactRef, *, run_root: Path) -> Mapping[str, object]:
    path, raw = _read_ref(ref, run_root=run_root)
    decoded = load_json_bytes(raw, source=path)
    roster = closed_mapping(decoded, fields={"record_kind", "schema_version", "roster_kind", "supported_tiers", "tasks"}, field="power roster")
    if roster["record_kind"] != "resampling_roster_v1" or roster["schema_version"] != "1":
        raise RecordValidationError("power roster has wrong identity")
    if roster["roster_kind"] not in {"synthetic_fixture", "eligible_confirmation"}:
        raise RecordValidationError("power roster has unsupported roster_kind")
    return roster


def _roster_rows(roster: Mapping[str, object]) -> dict[str, tuple[tuple[int, ...], tuple[tuple[str, str], ...]]]:
    """Return the exact accepted identity/tier/group surface for confirmation."""
    rows: dict[str, tuple[tuple[int, ...], tuple[tuple[str, str], ...]]] = {}
    for index, task_value in enumerate(cast(list[object], roster["tasks"])):
        task = closed_mapping(task_value, fields={"task_id", "benchmark", "stratum", "lineage", "groups", "tiers"}, field=f"power roster task[{index}]")
        task_id = task["task_id"]
        if type(task_id) is not str or not task_id or task_id in rows:
            raise RecordValidationError("power roster task IDs must be unique strict text")
        tiers = task["tiers"]
        groups = task["groups"]
        if not isinstance(tiers, list) or not isinstance(groups, list):
            raise RecordValidationError("power roster tiers/groups must be arrays")
        group_rows: list[tuple[str, str]] = []
        for group_index, group_value in enumerate(groups):
            group = closed_mapping(group_value, fields={"kind", "value"}, field=f"power roster task[{index}].groups[{group_index}]")
            if type(group["kind"]) is not str or type(group["value"]) is not str:
                raise RecordValidationError("power roster group fields must be strict text")
            group_rows.append((cast(str, group["kind"]), cast(str, group["value"])))
        rows[task_id] = (tuple(cast(list[int], tiers)), tuple(group_rows))
    return rows


def _validate_confirmation_eligibility(
    eligibility_ref: ArtifactRef,
    roster: Mapping[str, object],
    *,
    study_id: str,
    frozen_created_at: str,
    manifest_payload: Mapping[str, object],
    run_root: Path,
) -> None:
    """Prove the manifest-pinned eligibility source derives this exact roster.

    This is intentionally a closed source grammar.  A file that merely exists
    is not evidence of confirmation eligibility—cute try, attacker.
    """
    path, raw = _read_ref(eligibility_ref, run_root=run_root)
    value = load_json_bytes(raw, source=path)
    fields = {
        "record_kind", "schema_version", "study_id", "precommit", "precommit_sha256",
        "timestamp_receipt", "beacon_receipt", "roster_local_nonce_hex", "roster_seed_sha256",
        "accepted_task_ids", "rejected_task_ids", "tier_membership", "group_labels", "reserves",
    }
    eligibility = closed_mapping(value, fields=fields, field="confirmation eligibility manifest")
    if eligibility["record_kind"] != "resampling_eligibility_manifest_v1" or eligibility["schema_version"] != "1" or eligibility["study_id"] != study_id:
        raise RecordValidationError("confirmation eligibility manifest has wrong identity or study_id")
    precommit = closed_mapping(eligibility["precommit"], fields={"study_id", "qualification_universe_sha256", "roster_local_nonce_commitment_sha256", "schedule_seed_commitment_sha256", "assignment_master_key_commitment_sha256"}, field="confirmation eligibility precommit")
    if precommit["study_id"] != study_id:
        raise RecordValidationError("confirmation eligibility precommit study_id differs")
    for field in ("qualification_universe_sha256", "roster_local_nonce_commitment_sha256", "schedule_seed_commitment_sha256", "assignment_master_key_commitment_sha256"):
        _strict_sha256(precommit[field], field=f"confirmation eligibility precommit {field}")
    precommit_digest = hashlib.sha256(canonical_json_bytes(precommit, indent=None)).hexdigest()
    if eligibility["precommit_sha256"] != precommit_digest:
        raise RecordValidationError("confirmation eligibility precommit_sha256 does not bind precommit bytes")
    timestamp = closed_mapping(eligibility["timestamp_receipt"], fields={"precommit_sha256", "timestamp"}, field="confirmation eligibility timestamp receipt")
    if timestamp["precommit_sha256"] != precommit_digest or timestamp["timestamp"] != frozen_created_at:
        raise RecordValidationError("confirmation eligibility timestamp receipt does not bind precommit")
    beacon = closed_mapping(eligibility["beacon_receipt"], fields={"chain_hash", "round", "randomness_hex"}, field="confirmation eligibility beacon receipt")
    if beacon["chain_hash"] != "8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce" or type(beacon["round"]) is not int or beacon["round"] < 0 or type(beacon["randomness_hex"]) is not str:
        raise RecordValidationError("confirmation eligibility beacon receipt has invalid frozen contract")
    try:
        nonce = bytes.fromhex(cast(str, eligibility["roster_local_nonce_hex"]))
        randomness = bytes.fromhex(cast(str, beacon["randomness_hex"]))
    except ValueError as exc:
        raise RecordValidationError("confirmation eligibility nonce/beacon randomness must be hex") from exc
    if len(nonce) != 32 or len(randomness) != 32:
        raise RecordValidationError("confirmation eligibility nonce/beacon randomness must be 32 bytes")
    for field in ("roster_local_nonce_commitment_sha256", "schedule_seed_commitment_sha256", "assignment_master_key_commitment_sha256"):
        if precommit[field] != manifest_payload[field]:
            raise RecordValidationError(f"confirmation eligibility precommit {field} differs from study manifest")
    expected_nonce_commitment = commitment_sha256(
        "roster-local-nonce", study_id, BytesField(nonce)
    )
    if expected_nonce_commitment != manifest_payload["roster_local_nonce_commitment_sha256"]:
        raise RecordValidationError("confirmation eligibility nonce reveal does not match study manifest commitment")
    expected_seed = hashlib.sha256(kdf_frame("roster-seed-v1", [
        BytesField(bytes.fromhex(precommit_digest)), BytesField(nonce),
        BytesField(bytes.fromhex(cast(str, beacon["chain_hash"]))),
        U64Field(cast(int, beacon["round"])), BytesField(randomness),
    ])).hexdigest()
    if eligibility["roster_seed_sha256"] != expected_seed:
        raise RecordValidationError("confirmation eligibility roster_seed_sha256 is not the derived ceremony seed")
    accepted = eligibility["accepted_task_ids"]
    rejected = eligibility["rejected_task_ids"]
    if not isinstance(accepted, list) or not isinstance(rejected, list) or any(type(value) is not str or not value for value in [*accepted, *rejected]) or accepted != sorted(set(accepted)) or rejected != sorted(set(rejected)) or set(accepted) & set(rejected):
        raise RecordValidationError("confirmation eligibility accepted/rejected task IDs must be disjoint strict sorted sets")
    roster_rows = _roster_rows(roster)
    if accepted != sorted(roster_rows):
        raise RecordValidationError("confirmation eligibility accepted task IDs do not exactly reproduce roster")
    memberships = closed_mapping(eligibility["tier_membership"], fields={"120", "160"}, field="confirmation eligibility tier_membership")
    tier_ids: dict[int, list[str]] = {}
    for tier in (120, 160):
        values = memberships[str(tier)]
        if not isinstance(values, list) or any(type(value) is not str for value in values) or values != sorted(set(values)):
            raise RecordValidationError("confirmation eligibility tier membership must be sorted unique task IDs")
        tier_ids[tier] = cast(list[str], values)
        if set(values) != {task_id for task_id, (tiers, _groups) in roster_rows.items() if tier in tiers}:
            raise RecordValidationError("confirmation eligibility tier membership differs from roster")
    if not set(tier_ids[160]).issubset(tier_ids[120]):
        raise RecordValidationError("confirmation eligibility C160 membership must be nested in C120")
    labels = eligibility["group_labels"]
    if not isinstance(labels, Mapping) or set(labels) != set(roster_rows):
        raise RecordValidationError("confirmation eligibility group labels must exactly cover roster")
    for task_id, (_tiers, expected_groups) in roster_rows.items():
        groups = labels[task_id]
        if not isinstance(groups, list):
            raise RecordValidationError("confirmation eligibility group labels must be arrays")
        actual: list[tuple[str, str]] = []
        for group_index, group_value in enumerate(groups):
            group = closed_mapping(group_value, fields={"kind", "value"}, field=f"confirmation eligibility group_labels.{task_id}[{group_index}]")
            if type(group["kind"]) is not str or type(group["value"]) is not str:
                raise RecordValidationError("confirmation eligibility group label must use strict text")
            actual.append((cast(str, group["kind"]), cast(str, group["value"])))
        if tuple(actual) != expected_groups:
            raise RecordValidationError("confirmation eligibility group labels differ from roster")
    reserves = eligibility["reserves"]
    if not isinstance(reserves, list) or any(type(value) is not str or not value for value in reserves) or reserves != sorted(set(reserves)) or set(reserves) & set(accepted):
        raise RecordValidationError("confirmation eligibility reserves must be ordered, unique, and disjoint from accepted roster")


def _tier_membership_sha256(roster: Mapping[str, object]) -> str:
    tasks = roster["tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise RecordValidationError("power roster tasks must be a non-empty array")
    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    group_order = {"language": 0, "domain": 1, "issue_family": 2}
    for index, task_value in enumerate(tasks):
        task = closed_mapping(task_value, fields={"task_id", "benchmark", "stratum", "lineage", "groups", "tiers"}, field=f"power roster task[{index}]")
        task_id, benchmark = task["task_id"], task["benchmark"]
        if type(task_id) is not str or type(benchmark) is not str or not task_id or not benchmark:
            raise RecordValidationError("power roster task identity must be non-empty strict text")
        identity = (benchmark, task_id)
        if identity in seen:
            raise RecordValidationError("power roster tasks must have unique benchmark/task_id")
        seen.add(identity)
        tiers = task["tiers"]
        if not isinstance(tiers, list) or not tiers or any(type(tier) is not int for tier in tiers) or tiers != sorted(set(tiers)) or any(tier not in (120, 160) for tier in tiers):
            raise RecordValidationError("power roster tiers must be a strict non-empty C120/C160 subset")
        groups_value = task["groups"]
        if not isinstance(groups_value, list):
            raise RecordValidationError("power roster groups must be an array")
        groups: list[dict[str, str]] = []
        group_keys: list[tuple[int, str]] = []
        for group_index, group_value in enumerate(groups_value):
            group = closed_mapping(group_value, fields={"kind", "value"}, field=f"power roster task[{index}].groups[{group_index}]")
            kind, value = group["kind"], group["value"]
            if type(kind) is not str or type(value) is not str or not value or kind not in group_order:
                raise RecordValidationError("power roster group must use a registered non-empty kind/value")
            group_keys.append((group_order[kind], value))
            groups.append({"kind": kind, "value": value})
        if group_keys != sorted(set(group_keys)):
            raise RecordValidationError("power roster groups must be unique in frozen kind/value order")
        rows.append({"benchmark": benchmark, "groups": groups, "task_id": task_id, "tiers": tiers})
    if [(row["benchmark"], row["task_id"]) for row in rows] != sorted((row["benchmark"], row["task_id"]) for row in rows):
        raise RecordValidationError("power roster tasks must be UTF-8 ordered by benchmark/task_id")
    return hashlib.sha256(canonical_json_bytes({"rows": rows, "schema_version": "1"}, indent=None)).hexdigest()


def _authority_from_manifest(manifest_ref: ArtifactRef, *, run_root: Path, expected_kind: str) -> PowerAuthority:
    manifest = _manifest(manifest_ref, run_root=run_root)
    roster_ref = _manifest_ref(manifest, "roster_ref")
    roster = _load_roster(roster_ref, run_root=run_root)
    eligibility = manifest.get("eligibility_manifest_ref")
    membership = _tier_membership_sha256(roster)
    if expected_kind == "synthetic_validation":
        if roster["roster_kind"] != "synthetic_fixture" or eligibility is not None:
            raise RecordValidationError("synthetic authority requires synthetic_fixture and null eligibility_manifest_ref")
        return SyntheticPowerAuthority("1", "synthetic_validation", manifest_ref, roster_ref, membership)
    if roster["roster_kind"] != "eligible_confirmation":
        raise RecordValidationError("roster-bound authority requires eligible_confirmation roster")
    # `ConfirmationPreflightRegistry` deliberately exposes no reviewed live
    # ceremony adapter.  A local JSON beacon/timestamp receipt cannot prove it
    # was externally authenticated, so accepting one here would mint false
    # confirmation authority.  Future support must arrive through a
    # manifest-approved opaque capability, never a caller callback or blob.
    raise RecordValidationError(
        "roster-bound power authority unavailable: no reviewed verified ceremony adapter"
    )


def _authority_value(authority: PowerAuthority) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": authority.schema_version,
        "authority_kind": authority.authority_kind,
        "manifest_ref": _ref_mapping(authority.manifest_ref),
        "roster_ref": _ref_mapping(authority.roster_ref),
        "tier_membership_sha256": authority.tier_membership_sha256,
    }
    if isinstance(authority, RosterBoundPowerAuthority):
        value["eligibility_manifest_ref"] = _ref_mapping(authority.eligibility_manifest_ref)
    return value


def _seal(authority: PowerAuthority, *, run_root: Path, out: Path) -> ArtifactRef:
    target, _ = _prepare_destination(out, run_root)
    write_atomic_bytes(target, canonical_json_bytes(_authority_value(authority), indent=None))
    return _artifact_ref_for_path(target, run_root, "power_authority", POWER_AUTHORITY_MEDIA_TYPE)


def seal_synthetic_power_authority(manifest_ref: ArtifactRef, *, run_root: Path, out: Path) -> ArtifactRef:
    """Seal the sole synthetic arm derived from the referenced manifest."""
    if type(manifest_ref) is not ArtifactRef:
        raise TypeError("manifest_ref must be an exact ArtifactRef")
    return _seal(_authority_from_manifest(manifest_ref, run_root=run_root, expected_kind="synthetic_validation"), run_root=run_root, out=out)


def seal_roster_bound_power_authority(manifest_ref: ArtifactRef, *, run_root: Path, out: Path) -> ArtifactRef:
    """Seal the sole confirmation arm; no eligibility/roster override exists."""
    if type(manifest_ref) is not ArtifactRef:
        raise TypeError("manifest_ref must be an exact ArtifactRef")
    return _seal(_authority_from_manifest(manifest_ref, run_root=run_root, expected_kind="roster_bound_selection"), run_root=run_root, out=out)


def load_power_authority(authority_ref: ArtifactRef, *, run_root: Path) -> PowerAuthority:
    """Load canonical blob bytes and repeat all manifest/roster proofs."""
    if type(authority_ref) is not ArtifactRef or authority_ref.media_type != POWER_AUTHORITY_MEDIA_TYPE:
        raise RecordValidationError("power authority_ref must use the closed power-authority media type")
    path, raw = _read_ref(authority_ref, run_root=run_root)
    value = load_json_bytes(raw, source=path)
    if canonical_json_bytes(value, indent=None) != raw:
        raise RecordValidationError("power authority bytes must be compact canonical JSON")
    if not isinstance(value, Mapping):
        raise RecordValidationError("power authority must be a JSON object")
    kind = value.get("authority_kind")
    fields = _AUTHORITY_COMMON_FIELDS | ({"eligibility_manifest_ref"} if kind == "roster_bound_selection" else set())
    decoded = closed_mapping(value, fields=fields, field="power authority")
    if decoded["schema_version"] != "1" or kind not in {"synthetic_validation", "roster_bound_selection"}:
        raise RecordValidationError("power authority has unsupported identity")
    manifest_ref = decode_artifact_ref(decoded["manifest_ref"], field="power authority manifest_ref")
    expected = _authority_from_manifest(manifest_ref, run_root=run_root, expected_kind=cast(str, kind))
    if _authority_value(expected) != dict(decoded):
        raise RecordValidationError("power authority differs from manifest-derived closed authority")
    return expected


def _load_power_grid(grid_ref: ArtifactRef, *, run_root: Path) -> PowerGridSpec:
    """Decode the exact manifest fixture; all numeric science stays closed."""
    path, raw = _read_ref(grid_ref, run_root=run_root)
    value = load_json_bytes(raw, source=path)
    expected_fields = {
        "schema_version", "benchmark_tiers", "p0_values", "trigger_rates", "latent_rhos",
        "datasets_per_cell", "screen_datasets_per_cell", "max_projected_wall_seconds",
        "validation_cell_count", "validation_datasets_per_cell", "multiplier_draws",
        "target_effect", "target_power", "familywise_alpha", "gauss_hermite_order",
        "gauss_legendre_order", "probability_tolerance", "gaussian_root_tolerance",
        "gaussian_root_max_iterations", "clopper_pearson_tolerance", "clopper_pearson_max_iterations", "rng",
    }
    grid = closed_mapping(value, fields=expected_fields, field="power grid")
    if grid["schema_version"] != "1":
        raise RecordValidationError("power grid has unsupported schema_version")
    if grid["benchmark_tiers"] != [120, 160] or grid["p0_values"] != [0.1, 0.4, 0.7] or grid["trigger_rates"] != [0.6, 0.75, 0.9] or grid["latent_rhos"] != [0.0, 0.4, 0.8]:
        raise RecordValidationError("power grid does not contain the frozen P0 nuisance grid")
    for field, expected in (("datasets_per_cell", 20000), ("screen_datasets_per_cell", 200), ("max_projected_wall_seconds", 43200), ("validation_cell_count", 5), ("validation_datasets_per_cell", 2000), ("multiplier_draws", 99999), ("target_effect", 0.15), ("target_power", 0.8), ("familywise_alpha", 0.05), ("gauss_hermite_order", 96), ("gauss_legendre_order", 128), ("probability_tolerance", 1e-10), ("gaussian_root_tolerance", 1e-10), ("gaussian_root_max_iterations", 200), ("clopper_pearson_tolerance", 1e-12), ("clopper_pearson_max_iterations", 200)):
        if grid[field] != expected:
            raise RecordValidationError(f"power grid {field} differs from the frozen P0 contract")
    rng = closed_mapping(grid["rng"], fields=_RNG_FIELDS, field="power grid rng")
    if rng != _RNG_CONTRACT:
        raise RecordValidationError("power grid RNG contract differs from the frozen P0 contract")
    return PowerGridSpec("1", (120, 160), (0.1, 0.4, 0.7), (0.6, 0.75, 0.9), (0.0, 0.4, 0.8), 20000, 200, 43200, 5, 2000, 99999, 0.15, 0.8, 0.05, 96, 128, 1e-10, 1e-10, 200, 1e-12, 200, PowerRngContract(**cast(dict[str, object], rng)))


def grid_content_sha256(grid_ref: ArtifactRef, *, run_root: Path) -> str:
    """Return the scientific grid digest only after complete closed parsing."""
    path, raw = _read_ref(grid_ref, run_root=run_root)
    value = load_json_bytes(raw, source=path)
    if canonical_json_bytes(value, indent=None) != raw:
        raise RecordValidationError("power grid bytes must be compact canonical JSON")
    _load_power_grid(grid_ref, run_root=run_root)
    return hashlib.sha256(raw).hexdigest()


def load_power_config(authority_ref: ArtifactRef, grid_ref: ArtifactRef, screen_topology_ref: ArtifactRef, *, run_root: Path) -> PowerConfig:
    """Return the only public config constructor, rejecting all ref overrides."""
    authority = load_power_authority(authority_ref, run_root=run_root)
    manifest = _manifest(authority.manifest_ref, run_root=run_root)
    if grid_ref != _manifest_ref(manifest, "power_grid_ref") or screen_topology_ref != _manifest_ref(manifest, "power_screen_topology_ref"):
        raise RecordValidationError("power grid/topology refs must exactly equal manifest-bound refs")
    grid_content_sha256(grid_ref, run_root=run_root)
    _read_ref(screen_topology_ref, run_root=run_root)
    return PowerConfig(authority_ref, grid_ref, screen_topology_ref, RNG_CONTRACT_SHA256)


__all__ = (
    "POWER_AUTHORITY_MEDIA_TYPE", "RNG_CONTRACT_SHA256", "PowerAuthority", "PowerConfig", "PowerGridSpec",
    "RosterBoundPowerAuthority", "SyntheticPowerAuthority", "grid_content_sha256", "load_power_authority", "load_power_config",
    "seal_roster_bound_power_authority", "seal_synthetic_power_authority",
)
