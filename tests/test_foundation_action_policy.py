"""Signed local scopes and sole-operator high-impact denials."""

from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.foundation.action_policy import (
    HIGH_IMPACT_CLASSES,
    ActionDenied,
    LocalActionGuard,
    SignedLocalScope,
)


def _scope(root: Path, key: bytes, *, expires_at: int = 2_000) -> SignedLocalScope:
    return SignedLocalScope.issue(
        repository_root=root,
        allowed_tools=("python", "pytest"),
        expires_at=expires_at,
        signer_id="sole-operator",
        nonce="test-nonce",
        signing_key=key,
    )


def test_signed_scope_allows_only_named_tool_inside_repository(tmp_path: Path) -> None:
    key = b"test-only-local-key"
    scope = _scope(tmp_path, key)
    guard = LocalActionGuard(signing_keys={"sole-operator": key}, sole_operator=True)
    decision = guard.authorize(
        action_class="local_write",
        tool="pytest",
        target=tmp_path / "tests" / "test_x.py",
        scope=scope,
        now=1_000,
    )
    assert decision.allowed is True

    with pytest.raises(ActionDenied, match="outside"):
        guard.authorize(
            action_class="local_write",
            tool="pytest",
            target=tmp_path.parent / "outside.txt",
            scope=scope,
            now=1_000,
        )
    with pytest.raises(ActionDenied, match="tool"):
        guard.authorize(
            action_class="local_write",
            tool="deploy",
            target=tmp_path / "inside.txt",
            scope=scope,
            now=1_000,
        )


@pytest.mark.parametrize("action_class", sorted(HIGH_IMPACT_CLASSES))
def test_every_high_impact_class_is_denied_for_sole_operator(
    tmp_path: Path,
    action_class: str,
) -> None:
    key = b"test-only-local-key"
    guard = LocalActionGuard(signing_keys={"sole-operator": key}, sole_operator=True)
    with pytest.raises(ActionDenied, match="high-impact"):
        guard.authorize(
            action_class=action_class,
            tool="python",
            target=tmp_path / "inside.txt",
            scope=_scope(tmp_path, key),
            now=1_000,
        )


def test_expired_or_tampered_scope_fails_closed(tmp_path: Path) -> None:
    key = b"test-only-local-key"
    guard = LocalActionGuard(signing_keys={"sole-operator": key}, sole_operator=True)
    with pytest.raises(ActionDenied, match="expired"):
        guard.authorize(
            action_class="local_read",
            tool="python",
            target=tmp_path / "x.py",
            scope=_scope(tmp_path, key, expires_at=900),
            now=1_000,
        )
    scope = _scope(tmp_path, key)
    tampered = SignedLocalScope(
        repository_root=scope.repository_root,
        allowed_tools=("python", "pytest", "deploy"),
        expires_at=scope.expires_at,
        signer_id=scope.signer_id,
        nonce=scope.nonce,
        signature=scope.signature,
    )
    with pytest.raises(ActionDenied, match="signature"):
        guard.authorize(
            action_class="local_read",
            tool="python",
            target=tmp_path / "x.py",
            scope=tampered,
            now=1_000,
        )
