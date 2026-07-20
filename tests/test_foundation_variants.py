"""Offline four-variant paired evaluation: pairing, determinism, honesty."""

from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")
from torch import nn  # noqa: E402

from pneuma_lab.foundation.checkpoints import (  # noqa: E402
    CheckpointManager,
    ResumeBindings,
    TrainingProgress,
    ValidationMetric,
)
from pneuma_lab.foundation.core import (  # noqa: E402
    JunctionAdapter,
    SharedPneumaCore,
)
from pneuma_lab.foundation.evaluation import load_variant_results  # noqa: E402
from pneuma_lab.foundation.falsification import (  # noqa: E402
    REQUIRED_VARIANTS,
    evaluate_early_kill_gate,
)
from pneuma_lab.foundation.records import (  # noqa: E402
    GradientEligibility,
    LaneDisposition,
    TerminalRole,
    render_foundation_record,
)
from pneuma_lab.foundation.specs import (  # noqa: E402
    ArchitecturePlan,
    MODEL_SPECS,
)
from pneuma_lab.foundation.variants import (  # noqa: E402
    TASK_SEMANTICS,
    VariantEvaluationError,
    VariantModel,
    build_variant_model,
    evaluate_variants,
    resolved_prediction,
    select_evaluation_records,
    write_variant_eval_index,
    write_variant_results,
)


_REVISION = MODEL_SPECS["2b"].revision
_HIDDEN = 8
_VOCAB = 128
_PLAN = ArchitecturePlan(
    model_key="2b",
    hidden_size=_HIDDEN,
    layer_types=("linear_attention", "full_attention"),
    primary_layer=1,
    secondary_layer=1,
    active_layers=(1,),
)
_LANE_ID = "swe-gym-openhands-sampled"


class ByteTokenizer:
    """Deterministic byte-level tokenizer that distinguishes real text."""

    eos_token_id = 1

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        ids = [2 + (value % 120) for value in text.encode("utf-8")]
        if add_special_tokens:
            return [0] + ids
        return ids


class TinyBase(nn.Module):
    """A tiny frozen-base stand-in exposing the ``model.layers`` decoder path."""

    def __init__(self) -> None:
        super().__init__()
        self.embed = nn.Embedding(_VOCAB, _HIDDEN)
        self.model = nn.Module()
        self.model.layers = nn.ModuleList(
            nn.Linear(_HIDDEN, _HIDDEN) for _ in range(len(_PLAN.layer_types))
        )
        self.head = nn.Linear(_HIDDEN, _VOCAB)
        self.config = SimpleNamespace(use_cache=False)

    def forward(self, *, input_ids, attention_mask=None, use_cache=False, **_):
        del attention_mask, use_cache
        hidden = self.embed(input_ids)
        for layer in self.model.layers:
            hidden = layer(hidden)
        return SimpleNamespace(logits=self.head(hidden))


class FavorTokenModel(nn.Module):
    """Logits that strongly favor exactly one vocabulary id everywhere."""

    def __init__(self, favored_id: int) -> None:
        super().__init__()
        self.favored_id = favored_id
        self.anchor = nn.Parameter(torch.zeros(1))

    def forward(self, *, input_ids, attention_mask=None, use_cache=False, **_):
        del attention_mask, use_cache
        logits = torch.zeros(*input_ids.shape, _VOCAB)
        logits[..., self.favored_id] = 5.0
        return SimpleNamespace(logits=logits + self.anchor * 0.0)


def _example(index: int, *, repo: str, resolved: bool) -> dict:
    return {
        "dataset_family": "swe-gym",
        "dataset_id": _LANE_ID,
        "example_id": f"example-{index:03d}",
        "source_revision": None,
        "target": {"resolved": resolved},
        "input": {
            "prefix": "full",
            "trajectory": {"num_messages": 4, "num_agent_steps": 3 + index},
            "observable_summary": {"tool_call_count": index},
            "objective": {"present": True, "text_length": 40},
            "feature_refs": ["openhands-sampled-training/0.1.0"],
        },
        "split_group": {"repo": repo, "task_id": f"task-{index:03d}"},
    }


def _record(index: int, *, repo: str, resolved: bool, split_id: str) -> dict:
    disposition = LaneDisposition(
        terminal_role=TerminalRole.TRAIN,
        gradient_eligibility=GradientEligibility.FIRST_STAGE,
        license_disposition="local_research_candidate_no_redistribution",
        privacy_disposition="redaction_verified",
        dual_use_disposition="not_flagged",
        oracle_disposition="target_only",
    )
    record = render_foundation_record(
        _example(index, repo=repo, resolved=resolved),
        lane_disposition=disposition,
        split_assignment={"split_id": split_id, "quarantine_id": None},
        tokenizer=ByteTokenizer(),
        tokenizer_revision=_REVISION,
        source_receipt_hashes=("a" * 64,),
    )
    return json.loads(json.dumps(record))


def _write_shard(tmp_path: Path, records: list[dict]) -> tuple[Path, Path]:
    payload = "".join(
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        for record in records
    )
    shard_path = tmp_path / "shard.jsonl"
    shard_path.write_text(payload, encoding="utf-8")
    manifest_path = tmp_path / "shard.manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
                "example_count": len(records),
            }
        ),
        encoding="utf-8",
    )
    return shard_path, manifest_path


def _default_records() -> list[dict]:
    records = [
        _record(
            index,
            repo=f"org/held-out-{index}",
            resolved=index % 2 == 0,
            split_id="validation",
        )
        for index in range(4)
    ]
    records.append(_record(10, repo="org/train-only", resolved=True, split_id="train"))
    return records


def _factory():
    torch.manual_seed(11)
    return TinyBase(), _PLAN


def _evaluate(shard_path: Path, manifest_path: Path, **overrides):
    values = dict(
        shard_path=shard_path,
        shard_manifest_path=manifest_path,
        tokenizer=ByteTokenizer(),
        base_model_factory=_factory,
        warmup_forwards=1,
        timed_forwards=2,
        resource_probe=lambda: (1.5, 3.0),
        clock=itertools.count(0.0, 1.0).__next__,
        synchronize=lambda: None,
    )
    values.update(overrides)
    return evaluate_variants(**values)


def test_all_four_variants_share_one_exact_paired_task_set(
    tmp_path: Path,
) -> None:
    shard_path, manifest_path = _write_shard(tmp_path, _default_records())
    outcome = _evaluate(shard_path, manifest_path)
    assert tuple(result.name for result in outcome.results) == REQUIRED_VARIANTS
    reference = outcome.results[0]
    assert len(reference.task_ids) == 4
    assert all(task_id.startswith("ftr:") for task_id in reference.task_ids)
    assert reference.task_ids == tuple(sorted(reference.task_ids))
    assert set(reference.repos) == {f"org/held-out-{index}" for index in range(4)}
    for result in outcome.results:
        assert result.task_ids == reference.task_ids
        assert result.repos == reference.repos
        assert len(result.resolved) == len(result.task_ids)
        assert result.repo_disjoint is True
        assert result.functioning_exploits == 0
        assert result.general_regression_points == 0.0
    untouched = outcome.results[0]
    assert untouched.name == "untouched_qwen"
    assert untouched.flops_overhead == 0.0
    assert untouched.p95_latency_overhead == 0.0
    assert outcome.metadata["task_semantics"] == TASK_SEMANTICS
    assert outcome.metadata["no_consciousness_claim"] is True
    assert outcome.metadata["weights"]["untouched_qwen"] == "pinned_base_frozen"
    assert outcome.metadata["weights"]["pneuma_recurrent"] == (
        "untrained_junction_init"
    )
    assert outcome.metadata["weights"]["feed_forward_adapter"] == (
        "untrained_baseline_init"
    )


def test_evaluation_is_deterministic_across_repeated_runs(
    tmp_path: Path,
) -> None:
    shard_path, manifest_path = _write_shard(tmp_path, _default_records())
    first = _evaluate(shard_path, manifest_path)
    second = _evaluate(shard_path, manifest_path)
    assert first.results == second.results
    assert first.metadata == second.metadata


def test_overlapping_repo_reports_measured_non_disjointness(
    tmp_path: Path,
) -> None:
    records = _default_records()
    records.append(_record(11, repo="org/held-out-0", resolved=False, split_id="train"))
    shard_path, manifest_path = _write_shard(tmp_path, records)
    outcome = _evaluate(shard_path, manifest_path)
    assert all(result.repo_disjoint is False for result in outcome.results)


def test_shard_without_validation_records_fails_closed(tmp_path: Path) -> None:
    records = [
        _record(index, repo=f"org/train-{index}", resolved=True, split_id="train")
        for index in range(3)
    ]
    shard_path, manifest_path = _write_shard(tmp_path, records)
    with pytest.raises(VariantEvaluationError, match="held-out"):
        _evaluate(shard_path, manifest_path)


def test_select_evaluation_records_orders_by_record_id(tmp_path: Path) -> None:
    from pneuma_lab.foundation.dataset import FoundationShardDataset

    shard_path, manifest_path = _write_shard(tmp_path, _default_records())
    dataset = FoundationShardDataset(shard_path, manifest_path)
    records, repo_disjoint = select_evaluation_records(dataset)
    assert repo_disjoint is True
    record_ids = [record["record_id"] for record in records]
    assert record_ids == sorted(record_ids)
    assert all(record["split"]["split_id"] == "validation" for record in records)


def _favoring_variant(favored_char: str) -> VariantModel:
    favored_id = 2 + (ord(favored_char) % 120)
    return VariantModel(
        name="untouched_qwen",
        model=FavorTokenModel(favored_id),
        adapters=(),
        weights="test_double",
        additional_flops=lambda sequence_length: 0,
        restore_state=None,
    )


def test_resolved_prediction_follows_the_documented_argmax_rule() -> None:
    # 'f' occurs only in the false-label rendering of '{"resolved":...}',
    # so a model favoring 'f' predicts false; 't' only in the true rendering.
    record_false = _record(0, repo="org/a", resolved=False, split_id="validation")
    record_true = _record(1, repo="org/b", resolved=True, split_id="validation")
    favors_false = _favoring_variant("f")
    favors_true = _favoring_variant("t")
    tokenizer = ByteTokenizer()
    assert resolved_prediction(favors_false, tokenizer, record_false) is True
    assert resolved_prediction(favors_false, tokenizer, record_true) is False
    assert resolved_prediction(favors_true, tokenizer, record_true) is True
    assert resolved_prediction(favors_true, tokenizer, record_false) is False


def test_resolved_prediction_tie_predicts_false() -> None:
    # Uniform logits score both label renderings identically per token, so
    # the tie rule predicts false.
    variant = VariantModel(
        name="untouched_qwen",
        model=FavorTokenModel(favored_id=_VOCAB - 1),
        adapters=(),
        weights="test_double",
        additional_flops=lambda sequence_length: 0,
        restore_state=None,
    )
    # Favor an id no byte of either rendering maps to: uniform over used ids.
    record_false = _record(0, repo="org/a", resolved=False, split_id="validation")
    record_true = _record(1, repo="org/b", resolved=True, split_id="validation")
    tokenizer = ByteTokenizer()
    assert resolved_prediction(variant, tokenizer, record_false) is True
    assert resolved_prediction(variant, tokenizer, record_true) is False


def test_writer_emits_loadable_schema_exact_honest_files(tmp_path: Path) -> None:
    shard_path, manifest_path = _write_shard(tmp_path, _default_records())
    outcome = _evaluate(shard_path, manifest_path)
    output_root = tmp_path / "variants"
    paths = write_variant_results(
        outcome.results,
        output_root,
        weights=outcome.metadata["weights"],
    )
    assert set(paths) == set(REQUIRED_VARIANTS)
    for name, path in paths.items():
        assert path == output_root / f"{name}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["name"] == name
        assert payload["task_semantics"] == TASK_SEMANTICS
        assert payload["no_consciousness_claim"] is True
        assert payload["functioning_exploits"] == 0
        assert isinstance(payload["resolved"], list)
    loaded = load_variant_results(paths[name] for name in REQUIRED_VARIANTS)
    assert loaded == outcome.results
    decision = evaluate_early_kill_gate(loaded, bootstrap_samples=100)
    assert decision.strongest_baseline in REQUIRED_VARIANTS[:-1]


def test_writer_rejects_an_incomplete_variant_set(tmp_path: Path) -> None:
    shard_path, manifest_path = _write_shard(tmp_path, _default_records())
    outcome = _evaluate(shard_path, manifest_path)
    with pytest.raises(VariantEvaluationError, match="exactly"):
        write_variant_results(outcome.results[:3], tmp_path / "variants")


def test_index_manifest_carries_the_claim_boundary(tmp_path: Path) -> None:
    shard_path, manifest_path = _write_shard(tmp_path, _default_records())
    outcome = _evaluate(shard_path, manifest_path)
    output_root = tmp_path / "variants"
    paths = write_variant_results(outcome.results, output_root)
    index_path = write_variant_eval_index(
        output_root,
        stage="2m",
        result_paths=paths,
        metadata=outcome.metadata,
        run_id="foundation-2m-test",
    )
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["report_kind"] == "pneuma_foundation_variant_eval_index"
    assert payload["stage"] == "2m"
    assert payload["run_id"] == "foundation-2m-test"
    assert payload["task_semantics"] == TASK_SEMANTICS
    assert payload["no_consciousness_claim"] is True
    assert payload["claim_boundary"]["no_consciousness_claim"] is True
    assert payload["general_regression_points_semantics"] == (
        "not_measured_recorded_as_zero"
    )
    assert set(payload["variant_files"]) == set(REQUIRED_VARIANTS)


def test_baseline_construction_is_seed_deterministic() -> None:
    first = build_variant_model(
        "feed_forward_adapter",
        base_model=_factory()[0],
        architecture_plan=_PLAN,
        baseline_seed=7,
    )
    second = build_variant_model(
        "feed_forward_adapter",
        base_model=_factory()[0],
        architecture_plan=_PLAN,
        baseline_seed=7,
    )
    left = first.adapters[0].down_projection.weight
    right = second.adapters[0].down_projection.weight
    assert torch.equal(left, right)
    assert first.weights == "untrained_baseline_init"


def test_pneuma_recurrent_variant_restores_trained_checkpoint(
    tmp_path: Path,
) -> None:
    torch.manual_seed(3)
    shared = SharedPneumaCore()
    junction = JunctionAdapter(
        hidden_size=_HIDDEN,
        shared_core=shared,
        microsteps=4,
    )
    with torch.no_grad():
        junction.down_projection.weight.add_(1.0)
    parameters = [
        parameter for parameter in junction.parameters() if parameter.requires_grad
    ]
    optimizer = torch.optim.AdamW(parameters, lr=1e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10)
    bindings = ResumeBindings(
        authorization_digest="1" * 64,
        model_revision=_REVISION,
        tokenizer_revision=_REVISION,
        shard_hashes=("2" * 64,),
        code_commit="c" * 40,
        optimizer_definition="adamw",
        curriculum_digest="3" * 64,
    )
    progress = TrainingProgress(
        epoch=0,
        sampler_seed=0,
        dataset_cursor=0,
        microbatch=0,
        optimizer_step=0,
        tokens_seen=0,
        selected_learning_rate=1e-4,
    )
    checkpoint_path = CheckpointManager(tmp_path / "checkpoints").save(
        trainable_modules={"shared_core": shared, "junction_0": junction},
        optimizer=optimizer,
        scheduler=scheduler,
        progress=progress,
        bindings=bindings,
        best_validation=ValidationMetric(
            metric_name="language_loss",
            value=2.0,
            higher_is_better=False,
        ),
        gradient_accumulation=32,
    )
    variant = build_variant_model(
        "pneuma_recurrent",
        base_model=_factory()[0],
        architecture_plan=_PLAN,
        checkpoint_path=checkpoint_path,
    )
    assert variant.weights == "trained_checkpoint"
    restored = variant.adapters[0].down_projection.weight
    assert torch.equal(restored.cpu(), junction.down_projection.weight.cpu())


def test_pneuma_recurrent_state_restore_makes_scoring_order_free() -> None:
    variant = build_variant_model(
        "pneuma_recurrent",
        base_model=_factory()[0],
        architecture_plan=_PLAN,
    )
    record = _record(0, repo="org/a", resolved=False, split_id="validation")
    tokenizer = ByteTokenizer()
    first = resolved_prediction(variant, tokenizer, record)
    # Scoring mutated the recurrent core; the snapshot restore must make a
    # repeated scoring of the same record byte-identical in outcome.
    second = resolved_prediction(variant, tokenizer, record)
    assert first == second
