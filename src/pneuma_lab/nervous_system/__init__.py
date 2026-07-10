"""PneumaNervousSystem-v0: shadow-mode model-backed I/O shell (advisory only).

This package wraps the offline PneumaBrain-v0.1 risk estimator into auditable
Pneuma frames. It runs in SHADOW MODE: it emits advisory frames and appends to a
shadow log, but never actuates, never grants authority, and never contacts a
verifier. The evidence it produces is Level-1-compatible harness evidence, not a
consciousness claim. It imports nothing from 9to5.
"""

MODEL_ID = "PneumaBrain-v0.1"

BLOCKED_USES = (
    "no_runtime_authority",
    "no_verifier_bypass",
    "no_consciousness_claim",
)

LIMITATIONS = (
    "shadow_mode_advisory_only",
    "single_model_signal_not_integrated_psyche",
    "level_1_compatible_harness_evidence_only",
    "no_real_subject_evaluated",
)

# Constants above are defined before this import so the leaf modules (frames,
# shadow_evidence, runtime) can import them without a cycle.
from pneuma_lab.nervous_system.runtime import ShadowNervousSystem  # noqa: E402
from pneuma_lab.nervous_system.subject import BaselinePsycheSubject  # noqa: E402
from pneuma_lab.nervous_system.subject_runtime import run_subject  # noqa: E402

__all__ = [
    "ShadowNervousSystem",
    "BaselinePsycheSubject",
    "run_subject",
    "MODEL_ID",
    "BLOCKED_USES",
    "LIMITATIONS",
]
