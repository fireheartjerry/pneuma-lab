"""Fail-closed local training configuration and promotion request checks."""

from __future__ import annotations

from dataclasses import dataclass

from pneuma_lab.foundation.curriculum import TOKEN_STAGES
from pneuma_lab.foundation.specs import MODEL_SPECS


class TrainingRequestError(ValueError):
    """Raised before allocation when a training request violates the plan."""


class FoundationRunError(RuntimeError):
    """Raised when a gated foundation run cannot start or continue safely."""


@dataclass(frozen=True)
class LocalTrainingConfig:
    sequence_length: int = 512
    microbatch_size: int = 1
    gradient_accumulation: int = 32
    data_loader_workers: int = 8
    gradient_checkpointing: bool = True
    pack_multiple_documents: bool = False
    max_ram_gb: float = 24.0
    max_vram_gb: float = 7.5
    checkpoint_every_steps: int = 500
    checkpoint_every_seconds: int = 1_800
    thermal_pause_c: float = 85.0


@dataclass(frozen=True)
class FoundationTrainingRequest:
    model_key: str
    token_ceiling: int
    recurrent_gate_passed: bool = False
    freeze_base: bool = True
    freeze_shared_core: bool = False
    enable_rank8_lora: bool = False
    lora_fits_locally: bool = False
    lora_heldout_gain_points: float = 0.0


DEFAULT_TRAINING_CONFIG = LocalTrainingConfig()


def quantization_settings() -> dict[str, object]:
    """Dependency-neutral settings used to construct BitsAndBytesConfig."""

    return {
        "load_in_4bit": True,
        "bnb_4bit_quant_type": "nf4",
        "bnb_4bit_use_double_quant": True,
        "bnb_4bit_compute_dtype": "bfloat16",
    }


def configure_quantized_training_model(model):
    """Prepare one verified base for frozen-base junction training.

    The base is frozen parameter-by-parameter, gradient checkpointing is
    enabled, and the native cache is disabled before any junction attaches.
    A quantized base (NF4 double-quant) additionally requires peft's k-bit
    preparation; fake test doubles are plain modules and skip only that step.
    """

    parameters = getattr(model, "parameters", None)
    if not callable(parameters):
        raise FoundationRunError("training model must expose parameters()")
    quantized = bool(
        getattr(model, "is_loaded_in_4bit", False)
        or getattr(model, "is_quantized", False)
    )
    if quantized:
        try:
            from peft import prepare_model_for_kbit_training
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise FoundationRunError(
                "peft is required to prepare a quantized base for training"
            ) from exc
        model = prepare_model_for_kbit_training(model)
    for parameter in model.parameters():
        parameter.requires_grad = False
    enable_checkpointing = getattr(model, "gradient_checkpointing_enable", None)
    if callable(enable_checkpointing):
        enable_checkpointing()
    config = getattr(model, "config", None)
    if config is not None:
        config.use_cache = False
    return model


def validate_training_request(
    request: FoundationTrainingRequest,
) -> FoundationTrainingRequest:
    """Validate model, stage, transfer, and optional LoRA constraints."""

    spec = MODEL_SPECS.get(request.model_key)
    if spec is None:
        raise TrainingRequestError(f"unknown model key: {request.model_key!r}")
    if not spec.download_allowed:
        raise TrainingRequestError(
            f"{spec.model_id} is a compatibility reference only and cannot be trained"
        )
    if request.model_key == "2b" and request.token_ceiling not in TOKEN_STAGES:
        raise TrainingRequestError(
            "2B token ceiling must be an approved curriculum stage"
        )
    if request.model_key == "4b":
        if not request.recurrent_gate_passed:
            raise TrainingRequestError("4B promotion requires the 2B kill gate to pass")
        if request.token_ceiling > 1_000_000:
            raise TrainingRequestError("4B projection training is capped at 1M tokens")
        if not request.freeze_base or not request.freeze_shared_core:
            raise TrainingRequestError(
                "4B promotion must freeze both the base and transferred shared core"
            )
    if not request.freeze_base:
        raise TrainingRequestError("the quantized Qwen base must remain frozen")
    if request.enable_rank8_lora and (
        not request.lora_fits_locally or request.lora_heldout_gain_points <= 0.0
    ):
        raise TrainingRequestError(
            "rank-8 LoRA requires measured local fit and positive held-out gain"
        )
    return request
