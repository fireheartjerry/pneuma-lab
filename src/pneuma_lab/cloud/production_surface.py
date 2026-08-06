"""Validation for the real three-role cloud execution surface."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_production_execution_surface


ROLES = frozenset({"controller", "model-server", "benchmark-worker"})
_RUNTIME_MODULE = "pneuma_lab.cloud.production_runtime"


def require_production_execution_surface(record: Mapping[str, Any]) -> dict[str, Any]:
    surface = validate_production_execution_surface(record)
    roles = surface["roles"]
    names = [item["role"] for item in roles]
    if len(set(names)) != 3 or set(names) != ROLES:
        raise CloudManifestError("production surface requires each exact role once")
    entrypoints = [tuple(item["entrypoint"]) for item in roles]
    if len(set(entrypoints)) != 3:
        raise CloudManifestError("production roles must not share one entrypoint")
    if surface.get("schema_version") == "0.2.0":
        if (
            surface.get("surface_class")
            != "provenance_verified_official_batch_plan"
            or not isinstance(surface.get("launch_plan_sha256"), str)
        ):
            raise CloudManifestError("official Batch surface lacks its launch-plan binding")
        for role in roles:
            entrypoint = list(role["entrypoint"])
            if (
                entrypoint[:3] != ["python3", "-m", _RUNTIME_MODULE]
                or entrypoint[3:] != [role["role"]]
            ):
                raise CloudManifestError(
                    "production role must use the sealed role runtime entrypoint"
                )
            if not isinstance(role.get("sbom_sha256"), str) or not str(
                role.get("provenance_descriptor_digest", "")
            ).startswith("sha256:"):
                raise CloudManifestError(
                    f"production role {role['role']} lacks verified SBOM/provenance"
                )
        return surface
    for role in roles:
        entrypoint = list(role["entrypoint"])
        if entrypoint[:3] != ["python3", "-m", _RUNTIME_MODULE] or entrypoint[3:] != [role["role"]]:
            raise CloudManifestError("production role must use the sealed role runtime entrypoint")
        gates = role["gates"]
        hardened_surface = surface.get("e2e_class") == "non_scientific_bounded_surface"
        if hardened_surface:
            if not gates["docker_socket_absent"] or not gates["no_controller_credentials"]:
                raise CloudManifestError("provider-backed role surface must expose neither Docker nor credentials")
        elif role["role"] == "controller":
            if gates["docker_socket_absent"]:
                raise CloudManifestError("legacy qualification controller must honestly record its Docker socket")
            if gates["no_controller_credentials"]:
                raise CloudManifestError("legacy qualification controller must honestly record controller credentials")
        else:
            if not gates["docker_socket_absent"]:
                raise CloudManifestError("unprivileged role exposes the Docker socket")
            if not gates["no_controller_credentials"]:
                raise CloudManifestError("unprivileged role exposes controller credentials")
        if not all(gates.values() if role["role"] != "controller" else (
            gates["clean_start"], gates["expected_terminal_state"],
            gates["failure_receipt"], gates["no_class_a_secret"], gates["imds_blocked"],
        )):
            raise CloudManifestError(f"production role {role['role']} has a failing E2E gate")
    return surface
