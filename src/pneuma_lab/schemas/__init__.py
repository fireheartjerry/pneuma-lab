"""Schema loading helpers for Pneuma Lab contracts and manifests.

The JSON Schema files live in the repo-root ``schemas/`` directory (NOT inside
the package) so they are language-agnostic and easy to diff against the 9to5
source modules. This module locates that directory and loads the schemas as
plain dicts. The explicit registry keeps frames, envelopes, training controls,
and project-state manifests discoverable and makes accidental schema drift fail
the test suite.
"""

from __future__ import annotations

import json
from pathlib import Path

# repo root = .../pneuma-lab ; this file = .../pneuma-lab/src/pneuma_lab/schemas/__init__.py
_REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = _REPO_ROOT / "schemas"

# Kept explicit so a missing or accidentally-added schema is caught by tests.
INPUT_SCHEMA_FILES = (
    "world-frame.schema.json",
    "agent-trace-frame.schema.json",
    "memory-frame.schema.json",
    "governance-frame.schema.json",
    "intervention-frame.schema.json",
)

OUTPUT_SCHEMA_FILES = (
    "psyche-state-frame.schema.json",
    "workspace-broadcast.schema.json",
    "instinct-signal.schema.json",
    "control-pressure-vector.schema.json",
    "authority-request.schema.json",
    "causal-trace.schema.json",
    "consciousness-evidence-frame.schema.json",
    "grounded-self-report.schema.json",
    "risk-estimate-frame.schema.json",
)

ENVELOPE_SCHEMA_FILES = ("pneuma-trace.schema.json",)

# Container manifests (not cognition frames): aggregate I/O frames for the
# shadow nervous system. Validated via ``validate.validate_bundle``.
IO_BUNDLE_SCHEMA_FILES = (
    "pneuma-input-bundle.schema.json",
    "pneuma-output-bundle.schema.json",
)

# Evidence-campaign summary manifests (conservative, no level claim). Validated
# via ``validate.validate_campaign``.
EVIDENCE_CAMPAIGN_SCHEMA_FILES = ("subject-evidence-campaign.schema.json",)

# Expressive-view renderings (the Pneuma Voice). Derived, non-authoritative:
# validated via ``validate.validate_thought_stream``; never a cognition frame.
EXPRESSIVE_VIEW_SCHEMA_FILES = ("thought-stream.schema.json",)

TRAINING_SCHEMA_FILES = (
    "pneuma-training-example.schema.json",
    "estimator-run-manifest.schema.json",
    "estimator-training-authorization.schema.json",
    "pneuma-brain-corpus-authorization.schema.json",
)

MANIFEST_SCHEMA_FILES = ("project-status.schema.json",)

# Measurement-system analysis of an elicited metric channel. Descriptive
# metrology about a measurement procedure, not a cognition frame and not
# consciousness evidence: validated via ``gauge.card.validateCard``.
GAUGE_SCHEMA_FILES = ("gauge-card.schema.json",)

FOUNDATION_SCHEMA_FILES = (
    "foundation-training-authorization.schema.json",
    "foundation-run-manifest.schema.json",
    "learned-subject-profile.schema.json",
    "memory-erasure-receipt.schema.json",
    "foundation-training-record.schema.json",
    "foundation-suite-report.schema.json",
)

RESAMPLING_SCHEMA_FILES = (
    "resampling-study-manifest.schema.json",
    "resampling-branch-program-registry.schema.json",
    "resampling-prefix-schedule.schema.json",
    "resampling-prefix-receipt.schema.json",
    "resampling-assignment-ledger.schema.json",
    "resampling-packet-index.schema.json",
    "resampling-task-block.schema.json",
    "resampling-blinded-projection.schema.json",
    "resampling-analysis-freeze.schema.json",
    "resampling-analysis.schema.json",
    "resampling-power-report.schema.json",
    "resampling-timing-no-go.schema.json",
    "resampling-unblind-receipt.schema.json",
    "resampling-artifact-root.schema.json",
)

CLOUD_SCHEMA_FILES = (
    "cloud-input-lock.schema.json",
    "cloud-experiment-manifest.schema.json",
    "cloud-architecture-manifest.schema.json",
    "cloud-image-manifest.schema.json",
    "cloud-job-lease.schema.json",
    "cloud-spend-authorization.schema.json",
    "cloud-approval-receipt.schema.json",
    "cloud-result-binding.schema.json",
    "cloud-pilot-protocol.schema.json",
    "cloud-interruption-qualification-receipt.schema.json",
    "cloud-production-execution-surface.schema.json",
    "cloud-retrieval-authorization.schema.json",
    "cloud-qualification-audit.schema.json",
    "cloud-worker-admission-measurement.schema.json",
    "cloud-pilot-admission-receipt.schema.json",
    "cloud-image-build-receipt.schema.json",
    "cloud-aws-account-verification.schema.json",
    "cloud-approver-key-registry.schema.json",
    "cloud-licence-audit.schema.json",
    "cloud-unattended-spend-policy.schema.json",
    "cloud-preparation-envelope.schema.json",
    "cloud-preparation-admission.schema.json",
    "cloud-input-inventory-plan.schema.json",
    "cloud-payload-retrieval-manifest.schema.json",
    "cloud-payload-retrieval-plan.schema.json",
    "cloud-payload-pricing-receipt.schema.json",
    "cloud-payload-mirror-receipt.schema.json",
    "cloud-step5b-lifecycle-receipt.schema.json",
    "cloud-isolation-qualification-receipt.schema.json",
    "cloud-production-role-receipt.schema.json",
    "cloud-lease-contention-qualification-receipt.schema.json",
    "cloud-lease-contention-cleanup-receipt.schema.json",
    "cloud-batch-array-qualification-receipt.schema.json",
)

ALL_SCHEMA_FILES = (
    INPUT_SCHEMA_FILES
    + OUTPUT_SCHEMA_FILES
    + ENVELOPE_SCHEMA_FILES
    + IO_BUNDLE_SCHEMA_FILES
    + EVIDENCE_CAMPAIGN_SCHEMA_FILES
    + EXPRESSIVE_VIEW_SCHEMA_FILES
    + TRAINING_SCHEMA_FILES
    + MANIFEST_SCHEMA_FILES
    + FOUNDATION_SCHEMA_FILES
    + GAUGE_SCHEMA_FILES
    + RESAMPLING_SCHEMA_FILES
    + CLOUD_SCHEMA_FILES
)


def schema_path(filename: str) -> Path:
    """Absolute path to a schema file by name."""
    return SCHEMA_DIR / filename


def load_schema(filename: str) -> dict:
    """Load and parse a single schema file into a dict."""
    with schema_path(filename).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_all_schemas() -> dict[str, dict]:
    """Load every registered schema, keyed by filename."""
    return {name: load_schema(name) for name in ALL_SCHEMA_FILES}


__all__ = [
    "SCHEMA_DIR",
    "INPUT_SCHEMA_FILES",
    "OUTPUT_SCHEMA_FILES",
    "ENVELOPE_SCHEMA_FILES",
    "IO_BUNDLE_SCHEMA_FILES",
    "EVIDENCE_CAMPAIGN_SCHEMA_FILES",
    "EXPRESSIVE_VIEW_SCHEMA_FILES",
    "TRAINING_SCHEMA_FILES",
    "MANIFEST_SCHEMA_FILES",
    "FOUNDATION_SCHEMA_FILES",
    "GAUGE_SCHEMA_FILES",
    "RESAMPLING_SCHEMA_FILES",
    "CLOUD_SCHEMA_FILES",
    "ALL_SCHEMA_FILES",
    "schema_path",
    "load_schema",
    "load_all_schemas",
]
