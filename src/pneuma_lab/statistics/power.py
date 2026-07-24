"""Fail-closed Protocol-v2 P0 joint-power simulation."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ANCHOR_SCHEMA_VERSION = "pneuma-p0-prior-anchor/1.0.0"
PAIRED_DISCORDANCE = (
    (0.15, 0.15),
    (0.20, 0.35),
    (0.30, 0.35),
    (0.40, 0.15),
)
LINEAGE_ICC = (0.05, 0.15, 0.30)
CROSS_COMPONENT_CORRELATION = (0.25, 0.50, 0.75)
NUISANCE_PROFILES = (
    (0.00, 0.00, 0.05, 0.05),
    (0.025, 0.05, 0.15, 0.15),
    (0.05, 0.10, 0.30, 0.30),
)
DELTA_VALUES = (0.05, 0.10, 0.15)
HIGHLIGHTED_SUPPORT = (24, 32, 48, 64, 80, 96)
FULL_SUPPORT = tuple(range(24, 97))
EXPECTED_SUPPORT = 48
POWER_THRESHOLD = 0.80
NO_GO_THRESHOLD = 0.40
ALPHA = 0.05
UTILITY_MARGIN = 0.05
NESTED_SEQUENCES_PER_LINEAGE = 2
COMPARATORS = ("base", "retrieval", "scalar")
UTILITY_U0 = (
    "attempt",
    "completion",
    "verified_success",
    "normalized_severity",
    "false_avoidance",
    "nonengagement_runtime",
    "resource_cap_binding",
)
UTILITY_U1 = (
    "verified_success",
    "composite_adverse",
    "resource_cap_binding",
)
UTILITY_UNION = (*UTILITY_U0, "composite_adverse")
H2_COMPONENTS = ("influence_off", "full_state_clamp")
MODEL_VERSION = "paired-gaussian-studentized-max-t/1.0.0"
MC_Z_99 = 2.5758293035489004
ONE_SIDED_Z_95 = 1.6448536269514715

_COMPONENT_INDEX: dict[str, int] = {}
for _comparator in COMPARATORS:
    _COMPONENT_INDEX[f"repeat_harm:{_comparator}"] = len(_COMPONENT_INDEX)
for _comparator in COMPARATORS:
    for _utility in UTILITY_UNION:
        _COMPONENT_INDEX[f"utility:{_utility}:{_comparator}"] = len(
            _COMPONENT_INDEX
        )
for _component in H2_COMPONENTS:
    _COMPONENT_INDEX[f"h2:{_component}"] = len(_COMPONENT_INDEX)
COMPONENT_COUNT = len(_COMPONENT_INDEX)


class PriorAnchorError(ValueError):
    """Raised when the governed P0 prior anchor cannot be trusted."""


@dataclass(frozen=True)
class WeightedValue:
    value: float
    weight: float


@dataclass(frozen=True)
class NuisanceProfile:
    attrition: float
    evaluator_error: float
    utility_event_rate: float
    utility_discordance: float
    weight: float


@dataclass(frozen=True)
class PriorAnchor:
    sha256: str
    base_harm_support: tuple[WeightedValue, ...]
    paired_discordance: tuple[WeightedValue, ...]
    lineage_icc: tuple[WeightedValue, ...]
    cross_component_correlation: tuple[WeightedValue, ...]
    nuisance_profiles: tuple[NuisanceProfile, ...]
    payload: dict[str, Any]


@dataclass(frozen=True)
class PriorCell:
    base_harm: float
    paired_discordance: float
    lineage_icc: float
    cross_component_correlation: float
    nuisance: NuisanceProfile
    weight: float


@dataclass(frozen=True)
class PriorGrid:
    cells: tuple[PriorCell, ...]
    pre_rejection_count: int
    rejected_count: int


@dataclass(frozen=True)
class SelectedTierDecision:
    p_h1t: float
    p_h2t: float
    p_selected: float
    passed: bool
    failure_reason: str | None


@dataclass(frozen=True)
class _PowerCounts:
    conjunction: dict[int, int]
    components: dict[str, dict[int, int]]
    draws: int


@dataclass(frozen=True)
class _CellScopeOutcome:
    core: _PowerCounts
    floor: _PowerCounts
    adaptive: bool


def module_sha256() -> str:
    """Return the digest that an immutable anchor must bind."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise PriorAnchorError("prior-anchor is not canonicalizable") from exc
    return (text + "\n").encode("utf-8")


def _reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PriorAnchorError(f"prior-anchor has duplicate member {key!r}")
        result[key] = value
    return result


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PriorAnchorError(f"{name} must be an object")
    return value


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PriorAnchorError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise PriorAnchorError(f"{name} must be a finite number")
    return number


def _weighted_values(
    value: object,
    name: str,
) -> tuple[WeightedValue, ...]:
    if not isinstance(value, list) or not value:
        raise PriorAnchorError(f"{name} must be a non-empty array")
    result: list[WeightedValue] = []
    for index, item in enumerate(value):
        row = _mapping(item, f"{name}[{index}]")
        result.append(
            WeightedValue(
                value=_finite_number(row.get("value"), f"{name}[{index}].value"),
                weight=_finite_number(
                    row.get("weight"), f"{name}[{index}].weight"
                ),
            )
        )
    if any(item.weight <= 0.0 for item in result):
        raise PriorAnchorError(f"{name} weights must be positive")
    if not math.isclose(
        math.fsum(item.weight for item in result),
        1.0,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise PriorAnchorError(f"{name} weights must sum to one")
    return tuple(result)


def _assert_support(
    observed: Iterable[WeightedValue],
    expected: Iterable[tuple[float, float]],
    name: str,
) -> None:
    observed_pairs = tuple((item.value, item.weight) for item in observed)
    expected_pairs = tuple(expected)
    if len(observed_pairs) != len(expected_pairs) or any(
        not (
            math.isclose(left_value, right_value, abs_tol=1e-12)
            and math.isclose(left_weight, right_weight, abs_tol=1e-12)
        )
        for (left_value, left_weight), (right_value, right_weight) in zip(
            observed_pairs, expected_pairs, strict=True
        )
    ):
        raise PriorAnchorError(f"{name} does not match the governed support")


def create_prior_anchor_payload(
    adapter_records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Create the immutable prior payload from already hash-verified reports."""
    records = [dict(record) for record in adapter_records]
    expected_adapters = (
        "open-swe-traces",
        "openhands-sampled",
        "openhands-verifier",
    )
    if tuple(record.get("adapter") for record in records) != expected_adapters:
        raise PriorAnchorError("adapter records must use the frozen identity order")
    enriched: list[dict[str, Any]] = []
    failure_rates: list[float] = []
    for record in records:
        resolved_true = record.get("resolved_true")
        resolved_false = record.get("resolved_false")
        if (
            isinstance(resolved_true, bool)
            or isinstance(resolved_false, bool)
            or not isinstance(resolved_true, int)
            or not isinstance(resolved_false, int)
            or resolved_true < 0
            or resolved_false < 0
            or resolved_true + resolved_false <= 0
        ):
            raise PriorAnchorError("adapter resolved-label denominator is invalid")
        failure_rate = resolved_false / (resolved_true + resolved_false)
        if not math.isfinite(failure_rate):
            raise PriorAnchorError("adapter failure rate is non-finite")
        row = dict(record)
        row["failure_rate"] = failure_rate
        enriched.append(row)
        failure_rates.append(failure_rate)
    failure_anchor = sorted(failure_rates)[1]
    bridge = ((0.25, 0.25), (0.50, 0.50), (0.75, 0.25))
    combined_support: dict[float, float] = {}
    for share, weight in bridge:
        value = failure_anchor * share
        combined_support[value] = combined_support.get(value, 0.0) + weight
    serializer_contract = (
        "json.dumps(allow_nan=False,ensure_ascii=False,"
        "separators=(',',':'),sort_keys=True)+'\\n'"
    )
    return {
        "schema_version": ANCHOR_SCHEMA_VERSION,
        "kind": "governed_prior_anchor",
        "code_sha256": module_sha256(),
        "canonical_serializer_sha256": hashlib.sha256(
            serializer_contract.encode("utf-8")
        ).hexdigest(),
        "adapter_reports": enriched,
        "failure_anchor": failure_anchor,
        "recurrence_bridge": [
            {"value": value, "weight": weight} for value, weight in bridge
        ],
        "base_harm_support": [
            {"value": value, "weight": combined_support[value]}
            for value in sorted(combined_support)
        ],
        "prior_grid": {
            "paired_discordance": [
                {"value": value, "weight": weight}
                for value, weight in PAIRED_DISCORDANCE
            ],
            "lineage_icc": [
                {"value": value, "weight": 1 / 3} for value in LINEAGE_ICC
            ],
            "cross_component_correlation": [
                {"value": value, "weight": 1 / 3}
                for value in CROSS_COMPONENT_CORRELATION
            ],
            "nuisance_profiles": [
                {
                    "attrition": profile[0],
                    "evaluator_error": profile[1],
                    "utility_event_rate": profile[2],
                    "utility_discordance": profile[3],
                    "weight": 1 / 3,
                }
                for profile in NUISANCE_PROFILES
            ],
        },
    }


def load_prior_anchor(
    path: Path,
    *,
    expected_sha256: str,
) -> PriorAnchor:
    """Load an anchor only after verifying its externally supplied digest."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PriorAnchorError(f"prior-anchor is unavailable: {path}") from exc
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != expected_sha256:
        raise PriorAnchorError(
            "prior-anchor digest mismatch: "
            f"expected {expected_sha256}, observed {actual_sha256}"
        )
    try:
        parsed = json.loads(raw, object_pairs_hook=_reject_duplicate_members)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PriorAnchorError("prior-anchor is not valid canonical JSON") from exc
    payload = _mapping(parsed, "prior-anchor")
    if raw != _canonical_json_bytes(payload):
        raise PriorAnchorError("prior-anchor bytes are not canonical JSON")
    if payload.get("schema_version") != ANCHOR_SCHEMA_VERSION:
        raise PriorAnchorError("prior-anchor schema version mismatch")
    if payload.get("kind") != "governed_prior_anchor":
        raise PriorAnchorError("prior-anchor kind mismatch")
    if payload.get("code_sha256") != module_sha256():
        raise PriorAnchorError("prior-anchor code digest mismatch")
    reports = payload.get("adapter_reports")
    if not isinstance(reports, list) or len(reports) != 3:
        raise PriorAnchorError("prior-anchor must bind exactly three adapter reports")
    expected_adapters = {
        "open-swe-traces",
        "openhands-sampled",
        "openhands-verifier",
    }
    adapters: set[str] = set()
    failure_rates: list[float] = []
    for index, item in enumerate(reports):
        report = _mapping(item, f"adapter_reports[{index}]")
        adapter = report.get("adapter")
        digest = report.get("report_sha256")
        failure_rate = _finite_number(
            report.get("failure_rate"),
            f"adapter_reports[{index}].failure_rate",
        )
        if not isinstance(adapter, str):
            raise PriorAnchorError("adapter report identity must be a string")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise PriorAnchorError("adapter report digest must be lowercase SHA-256")
        if not 0.0 <= failure_rate <= 1.0:
            raise PriorAnchorError("adapter failure rate must be in [0, 1]")
        adapters.add(adapter)
        failure_rates.append(failure_rate)
    if adapters != expected_adapters:
        raise PriorAnchorError("prior-anchor adapter identities mismatch")

    failure_anchor = _finite_number(
        payload.get("failure_anchor"), "failure_anchor"
    )
    if not math.isclose(
        failure_anchor,
        sorted(failure_rates)[1],
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise PriorAnchorError("prior failure anchor is not the adapter median")
    bridge = _weighted_values(payload.get("recurrence_bridge"), "recurrence_bridge")
    _assert_support(
        bridge,
        ((0.25, 0.25), (0.50, 0.50), (0.75, 0.25)),
        "recurrence_bridge",
    )
    base_harm = _weighted_values(
        payload.get("base_harm_support"), "base_harm_support"
    )
    if any(not 0.0 < item.value < 1.0 for item in base_harm):
        raise PriorAnchorError("base-harm values must be inside (0, 1)")
    expected_base: dict[float, float] = {}
    for item in bridge:
        induced = failure_anchor * item.value
        expected_base[induced] = expected_base.get(induced, 0.0) + item.weight
    expected_base_items = tuple(sorted(expected_base.items()))
    observed_base_items = tuple((item.value, item.weight) for item in base_harm)
    if len(observed_base_items) != len(expected_base_items) or any(
        not (
            math.isclose(observed_value, expected_value, abs_tol=1e-12)
            and math.isclose(observed_weight, expected_weight, abs_tol=1e-12)
        )
        for (observed_value, observed_weight), (
            expected_value,
            expected_weight,
        ) in zip(observed_base_items, expected_base_items, strict=True)
    ):
        raise PriorAnchorError(
            "base-harm support does not match the recurrence bridge"
        )
    prior = _mapping(payload.get("prior_grid"), "prior_grid")
    discordance = _weighted_values(
        prior.get("paired_discordance"), "paired_discordance"
    )
    _assert_support(discordance, PAIRED_DISCORDANCE, "paired_discordance")
    icc = _weighted_values(prior.get("lineage_icc"), "lineage_icc")
    _assert_support(
        icc,
        ((value, 1 / 3) for value in LINEAGE_ICC),
        "lineage_icc",
    )
    correlation = _weighted_values(
        prior.get("cross_component_correlation"),
        "cross_component_correlation",
    )
    _assert_support(
        correlation,
        ((value, 1 / 3) for value in CROSS_COMPONENT_CORRELATION),
        "cross_component_correlation",
    )
    raw_profiles = prior.get("nuisance_profiles")
    if not isinstance(raw_profiles, list) or len(raw_profiles) != 3:
        raise PriorAnchorError("nuisance_profiles must contain three entries")
    profiles: list[NuisanceProfile] = []
    for index, item in enumerate(raw_profiles):
        profile = _mapping(item, f"nuisance_profiles[{index}]")
        profiles.append(
            NuisanceProfile(
                attrition=_finite_number(
                    profile.get("attrition"),
                    f"nuisance_profiles[{index}].attrition",
                ),
                evaluator_error=_finite_number(
                    profile.get("evaluator_error"),
                    f"nuisance_profiles[{index}].evaluator_error",
                ),
                utility_event_rate=_finite_number(
                    profile.get("utility_event_rate"),
                    f"nuisance_profiles[{index}].utility_event_rate",
                ),
                utility_discordance=_finite_number(
                    profile.get("utility_discordance"),
                    f"nuisance_profiles[{index}].utility_discordance",
                ),
                weight=_finite_number(
                    profile.get("weight"),
                    f"nuisance_profiles[{index}].weight",
                ),
            )
        )
    if any(
        not all(
            math.isclose(observed, expected, abs_tol=1e-12)
            for observed, expected in zip(
                (
                    profile.attrition,
                    profile.evaluator_error,
                    profile.utility_event_rate,
                    profile.utility_discordance,
                ),
                expected_profile,
                strict=True,
            )
        )
        or not math.isclose(profile.weight, 1 / 3, abs_tol=1e-12)
        for profile, expected_profile in zip(
            profiles, NUISANCE_PROFILES, strict=True
        )
    ):
        raise PriorAnchorError("nuisance_profiles do not match governed values")
    return PriorAnchor(
        sha256=actual_sha256,
        base_harm_support=base_harm,
        paired_discordance=discordance,
        lineage_icc=icc,
        cross_component_correlation=correlation,
        nuisance_profiles=tuple(profiles),
        payload=payload,
    )


def _paired_binary_compatible(
    base_harm: float,
    delta_power: float,
    discordance: float,
) -> bool:
    comparator_only = (discordance + delta_power) / 2.0
    pneuma_only = (discordance - delta_power) / 2.0
    both = base_harm - comparator_only
    neither = 1.0 - base_harm - pneuma_only
    return min(comparator_only, pneuma_only, both, neither) >= -1e-12


def _utility_pair_compatible(event_rate: float, discordance: float) -> bool:
    off_diagonal = discordance / 2.0
    return event_rate - off_diagonal >= -1e-12 and (
        1.0 - event_rate - off_diagonal >= -1e-12
    )


def build_prior_grid(
    anchor: PriorAnchor,
    *,
    delta_power: float,
) -> PriorGrid:
    """Build and compatibility-filter the frozen 324-cell product prior."""
    if delta_power not in {0.05, 0.10, 0.15}:
        raise PriorAnchorError("delta_power is outside the frozen sensitivity set")
    cells: list[PriorCell] = []
    rejected = 0
    products = itertools.product(
        anchor.base_harm_support,
        anchor.paired_discordance,
        anchor.lineage_icc,
        anchor.cross_component_correlation,
        anchor.nuisance_profiles,
    )
    for base, discordance, icc, correlation, nuisance in products:
        compatible = _paired_binary_compatible(
            base.value, delta_power, discordance.value
        ) and _utility_pair_compatible(
            nuisance.utility_event_rate,
            nuisance.utility_discordance,
        )
        component_count = 26
        positive_semidefinite = (
            1.0 - correlation.value > 0.0
            and 1.0 + (component_count - 1) * correlation.value > 0.0
        )
        if not compatible or not positive_semidefinite:
            rejected += 1
            continue
        cells.append(
            PriorCell(
                base_harm=base.value,
                paired_discordance=discordance.value,
                lineage_icc=icc.value,
                cross_component_correlation=correlation.value,
                nuisance=nuisance,
                weight=(
                    base.weight
                    * discordance.weight
                    * icc.weight
                    * correlation.weight
                    * nuisance.weight
                ),
            )
        )
    pre_rejection_count = (
        len(anchor.base_harm_support)
        * len(anchor.paired_discordance)
        * len(anchor.lineage_icc)
        * len(anchor.cross_component_correlation)
        * len(anchor.nuisance_profiles)
    )
    if pre_rejection_count != 324:
        raise PriorAnchorError(
            f"governed prior must have 324 cells, observed {pre_rejection_count}"
        )
    total_weight = math.fsum(cell.weight for cell in cells)
    if not cells or total_weight <= 0.0:
        raise PriorAnchorError("no governed prior cells survive compatibility checks")
    normalized = tuple(
        PriorCell(
            base_harm=cell.base_harm,
            paired_discordance=cell.paired_discordance,
            lineage_icc=cell.lineage_icc,
            cross_component_correlation=cell.cross_component_correlation,
            nuisance=cell.nuisance,
            weight=cell.weight / total_weight,
        )
        for cell in cells
    )
    return PriorGrid(
        cells=normalized,
        pre_rejection_count=pre_rejection_count,
        rejected_count=rejected,
    )


def evaluate_selected_tier(
    *,
    h1_component_pvalues: dict[str, float],
    h2_component_pvalues: dict[str, float],
    behavior_estimates: dict[str, float],
    behavior_lower_bounds: dict[str, float],
    hard_gates_pass: bool = True,
    alpha: float = 0.05,
    observed_behavior_gate: float = 0.05,
) -> SelectedTierDecision:
    """Apply the frozen H1-T ∩ H2-T IUT and behavioral co-gates."""
    if not h1_component_pvalues or not h2_component_pvalues:
        raise ValueError("both H1-T and H2-T require component p-values")
    if behavior_estimates.keys() != behavior_lower_bounds.keys():
        raise ValueError("behavior estimates and lower bounds must share keys")
    all_pvalues = (*h1_component_pvalues.values(), *h2_component_pvalues.values())
    if any(
        isinstance(value, bool)
        or not math.isfinite(value)
        or not 0.0 <= value <= 1.0
        for value in all_pvalues
    ):
        raise ValueError("component p-values must be finite and in [0, 1]")
    p_h1t = max(h1_component_pvalues.values())
    p_h2t = max(h2_component_pvalues.values())
    p_selected = max(p_h1t, p_h2t)
    failure_reason: str | None = None
    if not hard_gates_pass:
        failure_reason = "hard_gate"
    elif p_selected > alpha:
        failure_reason = "intersection_union_test"
    elif any(value < observed_behavior_gate for value in behavior_estimates.values()):
        failure_reason = "observed_behavior_gate"
    elif any(value <= 0.0 for value in behavior_lower_bounds.values()):
        failure_reason = "simultaneous_lower_bound"
    return SelectedTierDecision(
        p_h1t=p_h1t,
        p_h2t=p_h2t,
        p_selected=p_selected,
        passed=failure_reason is None,
        failure_reason=failure_reason,
    )


def _observed_discordance(discordance: float, error_rate: float) -> float:
    retained_difference = (1.0 - 2.0 * error_rate) ** 2
    introduced_difference = 2.0 * error_rate * (1.0 - error_rate)
    return discordance * retained_difference + introduced_difference


def _test_interval(
    z_values: np.ndarray,
    *,
    theta: float,
    scale: float,
    critical: float,
    point_gate: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    lower = np.zeros(z_values.shape[0], dtype=np.float64)
    upper = np.full(z_values.shape[0], np.inf, dtype=np.float64)
    below_critical = z_values < critical
    lower[below_critical] = (
        scale * (critical - z_values[below_critical]) / theta
    ) ** 2
    if point_gate is None:
        return lower, upper
    gap = theta - point_gate
    if gap > 1e-15:
        negative = z_values < 0.0
        point_lower = np.zeros_like(lower)
        point_lower[negative] = (
            scale * (-z_values[negative]) / gap
        ) ** 2
        np.maximum(lower, point_lower, out=lower)
    elif gap < -1e-15:
        possible = z_values > 0.0
        upper[~possible] = -1.0
        upper[possible] = (
            scale * z_values[possible] / (-gap)
        ) ** 2
    else:
        upper[z_values < 0.0] = -1.0
    return lower, upper


def _counts_for_intervals(
    lower: np.ndarray,
    upper: np.ndarray,
    support_counts: tuple[int, ...],
) -> dict[int, int]:
    minimum = min(support_counts)
    maximum = max(support_counts)
    starts = np.ceil(lower - 1e-12)
    ends = np.floor(upper + 1e-12)
    valid = np.isfinite(starts) & (ends >= minimum) & (starts <= maximum)
    start_values = np.clip(starts[valid], minimum, maximum + 1).astype(np.int64)
    end_values = np.clip(ends[valid], minimum - 1, maximum).astype(np.int64)
    valid_ranges = start_values <= end_values
    width = maximum - minimum + 2
    changes = np.zeros(width, dtype=np.int64)
    if np.any(valid_ranges):
        start_offsets = start_values[valid_ranges] - minimum
        end_offsets = end_values[valid_ranges] - minimum + 1
        changes += np.bincount(start_offsets, minlength=width)
        changes -= np.bincount(end_offsets, minlength=width)
    cumulative = np.cumsum(changes)[: maximum - minimum + 1]
    return {support: int(cumulative[support - minimum]) for support in support_counts}


def _component_names(tier: str, scope: str) -> tuple[str, ...]:
    comparators = COMPARATORS if tier == "core" else COMPARATORS[:1]
    utilities = UTILITY_U0 if scope == "U0" else UTILITY_U1
    behavior = tuple(f"repeat_harm:{name}" for name in comparators)
    utility = tuple(
        f"utility:{name}:{comparator}"
        for comparator in comparators
        for name in utilities
    )
    causal = tuple(f"h2:{name}" for name in H2_COMPONENTS)
    return (*behavior, *utility, *causal)


def _max_t_critical(
    *,
    correlation: float,
    component_count: int,
    seed: int,
) -> float:
    if component_count == 1:
        return ONE_SIDED_Z_95
    generator = np.random.Generator(np.random.PCG64(seed))
    draws = 100_000
    shared = generator.standard_normal((draws, 1))
    independent = generator.standard_normal((draws, component_count))
    values = (
        math.sqrt(correlation) * shared
        + math.sqrt(1.0 - correlation) * independent
    )
    maxima = np.max(values, axis=1)
    return float(np.quantile(maxima, 0.95, method="higher"))


def _scenario_counts(
    z_values: np.ndarray,
    *,
    cell: PriorCell,
    delta_power: float,
    tier: str,
    scope: str,
    support_counts: tuple[int, ...],
    max_t_critical: float,
) -> _PowerCounts:
    names = _component_names(tier, scope)
    effective_multiplier = (
        NESTED_SEQUENCES_PER_LINEAGE
        * (1.0 - cell.nuisance.attrition)
        / (1.0 + cell.lineage_icc)
    )
    observed_delta = (
        1.0 - 2.0 * cell.nuisance.evaluator_error
    ) * delta_power
    behavior_discordance = _observed_discordance(
        cell.paired_discordance,
        cell.nuisance.evaluator_error,
    )
    behavior_variance = behavior_discordance - observed_delta**2
    if behavior_variance <= 0.0:
        raise PriorAnchorError("behavior variance is non-positive after error model")
    behavior_scale = math.sqrt(behavior_variance / effective_multiplier)
    utility_discordance = _observed_discordance(
        cell.nuisance.utility_discordance,
        cell.nuisance.evaluator_error,
    )
    utility_scale = math.sqrt(utility_discordance / effective_multiplier)

    component_intervals: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for name in names:
        values = z_values[:, _COMPONENT_INDEX[name]]
        if name.startswith("repeat_harm:"):
            component_intervals[name] = _test_interval(
                values,
                theta=observed_delta,
                scale=behavior_scale,
                critical=max(max_t_critical, ONE_SIDED_Z_95),
                point_gate=0.05,
            )
        elif name.startswith("utility:"):
            component_intervals[name] = _test_interval(
                values,
                theta=UTILITY_MARGIN,
                scale=utility_scale,
                critical=ONE_SIDED_Z_95,
            )
        else:
            component_intervals[name] = _test_interval(
                values,
                theta=observed_delta,
                scale=behavior_scale,
                critical=ONE_SIDED_Z_95,
            )

    combined_lower = np.maximum.reduce(
        [interval[0] for interval in component_intervals.values()]
    )
    combined_upper = np.minimum.reduce(
        [interval[1] for interval in component_intervals.values()]
    )
    return _PowerCounts(
        conjunction=_counts_for_intervals(
            combined_lower,
            combined_upper,
            support_counts,
        ),
        components={
            name: _counts_for_intervals(lower, upper, support_counts)
            for name, (lower, upper) in component_intervals.items()
        },
        draws=z_values.shape[0],
    )


def monte_carlo_interval(successes: int, draws: int) -> tuple[float, float]:
    """Return the two-sided 99% Wilson interval for a decision probability."""
    if draws <= 0 or not 0 <= successes <= draws:
        raise ValueError("Monte Carlo counts are invalid")
    estimate = successes / draws
    denominator = 1.0 + MC_Z_99**2 / draws
    center = (estimate + MC_Z_99**2 / (2.0 * draws)) / denominator
    half_width = (
        MC_Z_99
        * math.sqrt(
            estimate * (1.0 - estimate) / draws
            + MC_Z_99**2 / (4.0 * draws**2)
        )
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def select_utility_scope(
    u0_no_go_probability: float,
    u1_no_go_probability: float,
) -> tuple[str | None, str]:
    """Apply the frozen U0→U1→P0-no-go ladder at Δ=.10 and G=48."""
    for value in (u0_no_go_probability, u1_no_go_probability):
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("no-go probabilities must be finite and in [0, 1]")
    if u0_no_go_probability <= NO_GO_THRESHOLD:
        return "U0", "proceed"
    if u1_no_go_probability <= NO_GO_THRESHOLD:
        return "U1", "proceed"
    return None, "P0 no-go"


def _straddles_threshold(counts: _PowerCounts) -> bool:
    return any(
        low <= POWER_THRESHOLD <= high
        for successes in counts.conjunction.values()
        for low, high in [monte_carlo_interval(successes, counts.draws)]
    )


def _cell_key(cell: PriorCell) -> tuple[float, ...]:
    return (
        cell.paired_discordance,
        cell.lineage_icc,
        cell.cross_component_correlation,
        cell.nuisance.attrition,
        cell.nuisance.evaluator_error,
        cell.nuisance.utility_event_rate,
        cell.nuisance.utility_discordance,
    )


def _group_cells(grid: PriorGrid) -> tuple[tuple[PriorCell, float, int], ...]:
    grouped: dict[tuple[float, ...], tuple[PriorCell, float, int]] = {}
    for cell in grid.cells:
        key = _cell_key(cell)
        if key in grouped:
            representative, weight, count = grouped[key]
            grouped[key] = representative, weight + cell.weight, count + 1
        else:
            grouped[key] = cell, cell.weight, 1
    return tuple(grouped[key] for key in sorted(grouped))


def _new_accumulator(
    delta_values: tuple[float, ...],
    support_counts: tuple[int, ...],
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    accumulator: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for delta in delta_values:
        delta_key = f"{delta:.2f}"
        accumulator[delta_key] = {}
        for support in support_counts:
            accumulator[delta_key][str(support)] = {}
            for scope in ("U0", "U1"):
                accumulator[delta_key][str(support)][scope] = {
                    "category": {"core": 0.0, "floor": 0.0, "no-go": 0.0},
                    "category_lower": {
                        "core": 0.0,
                        "floor": 0.0,
                        "no-go": 0.0,
                    },
                    "category_upper": {
                        "core": 0.0,
                        "floor": 0.0,
                        "no-go": 0.0,
                    },
                    "tiers": {
                        tier: {
                            "conjunction": 0.0,
                            "conjunction_lower": 0.0,
                            "conjunction_upper": 0.0,
                            "components": {},
                        }
                        for tier in ("core", "floor")
                    },
                    "adaptive_cells": 0,
                    "grid_cell_count": 0,
                    "parameter_cell_count": 0,
                    "minimum_draws": math.inf,
                    "maximum_draws": 0,
                }
    return accumulator


def _accumulate_cell(
    target: dict[str, Any],
    *,
    outcome: _CellScopeOutcome,
    support: int,
    weight: float,
    grid_cell_count: int,
) -> None:
    core_count = outcome.core.conjunction[support]
    floor_count = outcome.floor.conjunction[support]
    core_power = core_count / outcome.core.draws
    floor_power = floor_count / outcome.floor.draws
    core_interval = monte_carlo_interval(core_count, outcome.core.draws)
    floor_interval = monte_carlo_interval(floor_count, outcome.floor.draws)
    if core_power >= POWER_THRESHOLD:
        category = "core"
    elif floor_power >= POWER_THRESHOLD:
        category = "floor"
    else:
        category = "no-go"
    target["category"][category] += weight
    if core_interval[0] >= POWER_THRESHOLD:
        target["category_lower"]["core"] += weight
    if core_interval[1] >= POWER_THRESHOLD:
        target["category_upper"]["core"] += weight
    if (
        core_interval[1] < POWER_THRESHOLD
        and floor_interval[0] >= POWER_THRESHOLD
    ):
        target["category_lower"]["floor"] += weight
    if (
        core_interval[0] < POWER_THRESHOLD
        and floor_interval[1] >= POWER_THRESHOLD
    ):
        target["category_upper"]["floor"] += weight
    if floor_interval[1] < POWER_THRESHOLD:
        target["category_lower"]["no-go"] += weight
    if floor_interval[0] < POWER_THRESHOLD:
        target["category_upper"]["no-go"] += weight
    for tier, counts, interval in (
        ("core", outcome.core, core_interval),
        ("floor", outcome.floor, floor_interval),
    ):
        tier_target = target["tiers"][tier]
        tier_target["conjunction"] += weight * (
            counts.conjunction[support] / counts.draws
        )
        tier_target["conjunction_lower"] += weight * interval[0]
        tier_target["conjunction_upper"] += weight * interval[1]
        for name, component_counts in counts.components.items():
            tier_target["components"][name] = tier_target["components"].get(
                name, 0.0
            ) + weight * (component_counts[support] / counts.draws)
    target["adaptive_cells"] += grid_cell_count if outcome.adaptive else 0
    target["grid_cell_count"] += grid_cell_count
    target["parameter_cell_count"] += 1
    target["minimum_draws"] = min(target["minimum_draws"], outcome.core.draws)
    target["maximum_draws"] = max(target["maximum_draws"], outcome.core.draws)


def _finalize_accumulator(target: dict[str, Any]) -> dict[str, Any]:
    category_total = math.fsum(target["category"].values())
    if category_total <= 0.0:
        raise RuntimeError("prior category mass is non-positive")
    core_probability = target["category"]["core"] / category_total
    floor_probability = target["category"]["floor"] / category_total
    no_go_probability = 1.0 - core_probability - floor_probability
    category = {
        "core": core_probability,
        "floor": floor_probability,
        "no-go": no_go_probability,
    }
    tiers: dict[str, Any] = {}
    for tier, values in target["tiers"].items():
        components = dict(sorted(values["components"].items()))
        responsible = min(components, key=components.__getitem__)
        tiers[tier] = {
            "conjunction_power": values["conjunction"],
            "monte_carlo_interval_99": [
                values["conjunction_lower"],
                values["conjunction_upper"],
            ],
            "component_marginal_power": components,
            "component_most_responsible_for_failure": responsible,
            "failure_rate": 1.0 - components[responsible],
        }
    return {
        "tier_probabilities": category,
        "monte_carlo_uncertainty": {
            name: [
                max(0.0, min(1.0, target["category_lower"][name])),
                max(0.0, min(1.0, target["category_upper"][name])),
            ]
            for name in ("core", "floor", "no-go")
        },
        "tiers": tiers,
        "cell_draws": {
            "minimum": int(target["minimum_draws"]),
            "maximum": int(target["maximum_draws"]),
            "adaptive_cells": target["adaptive_cells"],
            "surviving_grid_cells": target["grid_cell_count"],
            "simulated_parameter_cells": target["parameter_cell_count"],
        },
    }


def simulate_power(
    *,
    anchor: PriorAnchor,
    seed: int,
    initial_draws: int,
    adaptive_draws: int,
    support_counts: tuple[int, ...] = FULL_SUPPORT,
    delta_values: tuple[float, ...] = DELTA_VALUES,
    adapt: bool = True,
) -> dict[str, Any]:
    """Run the governed joint decision pipeline with common random numbers."""
    if initial_draws <= 0 or adaptive_draws < initial_draws:
        raise ValueError("draw counts must be positive and nondecreasing")
    if not support_counts or tuple(sorted(set(support_counts))) != support_counts:
        raise ValueError("support_counts must be sorted and unique")
    if min(support_counts) < 24 or max(support_counts) > 96:
        raise ValueError("support_counts must stay inside [24, 96]")
    if any(delta not in DELTA_VALUES for delta in delta_values):
        raise ValueError("delta_values must use the frozen sensitivity set")
    generator = np.random.Generator(np.random.PCG64(seed))
    shared = generator.standard_normal((adaptive_draws, 1))
    independent = generator.standard_normal((adaptive_draws, COMPONENT_COUNT))
    z_by_correlation = {
        correlation: (
            math.sqrt(correlation) * shared
            + math.sqrt(1.0 - correlation) * independent
        )
        for correlation in CROSS_COMPONENT_CORRELATION
    }
    max_t = {
        (correlation, count): _max_t_critical(
            correlation=correlation,
            component_count=count,
            seed=seed ^ int(correlation * 10_000) ^ count,
        )
        for correlation in CROSS_COMPONENT_CORRELATION
        for count in (1, 3)
    }
    accumulator = _new_accumulator(delta_values, support_counts)
    grid_metadata: dict[str, Any] = {}
    for delta in delta_values:
        grid = build_prior_grid(anchor, delta_power=delta)
        grouped = _group_cells(grid)
        delta_key = f"{delta:.2f}"
        grid_metadata[delta_key] = {
            "pre_rejection_cells": grid.pre_rejection_count,
            "surviving_cells": len(grid.cells),
            "rejected_cells": grid.rejected_count,
            "surviving_parameter_cells": len(grouped),
        }
        for cell, weight, grid_cell_count in grouped:
            z_all = z_by_correlation[cell.cross_component_correlation]
            initial_outcomes: dict[str, _CellScopeOutcome] = {}
            should_adapt = False
            for scope in ("U0", "U1"):
                core = _scenario_counts(
                    z_all[:initial_draws],
                    cell=cell,
                    delta_power=delta,
                    tier="core",
                    scope=scope,
                    support_counts=support_counts,
                    max_t_critical=max_t[
                        (cell.cross_component_correlation, len(COMPARATORS))
                    ],
                )
                floor = _scenario_counts(
                    z_all[:initial_draws],
                    cell=cell,
                    delta_power=delta,
                    tier="floor",
                    scope=scope,
                    support_counts=support_counts,
                    max_t_critical=max_t[
                        (cell.cross_component_correlation, 1)
                    ],
                )
                initial_outcomes[scope] = _CellScopeOutcome(
                    core=core,
                    floor=floor,
                    adaptive=False,
                )
                should_adapt = should_adapt or _straddles_threshold(
                    core
                ) or _straddles_threshold(floor)
            if adapt and should_adapt and adaptive_draws > initial_draws:
                outcomes = {
                    scope: _CellScopeOutcome(
                        core=_scenario_counts(
                            z_all,
                            cell=cell,
                            delta_power=delta,
                            tier="core",
                            scope=scope,
                            support_counts=support_counts,
                            max_t_critical=max_t[
                                (
                                    cell.cross_component_correlation,
                                    len(COMPARATORS),
                                )
                            ],
                        ),
                        floor=_scenario_counts(
                            z_all,
                            cell=cell,
                            delta_power=delta,
                            tier="floor",
                            scope=scope,
                            support_counts=support_counts,
                            max_t_critical=max_t[
                                (cell.cross_component_correlation, 1)
                            ],
                        ),
                        adaptive=True,
                    )
                    for scope in ("U0", "U1")
                }
            else:
                outcomes = initial_outcomes
            for support in support_counts:
                for scope, outcome in outcomes.items():
                    _accumulate_cell(
                        accumulator[delta_key][str(support)][scope],
                        outcome=outcome,
                        support=support,
                        weight=weight,
                        grid_cell_count=grid_cell_count,
                    )
    results = {
        delta: {
            support: {
                scope: _finalize_accumulator(scope_values)
                for scope, scope_values in support_values.items()
            }
            for support, support_values in delta_values_map.items()
        }
        for delta, delta_values_map in accumulator.items()
    }
    selected: dict[str, Any]
    if "0.10" in results and str(EXPECTED_SUPPORT) in results["0.10"]:
        selected_result = results["0.10"][str(EXPECTED_SUPPORT)]
        u0_no_go = selected_result["U0"]["tier_probabilities"]["no-go"]
        u1_no_go = selected_result["U1"]["tier_probabilities"]["no-go"]
        scope, outcome = select_utility_scope(u0_no_go, u1_no_go)
        selected = {
            "delta_power": 0.10,
            "support": EXPECTED_SUPPORT,
            "scope": scope,
            "outcome": outcome,
            "U0_no_go_probability": u0_no_go,
            "U1_no_go_probability": u1_no_go,
        }
    else:
        selected = {
            "delta_power": 0.10,
            "support": EXPECTED_SUPPORT,
            "scope": None,
            "outcome": "not evaluated",
        }
    config = {
        "model_version": MODEL_VERSION,
        "seed": seed,
        "initial_draws": initial_draws,
        "adaptive_draws": adaptive_draws,
        "adaptive_enabled": adapt,
        "support_counts": list(support_counts),
        "delta_values": list(delta_values),
        "selected_support": EXPECTED_SUPPORT,
        "highlighted_support": list(HIGHLIGHTED_SUPPORT),
        "common_random_numbers": True,
        "utility_scopes": {"U0": list(UTILITY_U0), "U1": list(UTILITY_U1)},
        "core_comparators": list(COMPARATORS),
        "floor_comparators": [COMPARATORS[0]],
        "h2_components": list(H2_COMPONENTS),
        "alpha": ALPHA,
        "power_threshold": POWER_THRESHOLD,
        "no_go_threshold": NO_GO_THRESHOLD,
        "numpy_version": np.__version__,
        "fisher_role": "separate sharp-global-null output; not selected-tier gate",
        "population_inference": "centered studentized Gaussian bootstrap-t planning law",
        "simultaneous_bounds": "one-sided studentized max-T over H1-T behavior",
    }
    config_sha256 = hashlib.sha256(_canonical_json_bytes(config)).hexdigest()
    return {
        "schema_version": "pneuma-p0-power-report/1.0.0",
        "anchor_sha256": anchor.sha256,
        "code_sha256": module_sha256(),
        "config_sha256": config_sha256,
        "config": config,
        "grid": grid_metadata,
        "results": results,
        "selection": selected,
    }


def run_official_power(
    anchor_path: Path,
    *,
    expected_anchor_sha256: str,
    seed: int = 20260724,
) -> dict[str, Any]:
    """Run the official fixed P0 configuration."""
    anchor = load_prior_anchor(
        anchor_path,
        expected_sha256=expected_anchor_sha256,
    )
    return simulate_power(
        anchor=anchor,
        seed=seed,
        initial_draws=10_000,
        adaptive_draws=100_000,
        support_counts=FULL_SUPPORT,
        delta_values=DELTA_VALUES,
        adapt=True,
    )
