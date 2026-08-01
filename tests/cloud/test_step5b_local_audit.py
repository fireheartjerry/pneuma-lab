from __future__ import annotations

from scripts.research.step5b_local_audit import classify_licence


def test_classifies_registered_permissive_licence() -> None:
    value = b"Permission is hereby granted, free of charge, to any person obtaining a copy"
    assert classify_licence(value) == ("MIT", "unambiguous_registered_permissive")


def test_refuses_mixed_copyleft_terms() -> None:
    value = b"Permission is hereby granted, free of charge. GNU General Public License"
    assert classify_licence(value) == (None, "copyleft_or_mixed_terms_present")


def test_refuses_unknown_text() -> None:
    assert classify_licence(b"Copyright. All rights reserved.") == (None, "unrecognised")


def test_classifies_spdx_declared_bsd_licence() -> None:
    value = b"SPDX-License-Identifier: BSD-2-Clause\nRedistribution and use are permitted"
    assert classify_licence(value) == ("BSD-2-Clause", "unambiguous_registered_permissive_spdx")
