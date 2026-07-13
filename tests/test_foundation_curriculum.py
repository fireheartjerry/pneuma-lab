"""Learning-curve and local-training policy tests."""

from __future__ import annotations

import pytest

from pneuma_lab.foundation.curriculum import (
    LrTrial,
    next_token_stage,
    select_learning_rate,
)
from pneuma_lab.foundation.training import (
    DEFAULT_TRAINING_CONFIG,
    FoundationTrainingRequest,
    TrainingRequestError,
    quantization_settings,
    validate_training_request,
)


def test_learning_rate_smoke_selects_best_stable_and_lower_tie() -> None:
    trials = (
        LrTrial(5e-5, validation_loss=0.8, stable=True),
        LrTrial(1e-4, validation_loss=0.7, stable=True),
        LrTrial(2e-4, validation_loss=0.7, stable=True),
    )
    assert select_learning_rate(trials) == pytest.approx(1e-4)


def test_learning_rate_smoke_rejects_unapproved_or_all_unstable_trials() -> None:
    with pytest.raises(ValueError, match="approved learning rates"):
        select_learning_rate((LrTrial(3e-4, validation_loss=0.1, stable=True),))
    with pytest.raises(ValueError, match="no stable"):
        select_learning_rate(
            tuple(
                LrTrial(rate, validation_loss=0.1, stable=False)
                for rate in (5e-5, 1e-4, 2e-4)
            )
        )


def test_curriculum_requires_gate_and_half_point_extension_gain() -> None:
    assert next_token_stage(100_000, stable=True, regression_passed=True) == 500_000
    assert next_token_stage(500_000, stable=True, regression_passed=True) == 2_000_000
    assert (
        next_token_stage(
            2_000_000,
            stable=True,
            regression_passed=True,
            falsification_gate_passed=False,
        )
        is None
    )
    assert (
        next_token_stage(
            2_000_000,
            stable=True,
            regression_passed=True,
            falsification_gate_passed=True,
        )
        == 8_000_000
    )
    assert (
        next_token_stage(
            8_000_000,
            stable=True,
            regression_passed=True,
            validation_gain_points=0.49,
        )
        is None
    )
    assert (
        next_token_stage(
            8_000_000,
            stable=True,
            regression_passed=True,
            validation_gain_points=0.5,
        )
        == 16_000_000
    )
    assert (
        next_token_stage(
            16_000_000,
            stable=True,
            regression_passed=True,
            validation_gain_points=0.5,
        )
        == 32_000_000
    )


def test_curriculum_stops_immediately_on_instability_or_regression() -> None:
    assert next_token_stage(500_000, stable=False, regression_passed=True) is None
    assert next_token_stage(500_000, stable=True, regression_passed=False) is None


def test_default_local_training_configuration_is_bounded() -> None:
    config = DEFAULT_TRAINING_CONFIG
    assert config.sequence_length == 512
    assert config.microbatch_size == 1
    assert config.gradient_accumulation == 32
    assert config.data_loader_workers == 8
    assert config.gradient_checkpointing is True
    assert config.pack_multiple_documents is False
    assert config.max_ram_gb == pytest.approx(24.0)
    assert config.max_vram_gb == pytest.approx(7.5)
    assert quantization_settings() == {
        "load_in_4bit": True,
        "bnb_4bit_quant_type": "nf4",
        "bnb_4bit_use_double_quant": True,
        "bnb_4bit_compute_dtype": "bfloat16",
    }


def test_training_request_rejects_397b_and_ungated_4b() -> None:
    with pytest.raises(TrainingRequestError, match="compatibility reference"):
        validate_training_request(
            FoundationTrainingRequest(model_key="397b", token_ceiling=100_000)
        )
    with pytest.raises(TrainingRequestError, match="2B kill gate"):
        validate_training_request(
            FoundationTrainingRequest(model_key="4b", token_ceiling=1_000_000)
        )
    validated = validate_training_request(
        FoundationTrainingRequest(
            model_key="4b",
            token_ceiling=1_000_000,
            recurrent_gate_passed=True,
            freeze_base=True,
            freeze_shared_core=True,
        )
    )
    assert validated.model_key == "4b"


def test_lora_requires_local_fit_and_measured_heldout_gain() -> None:
    with pytest.raises(TrainingRequestError, match="LoRA"):
        validate_training_request(
            FoundationTrainingRequest(
                model_key="2b",
                token_ceiling=2_000_000,
                enable_rank8_lora=True,
                lora_fits_locally=True,
                lora_heldout_gain_points=0.0,
            )
        )
