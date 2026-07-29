"""Tests for the canonical resampling-null assignment derivation core."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
import copy
from dataclasses import FrozenInstanceError
import hashlib
from importlib import import_module
import os
from pathlib import Path
from typing import cast

import pytest

from pneuma_lab.resampling_null.assignment import (
    BytesField,
    FrameField,
    TextField,
    U64Field,
    UniformDraw,
    _AssignmentKeyBuffers,
    _derive_assignment_subkeys_into,
    _derive_unblind_subkey_into,
    _wipe_bytearray,
    commitment_sha256,
    derive_seed,
    kdf_frame,
    uniform_below,
)
import pneuma_lab.resampling_null.assignment as assignment_module
from pneuma_lab.resampling_null.types import ArtifactRef


FRAME_HEX = (
    "706e65756d612d726573616d706c696e672d6e756c6c2d6672616d652d763100"
    "0000000e6465726976652d736565642d763100000003"
    "01000000080000000000000007"
    "02000000067461736b2d31"
    "0200000006707265666978"
)
FRAME_SHA256 = "d0f92ef02cc64124ae8d651ad65c1f799f94fac4bd9923804cefbec2928cb327"
SCHEDULE_COMMITMENT = "9bc37b258cc847128e49ed05681652da344723220886ec59193e53a1c8577760"
SUBKEY_HEX = {
    "donor": "ba38f59248c6fddad640c1a047ee1ecf38a0420cc1546d2370f1b6534dc16517",
    "allocation": "225e87f89450b1297025d2de9c5871785fba25ec1c4c8ea2dc3b1cc0dbaffc29",
    "orientation": "1e69be341abf917e55156c95157c69fe70d3f0cd1d161fa6fbd11e189a8d6cf3",
    "capability": "64e481fc16011d95a1bdff96b43c5fbfc2c49df0b8203f56fca38e4a6fc8266a",
    "unblind": "19fd5926965155e44bc23ea0b2d804c7a1492a98183389e515eafb4b05290f6d",
}


def _manifest_ref() -> ArtifactRef:
    return ArtifactRef(
        "manifest",
        "manifest.json",
        "11" * 32,
        1,
        "application/json",
    )


def _schedule_ref() -> ArtifactRef:
    return ArtifactRef(
        "schedule",
        "schedule.json",
        "22" * 32,
        1,
        "application/json",
    )


class _TooManyFields(Sequence[FrameField]):
    def __len__(self) -> int:
        return 2**32

    def __getitem__(self, index: int) -> FrameField:
        raise IndexError(index)

    def __iter__(self) -> Iterator[FrameField]:
        raise AssertionError("oversized field count must reject before iteration")


class _InconsistentFields(Sequence[FrameField]):
    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> FrameField:
        if index == 0:
            return TextField("first")
        if index == 1:
            return TextField("smuggled")
        raise IndexError(index)


def test_t3_s03_frame_known_answer_vector_is_byte_exact() -> None:
    frame = kdf_frame(
        "derive-seed-v1",
        [U64Field(7), TextField("task-1"), TextField("prefix")],
    )
    assert frame.hex() == FRAME_HEX
    assert hashlib.sha256(frame).hexdigest() == FRAME_SHA256
    assert (
        int.from_bytes(hashlib.sha256(frame).digest()[:8], "big")
        == 15058118438168183076
    )


def test_t3_s03_frame_is_typed_length_prefixed_and_collision_resistant() -> None:
    assert kdf_frame(
        "frame-v1",
        [TextField("a"), TextField("bc")],
    ) != kdf_frame(
        "frame-v1",
        [TextField("ab"), TextField("c")],
    )
    assert kdf_frame("frame-v1", [TextField("7")]) != kdf_frame(
        "frame-v1",
        [U64Field(7)],
    )
    assert kdf_frame("frame-v1", [BytesField(b"7")]) != kdf_frame(
        "frame-v1",
        [TextField("7")],
    )


@pytest.mark.parametrize(
    "value",
    [-1, 2**64, True, 1.0, "7"],
)
def test_t3_s03_frame_rejects_invalid_u64(value: object) -> None:
    with pytest.raises((TypeError, ValueError), match="(?i)(u64|integer|range)"):
        kdf_frame("frame-v1", [U64Field(value)])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        "",
        "e\u0301",
        "line\nbreak",
        "join\u200der",
        "private\ue000",
        "unassigned\u0378",
        "\ud800",
    ],
)
def test_t3_s03_frame_rejects_noncanonical_or_category_c_text(value: str) -> None:
    with pytest.raises(ValueError, match="(?i)(text|tag|unicode|nfc|category|empty)"):
        kdf_frame("frame-v1", [TextField(value)])
    with pytest.raises(ValueError, match="(?i)(text|tag|unicode|nfc|category|empty)"):
        kdf_frame(value, [])


@pytest.mark.parametrize(
    "field",
    [
        TextField(cast(str, b"text")),
        BytesField(cast(bytes, bytearray(b"bytes"))),
        object(),
    ],
)
def test_t3_s03_frame_rejects_wrong_field_payload_or_variant(field: object) -> None:
    with pytest.raises((TypeError, ValueError), match="(?i)(field|text|bytes|type)"):
        kdf_frame("frame-v1", cast(Sequence[FrameField], [field]))


def test_t3_s03_frame_rejects_non_string_tag_and_oversized_field_count() -> None:
    with pytest.raises(TypeError, match="(?i)(tag|string)"):
        kdf_frame(cast(str, b"frame-v1"), [])
    with pytest.raises(ValueError, match="(?i)(field|count|32)"):
        kdf_frame("frame-v1", _TooManyFields())


def test_t3_s03_frame_rejects_sequence_that_lies_about_its_field_count() -> None:
    with pytest.raises(ValueError, match="(?i)(field|count|sequence)"):
        kdf_frame("frame-v1", _InconsistentFields())


def test_t3_s03_frame_records_are_frozen_and_slotted() -> None:
    values = [U64Field(7), TextField("text"), BytesField(b"bytes"), UniformDraw(1, 0)]
    for value in values:
        assert not hasattr(value, "__dict__")
        with pytest.raises(FrozenInstanceError):
            value.value = 2  # type: ignore[misc,union-attr]


def test_t3_s03_commitment_known_answer_and_label_value_discrimination() -> None:
    assert (
        commitment_sha256("schedule-seed", "kat-study", U64Field(7))
        == SCHEDULE_COMMITMENT
    )
    roster = commitment_sha256(
        "roster-local-nonce",
        "kat-study",
        BytesField(bytes(range(32))),
    )
    master = commitment_sha256(
        "assignment-master-key",
        "kat-study",
        BytesField(bytes(range(32))),
    )
    assert roster != master
    assert len(roster) == len(master) == 64


@pytest.mark.parametrize(
    ("label", "value"),
    [
        ("schedule-seed", BytesField(b"\x00" * 32)),
        ("roster-local-nonce", U64Field(7)),
        ("assignment-master-key", U64Field(7)),
        ("roster-local-nonce", BytesField(b"\x00" * 31)),
        ("assignment-master-key", BytesField(b"\x00" * 33)),
        ("unknown", BytesField(b"\x00" * 32)),
    ],
)
def test_t3_s03_commitment_rejects_cross_label_or_wrong_width(
    label: object,
    value: object,
) -> None:
    with pytest.raises(
        (TypeError, ValueError), match="(?i)(label|schedule|bytes|32|u64)"
    ):
        commitment_sha256(label, "study", value)  # type: ignore[arg-type]


def test_t3_s03_derive_seed_matches_normative_vector() -> None:
    assert derive_seed(7, "task-1", "prefix") == 15058118438168183076


def test_t3_s03_hkdf_assignment_and_unblind_subkeys_match_normative_vectors() -> None:
    master = bytearray(range(32))
    assignment_keys = _AssignmentKeyBuffers()
    unblind = bytearray(32)
    _derive_assignment_subkeys_into(
        memoryview(master),
        "kat-study",
        _manifest_ref(),
        _schedule_ref(),
        assignment_keys,
    )
    _derive_unblind_subkey_into(
        memoryview(master),
        "kat-study",
        _manifest_ref(),
        _schedule_ref(),
        unblind,
    )
    assert assignment_keys.donor.hex() == SUBKEY_HEX["donor"]
    assert assignment_keys.allocation.hex() == SUBKEY_HEX["allocation"]
    assert assignment_keys.orientation.hex() == SUBKEY_HEX["orientation"]
    assert assignment_keys.capability.hex() == SUBKEY_HEX["capability"]
    assert unblind.hex() == SUBKEY_HEX["unblind"]


def test_t3_s03_assignment_hkdf_extracts_once_and_expands_only_four_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import assignment

    original_new = assignment.hmac.new
    messages: list[object] = []

    def traced_new(key: object, message: object, digestmod: object) -> object:
        messages.append(message)
        return original_new(key, message, digestmod)  # type: ignore[arg-type]

    monkeypatch.setattr(assignment.hmac, "new", traced_new)
    keys = _AssignmentKeyBuffers()
    _derive_assignment_subkeys_into(
        memoryview(bytearray(range(32))),
        "kat-study",
        _manifest_ref(),
        _schedule_ref(),
        keys,
    )
    assert len(messages) == 5
    assert messages[1:] == [
        kdf_frame("assignment-subkey-v1", [TextField(label)]) + b"\x01"
        for label in ("donor", "allocation", "orientation", "capability")
    ]


@pytest.mark.parametrize(
    "master_view",
    [
        memoryview(bytearray(33))[:32],
        memoryview(bytearray(64))[16:48],
    ],
)
def test_t3_s03_hkdf_requires_the_whole_exact_32_byte_master_buffer(
    master_view: memoryview,
) -> None:
    with pytest.raises(ValueError, match="(?i)(master|mutable|32|view)"):
        _derive_assignment_subkeys_into(
            master_view,
            "kat-study",
            _manifest_ref(),
            _schedule_ref(),
            _AssignmentKeyBuffers(),
        )


def test_t3_s03_assignment_hkdf_wipes_partial_outputs_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import assignment

    original_new = assignment.hmac.new
    call_count = 0

    def failing_new(key: object, message: object, digestmod: object) -> object:
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            raise RuntimeError("injected derivation failure")
        return original_new(key, message, digestmod)  # type: ignore[arg-type]

    monkeypatch.setattr(assignment.hmac, "new", failing_new)
    keys = _AssignmentKeyBuffers()
    with pytest.raises(RuntimeError, match="injected derivation failure"):
        _derive_assignment_subkeys_into(
            memoryview(bytearray(range(32))),
            "kat-study",
            _manifest_ref(),
            _schedule_ref(),
            keys,
        )
    assert all(
        buffer == bytearray(32)
        for buffer in (
            keys.donor,
            keys.allocation,
            keys.orientation,
            keys.capability,
        )
    )


def test_t3_s03_assignment_hkdf_wipes_prk_after_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import assignment

    original_wipe = assignment._wipe_bytearray
    wiped_buffers: list[bytearray] = []

    def observed_wipe(buffer: bytearray) -> None:
        wiped_buffers.append(buffer)
        original_wipe(buffer)

    monkeypatch.setattr(assignment, "_wipe_bytearray", observed_wipe)
    _derive_assignment_subkeys_into(
        memoryview(bytearray(range(32))),
        "kat-study",
        _manifest_ref(),
        _schedule_ref(),
        _AssignmentKeyBuffers(),
    )
    assert len(wiped_buffers) == 1
    assert wiped_buffers[0] == bytearray(32)


def test_t3_s03_assignment_hkdf_wipes_destinations_on_invalid_master() -> None:
    keys = _AssignmentKeyBuffers()
    for buffer in (
        keys.donor,
        keys.allocation,
        keys.orientation,
        keys.capability,
    ):
        buffer[:] = b"\xaa" * 32
    with pytest.raises(ValueError, match="(?i)(master|mutable|32|view)"):
        _derive_assignment_subkeys_into(
            memoryview(bytearray(33))[:32],
            "kat-study",
            _manifest_ref(),
            _schedule_ref(),
            keys,
        )
    assert all(
        buffer == bytearray(32)
        for buffer in (
            keys.donor,
            keys.allocation,
            keys.orientation,
            keys.capability,
        )
    )


@pytest.mark.parametrize(
    "corrupt_allocation",
    [
        bytearray(b"\xbb" * 31),
        cast(bytearray, b"\xbb" * 32),
    ],
)
def test_t3_s03_assignment_hkdf_rejects_corrupt_destinations_before_hmac(
    monkeypatch: pytest.MonkeyPatch,
    corrupt_allocation: bytearray,
) -> None:
    from pneuma_lab.resampling_null import assignment

    def forbidden_new(key: object, message: object, digestmod: object) -> object:
        raise AssertionError("HMAC must not run for a corrupt destination")

    monkeypatch.setattr(assignment.hmac, "new", forbidden_new)
    keys = _AssignmentKeyBuffers()
    keys.donor[:] = b"\xaa" * 32
    keys.allocation = corrupt_allocation
    keys.orientation[:] = b"\xaa" * 32
    keys.capability[:] = b"\xaa" * 32

    with pytest.raises(ValueError, match="(?i)(destination|buffer|mutable|32)"):
        _derive_assignment_subkeys_into(
            memoryview(bytearray(range(32))),
            "kat-study",
            _manifest_ref(),
            _schedule_ref(),
            keys,
        )

    assert keys.donor == bytearray(32)
    assert keys.orientation == bytearray(32)
    assert keys.capability == bytearray(32)
    if type(corrupt_allocation) is bytearray:
        assert corrupt_allocation == bytearray(len(corrupt_allocation))


def test_t3_s03_unblind_hkdf_extracts_once_and_expands_only_unblind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import assignment

    original_new = assignment.hmac.new
    messages: list[object] = []

    def traced_new(key: object, message: object, digestmod: object) -> object:
        messages.append(message)
        return original_new(key, message, digestmod)  # type: ignore[arg-type]

    monkeypatch.setattr(assignment.hmac, "new", traced_new)
    destination = bytearray(32)
    _derive_unblind_subkey_into(
        memoryview(bytearray(range(32))),
        "kat-study",
        _manifest_ref(),
        _schedule_ref(),
        destination,
    )
    assert len(messages) == 2
    assert messages[1] == (
        kdf_frame("assignment-subkey-v1", [TextField("unblind")]) + b"\x01"
    )
    assert destination.hex() == SUBKEY_HEX["unblind"]


def test_t3_s03_unblind_hkdf_wipes_destination_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import assignment

    original_new = assignment.hmac.new
    call_count = 0

    def failing_new(key: object, message: object, digestmod: object) -> object:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("injected unblind failure")
        return original_new(key, message, digestmod)  # type: ignore[arg-type]

    monkeypatch.setattr(assignment.hmac, "new", failing_new)
    destination = bytearray(b"\xaa" * 32)
    with pytest.raises(RuntimeError, match="injected unblind failure"):
        _derive_unblind_subkey_into(
            memoryview(bytearray(range(32))),
            "kat-study",
            _manifest_ref(),
            _schedule_ref(),
            destination,
        )
    assert destination == bytearray(32)


def test_t3_s03_unblind_hkdf_wipes_wrong_length_mutable_destination() -> None:
    destination = bytearray(b"\xaa" * 31)
    with pytest.raises(ValueError, match="(?i)(destination|mutable|32)"):
        _derive_unblind_subkey_into(
            memoryview(bytearray(range(32))),
            "kat-study",
            _manifest_ref(),
            _schedule_ref(),
            destination,
        )
    assert destination == bytearray(31)


def test_t3_s03_uniform_draws_match_normative_vectors() -> None:
    master = bytearray(range(32))
    keys = _AssignmentKeyBuffers()
    _derive_assignment_subkeys_into(
        memoryview(master),
        "kat-study",
        _manifest_ref(),
        _schedule_ref(),
        keys,
    )
    allocation_frame = kdf_frame("allocation-v1", [TextField("task-1")])
    orientation_frame = kdf_frame("orientation-v1", [TextField("task-1")])
    assert uniform_below(keys.allocation, allocation_frame, 12) == UniformDraw(3, 0)
    assert uniform_below(keys.orientation, orientation_frame, 2) == UniformDraw(0, 0)


@pytest.mark.parametrize("upper", [0, -1, 2**64 + 1, True, 1.0, "2"])
def test_t3_s03_uniform_rejects_invalid_upper_before_hmac(upper: object) -> None:
    with pytest.raises(ValueError, match="(?i)(upper|integer|64)"):
        uniform_below(bytearray(32), b"frame", upper)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "key",
    [b"\x00" * 32, bytearray(31), bytearray(33), memoryview(bytearray(32))],
)
def test_t3_s03_uniform_requires_private_mutable_32_byte_key(key: object) -> None:
    with pytest.raises(ValueError, match="(?i)(key|mutable|32)"):
        uniform_below(key, b"frame", 2)  # type: ignore[arg-type]


def test_t3_s03_uniform_rejection_path_is_counter_framed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pneuma_lab.resampling_null import assignment

    values = iter([2**64 - 1, 5])
    observed_frames: list[bytes] = []

    class _FakeHmac:
        def __init__(self, value: int) -> None:
            self._value = value

        def digest(self) -> bytes:
            return self._value.to_bytes(8, "big") + b"\x00" * 24

    def fake_new(key: object, message: bytes, digestmod: object) -> _FakeHmac:
        assert type(key) is bytearray
        assert digestmod is hashlib.sha256
        observed_frames.append(message)
        return _FakeHmac(next(values))

    monkeypatch.setattr(assignment.hmac, "new", fake_new)
    draw = uniform_below(bytearray(32), b"message-frame", 3)
    assert draw == UniformDraw(value=2, counter=1)
    assert observed_frames == [
        kdf_frame(
            "uniform-below-v1",
            [BytesField(b"message-frame"), U64Field(0)],
        ),
        kdf_frame(
            "uniform-below-v1",
            [BytesField(b"message-frame"), U64Field(1)],
        ),
    ]


@pytest.mark.parametrize("word_bits", range(1, 9))
def test_t3_s03_rejection_arithmetic_is_exact_for_small_words(word_bits: int) -> None:
    population = 1 << word_bits
    for upper in range(1, population + 1):
        limit = population - (population % upper)
        assert limit % upper == 0
        assert 0 <= population - limit < upper
        residue_counts = [
            sum(value % upper == residue for value in range(limit))
            for residue in range(upper)
        ]
        assert residue_counts == [limit // upper] * upper


def test_t3_s03_wipe_zeroes_application_owned_buffers() -> None:
    buffer = bytearray(range(32))
    _wipe_bytearray(buffer)
    assert buffer == bytearray(32)


def test_t3_s04_store_claims_assignment_handle_and_reads_exact_master(
    tmp_path: Path,
) -> None:
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(bytes(range(32)))
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()

    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    handle = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    destination = bytearray(32)

    assignment_api = import_module("pneuma_lab.resampling_null.assignment")
    assignment_api._read_exact_master_into(handle, destination)

    assert type(handle) is secret_api.AssignmentSecretHandle
    assert destination == bytearray(range(32))
    store.close()


def test_t3_s04_assignment_handle_is_single_use(tmp_path: Path) -> None:
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(bytes(range(32)))
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    handle = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    assignment_api = import_module("pneuma_lab.resampling_null.assignment")
    assignment_api._read_exact_master_into(handle, bytearray(32))
    untouched = bytearray(b"\xaa" * 32)

    with pytest.raises(ValueError, match="(?i)(consumed|registered|unused)"):
        assignment_api._read_exact_master_into(handle, untouched)

    assert untouched == bytearray(32)
    store.close()


def test_t3_s04_assignment_handle_is_nominal_and_store_minted(
    tmp_path: Path,
) -> None:
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(bytes(range(32)))
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)

    with pytest.raises(TypeError, match="(?i)(construct|mint|private)"):
        secret_api.AssignmentSecretHandle(store)
    with pytest.raises(TypeError, match="(?i)(subclass|final|nominal)"):

        class _ForgedHandle(secret_api.AssignmentSecretHandle):
            pass

    handle = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    with pytest.raises(TypeError, match="(?i)(copy|nominal|handle)"):
        copy.copy(handle)
    with pytest.raises(TypeError, match="(?i)(copy|nominal|handle)"):
        copy.deepcopy(handle)
    store.close()


def test_t3_s04_store_claims_distinct_unblind_handle_and_reads_exact_master(
    tmp_path: Path,
) -> None:
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(bytes(reversed(range(32))))
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    handle = store.claim_unblind(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    destination = bytearray(32)

    assignment_api = import_module("pneuma_lab.resampling_null.assignment")
    assignment_api._read_exact_master_into(handle, destination)

    assert type(handle) is secret_api.UnblindSecretHandle
    assert not isinstance(handle, secret_api.AssignmentSecretHandle)
    assert destination == bytearray(reversed(range(32)))
    store.close()


@pytest.mark.parametrize(
    "case",
    [
        "relative_path",
        "inside_run_root",
        "terminal_symlink",
        "hard_link",
        "group_readable",
        "directory",
    ],
)
def test_t3_s04_claim_rejects_insecure_secret_source(
    tmp_path: Path,
    case: str,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_path = tmp_path / "assignment-master.key"

    if case == "relative_path":
        secret_path = Path("relative-assignment-master.key")
    elif case == "inside_run_root":
        secret_path = run_root / "assignment-master.key"
        secret_path.write_bytes(bytes(range(32)))
        secret_path.chmod(0o600)
    elif case == "terminal_symlink":
        target = tmp_path / "real-assignment-master.key"
        target.write_bytes(bytes(range(32)))
        target.chmod(0o600)
        secret_path.symlink_to(target)
    elif case == "hard_link":
        target = tmp_path / "real-assignment-master.key"
        target.write_bytes(bytes(range(32)))
        target.chmod(0o600)
        os.link(target, secret_path)
    elif case == "group_readable":
        secret_path.write_bytes(bytes(range(32)))
        secret_path.chmod(0o640)
    elif case == "directory":
        secret_path.mkdir()
    else:
        raise AssertionError(case)

    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    try:
        with pytest.raises(
            ValueError,
            match="(?i)(secret|absolute|run root|link|owner|permission|regular)",
        ):
            store.claim_assignment(
                _manifest_ref(),
                _schedule_ref(),
                run_root=run_root,
            )
    finally:
        store.close()


@pytest.mark.parametrize("secret_size", [31, 33])
def test_t3_s04_exact_read_wipes_destination_and_burns_malformed_secret(
    tmp_path: Path,
    secret_size: int,
) -> None:
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(b"\xaa" * secret_size)
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    handle = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    destination = bytearray(b"\xbb" * 32)
    assignment_api = import_module("pneuma_lab.resampling_null.assignment")

    with pytest.raises(ValueError, match="(?i)(master|secret|exact|32)"):
        assignment_api._read_exact_master_into(handle, destination)

    assert destination == bytearray(32)
    with pytest.raises(ValueError, match="(?i)(consumed|registered|unused)"):
        assignment_api._read_exact_master_into(handle, bytearray(32))
    store.close()


def test_t3_s04_registry_binds_context_and_purpose_and_burns_mismatch(
    tmp_path: Path,
) -> None:
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(bytes(range(32)))
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    wrong_schedule = ArtifactRef(
        "schedule",
        "schedule.json",
        "33" * 32,
        1,
        "application/json",
    )
    wrong_context = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )

    with pytest.raises(ValueError, match="(?i)(binding|context|purpose)"):
        secret_api._require_handle_binding(
            wrong_context,
            _manifest_ref(),
            wrong_schedule,
            run_root=run_root,
            purpose="assignment",
        )
    destination = bytearray(b"\xaa" * 32)
    assignment_api = import_module("pneuma_lab.resampling_null.assignment")
    with pytest.raises(ValueError, match="(?i)(consumed|registered|unused)"):
        assignment_api._read_exact_master_into(wrong_context, destination)
    assert destination == bytearray(32)

    wrong_purpose = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    with pytest.raises(ValueError, match="(?i)(binding|context|purpose)"):
        secret_api._require_handle_binding(
            wrong_purpose,
            _manifest_ref(),
            _schedule_ref(),
            run_root=run_root,
            purpose="unblind",
        )

    valid = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    secret_api._require_handle_binding(
        valid,
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
        purpose="assignment",
    )
    assignment_api._read_exact_master_into(valid, bytearray(32))
    store.close()


def test_t3_s04_consumption_rechecks_pinned_descriptor_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(bytes(range(32)))
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    handle = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    entry = store._registry[handle]
    descriptor = entry if type(entry) is int else entry.descriptor
    original_fstat = secret_api.os.fstat
    observed = original_fstat(descriptor)
    altered_values = list(observed)
    altered_values[1] += 1
    altered = os.stat_result(altered_values)

    def changed_fstat(fd: int) -> os.stat_result:
        return altered if fd == descriptor else original_fstat(fd)

    monkeypatch.setattr(secret_api.os, "fstat", changed_fstat)
    destination = bytearray(b"\xaa" * 32)
    assignment_api = import_module("pneuma_lab.resampling_null.assignment")
    with pytest.raises(ValueError, match="(?i)(identity|descriptor|changed)"):
        assignment_api._read_exact_master_into(handle, destination)
    assert destination == bytearray(32)
    store.close()


def test_t3_s04_secret_store_is_final_and_stably_exported() -> None:
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    package_api = import_module("pneuma_lab.resampling_null")
    for name in (
        "AssignmentSecretHandle",
        "AssignmentSecretStore",
        "UnblindSecretHandle",
    ):
        assert getattr(package_api, name) is getattr(secret_api, name)
        assert name in package_api.__all__

    with pytest.raises(TypeError, match="(?i)(final|subclass|concrete)"):

        class _CallerStore(secret_api.AssignmentSecretStore):
            pass


@pytest.mark.parametrize(
    "destination",
    [
        bytearray(b"\xaa" * 31),
        cast(bytearray, b"\xaa" * 32),
    ],
)
def test_t3_s04_invalid_destination_rejects_before_handle_consumption(
    tmp_path: Path,
    destination: bytearray,
) -> None:
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(bytes(range(32)))
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    handle = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    assignment_api = import_module("pneuma_lab.resampling_null.assignment")

    with pytest.raises(ValueError, match="(?i)(master|destination|mutable|32)"):
        assignment_api._read_exact_master_into(handle, destination)

    if type(destination) is bytearray:
        assert destination == bytearray(len(destination))
    valid_destination = bytearray(32)
    assignment_api._read_exact_master_into(handle, valid_destination)
    assert valid_destination == bytearray(range(32))
    store.close()


def test_t3_s04_claim_holds_original_descriptor_across_path_replacement(
    tmp_path: Path,
) -> None:
    secret_path = tmp_path / "assignment-master.key"
    original = bytes(range(32))
    replacement = bytes(reversed(range(32)))
    secret_path.write_bytes(original)
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    original_handle = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    archived_path = tmp_path / "archived.key"
    secret_path.rename(archived_path)
    secret_path.write_bytes(replacement)
    secret_path.chmod(0o600)
    replacement_handle = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    assignment_api = import_module("pneuma_lab.resampling_null.assignment")
    original_destination = bytearray(32)
    replacement_destination = bytearray(32)

    assignment_api._read_exact_master_into(original_handle, original_destination)
    assignment_api._read_exact_master_into(replacement_handle, replacement_destination)

    assert original_destination == bytearray(original)
    assert replacement_destination == bytearray(replacement)
    store.close()


def test_t3_s04_store_close_closes_unconsumed_handles_and_rejects_claims(
    tmp_path: Path,
) -> None:
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(bytes(range(32)))
    secret_path.chmod(0o600)
    run_root = tmp_path / "run"
    run_root.mkdir()
    secret_api = import_module("pneuma_lab.resampling_null.secrets")
    store = secret_api.AssignmentSecretStore(secret_path)
    handle = store.claim_assignment(
        _manifest_ref(),
        _schedule_ref(),
        run_root=run_root,
    )
    entry = store._registry[handle]
    descriptor = entry.descriptor

    store.close()

    with pytest.raises(OSError):
        os.fstat(descriptor)
    destination = bytearray(b"\xaa" * 32)
    assignment_api = import_module("pneuma_lab.resampling_null.assignment")
    with pytest.raises(ValueError, match="(?i)(consumed|registered|unused)"):
        assignment_api._read_exact_master_into(handle, destination)
    assert destination == bytearray(32)
    with pytest.raises(ValueError, match="(?i)(store|closed)"):
        store.claim_assignment(
            _manifest_ref(),
            _schedule_ref(),
            run_root=run_root,
        )


def test_t3_s05_assignment_authority_is_loaded_only_through_refs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_ref = ArtifactRef(
        role="manifest",
        relative_path="manifest.json",
        sha256="a" * 64,
        byte_count=1,
        media_type="application/json",
    )
    schedule_ref = ArtifactRef(
        role="schedule",
        relative_path="schedule.json",
        sha256="b" * 64,
        byte_count=2,
        media_type="application/json",
    )
    prefix_ref = ArtifactRef(
        role="prefix",
        relative_path="prefix.json",
        sha256="c" * 64,
        byte_count=3,
        media_type="application/json",
    )

    def ref_value(ref: ArtifactRef) -> dict[str, object]:
        return {
            "role": ref.role,
            "relative_path": ref.relative_path,
            "sha256": ref.sha256,
            "byte_count": ref.byte_count,
            "media_type": ref.media_type,
        }

    identity = {
        "study_id": "study-1",
        "frozen_created_at": "2026-07-28T12:00:00Z",
        "provenance": {"design_sha256": "d" * 64, "code_sha256": "e" * 64},
    }
    values = {
        "schedule_ref": {
            **identity,
            "payload": {"manifest_ref": ref_value(manifest_ref)},
        },
        "schedule manifest_ref": {**identity, "payload": {}},
        "prefix_index_ref": {
            **identity,
            "payload": {"schedule_ref": ref_value(schedule_ref)},
        },
    }
    calls: list[tuple[str, str]] = []

    class Document:
        def __init__(self, value: dict[str, object]) -> None:
            self.value = value

    def load_parent(
        value: object,
        *,
        run_root: Path,
        field: str,
        expected_kind: str,
        expected_stage: str | None = None,
    ) -> Document:
        del value, run_root, expected_stage
        calls.append((field, expected_kind))
        return Document(values[field])

    monkeypatch.setattr(
        assignment_module,
        "_load_direct_scientific_parent",
        load_parent,
    )

    authority = assignment_module.load_assignment_authority(
        schedule_ref,
        prefix_ref,
        run_root=tmp_path,
    )

    assert authority == assignment_module.AssignmentAuthority(
        study_id="study-1",
        frozen_created_at="2026-07-28T12:00:00Z",
        manifest_ref=manifest_ref,
        schedule_ref=schedule_ref,
        prefix_index_ref=prefix_ref,
    )
    assert calls == [
        ("schedule_ref", "resampling_prefix_schedule"),
        ("schedule manifest_ref", "resampling_study_manifest"),
        ("prefix_index_ref", "resampling_prefix_receipt"),
    ]

    values["prefix_index_ref"] = {
        **identity,
        "payload": {"schedule_ref": ref_value(manifest_ref)},
    }
    with pytest.raises(ValueError, match="does not descend"):
        assignment_module.load_assignment_authority(
            schedule_ref,
            prefix_ref,
            run_root=tmp_path,
        )


def test_t3_s06_matching_invocation_requires_real_signature() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    from pneuma_lab.foundation.artifacts import canonical_json_bytes

    private_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public_key_hex = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    unsigned: dict[str, object] = {
        "record_kind": "exact_matching_invocation_receipt_v1",
        "sequence_index": 0,
    }
    signature_hex = private_key.sign(
        canonical_json_bytes(unsigned, indent=None)
    ).hex()
    receipt = {**unsigned, "runner_signature_ed25519_hex": signature_hex}

    assert len(
        assignment_module.verify_matching_invocation_signature(
            receipt,
            runner_public_key_ed25519_hex=public_key_hex,
        )
    ) == 64
