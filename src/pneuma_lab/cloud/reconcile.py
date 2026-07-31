"""Fail-closed reconciliation for completed local orchestration leases."""

from __future__ import annotations

from .orchestration import Lease


def reconcile(lease: Lease) -> str:
    if lease.state == "terminal":
        return "one_valid_terminal_history"
    if lease.state == "invalid":
        return "whole_task_block_invalid"
    if lease.state == "active":
        return "resume_required"
    return "expired_fail_closed"
