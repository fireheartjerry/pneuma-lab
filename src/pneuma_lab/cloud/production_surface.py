"""Validation for the real three-role cloud execution surface."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_production_execution_surface


ROLES = frozenset({"controller", "model-server", "benchmark-worker"})


def require_production_execution_surface(record: Mapping[str, Any]) -> dict[str, Any]:
    surface = validate_production_execution_surface(record)
    roles = surface["roles"]
    names = [item["role"] for item in roles]
    if len(set(names)) != 3 or set(names) != ROLES:
        raise CloudManifestError("production surface requires each exact role once")
    entrypoints = [tuple(item["entrypoint"]) for item in roles]
    if len(set(entrypoints)) != 3:
        raise CloudManifestError("production roles must not share one entrypoint")
    for role in roles:
        gates = role["gates"]
        if role["role"] == "controller":
            if gates["docker_socket_absent"]:
                raise CloudManifestError("controller must honestly record its Docker socket")
        elif not gates["docker_socket_absent"]:
            raise CloudManifestError("unprivileged role exposes the Docker socket")
        if role["role"] == "controller":
            if gates["no_controller_credentials"]:
                raise CloudManifestError("controller must honestly record controller credentials")
        elif not gates["no_controller_credentials"]:
            raise CloudManifestError("unprivileged role exposes controller credentials")
        if not all(gates.values() if role["role"] != "controller" else (
            gates["clean_start"], gates["expected_terminal_state"],
            gates["failure_receipt"], gates["no_class_a_secret"], gates["imds_blocked"],
        )):
            raise CloudManifestError(f"production role {role['role']} has a failing E2E gate")
    return surface
