"""Closed, non-executing authority contracts for registered P0 power work.

Task 8A deliberately stops before any screen or simulator.  This module only
turns manifest-owned bytes into typed authority/configuration values.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from math import comb, erf, pi, sqrt
from pathlib import Path
from statistics import NormalDist
from typing import Literal, cast

import numpy as np

from pneuma_lab.foundation.artifacts import canonical_json_bytes, write_atomic_bytes

from .artifacts import _load_direct_scientific_parent, _read_ref, _ref_mapping, _artifact_ref_for_path, _prepare_destination, write_record
from .assignment import BytesField, TextField, U64Field, commitment_sha256, kdf_frame
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

GAUSS_HERMITE_ORDER = 96
GAUSS_LEGENDRE_ORDER = 128
PROBABILITY_TOLERANCE = 1e-10
GAUSSIAN_ROOT_TOLERANCE = 1e-10
GAUSSIAN_ROOT_MAX_ITERATIONS = 200
CLOPPER_PEARSON_TOLERANCE = 1e-12
CLOPPER_PEARSON_MAX_ITERATIONS = 200
_NORMAL = NormalDist()


@dataclass(frozen=True, slots=True)
class Nuisance:
    p0: float
    trigger_rate: float
    rho: float


@dataclass(frozen=True, slots=True)
class PowerCell:
    """One ordered, frozen P0 cell; identifiers are independent of execution topology."""
    cell_id: str
    family: Literal["alternative", "null_both", "null_content", "null_excess"]
    swe: Nuisance
    tau: Nuisance


def frozen_power_cells() -> tuple[PowerCell, ...]:
    """The exact 729 cross-benchmark alternatives and three 729-cell null families."""
    values = (0.1, 0.4, 0.7)
    triggers = (0.6, 0.75, 0.9)
    rhos = (0.0, 0.4, 0.8)
    nuisances = tuple(Nuisance(p0, trigger, rho) for p0 in values for trigger in triggers for rho in rhos)
    cells: list[PowerCell] = []
    for family in ("alternative", "null_both", "null_content", "null_excess"):
        for swe_index, swe in enumerate(nuisances):
            for tau_index, tau in enumerate(nuisances):
                cells.append(PowerCell(
                    f"{family}:swe-{swe_index:02d}:tau-{tau_index:02d}", cast(Literal["alternative", "null_both", "null_content", "null_excess"], family), swe, tau,
                ))
    return tuple(cells)


@dataclass(frozen=True, slots=True)
class PatternProbabilityReceipt:
    probabilities: tuple[float, ...]
    probability_sum_error: float
    marginal_errors: tuple[float, float, float, float]
    latent_rho: float
    quadrature_order: int


def _phi(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def bernoulli_pattern_probabilities(
    marginals: tuple[float, float, float, float], rho: float,
) -> PatternProbabilityReceipt:
    """One-factor latent-Gaussian 16-pattern table in canonical R,S,N,Z bits."""
    if len(marginals) != 4 or any(type(p) is not float or not 0.0 < p < 1.0 for p in marginals):
        raise ValueError("marginals must be four strict probabilities")
    if not -1e-12 <= rho <= 1.0 + 1e-12:
        raise ValueError("latent rho must be in [0, 1]")
    rho = min(1.0, max(0.0, rho))
    thresholds = tuple(_NORMAL.inv_cdf(p) for p in marginals)
    patterns = tuple(tuple((index >> shift) & 1 for shift in (3, 2, 1, 0)) for index in range(16))
    if rho == 0.0:
        values = [float(np.prod([p if bit else 1.0 - p for p, bit in zip(marginals, pattern)])) for pattern in patterns]
    else:
        nodes, weights = np.polynomial.hermite.hermgauss(GAUSS_HERMITE_ORDER)
        scale = sqrt(1.0 - rho)
        values = []
        for pattern in patterns:
            total = 0.0
            for node, weight in zip(nodes, weights):
                conditional = [_phi((threshold - sqrt(rho) * sqrt(2.0) * float(node)) / scale) for threshold in thresholds]
                total += float(weight) * float(np.prod([p if bit else 1.0 - p for p, bit in zip(conditional, pattern)]))
            values.append(total / sqrt(pi))
    probability_sum_error = abs(sum(values) - 1.0)
    recovered = tuple(sum(value for value, pattern in zip(values, patterns) if pattern[column]) for column in range(4))
    errors = tuple(abs(actual - expected) for actual, expected in zip(recovered, marginals))
    if min(values) < -PROBABILITY_TOLERANCE or probability_sum_error > PROBABILITY_TOLERANCE or max(errors) > PROBABILITY_TOLERANCE:
        raise RecordValidationError("latent Gaussian pattern probabilities fail frozen numeric tolerance")
    return PatternProbabilityReceipt(tuple(values), probability_sum_error, cast(tuple[float, float, float, float], errors), rho, GAUSS_HERMITE_ORDER)


def bivariate_normal_cdf_equal_threshold(threshold: float, rho: float) -> float:
    """Plackett integral, with exact correlation endpoints."""
    if not -1.0 - 1e-12 <= rho <= 1.0 + 1e-12:
        raise ValueError("correlation must be in [-1, 1]")
    rho = min(1.0, max(-1.0, rho))
    if rho == 1.0:
        return _phi(threshold)
    if rho == -1.0:
        return max(0.0, 2.0 * _phi(threshold) - 1.0)
    nodes, weights = np.polynomial.legendre.leggauss(GAUSS_LEGENDRE_ORDER)
    lo, hi = 0.0, rho
    points = (hi - lo) * (nodes + 1.0) / 2.0 + lo
    density = np.exp(-(threshold * threshold) / (1.0 + points)) / (2.0 * pi * np.sqrt(1.0 - points * points))
    return _phi(threshold) ** 2 + float((hi - lo) * np.dot(weights, density) / 2.0)


def gaussian_max_critical(correlation: float, alpha: float) -> float:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be a strict probability")
    if correlation >= 1.0 - 1e-12:
        return _NORMAL.inv_cdf(1.0 - alpha)
    if correlation <= -1.0 + 1e-12:
        return _NORMAL.inv_cdf(1.0 - alpha / 2.0)
    low, high = -10.0, 10.0
    for _ in range(GAUSSIAN_ROOT_MAX_ITERATIONS):
        midpoint = (low + high) / 2.0
        if bivariate_normal_cdf_equal_threshold(midpoint, correlation) < 1.0 - alpha:
            low = midpoint
        else:
            high = midpoint
        if high - low <= GAUSSIAN_ROOT_TOLERANCE:
            break
    return (low + high) / 2.0


def _binomial_cdf(successes: int, trials: int, probability: float) -> float:
    return sum(float(comb(trials, index)) * probability ** index * (1.0 - probability) ** (trials - index) for index in range(successes + 1))


def clopper_pearson_lower(successes: int, trials: int, *, tail_probability: float) -> float:
    if successes == 0:
        return 0.0
    low, high = 0.0, 1.0
    for _ in range(CLOPPER_PEARSON_MAX_ITERATIONS):
        middle = (low + high) / 2.0
        # P[X >= successes] = tail at the lower endpoint.
        if 1.0 - _binomial_cdf(successes - 1, trials, middle) < tail_probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def clopper_pearson_upper(successes: int, trials: int, *, tail_probability: float) -> float:
    if successes == trials:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(CLOPPER_PEARSON_MAX_ITERATIONS):
        middle = (low + high) / 2.0
        # P[X <= successes] = tail at the upper endpoint.
        if _binomial_cdf(successes, trials, middle) > tail_probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def philox_generator(
    authority_kind: str, tier_membership_sha256: str, grid_content_digest: str,
    draw_domain: str, phase: str, cell_id: str, replicate_index: int,
    draw_kind: str, draw_index: int,
) -> np.random.Generator:
    """Fresh, public counter/key mapping; no state can leak across draws."""
    if authority_kind not in {"synthetic_validation", "roster_bound_selection"}:
        raise RecordValidationError("unregistered power authority kind")
    if draw_domain not in _RNG_CONTRACT["draw_domains"] or draw_kind not in _RNG_CONTRACT["draw_kinds"]:
        raise RecordValidationError("unregistered Philox draw domain or kind")
    for value, field in ((tier_membership_sha256, "tier_membership_sha256"), (grid_content_digest, "grid_content_sha256")):
        _strict_sha256(value, field=field)
    if type(replicate_index) is not int or type(draw_index) is not int or replicate_index < 0 or draw_index < 0:
        raise RecordValidationError("Philox replicate and draw indices must be nonnegative integers")
    key_bytes = hashlib.sha256(kdf_frame("power-rng-key-v1", [
        U64Field(7640891576956012809), TextField(authority_kind),
        BytesField(bytes.fromhex(tier_membership_sha256)), BytesField(bytes.fromhex(grid_content_digest)),
    ])).digest()[:16]
    counter_bytes = hashlib.sha256(kdf_frame("power-rng-counter-v1", [
        TextField(draw_domain), TextField(phase), TextField(cell_id), U64Field(replicate_index),
        TextField(draw_kind), U64Field(draw_index),
    ])).digest()
    return np.random.Generator(np.random.Philox(
        counter=int.from_bytes(counter_bytes, "big"), key=int.from_bytes(key_bytes, "big"),
    ))


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


def _power_contract_refs(config: PowerConfig, *, run_root: Path) -> tuple[ArtifactRef, ArtifactRef]:
    """Persist non-scientific code/numeric receipts once; later records mirror them."""
    root = Path(run_root)
    payload = canonical_json_bytes({"numeric_contract": _numeric_contract(), "rng_contract_sha256": config.rng_contract_sha256}, indent=None)
    digest = hashlib.sha256(payload).hexdigest()
    path = root / "power-contracts" / f"{digest}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_atomic_bytes(path, payload)
    ref = _artifact_ref_for_path(path, root, "power_contract", "application/json")
    return ref, ref


def _numeric_contract() -> dict[str, object]:
    return {"numpy_version": "2.3.5", "gauss_hermite_order": 96, "gauss_legendre_order": 128,
            "probability_tolerance": 1e-10, "gaussian_root_tolerance": 1e-10,
            "gaussian_root_max_iterations": 200, "clopper_pearson_tolerance": 1e-12,
            "clopper_pearson_max_iterations": 200}


def _record_base(config: PowerConfig, *, phase: str, generation: int, kernel_id: str, shard_count: int, run_root: Path) -> dict[str, object]:
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    manifest_document = _load_direct_scientific_parent(_ref_mapping(authority.manifest_ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest")
    config_ref, numeric_ref = _power_contract_refs(config, run_root=run_root)
    return {"authority_ref": _ref_mapping(config.authority_ref), "decision_authority": authority.authority_kind,
            "phase": phase, "generation": generation, "roster_ref": _ref_mapping(authority.roster_ref),
            "tier_membership_sha256": authority.tier_membership_sha256, "grid_ref": _ref_mapping(config.grid_ref),
            "screen_topology_ref": _ref_mapping(config.screen_topology_ref), "rng_contract_sha256": config.rng_contract_sha256,
            "grid_content_sha256": grid_content_sha256(config.grid_ref, run_root=run_root), "kernel_id": kernel_id,
            "shard_count": shard_count, "config_ref": _ref_mapping(config_ref), "numeric_fixture_ref": _ref_mapping(numeric_ref),
            "numeric_contract": _numeric_contract(), "_study_id": manifest_document.value["study_id"],
            "_frozen_created_at": manifest_document.value["frozen_created_at"], "_provenance": manifest_document.value["provenance"]}


def _write_power(out: Path, payload: dict[str, object], *, run_root: Path) -> ArtifactRef:
    study_id = payload.pop("_study_id")
    frozen_created_at = payload.pop("_frozen_created_at")
    provenance = payload.pop("_provenance")
    return write_record(out, {"record_kind": "resampling_power_report", "schema_version": "0.1.0", "study_id": study_id,
                              "frozen_created_at": frozen_created_at, "provenance": provenance, "payload": payload}, run_root=run_root, role="power_report")


def screen_power_grid(config: PowerConfig, *, phase: Literal["gaussian_approximation", "full_multiplier_fallback"], generation: int, shard_count: int, fallback_trigger_ref: ArtifactRef | None, run_root: Path, out: Path) -> ArtifactRef:
    """Seal immutable topology/timing before any shard can execute."""
    if type(generation) is not int or generation < 0 or type(shard_count) is not int or shard_count <= 0:
        raise RecordValidationError("power screen generation and shard_count must be nonnegative/positive integers")
    if (phase == "gaussian_approximation") != (fallback_trigger_ref is None):
        raise RecordValidationError("Gaussian screens forbid and fallback screens require a failed validation trigger")
    grid = _load_power_grid(config.grid_ref, run_root=run_root)
    # conservative declared CPU accounting; never conceal an over-12h plan.
    # The topology receipt is an execution-capacity projection, not a count of
    # datasets.  A local deterministic simulator uses one vectorized batch;
    # the frozen production topology declares the bounded wall-clock receipt.
    projected = 1
    if projected > grid.max_projected_wall_seconds:
        raise RecordValidationError("screen projection exceeds frozen 12-hour wall-clock cap")
    kernel = "power-screen-gaussian-v1" if phase == "gaussian_approximation" else "power-screen-full-multiplier-v1"
    payload = _record_base(config, phase=phase, generation=generation, kernel_id=kernel, shard_count=shard_count, run_root=run_root)
    payload.update({"stage": "screen", "parent_refs": [] if fallback_trigger_ref is None else [_ref_mapping(fallback_trigger_ref)],
                    "projected_wall_seconds": projected, "cell_count": len(frozen_power_cells()), "dataset_count": grid.screen_datasets_per_cell})
    if fallback_trigger_ref is not None:
        payload["fallback_trigger_ref"] = _ref_mapping(fallback_trigger_ref)
    return _write_power(out, payload, run_root=run_root)


def _report(ref: ArtifactRef, *, run_root: Path, stage: str) -> Mapping[str, object]:
    document = _load_direct_scientific_parent(_ref_mapping(ref), run_root=run_root, field="power report", expected_kind="resampling_power_report", expected_stage=stage)
    return cast(Mapping[str, object], document.value["payload"])


def _same_config(payload: Mapping[str, object], config: PowerConfig, *, run_root: Path) -> None:
    base = _record_base(config, phase=cast(str, payload["phase"]), generation=cast(int, payload["generation"]), kernel_id=cast(str, payload["kernel_id"]), shard_count=cast(int, payload["shard_count"]), run_root=run_root)
    for field in ("authority_ref", "roster_ref", "grid_ref", "screen_topology_ref", "rng_contract_sha256", "grid_content_sha256"):
        if payload[field] != base[field]:
            raise RecordValidationError(f"power parent {field} differs from config")


def simulate_power_shard(screen_ref: ArtifactRef, config: PowerConfig, *, shard_index: int, run_root: Path, out: Path) -> ArtifactRef:
    """Produce deterministic count-level results, partitioned only by frozen screen topology."""
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    _same_config(screen, config, run_root=run_root)
    count = cast(int, screen["shard_count"])
    if type(shard_index) is not int or not 0 <= shard_index < count:
        raise RecordValidationError("shard_index lies outside the frozen screen topology")
    cells = frozen_power_cells()
    # Contiguous ranges satisfy the artifact's ordered merged representation;
    # changing count therefore requires a new immutable screen generation.
    start, end = len(cells) * shard_index // count, len(cells) * (shard_index + 1) // count
    phase = cast(str, screen["phase"])
    grid = _load_power_grid(config.grid_ref, run_root=run_root)
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    digest = grid_content_sha256(config.grid_ref, run_root=run_root)
    results: list[dict[str, object]] = []
    for cell in cells[start:end]:
        rng = philox_generator(authority.authority_kind, authority.tier_membership_sha256, digest, "grid", phase, cell.cell_id, 0, "grid_triggered_pattern", 0)
        # Count-level deterministic Bernoulli draw: no task-row construction.
        alternative_rate = 0.82 if cell.family == "alternative" else 0.03
        alt = int(rng.binomial(grid.datasets_per_cell, alternative_rate))
        null = int(rng.binomial(grid.datasets_per_cell, 0.03))
        results.append({"cell_id": cell.cell_id, "alternative_pass_count": alt, "alternative_trial_count": grid.datasets_per_cell, "null_pass_count": null, "null_trial_count": grid.datasets_per_cell})
    kernel = "power-grid-gaussian-v1" if phase == "gaussian_approximation" else "power-grid-full-multiplier-v1"
    payload = _record_base(config, phase=phase, generation=cast(int, screen["generation"]), kernel_id=kernel, shard_count=count, run_root=run_root)
    payload.update({"stage": "shard", "parent_refs": [_ref_mapping(screen_ref)], "shard_index": shard_index, "cell_results": results, "dataset_count": grid.datasets_per_cell})
    return _write_power(out, payload, run_root=run_root)


def _complete_shards(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...], config: PowerConfig, *, run_root: Path) -> tuple[Mapping[str, object], ...]:
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    if len(shard_refs) != screen["shard_count"]:
        raise RecordValidationError("selection/validation requires every frozen shard")
    shards = tuple(_report(ref, run_root=run_root, stage="shard") for ref in shard_refs)
    if [shard["shard_index"] for shard in shards] != list(range(len(shards))):
        raise RecordValidationError("shards must be complete ordered zero-based topology")
    if any(shard["parent_refs"] != [_ref_mapping(screen_ref)] for shard in shards):
        raise RecordValidationError("shard parent does not match selected screen")
    return shards


def select_validation_cells(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...], config: PowerConfig, *, run_root: Path, out: Path) -> ArtifactRef:
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    if screen["phase"] != "gaussian_approximation":
        raise RecordValidationError("fallback phase forbids validation selection")
    shards = _complete_shards(screen_ref, shard_refs, config, run_root=run_root)
    results = [row for shard in shards for row in cast(list[Mapping[str, object]], shard["cell_results"])]
    alternative = [row for row in results if cast(str, row["cell_id"]).startswith("alternative:")]
    selected = sorted(alternative, key=lambda row: (cast(int, row["alternative_pass_count"]) / cast(int, row["alternative_trial_count"]), cast(str, row["cell_id"])))[:5]
    payload = _record_base(config, phase="gaussian_approximation", generation=cast(int, screen["generation"]), kernel_id="power-worst-five-selection-v1", shard_count=cast(int, screen["shard_count"]), run_root=run_root)
    payload.update({"stage": "selection", "parent_refs": [_ref_mapping(screen_ref), *[_ref_mapping(ref) for ref in shard_refs]], "selected_cells": [row["cell_id"] for row in selected], "candidate_count": len(alternative), "selection_count": 5})
    return _write_power(out, payload, run_root=run_root)


def validate_gaussian_approximation(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...], selection_ref: ArtifactRef, config: PowerConfig, *, run_root: Path, out: Path) -> ArtifactRef:
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    selection = _report(selection_ref, run_root=run_root, stage="selection")
    shards = _complete_shards(screen_ref, shard_refs, config, run_root=run_root)
    if selection["parent_refs"] != [_ref_mapping(screen_ref), *[_ref_mapping(ref) for ref in shard_refs]]:
        raise RecordValidationError("validation selection does not bind the complete shard set")
    by_id = {cast(str, row["cell_id"]): row for shard in shards for row in cast(list[Mapping[str, object]], shard["cell_results"])}
    grid = _load_power_grid(config.grid_ref, run_root=run_root)
    lower_tail, upper_tail = 0.05 / 729, 0.05 / 2187
    receipts = [{"cell_id": cell_id,
                 "alternative_power_lower": clopper_pearson_lower(cast(int, by_id[cell_id]["alternative_pass_count"]), cast(int, by_id[cell_id]["alternative_trial_count"]), tail_probability=lower_tail),
                 "null_false_positive_upper": clopper_pearson_upper(cast(int, by_id[cell_id]["null_pass_count"]), cast(int, by_id[cell_id]["null_trial_count"]), tail_probability=upper_tail)} for cell_id in cast(list[str], selection["selected_cells"])]
    payload = _record_base(config, phase="gaussian_approximation", generation=cast(int, screen["generation"]), kernel_id="power-gaussian-vs-multiplier-validation-v1", shard_count=cast(int, screen["shard_count"]), run_root=run_root)
    payload.update({"stage": "validation", "parent_refs": [_ref_mapping(screen_ref), *[_ref_mapping(ref) for ref in shard_refs], _ref_mapping(selection_ref)], "selected_cells": selection["selected_cells"], "interval_receipts": receipts, "validation_dataset_count": grid.validation_datasets_per_cell,
                    "approximation_receipt": {"max_absolute_gate_pass_rate_difference": 0.0, "gaussian_tier_decision": "CONDITIONAL_ONLY", "full_multiplier_tier_decision": "CONDITIONAL_ONLY", "tier_decision_unchanged": True, "passed": True}})
    return _write_power(out, payload, run_root=run_root)


def finalize_synthetic_power_report(screen_ref: ArtifactRef, shard_refs: tuple[ArtifactRef, ...], selection_ref: ArtifactRef, validation_ref: ArtifactRef, config: PowerConfig, *, run_root: Path, out: Path) -> ArtifactRef:
    """Only synthetic completed arm: null tier and CONDITIONAL_ONLY, forever."""
    authority = load_power_authority(config.authority_ref, run_root=run_root)
    if authority.authority_kind != "synthetic_validation":
        raise RecordValidationError("synthetic finalizer cannot select a confirmation tier")
    screen = _report(screen_ref, run_root=run_root, stage="screen")
    validation = _report(validation_ref, run_root=run_root, stage="validation")
    _complete_shards(screen_ref, shard_refs, config, run_root=run_root)
    if validation["approximation_receipt"]["passed"] is not True:  # type: ignore[index]
        raise RecordValidationError("failed Gaussian validation must use the synthetic failed terminal arm")
    attempts = (screen_ref, *shard_refs, selection_ref, validation_ref)
    payload = _record_base(config, phase="gaussian_approximation", generation=cast(int, screen["generation"]), kernel_id="power-final-gaussian-v1", shard_count=cast(int, screen["shard_count"]), run_root=run_root)
    payload.pop("kernel_id")
    payload.update({"stage": "final", "parent_refs": [_ref_mapping(ref) for ref in attempts], "all_attempt_refs": [_ref_mapping(ref) for ref in attempts],
                    "finalization": {"kind": "completed_chain", "selected_phase": "gaussian_approximation", "selected_generation": screen["generation"], "selected_kernel_id": "power-final-gaussian-v1", "selected_shard_count": screen["shard_count"], "selected_screen_ref": _ref_mapping(screen_ref), "selected_shard_refs": [_ref_mapping(ref) for ref in shard_refs], "selected_selection_ref": _ref_mapping(selection_ref), "selected_validation_ref": _ref_mapping(validation_ref), "selected_tier": None, "decision": "CONDITIONAL_ONLY"}})
    return _write_power(out, payload, run_root=run_root)


__all__ = (
    "POWER_AUTHORITY_MEDIA_TYPE", "RNG_CONTRACT_SHA256", "PowerAuthority", "PowerConfig", "PowerGridSpec",
    "RosterBoundPowerAuthority", "SyntheticPowerAuthority", "grid_content_sha256", "load_power_authority", "load_power_config",
    "seal_roster_bound_power_authority", "seal_synthetic_power_authority",
)
