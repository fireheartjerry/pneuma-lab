"""Canonical text and digest identities shared by foundation data gates."""

from __future__ import annotations

import hashlib


_SHA256_PREFIX = "sha256:"
_HEX_CHARACTERS = frozenset("0123456789abcdef")


def normalize_identity_text(value: str | None) -> str | None:
    """Case-fold and collapse whitespace, returning null for empty text."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("identity value must be a string or null")
    normalized = " ".join(value.casefold().split())
    return normalized or None


def normalize_identity_digest(value: str | None) -> str | None:
    """Return one prefixed SHA-256 identity for valid digests or raw text."""

    normalized = normalize_identity_text(value)
    if normalized is None:
        return None
    if normalized.startswith(_SHA256_PREFIX):
        suffix = normalized.removeprefix(_SHA256_PREFIX)
        if len(suffix) == 64 and set(suffix) <= _HEX_CHARACTERS:
            return _SHA256_PREFIX + suffix
    if len(normalized) == 64 and set(normalized) <= _HEX_CHARACTERS:
        return _SHA256_PREFIX + normalized
    return _SHA256_PREFIX + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


__all__ = ["normalize_identity_digest", "normalize_identity_text"]
