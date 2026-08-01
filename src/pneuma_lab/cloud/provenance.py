"""Checkout-independent digests for provenance binding.

A provenance digest answers "was this record derived against these exact
contents", and it must give the same answer on every platform. Hashing raw
checkout bytes does not: Git may materialise a text file with CRLF endings on
Windows, so a digest committed from a Linux checkout fails on a Windows one even
though the content is identical. That turns a portability detail into a spurious
provenance failure, which is the worst kind of alarm — it trains readers to
ignore the mechanism that is supposed to catch real drift.

So text inputs are canonicalized before hashing: decoded as UTF-8, line endings
normalised to LF, and any trailing BOM removed. The digest then describes the
*content*, which is what provenance is about, and matches the bytes Git stores
in its blob for a text file with default normalisation.

Binary inputs must not go through this path — normalising a byte sequence that
merely happens to contain 0x0D 0x0A would corrupt it. Use `binary_digest` for
those; nothing in the provenance chain currently needs it, and the split is here
so a later caller does not reach for the text helper by default.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def canonical_text_bytes(payload: bytes) -> bytes:
    """Return the canonical form of a text payload: UTF-8, LF endings, no BOM."""

    text = payload.decode("utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def canonical_text_digest(path: Path) -> str:
    """Digest a text file by content, independent of the checkout's line endings."""

    return hashlib.sha256(canonical_text_bytes(path.read_bytes())).hexdigest()


def binary_digest(path: Path) -> str:
    """Digest a file byte for byte, for inputs that are not text."""

    return hashlib.sha256(path.read_bytes()).hexdigest()
