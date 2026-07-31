"""Errors for cloud-preparation records; none authorize external actions."""


class CloudManifestError(ValueError):
    """Raised when an immutable cloud-preparation record is invalid."""
