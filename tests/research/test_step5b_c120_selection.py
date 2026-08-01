from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "docs/research/neurips-2026-workshop/evidence/step5b-c120-g-roster-20260801"
AUTHORITY = ROOT / "docs/research/neurips-2026-workshop/52-g-roster-c120-authority-amendment.md"


def _module(name: str):
    path = ROOT / "scripts/research" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_swe_c120_selection_is_exact_and_bound() -> None:
    module = _module("step5b_c120_selection")
    selection = json.loads((EVIDENCE / "swe-selection.json").read_text(encoding="utf-8"))
    assert len(selection["rows"]) == 144
    assert Counter(row["language"] for row in selection["rows"]) == Counter(module.REQUIRED_REPOSITORIES)
    assert all(row["licence_status"] == "admissible" for row in selection["rows"])
    assert all(row["oci"]["manifest_digest"].startswith("sha256:") for row in selection["rows"])
    for language in module.REQUIRED_REPOSITORIES:
        repos = [row["repo"].lower() for row in selection["rows"] if row["language"] == language]
        assert len(repos) == len(set(repos))
    assert selection["authority_sha256"] == hashlib.sha256(AUTHORITY.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert hashlib.sha256((EVIDENCE / "swe-selection.json").read_bytes()).hexdigest() == "e6b4a052426f234daf7f1473d91ae3a861bd1dc5e270160936f4bc6015574071"


def test_tau2_c120_selection_uses_exact_sealed_pools() -> None:
    selection = json.loads((EVIDENCE / "tau2-selection.json").read_text(encoding="utf-8"))
    assert selection["source_sha256"] == {
        "airline.json": "ccd8ba737b4cc371415af70151187788f728d6108d0916e73bb4317b40542052",
        "banking.json": "213c7f3e6dc0420b1184ee271e39e38c6ece3c43edfa362db49a560828ebd543",
        "telecom-split-tasks.json": "605b488bb9a6acb3c7f4505240a855fdc8681d09aadb16a8f38b2efcfc5c3aec",
        "telecom.json": "37e562e1ae3242577407e1303b1548bc64e7ea68e37d36173e6747990ceaf8a4",
    }
    assert selection["eligible_pool_sizes"] == {"airline": 50, "banking": 88, "telecom": 114}
    assert Counter(row["domain"] for row in selection["rows"]) == Counter({"airline": 20, "telecom": 16, "banking": 13})
    assert all(len(ids) == len(set(ids)) for ids in selection["eligible_task_ids"].values())
    assert selection["authority_sha256"] == hashlib.sha256(AUTHORITY.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
