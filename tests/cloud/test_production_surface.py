from __future__ import annotations

import copy

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.production_surface import require_production_execution_surface


def surface() -> dict:
    roles = []
    for index, role in enumerate(("controller", "model-server", "benchmark-worker")):
        controller = role == "controller"
        roles.append({
            "role": role,
            "image_digest": "sha256:" + str(index + 1) * 64,
            "entrypoint": ["python3", "-m", "pneuma_lab.cloud.production_runtime", role],
            "source_sha256": chr(97 + index) * 64,
            "e2e_receipt_sha256": chr(100 + index) * 64,
            "gates": {
                "clean_start": True,
                "expected_terminal_state": True,
                "failure_receipt": True,
                "no_class_a_secret": True,
                "no_controller_credentials": not controller,
                "imds_blocked": True,
                "docker_socket_absent": not controller,
            },
        })
    return {
        "record_kind": "cloud_production_execution_surface",
        "schema_version": "0.1.0",
        "input_lock_sha256": "f" * 64,
        "source_commit": "1" * 40,
        "roles": roles,
    }


def test_exact_three_role_surface_passes() -> None:
    assert len(require_production_execution_surface(surface())["roles"]) == 3


def test_duplicate_role_or_entrypoint_fails() -> None:
    for field in ("role", "entrypoint"):
        row = copy.deepcopy(surface())
        row["roles"][1][field] = row["roles"][0][field]
        with pytest.raises(CloudManifestError):
            require_production_execution_surface(row)


def test_runtime_interpreter_must_match_built_images() -> None:
    row = surface()
    row["roles"][0]["entrypoint"][0] = "python"
    with pytest.raises(CloudManifestError, match="sealed role runtime"):
        require_production_execution_surface(row)


@pytest.mark.parametrize("role_index", [1, 2])
def test_unprivileged_role_cannot_expose_controller_surface(role_index: int) -> None:
    row = surface()
    row["roles"][role_index]["gates"]["docker_socket_absent"] = False
    with pytest.raises(CloudManifestError, match="Docker socket"):
        require_production_execution_surface(row)
