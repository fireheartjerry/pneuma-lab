"""Deterministic canonical serialisation and digests for review records.

The adversarial-review system is replay-deterministic: the same inputs and the
same reviewer proposals must produce byte-identical records and therefore an
identical disposition hash. That requires one canonical encoding, used
everywhere, with no locale, insertion-order, or float formatting freedom.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

CANONICAL_ENCODING = "utf-8"
DIGEST_ALGORITHM = "sha256"


def canonical_json(value: Any) -> str:
    """Return the canonical JSON text for ``value``.

    Sorted keys, no insignificant whitespace, ASCII-escaped, and a trailing
    newline so the text is a well-formed POSIX file when written directly.
    """

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ) + "\n"


def canonical_bytes(value: Any) -> bytes:
    """Return the canonical JSON bytes for ``value``."""

    return canonical_json(value).encode(CANONICAL_ENCODING)


def digest_bytes(payload: bytes) -> str:
    """Return the lowercase hex SHA-256 of ``payload``."""

    return hashlib.sha256(payload).hexdigest()


def digest_value(value: Any) -> str:
    """Return the lowercase hex SHA-256 of the canonical encoding of ``value``."""

    return digest_bytes(canonical_bytes(value))


def digest_file(path: str) -> str:
    """Return the lowercase hex SHA-256 of the file at ``path``.

    Read in bounded chunks so a large artifact bundle does not have to be held
    in memory during a campaign preflight.
    """

    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def is_sha256_hex(value: object) -> bool:
    """Return whether ``value`` is a well-formed lowercase hex SHA-256 string."""

    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)
