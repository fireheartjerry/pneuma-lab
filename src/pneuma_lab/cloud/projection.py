"""Conservative projection comparison for local watchdog admission."""

from .errors import CloudManifestError


def require_within_projection(projected: float, ceiling: float) -> None:
    if projected < 0 or ceiling <= 0 or projected > ceiling:
        raise CloudManifestError("projected cost/runtime envelope exceeded")
