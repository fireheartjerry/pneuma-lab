from __future__ import annotations

import copy

from pneuma_lab.adapters import envelope as env


def test_canonical_json_is_sorted_and_compact():
    s = env.canonical_json({"b": 1, "a": 2})
    assert s == '{"a":2,"b":1}'


def test_identity_hash_is_deterministic_and_prefixed():
    ids1 = env.derive_ids("swe-gym", "getmoto__moto-5752", "f70b1a29")
    ids2 = env.derive_ids("swe-gym", "getmoto__moto-5752", "f70b1a29")
    assert ids1 == ids2
    assert ids1["trace_id"].startswith("ptrace:")
    assert ids1["run_id"].startswith("run:")
    assert ids1["trace_id"][len("ptrace:") :] == ids1["run_id"][len("run:") :]


def test_identity_hash_changes_with_revision():
    a = env.derive_ids("swe-gym", "x", "rev-a")
    b = env.derive_ids("swe-gym", "x", "rev-b")
    assert a["trace_id"] != b["trace_id"]


def test_content_hash_excludes_self_and_validation():
    trace = {
        "build": {"content_hash": "SHOULD_BE_IGNORED"},
        "validation": {"status": "valid"},
        "labels": {"x": 1},
    }
    h1 = env.content_hash(trace)
    trace2 = copy.deepcopy(trace)
    trace2["build"]["content_hash"] = "DIFFERENT"
    trace2["validation"] = {"status": "invalid"}
    assert env.content_hash(trace2) == h1  # blanked/removed before hashing


def _minimal_valid_trace():
    return {
        "schema_version": "0.1.0",
        "trace_id": "ptrace:abc123",
        "run_id": "run:abc123",
        "adapter": {"name": "swe-gym", "version": "0.1.0"},
        "provenance": {
            "dataset": "swe-gym",
            "source_id": "x",
            "hf_repo": "r",
            "hf_revision": "rev",
            "source_file": "f",
            "source_row": 0,
        },
        "build": {
            "deterministic": True,
            "content_hash": "h",
            "generated_from": ["dataset"],
            "frame_sources": {"world-frame": "dataset-derived"},
        },
        "privacy": {"status": "clean", "pii_scanned": False, "redactions": []},
        "labels": {},
        "oracle": {"kind": "test-based"},
        "reference_supervision": {},
        "frames": [{"frame_kind": "world"}],
    }


def test_valid_envelope_passes():
    assert env.envelope_errors(_minimal_valid_trace()) == []


def test_malformed_envelope_rejected():
    bad = _minimal_valid_trace()
    del bad["provenance"]
    errs = env.envelope_errors(bad)
    assert errs and any("provenance" in e for e in errs)
