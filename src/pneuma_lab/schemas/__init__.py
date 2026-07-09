"""Schema loading helpers for Pneuma Lab I/O contracts.

The JSON Schema files live in the repo-root ``schemas/`` directory (NOT inside
the package) so they are language-agnostic and easy to diff against the 9to5
source modules. This module locates that directory and loads the schemas as
plain dicts. Validation against them (via ``jsonschema``) is a Phase-1 concern;
for now we only need load + parse so scaffolding tests can prove every contract
is well-formed.
"""

from __future__ import annotations

import json
from pathlib import Path

# repo root = .../pneuma-lab ; this file = .../pneuma-lab/src/pneuma_lab/schemas/__init__.py
_REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = _REPO_ROOT / "schemas"

# All first-pass contracts. Kept explicit so a missing or accidentally-added
# schema file is caught by the scaffolding test.
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
)

ENVELOPE_SCHEMA_FILES = ("pneuma-trace.schema.json",)

TRAINING_SCHEMA_FILES = ("pneuma-training-example.schema.json",)

ALL_SCHEMA_FILES = (
    INPUT_SCHEMA_FILES
    + OUTPUT_SCHEMA_FILES
    + ENVELOPE_SCHEMA_FILES
    + TRAINING_SCHEMA_FILES
)


def schema_path(filename: str) -> Path:
    """Absolute path to a schema file by name."""
    return SCHEMA_DIR / filename


def load_schema(filename: str) -> dict:
    """Load and parse a single schema file into a dict."""
    with schema_path(filename).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_all_schemas() -> dict[str, dict]:
    """Load every first-pass schema, keyed by filename."""
    return {name: load_schema(name) for name in ALL_SCHEMA_FILES}


__all__ = [
    "SCHEMA_DIR",
    "INPUT_SCHEMA_FILES",
    "OUTPUT_SCHEMA_FILES",
    "ENVELOPE_SCHEMA_FILES",
    "TRAINING_SCHEMA_FILES",
    "ALL_SCHEMA_FILES",
    "schema_path",
    "load_schema",
    "load_all_schemas",
]
