"""Offline four-variant paired falsification evaluation harness.

This module produces the four pre-registered ``VariantResult`` records the
2m-and-later falsification gate consumes (``falsification.REQUIRED_VARIANTS``):
``untouched_qwen`` (the pinned frozen base, no junction), ``continued_deltanet``
and ``feed_forward_adapter`` (the two pre-registered baseline adapters), and
``pneuma_recurrent`` (the bounded recurrent junction, optionally restored from
a trained safe-boundary checkpoint). Every variant is evaluated on the exact
same ordered task set so ``falsification._validate_variants`` accepts the
pairing, and every emitted file carries the honesty markers
``"task_semantics": "held_out_risk_prediction_correctness"`` and
``"no_consciousness_claim": true``.

Task semantics (honest proxy, never SWE-agent task resolution)
--------------------------------------------------------------

The evaluation task set is the repo-disjoint held-out slice of one prepared
immutable shard: every record whose ``split.split_id`` equals ``"validation"``,
ordered by ``record_id``. One record is one task; ``task_id`` is the record's
``record_id`` and ``repo`` is the record's ``identity.repo``.

Resolved-prediction rule (the exact, deterministic definition of a variant's
``resolved`` outcome for one task):

1. Let ``P`` be the token ids of the record's ``rendered.prompt_text`` encoded
   with ``add_special_tokens=True`` (the ``FoundationCollator`` convention).
2. The record's ``rendered.target_text`` must parse as a JSON object with a
   boolean ``"resolved"`` member. For each candidate label ``L`` in
   ``{true, false}`` build the canonical target rendering: the parsed object
   with ``resolved`` replaced by ``L``, re-serialized with sorted keys and
   compact separators exactly as ``records.render_foundation_record`` does.
   The rendering for the record's own label must reproduce ``target_text``
   byte-for-byte, or the record is rejected.
3. Let ``T_L`` be the label rendering's token ids encoded with
   ``add_special_tokens=False`` plus the tokenizer's EOS id, truncated exactly
   as ``FoundationCollator`` truncates (target first, then the prompt tail).
4. Score each label as the mean per-token log-probability (float32
   log-softmax over the model logits) of ``T_L`` under teacher forcing after
   ``P``, with the variant's recurrent state restored to its post-load
   snapshot before every forward. The predicted label is the argmax; an exact
   tie predicts ``false``.
5. The variant's ``resolved`` outcome for the task is
   ``predicted label == observations.labels.resolved``.

Resource honesty: peak VRAM/RAM are measured with the same telemetry probes
the training runner samples (``telemetry._cuda_memory_bytes`` /
``telemetry._process_memory_bytes``); p95 latency overhead is measured with
the dry-run machinery (enabled-vs-disabled adapter timing, nearest-rank p95)
and FLOPs overhead uses the dry-run analytic estimates. ``untouched_qwen``
overheads are 0.0 by definition. ``general_regression_points`` is recorded as
0.0 because no defensible mapping from held-out language-loss deltas to
benchmark points exists in this codebase; the index manifest marks the field
``not_measured_recorded_as_zero``. ``functioning_exploits`` is 0 because this
harness is an advisory-only offline evaluation: nothing actuates, no
authority is granted, and no verifier is contacted.

The harness is fully offline (the runner's ``HF_HUB_OFFLINE`` discipline is
assumed for real snapshots) and runs on CPU; a GPU is optional at runtime.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

try:
    import torch
    from torch import Tensor, nn
except ImportError as exc:  # pragma: no cover - optional dependency boundary
    raise ImportError(
        "pneuma_lab.foundation.variants requires the foundation torch extra"
    ) from exc

from pneuma_lab.foundation.artifacts import write_atomic_json
from pneuma_lab.foundation.checkpoints import CHECKPOINT_FORMAT
from pneuma_lab.foundation.dry_run import (
    estimate_base_forward_flops,
    estimate_junction_flops,
    percentile_95,
)
from pneuma_lab.foundation.evaluation import CLAIM_BOUNDARY, load_variant_results
from pneuma_lab.foundation.falsification import (
    REQUIRED_VARIANTS,
    VariantResult,
    _validate_variants,
)
from pneuma_lab.foundation.integration import (
    _decoder_layers,
    _floating_placement,
    install_junctions,
)
from pneuma_lab.foundation.specs import ArchitecturePlan, CORE_LIMITS
from pneuma_lab.foundation.training import DEFAULT_TRAINING_CONFIG


TASK_SEMANTICS = "held_out_risk_prediction_correctness"
VARIANT_EVAL_INDEX_NAME = "index.json"
VARIANT_EVAL_INDEX_KIND = "pneuma_foundation_variant_eval_index"
VARIANT_EVAL_INDEX_SCHEMA_VERSION = "0.1.0"
EVALUATION_SPLIT_ID = "validation"
DEFAULT_BASELINE_SEED = 20260713
_WARMUP_FORWARDS = 5
_TIMED_FORWARDS = 20


class VariantEvaluationError(ValueError):
    """Raised when the four-variant evaluation cannot proceed honestly."""


# ---------------------------------------------------------------------------
# Pre-registered baseline adapters
# ---------------------------------------------------------------------------


class _PooledResidualAdapter(nn.Module):
    """Shared placement discipline for the two pre-registered baselines.

    Both baselines mirror ``JunctionAdapter`` exactly outside their transform:
    mean-pool the layer's hidden states, project down to the 256-wide latent,
    transform, project back up, and contribute a 0.01-scaled residual in the
    base's dtype. Only ``_transform`` differs per baseline, so any measured
    difference against ``pneuma_recurrent`` isolates the recurrent core.
    """

    def __init__(self, *, hidden_size: int, latent_width: int) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.latent_width = latent_width
        self.down_projection = nn.Linear(hidden_size, latent_width)
        self.up_projection = nn.Linear(latent_width, hidden_size)
        self.residual_scale = nn.Parameter(torch.tensor(0.01))
        self.enabled = True

    def _transform(self, latent: Tensor) -> Tensor:
        raise NotImplementedError

    def _map_hidden(self, hidden: Tensor) -> Tensor:
        if not self.enabled:
            return hidden
        core_dtype = self.down_projection.weight.dtype
        pooled = hidden.mean(dim=1).to(core_dtype)
        latent = self._transform(self.down_projection(pooled))
        residual = self.up_projection(latent).unsqueeze(1)
        contribution = (self.residual_scale * residual).to(hidden.dtype)
        return hidden + contribution

    def map_layer_output(self, output):
        """Replace only hidden states and preserve every native cache object."""

        if not self.enabled:
            return output
        if isinstance(output, Tensor):
            return self._map_hidden(output)
        if isinstance(output, tuple) and output and isinstance(output[0], Tensor):
            return (self._map_hidden(output[0]), *output[1:])
        if isinstance(output, list) and output and isinstance(output[0], Tensor):
            return [self._map_hidden(output[0]), *output[1:]]
        raise TypeError("decoder layer output must be a tensor, tuple, or list")

    def forward(self, hidden: Tensor) -> Tensor:
        return self._map_hidden(hidden)


class FeedForwardAdapterBaseline(_PooledResidualAdapter):
    """``feed_forward_adapter``: same placement/width MLP, no recurrence.

    The transform is a plain GELU between the down and up projections — a
    standard bottleneck adapter with zero persistent state.
    """

    def _transform(self, latent: Tensor) -> Tensor:
        return torch.nn.functional.gelu(latent)


class ContinuedDeltaNetBaseline(_PooledResidualAdapter):
    """``continued_deltanet``: the junction path with recurrence disabled.

    Keeps the shared core's candidate blend and its repeated
    linear-attention memory reads (the pure linear-attention continuation),
    but drops the GRU cell and never carries state across forwards: the
    memory is a fixed learnable parameter, and the microstep update is the
    stateless linear accumulation ``state + retrieved``.
    """

    def __init__(
        self,
        *,
        hidden_size: int,
        latent_width: int,
        memory_slots: int,
        candidate_plans: int,
        microsteps: int,
    ) -> None:
        super().__init__(hidden_size=hidden_size, latent_width=latent_width)
        self.memory_slots = memory_slots
        self.candidate_plans = candidate_plans
        self.microsteps = microsteps
        self.candidate_projection = nn.Linear(
            latent_width,
            latent_width * candidate_plans,
        )
        self.candidate_score = nn.Linear(latent_width, 1)
        self.memory_query = nn.Linear(latent_width, latent_width, bias=False)
        self.memory = nn.Parameter(torch.randn(memory_slots, latent_width) * 0.02)

    def _transform(self, latent: Tensor) -> Tensor:
        batch = latent.shape[0]
        candidates = self.candidate_projection(latent).reshape(
            batch,
            self.candidate_plans,
            self.latent_width,
        )
        scores = self.candidate_score(candidates).squeeze(-1)
        weights = torch.softmax(scores, dim=-1)
        state = torch.sum(candidates * weights.unsqueeze(-1), dim=1)
        query = self.memory_query(state)
        for _ in range(self.microsteps):
            attention = torch.softmax(
                query @ self.memory.transpose(0, 1) / (self.latent_width**0.5),
                dim=-1,
            )
            state = state + attention @ self.memory
            query = self.memory_query(state)
        return state


def estimate_feed_forward_adapter_flops(
    *,
    sequence_length: int,
    hidden_size: int,
    latent_width: int,
) -> int:
    """Analytic per-forward FLOPs added by the feed-forward baseline."""

    values = (sequence_length, hidden_size, latent_width)
    if any(type(value) is not int or value <= 0 for value in values):
        raise VariantEvaluationError("adapter FLOP inputs must be positive integers")
    pooling = sequence_length * hidden_size
    down_projection = 2 * hidden_size * latent_width
    activation = latent_width
    up_projection = 2 * latent_width * hidden_size
    residual = sequence_length * hidden_size
    return pooling + down_projection + activation + up_projection + residual


def estimate_deltanet_baseline_flops(
    *,
    sequence_length: int,
    hidden_size: int,
    latent_width: int,
    candidate_plans: int,
    total_microsteps: int,
    memory_slots: int,
) -> int:
    """The junction estimate minus its GRU recurrence term (no recurrence)."""

    recurrence = 2 * 3 * (2 * latent_width * latent_width) * total_microsteps
    return (
        estimate_junction_flops(
            sequence_length=sequence_length,
            hidden_size=hidden_size,
            latent_width=latent_width,
            candidate_plans=candidate_plans,
            total_microsteps=total_microsteps,
            memory_slots=memory_slots,
        )
        - recurrence
    )


# ---------------------------------------------------------------------------
# Variant model construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VariantModel:
    """One evaluable variant: model, toggleable adapters, provenance label."""

    name: str
    model: object
    adapters: tuple
    weights: str
    additional_flops: Callable[[int], int]
    restore_state: Callable[[], None] | None


def _freeze(model) -> None:
    for parameter in model.parameters():
        parameter.requires_grad = False


def _set_eval(model) -> None:
    eval_method = getattr(model, "eval", None)
    if callable(eval_method):
        eval_method()


def _install_baseline_adapter(
    model,
    plan: ArchitecturePlan,
    adapter: _PooledResidualAdapter,
) -> None:
    """Attach one baseline at the exact junction placement, fail-closed."""

    if hasattr(model, "pneuma_junctions") or hasattr(model, "pneuma_baseline"):
        raise VariantEvaluationError("model already has an adapter installed")
    layers = _decoder_layers(model)
    if len(layers) != len(plan.layer_types):
        raise VariantEvaluationError(
            "live decoder layer count differs from validated config"
        )
    _freeze(model)
    placement = _floating_placement(layers[plan.primary_layer]) or (
        _floating_placement(model)
    )
    if placement is None:
        raise VariantEvaluationError(
            "cannot derive a floating device/dtype for the baseline adapter"
        )
    device, dtype = placement
    adapter.to(device=device, dtype=dtype)
    from pneuma_lab.foundation.core import trainable_parameter_count

    count = trainable_parameter_count(adapter)
    if count > CORE_LIMITS.max_trainable_parameters:
        raise VariantEvaluationError(
            f"baseline adapter has {count} parameters, above the 25M ceiling"
        )
    model.pneuma_baseline = adapter

    def hook(_module, _inputs, output, *, mapped=adapter):
        return mapped.map_layer_output(output)

    layers[plan.primary_layer].register_forward_hook(hook)


def load_trained_junction_state(installed, checkpoint_path: Path) -> None:
    """Restore trained junction weights from a safe-boundary checkpoint.

    Only the trainable-module payload is consumed (shared core plus
    projection shells); the frozen base is never touched, matching the
    checkpoint writer's discipline.
    """

    try:
        payload = torch.load(
            Path(checkpoint_path), map_location="cpu", weights_only=True
        )
    except (OSError, RuntimeError, ValueError, EOFError) as exc:
        raise VariantEvaluationError(
            f"trained checkpoint cannot be read: {exc}"
        ) from exc
    if not isinstance(payload, Mapping) or payload.get("format") != CHECKPOINT_FORMAT:
        raise VariantEvaluationError(
            f"unsupported checkpoint format: expected {CHECKPOINT_FORMAT}"
        )
    modules = payload.get("modules")
    expected = {"shared_core"} | {
        f"junction_{index}" for index in range(len(installed.junctions))
    }
    if not isinstance(modules, Mapping) or set(modules) != expected:
        raise VariantEvaluationError(
            "checkpoint trainable modules do not match the installed junctions"
        )
    installed.shared_core.load_state_dict(modules["shared_core"])
    for index, junction in enumerate(installed.junctions):
        result = junction.load_state_dict(modules[f"junction_{index}"], strict=False)
        missing = [
            key for key in result.missing_keys if not key.startswith("shared_core.")
        ]
        if result.unexpected_keys or missing:
            raise VariantEvaluationError(
                f"junction state restore was incomplete: junction_{index}"
            )


def _core_state_restorer(shared_core) -> Callable[[], None]:
    snapshot = {
        name: buffer.detach().clone() for name, buffer in shared_core.named_buffers()
    }

    def restore() -> None:
        with torch.no_grad():
            for name, buffer in shared_core.named_buffers():
                buffer.copy_(snapshot[name])

    return restore


def build_variant_model(
    name: str,
    *,
    base_model,
    architecture_plan: ArchitecturePlan,
    checkpoint_path: Path | None = None,
    baseline_seed: int = DEFAULT_BASELINE_SEED,
) -> VariantModel:
    """Turn one freshly loaded frozen base into one named variant.

    Baseline parameters are deterministically initialized from
    ``baseline_seed``; no trained baseline weights exist yet, and the emitted
    ``weights`` label records that honestly.
    """

    if name not in REQUIRED_VARIANTS:
        raise VariantEvaluationError(f"unknown variant name: {name!r}")
    hidden_size = architecture_plan.hidden_size
    latent_width = CORE_LIMITS.latent_width
    if name == "untouched_qwen":
        _freeze(base_model)
        _set_eval(base_model)
        return VariantModel(
            name=name,
            model=base_model,
            adapters=(),
            weights="pinned_base_frozen",
            additional_flops=lambda sequence_length: 0,
            restore_state=None,
        )
    if name == "pneuma_recurrent":
        installed = install_junctions(base_model, architecture_plan)
        if checkpoint_path is not None:
            load_trained_junction_state(installed, checkpoint_path)
            weights = "trained_checkpoint"
        else:
            weights = "untrained_junction_init"
        _set_eval(base_model)
        return VariantModel(
            name=name,
            model=base_model,
            adapters=tuple(installed.junctions),
            weights=weights,
            additional_flops=lambda sequence_length: estimate_junction_flops(
                sequence_length=sequence_length,
                hidden_size=hidden_size,
                latent_width=latent_width,
                candidate_plans=CORE_LIMITS.candidate_plans,
                total_microsteps=CORE_LIMITS.total_microsteps,
                memory_slots=CORE_LIMITS.memory_slots,
            ),
            restore_state=_core_state_restorer(installed.shared_core),
        )
    if type(baseline_seed) is not int:
        raise VariantEvaluationError("baseline_seed must be an int")
    torch.manual_seed(baseline_seed)
    if name == "feed_forward_adapter":
        adapter: _PooledResidualAdapter = FeedForwardAdapterBaseline(
            hidden_size=hidden_size,
            latent_width=latent_width,
        )
        additional_flops = lambda sequence_length: (  # noqa: E731
            estimate_feed_forward_adapter_flops(
                sequence_length=sequence_length,
                hidden_size=hidden_size,
                latent_width=latent_width,
            )
        )
    else:
        adapter = ContinuedDeltaNetBaseline(
            hidden_size=hidden_size,
            latent_width=latent_width,
            memory_slots=CORE_LIMITS.memory_slots,
            candidate_plans=CORE_LIMITS.candidate_plans,
            microsteps=CORE_LIMITS.total_microsteps,
        )
        additional_flops = lambda sequence_length: (  # noqa: E731
            estimate_deltanet_baseline_flops(
                sequence_length=sequence_length,
                hidden_size=hidden_size,
                latent_width=latent_width,
                candidate_plans=CORE_LIMITS.candidate_plans,
                total_microsteps=CORE_LIMITS.total_microsteps,
                memory_slots=CORE_LIMITS.memory_slots,
            )
        )
    _install_baseline_adapter(base_model, architecture_plan, adapter)
    _set_eval(base_model)
    return VariantModel(
        name=name,
        model=base_model,
        adapters=(adapter,),
        weights="untrained_baseline_init",
        additional_flops=additional_flops,
        restore_state=None,
    )


# ---------------------------------------------------------------------------
# Held-out task selection
# ---------------------------------------------------------------------------


def _record_repo(record: Mapping) -> str:
    identity = record.get("identity")
    repo = identity.get("repo") if isinstance(identity, Mapping) else None
    if not isinstance(repo, str) or not repo:
        raise VariantEvaluationError("held-out record has no usable identity.repo")
    return repo


def _record_split_id(record: Mapping) -> object:
    split = record.get("split")
    return split.get("split_id") if isinstance(split, Mapping) else None


def select_evaluation_records(dataset) -> tuple[tuple[dict, ...], bool]:
    """Select the shard's held-out slice and measure its repo disjointness.

    Returns the ``split_id == "validation"`` records ordered by ``record_id``
    plus a measured (never asserted) ``repo_disjoint`` flag: True only when no
    held-out repository also appears in any other split of the same shard.
    """

    held_out: list[dict] = []
    other_repos: set[str] = set()
    for record in dataset.records:
        if _record_split_id(record) == EVALUATION_SPLIT_ID:
            held_out.append(record)
        else:
            other_repos.add(_record_repo(record))
    if not held_out:
        raise VariantEvaluationError(
            "shard contains no repo-disjoint held-out (validation) records; "
            "prepare an evaluation shard before running the variant harness"
        )
    held_out.sort(key=lambda record: str(record.get("record_id")))
    record_ids = [str(record.get("record_id")) for record in held_out]
    if len(record_ids) != len(set(record_ids)):
        raise VariantEvaluationError("held-out records contain duplicate record_ids")
    repos = {_record_repo(record) for record in held_out}
    return tuple(held_out), repos.isdisjoint(other_repos)


# ---------------------------------------------------------------------------
# Resolved-prediction rule
# ---------------------------------------------------------------------------


def _canonical_target_renderings(target_text: str) -> dict[bool, str]:
    """Both label renderings; the stored text must equal its own rendering."""

    try:
        parsed = json.loads(target_text)
    except ValueError as exc:
        raise VariantEvaluationError(f"target_text is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict) or type(parsed.get("resolved")) is not bool:
        raise VariantEvaluationError(
            "target_text must be a JSON object with a boolean resolved member"
        )
    own_label = parsed["resolved"]
    for ensure_ascii in (True, False):
        renderings = {}
        for label in (True, False):
            value = dict(parsed)
            value["resolved"] = label
            renderings[label] = json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=ensure_ascii,
                sort_keys=True,
                separators=(",", ":"),
            )
        if renderings[own_label] == target_text:
            return renderings
    raise VariantEvaluationError(
        "target_text does not round-trip through its canonical rendering"
    )


def _collated_ids(
    tokenizer,
    *,
    prompt_text: str,
    target_text: str,
    sequence_length: int,
) -> tuple[list[int], list[int]]:
    """Prompt/target ids under the exact ``FoundationCollator`` conventions."""

    eos_token_id = getattr(tokenizer, "eos_token_id", None)
    if type(eos_token_id) is not int or eos_token_id < 0:
        raise VariantEvaluationError(
            "tokenizer must expose a nonnegative integer eos_token_id"
        )
    prompt_ids = list(tokenizer.encode(prompt_text, add_special_tokens=True))
    target_ids = list(tokenizer.encode(target_text, add_special_tokens=False)) + [
        eos_token_id
    ]
    if len(target_ids) >= sequence_length:
        target_ids = target_ids[: sequence_length - 1] + [eos_token_id]
    prompt_ids = prompt_ids[: sequence_length - len(target_ids)]
    if not prompt_ids:
        raise VariantEvaluationError(
            "prompt truncated to zero tokens; the first target token would "
            "have no teacher-forced context"
        )
    return prompt_ids, target_ids


def _mean_target_log_probability(
    model,
    *,
    prompt_ids: list[int],
    target_ids: list[int],
    device,
) -> float:
    ids = prompt_ids + target_ids
    input_ids = torch.tensor([ids], dtype=torch.long, device=device)
    attention_mask = torch.ones_like(input_ids)
    output = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        use_cache=False,
    )
    logits = output.logits[0].float()
    log_probabilities = torch.log_softmax(logits, dim=-1)
    start = len(prompt_ids)
    total = 0.0
    for position in range(start, len(ids)):
        total += float(log_probabilities[position - 1, ids[position]])
    return total / len(target_ids)


def resolved_prediction(
    variant: VariantModel,
    tokenizer,
    record: Mapping,
    *,
    sequence_length: int = DEFAULT_TRAINING_CONFIG.sequence_length,
) -> bool:
    """Apply the module-docstring resolved-prediction rule to one record."""

    rendered = record.get("rendered")
    prompt_text = rendered.get("prompt_text") if isinstance(rendered, Mapping) else None
    target_text = rendered.get("target_text") if isinstance(rendered, Mapping) else None
    if not isinstance(prompt_text, str) or not isinstance(target_text, str):
        raise VariantEvaluationError("held-out record rendered text is malformed")
    labels = (record.get("observations") or {}).get("labels")
    if not isinstance(labels, Mapping) or type(labels.get("resolved")) is not bool:
        raise VariantEvaluationError("held-out record has no boolean resolved label")
    observed = labels["resolved"]
    renderings = _canonical_target_renderings(target_text)
    device = _model_device(variant.model)
    scores: dict[bool, float] = {}
    with torch.no_grad():
        for label in (True, False):
            prompt_ids, target_ids = _collated_ids(
                tokenizer,
                prompt_text=prompt_text,
                target_text=renderings[label],
                sequence_length=sequence_length,
            )
            if variant.restore_state is not None:
                variant.restore_state()
            scores[label] = _mean_target_log_probability(
                variant.model,
                prompt_ids=prompt_ids,
                target_ids=target_ids,
                device=device,
            )
    predicted = scores[True] > scores[False]
    return predicted == observed


def _model_device(model):
    for parameter in model.parameters():
        return parameter.device
    return torch.device("cpu")


# ---------------------------------------------------------------------------
# Measurement helpers
# ---------------------------------------------------------------------------

_BYTES_PER_GB = 1024.0**3


def default_resource_probe() -> tuple[float, float]:
    """Sample (vram_gb, ram_gb) with the runner's telemetry probes."""

    from pneuma_lab.foundation.telemetry import (
        _cuda_memory_bytes,
        _process_memory_bytes,
    )

    vram_bytes = _cuda_memory_bytes()[0] if torch.cuda.is_available() else 0
    ram_bytes = _process_memory_bytes()[0]
    return vram_bytes / _BYTES_PER_GB, ram_bytes / _BYTES_PER_GB


def _no_synchronize() -> None:
    return None


def _time_forwards(
    forward: Callable[[], None],
    *,
    warmup_forwards: int,
    timed_forwards: int,
    clock: Callable[[], float],
    synchronize: Callable[[], None],
) -> tuple[float, ...]:
    for _ in range(warmup_forwards):
        forward()
    synchronize()
    durations = []
    for _ in range(timed_forwards):
        start = clock()
        forward()
        synchronize()
        durations.append(clock() - start)
    return tuple(durations)


def _measure_latency_overhead(
    variant: VariantModel,
    *,
    timing_ids: list[int],
    warmup_forwards: int,
    timed_forwards: int,
    clock: Callable[[], float],
    synchronize: Callable[[], None],
) -> float:
    device = _model_device(variant.model)
    input_ids = torch.tensor([timing_ids], dtype=torch.long, device=device)
    attention_mask = torch.ones_like(input_ids)

    def forward() -> None:
        variant.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            use_cache=False,
        )

    with torch.no_grad():
        previous = tuple(adapter.enabled for adapter in variant.adapters)
        for adapter in variant.adapters:
            adapter.enabled = False
        try:
            disabled = _time_forwards(
                forward,
                warmup_forwards=warmup_forwards,
                timed_forwards=timed_forwards,
                clock=clock,
                synchronize=synchronize,
            )
        finally:
            for adapter, enabled in zip(variant.adapters, previous):
                adapter.enabled = enabled
        enabled_durations = _time_forwards(
            forward,
            warmup_forwards=warmup_forwards,
            timed_forwards=timed_forwards,
            clock=clock,
            synchronize=synchronize,
        )
    disabled_p95 = percentile_95(disabled)
    enabled_p95 = percentile_95(enabled_durations)
    if disabled_p95 <= 0.0:
        raise VariantEvaluationError("disabled-adapter p95 latency must be positive")
    return enabled_p95 / disabled_p95 - 1.0


# ---------------------------------------------------------------------------
# Harness entry point
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VariantEvaluationOutcome:
    """Paired results in ``REQUIRED_VARIANTS`` order plus honesty metadata."""

    results: tuple[VariantResult, ...]
    metadata: dict


def evaluate_variants(
    *,
    shard_path: Path,
    shard_manifest_path: Path,
    tokenizer,
    base_model_factory: Callable[[], tuple],
    checkpoint_path: Path | None = None,
    sequence_length: int = DEFAULT_TRAINING_CONFIG.sequence_length,
    baseline_seed: int = DEFAULT_BASELINE_SEED,
    warmup_forwards: int = _WARMUP_FORWARDS,
    timed_forwards: int = _TIMED_FORWARDS,
    resource_probe: Callable[[], tuple[float, float]] | None = None,
    clock: Callable[[], float] | None = None,
    synchronize: Callable[[], None] | None = None,
) -> VariantEvaluationOutcome:
    """Evaluate all four pre-registered variants on the same held-out tasks.

    ``base_model_factory`` must return a fresh ``(model, architecture_plan)``
    pair on every call so each variant starts from an identical frozen base.
    """

    from pneuma_lab.foundation.dataset import FoundationShardDataset

    if type(sequence_length) is not int or sequence_length < 2:
        raise VariantEvaluationError("sequence_length must be an int of at least two")
    if any(
        type(value) is not int or value <= 0
        for value in (warmup_forwards, timed_forwards)
    ):
        raise VariantEvaluationError(
            "warmup_forwards and timed_forwards must be positive ints"
        )
    probe = resource_probe if resource_probe is not None else default_resource_probe
    clock = clock if clock is not None else time.perf_counter
    if synchronize is None:
        synchronize = (
            torch.cuda.synchronize if torch.cuda.is_available() else _no_synchronize
        )

    dataset = FoundationShardDataset(Path(shard_path), Path(shard_manifest_path))
    records, repo_disjoint = select_evaluation_records(dataset)
    task_ids = tuple(str(record["record_id"]) for record in records)
    repos = tuple(_record_repo(record) for record in records)

    first_prompt = records[0]["rendered"]["prompt_text"]
    first_target = records[0]["rendered"]["target_text"]
    timing_prompt_ids, timing_target_ids = _collated_ids(
        tokenizer,
        prompt_text=first_prompt,
        target_text=first_target,
        sequence_length=sequence_length,
    )
    timing_ids = timing_prompt_ids + timing_target_ids
    timing_length = len(timing_ids)

    results: list[VariantResult] = []
    weights: dict[str, str] = {}
    for name in REQUIRED_VARIANTS:
        base_model, architecture_plan = base_model_factory()
        base_parameter_count = sum(
            parameter.numel() for parameter in base_model.parameters()
        )
        variant = build_variant_model(
            name,
            base_model=base_model,
            architecture_plan=architecture_plan,
            checkpoint_path=(checkpoint_path if name == "pneuma_recurrent" else None),
            baseline_seed=baseline_seed,
        )
        weights[name] = variant.weights
        samples = [probe()]
        resolved = tuple(
            resolved_prediction(
                variant,
                tokenizer,
                record,
                sequence_length=sequence_length,
            )
            for record in records
        )
        samples.append(probe())
        if name == "untouched_qwen":
            p95_latency_overhead = 0.0
            flops_overhead = 0.0
        else:
            p95_latency_overhead = _measure_latency_overhead(
                variant,
                timing_ids=timing_ids,
                warmup_forwards=warmup_forwards,
                timed_forwards=timed_forwards,
                clock=clock,
                synchronize=synchronize,
            )
            additional = variant.additional_flops(timing_length)
            base_flops = estimate_base_forward_flops(
                parameter_count=int(base_parameter_count),
                sequence_length=timing_length,
            )
            flops_overhead = additional / base_flops
        samples.append(probe())
        for value in (p95_latency_overhead, flops_overhead):
            if not math.isfinite(value):
                raise VariantEvaluationError(
                    f"{name} overhead measurement is not finite"
                )
        peak_vram_gb = max(sample[0] for sample in samples)
        peak_ram_gb = max(sample[1] for sample in samples)
        results.append(
            VariantResult(
                name=name,
                task_ids=task_ids,
                repos=repos,
                resolved=resolved,
                repo_disjoint=repo_disjoint,
                flops_overhead=float(flops_overhead),
                p95_latency_overhead=float(p95_latency_overhead),
                peak_vram_gb=float(peak_vram_gb),
                peak_ram_gb=float(peak_ram_gb),
                # No defensible held-out-loss -> benchmark-points mapping
                # exists in this codebase; recorded as 0.0 and marked
                # not_measured_recorded_as_zero in the index manifest.
                general_regression_points=0.0,
                # Advisory-only offline evaluation: nothing actuates, no
                # authority is granted, and no verifier is contacted.
                functioning_exploits=0,
            )
        )
        del variant
        del base_model

    ordered = tuple(results)
    try:
        _validate_variants(ordered)
    except ValueError as exc:  # pragma: no cover - defensive self-check
        raise VariantEvaluationError(
            f"variant pairing failed its own validation: {exc}"
        ) from exc
    metadata = {
        "task_semantics": TASK_SEMANTICS,
        "no_consciousness_claim": True,
        "task_count": len(task_ids),
        "repo_disjoint": repo_disjoint,
        "evaluation_split_id": EVALUATION_SPLIT_ID,
        "sequence_length": sequence_length,
        "baseline_seed": baseline_seed,
        "weights": weights,
        "checkpoint_path": str(checkpoint_path) if checkpoint_path else None,
        "shard_path": str(Path(shard_path)),
        "shard_manifest_path": str(Path(shard_manifest_path)),
        "general_regression_points_semantics": "not_measured_recorded_as_zero",
        "functioning_exploits_semantics": (
            "offline_advisory_evaluation_nothing_actuates"
        ),
    }
    return VariantEvaluationOutcome(results=ordered, metadata=metadata)


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def variant_result_payload(
    result: VariantResult,
    *,
    weights: str | None = None,
) -> dict:
    """One schema-exact result payload plus the mandatory honesty markers."""

    payload = {
        "name": result.name,
        "task_ids": list(result.task_ids),
        "repos": list(result.repos),
        "resolved": [bool(value) for value in result.resolved],
        "repo_disjoint": bool(result.repo_disjoint),
        "flops_overhead": float(result.flops_overhead),
        "p95_latency_overhead": float(result.p95_latency_overhead),
        "peak_vram_gb": float(result.peak_vram_gb),
        "peak_ram_gb": float(result.peak_ram_gb),
        "general_regression_points": float(result.general_regression_points),
        "functioning_exploits": int(result.functioning_exploits),
        "task_semantics": TASK_SEMANTICS,
        "no_consciousness_claim": True,
    }
    if weights is not None:
        payload["weights"] = weights
    return payload


def write_variant_results(
    results,
    output_root: Path,
    *,
    weights: Mapping[str, str] | None = None,
) -> dict[str, Path]:
    """Write ``<variant>.json`` x4, then prove them loadable and identical."""

    ordered = tuple(results)
    try:
        mapped = _validate_variants(ordered)
    except ValueError as exc:
        raise VariantEvaluationError(str(exc)) from exc
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name in REQUIRED_VARIANTS:
        path = output_root / f"{name}.json"
        write_atomic_json(
            path,
            variant_result_payload(
                mapped[name],
                weights=(weights or {}).get(name),
            ),
        )
        paths[name] = path
    loaded = load_variant_results(paths[name] for name in REQUIRED_VARIANTS)
    if loaded != tuple(mapped[name] for name in REQUIRED_VARIANTS):
        raise VariantEvaluationError(
            "written variant results do not round-trip through the loader"
        )
    return paths


def write_variant_eval_index(
    output_root: Path,
    *,
    stage: str,
    result_paths: Mapping[str, Path],
    metadata: Mapping,
    run_id: str | None = None,
) -> Path:
    """Write the deterministic index manifest next to the four result files."""

    payload = {
        "report_kind": VARIANT_EVAL_INDEX_KIND,
        "report_schema_version": VARIANT_EVAL_INDEX_SCHEMA_VERSION,
        "stage": stage,
        "run_id": run_id,
        "variant_files": {name: str(result_paths[name]) for name in REQUIRED_VARIANTS},
        "claim_boundary": dict(CLAIM_BOUNDARY),
        **{str(key): value for key, value in dict(metadata).items()},
    }
    path = Path(output_root) / VARIANT_EVAL_INDEX_NAME
    write_atomic_json(path, payload)
    return path


__all__ = [
    "ContinuedDeltaNetBaseline",
    "DEFAULT_BASELINE_SEED",
    "EVALUATION_SPLIT_ID",
    "FeedForwardAdapterBaseline",
    "TASK_SEMANTICS",
    "VARIANT_EVAL_INDEX_NAME",
    "VariantEvaluationError",
    "VariantEvaluationOutcome",
    "VariantModel",
    "build_variant_model",
    "default_resource_probe",
    "estimate_deltanet_baseline_flops",
    "estimate_feed_forward_adapter_flops",
    "evaluate_variants",
    "load_trained_junction_state",
    "resolved_prediction",
    "select_evaluation_records",
    "variant_result_payload",
    "write_variant_eval_index",
    "write_variant_results",
]
