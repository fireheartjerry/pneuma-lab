"""T1 local behavioral fakes; deliberately not AWS emulators."""

from .control_plane import LocalControlPlane

__all__ = ["LocalControlPlane"]
