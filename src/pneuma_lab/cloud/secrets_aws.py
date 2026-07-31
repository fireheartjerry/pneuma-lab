"""Class-B infrastructure-secret references only; never opens Class-A keys."""

from .errors import CloudManifestError


def validate_class_b_reference(reference: str) -> str:
    if not reference.startswith("arn:aws:secretsmanager:") or "assignment" in reference.lower() or "unblind" in reference.lower():
        raise CloudManifestError("only Class-B AWS-managed secret references are permitted")
    return reference
