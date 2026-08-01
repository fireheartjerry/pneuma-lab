"""Terraform L1 validation status, resolved against an explicit search path.

The only thing this module decides is whether a terraform binary is reachable
and therefore whether L1 (static, credential-free) validation is *available*.
It never runs terraform, never reads credentials, and never plans or applies.

Resolution takes an explicit `search_path` rather than reading the ambient
environment, which is what makes both outcomes testable. A test can hand this
an empty directory to exercise the absent case on a machine where terraform is
installed, or a directory holding a stub to exercise the present case on a
machine where it is not. Neither test then depends on the developer's laptop.

L1 availability is not account evidence. A passing `fmt`/`validate` says the
configuration parses and is internally consistent; it says nothing about the
account, the applied quota, or an account-bound plan.
"""

from __future__ import annotations

import os
import shutil

from .errors import CloudManifestError


ABSENT = "terraform_absent_l1_validation_pending"
PRESENT = "terraform_present_l1_validation_available"


def resolve_terraform(search_path: str | None = None) -> str | None:
    """Return the terraform path on `search_path`, or None when unreachable.

    `search_path` is an OS path-separated string. Passing an empty string means
    "search nowhere" and deterministically yields None; passing None falls back
    to the ambient PATH, which is only appropriate for an environmental check.
    """

    if search_path is None:
        search_path = os.environ.get("PATH", "")
    if not search_path:
        return None
    return shutil.which("terraform", path=search_path)


def terraform_status(search_path: str | None = None) -> dict[str, object]:
    """Report L1 availability as a derived record, never an asserted one."""

    located = resolve_terraform(search_path)
    return {
        "status": ABSENT if located is None else PRESENT,
        "terraform_path": located,
        "l1_validation_available": located is not None,
        # Stated on every record so a caller cannot read L1 availability as
        # account, quota, plan, or deployment evidence.
        "account_evidence": False,
    }


def require_terraform_for_l1(search_path: str | None = None) -> str:
    """Return the binary path, or fail closed when L1 validation is unavailable."""

    located = resolve_terraform(search_path)
    if located is None:
        raise CloudManifestError("terraform is unreachable: L1 static validation is pending, and no L1 claim may be recorded")
    return located
