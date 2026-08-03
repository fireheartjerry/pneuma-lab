from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.manifests import (
    validate_ephemeral_dual_worker_qualification_receipt,
)


ROOT = Path(__file__).resolve().parents[2]
RECEIPT = (
    ROOT
    / "docs/research/neurips-2026-workshop/evidence/"
    / "dual-l40s-qualification-011-execution-receipt-20260803.json"
)


def test_current_terminal_no_go_receipt_is_schema_bound() -> None:
    record = json.loads(RECEIPT.read_text(encoding="utf-8"))
    validated = validate_ephemeral_dual_worker_qualification_receipt(record)
    assert validated["status"] == "no_go"
    assert validated["launch"]["retry_attempts"] == 1
    assert validated["teardown"]["teardown_complete_except_provider_history"] is True


def test_ephemeral_receipt_rejects_retry_or_launch_contract_drift() -> None:
    record = json.loads(RECEIPT.read_text(encoding="utf-8"))
    record = deepcopy(record)
    record["launch"]["retry_attempts"] = 2
    with pytest.raises(CloudManifestError):
        validate_ephemeral_dual_worker_qualification_receipt(record)
