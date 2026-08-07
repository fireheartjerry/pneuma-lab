from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "finalize_official_study", ROOT / "scripts/research/finalize_official_study.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

COMMITMENT_REF = {
    "role": "rng_commitment",
    "relative_path": "inputs/rng-commitment.json",
    "sha256": "a" * 64,
    "byte_count": 12,
    "media_type": "application/json",
}


def _sealed_rng() -> dict[str, object]:
    return {
        "contract_id": "official-study-rng-v1",
        "root_u64": 3559187605953737994,
        "draw_domains": list(MODULE.SEED_NAMES),
        "seeds": {
            name: f"{index:064x}" for index, name in enumerate(MODULE.SEED_NAMES)
        },
        "status": "sealed",
        "commitment_ref": {"role": "rng_commitment", "relative_path": "old.json"},
    }


def _package(tmp_path: Path, run_spec: object, *, name: str = "package.tar.gz") -> Path:
    payload = (json.dumps(run_spec, sort_keys=True) + "\n").encode("utf-8")
    source = tmp_path / f"{name}.run-spec.json"
    source.write_bytes(payload)
    archive = tmp_path / name
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(source, arcname="run-spec.json")
    return archive


def test_sealed_rng_block_is_carried_forward_verbatim(tmp_path: Path) -> None:
    rng = _sealed_rng()
    archive = _package(tmp_path, {"rng": rng})

    carried = MODULE._carried_rng(archive, COMMITMENT_REF)

    assert carried["root_u64"] == rng["root_u64"]
    assert carried["seeds"] == rng["seeds"]
    assert carried["draw_domains"] == list(MODULE.SEED_NAMES)
    assert carried["status"] == "sealed"


def test_carry_forward_rebinds_the_commitment_reference(tmp_path: Path) -> None:
    """The successor package binds its own commitment file, not the prior one."""

    archive = _package(tmp_path, {"rng": _sealed_rng()})

    carried = MODULE._carried_rng(archive, COMMITMENT_REF)

    assert carried["commitment_ref"] == COMMITMENT_REF


def test_carry_forward_refuses_an_unsealed_block(tmp_path: Path) -> None:
    rng = _sealed_rng() | {"status": "pending_commitments"}
    archive = _package(tmp_path, {"rng": rng})

    with pytest.raises(ValueError, match="not sealed"):
        MODULE._carried_rng(archive, COMMITMENT_REF)


def test_carry_forward_refuses_a_different_contract(tmp_path: Path) -> None:
    rng = _sealed_rng() | {"contract_id": "some-other-rng-v9"}
    archive = _package(tmp_path, {"rng": rng})

    with pytest.raises(ValueError, match="contract differs"):
        MODULE._carried_rng(archive, COMMITMENT_REF)


def test_carry_forward_refuses_altered_draw_domains(tmp_path: Path) -> None:
    rng = _sealed_rng() | {"draw_domains": ["roster", "schedule"]}
    archive = _package(tmp_path, {"rng": rng})

    with pytest.raises(ValueError, match="draw domains differ"):
        MODULE._carried_rng(archive, COMMITMENT_REF)


def test_carry_forward_refuses_an_altered_seed_closure(tmp_path: Path) -> None:
    rng = _sealed_rng()
    del rng["seeds"]["unblind"]
    archive = _package(tmp_path, {"rng": rng})

    with pytest.raises(ValueError, match="seed closure differs"):
        MODULE._carried_rng(archive, COMMITMENT_REF)


def test_carry_forward_refuses_malformed_seed_digests(tmp_path: Path) -> None:
    rng = _sealed_rng()
    rng["seeds"]["model"] = "not-a-digest"
    archive = _package(tmp_path, {"rng": rng})

    with pytest.raises(ValueError, match="seed digests are malformed"):
        MODULE._carried_rng(archive, COMMITMENT_REF)


@pytest.mark.parametrize("root", [-1, 2**64, "3559187605953737994", 1.0, True])
def test_carry_forward_refuses_a_non_uint64_root(tmp_path: Path, root: object) -> None:
    rng = _sealed_rng() | {"root_u64": root}
    archive = _package(tmp_path, {"rng": rng}, name=f"package-{abs(hash(root))}.tar.gz")

    with pytest.raises(ValueError, match="not an exact uint64"):
        MODULE._carried_rng(archive, COMMITMENT_REF)


def test_carry_forward_refuses_a_missing_rng_block(tmp_path: Path) -> None:
    archive = _package(tmp_path, {"action_id": "official-p0-step4b-c120-20260807-r9"})

    with pytest.raises(ValueError, match="no RNG block"):
        MODULE._carried_rng(archive, COMMITMENT_REF)


def test_carry_forward_refuses_an_absent_package(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="carry-forward package is absent"):
        MODULE._carried_rng(tmp_path / "missing.tar.gz", COMMITMENT_REF)
