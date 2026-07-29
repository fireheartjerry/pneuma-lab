"""Controller-owned deterministic stepping primitives."""

from __future__ import annotations

import hashlib
from typing import Literal

from .assignment import TextField, U64Field, kdf_frame


def derive_call_seed(
    slot_seed: int,
    subject_role: Literal["primary_subject", "user_simulator"],
    call_index: int,
) -> int:
    """Derive one role/index-separated uint64 call seed."""

    if type(slot_seed) is not int:
        raise TypeError("slot_seed must be an exact int")
    if not 0 <= slot_seed < 2**64:
        raise ValueError("slot_seed must fit uint64")
    if type(subject_role) is not str:
        raise TypeError("subject_role must be exact str")
    if subject_role not in ("primary_subject", "user_simulator"):
        raise ValueError("subject_role is not registered")
    if type(call_index) is not int:
        raise TypeError("call_index must be an exact int")
    if not 0 <= call_index < 2**64:
        raise ValueError("call_index must fit uint64")
    payload = kdf_frame(
        "call-seed-v1",
        [
            U64Field(slot_seed),
            TextField(subject_role),
            U64Field(call_index),
        ],
    )
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")
