"""Worker-visible environment is deliberately narrow and non-scientific."""

from __future__ import annotations

from collections.abc import Mapping

from .errors import CloudManifestError


_FORBIDDEN = frozenset({"ARM", "ANSWER", "THRESHOLD", "AWS_SECRET", "AWS_ACCESS_KEY", "CONTROLLER"})


def build_worker_env(values: Mapping[str, str]) -> dict[str, str]:
    result = dict(values)
    if any(token in key.upper() or token in value.upper() for key, value in result.items() for token in _FORBIDDEN):
        raise CloudManifestError("worker environment contains forbidden authority or arm material")
    return result
